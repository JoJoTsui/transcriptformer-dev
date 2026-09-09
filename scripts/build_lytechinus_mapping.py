#!/usr/bin/env python3
"""Build the Lytechinus variegatus gene-ID mapping for TranscriptFormer.

Maps the custom MAKER gene-model IDs (``L_var_XXXXX``, Davidson et al. 2020,
Genome Biol Evol 12(7):evaa101) used as the var index of the Foster et al. 2021
scRNA-seq dataset (GEO GSE184538) to the NCBI RefSeq LOC gene IDs of assembly
GCF_018143015.1 (Lvar_3.0, annotation release 100) used by the model vocab.

Primary method — genomic coordinate overlap. Both annotations are on the same
Lvar_3.0 assembly, so MAKER gene intervals (evaa101 supplementary data 1,
``L_var_annotations.gff``) are joined to RefSeq gene intervals
(``refseq_Lvar3.0.gff.gz``) by coordinate overlap. Seqid naming is reconciled
via the GCF assembly report (``chr1`` -> ``NC_054740.1``, etc.). For each MAKER
gene the RefSeq gene with the largest overlap on the same seqid and strand is
assigned; exact ties between distinct RefSeq genes are recorded as ambiguous
and skipped. Only mappings whose LOC id is in the model vocab are kept.

Cross-check — S. purpuratus ortholog names. The var index carries appended
S. purpuratus ortholog names (``L_var_00004:Sp-RtL_62``); the independent
ortholog-name chain (Echinobase gene-page synonyms + NCBI gene_info ->
Echinobase SpurLvar orthology -> Lv GeneID) is run for comparison and the
concordance between the two methods is reported. This route was the fallback
used before the MAKER GFF became available.

Outputs (under preprocess/gene_mappings/):
  lytechinus_lvar_to_loc.json       keyed by the exact var-index strings
  lytechinus_lvar_to_loc_base.json  keyed by bare L_var_XXXXX IDs
  REPORT_lytechinus.md is written separately (see repo).

Downloaded sources are cached under preprocess/gene_mappings/cache/.
"""

import argparse
import gzip
import json
import os
import re
import sys
import urllib.request
from bisect import bisect_right
from collections import defaultdict

import h5py

CACHE_URLS = {
    "refseq_Lvar3.0.gff.gz": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/018/143/015/GCF_018143015.1_Lvar_3.0/GCF_018143015.1_Lvar_3.0_genomic.gff.gz",
    "GCF_assembly_report.txt": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/018/143/015/GCF_018143015.1_Lvar_3.0/GCF_018143015.1_Lvar_3.0_assembly_report.txt",
    "GenePageGeneralInfo_AllGenes.txt": "https://download.echinobase.org/echinobase/GenePageReports/GenePageGeneralInfo_AllGenes.txt",
    "5ToolsLvarSpurp.tsv": "https://download.echinobase.org/echinobase/Orthology/SpurLvar/5ToolsLvarSpurp.tsv",
    "SpurLvar_FO.out": "https://download.echinobase.org/echinobase/Orthology/SpurLvar/FO.out",
    "SpurLvar_IP.out": "https://download.echinobase.org/echinobase/Orthology/SpurLvar/IP.out",
    "SpurLvar_OF.out": "https://download.echinobase.org/echinobase/Orthology/SpurLvar/OF.out",
    "SpurLvar_PO.out": "https://download.echinobase.org/echinobase/Orthology/SpurLvar/PO.out",
    "SpurLvar_SO.out": "https://download.echinobase.org/echinobase/Orthology/SpurLvar/SO.out",
    "All_Invertebrates.gene_info.gz": "https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Invertebrates/All_Invertebrates.gene_info.gz",
}

MAKER_GFF = os.path.join("Supplementary Data 1", "L_var_annotations.gff")
SP_TAXID = "7668"  # Strongylocentrotus purpuratus
ORTHO_TOOL_FILES = [
    "SpurLvar_FO.out",
    "SpurLvar_IP.out",
    "SpurLvar_OF.out",
    "SpurLvar_PO.out",
    "SpurLvar_SO.out",
]


def ensure_cache(cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    missing = []
    for fname, url in CACHE_URLS.items():
        if not os.path.exists(os.path.join(cache_dir, fname)):
            missing.append((fname, url))
    if not os.path.exists(os.path.join(cache_dir, MAKER_GFF)):
        sys.exit(
            f"MAKER GFF not found at {os.path.join(cache_dir, MAKER_GFF)} — "
            "download evaa101 supplementary data 1 and extract it there."
        )
    for fname, url in missing:
        print(f"downloading {fname} ...", flush=True)
        urllib.request.urlretrieve(url, os.path.join(cache_dir, fname))


def load_vocab_keys(vocab_h5):
    with h5py.File(vocab_h5, "r") as f:
        return set(k.decode() if isinstance(k, bytes) else k for k in f["keys"][:])


def load_var_index(h5ad_path):
    import anndata as ad

    a = ad.read_h5ad(h5ad_path, backed="r")
    return [str(v) for v in a.var.index]


def parse_attrs(field):
    attrs = {}
    for kv in field.split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            attrs[k] = v
    return attrs


def load_maker_genes(path):
    """MAKER GFF -> {L_var id: (seqid, start, end, strand)} (1-based, inclusive)."""
    genes = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 9 or c[2] != "gene":
                continue
            gid = parse_attrs(c[8]).get("ID", "")
            if not gid.startswith("L_var_"):
                continue
            genes[gid] = (c[0], int(c[3]), int(c[4]), c[6])
    print(f"MAKER genes: {len(genes)}")
    return genes


def load_refseq_genes(path):
    """RefSeq GFF -> per-seqid list of (start, end, strand, name, gene_id)."""
    per_seqid = defaultdict(list)
    with gzip.open(path, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 9 or c[2] not in ("gene", "pseudogene"):
                continue
            attrs = parse_attrs(c[8])
            name = attrs.get("gene") or attrs.get("Name", "")
            gid = ""
            for x in attrs.get("Dbxref", "").split(","):
                if x.startswith("GeneID:"):
                    gid = x.split(":", 1)[1]
            if not name and not gid:
                continue
            per_seqid[c[0]].append((int(c[3]), int(c[4]), c[6], name, gid))
    n = sum(len(v) for v in per_seqid.values())
    print(f"RefSeq genes: {n} on {len(per_seqid)} seqids")
    return per_seqid


def load_seqid_map(cache_dir):
    """submitter seqid -> RefSeq accession, from the GCF assembly report."""
    m = {}
    with open(os.path.join(cache_dir, "GCF_assembly_report.txt")) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) >= 7 and c[6] != "na":
                m[c[0]] = c[6]
    print(f"seqid map: {len(m)} submitter names -> RefSeq accessions")
    return m


def coordinate_map(maker_genes, refseq_per_seqid, seqid_map, vocab):
    """Assign each MAKER gene the best-overlapping same-strand RefSeq gene."""
    index = {}
    for acc, rows in refseq_per_seqid.items():
        rows = sorted(rows)
        index[acc] = (rows, [r[0] for r in rows])

    mapping = {}  # L_var id -> (vocab key, overlap, maker_len, ref_len, recip)
    stats = defaultdict(int)
    for lvar, (seqid, s, e, strand) in maker_genes.items():
        acc = seqid_map.get(seqid)
        if acc is None or acc not in index:
            stats["unmapped_seqid_not_in_refseq"] += 1
            continue
        rows, starts = index[acc]
        # candidate window: rows with start <= e; overlap requires end >= s
        cands = []
        i = bisect_right(starts, e) - 1
        while i >= 0 and rows[i][1] >= s:
            r = rows[i]
            ov = min(e, r[1]) - max(s, r[0]) + 1
            if ov > 0:
                cands.append((ov, r))
            i -= 1
        if not cands:
            stats["unmapped_no_overlap"] += 1
            continue
        same = [c for c in cands if c[1][2] == strand]
        if not same:
            stats["unmapped_opposite_strand_only"] += 1
            continue
        same.sort(key=lambda c: -c[0])
        best_ov, best = same[0]
        if len(same) > 1 and same[1][0] == best_ov and same[1][1][3] != best[3]:
            stats["ambiguous_tie"] += 1
            continue
        mlen = e - s + 1
        rlen = best[1] - best[0] + 1
        recip = min(best_ov / mlen, best_ov / rlen)
        name, gid = best[3], best[4]
        key = None
        for cand in (name, f"GeneID_{gid}" if gid else None):
            if cand and cand in vocab:
                key = cand
                break
        if key is None:
            stats["mapped_not_in_vocab"] += 1
            continue
        mapping[lvar] = (key, best_ov, mlen, rlen, recip)
        stats["mapped_in_vocab_recip50" if recip >= 0.5 else "mapped_in_vocab_partial"] += 1
    return mapping, stats


def load_sp_name_to_geneid(cache_dir, extra_genepage_files=()):
    """S. purpuratus name -> GeneID, from NCBI gene_info and Echinobase gene pages.

    Names that resolve to more than one GeneID are dropped as ambiguous.
    """
    name2gid = {}
    ambiguous = set()

    def add(name, gid):
        name = name.strip()
        if not name:
            return
        if name in name2gid and name2gid[name] != gid:
            ambiguous.add(name)
            name2gid.pop(name, None)
        elif name not in ambiguous:
            name2gid[name] = gid

    gi_path = os.path.join(cache_dir, "All_Invertebrates.gene_info.gz")
    symbol2gid = {}
    sp_gids = set()
    with gzip.open(gi_path, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if c[0] != SP_TAXID:
                continue
            gid, symbol, synonyms, other = c[1], c[2], c[4], c[13]
            sp_gids.add(gid)
            symbol2gid[symbol] = gid
            add(symbol, gid)
            if synonyms != "-":
                for n in synonyms.split("|"):
                    add(n, gid)
            if other != "-":
                for n in other.split("|"):
                    add(n, gid)

    loc_re = re.compile(r"^LOC(\d+)$")
    for gp in ["GenePageGeneralInfo_AllGenes.txt", *extra_genepage_files]:
        path = os.path.join(cache_dir, gp)
        if not os.path.exists(path):
            continue
        with open(path) as fh:
            fh.readline()
            for line in fh:
                c = line.rstrip("\n").split("\t")
                if len(c) < 5:
                    continue
                symbol = c[1]
                m = loc_re.match(symbol)
                gid = m.group(1) if m else symbol2gid.get(symbol)
                if gid is None or gid not in sp_gids:
                    continue
                add(symbol, gid)
                if c[4]:
                    for n in c[4].split("|"):
                        add(n, gid)

    print(
        f"Sp name->GeneID: {len(name2gid)} unique names "
        f"({len(ambiguous)} ambiguous names dropped)"
    )
    return name2gid


def load_sp_to_lv_orthologs(cache_dir):
    """Sp GeneID -> Lv GeneID (consensus >=3 tools, else single candidate)."""
    consensus = {}
    with open(os.path.join(cache_dir, "5ToolsLvarSpurp.tsv")) as fh:
        fh.readline()
        for line in fh:
            c = line.rstrip("\n").split("\t")
            if len(c) < 8:
                continue
            if int(c[7]) >= 3:
                consensus[c[1]] = c[0]

    cand = defaultdict(set)
    for fname in ORTHO_TOOL_FILES:
        with open(os.path.join(cache_dir, fname)) as fh:
            fh.readline()
            for line in fh:
                c = line.rstrip("\n").split("\t")
                if len(c) != 2:
                    continue
                lvs = [x if len(x) <= 9 else x[:9] for x in c[0].split(",")]
                for sp in c[1].split(","):
                    cand[sp].update(lvs)

    sp2lv = dict(consensus)
    for sp, s in cand.items():
        if sp not in sp2lv and len(s) == 1:
            sp2lv[sp] = next(iter(s))
    print(f"Sp->Lv orthologs: {len(consensus)} consensus, {len(sp2lv)} total")
    return sp2lv


def ortholog_map(var_index, name2gid, sp2lv, vocab):
    """Cross-check mapping via the var-index S. purpuratus ortholog names."""
    def lv_vocab_key(gid):
        for k in (f"LOC{gid}", f"GeneID_{gid}"):
            if k in vocab:
                return k
        return None

    out = {}
    for key in var_index:
        _, _, suffix = key.partition(":")
        if suffix == "none":
            continue
        gid = None
        for v in (suffix, suffix[3:] if suffix.startswith("Sp-") else None,
                  suffix.replace("_", " ")):
            if v and v in name2gid:
                gid = name2gid[v]
                break
        if gid is None:
            continue
        lv = sp2lv.get(gid)
        if lv is None:
            continue
        k = lv_vocab_key(lv)
        if k:
            out[key] = k
    print(f"ortholog-route mapped in vocab: {len(out)}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--h5ad", required=True, help="dataset h5ad (var index to map)")
    ap.add_argument("--vocab", required=True, help="model vocab HDF5 with 'keys'")
    ap.add_argument("--cache-dir", default="preprocess/gene_mappings/cache")
    ap.add_argument("--out-dir", default="preprocess/gene_mappings")
    ap.add_argument(
        "--extra-genepage",
        nargs="*",
        default=["GenePageGeneralInfo_AllGenes_2021.txt"],
        help="extra archived Echinobase gene-page reports in the cache dir",
    )
    args = ap.parse_args()

    ensure_cache(args.cache_dir)
    vocab = load_vocab_keys(args.vocab)
    var_index = load_var_index(args.h5ad)

    # ---- primary: coordinate overlap ----
    maker_genes = load_maker_genes(os.path.join(args.cache_dir, MAKER_GFF))
    refseq = load_refseq_genes(os.path.join(args.cache_dir, "refseq_Lvar3.0.gff.gz"))
    seqid_map = load_seqid_map(args.cache_dir)
    coord, stats = coordinate_map(maker_genes, refseq, seqid_map, vocab)

    var_bases = [k.partition(":")[0] for k in var_index]
    missing_in_gff = sum(1 for b in var_bases if b not in maker_genes)
    full_mapping = {}
    for key, base in zip(var_index, var_bases):
        if base in coord:
            full_mapping[key] = coord[base][0]

    # ---- cross-check: ortholog names ----
    name2gid = load_sp_name_to_geneid(args.cache_dir, args.extra_genepage)
    sp2lv = load_sp_to_lv_orthologs(args.cache_dir)
    ortho = ortholog_map(var_index, name2gid, sp2lv, vocab)

    both = set(full_mapping) & set(ortho)
    agree = sum(1 for k in both if full_mapping[k] == ortho[k])
    print(f"\ncross-check: both methods map {len(both)} var IDs; "
          f"agree {agree} ({100 * agree / max(len(both), 1):.2f}%), "
          f"disagree {len(both) - agree}")
    coord_only = set(full_mapping) - set(ortho)
    ortho_only = set(ortho) - set(full_mapping)
    print(f"  coordinate-only: {len(coord_only)}, ortholog-only: {len(ortho_only)}")

    base_mapping = {k.partition(":")[0]: v for k, v in full_mapping.items()}
    os.makedirs(args.out_dir, exist_ok=True)
    out_full = os.path.join(args.out_dir, "lytechinus_lvar_to_loc.json")
    out_base = os.path.join(args.out_dir, "lytechinus_lvar_to_loc_base.json")
    with open(out_full, "w") as fh:
        json.dump(dict(sorted(full_mapping.items())), fh, indent=1)
    with open(out_base, "w") as fh:
        json.dump(dict(sorted(base_mapping.items())), fh, indent=1)

    total = len(var_index)
    n_mapped = stats["mapped_in_vocab_recip50"] + stats["mapped_in_vocab_partial"]
    print(f"\ntotal var IDs: {total}; MAKER genes in GFF: {len(maker_genes)}; "
          f"var bases absent from MAKER GFF: {missing_in_gff}")
    for cat in sorted(stats):
        print(f"  {cat}: {stats[cat]} ({100 * stats[cat] / total:.2f}%)")
    print(f"coverage (mapped_in_vocab / total var IDs): {n_mapped / total:.4f}")
    # overlap-quality summary for mapped genes
    recips = sorted(v[4] for v in coord.values())
    if recips:
        med = recips[len(recips) // 2]
        print(f"reciprocal-overlap of mapped genes: median {med:.3f}, "
              f"min {recips[0]:.3f}; <0.5: {sum(1 for r in recips if r < 0.5)}")
    print(f"wrote {out_full} ({len(full_mapping)} keys)")
    print(f"wrote {out_base} ({len(base_mapping)} keys)")


if __name__ == "__main__":
    sys.exit(main())
