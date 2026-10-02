# Full native embryo support diagnostic — 2026-10-03

The bounded diagnostic completed successfully. Under both possible two-bundle orders, the conservative candidate upper bound is **14,295 / 15,705 = 91.02197%**, and **all 2,000 draws** have at least the required 12,564 potentially supported pairs. These necessary bounds do not establish impossibility or feasibility. Exact native-support embryo identities are now available from the existing artifacts. Actual finite impacts, the actual finite paired gene set `G`, peer/null variance, resampled scores, ranks and uncertainty intervals remain unavailable. Ticket #05 remains open; zebrafish is excluded.

The implementation and tiny-HDF5 public run/CLI tests are new files. Existing Python tools, support artifacts, preflights, plans and cost requests remain unchanged. The source is [assess_b3_full_native_embryo_support.py](../../scripts/assess_b3_full_native_embryo_support.py); [validation evidence](b3-full-native-embryo-support-2026-10-03-validation.json) records 23 passing targeted tests, Ruff and mypy. The [frozen wrapper request](b3-full-native-embryo-support-2026-10-03-request.json) binds the existing cost request and the exact diagnostic/helper software bytes.

## Source binding and validation

The frozen cost request points to the two existing shard plans. Their plan/full/paired/config metadata hashes and support HDF5 hashes are checked before use and after assessment. Relative plan and prior-evidence references in that existing request resolve against the repository root. All full-plan provenance, support and software paths remain absolute. The shared ortholog-table bytes are hashed and must reconcile with both plans and the paired preflight.

Each HDF5 artifact must have the frozen schema, method, cohort hash, little-endian bit packing and cell order. The diagnostic checks all gene and physical-embryo identities and dimensions; source/embryo/cell indexes; unique ordered source row identities; the selected-membership digest; padding bits; native support as a subset of raw-positive support; per-gene native/raw support cell counts; and per-gene native-support embryo counts. It streams at most 128 genes at a time.

Original/prepared matrices remain explicit frozen references and are not opened or freshly rehashed. Reconstruction of the membership digest from the existing HDF5 mappings checks agreement with the frozen preflight contract. It does not independently repeat source/native matrix row assembly or establish numerical model effects.

The structural candidate universe `P` is the preflight's whole-cohort necessary-condition intersection. Its exclusions inherit the **frozen strict native shard contract**: every nonempty matched-target focal attempt must be finite/scored, with no focal-cell dropping. A backend that drops nonfinite focal cells can change peer completeness and invalidate those exclusions; this diagnostic does not authorize that change.

## Necessary bounds

The approved sampler uses `random.Random(20260930)`, 2,000 draws, sorted physical embryo IDs, and one sampled slot per physical embryo with replacement. The family paths are not frozen, so both possible human/mouse bundle orders are assessed. The result applies to exactly those two eligible source bundles; adding another eligible source bundle changes the random stream and requires recalculation.

Let `S_s(g)` be gene `g`'s native-support embryo set and `E_s,d,o` the embryos selected by draw `d` under order `o`. A pair `(a,b)` has possible joint focal occupancy when both `E_human,d,o ∩ S_human(a)` and `E_mouse,d,o ∩ S_mouse(b)` are nonempty. Define `q_o(a,b)` as the number of such draws.

For any unknown but fixed original finite-score set `F` with at least 1,900 valid draws, every pair in `F` must have `q_o(a,b) ≥ 1,900`. Thus

```text
|F| ≤ number of pairs in P with q_o(a,b) ≥ 1900.
```

The reporting floor is `K = max(500, ceil(0.8 × frozen joined denominator))`, hence 12,564 for the existing 15,705-pair denominator. For each draw, count all pairs in `P` with possible joint focal occupancy. At least 1,900 draws must each support at least `K` such pairs for any fixed reporting-sized `F` to have 1,900 valid draws. Either necessary veto can establish failure for a sampler order; ruling out both possible orders establishes failure under the stated two-bundle assumption. Passing both bounds does not establish feasibility because all pairs in a fixed `F` must be valid on the same draws and finite-score/null/rank conditions remain unassessed.

The report also gives occupancy for the hypothetical fixed set of **all structural potential pairs**, explicitly conditional on every pair having finite original scores. This is not actual `G`. Failure of that hypothetical set cannot by itself rule out a smaller unknown fixed reporting-sized set. A public test covers that distinction.

## Bounded execution

The script has cooperative limits of 900 seconds, 4 GiB process RSS, at least 4 GiB available host RAM, at least 20 GiB free disk, one native thread, and gene chunks of 1–128. The existing supervisor supplies the external deadline; no GPU, weights, model forward, actual draw-score replay or production job is used.

Following source review and registration at commit `d3a485d`, the completed run used this command from the repository root:

```bash
.venv/bin/python scripts/supervise_b3_pilot.py \
  --run-dir runs/b3_pilot/full_native_embryo_support_2026-10-03 \
  --max-wall-seconds 950 --max-rss-gib 4 \
  --min-host-ram-gib 4 --min-disk-gib 20 -- \
  .venv/bin/python scripts/assess_b3_full_native_embryo_support.py \
  --config docs/agents/b3-full-native-embryo-support-2026-10-03-request.json \
  --output docs/agents/b3-full-native-embryo-support-2026-10-03-evidence.json \
  --gene-chunk 128 --max-seconds 900
```

The output is immutable: publication uses a new temporary file followed by a non-overwriting hard link. Failure leaves no report or replacement of an existing report. The supervisor's `state.elapsed_seconds` records its last monotonic heartbeat, not final child duration. `finished_unix - started_unix` is the recorded final wall-clock span and should be labelled separately.

## Completed assessment

The [compact tracked summary](b3-full-native-embryo-support-2026-10-03-summary.json) records all 24 frozen input hashes, both order results, resources, exact output bindings and the explicit source/native-contract limits. All 24 frozen input bytes matched after assessment. The full report is preserved byte-for-byte at the ignored [run archive](../../runs/b3_feasibility/20261003/full_native_embryo_support.json), and the original [immutable publication](b3-full-native-embryo-support-2026-10-03-evidence.json) remains in place. Neither report was moved or overwritten. Both are **28,234,696 bytes** with SHA-256:

```text
ebe0d650c04f5d071b7dbd8506d93438e81742c21fe60bb95eb9e2882b7f4814
```

| Sampler order | Candidate upper bound | Draws supporting at least 12,564 potential pairs | Potential pairs per draw, minimum–maximum | Conditional all-14,392-pair joint occupancy |
| --- | ---: | ---: | ---: | ---: |
| Human then mouse | 14,295 (91.02197%) | 2,000 / 2,000 | 14,270–14,392 | 225 / 2,000 (11.25%) |
| Mouse then human | 14,295 (91.02197%) | 2,000 / 2,000 | 14,110–14,392 | 222 / 2,000 (11.10%) |

Both candidate bounds exceed the reporting floor by 1,731 pairs. The conditional all-potential set fails the 1,900-draw requirement under either order, but that set is explicitly hypothetical. Its failure does not establish that unknown actual `G` fails, and the passing upper bounds do not establish that actual `G` succeeds. No gene or cohort selection is proposed.

The helper reported **144.33 seconds to report**, including **128.92 seconds** for source validation and support streaming and **0.255 seconds** for occupancy replay. Peak RSS was **434,135,040 bytes (0.404 GiB)**. The supervisor completed with return code 0; its last monotonic heartbeat was **135.14 seconds**, while the recorded final wall-clock span was **146.15 seconds**. These are separately labelled measurements. The [supervisor state](../../runs/b3_pilot/full_native_embryo_support_2026-10-03/state.json) has SHA-256 `d387ad306b10b51565e0a3dbdfabd409d012f07be0a6877c310e5b9f12e156d8`.

The remaining feasibility dependencies concern actual finite score support and the complete frozen uncertainty/null/rank rules, plus method-preserving numerical acceleration. This diagnostic resolves the missing structural embryo-identity dependency without changing the scientific method or establishing a B3 result.
