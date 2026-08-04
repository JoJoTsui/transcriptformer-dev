# Zebrafish Embryo Finetuning Strategy

**Status:** accepted

We will finetune the TranscriptFormer Metazoa checkpoint on independent *Danio rerio* single-cell and spatial transcriptomics datasets using the generative pretraining objective, full finetuning of the trainable weights, dataset-balanced sampling, and spatial coordinates kept as metadata rather than model input.

## Considered Options

- **Supervised adaptation vs generative finetuning**: supervised cell-type/stage heads were rejected because they optimize one label and can distort general representations; generative finetuning keeps the model useful for downstream discovery.
- **Full finetuning vs LoRA**: full finetuning of the trainable transformer/heads was chosen first; LoRA remains a fallback if memory, overfitting, or iteration speed becomes a problem.
- **Spatial coordinates as model input vs metadata**: coordinates as model input were rejected for the initial version because TranscriptFormer has no native spatial input; coordinates stay in `.obs` for downstream spatial analysis.
- **Natural vs dataset-balanced weighting**: natural weighting was rejected because ~30M single cells would drown out the smaller spatial modality; training batches mix single-cell and spatial data.
- **Fixed vs dynamic GPU selection**: fixed 1–4 GPU launch was rejected because the shared node's free GPUs change; the launcher probes utilization/VRAM at startup and sets `CUDA_VISIBLE_DEVICES`, batch size, and gradient accumulation accordingly.
- **Random vs embryo/section holdout**: random splitting was rejected because it leaks the same embryo/section into train and validation; the pipeline uses a three-way train/validation/final-holdout split by `embryo_id` (and `section_id` for spatial).

## Consequences

- Dataset preparation must produce model-ready H5AD files with `ENSDARG...` gene IDs, raw counts, harmonized `stage` and `cell_type`, `embryo_id`, `section_id` for spatial, and coordinates in `.obs`.
- The finetune pipeline must support multi-GPU DDP (1–4 GPUs), gradient accumulation, checkpoint-and-resume, early stopping, and a run manifest for reproducibility.
- Evaluation must compare the finetuned model against the original Metazoa model on the untouched final holdout, using cell-type macro-F1, pseudotime–stage correlation, and spatial-neighborhood coherence.
