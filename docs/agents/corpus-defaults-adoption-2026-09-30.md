# Owner adoption of non-zebrafish corpus defaults — 2026-09-30

The project owner answered **yes** to the consolidated corpus question on
2026-09-30. This records the decision for the existing non-zebrafish corpus;
it does not assert that a candidate dataset has passed the data gates below.

| Topic | Adopted decision | Current implementation and boundary |
| --- | --- | --- |
| Mouse prenatal time-lapse atlas (Nature 2024) | Exclude the atlas from this training corpus. | It is absent from `runs/spatial_coordinate_manifest.json`. If this decision changes, remove the overlapping TOME E8.5b slice before adding any atlas subset. |
| TOME E8.5b | Retain it while the atlas is excluded. | The active 27-source manifest includes E8.5b and excludes the atlas. |
| Nature2019 E4.5–E7.5 | Include **only after** source QC and identity review establish a suitable, split-safe source. | It is absent from the active manifest. The isolated 1,986-cell candidate has author RNA-QC passing, non-mixed embryo labels, but is not a final training input. |
| Training sampler | Keep the existing `BalancedDataset` policy. | The manifest's `sampling.max_single_cells=1000000` and `sampling.spatial_fraction=0.3` continue to drive the sampler. This decision does not claim species-balanced exposure; measure post-QC exposure before training. |
| Unstaged observations | Retain for training; exclude from phase-resolved analysis. | Preparation preserves null stage values; the training sampler groups with `dropna=False`. Evaluation excludes unstaged rows as documented in the readiness guide. This is a policy decision, not a substitute for source-specific QC. |

The Nature2019 candidate is pinned by
[`candidate_h5ad_provenance.json`](../../logs/dataset_audit/nature2019_candidate/candidate_h5ad_provenance.json)
and the [source suitability audit](nature2019-source-suitability-2026-09-29.md).
Before promotion, it still needs a declared acceptance standard for physical
embryo independence across the selected mouse sources, an assay-specific QC
decision for its Smart-seq2-based, non-UMI RNA counts, approved phase and
cell-type labels, and a split review using source-qualified author embryo IDs.
The exact-ID audit found no collision with selected mouse sources but cannot
prove physical specimen independence. The 494 RNA-QC-passing cells with mixed
embryo labels remain excluded from the candidate. The [embryo identity](nature2019-embryo-identity-2026-09-30.md),
[assay token](nature2019-assay-token-evidence-2026-09-30.md), and
[cross-source overlap](nature2019-cross-source-overlap-2026-09-30.md) notes
carry the current evidence. No source has been added to the active manifest by
this decision record.

The owner answered the B1-A question in the same exchange. Its method and
threshold sign-off are recorded separately from these corpus decisions.
