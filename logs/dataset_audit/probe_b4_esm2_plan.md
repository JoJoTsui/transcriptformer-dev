# Probe B4 unblock — asset/metadata audit, ESM-2 generation plan (NOT run), remaining blockers

Date: 2026-09-23. Read-only audit of the 8 probe H5ADs (obs/var metadata via h5py only; no
expression loaded, no source file modified). Companion to `preprocess/probe_stage_mappings.json`
(`metadata_provenance`, `fasta_provenance`) and `runs/probe_readiness.json`.
ESM-2 was **not** run; this file is documentation only.

2026-09-29 host check: `free -h` reports 31 GiB RAM and 8 GiB swap; the
repository volume has 415 GiB free. `nvidia-smi` cannot initialize NVML
because GPU access is blocked by the operating system in this WSL session.
These observations are a point-in-time resource check, not an accelerator
budget or permission to schedule embedding generation.

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
| ciona_intestinalis | NCBI `GCF_000224145.3_KH_protein.faa.gz` | 6,803,777 | 21,096 | n/a | **no** | **MISMATCH** for the current NCBI source: var = `KH2012:KH.C1.*` (15,228/15,269) + 39 ENSCING + 2 constructs; NCBI keys are NP/XP accessions. A separate Ghost KH2012 source has complete KH gene-root coverage, audited below. |
| branchiostoma_floridae | NCBI `GCF_000003815.2_Bfl_VNyyK_protein.faa.gz` | 10,031,501 | 43,041 | n/a (6,274 LOC tags in descriptions) | **no** | **PARTIAL** — var = `LOC1184xxxxx` from this same assembly (Markos 2024 quantified GCA_000003815.2); 6,273/29,726 var genes appear as description tokens, but `protein_embedding.py` would key by XP/NP accessions. GCF_000003815.1 (JGI) uses `BRAFLDRAFT_*` protein-model IDs — wrong namespace. |

Consequence: `record.description.split("gene:")` yields **protein accessions** (not gene IDs) for
the two NCBI files, so even after generation the vocab keys would not join to `var_names` without
a header rewrite or mapping table (not done). For xenopus the *existing* manifest entry has the
same problem in reverse: pre-generated ENSXETG keys vs var gene symbols.

2026-09-29 bounded Ciona follow-up: Ghost's [official download page](https://ghost.zool.kyoto-u.ac.jp/download_kh.html)
provides `KH.KHGene.2012.Longest.protein.zip` and KH2012 GFF3. The 5,230,945-byte
ZIP was retrieved to `/tmp` only (SHA-256
`91ae06cfab8010664f3d6a9a9ee18dff0375eb1cd581617f0988e59002b4d22a`).
Streaming its FASTA headers gives 54,733 protein records and 15,285 unique
gene roots when the first three dot-delimited fields of each `KH.C1.1.v1…`
identifier are treated as the KH gene ID. Those roots match **all 15,228 of
15,228** local probe `KH2012:` gene keys (SHA-256 of sorted UTF-8 keys with
one newline after each key:
`a307c7692e57bb92aa6762a6d4452c1d71181282a5a9ddcb595472e23e7920b5`);
the other 41 probe keys are 39
ENSCING IDs and two constructs. This verifies a candidate identifier bridge,
not the biological equivalence of every protein isoform or a generated vocab.
Of the 15,285 roots, 8,908 have multiple protein records (maximum 154), so a
deterministic, documented per-gene aggregation rule is needed before embedding
generation. The author preprint specifies averaging protein embeddings per
gene, and the local generator now retains multiple isoforms for that mean;
this has not been verified on Ghost data. The current generator does not read
ZIP and would not add the `KH2012:` prefix. Keep the raw Ghost ZIP outside the repository,
attribute the source, and do not redistribute its files without permission
under the page's stated terms. No expression matrix was opened.

For amphioxus, the [NCBI GFF3
specification](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/)
documents `protein_id` and parent/GeneID relationships. A same-assembly
protein-to-gene bridge using those fields or [NCBI gene product reports](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/data-reports/gene-product/)
is a better candidate than parsing free-text `LOC` tokens; reject ambiguous
relationships and audit probe joins. A [same-assembly RefSeq bridge](../../docs/agents/amphioxus-protein-bridge-2026-09-29.md)
now maps every one of 43,041 proteins to an unambiguous GeneID and gene Name;
26,676/29,726 local probe keys have protein input. The remaining 3,050 do not
have an accepted protein in this release. Its gene-key FASTA adapter and any
ESM output remain separate steps.

A [Ghost KH2012 normalization audit](../../docs/agents/ciona-ghost-bridge-2026-09-29.md)
now writes an external gene-key FASTA with unique protein labels and verifies
the 15,228 KH probe-key joins. The embedding generator accepts a local FASTA
only with its audit JSON and raw source archive, and checks the organism and
both byte hashes before loading ESM. This does not represent the 41 non-KH
features or establish a safe GPU budget.

Pinned [same-release Ensembl symbol bridges](../../docs/agents/b4-macaque-xenopus-symbol-bridges-2026-09-29.md)
offer candidate joins for the three macaque probes (12,613/26,135;
14,202/33,960; 3,263/4,663) and Xenopus (9,485/26,550). They exclude
ambiguous symbols and enforce one-to-one stable-ID targets. Actual ESM/vocab
release joins remain unverified, and the many unmatched LOC/JGI keys need a
source-specific ruling before any B4 metric is interpreted.
The [vocabulary-key audit](../../docs/agents/b4-vocabulary-join-audit-2026-09-29.md)
also excludes 207 pig `GEO_GSE236766_unresolved_row_*` placeholders from its
19,236 ENSSSCG direct-key candidates. All six configured B4 vocabularies are
currently absent, so actual joins are unmeasured.

Validator caveats (expected, captured in the report): the URL-substring check flags
"FASTA reference does not identify ciona_intestinalis / branchiostoma_floridae" because NCBI URLs
carry assembly accessions; species identity was verified from NCBI assembly records and the
`[Ciona intestinalis]` / `[Branchiostoma floridae]` organism field of every FASTA header.
macaque_zhai_2022 keeps its "Missing species metadata: species" blocker (obs has no species
column; README + Zhai 2022 identify M. fascicularis; not fabricatable read-only).

## 3. ESM-2 generation plan (document only — do NOT run until data joins and dependencies are resolved)

The Ensembl-header commands below are candidates after installing fair-esm and
biopython and measuring accelerator headroom. The Ciona and amphioxus NCBI
headers lack `gene:` and cannot be passed through this direct path; use the
audited external FASTA commands in the [Ciona](../../docs/agents/ciona-ghost-bridge-2026-09-29.md)
and [amphioxus](../../docs/agents/amphioxus-protein-bridge-2026-09-29.md)
bridge notes instead. No command in this section has run.

```bash
.venv/bin/python preprocess/protein_embedding.py --organism_key macaca_fascicularis   --max_tokens 2048 --output_dir checkpoints/tf_metazoa_finetuned/vocabs
.venv/bin/python preprocess/protein_embedding.py --organism_key cavia_porcellus       --max_tokens 2048 --output_dir checkpoints/tf_metazoa_finetuned/vocabs
```

Size/time estimates (stream-counted from the verified FASTAs; esm2_t36_3B_UR50D on the single
RTX 3090 24 GB; assume 1,000-3,000 residues/s with token-budget batching):

| key | proteins | genes | total residues | est. GPU time | output h5 (2560-d f32) |
|---|---|---|---|---|---|
| macaca_fascicularis | 49,919 | 22,504 | 27.1 M | 2.5-7.5 h | ~230 MB |
| cavia_porcellus | 25,582 | 18,095 | 14.4 M | 1.3-4 h | ~185 MB |
| ciona_intestinalis | 21,096 | 21,096* | 13.5 M | 1.2-3.8 h | ~216 MB |
| branchiostoma_floridae | 43,041 | 43,041* | 28.3 M | 2.6-7.9 h | ~441 MB |

*no `gene:` tags → the current generator rejects these sources until a verified
protein-to-gene bridge is supplied; the displayed gene/output estimates are
historical accession-key estimates, not a runnable plan. Add ~2.5 GB one-off ESM-2 3B
checkpoint download. Sequences longer than 1,022 residues are truncated (`seq_length=1022`).
The generator now defaults to 2,048 tokens per inference batch; this is a starting limit,
not a measured safe value for the RTX 3090. Batch accounting includes the
ESM-2 beginning/end tokens and rejects a sequence whose truncated token count
could exceed the budget; longer raw proteins are still truncated at 1,022
residues. Pooling uses encoded residue counts, so replacement of a stop
symbol by the ESM `<unk>` token cannot include end/padding tokens in the mean.
These rules follow the [official ESM batching and alphabet source](https://github.com/facebookresearch/esm/blob/main/esm/data.py)
and [ESM-2 model loader](https://github.com/facebookresearch/esm/blob/main/esm/pretrained.py).
Probe VRAM with a small job before any proteome run.
Each completed batch is stored once in `<output>.parts/batch_*.h5`. The run manifest fixes
the source URL and SHA-256, optional local normalization audit SHA-256,
normalized FASTA SHA-256, model checkpoint SHA-256, ESM version,
layer, sequence length, token budget, and batch count. Resume skips only chunks with matching
identity, batch index, gene labels, shape and content checksum. Per-gene protein means are assembled from chunks via
an on-disk HDF5 sum/count file; the final `keys`/`arrays` HDF5 is atomically published only
after all genes have values. Chunk and aggregate files temporarily increase disk use; completed
chunks are retained for inspection and reruns. Changing an input or parameter requires a new
output path or deliberate removal of the old partial directory. No ESM job has been run.

Crash/replay invariant: the manifest is written before inference; each batch writes
`batch_N.h5.tmp` and renames it to `batch_N.h5` only after its HDF5 file closes. On restart,
the generator recomputes the source, normalized FASTA, model and parameter identity and
rejects any manifest mismatch. It skips a batch only when the completed chunk's identity,
index, labels, shape and SHA-256 content checksum match the freshly reconstructed batch. It validates **every** chunk
again before aggregation. Aggregate and final temporary files can be rebuilt after a process
crash; only a closed, complete final file is renamed to the requested `.h5`. No partial `.h5`
is advertised as a vocab. A power failure or underlying filesystem corruption still requires
manual inspection of the affected chunk and source cache.

Known limits of `preprocess/protein_embedding.py` (CPU guard, path resolution,
bounded batch output and resume were repaired on 2026-09-29):
1. **`fair-esm`/`esm` is NOT installed in `.venv`** (verified `ModuleNotFoundError: No module
   named 'esm'`; `Bio`/biopython is also missing and imported at module top) — the script cannot
   even import today.
2. **CUDA remains required.** The model forward, pooling and accumulation occur
   only on the CUDA path. A CPU invocation now fails before writing an output,
   preventing the former silent empty `keys`/`arrays` HDF5 result. CPU inference
   itself has not been implemented.
3. **Inference still needs a measured VRAM budget.** The default is capped at 2,048 tokens,
   but the 3B model has not been loaded on this host for this plan. HDF5 chunk publication
   prevents a partial final vocab after a process crash and avoids the former growing pickle.
   A machine or filesystem crash can still damage an HDF5 chunk; resume rejects it for review.
4. **Resolved path footgun:** the FASTA manifest and stable-ID cache now resolve
   relative to `preprocess/protein_embedding.py`, independent of the invocation
   directory. The downloaded source FASTA is preserved; a separate normalized gene-key
   FASTA is generated atomically. Missing `gene:` tags now fail explicitly, so the
   Ciona and amphioxus NCBI sources cannot silently produce protein-accession
   vocabularies. `--output_dir` still resolves from the caller's working directory.
5. **Protein aggregation discrepancy (code adjusted, not run):** the [TranscriptFormer author preprint,
   Methods 1.4](https://www.biorxiv.org/content/10.1101/2025.04.25.650731v1)
   describes averaging ESM-2 protein embeddings when a gene has multiple
   proteins. The public generator had dropped every protein after the first
   encountered `gene_id` while rewriting FASTA (`seen_names`), before its
   existing accumulation/mean step. The local script now retains all protein
   records for that step; no embedding job or runtime validation was run. The
   Ghost audit found 8,908 Ciona gene roots with multiple protein records.
   Resolve the Ghost header-to-gene rewrite, gene-namespace joins and assay
   resource plan before generating new B4 assets.

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

2026-09-29 public-bucket listing (`aws s3 ls
s3://czi-transcriptformer/weights/ --no-sign-request`) returned only
`all_embeddings.tar.gz` and three multi-gigabyte checkpoint archives under
`weights/`; no per-species pig or Xenopus embedding object is exposed there.
The bundled archive still requires a separate transfer/resource decision.
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
   keys (all 3 macaque files), Ciona KH2012 var vs current NCBI NP/XP keys,
   amphioxus LOC var vs XP/NP keys, Xenopus symbol var vs ENSXETG keys (also
   for the pre-generated embeddings). The separately audited Ghost KH2012
   header roots cover all KH2012 probe keys, but no compatible vocab exists.
   Guinea pig matches at the gene-ID level (strip `:symbol`); pig matches.
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
