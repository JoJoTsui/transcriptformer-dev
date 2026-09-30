# Ticket 12 scientific and production gate research — 2026-09-30

Scope: non-zebrafish continuation, repository inspection and primary online
sources. No checkpoint tensors, expression corpus, GPU job or download was
loaded. This is a requirements/evidence audit; it freezes no new threshold.

## Ticket contract and current evidence

[Ticket 12](../../.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md)
already checks all seven of its own bounded engineering acceptance criteria.
Its previously open status came from a dependency/evidence interpretation,
primarily ticket 05’s observed comparison, rather than an unimplemented CI feature.
The scope audit now closes this bounded engineering ticket while explicitly
retaining ticket 05 and the wider scientific/project gates.
The [repair record](implementation-repairs-2026-09-30.md) records 479 remote
CPU tests and passing change-scoped pre-commit. Neither proves project model
performance. The ticket expressly requires no full-corpus, GPU or embedding
run for its bounded verification and prohibits automatic scientific sign-off.

The broader project readiness inventory must therefore be distinguished from
this ticket's bounded acceptance. It is not accurate to describe every open
biological decision as missing ticket-12 implementation.

## Repository requirements, in dependency order

| Gate | Existing authoritative requirement | Evidence still needed / next action |
| --- | --- | --- |
| Corpus decisions | [Owner corpus defaults](corpus-defaults-adoption-2026-09-30.md): exclude prenatal atlas, retain TOME E8.5b, conditionally include Nature2019, retain sampler and unstaged training observations. | Those approvals already exist. Nature2019 remains conditional; source physical independence, assay-specific non-UMI QC and labels cannot be inferred from identifier noncollision. Preserve exclusion until suitability evidence passes. |
| QC and preparation | [Readiness guide](../finetune-readiness-tools.md), [spec](../../.scratch/multispecies-readiness-remediation/spec.md): validate exact coordinate-derived manifest and prepared artifact hashes/membership. | Freeze source-specific QC/assay policy; prepare full selected corpus on suitable host; run `validate_prepared_artifacts.py` and prepared-mode `report_holdout_coverage.py`. The 27-source bounded rehearsal is not full preparation. |
| B1 holdout | [Owner B1-A decision](b1-owner-decision-2026-09-30.md) explicitly approves the 5% improvement / 2% deterioration limits and embryo-first analysis. | Freeze surviving independent embryos and phase strata after QC, before inspecting results. Mouse strata need at least three embryos; human endpoint remains descriptive. Old unsigned/six-species wording elsewhere is historical. |
| Reference/forgetting | [Design §4](../perturbation-and-baseline-design.md), [reference inventory](forgetting-reference-inventory-2026-09-29.md). | Freeze dated Census adult human/mouse references and locate sponge/yeast canaries; preserve source, cell identities, exclusions and hashes. Public availability does not supply a selected frozen project reference. |
| Runtime/model | [Ticket 12 constraints](../../.scratch/multispecies-readiness-remediation/issues/12-readiness-evidence-and-ci.md), [ADR 0004](../adr/0004-multispecies-checkpoint-selection.md). | Verify base and nominal finetuned asset paths independently, including byte identity and training provenance; a directory named finetuned is not proof of model adaptation. Selected-weight, baseline/selection/resume and accelerator evidence remain separate. Check live resources before execution; CPU fixture CI is sufficient only for bounded software acceptance. |
| B2 | [Design §3](../perturbation-and-baseline-design.md), `scripts/compare_representations.py`. | Real paired base/finetuned embeddings on identical eligible holdout cells and frozen cohort identity; no verdict from synthetic geometry. The draft 5-point purity criterion has no new approval from this research. |
| B3 / ticket 05 | [Approved paired rule](b3-paired-comparison-decision-proposal-2026-09-30.md), [score definition](b3-deletion-score-decision-2026-09-30.md), [approved descriptive null](b3-null-method-review-2026-09-30.md). | Produce actual hash-bound full score tables and audit via `produce_b3_scores.py`, then handoff, full-universe comparison, coverage TSV and rank SVG. Freeze actual species/phase membership and family. Preserve 500-pair/80% reporting floor; bootstrap is conditional on five independent embryos per side. Finetuned arm is required for base-versus-finetune claims, but a genuine base-arm species-pair comparison is distinct evidence. |
| B3 inferential/external verdict | [Design §§1–3](../perturbation-and-baseline-design.md), amended by the approved null note. | Per-gene p-values/FDR remain explicitly unevaluable pending sample-unit/calibration approval. Freeze phenotype sets, tested genes, positive/negative rules and external verdict before viewing rankings. The draft AUROC tolerance is not approved by discovering a public screen. |
| B4 | [Probe audit](b4-vocabulary-join-audit-2026-09-29.md), `scripts/validate_probes.py` and `scripts/audit_probe_vocab_joins.py`. | Obtain exact-species vocabularies/ESM2 embeddings, verify identifier joins and metadata, preserve phase-boundary sensitivity, then generate real matched probe embeddings. Existing FASTA provenance is not a completed vocabulary or B4 result. |

Ticket 11 remains excluded by owner instruction. Its dependency cannot be
silently marked completed. Ticket 12 expressly permits dependency completion
with documented unresolved external evidence where the preceding ticket
permits partial tooling delivery. Thus its own bounded engineering scope can
be closed with explicit exclusion and unresolved evidence if that rule is
applied consistently. Wider scientific outcomes and production runs are not
additional ticket-12 acceptance tests: its contract says none is needed. The
currently explicit ticket-05 observed-comparison acceptance remains open and
must either be met or retained as an unresolved dependency; it cannot be
erased by relabeling synthetic CI as observed results.

## What the TranscriptFormer sources establish

The [first-party model card](https://virtualcellmodels.cziscience.com/model/transcriptformer)
identifies Metazoa as the broad twelve-species model and provides its weight
archive. It describes protein embeddings plus an assay token, and distinguishes
cell classification/regulatory tasks from experimental validation. Its system
requirements concern inference, not this project's spatial finetune budget.
These facts support checking Metazoa as the base arm; they do not validate our
developmental phases, spatial extension, biological independence or final
checkpoint. The card does not certify spatial transcriptomics support.

The [upstream README](https://github.com/czi-ai/transcriptformer)
documents the default `./checkpoints/tf_metazoa/` download location and model
assets. Its [inference configuration](https://github.com/czi-ai/transcriptformer/blob/main/src/transcriptformer/cli/conf/inference_config.yaml)
requires a checkpoint directory and sets the weight path via the CLI. Missing
verified finetuning provenance must not be restated as a missing pretrained
asset; search and identify those separately. Upstream defaults do not authorize
raising this WSL host's limits.

The manuscript linked by the repository is
[bioRxiv DOI 10.1101/2025.04.25.650731](https://www.biorxiv.org/content/10.1101/2025.04.25.650731v2).
The browser returned an internal error for the article, so no claim here is
represented as verified from its full text. The accessible first-party card
and code are the evidence used; secondary summaries were not substituted.

## Public sources that can supply inputs, not project results

- [MGI report index](https://www.informatics.jax.org/downloads/reports/index.html)
  supplies curated downloadable reports. Freeze the report version, gene IDs,
  phenotype terms and negative-label evidence when building the mouse external
  set; an absent annotation alone is not a demonstrated viable control.
- [IMPC viability protocol](https://web.mousephenotype.org/impress/ProcedureInfo?action=list&pipeID=16&procID=154)
  measures postnatal homozygote viability. A no-homozygote classification must
  not automatically become phase-specific gastrulation lethality; stage-window
  labels require matching evidence.
- [FlyBase bulk data](https://flybase.org/downloads/bulkdata) provides
  release-qualified genotype/phenotype tables. Its [download format guide](https://wiki.flybase.org/wiki/FlyBase%3ADownloads_Overview)
  identifies genotype IDs, phenotype identifiers, qualifiers and references;
  build an explicitly reviewed genotype-to-gene interpretation and pin an
  archived release, rather than a moving `current` URL.
- [WormBase ParaSite download documentation](https://parasite.wormbase.org/info/Getting_started/downloads.html)
  separates direct phenotype associations from orthology-inferred ones. Only
  direct experimental C. elegans evidence appropriate to the approved external
  screen should enter that test. This documentation is an access lead, not
  proof of a frozen Kamath/Sönnichsen-derived project gene set.
- [Census release documentation](https://chanzuckerberg.github.io/cellxgene-census/cellxgene_census_docsite_data_release_info.html)
  supports dated LTS versions; `stable` is an alias. Resolve and record the
  actual dated release before selecting adult reference cells. The
  [source-H5AD API](https://chanzuckerberg.github.io/cellxgene-census/_autosummary/cellxgene_census.download_source_h5ad.html)
  is a reproducible acquisition route once dataset selection and resource
  budget are fixed. No large source downloads were performed here.

## Addressable now and closure limits

Repository/online research can identify pretrained assets, reconcile approval
records, establish resource URLs and versioning rules, inspect metadata and
produce an execution/evidence manifest. It cannot provide the project's
post-QC membership, model forwards, observed score comparison, verified candidate
training provenance or outcome verdict. The next concrete ticket-05 evidence is a genuine
base-arm comparison if compatible prepared inputs can be established without
misrepresenting their QC status. That evidence should be assessed against the
ticket's actual comparison acceptance, separately from the full base-versus-
finetune scientific adoption gate.

The root checkpoint audit [found both assets](ticket05-checkpoint-discovery-2026-09-30.md)
and distinct weight hashes; candidate training provenance is not established.
Tracking was subsequently reconciled by the parent agent under this ticket
contract. No scientific threshold, checkpoint tensor or corpus source was changed. All links were inspected on 2026-09-30; public
release aliases must be resolved at acquisition time.
