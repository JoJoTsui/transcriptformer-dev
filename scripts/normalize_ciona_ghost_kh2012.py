"""Audit a local Ghost KH2012 protein ZIP and optionally write gene-key FASTA.

The Ghost source and derived FASTA must stay outside the repository. This script
does not download data or run a protein model.
"""

import argparse
import hashlib
import json
import os
import re
import zipfile
from collections import Counter
from pathlib import Path


SOURCE_PAGE = "https://ghost.zool.kyoto-u.ac.jp/download_kh.html"
SOURCE_NAME = "KH.KHGene.2012.Longest.protein.zip"
FASTA_MEMBER = "KH.KHGene.2012.Longest.protein.fasta"
AUDITED_ZIP_SHA256 = "91ae06cfab8010664f3d6a9a9ee18dff0375eb1cd581617f0988e59002b4d22a"
MODEL_ID = re.compile(r"^(KH\.[A-Za-z0-9]+\.[0-9]+)\.v[0-9]+\.[^\s]+$")
GENE_KEY = re.compile(r"^KH2012:KH\.[A-Za-z0-9]+\.[0-9]+$")
PROTEIN_CHARS = frozenset("ACDEFGHIKLMNPQRSTVWYX+")
MAX_ZIP_BYTES = 16 * 1024 * 1024
MAX_FASTA_BYTES = 64 * 1024 * 1024
MAX_PROBE_GENES = 100_000


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_keys(keys):
    digest = hashlib.sha256()
    for key in sorted(keys):
        digest.update(key.encode("utf-8") + b"\n")
    return digest.hexdigest()


def read_probe_keys(path):
    import h5py

    with h5py.File(path, "r") as handle:
        if "var" not in handle or "_index" not in handle["var"].attrs:
            raise ValueError("Probe H5AD has no var/_index")
        var = handle["var"]
        index_name = var.attrs["_index"]
        if index_name not in var:
            raise ValueError(f"Probe var index dataset is absent: {index_name}")
        values = var[index_name]
        if values.ndim != 1 or len(values) > MAX_PROBE_GENES:
            raise ValueError("Probe var index is malformed or exceeds the 100,000-key cap")
        keys = [item.decode("utf-8") if isinstance(item, bytes) else str(item) for item in values[:]]
    if len(keys) != len(set(keys)):
        raise ValueError("Probe var index has duplicate keys")
    kh_keys = {key for key in keys if key.startswith("KH2012:")}
    malformed = sorted(key for key in kh_keys if not GENE_KEY.fullmatch(key))
    if malformed:
        raise ValueError(f"Unexpected KH2012 probe key: {malformed[0]}")
    return keys, kh_keys


def normalize(zip_path, kh_keys, output_fasta):
    """Stream one pinned ZIP member; map each protein model to its KH gene root."""
    normalized_digest = hashlib.sha256()
    source_member_digest = hashlib.sha256()
    model_ids = set()
    genes = Counter()
    plus_count = 0
    plus_records = 0
    protein_count = 0
    source_bytes = 0
    current_model = None
    current_length = 0
    current_has_plus = False
    temporary = output_fasta.with_name(output_fasta.name + ".tmp") if output_fasta else None

    def emit(line, output):
        normalized_digest.update(line)
        if output is not None:
            output.write(line)

    try:
        output = open(temporary, "wb") if temporary else None
        try:
            with zipfile.ZipFile(zip_path) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                if len(members) != 1 or members[0].filename != FASTA_MEMBER:
                    raise ValueError(f"Expected one ZIP member named {FASTA_MEMBER}")
                if members[0].file_size > MAX_FASTA_BYTES:
                    raise ValueError("Ghost FASTA exceeds the 64 MiB input cap")
                with archive.open(members[0]) as source:
                    for raw in source:
                        source_bytes += len(raw)
                        if source_bytes > MAX_FASTA_BYTES:
                            raise ValueError("Ghost FASTA exceeds the 64 MiB streaming cap")
                        source_member_digest.update(raw)
                        line = raw.strip()
                        if not line:
                            continue
                        if line.startswith(b">"):
                            if current_model is not None:
                                if not current_length:
                                    raise ValueError(f"Empty protein sequence: {current_model}")
                                plus_records += int(current_has_plus)
                            model_id = line[1:].decode("ascii")
                            match = MODEL_ID.fullmatch(model_id)
                            if not match:
                                raise ValueError(f"Unexpected Ghost protein header: {model_id[:120]}")
                            if model_id in model_ids:
                                raise ValueError(f"Duplicate Ghost protein model: {model_id}")
                            model_ids.add(model_id)
                            gene_key = "KH2012:" + match.group(1)
                            genes[gene_key] += 1
                            protein_count += 1
                            current_model = model_id
                            current_length = 0
                            current_has_plus = False
                            emit(
                                b">" + gene_key.encode("ascii") + b" protein=" + model_id.encode("ascii") + b"\n",
                                output,
                            )
                        else:
                            if current_model is None:
                                raise ValueError("Sequence precedes the first Ghost FASTA header")
                            try:
                                sequence = line.decode("ascii")
                            except UnicodeDecodeError as error:
                                raise ValueError(f"Non-ASCII protein sequence: {current_model}") from error
                            invalid = set(sequence) - PROTEIN_CHARS
                            if invalid:
                                raise ValueError(f"Unsupported amino-acid symbol(s) in {current_model}: {sorted(invalid)}")
                            count = sequence.count("+")
                            plus_count += count
                            current_has_plus |= count > 0
                            current_length += len(sequence)
                            emit(sequence.replace("+", "X").encode("ascii") + b"\n", output)
                    if current_model is not None:
                        if not current_length:
                            raise ValueError(f"Empty protein sequence: {current_model}")
                        plus_records += int(current_has_plus)
            if output is not None:
                output.flush()
                os.fsync(output.fileno())
        finally:
            if output is not None:
                output.close()
        if not protein_count:
            raise ValueError("Ghost FASTA contains no protein sequences")
        missing = kh_keys - genes.keys()
        if missing:
            raise ValueError(f"Ghost gene roots miss {len(missing)} KH2012 probe keys; first: {sorted(missing)[0]}")
        if output_fasta:
            os.replace(temporary, output_fasta)
    except Exception:
        if temporary:
            temporary.unlink(missing_ok=True)
        raise

    return {
        "source_member_sha256": source_member_digest.hexdigest(),
        "normalized_fasta_sha256": normalized_digest.hexdigest(),
        "protein_models": protein_count,
        "unique_gene_roots": len(genes),
        "gene_roots_with_multiple_models": sum(count > 1 for count in genes.values()),
        "maximum_models_per_gene": max(genes.values()),
        "plus_replaced_with_x": plus_count,
        "protein_models_with_plus": plus_records,
        "probe_kh_gene_keys_matched": len(kh_keys),
        "ghost_gene_roots_absent_from_probe": len(genes.keys() - kh_keys),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, required=True, help="Local Ghost KH2012 ZIP; never fetched by this script")
    parser.add_argument("--probe-h5ad", type=Path, required=True, help="Local Ciona probe H5AD; reads var keys only")
    parser.add_argument("--report", type=Path, required=True, help="Local JSON provenance/audit report")
    parser.add_argument("--output-fasta", type=Path, help="Optional local normalized FASTA; omit for audit only")
    parser.add_argument("--expected-zip-sha256", default=AUDITED_ZIP_SHA256, help="Explicit source pin for a different Ghost archive")
    args = parser.parse_args()

    if args.source_zip.stat().st_size > MAX_ZIP_BYTES:
        parser.error("Ghost ZIP exceeds the 16 MiB input cap")
    actual_sha = sha256_file(args.source_zip)
    if actual_sha != args.expected_zip_sha256:
        parser.error(f"Ghost ZIP SHA-256 mismatch: {actual_sha}")
    if args.output_fasta and args.output_fasta.exists():
        parser.error(f"Output FASTA exists: {args.output_fasta}")
    if args.report.exists():
        parser.error(f"Report exists: {args.report}")
    if args.output_fasta:
        if args.output_fasta.resolve() == args.report.resolve():
            parser.error("Output FASTA and report must be different files")
        if args.output_fasta.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            parser.error("Keep the Ghost-derived FASTA outside the repository")
    for path in (args.report, args.output_fasta):
        if path is not None and not path.parent.is_dir():
            parser.error(f"Output directory does not exist: {path.parent}")

    probe_keys, kh_keys = read_probe_keys(args.probe_h5ad)
    result = normalize(args.source_zip, kh_keys, args.output_fasta)
    report = {
        "schema_version": 1,
        "organism_key": "ciona_intestinalis",
        "source_page": SOURCE_PAGE,
        "source_archive": SOURCE_NAME,
        "source_archive_sha256": actual_sha,
        "source_zip_sha256": actual_sha,
        "source_member": FASTA_MEMBER,
        "probe_h5ad": str(args.probe_h5ad),
        "probe_var_keys": len(probe_keys),
        "probe_var_keys_sha256": digest_keys(probe_keys),
        "probe_kh_gene_keys": len(kh_keys),
        "probe_kh_gene_keys_sha256": digest_keys(kh_keys),
        "probe_non_kh_keys": sorted(set(probe_keys) - kh_keys),
        "header_rule": "KH.<scaffold>.<gene>.v<version>.<model> -> >KH2012:KH.<scaffold>.<gene> protein=<full-model-ID>",
        "sequence_rule": "Preserve uppercase amino acids; replace Ghost '+' with ESM unknown residue X",
        "output_fasta": str(args.output_fasta) if args.output_fasta else None,
        **result,
    }
    report_tmp = args.report.with_name(args.report.name + ".tmp")
    with open(report_tmp, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(report_tmp, args.report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
