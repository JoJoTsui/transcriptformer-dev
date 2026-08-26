# 09 — Real-data smoke run on the RTX 3090

**What to build:** run the actual `transcriptformer finetune` CLI end-to-end on the local RTX 3090 — prepare real (or contract-complete) H5AD input, train for a small number of steps on one GPU, then repeat with 2+ GPUs to exercise the DDP path for the first time. Save the run artifacts (run manifest, training summary, checkpoint) as evidence.

**Blocked by:** 03 — Single-GPU generative finetune smoke path; 04 — Shared-GPU preflight and distributed training

**Status:** triaged

- [ ] A single-GPU CLI run from prepared data completes and produces a checkpoint, `training_summary.json`, and `run_manifest.json`.
- [ ] A multi-GPU CLI run launches DDP workers, shards via `DistributedSampler`, and completes without I/O or sharding errors.
- [ ] Backed data loading holds peak RAM near-constant during the run (measured, not just asserted).
- [ ] Any failures found are filed as new tickets or fixed.
- [ ] The run artifacts are kept as evidence and referenced from tickets 03 and 04.

## Notes

Closes the open hardware-validation items on tickets 03 and 04. The existing `checkpoints/tf_metazoa_finetuned/` does not count — it predates the pipeline and came from the standalone `scripts/finetune.py` smoke script. If real zebrafish embryo data is still unavailable, a real public H5AD that meets the data contract (raw counts, Ensembl IDs, required obs columns) is an acceptable substitute for the smoke run.
