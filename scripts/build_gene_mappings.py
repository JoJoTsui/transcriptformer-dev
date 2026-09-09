"""Build gene-ID mapping JSONs (old_id -> vocab_id) for scRNA-seq datasets
whose gene identifiers are not in the model vocabulary namespace.

Queries the mygene.info REST API (batch POST), filters returned ensembl.gene
IDs against the per-species model vocabulary
(checkpoints/tf_metazoa_finetuned/vocabs/{species}_gene.h5, dataset "keys"),
and writes one mapping JSON per dataset group into preprocess/gene_mappings/.

Resolution rules per input ID:
  - Prefer hits whose returned symbol exactly matches the query; fall back to
    all hits if none match exactly.
  - Collect distinct ensembl.gene IDs from those hits.
  - Exactly one in-vocab gene            -> mapped
  - More than one in-vocab gene          -> ambiguous (skipped)
  - Genes found but none in vocab        -> mapped-but-not-in-vocab (skipped)
  - No hits at all                       -> unmapped

API responses are cached in preprocess/gene_mappings/cache/ so re-runs do
not re-query.
"""

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import anndata as ad
import h5py
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_REPORT = REPO_ROOT / "logs" / "dataset_audit" / "report.json"
VOCAB_DIR = REPO_ROOT / "checkpoints" / "tf_metazoa_finetuned" / "vocabs"
OUT_DIR = REPO_ROOT / "preprocess" / "gene_mappings"
CACHE_DIR = OUT_DIR / "cache"

MYGENE_URL = "https://mygene.info/v3/query"
BATCH_SIZE = 1000


@dataclass
class Group:
    species: str
    taxid: str
    out_name: str
    # Returns (query_id, scopes) for a raw input ID.
    def query_spec(self, raw_id: str) -> tuple[str, str]:
        raise NotImplementedError
    # Splits a raw input ID into queryable aliases (default: itself).
    def aliases(self, raw_id: str) -> list[str]:
        return [raw_id]


@dataclass
class SymbolGroup(Group):
    scopes: str = "symbol,alias,other_names"

    def query_spec(self, raw_id):
        return raw_id, self.scopes


@dataclass
class MouseGroup(Group):
    def query_spec(self, raw_id):
        return raw_id, "symbol,alias,other_names"

    def aliases(self, raw_id):
        return [a for a in raw_id.split(";") if a]


@dataclass
class ZebrafishGroup(Group):
    def query_spec(self, raw_id):
        m = re.fullmatch(r"LOC(\d+)", raw_id)
        if m:
            return m.group(1), "entrezgene,retired"
        return raw_id, "symbol,alias,other_names"


GROUPS = {
    "human": SymbolGroup(
        species="homo_sapiens", taxid="9606", out_name="human_symbol_to_ensg.json"
    ),
    "mouse": MouseGroup(
        species="mus_musculus", taxid="10090", out_name="mouse_symbol_to_ensmusg.json"
    ),
    "zebrafish": ZebrafishGroup(
        species="danio_rerio", taxid="7955", out_name="zebrafish_loc_to_ensdarg.json"
    ),
    "drosophila": SymbolGroup(
        species="drosophila_melanogaster",
        taxid="7227",
        out_name="drosophila_symbol_to_fbgn.json",
        scopes="symbol,alias",
    ),
    "celegans": SymbolGroup(
        species="caenorhabditis_elegans",
        taxid="6239",
        out_name="celegans_name_to_wbgene.json",
        scopes="other_names,name,symbol,alias",
    ),
}


def load_vocab(species: str) -> set[str]:
    with h5py.File(VOCAB_DIR / f"{species}_gene.h5") as f:
        return {k.decode() if isinstance(k, bytes) else str(k) for k in f["keys"][:]}


def zero_overlap_files(species: str) -> list[str]:
    report = json.loads(AUDIT_REPORT.read_text())
    return [
        e["file"]
        for e in report.get(species, [])
        if e.get("vocab_overlap_frac") == 0.0 and e.get("n_vars")
    ]


def read_var_names(path: str) -> list[str]:
    a = ad.read_h5ad(path, backed="r")
    try:
        return [str(x) for x in a.var_names]
    finally:
        a.file.close()


# ---------------------------------------------------------------- mygene API


class MyGeneClient:
    """Batch-query mygene.info with a per-group on-disk cache.

    Cache layout: {raw_alias: {"hits": [{"genes": [...], "symbol": str}]}}.
    Missing / not-found queries are cached as {"hits": []}.
    """

    def __init__(self, group: Group):
        self.group = group
        self.cache_path = CACHE_DIR / f"{group.species}.json"
        if self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text())
        else:
            self.cache = {}

    def _save(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache))
        tmp.replace(self.cache_path)

    @staticmethod
    def _trim(hits):
        out = []
        for h in hits:
            ens = h.get("ensembl")
            if ens is None:
                continue
            entries = ens if isinstance(ens, list) else [ens]
            genes = [e["gene"] for e in entries if "gene" in e]
            if genes:
                out.append({"genes": genes, "symbol": h.get("symbol", "")})
        return out

    def _post(self, ids: list[str], scopes: str) -> list[dict]:
        data = {
            "q": ",".join(ids),
            "scopes": scopes,
            "fields": "ensembl.gene,symbol",
            "species": self.group.taxid,
        }
        delay = 2.0
        for attempt in range(5):
            try:
                r = requests.post(MYGENE_URL, data=data, timeout=120)
                if r.status_code == 200:
                    return r.json()
                if 400 <= r.status_code < 500:
                    # Client error (e.g. an ID mygene's parser rejects) — retrying
                    # won't help; let the caller bisect.
                    raise RuntimeError(f"HTTP {r.status_code}")
                print(f"    HTTP {r.status_code}, retrying in {delay:.0f}s")
            except requests.RequestException as e:
                print(f"    request error: {e}, retrying in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
        raise RuntimeError(f"mygene query failed after retries ({len(ids)} ids)")

    def _post_resilient(self, ids: list[str], scopes: str) -> list[dict]:
        """POST a batch; on persistent failure bisect to isolate bad IDs.

        Single IDs that still fail (e.g. characters mygene's query parser
        rejects) are returned as synthetic not-found entries.
        """
        try:
            return self._post(ids, scopes)
        except RuntimeError:
            if len(ids) == 1:
                print(f"    giving up on unqueryable ID: {ids[0]!r}")
                return [{"query": ids[0], "notfound": True}]
            mid = len(ids) // 2
            return self._post_resilient(ids[:mid], scopes) + self._post_resilient(
                ids[mid:], scopes
            )

    def fetch(self, aliases: list[str]):
        """Ensure every raw alias has its hits in the cache (keyed by raw alias)."""
        todo = [a for a in dict.fromkeys(aliases) if a not in self.cache]
        if not todo:
            return
        # Group aliases by scopes so zebrafish LOC vs symbol queries stay separate.
        by_scopes: dict[str, list[tuple[str, str]]] = {}
        for a in todo:
            q, scopes = self.group.query_spec(a)
            by_scopes.setdefault(scopes, []).append((a, q))
        for scopes, pairs in by_scopes.items():
            for i in range(0, len(pairs), BATCH_SIZE):
                chunk = pairs[i : i + BATCH_SIZE]
                results = self._post_resilient([q for _, q in chunk], scopes)
                # Merge duplicate-query responses (mygene emits one entry per hit).
                merged: dict[str, list] = {}
                for h in results:
                    q = h["query"]
                    merged.setdefault(q, [])
                    if not h.get("notfound"):
                        merged[q].extend(self._trim([h]))
                for a, q in chunk:
                    self.cache[a] = {"hits": merged.get(q, [])}
                self._save()
                print(
                    f"    cached {min(i + BATCH_SIZE, len(pairs))}/{len(pairs)}"
                    f" queries (scopes={scopes})"
                )


# ---------------------------------------------------------------- resolution


def resolve_hits(query: str, hits: list[dict], vocab: set[str]) -> tuple[str, str | None]:
    """Return (status, gene). Status: mapped / ambiguous / not_in_vocab / unmapped."""
    if not hits:
        return "unmapped", None
    exact = [h for h in hits if h["symbol"] == query]
    pool = exact or hits
    genes: list[str] = []
    for h in pool:
        for g in h["genes"]:
            if g not in genes:
                genes.append(g)
    in_vocab = [g for g in genes if g in vocab]
    if len(in_vocab) == 1:
        return "mapped", in_vocab[0]
    if len(in_vocab) > 1:
        return "ambiguous", None
    return "not_in_vocab", None


def resolve_id(group: Group, client: MyGeneClient, raw_id: str, vocab: set[str]):
    """Resolve one raw input ID (possibly multi-alias). Returns (status, gene, detail)."""
    aliases = group.aliases(raw_id)
    mapped_genes: list[str] = []
    any_hits = False
    any_ambiguous = False
    for a in aliases:
        status, gene = resolve_hits(a, client.cache.get(a, {}).get("hits", []), vocab)
        if status == "mapped":
            if gene not in mapped_genes:
                mapped_genes.append(gene)
        elif status == "ambiguous":
            any_ambiguous = True
        if status != "unmapped":
            any_hits = True
    if len(mapped_genes) == 1:
        return "mapped", mapped_genes[0], {"n_aliases": len(aliases)}
    if len(mapped_genes) > 1:
        return "ambiguous", None, {"n_aliases": len(aliases), "genes": mapped_genes}
    if any_ambiguous:
        return "ambiguous", None, {"n_aliases": len(aliases)}
    if any_hits:
        return "not_in_vocab", None, {"n_aliases": len(aliases)}
    return "unmapped", None, {"n_aliases": len(aliases)}


# ---------------------------------------------------------------- main


def build_group(name: str, group: Group, report_lines: list[str]) -> dict:
    print(f"\n=== {name} ({group.species}) ===")
    vocab = load_vocab(group.species)
    files = zero_overlap_files(group.species)
    print(f"  vocab keys: {len(vocab)}, zero-overlap files: {len(files)}")

    # Extract unique IDs per file (backed mode; never touch .X).
    per_file_ids: dict[str, list[str]] = {}
    per_file_dupes: dict[str, int] = {}
    for path in files:
        names = read_var_names(path)
        uniq = list(dict.fromkeys(names))
        per_file_ids[path] = uniq
        per_file_dupes[path] = len(names) - len(uniq)
        print(f"  {Path(path).name}: {len(names)} vars, {len(uniq)} unique")

    # Fetch all needed query IDs.
    client = MyGeneClient(group)
    all_aliases = []
    for ids in per_file_ids.values():
        for raw in ids:
            all_aliases.extend(group.aliases(raw))
    print(f"  querying mygene for {len(set(all_aliases))} unique query IDs...")
    client.fetch(all_aliases)

    # Resolve per file and build the union mapping.
    mapping: dict[str, str] = {}
    group_counts = {"mapped": 0, "ambiguous": 0, "not_in_vocab": 0, "unmapped": 0}
    report_lines.append(f"## {name} ({group.species} -> {group.out_name})\n")
    report_lines.append(
        "| file | unique IDs | mapped in-vocab | mapped not-in-vocab | ambiguous | unmapped | dup IDs in index | coverage |"
    )
    report_lines.append("|---|---|---|---|---|---|---|---|")
    file_notes: list[str] = []
    for path, uniq in per_file_ids.items():
        counts = {"mapped": 0, "ambiguous": 0, "not_in_vocab": 0, "unmapped": 0}
        n_multi = n_multi_mapped = 0
        for raw in uniq:
            status, gene, _ = resolve_id(group, client, raw, vocab)
            counts[status] += 1
            if status == "mapped":
                mapping[raw] = gene
            if len(group.aliases(raw)) > 1:
                n_multi += 1
                n_multi_mapped += status == "mapped"
        cov = counts["mapped"] / len(uniq) if uniq else 0.0
        for k in group_counts:
            group_counts[k] += counts[k]
        report_lines.append(
            f"| {Path(path).name} | {len(uniq)} | {counts['mapped']} "
            f"| {counts['not_in_vocab']} | {counts['ambiguous']} "
            f"| {counts['unmapped']} | {per_file_dupes[path]} | {cov:.3f} |"
        )
        if n_multi:
            file_notes.append(
                f"- `{Path(path).name}`: {n_multi} ';'-joined alias IDs, "
                f"{n_multi_mapped} resolved via at least one alias."
            )
    report_lines.append("")
    report_lines.extend(file_notes)
    if file_notes:
        report_lines.append("")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / group.out_name
    out_path.write_text(json.dumps(mapping, indent=1, sort_keys=True))
    print(f"  wrote {out_path} ({len(mapping)} mappings)")
    print(f"  counts: {group_counts}")
    return mapping


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--groups",
        nargs="*",
        default=list(GROUPS),
        choices=list(GROUPS),
        help="dataset groups to build (default: all)",
    )
    args = ap.parse_args()

    report_lines = [
        "# Gene-ID mapping report",
        "",
        "Built by `scripts/build_gene_mappings.py` via the mygene.info API.",
        "Status columns count unique input IDs per file: `mapped in-vocab` is the",
        "number written to the mapping JSON; `mapped not-in-vocab` resolved to an",
        "ensembl gene absent from the model vocabulary; `ambiguous` had >1 in-vocab",
        "candidate and was skipped; `unmapped` had no mygene hit. `dup IDs in index`",
        "counts repeated index entries (mapping collapses them, by design).",
        "",
        "Notes:",
        "- Human: the audit's apparent duplicate index symbols (e.g. `RP11-34P13`",
        "  twice) are a display truncation — the real index holds versioned names",
        "  (`RP11-34P13.7`, `.8`, ...), so every file's index is fully unique.",
        "  Unmapped human IDs are mostly clone-based lncRNA names (`RP11-...`,",
        "  `AL627309.1`) that mygene does not index; `not-in-vocab` reflects that",
        "  the model vocabulary (23,823 keys) is a subset of the full annotation.",
        "- Zebrafish: high ambiguity is real — many `LOC...` records carry two",
        "  Ensembl genes (teleost whole-genome duplicates), both in the vocab.",
        "- Drosophila: most unmapped IDs are non-gene features (`FBti...`",
        "  transposons, `FBtr...` fragments); most `not-in-vocab` hits are ncRNAs",
        "  (`sisRNA:`, `lncRNA:`, `mir-...`) absent from the 13,986-key vocab.",
        "",
    ]
    for name in args.groups:
        build_group(name, GROUPS[name], report_lines)

    report_path = OUT_DIR / "REPORT.md"
    report_path.write_text("\n".join(report_lines) + "\n")
    print(f"\nwrote {report_path}")


if __name__ == "__main__":
    main()
