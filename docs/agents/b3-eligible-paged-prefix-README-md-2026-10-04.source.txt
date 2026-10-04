# Synthetic eligible prefix preparation

This ignored helper has **not been executed**. It creates no project-model
evidence. The intended fixture has 502 frozen genes per species, five cells in
five physical embryos, one measured-zero gene and 501 raw-positive genes in
each cell. Native sequence length is 512. Actual public scoring/comparison must
determine whether at least 500 finite pairs and 80% coverage are achieved.

The fixture table explicitly contains **5,000 unique synthetic one-to-one
pairs**: 502 measured/checkpoint-joined pairs and 4,498 background pairs. The
background identities are artificial Ensembl-shaped human/mouse IDs numbered
503 through 5,000, absent from both checkpoint vocabularies and the measured
502-gene sets. `synthetic-ortholog-fixture.json` lists every measured and
background identity; the material receipt binds it and reports all three
counts. This makes no biological orthology claim and changes no project table.
It preserves the independent 5,000-pair mapping floor and the actual 502-pair
checkpoint-joined score denominator. Eligibility is derived by the unchanged
public paired preflight and observed comparator.

The checkpoint is a real tiny PyTorch state dictionary for a deterministic
gene-ID head, with its external loader source reference in the checkpoint
configuration. The helper substitutes only `train._load_model` at the model
boundary and restores it afterwards. Probe timings, original likelihoods,
scores, certificates, index arrays, metrics and catalog provenance come from
the existing public producers. There are no invented successful probe timings,
eligible plans, native certificates or pilot-import records.

## Freeze and command wrapper

Wait for the final committed application reviews and the sole heavy-job slot.
Use the final reviewed application SHA, not an earlier working-source hash.
Every stage checks the exact frozen repository source tree and helper before
imports, and again at final sealing. A source repair requires a new attempt and
new freeze; do not rebind a previous stage to different software.

The runner is:

`runs/b3_feasibility/20261004/eligible_paged_prefix_tools/study_eligible_paged_prefix.py`

Choose a new study root, for example:

`/mnt/d/sc/transcriptformer/transcriptformer/runs/b3_feasibility/20261004/eligible_paged_prefix_attempt01`

For **each** stage below, run one command using this wrapper. Replace the
capitalized placeholders with the chosen paths and table arguments. The
supervisor creates `SUPERVISOR_DIR` before GNU time opens its new cost receipt.

```sh
.venv/bin/python scripts/supervise_b3_pilot.py \
  --run-dir SUPERVISOR_DIR \
  --max-wall-seconds 950 --max-rss-gib 4 \
  --min-host-ram-gib 4 --min-disk-gib 20 \
  -- /usr/bin/time -v -o SUPERVISOR_DIR/gnu-time.txt \
  .venv/bin/python RUNNER ACTION \
  --output STUDY_ROOT/STAGE --max-seconds 900 STAGE_ARGUMENTS
```

All output/supervisor directories must be new. They preserve partial public
producer artifacts and write `failure.json` when a stage fails. A failed stage
has no valid `summary.json`. Begin a new attempt when fixed prospective score
paths have failed; do not overwrite or silently retry their output folders.

## Immutable stages

In the table, `F`, `M`, `H`, `U`, `C`, `SH`, `SM`, `P`, `N`, and `K` denote
directories under the chosen study root. All stages after freeze also take
`--freeze-dir F`.

| Action | Output stage | Additional arguments |
|---|---|---|
| `freeze` | `00-freeze` (`F`) | `--expected-app-sha256 FINAL_REVIEWED_APP_SHA` |
| `material` | `01-material` (`M`) | None |
| `probe` | `02-probe-human` (`H`) | `--material-dir M --species human` |
| `probe` | `02-probe-mouse` (`U`) | `--material-dir M --species mouse` |
| `score` | **`03-score-human`** | `--material-dir M --probe-dir H --species human` |
| `score` | **`03-score-mouse`** | `--material-dir M --probe-dir U --species mouse` |
| `compare` | `04-compare` (`C`) | `--material-dir M --human-score-dir STUDY_ROOT/03-score-human --mouse-score-dir STUDY_ROOT/03-score-mouse` |

Inspect the actual comparator after these stages. A constant-rank or missing
score result must remain unavailable. The existing loader's uniform context
head has positional variation, but this fixture's finite count is unmeasured.
If a declared model change is required, preserve the attempt, change the ignored
fixture head/state explicitly, and create a new software freeze. Do not edit
scientific helpers or promote a comparison by changing a status field.

Continue only after actual comparison succeeds:

| Action | Output stage | Additional arguments |
|---|---|---|
| `support` | `05-support-human` (`SH`) | `--material-dir M --species human` |
| `support` | `05-support-mouse` (`SM`) | `--material-dir M --species mouse` |
| `full-pair` | `06-full-pair` (`P`) | `--material-dir M --human-support-dir SH --mouse-support-dir SM` |
| `native-import` | `07-native-human` (`N`) | `--material-dir M --score-dir STUDY_ROOT/03-score-human --support-dir SH --full-pair-dir P --compare-dir C --species human` |
| `native-catalog` | `08-native-catalog-human` (`K`) | `--native-import-dir N` |
| `cache-measure` | `09-cache-human-cold` | `--native-catalog-dir K` |
| `cache-measure` | `10-cache-human-warm` | `--native-catalog-dir K --prior-cache-measurement-dir STUDY_ROOT/09-cache-human-cold` |

The cold/warm labels mean first and repeated complete public invocation against
the exact same immutable request. They do **not** assert that OS filesystem
caches were flushed. Each invocation creates a new physical statistics cache.
The warm comparison checks the complete four-array manifests and source key.
No 126-block catalog or eligible execute/replay is generated at this stage.

## Receipts and cost decision

Every action publishes `b3_eligible_paged_prefix_study_stage_v1` only after its
declared inputs and generated files pass final byte checks. The source freeze
uses `b3_eligible_paged_prefix_software_freeze_v1`. It binds all original/current
`src/transcriptformer/**/*.py` and `scripts/*.py` bytes, final application,
fixture source and actual Git HEAD. Old public producer schemas and outputs
remain unchanged.

Compare publishes the unchanged `comparison.json` and `coverage.tsv`, not a
custom eligibility claim. Native import additionally requires the real
comparison to be reportable, at least 500 finite pairs, 80% coverage and five
physical embryos per species. Five-cell pilot provenance is legitimate only
because the original public capped importer actually processes those files.

For cache measurements, use `details.public_run_complete_seconds`: its timer
starts immediately before the public native-cache call and ends after return,
including native validation, snapshot, hashing, all final seals and publication.
GNU `gnu-time.txt` captures complete child startup, imports and study-receipt
sealing in addition. Supervisor `elapsed_seconds` may be only its last heartbeat.

The intended arrays are small: one float64 logit tensor is 4,128,768 bytes
(`512 × 1008 × 8`); expression data is 20,120 bytes; one maximum eight-focal
physical cache is 201,120 numeric bytes. These are component estimates, not a
measured process peak or proof of every transient allocation. Supervisor caps
remain 4 GiB RSS, 4 GiB host free RAM, 20 GiB disk, one CPU thread/CUDA disabled;
native numeric admission remains 200 MiB.

At least 63 blocks per species are required for a 500-pair family. Multiply
measured **complete** representative cache invocation costs by at least 126
before estimating each execute/replay job. Add application re-admission, unit
controls, queries and final sealing; do not treat that multiplication as a
validated throughput forecast. If a full call cannot fit 900 seconds, keep the
eligible integration gate open and implement bounded common source preparation
before claiming a positive execute/replay result.
