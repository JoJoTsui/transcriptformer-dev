# Amphioxus same-assembly protein-to-gene bridge

The exact RefSeq `GCF_000003815.2_Bfl_VNyyK` protein FASTA and genomic GFF3
provide an explicit bridge from every FASTA protein accession to one NCBI
GeneID and one gene `Name`. The GFF3 header identifies *Branchiostoma
floridae*, assembly `GCF_000003815.2`, and Annotation Release 100. [NCBI's GFF3
specification](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/)
defines the `protein_id` attribute and `Dbxref=GeneID` relationship used here.
The bridge uses `CDS.protein_id → CDS.Dbxref GeneID → gene.Dbxref GeneID →
gene.Name`; it never guesses from free-text protein descriptions.

The pinned sources are the [protein FASTA](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/003/815/GCF_000003815.2_Bfl_VNyyK/GCF_000003815.2_Bfl_VNyyK_protein.faa.gz)
(SHA-256 `de341da4441b5d120437e23242b794f46e9f4aaf49d2f1b465abcd4388aacd89`)
and [genomic GFF3](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/003/815/GCF_000003815.2_Bfl_VNyyK/GCF_000003815.2_Bfl_VNyyK_genomic.gff.gz)
(SHA-256 `df14aad495f14c4fda6b6e210ebc510839034d0785f92cc26e4b264907e42eb6`).
Compressed sizes are 10.0 MB and 13.5 MB. The downloaded sources were kept in
`/tmp`, outside the repository.

The reproducible tool is [build_amphioxus_protein_bridge.py](../../scripts/build_amphioxus_protein_bridge.py).
It verifies source hashes, exact assembly and annotation release, species in
every FASTA header, complete accession agreement, unique GeneID assignments,
and unique protein-bearing gene names. It reads only `var` keys from the local
Markos 2024 H5AD; it does not load an expression matrix. It writes a
deterministic compressed [bridge](../../preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz)
and [manifest](../../preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz.json).
The checked bridge has 43,041 protein rows and 26,689 protein-bearing gene keys.

| Local Markos probe keys | Count |
|---|---:|
| All unique `var` keys | 29,726 |
| Exact gene-key match with a FASTA protein | 26,676 (89.74%) |
| Present in the GFF3 gene annotation, without a FASTA protein | 2,672 |
| Absent from the GFF3 gene annotation | 378 |

The probe file SHA-256 is
`4123e437126222591c6d99382af72ef1f5a5aca0e09d426d92df44c756af8c6c`.
The bridge SHA-256 is
`2695e59c5c5774db9a88ca46f9655058f0b16f8250a01a25c4be4169bc9286dd`.
The 3,050 uncovered keys have **no accepted protein embedding input from this
release**. They must not be silently assigned a similarly named protein or
treated as zero expression. The 378 absent keys need source-annotation
reconciliation if a larger probe join is required. The 2,672 GFF3 genes
without a protein may include noncoding genes; no protein representation is
asserted for them.

To reproduce with local sources and the same probe H5AD:

```bash
.venv/bin/python scripts/build_amphioxus_protein_bridge.py \
  --gff /tmp/GCF_000003815.2_Bfl_VNyyK_genomic.gff.gz \
  --fasta /tmp/GCF_000003815.2_Bfl_VNyyK_protein.faa.gz \
  --probe-h5ad '/mnt/d/sc/data/scRNAseq-YBY/h5ad/佛罗里达文昌鱼_Branchiostoma_floridae/佛罗里达文昌鱼_Branchiostoma_floridae__Cell type and regulatory analysis in amphioxus illuminates evolutionary origin of the vertebrate head.h5ad' \
  --output preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz
```

The [local FASTA normalizer](../../scripts/normalize_amphioxus_refseq.py) then
verifies the pinned compressed FASTA and committed bridge hashes, streams each
protein to a `>gene_key protein=<accession.version>` header, preserves the
source sequence, and writes both derived files outside the repository. The
gene key is the first header token; the full RefSeq accession makes every
protein label distinct while retaining all isoforms for per-gene averaging.
For the audited source, it produced 43,041 records, 26,689 gene keys, and a
30,266,593-byte FASTA with SHA-256
`e5257bc244c7f8f97db7e4c18556933f1b24b85f46e329de7cf0c473af2d439a`.
The raw FASTA archive remains unchanged.

```bash
.venv/bin/python scripts/normalize_amphioxus_refseq.py \
  --source-fasta /tmp/GCF_000003815.2_Bfl_VNyyK_protein.faa.gz \
  --bridge preprocess/gene_mappings/amphioxus_protein_bridge.tsv.gz \
  --output-fasta /tmp/branchiostoma_floridae_gene_key.fasta \
  --report /tmp/branchiostoma_floridae_gene_key.audit.json
```

The audit contains `schema_version: 1`, `organism_key:
branchiostoma_floridae`, `normalized_fasta_sha256`,
`source_archive_sha256` (the compressed FASTA hash), and an HTTPS
`source_page`. These are the fields checked by the generator's local-input
path. Once the project dependencies and measured GPU budget are ready, its
input command is:

```bash
.venv/bin/python preprocess/protein_embedding.py \
  --organism_key branchiostoma_floridae --max_tokens 2048 \
  --input_gene_fasta /tmp/branchiostoma_floridae_gene_key.fasta \
  --input_gene_audit /tmp/branchiostoma_floridae_gene_key.audit.json \
  --input_source_archive /tmp/GCF_000003815.2_Bfl_VNyyK_protein.faa.gz \
  --output_dir checkpoints/tf_metazoa_finetuned/vocabs
```

This resolves the row-level protein-to-gene mapping and generator input gates
for the covered keys. Embeddings and a probe vocabulary have not been
generated. The same-assembly GFF3 join does not establish orthology or a
measured VRAM budget for the WSL host.
