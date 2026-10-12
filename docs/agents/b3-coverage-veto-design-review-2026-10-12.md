# B3 coverage veto — design review for owner decision — 2026-10-12

Drafted 2026-10-12 at the owner's direction (track decision: treat the B3
coverage veto as a design problem, not an engineering one). This document
frames a decision; it is not an ADR and changes no registered rule. Once the
owner decides, the outcome belongs in an ADR (hard to reverse, surprising
without context, real trade-off).

## Status facts (unchanged since 2026-10-01/03)

- Registered reporting floors: 500-pair and **80% coverage** floors for the
  paired Spearman comparison, distinct from the 60% eligibility floors.
- Observed paired pilot coverage: **5,111/15,705 = 32.54%** → verdict
  `withheld_insufficient_coverage`; `paired_measured_zero_final.json` records
  `structurally_unreportable`.
- Coordinated embryo-block bootstrap: **0/2,000** necessary jointly supported
  draws (singleton-supported genes).
- v1 full-cohort structural support: **0/15,705 pairs** — primary v1 is
  impossible, not merely expensive.
- v2 (measured-zero amendment) structural upper bounds: 14,392/15,705 =
  **91.64%**; native-embryo diagnostic 14,295/15,705 = **91.02%** — necessary
  bounds, never observed coverage.
- Exhaustive full-cohort scoring cost: ~1.066B forwards/arm ≈ **8.44 years**
  at pilot pacing.
- Engineering state: method fully specified and hash-bound; backends bit-exact
  vs the public scorer; local full CPU suite green (1,451 passed/5 skipped,
  2026-10-12). Ticket 05's remaining gates (reconciliation, producer/source
  acceptance, publication/replay, runtime/authority/compare) are parked.

## Why engineering cannot lift the veto

The veto is driven by **observed joint support** — which gene pairs actually
carry measured evidence in the corpus — not by compute, code, or storage.
Every remaining ticket 05 gate improves provenance and control of a statistic
whose inputs are absent for ~67% of the registered pair universe. Completing
them changes neither 32.54% nor 0/2,000.

## Options

**A. Keep the registered floors — B3 stays withheld.**
No reportable comparison; pre-registration integrity fully intact. B3 becomes
a documented non-result.

**B. Relax the reporting floor below 80%.**
Owner amendment to a registered threshold. The observed 32.54% is far below
any plausible confirmatory floor; reporting on the supported minority risks
selection bias (supported pairs enrich for well-measured genes — non-random).

**C. Narrow the estimand.**
Redefine the comparison universe to the measured/shared intersection (15,033
pairs) or the pilot-supported subset. Reportable within the subset, but it is
a new estimand requiring registration amendment; coverage within the subset
still needs measuring before claims.

**D. Bounded descriptive claims only.**
Publish the structural bounds (91.64%/91.02%) and pilot-subset results
explicitly labeled descriptive; no confirmatory claim, no threshold change.

**E. Cost reduction to raise observed coverage.**
Sampled/approximate scoring against the 8.44-year exhaustive cost; changes
null calibration; engineering-heavy; still bounded by what the corpus
measures.

## The question that decides between them

What is B3 *for* in this program? If it is a **confirmatory gate**, the
choices reduce to A (accept the non-result) or C (amend the estimand with
re-registration). If **descriptive evidence** suffices, D reports something
honest now. B weakens a registered floor against a 32.54% reality and is
listed for completeness. E does not address the support gap.

## Open for the owner

1. Confirmatory gate or descriptive evidence?
2. If confirmatory: is an estimand amendment (option C) acceptable, with
   re-registration of the narrowed universe and its own coverage floors?
3. Does B3 block any publication/claim timeline, or may it remain withheld
   while B1 proceeds?

No code, threshold, or registration changes are made by this document.
