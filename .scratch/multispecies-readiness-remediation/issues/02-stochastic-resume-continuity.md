# 02 — Preserve stochastic optimization across single-process and distributed resume

Category: correctness and readiness
Status: Implemented; bounded CPU validation passed; distributed runtime unverified
Priority: P2
Execution: authorized by owner for implementation on 2026-09-28; retain external scientific and data gates.
Depends on: 01
Traceability: R7; tracker A/F
Spec: [Multispecies readiness remediation](../spec.md)

## Outcome

Repair RNG/iterator restoration so sample-order continuity also preserves stochastic model behavior. Include worker/epoch boundaries and per-rank RNG state.

## Acceptance Criteria

- [ ] A deterministic CPU backend with a tiny dropout model produces matching parameters and losses for uninterrupted versus interrupted/resumed runs under the same contract.
- [ ] Creating iterators and skipping historical batches does not consume model RNG intended for future updates; continuation covers mid-epoch, cross-epoch and gradient-accumulation boundaries.
- [ ] Worker configurations supported by the existing pipeline retain deterministic observation and stochastic-transform behavior; unsupported combinations fail or state explicit limitations.
- [ ] A bounded two-rank CPU gloo case retains each rank's RNG rather than copying rank zero's state to every rank.
- [ ] World size, worker/data-order assumptions and state format participate in resume compatibility. Legacy records lacking required state fail clearly.
- [ ] Document CPU evidence separately from untested CUDA/kernel determinism; do not claim hardware-independent bitwise equivalence.

## Testing Seam

Prefer the public training/resume boundary using the existing stochastic reproduction and worker/gloo fixtures. Run distributed checks sequentially and only when local sockets are available; record unavailable execution rather than a fabricated pass.

## Constraints and Completion Limits

Actual GPU validation is a separate environment gate. No allocation of GPU memory or change to WSL limits is needed.

Use bounded CPU fixtures and metadata/streamed reads, preserve existing WSL
limits, cap native threads and run memory-heavy checks sequentially. No full
model training, broad download, production launch or automatic scientific
sign-off is authorized. Implementation was authorized on 2026-09-28; the
scientific and external-data gates remain in effect.

## Comments

Initially published as a specification-only ticket. 2026-09-28 implementation evidence: Stochastic CPU continuation is implemented and covered by the bounded 37-test resume/compatibility selection. A local Gloo runtime could not start because sockets returned EPERM; distributed behavior still needs an environment that permits it.

2026-09-29 remote CI follow-up: the first GitHub Actions run failed before
Gloo started because its smoke fixture contained only single-embryo sources,
which preparation correctly pinned to training, leaving no validation cohort.
The tiny fixture now includes one multi-embryo source. The subsequent
[finetune CI run](https://github.com/JoJoTsui/transcriptformer-dev/actions/runs/36567304030)
passed 337 selected tests, including the two-rank CPU Gloo smoke path. This
establishes that the launch/training path works on that runner. The smoke case
does not compare each rank's RNG or parameters across an interrupted and
resumed two-rank run, so acceptance criterion 4 remains open. Local WSL sockets
remain unavailable; CUDA/kernel behavior remains unverified.
