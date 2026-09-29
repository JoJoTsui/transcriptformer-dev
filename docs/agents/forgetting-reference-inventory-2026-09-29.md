# Forgetting-reference source inventory — 2026-09-29

The [design](../perturbation-and-baseline-design.md#41-reference-set-frozen-never-trained-on)
calls for 2,000 adult human and 2,000 adult mouse CELLxGENE Census cells plus
*Spongilla lacustris* and *S. cerevisiae* canaries; optional adult fly cells
are separate. The [Census release guide](https://chanzuckerberg.github.io/cellxgene-census/cellxgene_census_docsite_data_release_info.html)
supports pinning a dated release, and the [online gate follow-up](non-zebrafish-online-followup-2026-09-29.md)
identifies `2025-11-08` as a candidate, not a chosen reference.

A bounded current-workspace file inventory (`rg --files --hidden --no-ignore
-g '*.h5ad' -g '!**/.venv/**'`) found 23 H5AD paths. They are test human,
mouse and chicken data, human spatial copies, inference output, and synthetic
work under `.scratch`; none is named for sponge or yeast. Searches of source
manifests and run metadata also found no canary H5AD path. This is a workspace
inventory, not proof that the research group has no such files elsewhere.
The [producer README](https://github.com/czi-ai/transcriptformer/blob/main/README.md)
lists sponge and yeast among TF-Metazoa training/vocabulary species, which
establishes model support but does not locate an unused reference dataset.

Before a reference freeze, locate or acquire the two canary count matrices,
record source URLs and hashes, check their gene-key joins to the actual model
vocabularies, and verify they are excluded from this finetuning corpus and its
holdouts. Record the pinned Census release, adult/normal/tissue filters,
dataset and donor IDs, sampling seed, cell and feature IDs, and hashes before
retrieving expression. The 3% likelihood and 0.90 CKA gates remain proposed
until the project approves the reference composition and thresholds. No
reference data were downloaded or read in this inventory.
