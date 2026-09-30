# Ticket 05 checkpoint discovery — 2026-09-30

The pretrained Metazoa checkpoint is available at `../checkpoints/tf_metazoa`.
The nominal finetuned checkpoint is available at `checkpoints/tf_metazoa_finetuned`.
The earlier blanket wording “checkpoint unavailable” was too broad. Both weight
files are present and each is 4,309,413,022 bytes. See the
[byte/metadata audit](ticket05-checkpoint-discovery-2026-09-30.json).

| Asset | Weight SHA-256 | Current classification |
| --- | --- | --- |
| `../checkpoints/tf_metazoa/model_weights.pt` | `16eb858e39ed69d6e07d5a0a5a4edd8d885951493ffd218097fc4db0c8b29c29` | Available pretrained/base asset; local download script identifies the upstream Metazoa archive URL. |
| `checkpoints/tf_metazoa_finetuned/model_weights.pt` | `f414f222a729631e02507aa75e3a984c1205000056b6267ccd575de0bd765f59` | Available distinct candidate; training provenance not found. |

Both configurations have SHA-256
`84042c79ba1b452bc64ad78c6a39831b60e0b533c222dad4cddf0704a4c4d80f`.
The candidate vocabulary directory is a symlink to the base checkpoint vocabulary
assets, including twelve species embedding H5 files and an assay vocabulary.
The PyTorch ZIP central directories have the same tensor metadata but all 140
storage entries have different recorded CRCs; this supports changed tensor bytes,
not merely a renamed directory. CRCs are not a replacement for file SHA-256.

No `training_summary.json`, `run_manifest.json`, `selected_model.json` or
`terminal_state.pt` was found beside either real checkpoint. The legacy
`scripts/finetune.py` defaults its output to the nominal candidate path and saves
configuration, vocabulary linkage and weights. That is a possible production
mechanism, **not evidence that this specific file came from that script or an
approved project corpus**. No provenance was invented from its name or timestamp.

## Ticket 05's actual remaining evidence

An available pretrained model can serve a genuine base-arm species-pair B3
comparison. Ticket 05's explicit comparison acceptance does not intrinsically
require a newly finetuned model; a claim about finetuning improvement does.
The approved method requires same model arm on both species, validated prepared
cells, frozen phase/embryo membership and actual full B3 score artifacts. The
base asset is therefore ready for method input identification. The candidate
requires source/run provenance before attributing it to the planned finetune.

The configured `runs/multispecies_v1` output is absent. Current preparation
reports identify their scope as bounded rehearsal and say temporary artifacts
were removed. The archived synthetic smoke prepared report is legacy-format
and cannot substitute for the approved real prepared corpus. No project B3
rankings or scored comparison were found in the searched checkout/parent paths.
Therefore the observed-comparison criterion remains open on corpus/score
execution evidence, rather than on missing pretrained weight bytes.

## Resource and source limits

The two checkpoint SHA-256 values were read sequentially using 8 MiB buffers
(16.64 and 17.00 seconds). ZIP metadata was inspected without unpickling or
`torch.load`; no checkpoint model or expression matrix was materialized.
The host reports 31 GiB RAM / 8 GiB swap. No production forwards, GPU job, data
mutation, full-corpus preparation or new zebrafish work was performed.
The [upstream README](https://github.com/czi-ai/transcriptformer#downloading-model-weights)
documents the pretrained Metazoa download layout; the
[first-party model card](https://virtualcellmodels.cziscience.com/model/transcriptformer)
provides the upstream asset entry point. These sources cannot supply this
candidate's missing training records or project score results.
