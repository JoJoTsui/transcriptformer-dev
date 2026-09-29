"""Audit B4 probe var keys against actual ESM vocabulary keys, without reading X.

The report distinguishes observed key coverage from source provenance. A generated
vocabulary needs its matching chunk-run manifest; older vocabularies without one
remain provenance-unverified even when their keys join.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import h5py


ROOT = Path(__file__).resolve().parents[1]
MAX_KEYS = 100_000
MAX_MAP_BYTES = 4 * 1024 * 1024
SYMBOL_MAPS = {
    "macaca_fascicularis": "macaca_fascicularis_probe_symbol_to_ensmfag.json",
    "xenopus_tropicalis": "xenopus_tropicalis_probe_symbol_to_ensxetg.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def key_sha256(keys: set[str]) -> str:
    digest = hashlib.sha256()
    for key in sorted(keys):
        digest.update(key.encode("utf-8") + b"\n")
    return digest.hexdigest()


def read_keys(dataset: h5py.Dataset) -> list[str]:
    if dataset.ndim != 1 or not 0 < len(dataset) <= MAX_KEYS:
        raise ValueError(f"{dataset.name}: expected 1..{MAX_KEYS} one-dimensional keys")
    keys = [value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in dataset[:]]
    if len(keys) != len(set(keys)) or any(not key for key in keys):
        raise ValueError(f"{dataset.name}: duplicate or empty keys")
    return keys


def read_probe(path: Path) -> tuple[set[str], str]:
    with h5py.File(path, "r") as source:
        var = source["var"]
        index = var.attrs["_index"]
        if isinstance(index, bytes):
            index = index.decode("utf-8")
        keys = read_keys(var[index])
    return set(keys), index


def read_vocab(path: Path) -> tuple[set[str], dict]:
    with h5py.File(path, "r") as source:
        keys = set(read_keys(source["keys"]))
        arrays = source["arrays"]
        if not isinstance(arrays, h5py.Group):
            raise ValueError(f"{path}: arrays is not an HDF5 group")
        missing = sum(key not in arrays or arrays[key].shape != (2560,) for key in keys)
        if missing:
            raise ValueError(f"{path}: {missing} keys lack 2560-dimensional arrays")
        identity = source.attrs.get("identity")
        complete = bool(source.attrs.get("complete", False))
    return keys, {"identity": identity, "complete": complete}


def provenance(path: Path, vocab: dict, expected_url: str | None,
               expected_sha256: str | None) -> dict:
    manifest = path.with_name(path.name + ".parts") / "manifest.json"
    if not manifest.is_file():
        return {"status": "unverified_no_run_manifest"}
    if manifest.stat().st_size > 64 * 1024:
        raise ValueError(f"{manifest}: run manifest exceeds cap")
    run = json.loads(manifest.read_text())
    expected = hashlib.sha256(json.dumps(run, sort_keys=True).encode("utf-8")).hexdigest()
    if not vocab["complete"] or vocab["identity"] != expected:
        raise ValueError(f"{path}: output identity does not match its run manifest")
    required = {"source_url", "source_sha256", "fasta_sha256", "model_name", "model_sha256", "esm_version", "layer"}
    if not required <= run.keys():
        raise ValueError(f"{manifest}: incomplete source/model provenance")
    if expected_url and run["source_url"] != expected_url:
        raise ValueError(f"{path}: run source URL differs from pinned species source")
    if expected_sha256 and run["source_sha256"] != expected_sha256:
        raise ValueError(f"{path}: run source hash differs from pinned archive")
    return {"status": "run_manifest_bound_source_hash_pinned" if expected_sha256 else
            "run_manifest_bound_source_hash_unpinned", "manifest_sha256": sha256(manifest),
            "run": run}


def audited_symbol_map(root: Path, species: str, probes: list[dict]) -> tuple[dict[str, str], dict]:
    mapping_path = root / "preprocess/gene_mappings" / SYMBOL_MAPS[species]
    audit_path = root / "logs/dataset_audit" / f"b4_{'macaque' if species.startswith('macaca') else 'xenopus'}_symbol_bridge.json"
    if mapping_path.stat().st_size > MAX_MAP_BYTES:
        raise ValueError(f"{mapping_path}: symbol bridge exceeds cap")
    mapping = json.loads(mapping_path.read_text())
    audit = json.loads(audit_path.read_text())
    if audit["species"] != species or sha256(mapping_path) != audit["mapping_sha256"]:
        raise ValueError(f"{species}: symbol bridge audit hash or species mismatch")
    if len(mapping) != audit["mapping_entries"] or len(set(mapping.values())) != len(mapping):
        raise ValueError(f"{species}: symbol bridge count or target uniqueness mismatch")
    if set(audit["probes"]) != {entry["id"] for entry in probes}:
        raise ValueError(f"{species}: symbol bridge probe set mismatch")
    return mapping, {"path": str(mapping_path), "sha256": audit["mapping_sha256"],
                     "audit_sha256": sha256(audit_path), "release": audit["ensembl_release"],
                     "pep_sha256": audit["pep_sha256"], "gtf_sha256": audit["gtf_sha256"]}


def amphioxus_bridge(root: Path) -> tuple[set[str], dict]:
    path = root / "preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz"
    metadata = json.loads(path.with_name(path.name + ".json").read_text())
    if sha256(path) != metadata["bridge_sha256"]:
        raise ValueError("Amphioxus bridge hash mismatch")
    if path.stat().st_size > MAX_MAP_BYTES:
        raise ValueError("Amphioxus bridge exceeds cap")
    with gzip.open(path, "rt") as source:
        if source.readline().rstrip("\n") != "protein_accession\tncbi_gene_id\tgene_key":
            raise ValueError("Amphioxus bridge columns differ")
        genes = {line.rstrip("\n").split("\t")[2] for line in source}
    if len(genes) != metadata["protein_bearing_gene_keys"]:
        raise ValueError("Amphioxus bridge gene count differs")
    return genes, {"path": str(path), "sha256": metadata["bridge_sha256"],
            "annotation_release": metadata["annotation_release"],
            "protein_fasta_sha256": metadata["protein_fasta_sha256"],
            "protein_fasta_url": metadata["protein_fasta_url"]}


def translate(species: str, probe_keys: set[str], mapping: dict[str, str] | None,
              allowed_direct: set[str] | None = None) -> tuple[dict[str, str], set[str]]:
    mapped = {}
    ambiguous = set()
    for key in probe_keys:
        if mapping is not None:
            target = mapping.get(key)
            if target is None:
                continue
        elif species == "cavia_porcellus":
            target = key.split(":", 1)[0]
            if not key.startswith("ENSCPOG") or ":" not in key:
                continue
        elif species == "sus_scrofa":
            if not key.startswith("ENSSSCG"):
                continue
            target = key
        elif allowed_direct is not None:
            if key not in allowed_direct:
                continue
            target = key
        else:
            target = key
        mapped[key] = target
    targets = {}
    for key, target in mapped.items():
        targets.setdefault(target, []).append(key)
    for aliases in targets.values():
        if len(aliases) > 1:
            ambiguous.update(aliases)
    for key in ambiguous:
        del mapped[key]
    return mapped, ambiguous


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=Path("preprocess/probe_stage_mappings.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = root / args.config
    config = json.loads(config_path.read_text())
    fasta_manifest = json.loads((root / config["fasta_manifest"]).read_text())
    entries = [entry for entry in config["datasets"] if entry["species"] != "danio_rerio"]
    species_entries = {species: [entry for entry in entries if entry["species"] == species]
                       for species in {entry["species"] for entry in entries}}
    maps = {}
    map_provenance = {}
    for species in SYMBOL_MAPS:
        maps[species], map_provenance[species] = audited_symbol_map(root, species, species_entries[species])
    amphioxus_keys, map_provenance["branchiostoma_floridae"] = amphioxus_bridge(root)
    result = {"schema_version": 1, "config_sha256": sha256(config_path),
              "scope": "H5AD var and HDF5 vocabulary keys/array shape only; no expression or embedding values read",
              "datasets": [], "vocabularies": {}}
    for species in sorted(species_entries):
        path = root / config["vocab_dir"] / f"{species}_gene.h5"
        if path.is_file():
            keys, attrs = read_vocab(path)
            expected_url = fasta_manifest.get(species, {}).get("fa")
            expected_sha256 = None
            if species in SYMBOL_MAPS:
                expected_url = json.loads((root / "logs/dataset_audit" / f"b4_{'macaque' if species.startswith('macaca') else 'xenopus'}_symbol_bridge.json").read_text())["pep_url"]
            elif species == "branchiostoma_floridae":
                expected_url = map_provenance[species]["protein_fasta_url"]
                expected_sha256 = map_provenance[species]["protein_fasta_sha256"]
            elif species == "ciona_intestinalis":
                expected_url = "https://ghost.zool.kyoto-u.ac.jp/download_kh.html"
                expected_sha256 = "91ae06cfab8010664f3d6a9a9ee18dff0375eb1cd581617f0988e59002b4d22a"
            source = provenance(path, attrs, expected_url, expected_sha256)
            result["vocabularies"][species] = {"path": str(path), "present": True,
                "gene_keys": len(keys), "key_sha256": key_sha256(keys), "provenance": source}
        else:
            keys = set()
            result["vocabularies"][species] = {"path": str(path), "present": False}
        for entry in species_entries[species]:
            probe_path = Path(entry["path"])
            if not probe_path.is_absolute():
                probe_path = root / probe_path
            probe_keys, column = read_probe(probe_path)
            if species in maps:
                expected = json.loads((root / "logs/dataset_audit" / f"b4_{'macaque' if species.startswith('macaca') else 'xenopus'}_symbol_bridge.json").read_text())["probes"][entry["id"]]
                if column != expected["var_column"] or key_sha256(probe_keys) != expected["probe_key_sha256"]:
                    raise ValueError(f"{entry['id']}: probe var index differs from audited symbol bridge")
            allowed_direct = amphioxus_keys if species == "branchiostoma_floridae" else None
            if species == "ciona_intestinalis":
                allowed_direct = {key for key in probe_keys if key.startswith("KH2012:KH.")}
                if key_sha256(allowed_direct) != "a307c7692e57bb92aa6762a6d4452c1d71181282a5a9ddcb595472e23e7920b5":
                    raise ValueError("Ciona KH probe set differs from pinned Ghost audit")
                map_provenance[species] = {"rule": "pinned Ghost KH2012 protein roots",
                    "source_zip_sha256": "91ae06cfab8010664f3d6a9a9ee18dff0375eb1cd581617f0988e59002b4d22a",
                    "probe_kh_sha256": key_sha256(allowed_direct)}
            mapped, ambiguous = translate(species, probe_keys, maps.get(species), allowed_direct)
            audited_ambiguous = 0
            if species in maps:
                audited_ambiguous = expected["ambiguous_peptide_symbols"]
            if ambiguous and audited_ambiguous:
                raise ValueError(f"{entry['id']}: overlapping ambiguity classes need row-level reconciliation")
            ambiguous_count = len(ambiguous) + audited_ambiguous
            present = path.is_file()
            joined = {key for key, target in mapped.items() if target in keys} if present else set()
            direct = {key for key in probe_keys if key in keys} if present else set()
            provenance_status = (
                result["vocabularies"][species]["provenance"]["status"]
                if present else None
            )
            status = (
                "vocabulary_missing" if not present else
                "measured" if provenance_status == "run_manifest_bound_source_hash_pinned" else
                "measured_provenance_unverified"
            )
            report = {"id": entry["id"], "species": species, "probe_path": str(probe_path),
                      "var_index": column, "probe_key_sha256": key_sha256(probe_keys),
                      "probe_genes": len(probe_keys), "direct_vocab_matches": len(direct) if present else None,
                      "bridge_eligible": len(mapped), "bridge_ambiguous_excluded": ambiguous_count,
                      "bridge_unmapped": len(probe_keys) - len(mapped) - ambiguous_count,
                      "actual_vocab_joined": len(joined) if present else None,
                      "eligible_absent_from_vocab": len(mapped) - len(joined) if present else None,
                      "actual_coverage_fraction": round(len(joined) / len(probe_keys), 6) if present else None,
                      "bridge_provenance": map_provenance.get(species, {"rule": "exact var key" if species != "cavia_porcellus" else "ENSCPOG prefix before colon"}),
                      "status": status}
            result["datasets"].append(report)
    serialized = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        output = args.output.resolve()
        inputs = {config_path.resolve(), (root / config["fasta_manifest"]).resolve()}
        inputs.update(Path(entry["path"]).resolve() for entry in entries)
        inputs.update(Path(item["path"]).resolve() for item in result["vocabularies"].values())
        inputs.update((root / "preprocess/gene_mappings" / name).resolve() for name in SYMBOL_MAPS.values())
        inputs.update((root / "logs/dataset_audit" / name).resolve() for name in
                      ("b4_macaque_symbol_bridge.json", "b4_xenopus_symbol_bridge.json"))
        inputs.add((root / "preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz").resolve())
        inputs.add((root / "preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz.json").resolve())
        if output in inputs:
            parser.error("Output cannot overwrite an input")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized)
    else:
        print(serialized, end="")
    return 0 if all(item["status"] == "measured" for item in result["datasets"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
