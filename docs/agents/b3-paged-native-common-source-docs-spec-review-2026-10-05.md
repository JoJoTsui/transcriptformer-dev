# Final common-source documentation and evidence — Spec review

Reviewed 2026-10-05, statically against ticket 05, ADR 0005, the common-source
contract, and the captured metadata. **Hard findings: 0. Optional findings: 0.**
No imports, compilation, tests, model work, H5 or numeric payload reads were
performed. No tracked files, Git index, or HEAD were changed by this review.

The eight WIP Markdown changes and new validation correctly distinguish the
source-stable 1,092 PASS / 5 SKIP runtime and same-XML 45+30 PASS subset from
the original failed/exit-1 wrappers. Fresh v2 collect-only accounts for all 71
supplied files as 69 nonempty modules plus two empty CLI utilities and retains
identical 1,097 IDs. The accepted v3 metadata capture and its two review axes
are separate from the runtime and preserve the failed first reconciliation.

The 27-entry archive manifest binds 3,520,791 bytes of original metadata/source
copies, including both parent evidence files. Their observed SHA values match
the manifest; embedded original paths remain unchanged. `.py.txt` archives are
historical source evidence. The archive explicitly limits portability and
payload verification; no H5/numeric revalidation is claimed.

The seven-stage, failed 50-draw, and completed fresh 10-draw records retain
their distinct scopes. The 49.30-hour public-call projection, 398 unmeasured
invocations, separate clocks/caps, original 67/74 and new 69/82 identities,
and baseline 224/228/current 233 Python inventories are reported accurately.
Ticket 05 stays open, 11 excluded, and ten bounded tickets closed. Pilot
32.54% coverage, 0/2,000 necessary joint support, reporting veto and null
intervals are retained. No full bootstrap, method cost, effect attestation,
real scored corpus, or reportability is inferred. Publisher/controller drafts
and future registration/comparison/effect dependencies remain unaccepted.

## Exact reviewed SHA-256

| File | SHA-256 |
| --- | --- |
| `.scratch/multispecies-readiness-remediation/README.md` | `9d2a62d018a72ee3568d50807f18c6518035b12b34da18024c4373df6ffc4ddb` |
| `.scratch/multispecies-readiness-remediation/spec.md` | `1f3a89a4e7e0484ef4b6c6f42c6fa7300e0c6ea9567c62a528a7ee7654341624` |
| `.scratch/multispecies-readiness-remediation/issues/05-statistic-specific-ortholog-eligibility.md` | `637d7aec2f8b146cd0a7716d39f6f70ddbeb5773baaf7e11d42e5342ecc71879` |
| `docs/agents/b3-paged-native-common-source-contract-2026-10-04.md` | `da8f89a815220abc9db3541b8dd8d14f8865b58c32bf448bf3c988158707589b` |
| `docs/agents/b3-paged-native-common-source-proposal-2026-10-04.md` | `41b209b32c2f92c9d800ec6ee9aeb0be654cf831d075b791e73c0d51f8b4b11e` |
| `docs/agents/b3-pilot-progress-2026-10-02.md` | `58f507be580d7582187622804126370cdf9f5835d021a1100cd26cd8508c0fbd` |
| `docs/agents/finetune-readiness-tracker.md` | `ec71782fd5fc3c062559e3078ae57c7b15d29659ec41231f8ef9135610c758cf` |
| `docs/finetune-major-issues.md` | `3e8cab7575a1d09b4f07d3c4c4331731a1963b4718bc73825bd8396d289510c4` |
| `docs/agents/b3-paged-native-common-source-validation-2026-10-04.md` | `c96800d87e0c460e95fd62f2404d2ba239604d9bdbad89ef6f3f79ef9462cd9b` |
| `docs/agents/b3-paged-native-common-source-evidence-2026-10-04.json` | `cd2a7d15b6363bb8d0b15f41bf4b77fb0c05d33f82a8cee7efbc02016a5618d2` |
| `docs/agents/b3-paged-native-common-source-10-draw-evidence-2026-10-04.json` | `0868a11387eb3c9f031bf2fa6a99c366a2327fa7e3673eab61aa26c791a87314` |
| `docs/agents/b3-common-source-evidence-archive-2026-10-04/archive_manifest.json` | `1a6e3807fa885b6bb3b967321b661f650fb681796e84b8d9cbc3744ca2e213d3` |
| `docs/agents/b3-common-source-evidence-archive-2026-10-04/README.md` | `1ce67c882faf86d5cd9843dbf1b73091d83c05958c3b4a617ee4f3c5fcaf15b8` |

This record binds the observed WIP documentation and historical captured HEAD
`71c12543277895678bef85f4d9524a183234d0bd`; it makes no acceptance claim for
later source changes or the full-context drafts.
