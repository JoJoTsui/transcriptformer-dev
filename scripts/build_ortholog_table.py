#!/usr/bin/env python3
"""Build the cross-species 1:1 ortholog table for the multi-species embryogenesis finetune.

Frozen design: docs/perturbation-and-baseline-design.md section 6 (S6) and
docs/finetune-major-issues.md item 4.3. Sources and rules:

  - Orthology calls come from Ensembl Compara. The acquisition interface is the Compara
    gene-tree homology TSV dumps (one bulk download per genome; <= 20 files for all 14
    species) because BioMart was persistently unavailable at build time (see the manifest's
    ``acquisition`` block for the probed status codes). The dumps are Ensembl Compara's own
    export of the same homology table BioMart serves; the Ensembl release is pinned
    (default release-110, matching preprocess/fasta_manifest_pep.json) and every file's
    MD5 is checked against its published MD5SUM. Only ``ortholog_one2one`` homologies with
    orthology confidence (``is_high_confidence``) = 1 are kept.
  - Many-to-one and many-to-many orthologs are dropped, never collapsed. Any gene that
    still ends up with more than one retained partner (e.g. after version stripping) is
    dropped together with its pairs. Xenopus laevis L/S homeolog pairs are out of scope
    (we use X. tropicalis). Homologies are read within a single Compara gene-tree
    collection only (Ensembl "default" for vertebrates + ciona + fly + worm; Ensembl
    Metazoa for the urchins); cross-collection species pairs have no Compara homologies
    and are recorded as gaps, never substituted.
  - Urchin bridge fallback: when Compara coverage for Lytechinus variegatus is thin for a
    pair (fewer than --bridge-threshold direct 1:1 pairs), pairs are bridged through
    Strongylocentrotus purpuratus using the EchinoBase 5-tool-consensus orthology cached by
    scripts/build_lytechinus_mapping.py (preprocess/gene_mappings/cache/5ToolsLvarSpurp.tsv,
    consensus of >= 3 tools, strict 1:1) and then Compara from S. purpuratus outward. The
    manifest records when the bridge was used.
  - Cross-check: 200 random retained pairs (seeded) are validated against OrthoDB
    (https://www.orthodb.org; shared orthogroup levels holding exactly one gene per species
    for the pair) and, for Alliance of Genome Resources member species
    (human/mouse/zebrafish/fly/worm/xenopus), against Alliance DIOPT-integrated calls
    (https://www.alliancegenome.org). Concordance is reported; pairs a source disagrees
    with are dropped. A source "disagrees" when it resolves both genes and does not support
    the pairing; a source that cannot resolve a gene - or is unavailable at build time - is
    "unavailable" and the pair is kept, reported as unverified (never fabricated).
  - Coverage floors per species pair (design section 6, rule 4): (a) >= 60% of each side's
    compared genes have 1:1 orthologs across the pair, (b) the genome-wide 1:1 set is
    >= 5,000 genes. Every pair failing either floor is flagged so later claims on it are
    downgraded to single-species findings. "Compared genes" is the species' model vocabulary
    (training species) or its Ensembl protein-coding gene count from the pinned release's
    GTF (zero-shot probe species); the denominator source is recorded per species.
  - Version suffixes are stripped only from Ensembl/FBgn/WBGene-style stable IDs
    (docs/finetune-data-requirements.md section 3; the regex is kept in sync with
    src/transcriptformer/finetune/prepare.py). Dots that are part of an identifier
    (``2L52.1``, ``acy3.1``) are never touched. Urchin LOC<n>/GeneID_<n> spellings name the
    same NCBI gene and are canonicalized to GeneID_<n>.
  - The Ensembl release and data snapshot date are pinned in the output manifest.

Raw downloads/HTTP responses are cached under --cache-dir (default cache/orthologs, git
ignored) so re-runs resume instead of refetching. All requests are throttled per host and
honor Retry-After. Outputs:

  preprocess/orthologs/ortholog_pairs.tsv.gz    species_a gene_a species_b gene_b (1:1 pairs)
  preprocess/orthologs/manifest.json            releases, snapshot date, per-pair counts/floors
  logs/dataset_audit/orthologs/*.json           availability, coverage and cross-check evidence

Run: .venv/bin/python scripts/build_ortholog_table.py
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import h5py
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
VOCAB_DIR = REPO_ROOT / "checkpoints" / "tf_metazoa_finetuned" / "vocabs"
ECHEINOBASE_CONSENSUS = REPO_ROOT / "preprocess" / "gene_mappings" / "cache" / "5ToolsLvarSpurp.tsv"

MAIN_FTP = "https://ftp.ensembl.org/pub"
METAZOA_FTP = "https://ftp.ebi.ac.uk/ensemblgenomes/pub/metazoa"
ENSEMBL_REST_DATA = "https://rest.ensembl.org/info/data"
BIOMART_PROBE_URL = "https://www.ensembl.org/biomart/martservice"
ORTHODB_API = "https://data.orthodb.org/v12"
ALLIANCE_API = "https://www.alliancegenome.org/api"
USER_AGENT = "transcriptformer-ortholog-builder/1.0 (czi-ai/transcriptformer)"

HOMOLOGY_FIELDS = [
    "gene_stable_id",
    "protein_stable_id",
    "species",
    "identity",
    "homology_type",
    "homology_gene_stable_id",
    "homology_protein_stable_id",
    "homology_species",
    "homology_identity",
    "dn",
    "ds",
    "goc_score",
    "wga_coverage",
    "is_high_confidence",
    "homology_id",
]

# Kept in sync with src/transcriptformer/finetune/prepare.py (docs/finetune-data-requirements.md section 3):
# only stable database IDs carry a true version suffix. WormBase sequence names (2L52.1,
# AC3.12) and zebrafish paralog symbols (acy3.1) keep their dots.
VERSIONED_STABLE_ID_RE = re.compile(r"^(ENS[A-Z]*\d+|FBgn\d+|WBGene\d+)\.\d+$")

# Species whose gene-level cross-species claims the Alliance of Genome Resources serves
# with DIOPT-integrated calls (docs/perturbation-and-baseline-design.md section 6).
ALLIANCE_SPECIES = {
    "homo_sapiens",
    "mus_musculus",
    "danio_rerio",
    "drosophila_melanogaster",
    "caenorhabditis_elegans",
    "xenopus_tropicalis",
}

# NCBI GeneID identity aliases: RefSeq LOC tags and GeneID_* keys name the same gene
# (precedent: scripts/build_lytechinus_mapping.py maps to either vocab key interchangeably).
_GENEID_ALIAS_RE = re.compile(r"^(?:LOC|GeneID_)(\d+)$")

TRAINING_SPECIES = [
    "caenorhabditis_elegans",
    "danio_rerio",
    "drosophila_melanogaster",
    "gallus_gallus",
    "homo_sapiens",
    "lytechinus_variegatus",
    "mus_musculus",
    "oryctolagus_cuniculus",
]
PROBE_SPECIES = [
    "macaca_fascicularis",
    "sus_scrofa",
    "cavia_porcellus",
    "xenopus_tropicalis",
    "ciona_intestinalis",
    "branchiostoma_floridae",
]
SPECIES_ORDER = TRAINING_SPECIES + PROBE_SPECIES


@dataclass(frozen=True)
class Species:
    name: str
    taxid: str
    genomes: tuple  # (Ensembl genome dir or "", Ensembl Metazoa genome dir or "")
    has_vocab: bool  # model vocabulary at VOCAB_DIR / f"{name}_gene.h5"
    role: str = "training"

    def genome_for(self, collection: str) -> str:
        return self.genomes[0] if collection == "main" else self.genomes[1]

    def marts(self) -> list[str]:
        return [m for m, d in zip(("main", "metazoa"), self.genomes) if d]

    def datasets_any(self) -> bool:
        return any(self.genomes)


def _sp(name, taxid, main_genome, metazoa_genome, has_vocab, role):
    return Species(name=name, taxid=taxid, genomes=(main_genome, metazoa_genome), has_vocab=has_vocab, role=role)


SPECIES = {
    s.name: s
    for s in [
        _sp("caenorhabditis_elegans", "6239", "caenorhabditis_elegans", "caenorhabditis_elegans", True, "training"),
        _sp("danio_rerio", "7955", "danio_rerio", "", True, "training"),
        _sp("drosophila_melanogaster", "7227", "drosophila_melanogaster", "drosophila_melanogaster", True, "training"),
        _sp("gallus_gallus", "9031", "gallus_gallus", "", True, "training"),
        _sp("homo_sapiens", "9606", "homo_sapiens", "", True, "training"),
        _sp("lytechinus_variegatus", "7665", "", "lytechinus_variegatus_gca018143015v1", True, "training"),
        _sp("mus_musculus", "10090", "mus_musculus", "", True, "training"),
        _sp("oryctolagus_cuniculus", "9986", "oryctolagus_cuniculus", "", True, "training"),
        _sp("macaca_fascicularis", "9541", "macaca_fascicularis", "", False, "probe"),
        _sp("sus_scrofa", "9823", "sus_scrofa", "", False, "probe"),
        _sp("cavia_porcellus", "10141", "cavia_porcellus", "", False, "probe"),
        _sp("xenopus_tropicalis", "8364", "xenopus_tropicalis", "", False, "probe"),
        _sp("ciona_intestinalis", "7719", "ciona_intestinalis", "", False, "probe"),
        _sp("branchiostoma_floridae", "7739", "", "", False, "probe"),
    ]
}
# S. purpuratus is not a project species; it is the urchin bridge waypoint only.
BRIDGE_SPECIES = _sp("strongylocentrotus_purpuratus", "7668", "", "strongylocentrotus_purpuratus", False, "auxiliary")

BRIDGE_WAYPOINT = "strongylocentrotus_purpuratus"
URCHIN_SPECIES = ("lytechinus_variegatus", BRIDGE_WAYPOINT)

EMPTY_STATS = {
    "n_rows": 0,
    "n_dropped_type": 0,
    "n_dropped_confidence": 0,
    "n_kept_bijection": 0,
    "n_dropped_bijection": 0,
}


# ---------------------------------------------------------------- gene IDs


def strip_version_suffix(gene_id: str) -> str:
    """Strip an Ensembl/FBgn/WBGene-style version suffix; leave other dotted IDs intact."""
    if VERSIONED_STABLE_ID_RE.match(gene_id):
        return gene_id.rsplit(".", 1)[0]
    return gene_id


def canonical_gene_id(species: str, gene_id: str) -> str:
    """Canonicalize a gene ID: strip stable-ID versions and unify urchin LOC/GeneID aliases."""
    gene_id = strip_version_suffix(gene_id)
    if species in URCHIN_SPECIES:
        m = _GENEID_ALIAS_RE.match(gene_id)
        if m:
            return f"GeneID_{m.group(1)}"
    return gene_id


def gene_aliases(species: str, gene_id: str) -> list[str]:
    """Alternative query strings for a gene ID (urchin LOC <-> GeneID_ identity)."""
    canon = canonical_gene_id(species, gene_id)
    m = _GENEID_ALIAS_RE.match(canon)
    if m:
        return [f"GeneID_{m.group(1)}", f"LOC{m.group(1)}"]
    return [canon]


# ---------------------------------------------------------------- pair construction


def select_one2one(rows) -> tuple[list[tuple[str, str]], dict]:
    """Filter raw homolog rows to a strict 1:1 set.

    ``rows`` yields ``(gene_a, gene_b, orthology_type, orthology_confidence)``. Keeps only
    ``ortholog_one2one`` with confidence ``1``, strips stable-ID versions, deduplicates
    identical pairs, then enforces a strict bijection: a gene with anything other than one
    retained partner is dropped together with all its pairs (many-to-one / many-to-many are
    dropped, never collapsed).
    """
    stats = dict(EMPTY_STATS)
    seen: set[tuple[str, str]] = set()
    for gene_a, gene_b, otype, confidence in rows:
        stats["n_rows"] += 1
        if otype != "ortholog_one2one":
            stats["n_dropped_type"] += 1
            continue
        if str(confidence) != "1":
            stats["n_dropped_confidence"] += 1
            continue
        pair = (strip_version_suffix(gene_a), strip_version_suffix(gene_b))
        if pair[0] and pair[1]:
            seen.add(pair)
    partners_a: dict[str, set[str]] = {}
    partners_b: dict[str, set[str]] = {}
    for gene_a, gene_b in seen:
        partners_a.setdefault(gene_a, set()).add(gene_b)
        partners_b.setdefault(gene_b, set()).add(gene_a)
    kept = sorted(p for p in seen if len(partners_a[p[0]]) == 1 and len(partners_b[p[1]]) == 1)
    stats["n_kept_bijection"] = len(kept)
    stats["n_dropped_bijection"] = len(seen) - len(kept)
    return kept, stats


def filter_pair_rows(raw_rows, species_a: str, species_b: str) -> tuple[list[tuple[str, str]], dict]:
    """Finalize one pair's raw rows: 1:1 filtering, canonical IDs, (species_a, species_b) order."""
    pairs, stats = select_one2one(raw_rows)
    canon = {(canonical_gene_id(species_a, x), canonical_gene_id(species_b, y)) for x, y in pairs}
    return sorted(canon), stats


def chain_bridge(link_lv_sp: list[tuple[str, str]], link_sp_x: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Compose two strict 1:1 links into lv <-> x pairs.

    ``link_lv_sp`` holds (lv, sp) pairs and ``link_sp_x`` holds (sp, x) pairs. A sp gene
    must appear exactly once in each link; ambiguous sp genes are dropped.
    """
    sp_to_lv: dict[str, list[str]] = {}
    for lv, sp in link_lv_sp:
        sp_to_lv.setdefault(sp, []).append(lv)
    sp_to_x: dict[str, list[str]] = {}
    for sp, x in link_sp_x:
        sp_to_x.setdefault(sp, []).append(x)
    out = []
    for sp, lvs in sp_to_lv.items():
        xs = sp_to_x.get(sp, [])
        if len(lvs) == 1 and len(xs) == 1:
            out.append((lvs[0], xs[0]))
    return sorted(out)


def merge_bridge(
    direct: list[tuple[str, str]], bridged: list[tuple[str, str]], threshold: int
) -> tuple[list[tuple[str, str]], bool]:
    """Apply the urchin bridge fallback: when the direct set is thin, add bridged pairs.

    "Thin" means fewer than ``threshold`` direct 1:1 pairs (default: the >= 5,000 floor).
    Returns (pairs, bridge_used).
    """
    if len(direct) >= threshold:
        return sorted(direct), False
    return sorted(set(direct) | set(bridged)), bool(bridged)


# ---------------------------------------------------------------- coverage floors


def evaluate_floors(
    n_pairs: int, n_compared_a: int, n_compared_b: int, min_fraction: float = 0.6, min_pairs: int = 5000
) -> dict:
    """Evaluate the per-pair coverage floors (design section 6, rule 4).

    (a) fraction of compared genes with a 1:1 ortholog >= ``min_fraction`` on both sides;
    (b) genome-wide 1:1 set size >= ``min_pairs``. Pairs with no data fail both.
    """
    frac_a = n_pairs / n_compared_a if n_compared_a else None
    frac_b = n_pairs / n_compared_b if n_compared_b else None
    pass_fraction = frac_a is not None and frac_b is not None and frac_a >= min_fraction and frac_b >= min_fraction
    pass_min_pairs = n_pairs >= min_pairs
    return {
        "n_pairs": n_pairs,
        "n_compared_a": n_compared_a,
        "n_compared_b": n_compared_b,
        "coverage_a": frac_a,
        "coverage_b": frac_b,
        "pass_fraction_floor": pass_fraction,
        "pass_min_pairs_floor": pass_min_pairs,
        "floors_pass": pass_fraction and pass_min_pairs,
        "no_data": n_pairs == 0,
    }


# ---------------------------------------------------------------- HTTP


class CachedHTTP:
    """Throttled GET with an on-disk cache; retries transient failures, honors Retry-After.

    ``url`` may be one URL or a list of mirrors (tried in order each attempt). Transient
    failures (429/403/5xx/network) retry with exponential backoff. Every response body is
    cached so a rerun resumes instead of refetching. ``get_binary`` streams large files.
    """

    def __init__(self, cache_dir: Path, offline: bool = False, throttle: float = 5.0):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.throttle = throttle
        # Ensembl's CDN rejects the default python-requests User-Agent (403/429); send ours.
        self.headers = {"User-Agent": USER_AGENT}
        self._host_lock = threading.Lock()
        self._last: dict[str, float] = {}
        self.per_host_interval = {
            "ftp.ensembl.org": 2.0,
            "ftp.ebi.ac.uk": 2.0,
            "www.ensembl.org": 10.0,
            "metazoa.ensembl.org": 10.0,
        }

    def _throttle(self, url: str) -> None:
        host = url.split("/")[2]
        interval = self.per_host_interval.get(host, self.throttle)
        with self._host_lock:
            wait = self._last.get(host, 0.0) + interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last[host] = time.monotonic()

    def _cache_path(self, tag: str, urls: list[str], params: dict | None) -> str:
        key = hashlib.sha1(f"{sorted(urls)}\n{sorted((params or {}).items())}".encode()).hexdigest()[:16]
        return str(self.cache_dir / f"{tag}_{key}")

    def get(self, tag: str, url, params: dict | None = None) -> str:
        urls = list(url) if isinstance(url, (list, tuple)) else [url]
        path = Path(self._cache_path(tag, urls, params) + ".txt")
        if path.exists():
            return path.read_bytes().decode("utf-8")  # byte-faithful: text mode would translate newlines
        if self.offline:
            raise RuntimeError(f"offline: no cache entry for {urls[0]} ({tag})")
        delay = 5.0
        for _ in range(8):
            retry_after = None
            n_missing = 0
            for u in urls:
                self._throttle(u)
                try:
                    r = requests.get(u, params=params, headers=self.headers, timeout=600)
                except requests.RequestException as e:
                    print(f"    request error for {tag} at {u}: {e}, trying next/retrying", flush=True)
                    continue
                if r.status_code == 200:
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    tmp = path.parent / (path.name + ".tmp")
                    tmp.write_bytes(r.text.encode("utf-8"))
                    tmp.replace(path)
                    return r.text
                if r.status_code == 404:
                    n_missing += 1
                    print(f"    HTTP 404 (missing) for {tag} at {u}", flush=True)
                    continue
                print(f"    HTTP {r.status_code} for {tag} at {u}, trying next/retrying", flush=True)
                if r.headers.get("Retry-After"):
                    retry_after = max(retry_after or 0.0, float(r.headers["Retry-After"]))
            if n_missing == len(urls):
                raise RuntimeError(f"HTTP 404 (missing resource): {urls[0]} ({tag})")
            time.sleep(retry_after if retry_after is not None else delay)
            delay = min(delay * 2, 300.0)
        raise RuntimeError(f"GET failed after retries: {urls[0]} ({tag})")

    def get_binary(self, tag: str, url: str) -> Path:
        """Stream a large binary into the cache; returns the cache path."""
        path = Path(self._cache_path(tag, [url], None) + ".bin")
        if path.exists():
            return path
        if self.offline:
            raise RuntimeError(f"offline: no cache entry for {url} ({tag})")
        delay = 5.0
        for _ in range(8):
            self._throttle(url)
            tmp = path.parent / (path.name + ".tmp")
            try:
                with requests.get(url, headers=self.headers, stream=True, timeout=1800) as r:
                    if r.status_code == 200:
                        self.cache_dir.mkdir(parents=True, exist_ok=True)
                        with open(tmp, "wb") as fh:
                            for chunk in r.iter_content(1 << 20):
                                fh.write(chunk)
                        tmp.replace(path)
                        return path
                    if r.status_code == 404:
                        raise RuntimeError(f"HTTP 404 (missing resource): {url} ({tag})")
                    print(f"    HTTP {r.status_code} for {tag} at {url}, retrying", flush=True)
                    if r.headers.get("Retry-After"):
                        delay = max(delay, float(r.headers["Retry-After"]))
            except requests.RequestException as e:
                print(f"    request error for {tag} at {url}: {e}, retrying", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 300.0)
        raise RuntimeError(f"binary GET failed after retries: {url} ({tag})")


# ---------------------------------------------------------------- Compara bulk dumps


def iter_homology_rows(lines):
    """Yield (species, gene, homology_species, homology_gene, homology_type, confidence)."""
    idx = [
        HOMOLOGY_FIELDS.index(f)
        for f in (
            "species",
            "gene_stable_id",
            "homology_species",
            "homology_gene_stable_id",
            "homology_type",
            "is_high_confidence",
        )
    ]
    for line in lines:
        line = line.rstrip("\n")
        if not line:
            continue
        if line.startswith("gene_stable_id"):
            cols = line.split("\t")
            idx = [
                cols.index(f)
                for f in (
                    "species",
                    "gene_stable_id",
                    "homology_species",
                    "homology_gene_stable_id",
                    "homology_type",
                    "is_high_confidence",
                )
            ]
            continue
        c = line.split("\t")
        if len(c) <= max(idx):
            continue
        yield c[idx[0]], c[idx[1]], c[idx[2]], c[idx[3]], c[idx[4]], c[idx[5]]


def match_wanted(value: str, wanted: list[str]) -> str | None:
    """Map a dump ``species`` value to one of our species names (handles _gca... suffixes)."""
    if value in wanted:
        return value
    for name in wanted:
        if value.startswith(name + "_gca"):
            return name
    return None


def collection_for(name_a: str, name_b: str) -> str:
    """Compara gene-tree collection serving a species pair (urchins live in Metazoa)."""
    if URCHIN_SPECIES[0] in (name_a, name_b) or BRIDGE_WAYPOINT in (name_a, name_b):
        return "metazoa"
    return "main"


def collect_pair_rows(rows, source: str, wanted: list[str], order: dict[str, int]) -> dict:
    """Bucket raw homology rows per species pair, oriented by ``order`` and collection-filtered."""
    out: dict = {}
    for species, gene, hspecies, hgene, otype, confidence in rows:
        a = match_wanted(species, wanted)
        b = match_wanted(hspecies, wanted)
        if a is None or b is None or a == b:
            continue
        if collection_for(a, b) != source:
            continue
        if order[a] < order[b]:
            out.setdefault((a, b), []).append((gene, hgene, otype, confidence))
        else:
            out.setdefault((b, a), []).append((hgene, gene, otype, confidence))
    return out


class ComparaBulk:
    """Per-genome Ensembl Compara homology TSV dumps (bulk source; <= 20 files)."""

    def __init__(self, http: CachedHTTP, main_release: str, metazoa_release: str):
        self.http = http
        self.main_release = main_release
        self.metazoa_release = metazoa_release
        self.provenance: list[dict] = []

    def _base(self, collection: str) -> str:
        if collection == "main":
            return f"{MAIN_FTP}/release-{self.main_release}/tsv/ensembl-compara/homologies"
        return f"{METAZOA_FTP}/release-{self.metazoa_release}/tsv/ensembl-compara/homologies"

    def genome_files(self, collection: str, genome: str) -> list[str]:
        """Homology dump file names in one genome directory (protein collections only)."""
        text = self.http.get(f"listing_{collection}_{genome}", f"{self._base(collection)}/{genome}/", None)
        names = re.findall(r'href="(Compara\.[^"]+\.homologies\.tsv\.gz)"', text)
        keep = [n for n in names if "protein_" in n and not any(x in n for x in ("pangenome", "murinae", "pig_breeds"))]
        return sorted(set(keep))

    def md5sums(self, collection: str, genome: str) -> dict[str, str]:
        """Published checksums for a genome dir ({file: md5}); {} when none are published."""
        for name in ("MD5SUM", "CHECKSUMS"):
            try:
                text = self.http.get(
                    f"md5_{collection}_{genome}_{name}", f"{self._base(collection)}/{genome}/{name}", None
                )
            except RuntimeError:
                continue
            out = {}
            for line in text.splitlines():
                m = re.search(r"([0-9a-f]{32})", line)
                m2 = re.search(r"[* ](\S*\.tsv\.gz)\s*$", line) or re.search(r"\((\S*\.tsv\.gz)\)", line)
                if m and m2:
                    out[m2.group(1)] = m.group(1)
            return out
        return {}

    def load_genome(self, collection: str, genome: str, wanted: list[str], order: dict[str, int]) -> dict:
        """Download and parse one genome's dump files; return pair->raw-rows buckets."""
        merged: dict = {}
        md5s = self.md5sums(collection, genome)
        for fname in self.genome_files(collection, genome):
            url = f"{self._base(collection)}/{genome}/{fname}"
            path = self.http.get_binary(f"compara_{collection}_{genome}", url)
            sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            expected = md5s.get(fname)
            with gzip.open(path, "rt") as fh:
                buckets = collect_pair_rows(iter_homology_rows(fh), collection, wanted, order)
            n_rows = sum(len(v) for v in buckets.values())
            for key, rows in buckets.items():
                merged.setdefault(key, []).extend(rows)
            self.provenance.append(
                {
                    "collection": collection,
                    "genome": genome,
                    "file": fname,
                    "url": url,
                    "bytes": path.stat().st_size,
                    "sha256": sha256,
                    "md5_expected": expected,
                    "md5_ok": expected is None or hashlib.md5(path.read_bytes()).hexdigest() == expected,
                    "n_rows_in_scope": n_rows,
                }
            )
            print(f"    parsed {collection}/{genome}/{fname}: {n_rows} in-scope rows", flush=True)
        return merged


def protein_coding_genes(gtf_gz: Path) -> set[str]:
    """Distinct protein-coding gene IDs in an Ensembl GTF."""
    out = set()
    gene_id_re = re.compile(r'gene_id "([^"]+)"')
    with gzip.open(gtf_gz, "rt") as fh:
        for line in fh:
            if line.startswith("#") or "\tgene\t" not in line:
                continue
            if 'gene_biotype "protein_coding"' not in line:
                continue
            m = gene_id_re.search(line)
            if m:
                out.add(m.group(1))
    return out


# ---------------------------------------------------------------- cross-check clients


class OrthoDBClient:
    """OrthoDB v12 REST (https://data.orthodb.org/v12), via CachedHTTP."""

    def __init__(self, http: CachedHTTP):
        self.http = http

    def genesearch(self, query: str) -> dict:
        return json.loads(self.http.get("orthodb_genesearch", f"{ORTHODB_API}/genesearch", {"query": query}) or "{}")

    def orthologs(self, gene_id: str, organisms: list[str]) -> dict:
        params = {"id": gene_id, "species": ",".join(organisms)}
        return json.loads(self.http.get("orthodb_orthologs", f"{ORTHODB_API}/orthologs", params) or "{}")


class AllianceClient:
    """Alliance of Genome Resources API (DIOPT-integrated orthology), via CachedHTTP."""

    def __init__(self, http: CachedHTTP):
        self.http = http

    def search(self, query: str) -> dict:
        return json.loads(self.http.get("alliance_search", f"{ALLIANCE_API}/search", {"q": query}) or "{}")

    def orthologs(self, curie: str) -> dict:
        return json.loads(self.http.get("alliance_orthologs", f"{ALLIANCE_API}/gene/{curie}/orthologs", None) or "{}")


def orthodb_resolve(client, species: str, gene_id: str) -> dict | None:
    """Resolve a gene to its OrthoDB gene id + organism id, or None when unresolved.

    Ambiguous matches (more than one gene matched the query) are unresolved.
    """
    for query in gene_aliases(species, gene_id):
        data = client.genesearch(query)
        gene = data.get("gene") or {}
        gene_id_obj = gene.get("gene_id") or {}
        organism = data.get("organism") or {}
        if gene_id_obj.get("param") and organism.get("id") and str(data.get("nb_genes_matched_the_query")) == "1":
            return {"odb_gene": gene_id_obj["param"], "organism": organism["id"], "query": query}
    return None


def orthodb_verdict(resolution_a: dict | None, resolution_b: dict | None, response: dict | None) -> dict:
    """Verdict of the OrthoDB check for one retained pair.

    Concordant when some shared orthogroup level holds exactly one gene per species for the
    pair's two genes; discordant when both genes resolve but no level does; unavailable when
    at least one gene does not resolve in OrthoDB.
    """
    if resolution_a is None or resolution_b is None:
        missing = [k for k, r in (("gene_a", resolution_a), ("gene_b", resolution_b)) if r is None]
        return {"verdict": "unavailable", "reason": f"unresolved_in_orthodb:{','.join(missing)}"}
    entries = (response or {}).get("data") or []
    by_clade: dict = {}
    for e in entries:
        params = by_clade.setdefault(e.get("clade_id"), {resolution_a["organism"]: [], resolution_b["organism"]: []})
        if e.get("taxon_id") in params:
            params[e["taxon_id"]].append((e.get("gene") or {}).get("param", ""))
    for clade, params in sorted(by_clade.items(), key=lambda kv: str(kv[0])):
        if set(params[resolution_a["organism"]]) == {resolution_a["odb_gene"]} and set(
            params[resolution_b["organism"]]
        ) == {resolution_b["odb_gene"]}:
            return {"verdict": "concordant", "level_taxid": clade}
    return {"verdict": "discordant", "reason": "no_shared_orthogroup_level_with_one_gene_per_species"}


def match_alliance_hits(query_id: str, results: list[dict]) -> str | None:
    """Return the CURIE of the unique exact match for ``query_id`` in /search results.

    Matching is exact on the identifier or its CURIE local part (prefix differences such as
    ``WBGene1`` vs ``WB:WBGene1`` are bridged); the fuzzy search index never decides.
    """
    hits = []
    for r in results:
        ids = {r.get("curie"), r.get("id")}
        ids |= {x.get("referencedCurie") if isinstance(x, dict) else str(x) for x in (r.get("crossReferences") or [])}
        if any(i and (i == query_id or i.split(":")[-1] == query_id) for i in ids):
            hits.append(r.get("curie") or r.get("id"))
    hits = [h for h in dict.fromkeys(hits) if h]
    return hits[0] if len(hits) == 1 else None


def alliance_resolve(client, species: str, gene_id: str) -> dict | None:
    """Resolve a gene to its Alliance CURIE, or None when unresolved/ambiguous."""
    for query in gene_aliases(species, gene_id):
        curie = match_alliance_hits(query, client.search(query).get("results") or [])
        if curie:
            return {"curie": curie, "query": query}
    return None


def alliance_called_pairs(orthologs_response: dict) -> set[tuple[str, str]]:
    """Pairs of CURIEs called as orthologs in an Alliance /orthologs response."""
    out = set()
    for r in (orthologs_response or {}).get("results") or []:
        g = r.get("geneToGeneOrthologyGenerated") or {}
        subject = ((g.get("subjectGene") or {}).get("primaryExternalId") or "").strip()
        obj = ((g.get("objectGene") or {}).get("primaryExternalId") or "").strip()
        if subject and obj:
            out.add(tuple(sorted((subject, obj))))
    return out


def alliance_verdict(
    resolution_a: dict | None, resolution_b: dict | None, orthologs_a: dict, orthologs_b: dict
) -> dict:
    """Verdict of the Alliance DIOPT-integrated check for one retained pair.

    Concordant when an Alliance orthology call links the two genes; discordant when both
    genes resolve and Alliance has orthology calls but not for this pair; unavailable
    otherwise (gene unresolved or no calls at all).
    """
    if resolution_a is None or resolution_b is None:
        missing = [k for k, r in (("gene_a", resolution_a), ("gene_b", resolution_b)) if r is None]
        return {"verdict": "unavailable", "reason": f"unresolved_in_alliance:{','.join(missing)}"}
    pair = tuple(sorted((resolution_a["curie"], resolution_b["curie"])))
    called = alliance_called_pairs(orthologs_a) | alliance_called_pairs(orthologs_b)
    if pair in called:
        return {"verdict": "concordant"}
    if called:
        return {"verdict": "discordant", "reason": "alliance_has_orthology_calls_but_not_this_pair"}
    return {"verdict": "unavailable", "reason": "no_alliance_orthology_calls"}


def _service_unavailable(source: str, error: Exception) -> dict:
    return {"verdict": "unavailable", "reason": f"service_unavailable:{source}:{error}"}


def pair_crosscheck(row: dict, odb, agr, alliance_scope: bool) -> dict:
    """Run the cross-check for one sampled pair; ``drop`` is True when a source disagrees.

    A source outage is recorded as an explicit ``unavailable`` gap and never a fabricated
    verdict; outages never drop pairs.
    """
    result = {"pair": row}
    try:
        res_a = orthodb_resolve(odb, row["species_a"], row["gene_a"])
        res_b = orthodb_resolve(odb, row["species_b"], row["gene_b"])
        response = odb.orthologs(res_a["odb_gene"], [res_a["organism"], res_b["organism"]]) if res_a and res_b else None
        result["orthodb"] = orthodb_verdict(res_a, res_b, response)
    except Exception as e:  # OrthoDB outage/blockage: record the gap, continue
        result["orthodb"] = _service_unavailable("orthodb", e)
    if alliance_scope:
        try:
            a_res = alliance_resolve(agr, row["species_a"], row["gene_a"])
            b_res = alliance_resolve(agr, row["species_b"], row["gene_b"])
            o_a = agr.orthologs(a_res["curie"]) if a_res else {}
            o_b = agr.orthologs(b_res["curie"]) if b_res else {}
            result["alliance"] = alliance_verdict(a_res, b_res, o_a, o_b)
        except Exception as e:  # Alliance outage/blockage: record the gap, continue
            result["alliance"] = _service_unavailable("alliance", e)
    else:
        result["alliance"] = {"verdict": "skipped", "reason": "species_not_in_alliance_member_set"}
    result["drop"] = any(result[s]["verdict"] == "discordant" for s in ("orthodb", "alliance"))
    return result


# ---------------------------------------------------------------- inputs


def load_vocab(species: str) -> set[str]:
    with h5py.File(VOCAB_DIR / f"{species}_gene.h5") as f:
        return {k.decode() if isinstance(k, bytes) else str(k) for k in f["keys"][:]}


def load_echinobase_consensus(path: Path) -> list[tuple[str, str]]:
    """EchinoBase 5-tool-consensus lv <-> sp pairs (>= 3 tools) as (lv, sp) GeneID_ IDs."""
    rows = []
    with open(path) as fh:
        next(fh, None)  # header: LVAR SPURP FO IP OF PO SO TOTAL
        for line in fh:
            c = line.rstrip("\n").split("\t")
            if len(c) < 8 or not c[0].isdigit() or not c[1].isdigit():
                continue
            if int(c[7]) >= 3:
                rows.append((f"GeneID_{c[0]}", f"GeneID_{c[1]}"))
    kept, _ = select_one2one([(a, b, "ortholog_one2one", "1") for a, b in rows])
    return kept


def compared_genes(sp: Species, vocab: set[str] | None, n_protein_coding: int) -> tuple[set[str] | None, str, int]:
    """Compared-gene set and denominator source for a species.

    Training species use the model vocabulary; probe species use the Ensembl protein-coding
    gene count of the pinned release (their only stable genome-wide gene universe) - only
    the count is needed for the floor fractions.
    """
    if vocab is not None:
        return {canonical_gene_id(sp.name, g) for g in vocab}, "model_vocabulary", n_protein_coding
    return None, "ensembl_protein_coding_genes", n_protein_coding


# ---------------------------------------------------------------- build


@dataclass
class PairPlan:
    species_a: str
    species_b: str
    collection: str = ""
    status: str = "compara"
    reason: str = ""


def plan_pair(a: Species, b: Species) -> PairPlan:
    """Decide where (if anywhere) Compara serves this species pair."""
    if not a.datasets_any() or not b.datasets_any():
        missing = a.name if not a.datasets_any() else b.name
        return PairPlan(
            a.name, b.name, status="no_compara_gene_set", reason=f"{missing} has no Ensembl Compara gene set"
        )
    shared = set(a.marts()) & set(b.marts())
    if "main" in shared:
        return PairPlan(a.name, b.name, collection="main")
    if "metazoa" in shared:
        return PairPlan(a.name, b.name, collection="metazoa")
    return PairPlan(
        a.name,
        b.name,
        status="no_homology_data",
        reason=(
            "Ensembl Compara computes homologies within gene-tree collections; this pair spans "
            "the Ensembl (vertebrates) and Ensembl Metazoa collections and has no Compara homologies"
        ),
    )


def write_table(pairs: list[dict], path: Path) -> tuple[int, str]:
    """Write the ortholog table (sorted TSV.gz); returns (rows, sha256)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = "".join(f"{r['species_a']}\t{r['gene_a']}\t{r['species_b']}\t{r['gene_b']}\n" for r in pairs)
    payload = gzip.compress(raw.encode(), compresslevel=9, mtime=0)
    path.write_bytes(payload)
    return len(pairs), hashlib.sha256(payload).hexdigest()


def run_parallel(fn, items, workers: int):
    items = list(items)
    if workers <= 1 or len(items) <= 1:
        return [fn(x) for x in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


def release_info(http: CachedHTTP, args) -> dict:
    """Pin the Ensembl releases and record source provenance/blockage evidence."""
    out = {
        "ensembl_release": args.compara_release,
        "ensembl_metazoa_release": args.metazoa_release,
        "source": "Ensembl Compara gene-tree homology TSV dumps (ftp.ensembl.org + EBI Ensembl Genomes FTP)",
        "rest_ensembl_releases": None,
        "biomart_status": None,
        "biomart_status_note": (
            "BioMart (the design's primary interface) was persistently unavailable at build time "
            "(429/403 from www.ensembl.org and its mirrors across several runs); the Compara homology "
            "TSV dumps are Ensembl Compara's own export of the same homology table and were preferred "
            "as the bulk source. One registry probe is recorded below."
        ),
        "release_url_checks": {},
    }
    try:
        body = http.get("ensembl_rest_data", ENSEMBL_REST_DATA, {"content-type": "application/json"})
        out["rest_ensembl_releases"] = json.loads(body).get("releases")
    except Exception as e:  # release pinning is best effort; failures are recorded verbatim
        out["rest_error"] = str(e)
    for release in ("release-110", "release-116"):
        url = f"{MAIN_FTP}/{release}/tsv/ensembl-compara/homologies/"
        try:
            http.get(f"check_{release}", url, None)
            out["release_url_checks"][release] = "available"
        except Exception as e:
            out["release_url_checks"][release] = f"unavailable: {e}"
    try:
        text = http.get("biomart_probe", BIOMART_PROBE_URL, {"type": "registry"})
        out["biomart_status"] = (
            "200 (unexpectedly available)" if "MartRegistry" in text else "200 but not a mart registry"
        )
    except Exception as e:  # the probe exists to record blockage evidence verbatim
        out["biomart_status"] = f"unavailable: {e}"
    return out


def gtf_url(http: CachedHTTP, species: str, release: str) -> str | None:
    """Locate the pinned release's annotation GTF for a species (plain *.gtf.gz, no abinitio)."""
    listing = http.get(f"gtf_listing_{species}", f"{MAIN_FTP}/release-{release}/gtf/{species}/", None)
    names = [n for n in re.findall(r'href="([^"]+\.gtf\.gz)"', listing) if ".abinitio." not in n and ".chr." not in n]
    return f"{MAIN_FTP}/release-{release}/gtf/{species}/{names[0]}" if names else None


def build(args) -> int:
    http = CachedHTTP(args.cache_dir, offline=args.offline, throttle=args.throttle)
    snapshot = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    releases = release_info(http, args)

    wanted = SPECIES_ORDER + [BRIDGE_WAYPOINT]
    order = {name: i for i, name in enumerate(SPECIES_ORDER + [BRIDGE_WAYPOINT])}

    pair_keys = []
    plans: dict[str, PairPlan] = {}
    for i, name_a in enumerate(SPECIES_ORDER):
        for name_b in SPECIES_ORDER[i + 1 :]:
            key = f"{name_a}__{name_b}"
            plan = plan_pair(SPECIES[name_a], SPECIES[name_b])
            plans[key] = plan
            pair_keys.append(key)

    # ---- bulk acquisition: <= 20 per-genome homology dump files ----
    bulk = ComparaBulk(http, args.compara_release, args.metazoa_release)
    pair_rows: dict = {}
    availability = {"species": {}, "pairs": {}}
    genomes: dict[str, list[str]] = {}
    for name in wanted:
        sp = SPECIES.get(name) or BRIDGE_SPECIES
        for collection in sp.marts():
            genomes.setdefault(collection, []).append(sp.genome_for(collection))
    for collection in ("main", "metazoa"):
        for genome in sorted(set(genomes.get(collection, []))):
            print(f"loading {collection}/{genome}...", flush=True)
            for key, rows in bulk.load_genome(collection, genome, wanted, order).items():
                pair_rows.setdefault(key, []).extend(rows)

    for name in SPECIES_ORDER:
        sp = SPECIES[name]
        info = {"taxid": sp.taxid, "role": sp.role, "has_vocab": sp.has_vocab, "genomes": {}}
        if not sp.datasets_any():
            info["status"] = "no_compara_gene_set"
            info["note"] = (
                "Ensembl (Compara release %s) and Ensembl Metazoa (release %s) carry no "
                "Branchiostoma floridae gene set; Ensembl Metazoa carries Branchiostoma "
                "lanceolatum only, which is a different species and is NOT substituted here."
                % (args.compara_release, args.metazoa_release)
            )
        else:
            for collection in sp.marts():
                info["genomes"][collection] = sp.genome_for(collection)
            info["status"] = "compara"
        availability["species"][name] = info

    # ---- assemble per-pair 1:1 sets (with the urchin bridge fallback) ----
    sp_links: dict[str, list] = {}
    link_lv_sp = load_echinobase_consensus(args.echinobase_consensus)
    print(f"EchinoBase consensus lv<->sp link: {len(link_lv_sp)} strict 1:1 pairs", flush=True)
    pair_sets: dict[str, list[tuple[str, str]]] = {}
    pair_stats: dict[str, dict] = {}
    bridge_notes: dict[str, dict] = {}
    for key in pair_keys:
        plan = plans[key]
        raw = pair_rows.get((plan.species_a, plan.species_b), []) if plan.collection else []
        direct, stats = filter_pair_rows(raw, plan.species_a, plan.species_b)
        bridged: list[tuple[str, str]] = []
        if "lytechinus_variegatus" in (plan.species_a, plan.species_b):
            x = plan.species_b if plan.species_a == "lytechinus_variegatus" else plan.species_a
            if x not in sp_links:
                sp_key = tuple(sorted((BRIDGE_WAYPOINT, x), key=order.__getitem__))
                sp_links[x] = filter_pair_rows(pair_rows.get(sp_key, []), *sp_key)[0]
            link_sp_x = [(sp, gx) for gx, sp in sp_links[x]]  # chain_bridge expects (sp, x) links
            bridged = chain_bridge(link_lv_sp, link_sp_x)
            if plan.species_b == "lytechinus_variegatus":
                bridged = sorted((y, lv) for lv, y in bridged)
        pairs, used = merge_bridge(direct, bridged, args.bridge_threshold)
        pair_sets[key] = pairs
        pair_stats[key] = stats
        bridge_notes[key] = {
            "bridge_used": used,
            "n_direct_compara": len(direct),
            "n_bridged_via_spurpuratus": len(bridged),
        }
        if plan.collection and not raw:
            plan.status = "no_homology_data"
            plan.reason = (
                f"the {plan.collection} Compara collection serves both species but the pinned dumps "
                f"contain zero homology rows for this pair"
            )
        availability["pairs"][key] = {
            "status": plan.status,
            "reason": plan.reason,
            "collection": plan.collection or None,
            "n_raw_rows": len(raw),
        }

    # ---- compared gene sets ----
    print("counting probe protein-coding genes (pinned release GTFs)...", flush=True)
    n_protein_coding: dict[str, int] = {}
    for name in SPECIES_ORDER:
        sp = SPECIES[name]
        if sp.has_vocab or not sp.datasets_any():
            n_protein_coding[name] = 0
            continue
        url = gtf_url(http, name, args.compara_release)
        if url is None:
            n_protein_coding[name] = 0
            continue
        path = http.get_binary(f"gtf_{name}", url)
        n_protein_coding[name] = len(protein_coding_genes(path))
        print(f"  {name}: {n_protein_coding[name]} protein-coding genes", flush=True)

    compared = {}
    for name in SPECIES_ORDER:
        sp = SPECIES[name]
        vocab = load_vocab(name) if sp.has_vocab else None
        genes, source, n_pc = compared_genes(sp, vocab, n_protein_coding.get(name, 0))
        compared[name] = {
            "source": source,
            "n_compared": len(genes) if genes is not None else n_pc,
            "n_ensembl_protein_coding": n_pc,
        }

    # ---- coverage report ----
    coverage = {}
    for key in pair_keys:
        plan = plans[key]
        n_pairs = len(pair_sets[key])
        a, b = compared[plan.species_a], compared[plan.species_b]
        floors = evaluate_floors(n_pairs, a["n_compared"], b["n_compared"], args.min_fraction, args.min_pairs)
        floors.update(
            {
                "denominator_source_a": a["source"],
                "denominator_source_b": b["source"],
                "n_ensembl_protein_coding_a": a["n_ensembl_protein_coding"],
                "n_ensembl_protein_coding_b": b["n_ensembl_protein_coding"],
            }
        )
        coverage[key] = floors
        cov_a = f"{floors['coverage_a']:.3f}" if floors["coverage_a"] is not None else "n/a"
        cov_b = f"{floors['coverage_b']:.3f}" if floors["coverage_b"] is not None else "n/a"
        print(
            f"  {key}: {n_pairs} pairs, cov {cov_a}/{cov_b} [{'ok' if floors['floors_pass'] else 'FLAGGED'}]",
            flush=True,
        )

    # ---- cross-check ----
    table_rows = [
        {"species_a": plans[k].species_a, "species_b": plans[k].species_b, "gene_a": ga, "gene_b": gb}
        for k in pair_keys
        for ga, gb in pair_sets[k]
    ]
    sample = random.Random(args.seed).sample(table_rows, min(args.sample_size, len(table_rows)))
    print(f"cross-checking {len(sample)} sampled pairs (throttled, cached)...", flush=True)
    odb = OrthoDBClient(http)
    agr = AllianceClient(http)

    def _check(row):
        scope = row["species_a"] in ALLIANCE_SPECIES and row["species_b"] in ALLIANCE_SPECIES
        return pair_crosscheck(row, odb, agr, scope)

    checks = run_parallel(_check, sample, max(1, args.workers // 2))
    dropped = {
        (c["pair"]["species_a"], c["pair"]["gene_a"], c["pair"]["species_b"], c["pair"]["gene_b"])
        for c in checks
        if c["drop"]
    }
    kept_rows = [r for r in table_rows if (r["species_a"], r["gene_a"], r["species_b"], r["gene_b"]) not in dropped]
    kept_rows.sort(
        key=lambda r: (
            SPECIES_ORDER.index(r["species_a"]),
            r["gene_a"],
            SPECIES_ORDER.index(r["species_b"]),
            r["gene_b"],
        )
    )

    concordance = {
        "n_sampled": len(sample),
        "seed": args.seed,
        "orthodb": {"concordant": 0, "discordant": 0, "unavailable": 0},
        "alliance": {"concordant": 0, "discordant": 0, "unavailable": 0, "skipped": 0},
        "n_dropped": len(dropped),
    }
    for c in checks:
        concordance["orthodb"][c["orthodb"]["verdict"]] += 1
        concordance["alliance"][c["alliance"]["verdict"]] += 1

    # ---- write outputs ----
    n_rows, sha256 = write_table(kept_rows, args.out_dir / "ortholog_pairs.tsv.gz")
    final_counts = {key: 0 for key in pair_keys}
    for r in kept_rows:
        final_counts[f"{r['species_a']}__{r['species_b']}"] += 1
    manifest = {
        "schema_version": 1,
        "built_by": "scripts/build_ortholog_table.py",
        "design": "docs/perturbation-and-baseline-design.md#6-orthology-framework-s6",
        "snapshot_utc": snapshot,
        "ensembl_release": releases,
        "acquisition": {
            "files": bulk.provenance,
            "n_files": len(bulk.provenance),
            "biomart_probe": releases.get("biomart_status"),
        },
        "rules": {
            "kept_homology_type": "ortholog_one2one",
            "kept_orthology_confidence": 1,
            "many_to_one_many_to_many": "dropped, never collapsed",
            "version_stripping": "only ENS*/FBgn/WBGene stable IDs (docs/finetune-data-requirements.md section 3)",
            "id_aliases": "urchin LOC<n> and GeneID_<n> name the same NCBI gene; the table uses GeneID_<n>",
            "coverage_floors": {"min_fraction_compared_genes": args.min_fraction, "min_pairs": args.min_pairs},
            "bridge_threshold_pairs": args.bridge_threshold,
        },
        "species": {
            name: {
                "taxid": SPECIES[name].taxid,
                "role": SPECIES[name].role,
                "has_vocab": SPECIES[name].has_vocab,
                "denominator_source": compared[name]["source"],
                "n_compared_genes": compared[name]["n_compared"],
                "n_ensembl_protein_coding": compared[name]["n_ensembl_protein_coding"] or None,
            }
            for name in SPECIES_ORDER
        },
        "pairs": {
            key: {
                "species_a": plans[key].species_a,
                "species_b": plans[key].species_b,
                "status": plans[key].status,
                "reason": plans[key].reason,
                "collection": plans[key].collection or None,
                "n_raw_rows": availability["pairs"][key]["n_raw_rows"],
                "n_pairs": final_counts[key],
                "filter_stats": pair_stats[key],
                **bridge_notes[key],
                **{k2: v2 for k2, v2 in coverage[key].items() if k2 != "n_pairs"},
            }
            for key in pair_keys
        },
        "crosscheck": concordance,
        "table": {"path": "preprocess/orthologs/ortholog_pairs.tsv.gz", "rows": n_rows, "sha256": sha256},
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    (args.evidence_dir / "availability_report.json").write_text(
        json.dumps(availability, indent=1, sort_keys=True) + "\n"
    )
    (args.evidence_dir / "coverage_report.json").write_text(
        json.dumps(
            {
                "denominator_note": (
                    "floor (a) is evaluated on each side's compared genes: the model vocabulary for training "
                    "species, the Ensembl protein-coding gene count of the pinned release for zero-shot probe species"
                ),
                "pairs": {key: coverage[key] for key in pair_keys},
            },
            indent=1,
            sort_keys=True,
        )
        + "\n"
    )
    (args.evidence_dir / "crosscheck_report.json").write_text(
        json.dumps({"summary": concordance, "checks": checks}, indent=1, sort_keys=True) + "\n"
    )
    print(f"\nwrote {args.out_dir / 'ortholog_pairs.tsv.gz'} ({n_rows} rows, sha256 {sha256[:12]}...)")
    print(f"wrote {args.out_dir / 'manifest.json'}")
    print(f"wrote evidence reports under {args.evidence_dir}")
    print(f"cross-check concordance: {concordance}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / "cache" / "orthologs")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "preprocess" / "orthologs")
    parser.add_argument("--evidence-dir", type=Path, default=REPO_ROOT / "logs" / "dataset_audit" / "orthologs")
    parser.add_argument(
        "--compara-release",
        default="110",
        help="Ensembl release of the homology dumps (default 110, matching preprocess/fasta_manifest_pep.json)",
    )
    parser.add_argument("--metazoa-release", default="57", help="Ensembl Metazoa release (default 57 = Ensembl 110)")
    parser.add_argument(
        "--echinobase-consensus",
        type=Path,
        default=ECHEINOBASE_CONSENSUS,
        help="cached EchinoBase Spur-Lvar 5-tool consensus TSV (urchin bridge link)",
    )
    parser.add_argument("--sample-size", type=int, default=200, help="cross-check sample size (frozen design: 200)")
    parser.add_argument("--seed", type=int, default=42, help="cross-check sampling seed")
    parser.add_argument(
        "--min-fraction", type=float, default=0.6, help="coverage floor (a): fraction of compared genes"
    )
    parser.add_argument("--min-pairs", type=int, default=5000, help="coverage floor (b): genome-wide 1:1 set size")
    parser.add_argument(
        "--bridge-threshold", type=int, default=5000, help="direct pairs below which the urchin bridge is applied"
    )
    parser.add_argument("--workers", type=int, default=2, help="parallel cross-check workers")
    parser.add_argument("--throttle", type=float, default=5.0, help="min seconds between requests per host")
    parser.add_argument("--offline", action="store_true", help="use cached responses only")
    return build(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
