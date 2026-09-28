# 02 — Preserve stochastic optimization across single-process and distributed resume

Category: correctness and readiness
Status: ready-for-agent
Priority: P2
Execution: held by owner — do not implement yet.
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
sign-off is authorized. The ready-for-agent label describes specification
readiness; it does not override the owner's implementation hold.

## Comments

Created from the adversarial review and grill-with-docs decisions. No
implementation or new test execution has occurred as part of ticket publication.
