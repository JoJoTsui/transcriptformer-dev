# Ciona KH2012 protein-to-probe bridge

The Ciona Cao 2019 probe uses `KH2012:KH.<scaffold>.<gene>` keys, while the
NCBI protein FASTA in `preprocess/fasta_manifest_pep.json` carries NP/XP
accessions. Ghost publishes the [KH gene models version 2012 protein ZIP](https://ghost.zool.kyoto-u.ac.jp/download_kh.html)
for this historical key space. The site lists the archive as last updated in
2011 and asks users to cite Ghost and its publications; it prohibits
redistributing downloaded resources without permission. Keep both the ZIP and
the derived protein FASTA outside this repository.

`scripts/normalize_ciona_ghost_kh2012.py` reads a locally supplied copy of
`KH.KHGene.2012.Longest.protein.zip`. It accepts exactly its one expected FASTA
member, checks the audited archive SHA-256, and streams it under a 64 MiB
uncompressed cap. Every full model ID must match
`KH.<scaffold>.<gene>.v<version>.<model>` and be unique. The script writes the
gene key `KH2012:KH.<scaffold>.<gene>` as the first token for **every** model,
then appends `protein=<full-model-ID>` to keep the complete FASTA labels
unique as required by ESM's FASTA loader. The generator groups by the first
token for its per-gene mean. It rejects malformed
headers, empty proteins and unsupported sequence characters. Ghost's `+`
character is replaced with the ESM unknown amino acid `X`, with counts and
the normalized FASTA hash in a JSON audit. The meaning of `+` in Ghost's
translation is not established here; downstream sensitivity to this
replacement remains an analysis limit.

The script opens only `var/_index` in the local H5AD, caps it at 100,000 keys,
rejects duplicate or malformed KH keys, and requires every KH probe key to
appear among the protein gene roots. It does **not** claim that all protein
isoforms are biologically equivalent or that the 41 non-KH probe features have
an ESM embedding.

To reproduce the bounded audit without creating a FASTA:

```bash
.venv/bin/python scripts/normalize_ciona_ghost_kh2012.py \
  --source-zip /tmp/KH.KHGene.2012.Longest.protein.zip \
  --probe-h5ad '/mnt/d/sc/data/scRNAseq-YBY/h5ad/海鞘_Ciona_intestinalis/海鞘_Ciona_intestinalis__Comprehensive single cell transcriptome lineages of a proto-vertebrate.h5ad' \
  --report /tmp/ciona_ghost_kh2012_audit.json
```

For a future embedding run, regenerate with
`--output-fasta /tmp/ciona_kh2012_gene_unique.fa` and
`--report /tmp/ciona_kh2012_gene_unique_audit.json`, then pass the three local
inputs to the generator:

```bash
.venv/bin/python preprocess/protein_embedding.py \
  --organism_key ciona_intestinalis \
  --input_gene_fasta /tmp/ciona_kh2012_gene_unique.fa \
  --input_gene_audit /tmp/ciona_kh2012_gene_unique_audit.json \
  --input_source_archive /tmp/KH.KHGene.2012.Longest.protein.zip \
  --max_tokens 2048 \
  --output_dir checkpoints/tf_metazoa_finetuned/vocabs
```

The generator verifies the source archive and normalized FASTA hashes and
organism before loading ESM. **This invocation has not been run.** The source
ZIP must be acquired from Ghost by each user under its terms. The normalizer
refuses to put the derived FASTA under the repository root.

The 2026-09-29 audit of the local probe and the 5,230,945-byte Ghost ZIP
(SHA-256 `91ae06cfab8010664f3d6a9a9ee18dff0375eb1cd581617f0988e59002b4d22a`)
found:

| Measure | Result |
| --- | ---: |
| Unique protein model headers | 54,733 / 54,733 |
| KH gene roots | 15,285 |
| KH probe keys joined | 15,228 / 15,228 |
| Other probe keys | 39 ENSCING, 2 constructs |
| Gene roots with multiple models | 8,908 (maximum 154) |
| Gene roots absent from probe | 57 |
| `+` residues replaced by `X` | 1,356 in 1,356 models |
| Probe KH key SHA-256, sorted newline-delimited | `a307c7692e57bb92aa6762a6d4452c1d71181282a5a9ddcb595472e23e7920b5` |
| Normalized FASTA SHA-256 | `659bcef8663b9305482a95784b0a0839b22130d96faaca53e9616d8f911ffb2b` |

This closes the deterministic identifier/header and probe-key join step for
the audited source. Embedding generation, vocabulary publication, the 41
non-KH features, assay/resource gates, and any actual B4 score remain open.
