# Full-context family/source registration — contract draft v02

Date: 2026-10-05. Static design only; no implementation or runtime acceptance.

This separately versioned repair closes the registration interface used by
`full_context_comparison_bridge_design_draft_v02.md`. It proposes registration as
one phase of that bridge Module, not a second registrar Module. The bridge owns
registration validation, publication and replay. Its planned 80-file execution
closure and the v4 adapter's planned 83-file closure stay unchanged. The
standalone observed publisher remains independently useful.

The original draft is preserved unchanged at byte SHA256
`ab9bedb0c07cd00289a8b3454ef2c1d07110103b5b06c77034f74f209c7b56bf`.
The independent Spec record `598a22e25fc62b316a85de8f49b54e31b402160766fb34b7a2ec2a778e5ab877`
and Standards record `56ca73040c7f442332eb40ca0395b3dc3f608185def4cd37411dfb3b2b3e43e3`
identify the missing controlled-history and synthetic-profile interfaces.
All new registration/start/origin envelope schemas below are v2; frozen
family, native67, common69, publisher70 and mathematical schemas are unchanged.

## 1. Scope and claims

The register phase freezes a complete prospective comparison family, its
original source keys, complete configured gene axes, intended physical embryo
axes, exact preparation/selection/split evidence, checkpoint and producer
identities, and the approved RNG policy. It consumes no observed rows, score
tables, selected finite pairs, correlations or bootstrap results. Scored native
shards do not have to exist to register future production.

A completed registration receipt proves the admitted metadata bytes and their
agreement. It proves no controlled execution, chronology or prior human
knowledge. Positive comparison additionally requires section 7's actual
controlled-execution witness, independent runtime admission and an authority
pin admitted outside the untrusted request. A timestamp, source-code listing,
retrofitted start or mutually consistent JSON cannot supply that dependency.
Its capture/producer software is not implemented or authorized by this draft;
until it is independently accepted and a genuine run admitted, compare refuses.

There are exactly two profiles: `project_organogenesis_v1` and
`synthetic_stored_arithmetic_v1`. The former retains the existing six-source,
16-artifact human–mouse corpus and genuine project origin gates. The latter
binds actual generated fixture artifacts and real public-operation history;
it never claims project origin, biological independence or likelihood effects.
Profiles cannot be mixed within a registration or comparison family.

The scientific rules remain those of ADR 0005 and the existing approved paired
comparison, likelihood, null and measured-zero decisions. There is no change to
cohort selection, target/sign/order, complete all-gene binning, peer support,
equal embryo aggregation, fixed observed finite-pair selection, reporting floors
or uncertainty. Zebrafish is excluded. Registration authorizes no model job.

Registration cannot create an authentic old `b3_measured_zero_score_sidecar_v2`,
old score bundle, v2 preparation receipt or old observed bridge. New publications
do not pass through the frozen 48-cell `_pilot_bridge` or v3 `_legacy_facts`.

## 2. Common notation and admission

Every record below has exactly the listed keys. Reject duplicate JSON keys,
unknown keys, nonfinite JSON numbers, wrong types, booleans used as integers,
empty or padded names, noncanonical IDs and conflicting declarations.

`Ref` is exactly `path, sha256, bytes`: canonical absolute persistent path,
lowercase 64-character SHA256, strict nonnegative integer size. It denotes an
existing admitted regular file. A planned future output path is a string, not a
Ref; it has no invented size/hash and is never passed to a source-file reader.

`FileMap` is a canonically sorted absolute-path-to-lowercase-SHA256 map with an
explicit expected path set. Counts alone never authenticate a closure.
`Refs` are unique, sorted by canonical path. Repeated roles may refer to the
same exact Ref; independent raw/prepared sources and producer keys may not be
aliases of one another. Retain caller-resolution and canonical-path pins.

Metadata JSON uses the existing 64 MiB per-file ceiling. Native catalogs,
support and source assets retain their existing separate ceilings. Stream CSV,
raw/prepared/checkpoint and vocabulary assets as bytes with bounded scratch;
never collect cell-sized tables merely to hash them. Bound aggregate retained
bytes, parsed objects, temporary serialization and output reservations before
allocation, with RSS/deadline checks through cleanup. Larger honest inputs can
be safely refused; no unmeasured fit promise is made.

## 3. Closed bridge register request

Entry point remains `run(request_path, output, *, max_seconds=900)` in intended
`scripts/bridge_b3_full_context_observed.py`.

The new registration request is exactly:

```text
schema, phase, registration_profile, family, family_sha256, decision_evidence,
preparation, source_bindings, producer_intent, issuer_source_admission,
rng_contract, execution_catalog, consumer_file_sha256
```

| Field | Exact meaning |
| --- | --- |
| `schema` | `b3_full_context_family_registration_request_v2` |
| `phase` | `register` or `replay_registration` |
| `registration_profile` | Exactly one of the two profiles in section 1 |
| `family` | Ref to the genuine `b3_measured_zero_bootstrap_family_v1` JSON |
| `family_sha256` | Existing frozen `digest(family)`, distinct from its file-byte SHA |
| `decision_evidence` | Closed DecisionEvidence record below |
| `preparation` | Closed Preparation record below |
| `source_bindings` | Exact original family source-key closure to SourceBinding records |
| `producer_intent` | Same exact source-key closure to ProducerIntent records |
| `issuer_source_admission` | Actual source-admission Ref from section 7; pins existing intended capture/producer bytes, not a completed run |
| `rng_contract` | Closed, constant policy record below |
| `execution_catalog` | Null for register; Ref to the original completed registration summary for replay |
| `consumer_file_sha256` | Exact proposed bridge80 map, including the actual canonical bridge bytes |

For replay, authenticate the old summary, its marker, registration payload and
original persistent register request; validate every original source anew.
The replay request must equal the original scientific request fields and exact
consumer map. Its phase, own request Ref and execution_catalog are the only
different controls. No private copied addresses enter a commitment.

Family validation reuses frozen
`src/transcriptformer/finetune/b3_measured_zero_bootstrap.py:47` `validate_family`
and `digest`, through authenticated retained-buffer helpers. Do not call its
old bundle loader or numerical producer. Its exact family keys remain:

```text
schema, family_id, model_arm, comparisons
```

Each comparison retains exactly:

```text
comparison_id, bundle_a, bundle_b, table, paired_preflight,
table_sha256, paired_preflight_sha256
```

Preserve the comparison list order. `bundle_a` and `bundle_b` are the original
logical producer source keys. They are canonical absolute planned paths frozen
before new production, not proof that old-v2 bundles exist. Never substitute
registration, cache, publisher-summary or temporary paths, or choose keys from
observed output. Both keys of a member differ; reject canonical aliases,
duplicate strata and exact/reversed duplicate scientific comparisons. At most
16 comparisons and 32 distinct original source keys. Every planned member,
including a later unavailable one, remains in the family.

The existing 2026-10-03 observed-pilot family is a diagnostic family over
already inspected pilot outputs. It must not be relabeled as a prospective
full-cohort registration. Genuine new full-cohort keys/family bytes must be
recorded before their scored outcomes. Choosing a new filesystem location does
not permit changing the cohort, family membership or frozen draw identity of
an already registered run.

## 4. Closed evidence and source records

### DecisionEvidence

Exactly:

```text
feasibility_decision, comparison_decision, likelihood_decision,
null_decision, measured_zero_decision, selection_record
```

All six are Refs to actual preserved decision/preparation evidence. The first
five are the existing accepted normative decisions listed in section 9, for
both profiles. For `project_organogenesis_v1`, `selection_record` binds the
existing preparation/recommendation record and original selected corpus/split.
For `synthetic_stored_arithmetic_v1`, it is the closed SyntheticSelection below;
it cannot substitute toy literals for the real recommendation. These documents
authorize their recorded method and scope, not a future output or model job.

The original register request and its sealed payload are the new scope freeze
for an unchanged already authorized comparison. A source key/family/cohort
selection inconsistent with the authorized scope is refused. A changed
estimand, cohort-selection policy, null, embryo-independence policy or
uncertainty method needs a separate recorded owner decision. Routine future
publication paths and metadata validation require no new scientific decision.

### Preparation

Exactly:

```text
manifest, preparation_report, prospective_split_plan, split_assignments,
raw_sources, prepared_artifacts, preparation_assets, physical_identity
```

The first four are Refs; the next three are complete sorted Refs closures
derived from the original manifest/report/fingerprint, not caller-selected
subsets. Under the project profile, `raw_sources` is all six manifest raw
sources and `prepared_artifacts` all 16 reported split artifacts, not just
training files. Under the synthetic profile they are every actual fixture
manifest source and reported artifact; counts are independently derived, not
the real corpus's constants or a selected positive subset. Bind all required
preparation vocabularies/mappings/identity assets in
`preparation_assets`, including the manifest's actual vocabulary paths. Their
role is preparation provenance; do not equate them with the producer's scoring
checkpoint merely because paths contain `finetuned`.

`physical_identity` is exactly `human, mouse` for both profiles. The following
project record shapes and facts apply only to the existing real corpus.
Synthetic identity has the separate closed record below. Project Human is exactly:

```text
basis, source, observation_column
```

`basis=original_source_observation_embryo_column`, `source` is the actual human
raw-source Ref and `observation_column=embryo` from its manifest mapping.
Mouse is exactly:

```text
basis, recovery_report, author_metadata, sidecars
```

`basis=exact_author_sample_barcode_join`; the two records are actual Refs.
The five sidecar records are exactly `source, sidecar, sample_column`, with
actual raw-source/CSV Refs and `sample_column=sample`. Match every manifest
`embryo_identity` sidecar and the recovery report's exact source/sidecar/hash
closure and the **accepted historical** ordered-barcode/stage/QC join evidence.
Registration authenticates that report and streams each CSV's consistency; it
does not freshly perform the raw H5 observation join. In particular, bind each
report source's `sample_sha256` and its recorded encoding
`ordered JSON ASCII strings, one newline per barcode`, sidecar SHA, row count,
embryo counts and author-QC/join scope to the manifest and recovery sidecars.
Any missing or inconsistent historical audit is refusal. A new raw observation
audit would be a separately scoped dependency, not an assertion by register.
Reject stage-file constants as physical identity.

The real five-embryo predicate uses those accepted author physical-identity
assignments plus the exact selected report/split membership, then exact original
native proof/support/metric-axis agreement. Hash-bound labels and matched axes
are not a newly performed biological-independence audit. Project and synthetic
identity evidence cannot substitute for one another.

### SyntheticSelection and genuine engineering preparation profile

SyntheticSelection has exactly:

```text
schema, registration_profile, fixture_id, preparation_manifest,
preparation_report, preparation_source_files, generation_seed,
selection_policy, phase, split, source_keys, gene_universe,
ortholog_table, checkpoint, identity_audit
```

`schema=b3_full_context_synthetic_selection_v1` and the profile is exactly
`synthetic_stored_arithmetic_v1`; fixture_id is a nonempty canonical ID.
`preparation_manifest`, `preparation_report`, `gene_universe`, `ortholog_table`
and `identity_audit` are actual Refs. `preparation_source_files` is the complete
explicit actual preparation/builder FileMap, including its entrypoint.
`generation_seed` is a strict nonnegative integer fixed before outcomes;
it is distinct from and cannot alter bootstrap seed20260930. `selection_policy`
is exactly `complete_generated_sources_original_axes_no_outcome_selection`.
`phase=organogenesis`, `split=train`, `source_keys` is the exact sorted family
original-key list, and `checkpoint` is the actual closed Checkpoint record.
Its digest and every original asset are bound before the controlled operation.

Invoke the real preparation interface
`src/transcriptformer/finetune/prepare.py::prepare_run`, with actual generated
raw inputs, manifest, source fingerprints, prepared split artifacts, report,
prospective split plan and split assignments. Original full-preflight/support,
native context/catalog/common-source and observed publisher operations must
produce their genuine typed artifacts; do not fabricate reports or completion
receipts, copy project corpus constants, mock admission/math, or manufacture an
old-v2 six-file bundle. Assets can be genuinely constructed fixture bytes;
every origin label must describe that construction.

Each synthetic `physical_identity` species value has exactly:

```text
basis, identity_audit, assignments
```

`basis=simulated_original_physical_unit_assignments`, identity_audit is a Ref
to the same complete audit selected above, and assignments is a sorted list
of exactly `source, assignment` records with actual raw-source/CSV Refs.
Each assignment CSV has exactly the columns `row_index, sample,
simulated_unit_id`, with one complete ordered row per source observation.
row_index covers strict consecutive0:n_obs, sample is the original unmodified
barcode and simulated_unit_id is a canonical original fixture ID. Reject
duplicate/missing barcodes, ID rewrites, delimiter-unsafe values or extra columns.
The closed audit has exactly:

```text
schema, registration_profile, fixture_id, sources
```

`schema=b3_full_context_synthetic_identity_audit_v1`; profile/fixture match.
Each `sources` row is exactly `source, assignment, n_obs, sample_sha256,
sample_digest_encoding, unit_ids, unit_ids_sha256, cells_per_unit`.
Counts are strict nonnegative integers, IDs are complete sorted canonical
strings, unit_ids_sha256 is the existing canonical JSON digest of that list,
sample digest encoding is the historical ordered JSON ASCII/newline format,
and `cells_per_unit` is the exact sorted ID-to-positive-integer map summing to
n_obs. Fresh controlled fixture preparation validates these original rows;
registration streams the assignment bytes and reconciles that admitted audit,
the actual report and split records. Later native/support/metric axes and selected
membership must match exactly. These units are simulated, never biological embryos.

Positive engineering fixtures must use **more than 48 source cells and at least
five original simulated physical units on each side**, actual all-axis null/z/TSV
and rank calculations, and the unchanged 500-finite-pair/80%/five-unit predicates.
One practical intended shape is a real complete final one-to-one ortholog table
and gene universes with 5,000 pairs, an actual complete checkpoint vocabulary and
configured native gene axes joining 502 pairs, and at least 500 genuinely finite
paired scores. All 5,000 coverage rows remain: 4,498 vocabulary-excluded, full
502-pair joined denominator, and no selected-list denominator or imputation.
The original paired-preflight genome-wide 5,000 and mapped-input 60% floors also
apply. The 502-gene axes are complete registered scoring axes, not later finite
subsets; original metric normalization still uses every prepared measured gene
before vocabulary filtering. Full peer populations must supply genuine frozen
same-bin support (at least50), at least two positive unequal peer means and
positive SD/nonconstant ranks; never force bins, replace the kernel or widen
tolerance to obtain finite rows.

That shape is a proposed acceptance fixture, not a runtime promise. Its actual
preallocation, precision/public-oracle parity, complete production/fresh replay
and inclusive900s/200MiB/4GiB fit must be measured. If it fails, preserve the
failure and pursue separate method-preserving acceleration; do not raise caps
or relax floors. A 129-cell/four-gene/two-unit fixture only proves refusal and
stored arithmetic; a 64-gene/two-unit finite fixture does not prove500/5.

### SourceBinding

Exactly:

```text
config, native_plan, full_preflight, support, species, phase, split,
model_arm, cohort_sha256, gene_ids_sha256, n_genes,
selected_membership_sha256, n_cells, embryo_ids, embryo_ids_sha256,
prepared_entries, registered_paired_inputs, metric_normalization
```

`config`, `native_plan`, `full_preflight` and `support` are original Refs.
The others are independently derived from their admitted bytes and the
Preparation closure, never accepted from final score tables. Keep original
config `gene_ids`, sorted exactly as the frozen native plan/kernel expects;
bind the complete axis and its digest, not a finite-score or focal subset.
Keep all original peer genes, including raw-zero/no-op candidates and positive
attempts that later have no matched target.

`prepared_entries` records are exactly:

```text
report_entry_index, source, prepared, survivor_digest, survivor_count,
split, n_obs, embryo_ids
```

Indices are strict nonnegative integers into the original report list. Refs
match `sha256`/`prepared_sha256` in that exact entry. Its `survivor_count` and
`survivor_digest` cover that raw source's complete post-QC survivors across
splits, not just one selected split; preserve that distinction. Selected
`n_obs` and physical IDs match the exact entry and split assignments.

For the project all-organogenesis manifest, every admitted native stage maps
to organogenesis. The complete training-ID union can therefore be derived
from genuine training entries, with no inference from `n_embryos`. For another
phase or mixed-phase report, these per-split lists alone are insufficient:
require a genuine source-bound phase-membership audit before registration;
do not assume that every reported split embryo occurs in the selected phase.
That audit would require a versioned contract extension, not an extra arbitrary
field in this closed v2. The synthetic profile is explicitly all-organogenesis
and independently reconciles its actual selected unit membership; it cannot
borrow the real five-human/43-mouse ID lists or supply only `n_embryos`.

`registered_paired_inputs` is the complete canonically sorted list of every
family member using this source, records exactly:

```text
comparison_id, side, paired_preflight, ortholog_table
```

`side` is `a` or `b`; the two files are Refs matching the family strings/hashes.
No unused, missing or repeated member is allowed. Independently reconcile all
four config/full-preflight inputs, both cohort hashes, full gene axes, table
orientation, phase/split/arm, method and prospective statistic of each paired
report. A source reused across members registers them all before production.

Metric normalization is exactly the approved three-field object:

```text
method=library_size_log1p
target_sum=10000
denominator=all_prepared_measured_genes_before_vocab_filter_clipping
```

### ProducerIntent and Checkpoint

ProducerIntent is exactly:

```text
schema, entrypoint, producer_file_sha256, software_commit_actual, checkpoint,
execution_context, producer_kind
```

`schema=b3_full_context_scoring_intent_v2`;
producer_kind is exactly `genuine_prospective_project_native_producer` for the
project profile or `controlled_synthetic_stored_arithmetic_producer` for the
synthetic profile. It must match the registration and issuer source admission.
`entrypoint` is an actual source-code Ref, and `producer_file_sha256` is its
complete explicit original scoring/dependency FileMap, authenticated as bytes.
It must include the actual executed entrypoint and unchanged scientific
implementation; a list containing old code without the actual new runner is
insufficient. No future source file gets a fabricated Ref/hash.
software_commit_actual is the actual original full40-character lowercase Git
commit of that admitted producer source, independently bound with the source
map before operation. Source admission authenticates that Git object and the
registered repository paths' blob bytes/modes against the live source map;
repository code absent from that commit cannot be described as committed there.
Start/witness/origin must retain it; current documentation
HEAD is not substituted. Missing genuine source identity is refusal, not null
or a fabricated commit. The issuer's actual source closure is separately pinned
in SourceAdmission, so neither map hides an executed new entrypoint.

Checkpoint is exactly:

```text
path, weights, config, gene_vocabulary, aux_vocabulary, vocabulary_assets,
model_arm, training_selection_provenance
```

`path` is the original canonical checkpoint-directory string; the next four
are actual Refs and vocabulary_assets is the complete original sorted asset
Refs closure. This binds weights as bytes without tensor loading, and binds
the complete gene/aux vocabularies. `training_selection_provenance` is null
for the base arm; for a finetuned arm it is a Ref to genuine complete project
training and candidate-selection provenance. The synthetic profile is base-arm
only, with null training provenance; actual fixture weights/config/vocab bytes
prove identity only and are not project model tensors or scientific effects.
A nominal directory name,
equal file size or weights presence cannot fill that field.

ExecutionContext is exactly:

```text
torch_version, numpy_version, execution_device, cublas_workspace_config,
normalization_chunk_rows, deterministic_algorithms_required,
deterministic_eval, stochastic_layers_disabled
```

The first four are explicit original/planned producer values, not wrapper
defaults; chunk rows is strict integer 8 and the last three are true. Actual
producer values must later equal the registered values and each other across
comparable sides. Metadata naming an execution device grants no permission to
use it. The registration/bridge consumer itself remains GPU-off/math-threads-1.

The bridge keeps the exact old `_compatible` factual requirements without
constructing sidecars: species distinction; method/score-definition; identical
phase, split, arm, normalization, checkpoint path/weights/config, complete
gene/aux vocabularies; matching original scoring-code projection; chunk8 and
actual deterministic execution context. It additionally binds the actual new
runner and its full intended code map. The producer's real source commit
remains original evidence, not the current documentation HEAD.

## 5. RNG contract: frozen policy, deferred outcome-derived subset

Exactly:

```text
schema, seed, draws_required, min_independent_embryos,
min_joint_valid_draws, max_shard_draws, source_order, embryo_order,
advancement, source_subset_rule, pair_subset_rule,
interval_rule, implementation
```

| Field | Exact value |
| --- | --- |
| `schema` | `b3_full_context_rng_registration_v1` |
| `seed` | Strict integer 20260930 |
| `draws_required` | Strict integer 2000 |
| `min_independent_embryos` | Strict integer 5 per source |
| `min_joint_valid_draws` | Strict integer 1900 |
| `max_shard_draws` | Strict integer 100 |
| `source_order` | `lexicographic_original_source_key` |
| `embryo_order` | `lexicographic_original_physical_embryo_id` |
| `advancement` | `draw_major_source_then_one_choice_per_original_embryo` |
| `source_subset_rule` | `union_of_original_keys_in_prespecified_bootstrap_eligible_members` |
| `pair_subset_rule` | `original_complete_joined_pairs_finite_both_once_then_fixed` |
| `interval_rule` | `frozen_valid_joint_max_abs_deviation_95th_percentile` |
| `implementation` | Actual Ref to frozen `scripts/b3_streamed_draw_schedule.py` |

Register all original keys and original intended embryo axes before outcomes.
The production RNG's used-source subset is determined later by the frozen
coverage/embryo eligibility rule, exactly as existing `execute_draws` and
`iter_bootstrap_draw_weights` do. Register that rule now; do not preselect an
eligible subset from unobserved scores, sample all planned-but-ineligible
sources into the production RNG, or change source ordering after observing
coverage. Unavailable members remain reported, but consume no extra production
RNG choices under the existing eligible-member policy.

The fixed finite pair set also cannot exist before scoring. Register the
complete one-to-one/vocabulary-joined denominator and the existing finite-both
selection rule; derive that set once in the observed bridge, then keep it
fixed for every draw/replay. No imputation, pruning, changed null peers, redraws
or manufactured RNG/old-sidecar origin. This receipt generates no draws.

## 6. Closed registration payload, result and publication

`registration.json` has exactly:

```text
schema, method, statistic, registration_profile, prospective_request, family,
family_sha256, model_arm, comparison_ids, source_keys, decision_evidence,
preparation, source_bindings, producer_intent, issuer_source_admission,
rng_contract, source_files, consumer_file_sha256
```

`schema=b3_full_context_family_registration_v2`,
`method=b3_measured_zero_peer_null_v2`,
`statistic=B3_measured_zero_peer_null_v2_z`.
`prospective_request` is the original persistent register request Ref, even
on replay. source_files is the exact sorted deduplicated existing-file Ref
closure derived from every binding above. It never includes future scored
outputs. The payload binds exact original paths, including both byte-identical
but separately addressed split files. Its digest is frozen canonical JSON
SHA256 using the existing family `digest` convention.

`summary.json` has exactly:

```text
schema, status, phase, method, registration_profile, request, registration,
registration_sha256, execution_catalog, consumer_file_sha256,
flags, resources
```

`schema=b3_full_context_family_registration_result_v2`;
status is `complete_metadata_registration` for the project profile and
`complete_synthetic_metadata_registration` for the synthetic profile.
request is the current public request
Ref; registration is the actual owned published payload Ref after writing.
execution_catalog preserves the phase-specific input. All scientific facts
and payload bytes must be bit-exact on fresh replay; current request/output
addresses, phase, elapsed/resource observations and marker refs are invocation
facts and are bound separately.

Flags is exactly:

```text
registration_inputs_byte_verified=true
family_source_keys_and_rng_frozen=true
independent_registration_metadata_replay_verified=(phase==replay_registration)
registration_before_first_scored_outcome_verified=false
producer_origin_verified=false
controlled_synthetic_operation_order_verified=false
synthetic_original_native_origin_verified=false
synthetic_fixture_only=(profile==synthetic_stored_arithmetic_v1)
method_only_engineering=(profile==synthetic_stored_arithmetic_v1)
native_likelihood_effects_attested=false
model_forwards_performed=false
checkpoint_tensors_loaded=false
full_pipeline_integration_complete=false
scientific_readiness=unavailable
interval=null
```

Resources is exactly:

```text
max_seconds, max_rss_bytes, max_numeric_working_bytes,
min_available_host_ram_bytes, min_free_disk_bytes, math_threads, gpu_enabled,
prefinal_elapsed_seconds, public_elapsed_seconds,
peak_rss_bytes, peak_live_numeric_bytes
```

The immutable summary records `prefinal_elapsed_seconds` only at its named
serialization boundary. `public_elapsed_seconds` is exactly null in that
summary, because the complete public return follows final source/artifact
seals and cleanup. A supervised caller records the complete public clock
externally; it must not rewrite an already sealed summary or marker.

Limits are section 10's unchanged values. Missing/contradictory required
evidence, absent intended producer source, unavailable finetuned provenance,
source changes or exceeded resources cause refusal and no complete marker.
Do not create a consumable registration with null mandatory refs. Metadata
inspection may report such missing gates separately, but is not this completed
publication type.

Publish exactly registration.json, summary.json and complete.json in a new
owned output directory. complete.json is exactly:

```text
schema, registration, summary
```

`schema=b3_full_context_family_registration_publication_v2`; both records are
actual final-file Refs. Seal data/directory with fsync before exposing the
marker, then retain ownership and reauthenticate sources/generated/marker
bytes, caller/canonical directory aliases and live identities through final
cleanup and deadline checks. Finish helper/private/primary cleanup before the
last byte/alias seal; only guarded trusted terminal descriptor releases follow.
Their exceptions still invalidate owned completion, but this cooperative
boundary promises no arbitrary concurrent mutation/relocation immunity after
the final seal or return. Any late failure invalidates only this writer's
owned marker, preserving a foreign directory/marker replacement. Input and
planned producer namespaces are protected from publication.

## 7. Controlled-execution dependency and strict origin admission

This section closes the required evidence interface; it does not create a
trusted issuer, accepted controlled run or project scoring authorization.
The prior software dependency is a narrowly scoped intended
`capture_b3_full_context_controlled_execution.py` and its registered producer
hook. Its own execution closure must be derived from the actual implemented
entrypoint/imports and independently reviewed before use. Do not guess that
closure from native67 or add the issuer to bridge80/v483: the bridge reads its
source and evidence **as data** and never executes it. No issuer file or SHA
is claimed to exist by this design. Absent accepted issuer software, metadata
inspection/refusal is addressable, but completed registration requires actual
source refs and positive comparison is unavailable.

### Trusted origin, source admission and runtime pin

The admitted owner or source-bound acceptance harness must capture the actual
controlled run and pin its accepted runtime admission outside the untrusted
comparison request. The authority is an existing trusted local execution
boundary, not a key the request can create. Before implementing positive compare,
separately review its concrete authority resolver and capture contract. A public
request cannot choose/replace the authority ledger, add a trusted issuer, provide
an allow-all callback, or make a supplied Ref trusted by naming it `approved`.
If no externally admitted authority pin is available, refuse compare and leave
project chronology/origin false. Do not silently fall back to JSON consistency.

Within that cooperative boundary, SourceAdmission has exactly:

```text
schema, authority_id, issuer_id, registration_profile, family_sha256,
source_keys, issuer_entrypoint, issuer_file_sha256, producer_intent_sha256,
operation_kind, transition_contract, resource_policy, source_reviews
```

`schema=b3_full_context_controlled_source_admission_v1`;
authority_id/issuer_id are canonical nonempty IDs already admitted by that
authority. Profile/family/keys match registration. issuer_entrypoint is an
actual Ref and issuer_file_sha256 its complete explicit actual FileMap.
producer_intent_sha256 is the exact sorted original-key-to-canonical-intent-
digest map, independently matching every registered ProducerIntent.
operation_kind is `project_native_scoring` or
`synthetic_native_stored_arithmetic`, exactly profile-dependent.
transition_contract is `registered_start_durable_before_computation_v1`.
source_reviews is exactly `spec, standards`, both actual independently accepted
review Refs binding these exact issuer/producer bytes, with zero blocking findings.
resource_policy is the closed constant Limits record defined below.
Authenticating its JSON and source hashes is source admission, not run evidence.

AuthorityPin is a separate immutable **external** record with exactly:

```text
schema, authority_id, registration_profile, attempt_id, source_key,
registration_sha256, issuer_source_admission, runtime_admission, acceptance
```

`schema=b3_full_context_controlled_run_authority_pin_v1`; issuer_source_admission
and runtime_admission are actual Refs, acceptance is an actual independent
run-admission/acceptance Ref from that owner/harness. The authority resolver
provides the expected pin Ref and exact byte SHA from its separately admitted
launch scope, not from this request's fields. Verify its complete bytes and
all identities. A forged internally consistent pin, a copied acceptance,
source code alone, timestamps, process IDs or a producer-supplied assertion
must not introduce a new authority or accepted run. This is explicit trust in
genuine retained local capture, not a cryptographic proof against a malicious
trusted owner, a new signature system, or evidence of prior human knowledge.

### Controlled producer sequence and original start

The issuer and producer hook must actually own these transitions:

1. Freeze actual issuer/producer/input bytes, invocation and resource policy;
   reject existing outcomes for this attempt. Independently replay the admitted
   metadata registration, source key, complete cohort/axes/checkpoint/context.
2. Producer durably seals its original start, then the issuer verifies its
   bytes/ownership and supplies a single-use permit through an issuer-owned
   control channel. The registered producer cannot enable computation before
   this permit; it cannot import a caller-supplied completed start or permit.
3. Execute the registered operation. Seal original native outputs/provenance,
   exact source-before/after and controlled event witness. Preserve failed
   attempts; failure cannot become a complete witness or runtime admission.
4. An independent admitted supervisor/harness seals actual raw invocation,
   transition/completion and resource observations into RuntimeAdmission and
   publishes the authority pin. The producer then emits Origin referring to
   those already complete predecessors. Consumers only validate, never rerun
   this producer or fabricate its history.

Project producers must retain genuine complete original likelihood vectors,
all positive attempts including no-matched-target attempts, and whole-axis
raw-zero/no-op eligibility needed by the separate effect consumer. None is
supplied by registration. Synthetic operations may generate stored arithmetic
inputs with zero tensors/forwards, truthfully marked constructed; their history
does not attest real project likelihoods.
Retain unchanged original native declarations and byte/code closures at their
actual scope: helper/scoring-source byte identity is not proof that a model
executed. The synthetic envelope binds the actual fixture producer and public-
operation history separately; it must not falsely claim execution of old107/109
project producers or import a fabricated old score bundle. If genuine fixture
output cannot satisfy unchanged native admission with truthful fields, refuse
and review that dependency; never loosen native67/69.

ProducerStart has exactly:

```text
schema, status, method, registration_profile, attempt_id, source_key,
registration_result, registration_sha256, issuer_source_admission,
producer_intent_sha256, source_binding_sha256, producer_entrypoint,
producer_file_sha256, software_commit_actual, execution_context,
checkpoint_tensors_loaded, model_forwards_performed
```

`schema=b3_full_context_producer_start_v2`; status is `ready_to_score` for
project or `ready_for_synthetic_stored_arithmetic` for synthetic. Method is
the frozen constant; both last booleans are false at this pre-computation
transition. attempt_id is a unique canonical ID fixed before the operation;
it never replaces original source keys in family/RNG. Actual source commit
and entrypoint/map must equal registration, not current documentation HEAD.

TransitionPermit has exactly:

```text
schema, registration_profile, attempt_id, source_key, issuer_id,
issuer_source_admission, registration_sha256, producer_start,
process_identity, permit_nonce, operation_kind
```

`schema=b3_full_context_controlled_transition_permit_v1`; nonce is a unique
canonical nonempty attempt-local token fixed by the issuer; process_identity
is exactly `pid, start_nonce`, strict positive pid and issuer-owned canonical
start nonce. The actual control-channel release follows durable start admission;
this published metadata projection is not itself a reusable authorization.

### Completed controlled witness and raw runtime admission

ControlledWitness has exactly:

```text
schema, status, registration_profile, authority_id, issuer_id, attempt_id,
source_key, issuer_source_admission, registration_result, registration_sha256,
producer_start, transition_permit, producer_intent_sha256, source_binding_sha256,
producer_entrypoint, producer_file_sha256, software_commit_actual,
execution_context, invocation, source_before, source_after, events,
native_plan, native_producer_provenance, native_catalog,
resource_observations, checkpoint_tensors_loaded, model_forwards_performed
```

`schema=b3_full_context_controlled_execution_witness_v1`, status is
`complete_controlled_execution`. The predecessor/output fields are actual
original Refs. invocation is exactly `argv, cwd, process_identity` with complete
actual string argv, canonical cwd and the same process_identity. source_before
and source_after are complete sorted persistent-input Refs closures derived
from registration/source admission, including all actually executed code,
prepared/raw/checkpoint/plan/support assets; the same path/hash/size set must
match. Generated output refs are bound separately, not invented into the
before-input map. All source/registration/intent/key/context bindings must agree.

events is exactly four ordered records, each with exactly
`ordinal, state, previous_event_sha256, artifact, monotonic_seconds,
process_identity`. Ordinals are strict0,1,2,3; states respectively
`registration_replayed`, `producer_start_durable`, `computation_enabled`,
`native_publication_complete`. artifact is respectively the original registration
result, original start, issuer permit, original native catalog Ref. First
predecessor digest is null; later ones are the frozen canonical digest of the
previous complete event. Finite nonnegative monotonic observations are strictly
increasing and process identity matches. These checks reconcile **already
trusted actual transition capture**; an invented ordered event list is not
chronology evidence. Raw capture must show durable-start acknowledgement and
issuer-owned permit release preceding the first producer computation/outcome.

RuntimeAdmission has exactly:

```text
schema, status, registration_profile, authority_id, attempt_id, source_key,
issuer_source_admission, controlled_witness, invocation_record,
supervisor_entrypoint, supervisor_file_sha256, supervisor_state,
gnu_cost, stdout, stderr, argv, cwd, resource_policy,
source_freeze_before, source_freeze_after, exit_codes, admission_reviews
```

`schema=b3_full_context_controlled_runtime_admission_v1`, status is
`accepted_actual_controlled_execution`. Witness/invocation/supervisor state/
GNU/stdout/stderr are actual retained Refs. Supervisor entrypoint is an actual
code Ref with complete actual FileMap. Its own independent supervisor must be
admitted by the authority, not the producer under another filename.
invocation_record is a captured record with exactly
`schema, attempt_id, process_identity, argv, cwd, issuer_source_admission,
resource_policy, source_freeze_before, started_monotonic_seconds,
finished_monotonic_seconds, return_code`, schema
`b3_full_context_controlled_invocation_v1`. Exact actual argv/cwd/process,
positive elapsed order, strict0 return code and retained freeze refs reconcile
with raw supervisor and witness, not a normalized imagined command.
source_freeze_before/after are actual snapshot Refs containing exactly
`schema, files`, schema `b3_full_context_controlled_source_freeze_v1`, files
the identical complete sorted input Ref set also recorded in the witness.
exit_codes has exactly `issuer, producer, supervisor, gnu`, all strict integer0.
admission_reviews is exactly `spec, standards`, actual independent acceptance
Refs binding this exact source/witness/raw-runtime closure with zero blocking
findings. Acceptable authority generation of these records remains an actual
upstream dependency, never a declaration inside the public request.

Limits is exactly `public_seconds, supervisor_seconds, rss_bytes,
numeric_bytes, min_available_ram_bytes, min_free_disk_bytes, cpu_threads,
cuda_enabled`: strict constants900,950,4294967296,209715200,4294967296,
21474836480,1,false. Controlled fixture operations respect these unchanged
caps; project use remains unavailable without independently authorized actual
scoring/data/hardware admission. resource_observations is exactly
`public_elapsed_seconds, supervised_elapsed_seconds, gnu_wall_seconds,
peak_rss_bytes, peak_live_numeric_bytes, min_available_ram_bytes,
min_free_disk_bytes, cpu_threads, cuda_enabled`; actual finite nonnegative
clocks retain their separate scopes, strictly measured counters obey Limits.
Complete public time includes helper load, checks, publication/seals/cleanup.
RuntimeAdmission independently reconciles witness observations with raw
supervisor/GNU; a positive public-only time cannot mask a failed outer seal.
All source reviews bind pre-existing software bytes; run-admission reviews
bind already captured witness/raw-runtime bytes. None points forward to its
containing admission record. The later authority acceptance may bind the
completed RuntimeAdmission but cannot point forward to its own AuthorityPin.
This ordering and Origin-last publication prohibit review/envelope hash cycles.

### Origin envelope, acyclic binding and fresh replay

ProducerOrigin has exactly:

```text
schema, method, registration_profile, attempt_id, source_key,
registration_result, registration_sha256, producer_start,
issuer_source_admission, controlled_execution_witness, runtime_admission,
producer_intent_sha256, source_binding_sha256, producer_entrypoint,
producer_file_sha256, software_commit_actual, execution_context, native_plan,
native_producer_provenance, native_producer_provenance_sha256, native_catalog,
gene_ids_sha256, embryo_ids_sha256, selected_membership_sha256
```

`schema=b3_full_context_producer_origin_v2`. Actual original native provenance
and catalog remain referenced under their unchanged native schemas. Neither
catalog nor witness/runtime admission points forward to Origin. Origin is
emitted last and binds their actual Refs; this prevents a hash cycle or any
manufactured old score sidecar. Each comparison observed_sources leaf stays
exactly `observed_publication, producer_origin`, both Refs. The origin explicitly
supplies the mandatory witness/runtime bindings; both must also match the
externally resolved AuthorityPin for this registration/key/attempt/profile.

Fresh bridge admission/replay first resolves that external authority pin and
authenticates SourceAdmission, witness, raw RuntimeAdmission and their complete
bounded typed closure as bytes. Metadata files are each at most64MiB, closures
explicitly derived (no directory scan), with aggregate parsed/retained buffers
reserved. Then independently reconcile registered start/transition/completion,
actual argv/code/source freeze/context and original outputs before replaying the
publisher. Native plan/catalog/provenance, original source commit, all complete
gene/unit/support/metric/membership axes must equal registration and the
publisher's OriginalFacts, including unavailable rows. Changed code, authority,
nonce, output/source path, commit, closed field set, order, input hash, failed
runtime, missing start/witness/authority or a legacy retrofit is strict refusal.
Replay retains original trusted history; fresh arithmetic replay is not fresh
production chronology and must never emit another origin.

For the project profile only, an admitted actual project run permits
registration_before_first_scored_outcome_verified and producer_origin_verified
to be true. Synthetic comparison instead keeps those project flags false and
can set controlled_synthetic_operation_order_verified and
synthetic_original_native_origin_verified true from its genuine admitted run.
Metadata register/replay keeps all four false. Both paths keep likelihood
effects/reportability unavailable. Historical genuine v2 imports retain their
own six-file lineage; absent original fields cannot be filled by this envelope.

## 8. Addressable engineering and acceptance seams

Build now, without actual full scored shards: phase-specific registration
parser, exact closure/ref admission, existing-family validation, metadata
reconciliation, complete source/selection/checkpoint identity projections,
owned publication/fresh replay, strict refusal, and typed start/witness/runtime/
origin validators. Keep metadata validators inside the existing deep bridge
Module. Source admission, controlled issuer/producer enforcement and the
non-request authority resolver are prior separately reviewed dependencies;
until accepted, compare refuses for both profiles. Consistent software-only
metadata fixtures cannot establish controlled or project history.

Adversarial public cases must cover: source-key alias/renaming; missing/reversed
members; omitted registered paired inputs; wrong arm/cohort/gene axis; attempted
finite-output inputs; differing checkpoint/code/chunk/determinism context;
stage constants masquerading as physical IDs; changed/cross-split duplicated
physical IDs; raw-survivor versus selected-split denominator confusion;
modified recovery/split evidence; partial source/provenance inventory;
future nonexistent Ref; late same-inode mutation; symlink/FIFO rebinding;
foreign marker/output replacement; cleanup/deadline failure; changed prior
register request; fake timestamp-only origin; start/registration mismatch;
missing actual producer source; finetuned weights without genuine provenance;
and unavailable members changing the production RNG's eligible-source subset.
Also require: unadmitted issuer/authority, a request introducing its own pin,
copied/fake acceptance, changed captured argv or supervisor source, missing/
reordered permit, complete-looking witness with failed raw supervisor, source
freeze mismatch, profile mixing, synthetic history relabeled project, and
nonexistent controlled-source refs. These are public refusal controls, not
positive coverage proof from monkeypatched authority/admission.

The 129-cell/4-gene/2-unit and64-gene/2-unit fixtures exercise refusal and actual
stored arithmetic, but do not establish500/5. A positive synthetic bridge/v4
fixture uses section4's actual preparation and admitted controlled producer
history, complete502 joined denominator within a genuine5000 genome-wide table,
>=500 actual finite scores/80% coverage, >48cells and>=5 original simulated
units per source, and actual public source reconstruction/replay. It is method-
only eligibility evidence, not project outcomes, biological independence,
effects, a 2,000-draw or whole-cost acceptance. Runtime fit remains measured.

Dependency order: review this v02 contract → implement/validate bridge metadata
register/replay and refusal paths → separately accept actual controlled issuer,
producer hook and authority resolver → actual profile-specific controlled run
and independently admitted original native history → independent complete
observed publisher replay → comparison/fixed-family admission → v4 full-axis
unit controls and bounded traversal → complete authorized family/replay and
effect/reporting/cost gates. Synthetic acceptance never clears the real input,
training, chronology or likelihood-effect gates. No step supplies a missing
upstream fact by manufacturing an old receipt.

## 9. Existing evidence frozen by this static read

Paths below are relative to repository root. SHA256s authenticate this draft's
static source of facts only; raw/H5/checkpoint data were not freshly scanned,
imported or executed for this draft. Original recorded asset digests retain
their original evidence scope.

| Existing record | SHA256 |
| --- | --- |
| docs/adr/0005-b3-feasibility-before-full-cohort-expansion.md | ac943ea44047957addbc4b8de7d672e34e1c246bd20471820e4dd1355987a994 |
| docs/agents/b3-paired-comparison-decision-proposal-2026-09-30.md | eb8e5ff307bfc54cfe32a792fe0d67a75ed5d73196283b1d47a2a3ce52f7c648 |
| docs/agents/b3-deletion-score-decision-2026-09-30.md | 5eac3a43f15c6869497180f8228948cedf9b217410fc388f165cb56e56c7ca59 |
| docs/agents/b3-null-method-review-2026-09-30.md | 4519a1b06e0d85e8ec626736277abbe208d76361892a35e1cd7ea296b9ce8bbf |
| docs/agents/b3-measured-zero-owner-decision-2026-10-01.md | 1587713676b43d420ec6db6fb3d568356ad5887bf2e29ecda3a6314240f3f014 |
| docs/agents/b3-recommendation-implementation-2026-09-30.md | c703bdfaaf5cff253b6809d64252f054a61ac61a2fae3e4f8efd992d2028bda7 |
| runs/b3_pilot/full_organogenesis_v3/manifest.json | e3190a9e14bd0f17157891033096e5fb3bbe7585d3932d26ae2834d3633f649f |
| runs/b3_pilot/full_organogenesis_v3/prepared_run/preparation_report.json | 8ec35395a8bc375e4cd1c0c76aedf85d87555b59a33dec109f1cbe730a6d6532 |
| runs/b3_pilot/full_organogenesis_v3/prospective_split_plan.json | 87ccff66735139dd11944f9d355185670befd73ee7b1f3de1417cbb4ff9e0210 |
| runs/b3_pilot/full_organogenesis_v3/prepared_run/split_assignments.json | 87ccff66735139dd11944f9d355185670befd73ee7b1f3de1417cbb4ff9e0210 |
| runs/b3_pilot/full_organogenesis_v3/homo_sapiens_support_config.json | 2624358168ed815ec1d4d7c7589f87a31b7cf0535f7004f7136b10b156745132 |
| runs/b3_pilot/full_organogenesis_v3/mus_musculus_support_config.json | 2b12ba00de1173dfe2ae136125425be7f6af5025540493b26d39e06829adb055 |
| runs/b3_pilot/full_organogenesis_v3/human_measured_zero_support/support_preflight.json | 03c1071f03f84b66daf93dfa9864dbdb0c1e4860be060ade02e8fec74cf043d0 |
| runs/b3_pilot/full_organogenesis_v3/mouse_measured_zero_support/support_preflight.json | 819d751f16e6c5c63f6c0ef92a9788fe5cd890d14759b16226143891887e88ae |
| runs/b3_pilot/full_organogenesis_v3/paired_measured_zero_support.json | 1f79d92fa2e63c0ee924b9b2d8e6112650801182b2fa5788560b11585972a27e |
| runs/b3_pilot/full_organogenesis_v3/human_native_shard_plan.json | b06233309be599e05c8bff01c2aea2b4df276f28fd853aae786ad54bd7141fa2 |
| runs/b3_pilot/full_organogenesis_v3/mouse_native_shard_plan.json | 559c87f71fa4ad220305a827ca11d8d1907d81c911af2926cc10473e4a888c8f |
| runs/b3_pilot/embryo_recovery_final/recovery_report.json | d492aba33b36b05ca929ee26f40961389fa9b44749032e39334197392c713c8c |

The real report's complete training physical IDs are:

| Prepared source | Cells | Exact IDs |
| --- | ---: | --- |
| Human CS12–CS16 | 123952 | emb1, emb2, emb5, emb6, emb7 |
| Mouse E10.5 | 222337 | tome_cao_embryo_24, 25, 26, 4, 46, 5, 59, 6, 60 |
| Mouse E11.5 | 319717 | tome_cao_embryo_27, 47, 48, 49, 50, 61, 62, 8, 9 |
| Mouse E12.5 | 160318 | tome_cao_embryo_11, 12, 13, 34, 52, 64 |
| Mouse E13.5 | 146334 | tome_cao_embryo_15, 35, 36, 53, 66, 68 |
| Mouse E9.5 | 96683 | tome_cao_embryo_1, 19, 20, 21, 22, 3, 40, 41, 42, 55, 57, 58, 63 |

Each abbreviated mouse number carries the full `tome_cao_embryo_` prefix;
actual committed axes retain full strings and ordinary lexicographic ordering.
These original report facts sum to five human and 43 mouse training embryos;
the list evidence, not a count, establishes the candidate axis. Full-preflight
JSON itself contains only n_embryos. The eventual genuine native axis must be
identical to the admitted source/proof/metric identity evidence.

Manifest-bound recovery sidecar commitments, as originally recorded:

| Sidecar under runs/b3_pilot/embryo_recovery_final/ | Recorded SHA256 |
| --- | --- |
| E10_5_embryo_ids.csv | fbed0147738b04d56b7a0a7022e045fb57065428d3c39907625c52c2f4620d55 |
| E11_5_embryo_ids.csv | d3475f811a3e0a8a9600a58e68c034e8c2cb668cc581c8dce66c491864fed358 |
| E12_5_embryo_ids.csv | 675ba985b204fe2793cbb743369e9b8d67a9255b147701a4bb8b5dc318b6887d |
| E13_5_embryo_ids.csv | 8f6918f70bb54959789bb623b2d56a2cf0ea80a7cc048df4eed72d6f3c48d850 |
| E9_5_embryo_ids.csv | d2ad2d0810087611b66ce81b31d604f159cb33c2d40cab88b0f503ee17a76eaa |

The author annotation is
`runs/b3_pilot/source_metadata/GSE186068_cell_annotate.csv.gz`, recorded
48,824,294 bytes and SHA256
91e999adecbb1714d31758aaf1373e579b0523a5df0f42722d35e6b5a1b64187.
The preparation fingerprint is
9b3a1ffdf85823f0a7e098442b60ba50c04a8f63890ba41775be1dd79ac06e6a.
Human/mouse full cohort hashes are respectively
e2259aeb4c6e7d8560d34b95eba513e7fb508ab6297335028d9322dea6ce98c8 /
cc15e2e7bd18c0b074d70925fbcef3f9a3558f3b544de257b7b5538977d56724.
Raw/prepared/survivor digests come from the complete original report and
full-preflight cohort sources; copying selected examples is not full closure.

The support configs explicitly say `full-cohort necessary support diagnostic;
cannot be passed to bounded score producer`. The native plans remain
`planned_storage_only`. Neither file is a full inference runner or scored
input. Do not relabel them to overcome the bounded producer's row/cell caps.

Useful actual seams: native catalog original provenance/common admission at
`scripts/b3_native_catalog_pages.py:273`; family validation at
`b3_measured_zero_bootstrap.py:47`; existing pre-inference complete registered
paired inputs at `scripts/produce_b3_measured_zero_scores.py:194`; complete
metric/cohort evidence at `preflight_b3_measured_zero_full.py:437`; exact
prepared identity/split checks at `finetune/artifacts.py:200`; source report IDs
at `finetune/prepare.py:360`; old comparator requirements at
`summarize_ortholog_measured_zero_v2.py:132`; original eligible-source RNG order
at `b3_measured_zero_bootstrap.py:270` and
`scripts/b3_streamed_draw_schedule.py:147`.

## 10. Cost and real-data gates

Every public call stays at 900 seconds inclusive of admission, source hashing,
replay, serialization, fsync, publication seals and cleanup; supervisor950,
RSS4 GiB, live numeric200 MiB, available hostRAM4 GiB, free disk20 GiB after
reservation, one math thread, GPU off. The registration path uses no numerical
arrays or checkpoint tensors. Full raw/prepared/weights byte admission can
itself be costly; full registry cost is unmeasured and cannot be waived by an
old receipt or forecast. New registry/bridge/v4 calls need separate bounded
measurement after implementation acceptance.

Project blockers are concrete: no genuine prospective full-context family/
source-key/producer origin currently established; no authenticated executable
full inference runner; no actual complete scored native shards/effect vectors;
no original full-axes observed comparison; nominal finetuned weights lack
verified project training/candidate-selection provenance; and no accepted
complete method/family cost. Metadata validation and present prepared sources
cannot supply any of these. The real runner's historical roughly15 GiB RSS/
16 GiB guard does not fit the unchanged 4 GiB/GPU-off public scope.

No new scientific choice is needed to implement/replay the closed metadata
validator and refusal paths with the existing exact corpus and approved rules.
Authentic data/origin production is an evidence/implementation dependency,
not permission to reinterpret the method. Scientific input is required only
if the owner wants to change the complete comparison family/cohort policy,
physical-embryo identity/independence interpretation, likelihood/null/bin/zero
rule, eligibility/reporting thresholds, seed/draw policy or uncertainty. An
unknown author's physical identity mapping cannot be invented as engineering.

Existing pilot5111/15705=32.54%, 0/2000 necessary jointly supported draws and
its reporting veto remain. No2k permission is inferred. The10-draw measured
public423.59/463.82 and whole supervised526.31/642.81 scopes stay separate;
the49.30-hour200+200 public-calls-only projection leaves398 calls, aggregation
and seals unmeasured. Registration adds no project effect or reportability claim.

## 11. Exact prospective software path sets

Let N be the explicit 58 Python paths/hashes in the source table below. At
implementation time verify that exact path set; a scan may detect additions
but must not silently redefine N. The intended canonical bridge/v4 source
files do not yet exist; their hashes must be frozen from actual reviewed
canonical bytes later. An ignored draft hash is not a canonical-source Ref.

Original native67 = N plus exactly:

```text
scripts/prepare_b3_paged_native_cache.py
scripts/b3_native_catalog_pages.py
scripts/prepare_b3_paged_native_context.py
scripts/bootstrap_b3_streamed.py
scripts/reduce_b3_streamed_fixed_pairs.py
scripts/replay_b3_sparse_null.py
scripts/b3_windowed_native.py
scripts/b3_h5_attribute_admission.py
scripts/replay_b3_prepared_sparse_session.py
```

Common69 adds exactly:

```text
scripts/prepare_b3_paged_native_common_source.py
scripts/b3_authenticated_helpers.py
```

Publisher70 adds exactly:

```text
scripts/publish_b3_full_context_observed.py
```

Bridge80 adds exactly these nine existing helpers and its actual new self:

```text
scripts/summarize_ortholog_measured_zero_v2.py
scripts/summarize_ortholog_paired_scores.py
scripts/build_ortholog_table.py
scripts/handoff_ortholog_scores.py
scripts/report_ortholog_eligibility.py
scripts/summarize_ortholog_full_universe.py
scripts/b3_score_contract.py
scripts/b3_streamed_bootstrap.py
scripts/b3_streamed_draw_schedule.py
scripts/bridge_b3_full_context_observed.py
```

V4 83 adds exactly:

```text
scripts/replay_b3_sparse_bootstrap_draws.py
scripts/replay_b3_streamed_sparse_blocks.py
scripts/bootstrap_b3_full_context_common_source.py
```

Register/replay executes only authenticated needed metadata functions, without
calling old bundle/H5/model/numerical paths. Preparation/scoring/recovery code
and checkpoint assets are original provenance data refs, not automatic
execution permission. A future producer hook has its own genuine explicit
code closure; it cannot borrow bridge80 or unchanged original67 as its actual
runner inventory. Any newly executed dependency changes the prospective
consumer path set and requires a fresh closure/review.

### Native source table N (static snapshot)

| Canonical path relative to repository root | SHA256 |
| --- | --- |
| src/transcriptformer/__init__.py | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| src/transcriptformer/cli/__init__.py | 8173662ae3ee09cac7f8a9e46f5fc6817d13908b05926373eade4e740e7a9e09 |
| src/transcriptformer/cli/download_artifacts.py | 45f51bbcb76fcc6a1454fd8f249c814070b05020bee16ab9dc6f823e24ed4c29 |
| src/transcriptformer/cli/download_data.py | 6b7839d924ec54c1b1fbdc4642d9aaff175721a9a589380d0eab2fafb3a376dc |
| src/transcriptformer/cli/evaluate.py | 514205f44b5fbc47cd9839259c52061b33a04890b8ab2d292e2e0bb2773b456e |
| src/transcriptformer/cli/finetune.py | 2cc67b11d642a670a35e823a341039166b2e48514c151adfb0a4d133798605ff |
| src/transcriptformer/cli/inference.py | aeaa66a6f58ab8b452f37b62d3ad37d548eafbadcfea6926de5349e5ac8308c5 |
| src/transcriptformer/data/__init__.py | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| src/transcriptformer/data/bulk_download.py | 6f4f2ad5be69363190e5ffa8699c48e30e66ce1648a3a0aba560518d77b98517 |
| src/transcriptformer/data/dataclasses.py | 29ac8a4f45b77cf919cbd0a377b0008668c6fbcce90939d970c9cae56a66b8ae |
| src/transcriptformer/data/dataloader.py | 685dc3c80e6e5cd792659045e176036affef9a92032337cbe00e555e4412e617 |
| src/transcriptformer/datasets.py | d9f92726b108824a075035aa9ae4ccd8b5a8c02bbac4facb136e7e12c51b7fcb |
| src/transcriptformer/finetune/__init__.py | 8dd33a458684e04325cfe1be6391dea796c945feff3a0e2051fb345a1e8135a6 |
| src/transcriptformer/finetune/artifacts.py | 7533d7a27942a554c17cc62be1be97025670304fb5d7872899d54d968479ace8 |
| src/transcriptformer/finetune/b3_aggregation.py | a5f815e76481539506ca6366d46391fdd186ae00b5c1d4a4395280278cb8a178 |
| src/transcriptformer/finetune/b3_bins.py | 59074199f5f74c4f34528438c9fbd281a0c14d45d03706ec654a458ae4621dca |
| src/transcriptformer/finetune/b3_bootstrap.py | c42e8070fd48b9142a7d50274f838426990bea4c03b4c618b028be6801ff756d |
| src/transcriptformer/finetune/b3_cell_stream.py | d62d0fd30de25dde4866ff551c43dfd876b742d6dcdb4d19372de3b4e8894bef |
| src/transcriptformer/finetune/b3_gene_id.py | 94d680baeb6b5315a7f6d775b701968518271d3c757abfc9b05fef563cfa34a4 |
| src/transcriptformer/finetune/b3_identifiers.py | 3b9d9d5462e447e0a4d8d3eb3f7bceb125010d8cb68219d76215a92bc8046247 |
| src/transcriptformer/finetune/b3_matched_null.py | 5cb3095ba497a18cf4c4cbc4cfbdb42f416938bd57404fa7fc9e4172fecee283 |
| src/transcriptformer/finetune/b3_measured_zero.py | 18115a2780965c9b258ff06fa52367ad819192668b300c320feaf2bf8733484d |
| src/transcriptformer/finetune/b3_measured_zero_bootstrap.py | a3a5f740a7e3521e61f0076baca10c4256ae839c4887a5f4f50ffaafc19d2683 |
| src/transcriptformer/finetune/b3_measured_zero_prepared.py | 537bae6885198585940cf0c9a4a8818bc6c8935f7679f87d674c4df2f45611d4 |
| src/transcriptformer/finetune/b3_measured_zero_scores.py | 8a6f23d7b0fdc761258c0922dc0d7ba19471bc5a6696d7191ec3da04b0fd8c65 |
| src/transcriptformer/finetune/b3_measured_zero_shards.py | 08ce6479fbd2658d88caad83c0bb32c3047e75b30d0248382e5d1ecfffada66e |
| src/transcriptformer/finetune/b3_pipeline.py | 8720c1f081d9acb61673931a00d9ec5196870a7adf2cf08301f7ae66e233b7a8 |
| src/transcriptformer/finetune/b3_prepared.py | d261c760d29dd7b50ec652b4c70d81f42a15c3c6ca1b2ff1a71f018e76bbcc57 |
| src/transcriptformer/finetune/b3_raw_artifact.py | fc4e2ac7f42d5fa3a19fcf2eadfa2c27a301282528681e3caaed0fe043338159 |
| src/transcriptformer/finetune/b3_score_contract.py | f8da0dc0a37f46916e2503a5d3e92b011f682132113846c201b538b17cbc96ec |
| src/transcriptformer/finetune/coordinates.py | 6b62faa663e03e67812dccf7537163dacba59ffdffc141c35ac2278404b315af |
| src/transcriptformer/finetune/coverage.py | 4b6bae38aecaa74824af15d5864962b0a372aae8bab7d9fb28e73bb9d1404b81 |
| src/transcriptformer/finetune/early_stopping.py | 73b1ec0c841bae457aea1289160c813a0f5f00b3cc587277bedee2e9b11a7996 |
| src/transcriptformer/finetune/embryo_identity.py | 9904fa2770d502afb9daac0452b42bb138b7dcb609dcc36c9c32fdb7097cdaba |
| src/transcriptformer/finetune/evaluate.py | c840c846b2b3d1748de108271954224eae30b9b0a7b61296f52e5a0f6b176f3e |
| src/transcriptformer/finetune/gpu.py | 7f25833d2dd616da68ce78d1f6945dc0176490d881faa243797e3d91bf8a6b30 |
| src/transcriptformer/finetune/manifest.py | c8e2e3d821ebffc3c5472a9d6507873db23b0898567ca0b77dbecf18e273a9f3 |
| src/transcriptformer/finetune/prepare.py | 0cd93a0d9925fded3a6dc6f636eae81bf389020695de3e480998ac4e5ae61096 |
| src/transcriptformer/finetune/probes.py | 539ff82c6e4529004fb937c475f71e8019fbe93498579e834556a83e243b9fa8 |
| src/transcriptformer/finetune/representation.py | 86442e4ae797e85feff34b6904c6c2b707e37aa4a0f930f448409e0ab6d21cde |
| src/transcriptformer/finetune/resume.py | b3532adcb79f8da6fd16298e6614794578136ef6f763c57d9b31fb37563676ad |
| src/transcriptformer/finetune/sampling_audit.py | 69fa5387b4c0886ad647e8baedda4ada396911a948a4b419dd33fca5ebadf397 |
| src/transcriptformer/finetune/selection.py | e67b1fc5848149f707386abb26323945c2a646925a5cb622445ab92c28422b87 |
| src/transcriptformer/finetune/spatial.py | d8479c86b266fd5d2818efa5ed0aaeacb91307f4205b75bbac3ddf4c8a914e68 |
| src/transcriptformer/finetune/species_readiness.py | c3a5a9316217a0b72b0caa1f620f6edfc55328ac910e086206533b668e512d39 |
| src/transcriptformer/finetune/train.py | be73585f49e9947a183f3762ab545522d1661d68aca4c22df4af658fb432bec4 |
| src/transcriptformer/model/__init__.py | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| src/transcriptformer/model/embedding_surgery.py | 3cf345ffc3318af096dc4022e77b932aae374788874ba32c10d36324a2c9f9ec |
| src/transcriptformer/model/inference.py | 16c54023070262a6884019e737a14de5c95496f9c536aca49ff93fcfc3ecbbc2 |
| src/transcriptformer/model/layers.py | b77161f4c1a8c83fbcbbd322adf98bf37277b023c11f56ce20e8a4e0691973b0 |
| src/transcriptformer/model/losses.py | cf16887090984b10f2b8bb1eddec4d50e4acebac575d63cacd09670cf6abbb81 |
| src/transcriptformer/model/masks.py | 7e3e032a14aae9c88731ca68f778022590a4f371836b804d187cd89d2a935280 |
| src/transcriptformer/model/model.py | ad015ff76f093ad38e2394429d72468158da648f971b0a5993a3498767508c96 |
| src/transcriptformer/tokenizer/__init__.py | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| src/transcriptformer/tokenizer/tokenizer.py | be0215d924a7e1404be65390d29dd03514f3d136ee67bf0841b9f44eecabb1fc |
| src/transcriptformer/tokenizer/vocab.py | 73c29984b727a29340383b93b6899c8bc4435b826f464f8eafcf123fc50878d1 |
| src/transcriptformer/utils/__init__.py | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| src/transcriptformer/utils/utils.py | 1d21d047147f6a99efbb5dc6ed9ab86044c55c11c1593e8a7fa98dc039c85348 |
