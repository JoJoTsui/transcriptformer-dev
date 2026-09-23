# Probe B4 unblock — asset/metadata audit, ESM-2 generation plan (NOT run), remaining blockers

Date: 2026-09-23. Read-only audit of the 8 probe H5ADs (obs/var metadata via h5py only; no
expression loaded, no source file modified). Companion to `preprocess/probe_stage_mappings.json`
(`metadata_provenance`, `fasta_provenance`) and `runs/probe_readiness.json`.
ESM-2 was **not** run; this file is documentation only.

## 1. Per-dataset metadata resolution (see config for full citations)

| dataset | cell_type | embryo_id | assay |
|---|---|---|---|
| macaque_zhai_2022 | `cell_type` (38) | **`sample` (6)** — Zhai 2022 "six CS8-11 embryos", 7 orig.ident libraries / 56,636 cells = n_obs | null — documented constant *10x Genomics Chromium* (Zhai 2022 Methods) |
| macaque_gong_2023 | null — no annotation at source (dataset README) | **`sample` (24)** — GEO GSE207534 GSM "ME…, replicate N" + "cell type: Embryo"; residual caveat: embryo count per library not stated anywhere | null — constant *10x Chromium SC 3' v3.1* (GEO GSE207534; README) |
| macaque_spatial | `celltype_detailed` (32) | null — 20 serial sections (`spatial_slice_id`) are not embryos; embryo count undocumented (README, Zenodo 19061842, NCB 2026 abstract) | null — platform not citable ("high-resolution spatial transcriptomics" only) |
| pig_simpson_2024 | `Celltypes` (36) | null — **pooled**: "23 pooled samples encompassing 62 pig embryos" (Simpson 2024) | null — constant *10x Genomics Chromium* (Simpson 2024 Methods) |
| guinea_pig_canizo_2025 | `author_cell_type` (8) | `embryo` (42, pre-existing) | null — constant *Smart-seq2* single-cell picking (Canizo 2025 Methods) |
| xenopus_briggs_2018 | `author_cell_type` (260) | null — **pooled**: "5-15 healthy embryos … per developmental stage" (GEO GSE113074 extract protocol) | **`InDrops_version`** (per-cell v2/v3; inDrop per Briggs 2018) |
| ciona_cao_2019 | null — no annotation at source (README) | null — **pooled**: "100 to 500 … embryos … per sample" (Cao 2019 Methods) | null — constant *10x Chromium SC 3' v2* (Cao 2019 Methods) |
| amphioxus_markos_2024 | null — no annotation at source (README) | null — **pooled**: "15 to 20 … embryos … per sample" (Markos 2024 Methods); `sample` == `stage` | null — constant *10x Chromium Next GEM 3' v3.1* (Markos 2024 Methods) |

Assay constants are recorded in the config but `metadata_columns.assay` stays null everywhere
except xenopus: `audit_probe_dataset` requires a real obs column, and no probe H5AD has one.
The resulting "assay lacks a verified source column" blockers are therefore expected.

## 2. FASTA verification and gene-ID namespaces (all URLs HTTP 200; headers inspected)

| species | URL (in `preprocess/fasta_manifest_pep.json`) | bytes | proteins | genes | `gene:` tag | vs probe var index |
|---|---|---|---|---|---|---|
| macaca_fascicularis | Ensembl r110 `Macaca_fascicularis.Macaca_fascicularis_6.0.pep.all.fa.gz` | 10,128,609 | 49,919 | 22,504 ENSMFAG | yes | **MISMATCH** — var = symbols/LOC; 0/26,135, 0/33,960, 0/4,663 exact (symbol overlap 12,613/14,202/3,263) |
| cavia_porcellus | Ensembl r110 `Cavia_porcellus.Cavpor3.0.pep.all.fa.gz` | 7,883,700 | 25,582 | 18,095 ENSCPOG | yes | **match at gene-ID level** — var composite `ENSCPOG…:SYMBOL`; 15,333/19,323 ENSCPOG components match (rest = non-coding); strip `:symbol` for lookup |
| ciona_intestinalis | NCBI `GCF_000224145.3_KH_protein.faa.gz` | 6,803,777 | 21,096 | n/a | **no** | **MISMATCH** — var = `KH2012:KH.C1.*` (15,228/15,269) + 39 ENSCING + 2 constructs; NCBI keys are NP/XP accessions; no verified FASTA exposes KH2012 IDs (Metazoa r39-63 has no Ciona; Ghost now ships KY/KY21 models) |
| branchiostoma_floridae | NCBI `GCF_000003815.2_Bfl_VNyyK_protein.faa.gz` | 10,031,501 | 43,041 | n/a (6,274 LOC tags in descriptions) | **no** | **PARTIAL** — var = `LOC1184xxxxx` from this same assembly (Markos 2024 quantified GCA_000003815.2); 6,273/29,726 var genes appear as description tokens, but `protein_embedding.py` would key by XP/NP accessions. GCF_000003815.1 (JGI) uses `BRAFLDRAFT_*` protein-model IDs — wrong namespace. |

Consequence: `record.description.split("gene:")` yields **protein accessions** (not gene IDs) for
the two NCBI files, so even after generation the vocab keys would not join to `var_names` without
a header rewrite or mapping table (not done). For xenopus the *existing* manifest entry has the
same problem in reverse: pre-generated ENSXETG keys vs var gene symbols.

Validator caveats (expected, captured in the report): the URL-substring check flags
"FASTA reference does not identify ciona_intestinalis / branchiostoma_floridae" because NCBI URLs
carry assembly accessions; species identity was verified from NCBI assembly records and the
`[Ciona intestinalis]` / `[Branchiostoma floridae]` organism field of every FASTA header.
macaque_zhai_2022 keeps its "Missing species metadata: species" blocker (obs has no species
column; README + Zhai 2022 identify M. fascicularis; not fabricatable read-only).

## 3. ESM-2 generation plan (document only — do NOT run until defects below are fixed)

Exact commands (per deliverable; run after installing fair-esm + biopython):

```bash
.venv/bin/python preprocess/protein_embedding.py --organism_key macaca_fascicularis   --output_dir checkpoints/tf_metazoa_finetuned/vocabs
.venv/bin/python preprocess/protein_embedding.py --organism_key cavia_porcellus       --output_dir checkpoints/tf_metazoa_finetuned/vocabs
.venv/bin/python preprocess/protein_embedding.py --organism_key ciona_intestinalis    --output_dir checkpoints/tf_metazoa_finetuned/vocabs
.venv/bin/python preprocess/protein_embedding.py --organism_key branchiostoma_floridae --output_dir checkpoints/tf_metazoa_finetuned/vocabs
```

Size/time estimates (stream-counted from the verified FASTAs; esm2_t36_3B_UR50D on the single
RTX 3090 24 GB; assume 1,000-3,000 residues/s with token-budget batching):

| key | proteins | genes | total residues | est. GPU time | output h5 (2560-d f32) |
|---|---|---|---|---|---|
| macaca_fascicularis | 49,919 | 22,504 | 27.1 M | 2.5-7.5 h | ~230 MB |
| cavia_porcellus | 25,582 | 18,095 | 14.4 M | 1.3-4 h | ~185 MB |
| ciona_intestinalis | 21,096 | 21,096* | 13.5 M | 1.2-3.8 h | ~216 MB |
| branchiostoma_floridae | 43,041 | 43,041* | 28.3 M | 2.6-7.9 h | ~441 MB |

*no `gene:` tags → one key per protein, no isoform averaging. Add ~2.5 GB one-off ESM-2 3B
checkpoint download. Sequences longer than 1,022 residues are truncated (`seq_length=1022`).
Whole-proteome embeddings are held in RAM and re-pickled after every batch (~0.5-1 GB/species
duplicated); batch token budget at the default `--batch_size 16` is 65,536 tokens/batch — too
large for 24 GB with a 3B model; use `--batch_size 1-2` (4,096-8,192 tokens) or fix chunking first.

Known defects of `preprocess/protein_embedding.py` (recorded, **not fixed** — out of scope):
1. **`fair-esm`/`esm` is NOT installed in `.venv`** (verified `ModuleNotFoundError: No module
   named 'esm'`; `Bio`/biopython is also missing and imported at module top) — the script cannot
   even import today.
2. **Embedding computation happens only inside `if torch.cuda.is_available():`** (the model
   forward, pooling and accumulation in `generate_embeddings`); a CPU run iterates the loader and
   **silently produces an empty `keys`/`arrays` HDF5** with no error.
3. **No chunked-inference mode** although register 8.1 requires chunking on this memory-limited
   host (~26 GiB RAM). There is also no resume (the `.tmp` pickle is written but never reloaded)
   and the batch token budget above is not clamped to VRAM.
4. Footgun: `FASTA_MANIFEST = "fasta_manifest_pep.json"` and `STABLE_ID_DIR` resolve relative to
   the **current working directory**, so the commands above must be run with CWD = `preprocess/`
   (with `--output_dir ../../checkpoints/tf_metazoa_finetuned/vocabs`) or the manifest must be
   staged at the CWD; as written from the repo root they fail to find the manifest.

## 4. Pre-generated ESM-2 embeddings for sus_scrofa / xenopus_tropicalis — provenance

Source of record (found in this repo, verified against the live bucket):
- `src/transcriptformer/datasets.py::download_all_embeddings` downloads
  **`s3://czi-transcriptformer/weights/all_embeddings.tar.gz`** (public, unsigned) via
  `transcriptformer download all-embeddings`; the README's 24-species table lists *Sus scrofa*
  and *Xenopus tropicalis* (and *Macaca mulatta*, but NOT *M. fascicularis* — consistent with
  register 8.1).
- Candidate URL (HTTP 200 verified 2026-09-23):
  `https://czi-transcriptformer.s3.amazonaws.com/weights/all_embeddings.tar.gz`
  **Content-Length 4,771,779,019 B (4.77 GB)** — over the 500 MB download cap, **not downloaded**.
  Last-Modified 2025-04-10. Sibling keys: `weights/tf_metazoa.tar.gz` (6,341,673,215 B),
  `weights/tf_exemplar.tar.gz` (4,102,873,511 B), `weights/tf_sapiens.tar.gz` (1,819,975,447 B).
- Caveat: the tarball is a single 4.77 GB bundle (no per-species files in the bucket); pig/frog
  embeddings inside are expected to carry Ensembl stable-ID keys (ENSSSCG/ENSXETG) from the same
  `protein_embedding.py` pipeline. Pig `var_names` (ENSSSCG) will join; **xenopus `var_names`
  (gene symbols) will not** without a symbol→ENSXETG map.
- Zenodo/Figshare/HuggingFace mirrors: not established — web search was unavailable this session
  (repeated "Web search cancelled"); repo docs (README, ADR 0002) and register 8.1 reference only
  the S3 route and the M. mulatta embeddings. Re-check mirrors before any manual download.

## 5. Precise remaining blockers for B4 (fresh report: `runs/probe_readiness.json`, exit 1)

1. **All six species vocabularies absent** at `checkpoints/tf_metazoa_finetuned/vocabs/<key>_gene.h5`
   — i.e. §3 has not been run (blocked on defects 1-3 above).
2. **Key-namespace mismatches** (not checked by the validator): macaque symbol/LOC var vs ENSMFAG
   keys (all 3 macaque files), ciona KH2012 var vs NP/XP keys, amphioxus LOC var vs XP/XP keys,
   xenopus symbol var vs ENSXETG keys (also for the pre-generated embeddings). Guinea pig matches
   at the gene-ID level (strip `:symbol`); pig matches.
3. **macaque_zhai_2022 has no species column in obs** → "explicit source identity" blocker is
   unresolvable read-only (README/Zhai 2022 provenance recorded).
4. **Assay blockers remain on 7/8 datasets** (all but xenopus): no obs assay column; documented
   constants + citations recorded in `metadata_provenance`, but the validator requires columns.
5. **Embryo identity unavailable by design** for macaque_spatial (sections only), pig, xenopus,
   ciona, amphioxus (documented embryo pooling) — recorded with precise reasons. The gong
   embryo_id resolution rests on GEO "cell type: Embryo" per GSM (embryo count per library not
   explicitly documented) — flagged for collaborator confirmation; the zhai resolution rests on
   the paper's "six embryos" (E26-E1 + E26-Y1 = one embryo, two tissue libraries — figure-legend
   reading flagged).
6. Scope note unchanged: the readiness report validates obs labels/asset presence only — gene
   coverage, phase-boundary sensitivity and spatial metrics remain unvalidated.
