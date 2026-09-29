# 04 — Validate actual ortholog joins and reconcile chicken identifiers

Category: correctness and readiness
Status: Strict partial chicken bridge implemented; exact checkpoint release and full repair pending
Priority: P1
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: none
Traceability: R2; register 4.3; tracker N
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Retain real identifier sets through ortholog preparation and compute usable joins on both species. Investigate the observed chicken namespace mismatch using authoritative, provenance-bearing mappings.

## Acceptance Criteria

- [x] A table whose gene counts look plausible but whose keys do not match the vocabulary reports zero usable coverage, never the raw-count percentage.
- [x] Validate keys on both sides and retain counts for raw pairs, joined pairs, ambiguous mappings and unresolved identifiers.
- [x] Audit the existing chicken vocabulary against the retained ortholog table, recording the observed zero-join case before any correction.
- [x] Where a defensible unambiguous mapping exists, record source/release/assembly provenance and demonstrate actual joined genes. Exclude ambiguous or missing mappings without guessing aliases.
- [x] Do not silently change species, release or assembly; preserve source assets and produce inspectable derived mapping/report artifacts.
- [x] If mapping evidence is unavailable, complete accurate validation/reporting but explicitly leave the chicken asset repair and R2 unresolved. Do not mark usable mapping complete from a zero-coverage report.

## Testing Seam

Use the ortholog preparation/report boundary with offline mapping fixtures, same-sized disjoint gene sets, duplicate aliases and one-to-many cases. Add a bounded read-only check against local chicken keys when available.

## Constraints and Completion Limits

Targeted source retrieval may be needed during future implementation. Mapping availability is an external completion gate; large asset rebuilds are outside the WSL work budget.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: The offline join audit reports zero usable human–chicken pairs out of 12,166 finalized pairs against 16,878 chicken vocabulary keys. No authoritative identifier conversion is available. Mapping repair remains open; the shipped source table is preserved.

2026-09-28 follow-up: A bounded local audit found 13,145 distinct
`ENSGALG000100` chicken IDs in the finalized table and 16,878
`ENSGALG000000` checkpoint keys, with zero intersection. The checkpoint
vocabulary carries no source release or assembly metadata; cached BioMart
queries contain current IDs but no old-to-current conversion. The exact
required Ensembl history export, provenance fields, ambiguity exclusions and
post-mapping audit are recorded in
[the ortholog eligibility report](../../../docs/ortholog-eligibility-report.md#chicken-reconciliation-evidence-needed).
The chicken asset repair is still blocked on that evidence.

Primary-source follow-up on 2026-09-28: Ensembl announced the GRCg6a-to-GRCg7b
reference switch at release 107 and still serves `ENSGALG000000…` genes on
the separate GRCg6a assembly. This supports, but does not prove for the exact
checkpoint, an assembly mismatch. The checkpoint vocabulary/config has no
source release or assembly metadata, and no authoritative one-to-one
cross-assembly conversion was obtained. The cited
[investigation](../../../docs/agents/chicken-identifier-provenance-2026-09-28.md)
sets out the evidence required to close R2. Zero usable chicken joins remain.

Further bounded work on 2026-09-28 established that the checkpoint chicken IDs
exactly match the selected GRCg6a genes in archived Ensembl releases 99, 100,
101 and 106, without distinguishing the producer's exact release. A strict
NCBI GeneID and shared unversioned `DIRECT` RefSeq accession bridge supplies 7,267
unambiguous release-110-to-checkpoint pairs. The optional
[join report](../../../docs/ortholog-eligibility-chicken-geneid-bridge.json)
shows 6,129 usable human–chicken pairs out of 12,166 raw pairs. The
[mapping TSV](../../../preprocess/orthologs/chicken_ncbi_geneid_bridge_r110_to_r106.tsv),
[builder](../../../scripts/build_chicken_geneid_bridge.py), and
[source audit](../../../docs/chicken-geneid-bridge-audit.json) preserve row-level
evidence and hashes. The 9,611 remaining checkpoint genes are unresolved;
the producer's exact annotation release and scientific review remain open.
R2 is not closed by this partial genome-wide join.

Article/code follow-up on 2026-09-29: The author preprint says pretraining and
evaluation gene features were updated to Ensembl v113, and the later public
preprocessing manifest points chicken to release-113 GRCg7b. Neither is bound
to the released chicken HDF5, whose old-prefix genes match GRCg6a archives.
Ensembl also publishes GRCg6a as a release-113 alternative assembly, so the
paper's release number and the old-ID namespace can coexist. Its official
peptide FASTA contains only 14,204 of the 16,878 checkpoint keys, however:
2,674 checkpoint genes are missing and 2,873 extra genes appear. This rules
out a direct unfiltered build from that particular release-113 FASTA.
The initial public repository's `test/data/chicken_val.h5ad` contains all
16,878 checkpoint chicken keys in the same old namespace. A bounded audit of
official release-99/100/101/106 GRCg6a peptide FASTAs found identical
per-gene protein-sequence multisets across all four; even sequence-based
fingerprinting cannot select one exact release. See the
[provenance follow-up](../../../docs/agents/chicken-identifier-provenance-2026-09-28.md#article-code-and-peptide-follow-up--2026-09-29).
The exact source now requires a producer build manifest/log or artifact record
tied to the HDF5 hash. Release 106 remains a reference mapping release only.

Published-table follow-up on 2026-09-29: A [primary chicken annotation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10951430/)
provides GRCg6a-to-GRCg7b correspondences in Supplementary Table 12. The
[bounded audit](../../../docs/agents/chicken-online-followup-2026-09-29.md)
compared its direct Ensembl-ID rows with the exact checkpoint HDF5 and the
current strict bridge. Of 224 unique-in-that-subset checkpoint candidate rows,
40 overlap the bridge and **37 conflict**; only 28 other candidates have a
local ortholog-table join. Row coordinates and both conflicting IDs are in
the [candidate report](../../../docs/chicken-published-table12-candidates.tsv),
with source hashes in the [audit summary](../../../docs/chicken-published-table12-audit.json).
No candidate was applied; the 7,267-pair accepted bridge and R2 state remain
unchanged. Resolve the conflicting gene identities and producer provenance
before accepting another mapping layer.

Independent-core follow-up on 2026-09-29: the [row-level conflict review](../../../docs/agents/chicken-conflict-review-2026-09-29.md)
checked all 37 conflicts and all 28 additional ortholog candidates against
the archived release-106/110 Ensembl core xrefs. None meets the existing
unique-GeneID plus same-direct-RefSeq rule. All 37 conflicting published
targets lack a release-110 GeneID xref; the current bridge targets retain
both independent evidence types. Three of the 28 additions share a GeneID
but fail the RefSeq requirement. R2 remains open without a mapping change.

A [three-candidate protein/exon follow-up](../../../docs/agents/chicken-three-candidates-2026-09-29.md)
found a unique shared GeneID-linked gene per archived core for all three,
an exact 247-residue FBXO2 peptide match, near-identical KXD1 peptides and
substantial SH3BP1 exon/protein continuity. The current REST records are not
frozen release histories; possible competing genes without a GeneID xref and
the checkpoint's exact source remain unresolved. No mapping was added.

The [closure-evidence memo](../../../docs/agents/chicken-closure-gate-2026-09-29.md)
shows why the checkpoint gene/protein content cannot distinguish GRCg6a
releases 99/100/101/106, lists the exact producer-bound manifest fields needed
for a source-release claim, and states the separate row-level evidence needed
to expand the 7,267-pair bridge. It includes a ready-to-send producer request;
no external message was sent. Ticket 04's implementation acceptance criteria
above are met for the scoped partial bridge, while the R2 scientific and
provenance gate remains open.
