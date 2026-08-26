# 15 — Measured batch-plan calibration

**What to build:** replace the guessed constant in `derive_batch_plan` (8 GB reserve + ~8 GB per sample) with measured values: run forward+backward passes at batch sizes 1/2/4/8 on the RTX 3090 with the real Metazoa checkpoint, record peak VRAM per configuration, fit per-sample activation memory, and update the heuristic. Record measurements in the repo.

**Blocked by:** None — single GPU suffices.

**Status:** triaged

- [ ] Peak VRAM is measured for forward+backward at several batch sizes with the real checkpoint on the RTX 3090.
- [ ] `derive_batch_plan` uses the measured per-sample cost and model/optimizer state footprint instead of the 8+8 guess.
- [ ] Tests for `derive_batch_plan` are updated to the new heuristic.
- [ ] Measurements and the fitted constants are recorded in the ticket or docs.

## Notes

Motivated by the ticket-09 smoke run: `--batch-size 8` was silently derived down to 1. Full finetuning with AdamW holds ~15 GB of weight/gradient/optimizer state before activations, so the reserve term is roughly right; the per-sample term is the unknown.
