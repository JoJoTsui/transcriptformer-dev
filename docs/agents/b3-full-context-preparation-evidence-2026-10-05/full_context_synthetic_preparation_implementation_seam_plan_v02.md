# Genuine synthetic preparation — public implementation seam plan v02

2026-10-05. Author planning record for an ignored source/test draft. This is
not an execution receipt, independent review, SourceAdmission, registration,
finite-score result, or permission to run a project model. Root owns execution.

Preserved plan v01 SHA-256:
`451cfd497611c71d42339d0f645cb5c8a092f0957bfa500e768a218b3c695244`.
This author revision distinguishes preparation sidecars from registration
assignments and limits the empty auxiliary vocabulary claim to support scans.

## 1. Accepted predecessors and public seam

- Issuer design v02 SHA-256:
  `ba2d51feb89c577cea3d1aa67c6300cef6b55d0882a3f71eb32e29ca4957a58e`.
- Its independent Spec record:
  `2b64fb309af512893806a8522e72d2f9e07b3eb969e612fad067ec5cc9a85bb9`,
  0 hard / 0 optional; independent Standards record:
  `f8da968e14bb55e4246a1d7d7205609df6453e936494e5e4a2b6ad5d3d8d0c2b`,
  0 hard / 0 optional. These are design verdicts only.
- Registration v02 `5347353fb5fc1e9a8b0e0f62a3492deca547533abd849e0eba8e9a5f667db6de`
  and bridge v02 `5d2e163836db641f19b1e3984250e30f313369cd002eb48ccedbdf017f2124b8`
  retain the frozen science, prospective family, later finite-set freeze,
  source inventories, issuer authority and acyclic admission chain.

Root has agreed the path/file public seam:

```text
scripts/prepare_b3_full_context_synthetic_fixture.py
run(request_path: Path, output: Path, *, max_seconds=900) -> dict
CLI: --request PATH --output PATH --max-seconds NUMBER
```

The strict closed request has exactly `schema`, `profile`, `fixture_profile`,
`consumer_file_sha256`, `inference_defaults`. Schema is
`b3_full_context_synthetic_preparation_request_v1`; profile is only
`synthetic_stored_arithmetic_v1`; fixture_profile is only
`human_mouse_5000_measured_502_joined_5_units_60_cells_v1`.
`consumer_file_sha256` is the exact 70-path Python source map described below.
`inference_defaults` is a closed actual file Ref with `path`, `sha256`, `bytes`.
Reject duplicate JSON keys, NaN/Infinity, extra/missing fields, wrong types,
project profiles, arbitrary input paths/axis selectors and outcome fields.
This consistent request establishes source consistency, not trusted admission
or comparison authority. Independent source reviews and SourceAdmission are
later owner-controlled records.

## 2. Source authentication and private import boundary

Use the literal 58 native paths in registration v02 section 11; do not scan a
directory to define membership. Add these ten existing script paths:

```text
scripts/preflight_b3_measured_zero_full.py
scripts/preflight_b3_measured_zero_pair.py
scripts/plan_b3_measured_zero_shards.py
scripts/prepare_b3_measured_zero_embryo_metrics.py
scripts/report_ortholog_eligibility.py
scripts/summarize_ortholog_full_universe.py
scripts/build_ortholog_table.py
scripts/handoff_ortholog_scores.py
scripts/summarize_ortholog_paired_scores.py
scripts/b3_score_contract.py
```

Add frozen `scripts/b3_authenticated_helpers.py` and the new entrypoint: 70
Python members. Inference YAML is a distinct configuration input, never a
71st Python member. Retain the complete actual byte buffers before executing
the loader. Hash the same bounded regular file descriptors that supply those
buffers; verify their original pathname/storage identities at final seal.
Record the actual execution subset separately from mandatory retained paths.

The old loader delegates bare imports to ordinary Python imports and copies
`sys.path` by reference (`b3_authenticated_helpers.py:75,142–162`). Supply a
consumer-owned local sys facade with a copied path list and an object-owned
private-module mapping. Configure only the ten explicit admitted bare sibling
names to resolve to their authenticated `scripts.*` module identities. Keep
relative and `scripts.*`/`transcriptformer.*` imports source-bound. Do not edit
loader/native buffers, install a global importer, replace global builtins,
mutate actual sys.path, or import a sibling through an unauthenticated search
path. Unknown repository identities remain refusals. Canonical and foreign
sys.modules objects survive; removal requires the exact installed object.

## 3. Fixed toy assets and distinct vocabulary roles

Construct two raw CSR H5AD sources, one per species, with 60 original rows and
5,000 unique canonical gene features. Species are `homo_sapiens` and
`mus_musculus`; constructed IDs are `ENSG`/`ENSMUSG` plus eleven-digit integers
1..5,000. Each source has five labelled simulated original units with 12 rows
per unit. The genuine preparation sidecar has exactly five columns:
`source_row_index,sample,stage,embryo_id,embryo_sex`; it maps every ordered
barcode/stage/source-row to its original simulated unit and sex. A separate
registration assignment CSV has exactly three columns:
`row_index,sample,simulated_unit_id`. Retain both actual assets and a complete
identity audit joining the original raw row, prepared source_row_index,
barcode, sidecar embryo_id and assignment simulated_unit_id; never substitute
the five-column preparation file for the three-column registration file.
The manifest sets `train_only: true`
explicitly for both sources, `dataset_type: single_cell`, seed 20260930,
and maps the native toy stage to `organogenesis`. This is a synthetic fixture,
not five independent biological embryos or a project training operation.

Preparation vocabulary is an actual HDF5 `keys` asset containing all 10,000
measured human/mouse IDs. Genuine `_map_gene_ids` uses that vocabulary so all
5,000 measured features survive per source. Scoring vocabulary is a separate
checkpoint JSON dictionary containing 502 IDs per species plus the configured
pad token. The two scoring configs use that same complete checkpoint directory,
gene vocabulary, empty auxiliary vocabulary, base arm, organogenesis, train,
native sequence length 502 and the frozen preprocessing. Empty auxiliary
vocabulary is sufficient only for these genuine support/metric scans. Later
producer/native tokenization must independently verify its actual auxiliary
vocabulary requirements; this plan proves no positive tokenizer or producer
admission. A labelled fixture
`model_weights.pt` is actual non-model byte provenance, never a serialized
tensor or claim of trained weights. Bind it, config.json and every actual
vocabulary asset separately; do not invoke torch.save/load or a model.

Counts for the first 501 scoring genes are one; the 502nd is a genuine raw
zero. The other 4,498 measured genes have count one. The all-measured library
sum is therefore 4,999 per cell. This deliberately differs from the scoring
vocabulary sum 501; expression metrics must use 4,999. The prospective native
geometry has 501 raw positive scoring attempts and 500 structurally scorable
focals per cell at sequence length 502. These are preparation/support targets,
not proof that any later B3 score or resampling draw is finite.

Construct the complete four-column one-to-one ortholog table of all 5,000
rows. Actual pair auditing must retain the full 5,000 raw/genome-wide universe,
502 final vocabulary-joined pairs, and 4,498 vocabulary exclusions. Never
replace that denominator with 500 potentially scorable genes.

## 4. Genuine operation order and durable references

1. Admit closed request, exact retained sources/YAML, namespace and budget.
   Reserve one exclusively created owned output directory; actual paths are
   stable so no publication rename invalidates embedded provenance paths.
2. Create labelled raw/sidecar/retention-vocab/checkpoint/manifest/table assets.
   Invoke authenticated `prepare_run(manifest: dict, output_dir: Path)`
   (`prepare.py:528–575`). Retain its genuine preparation_report.json,
   split_assignments.json, prepared CSR files and all fingerprints. Check full
   original rows, five simulated units, train-only splits and retained axes.
3. Write both actual scoring configs. Invoke authenticated full support
   `run(config_path, output_dir, chunk_rows=8, max_storage_bytes=...)`
   (`preflight_b3_measured_zero_full.py:60`). Retain actual support.h5 and
   support_preflight.json. Do not use the pilot branch or manufacture output.
4. Invoke authenticated pair `run(SimpleNamespace(config_a, config_b,
   preflight_a, preflight_b, table, output))` (pair.py:600–672). It returns None;
   read the actual written paired report. Retain its real joins/eligibility.
5. For each species invoke `plan(config_path, report_path, paired_path,
   table_path, output_path)` (plan.py:106–318), then genuine embryo metric
   `run(plan_path, output, chunk_rows=8, max_seconds=remaining)`
   (metrics.py:297–388). Keep every original range and exact metric inputs.
6. Seal actual asset Ref inventories, embedded file/hash/source memberships,
   YAML and software aliases, complete-marker namespace and original public
   deadline. Release local import resources, then publish the final marker
   and perform final owned-marker/deadline seals. Any later failure withdraws
   the owned complete marker. Failed owned attempt assets may remain.

No stored target likelihoods, native impact records, shard certificates,
native catalogs, observed scores, registration, Start/Permit/Witness,
RuntimeAdmission, Acceptance, AuthorityPin or Origin is produced here. Those
require later separately reviewed genuine operations and authority.

## 5. Resources, refusal and publication

Set one-thread native numerical environment and CUDA_VISIBLE_DEVICES empty
before any numerical/repository import. Keep the original public deadline
positive and at most 900 seconds; guard throughout admission, calls, byte
reads, writes, final seals and cleanup. Helpers without deadline parameters
remain inside that original budget; their return cannot reset it. Pass metric
calls the floor of remaining seconds, capped at 900; refuse below one before
the call. Outer root supervision remains separate (950 seconds/CPU one).

RSS cap 4 GiB, numeric admission cap 200 MiB, available-host-RAM floor 4 GiB,
and free-disk floor 20 GiB after prospective allocation remain frozen. Compute
allocation upper bounds from fixed actual toy shapes before arrays/caches;
record these as upper bounds. Actual public elapsed and Linux process peak RSS
are measured. A complete numerical allocation census is not yet demonstrated:
`peak_live_numeric_bytes` stays null with explicit unavailable status, distinct
from any shape upper bound or the 200 MiB policy. This cannot satisfy a later
RuntimeAdmission field that requires a measured complete census.

Refuse existing output/claims, aliases into sources/request/YAML, symlinked
output ancestors, changed source storage/bytes and changed final caller aliases.
Owned directory and complete marker operations use original admitted FDs and
inode identities. Do not follow a replaced output pathname or remove/close a
foreign inode/FD/module object. Marker-last success must be withdrawn after
late cleanup/final-seal failures; retained failed assets lack complete status.

## 6. Public tests first and execution handoff

Start with a public run/CLI refusal slice: absent implementation is a genuine
RED; a valid closed request with one changed helper hash must refuse before
fixture allocation/numeric imports and leave no completion marker. Root runs
the sealed ignored test at the canonical seam; this agent does not execute it.
Then draft the smallest source slice and hand it off for independent review.

Broaden after actual root RED/implementation evidence: complete genuine toy
preparation via returned actual refs; scalar oracle log1p(10000/4999), five
original train-only units, full 5,000/502/4,498 joins; CLI equivalence;
extra/duplicate/project request refusals; source/alias late-change refusal;
copied sys.path and preservation of canonical/foreign module identities;
late marker/descriptor cleanup failure with no complete marker. Exercise OS
file/clock/resource boundaries only, never mock prepare/support/pair/plan/
metrics implementations or fabricate their records. Tests consume only public
outputs and actual files explicitly referenced by the public result.

## 7. Actual source reference hashes read for this plan

| File | SHA-256 |
| --- | --- |
| src/transcriptformer/finetune/prepare.py | 0cd93a0d9925fded3a6dc6f636eae81bf389020695de3e480998ac4e5ae61096 |
| src/transcriptformer/finetune/artifacts.py | 7533d7a27942a554c17cc62be1be97025670304fb5d7872899d54d968479ace8 |
| src/transcriptformer/finetune/embryo_identity.py | 9904fa2770d502afb9daac0452b42bb138b7dcb609dcc36c9c32fdb7097cdaba |
| src/transcriptformer/finetune/b3_prepared.py | d261c760d29dd7b50ec652b4c70d81f42a15c3c6ca1b2ff1a71f018e76bbcc57 |
| scripts/b3_authenticated_helpers.py | a931e9d2ee1a35a13d2e7659fa71ff6e1565e289d5ab6c6f15170701525487f3 |
| scripts/preflight_b3_measured_zero_full.py | 20304ceda81d53ad064d32b6ccad5b0db2c5e45728cfee9cdca3bd5d5783d901 |
| scripts/preflight_b3_measured_zero_pair.py | 8897a84b605fe4e63c14f55c7da062103f1d8ee2ee148e4a5a926c7fc817be71 |
| scripts/plan_b3_measured_zero_shards.py | bf65af4bd4c02010d5140c672b5cfd23b5b947c23f195599da390754d375d800 |
| scripts/prepare_b3_measured_zero_embryo_metrics.py | 8393edd2cbe897f325a8985ac87b63c6de088a11069bafa551d08a7142c4a097 |
| src/transcriptformer/cli/conf/inference_config.yaml | e8567437b22a51f21c7e853a2e35efbc371c0a93d5fbca69206d6657851ade3a |
