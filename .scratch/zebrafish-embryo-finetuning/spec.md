# Zebrafish Embryo Finetuning Pipeline

Category: enhancement
Status: ready-for-agent

## Problem Statement

The researcher has ~30M single-cell and an unknown amount of spatial transcriptomics data from zebrafish embryo development. They want to finetune the Metazoa checkpoint so the resulting model can be used to discover cellular development and regulation mechanisms, but there is no dataset-preparation, finetuning, or evaluation pipeline that handles both modalities, shared-GPU nodes, and trustworthy validation.

## Solution

Provide a finetuning and evaluation pipeline that:

- standardizes single-cell and spatial data into model-ready H5AD files,
- finetunes the Metazoa checkpoint with generative finetuning on a dataset-balanced sample,
- runs safely on 1–4 shared GPUs with launch-time resource probing and resume,
- evaluates the finetuned model against the original Metazoa checkpoint on an untouched final holdout using agreed metrics,
- records every run in a reproducible run manifest.

## User Stories

1. As a bioinformatics researcher, I want to point the pipeline at my single-cell and spatial embryo files, so that they are converted into model-ready H5AD inputs without manual scripting.
2. As a bioinformatics researcher, I want gene symbols converted to `ENSDARG...` IDs when needed, so that my data aligns with the Metazoa checkpoint vocabulary.
3. As a bioinformatics researcher, I want raw count matrices validated and preserved, so that normalized or log-transformed data is rejected instead of silently used.
4. As a bioinformatics researcher, I want my raw developmental stage labels harmonized into one `stage` vocabulary, so that development can be compared across datasets.
5. As a bioinformatics researcher, I want my raw cell type annotations harmonized into one `cell_type` vocabulary, so that evaluation is comparable across modalities.
6. As a bioinformatics researcher, I want conservative QC with every filter recorded, so that rare developmental states are not removed and the filtering is auditable.
7. As a bioinformatics researcher, I want spatial spots treated as pseudo-cells with raw spot counts, so that spatial transcriptomes can be included without deconvolution assumptions.
8. As a bioinformatics researcher, I want spatial coordinates preserved as metadata, so that downstream spatial analysis remains possible without changing the model architecture.
9. As a bioinformatics researcher, I want targeted-panel spatial genes intersected with the model vocabulary, so that partial gene panels can be finetuned without imputation.
10. As a bioinformatics researcher, I want the pipeline to split data into train, validation, and final holdout by embryo and section, so that evaluation is not leaked.
11. As a bioinformatics researcher, I want dataset-balanced sampling between single-cell and spatial observations, so that the spatial modality is not drowned out by ~30M single cells.
12. As a bioinformatics researcher, I want a stratified ~1–2M single-cell subset sampled by stage and cell type, so that training time is practical on available GPUs.
13. As a shared-node user, I want the pipeline to probe GPU utilization and free VRAM at launch, so that it selects only GPUs that are actually available.
14. As a shared-node user, I want batch size and gradient accumulation derived from the smallest free GPU, so that runs do not start with an impossible memory footprint.
15. As a shared-node user, I want the number of GPUs configurable from 1 to 4, so that the pipeline respects other users on the node.
16. As a researcher, I want multi-GPU distributed training, so that a meaningful finetune completes in days rather than weeks.
17. As a researcher, I want full finetuning of the trainable transformer and head weights with frozen gene embeddings and mixed precision, so that the model adapts to zebrafish embryo biology.
18. As a shared-node user, I want frequent checkpointing and resume, so that losing a GPU mid-run does not discard completed work.
19. As a researcher, I want early stopping on validation metrics, so that training stops when improvements plateau.
20. As a researcher, I want a run manifest capturing data versions, harmonization mappings, QC filters, split assignments, GPU plan, hyperparameters, and metrics, so that every finetune is reproducible.
21. As a researcher, I want the original Metazoa checkpoint evaluated on the same final holdout, so that finetune improvements are measured against a baseline.
22. As a researcher, I want cell type macro-F1 from embedding-based logistic regression, so that representation quality is checked separately for single cells and spatial spots.
23. As a researcher, I want pseudotime–stage Spearman correlation, so that developmental trajectory ordering is checked.
24. As a researcher, I want spatial neighborhood coherence and Moran's I, so that spatial structure is checked.
25. As a researcher, I want all final metrics computed on the untouched final holdout, so that early stopping and checkpoint selection cannot inflate the results.
26. As a researcher, I want a single-GPU smoke-test mode, so that quick sanity checks run on the local RTX 3090 before production runs.
27. As a researcher, I want configurable batch size, learning rate, max steps, and epochs, so that I can iterate on experiments.
28. As a researcher, I want finetuned embeddings saved with cell metadata including spatial coordinates, so that downstream developmental and regulatory analyses can use them.
29. As a researcher, I want the evaluation report saved next to the checkpoint, so that I can decide whether the finetuned model is good enough to use.
30. As a pipeline maintainer, I want the entire workflow exposed through a CLI, so that the same commands work for smoke tests and production runs.

## Implementation Decisions

- Add two CLI commands to the existing transcriptformer CLI: one finetune pipeline command and one evaluation command.
- The finetune command accepts a run manifest describing dataset files, harmonization mappings, QC settings, split policy, GPU policy, and training hyperparameters.
- The finetune command runs dataset preparation internally; a prepare-only mode emits model-ready H5AD files, harmonized metadata, and split assignments without training.
- Model-ready H5AD files require `var.ensembl_id` with `ENSDARG...` IDs, a raw count matrix in `.X` or `.raw.X`, and harmonized `stage`, `cell_type`, `assay`, `embryo_id`, and `section_id` columns.
- Spatial files additionally preserve `spatial_x` and `spatial_y` (or an equivalent coordinate representation) in metadata.
- Gene symbol mapping, stage harmonization, and cell type harmonization use standard zebrafish references with documented custom fallback mappings.
- A dataset-balanced sampler mixes single-cell and spatial observations in each batch; the single-cell side is stratified to roughly 1–2M cells by stage and cell type.
- A GPU preflight step uses NVML to inspect free VRAM and utilization, selects 1–4 usable GPUs, sets visible devices, and derives per-GPU batch size and gradient accumulation from the smallest free GPU.
- Training uses distributed data parallelism, mixed precision, full finetuning of trainable weights, frozen gene embeddings, gradient accumulation, checkpoint-and-resume, and early stopping on validation metrics.
- The pipeline does not modify the model architecture; spatial coordinates are metadata only.
- The evaluation command computes embeddings from the original and finetuned checkpoints on the final holdout and reports cell type macro-F1, pseudotime–stage Spearman correlation, spatial neighborhood coherence, and Moran's I.
- Every run writes a run manifest containing data versions, harmonization mappings, QC filters, split assignments, GPU plan, hyperparameters, checkpoint paths, and metrics.
- No deconvolution is performed as part of training input; the schema leaves room for an optional downstream deconvolution extension.

## Testing Decisions

- Good tests exercise external behavior through the CLI: given small synthetic H5AD fixtures and a run manifest, the finetune and evaluate commands must produce the expected files, exit successfully, and report metrics.
- The primary seam is the CLI level; internal GPU probing, sampling, harmonization, and training mechanics are tested through this seam rather than through direct unit-level assertions on implementation details.
- Synthetic fixtures should cover scRNA-seq, full-transcriptome spatial spots, targeted-panel spatial data, symbol-based gene IDs, harmonizable stage labels, and mismatched cell type vocabularies.
- GPU-dependent behavior is tested with a mocked NVML probe; multi-GPU behavior is exercised on one GPU in CI and smoke-tested locally on the RTX 3090.
- Prior art for the test style exists in the repo's existing CLI integration tests and mocked inference tests.

## Out of Scope

- Acquiring or organizing the actual embryo datasets, which are still being prepared by the researcher.
- Changing the TranscriptFormer architecture to consume spatial coordinates as model input.
- Using deconvolution results as training input.
- Training supervised task heads or regulatory-network objectives inside the finetune pipeline.
- Generating new protein/gene embeddings for species outside the Metazoa checkpoint vocabulary.
- Training on all 30M single cells in the initial implementation; the first production runs use a stratified subset.
- Migrating the issue to GitHub Issues; the spec is published to the local tracker for now.

## Further Notes

- The dataset files are not available yet, so implementation should be driven by synthetic fixtures and validated when real files arrive.
- The plan respects the decisions recorded in the Zebrafish Embryo Finetuning ADR and uses the vocabulary in the project glossary.
- The local RTX 3090 is the smoke-test target; the 4-GPU node is the production target, with resources chosen dynamically at launch.
