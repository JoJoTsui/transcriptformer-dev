# 05 — Resume, early stopping, and complete run manifest

**What to build:** interrupted finetune runs resume from the latest checkpoint, training stops when validation metrics plateau, and the run manifest records data versions, harmonization mappings, QC filters, split assignments, GPU plan, hyperparameters, and final metrics.

**Blocked by:** 04 — Shared-GPU preflight and distributed training

**Status:** ready-for-agent

- [ ] A killed or interrupted run can resume from the latest checkpoint.
- [ ] Early stopping triggers on a validation-metric plateau.
- [ ] The final run manifest contains all required reproducibility fields.
- [ ] Tests simulate interruption/resume and early stopping through the CLI.
