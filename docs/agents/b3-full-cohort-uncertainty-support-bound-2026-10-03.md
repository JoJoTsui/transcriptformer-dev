# Full-cohort necessary uncertainty-support bound — 2026-10-03

The existing full measured-zero JSON preflights omit per-gene physical-embryo support identities. Their support counts permit a conservative candidate upper bound of **14,295 / 15,705 = 91.02197%**, necessary only. This exceeds the frozen 80% reporting floor of **12,564** pairs by 1,731, so this check establishes neither impossibility nor feasibility. **Ticket #05 remains open.**

Scope: the existing human/mouse organogenesis cohort and approved rules; no zebrafish. Only existing JSON metadata and helper source text were read. No matrices, support HDF5/bitmap bytes, weights, models, model forwards, source edits, or full-cohort execution jobs were used.

## Available metadata and remaining dependency

The human and mouse full preflights report 5 and 43 physical embryos. Every `gene_support` row provides `potentially_scorable_embryos` as an integer, together with cell counts and whole-cohort necessary-condition flags. It does not provide the supporting embryo IDs. Shard plans provide cell ranges and contrast counts rather than gene-by-embryo support sets.

The builder accumulates a temporary `embryo_native_support` array at [preflight_b3_measured_zero_full.py](../../scripts/preflight_b3_measured_zero_full.py#L195), reduces it to per-gene counts at line 339, and writes those counts at line 359. The exact native embryo sets could be reconstructed in a separately bounded pass over the existing native-support artifact and its cell-to-embryo mapping, whose datasets are declared at lines 204–212. That artifact was not opened here. Actual scored focal support can be smaller than native support; resampled bins, peers, finite null variance, scores, and ranks remain separate dependencies.

## Necessary bound

Let `P` be the structurally possible original paired universe, `S_s(g)` the embryos with potentially native-scorable focal cells for gene `g` in species `s`, and `D_s,d,o` the embryos selected by approved draw `d` under sampler order `o`. Define

```text
q_s,o(g) = sum(d = 0..1999) 1[D_s,d,o intersects S_s(g)]
C_o = {(a,b) in P : q_human,o(a) >= 1900 and q_mouse,o(b) >= 1900}
```

Any fixed original finite-score set `F` yielding at least 1,900 jointly valid draws must satisfy `F ⊆ C_o`. Consequently, `|F| ≤ |C_o|`. If the two bundle orders are both possible, `max_o |C_o| < 12,564` would establish impossibility without model scoring. Passing this bound cannot establish feasibility: individually supported genes can fail on different draws, and support does not establish finite scores or nonconstant ranks. An intersection test for both genes within each draw could tighten the necessary bound after obtaining embryo identities.

The shipped helper requires every fixed pair's two scores in each valid draw at [b3_measured_zero_bootstrap.py](../../src/transcriptformer/finetune/b3_measured_zero_bootstrap.py#L212), samples with replacement at line 201, sorts absolute bundle paths and physical embryos at lines 272–274, and requires 1,900 joint draws at lines 428 and 477.

## Count-only result under both bundle orders

Assume the eligible family contains exactly the two human/mouse organogenesis source bundles. Use Python `random.Random(20260930)`, 2,000 draws, sorted physical embryos, and one sampled slot per physical embryo. To account for missing identities, maximize support over every subset of two sorted embryo positions. Genes supported in zero or one embryo cannot exceed this maximum.

| Bundle sampler order | Human maximum support with 2 embryos | Mouse maximum support with 2 embryos |
| --- | ---: | ---: |
| Human then mouse | 1,858 draws | 1,784 draws |
| Mouse then human | 1,861 draws | 1,789 draws |

All are below 1,900. Therefore, a gene with native support in fewer than three embryos necessarily fails the individual draw-support condition under either order, regardless of its missing support identities.

The paired metadata contain 15,033 measured comparable pairs. Filtering them by both species' `necessary_conditions_met` flags reproduces the frozen structural upper bound of 14,392. Exactly 97 of those pairs have a human support count below three; none have a mouse support count below three. Removing their union gives the **14,295 candidate upper bound**. This does not claim that the remaining candidates pass the individual condition. As an additional check, 12,402 structural pairs have native support in every physical embryo on both sides and always satisfy the necessary potential focal-occupancy condition; actual scored support remains unmeasured.

The 14,392-pair pool inherits the unchanged strict native producer contract: every nonempty matched-target attempt has a finite scored effect, original likelihoods are finite, and focal cells are not silently omitted. Whole-cohort peer-completeness flags use that full native focal-cell support. A future backend that permits dropping nonfinite focal cells could change peer eligibility and would require reconsidering the pool and this bound.

The result accounts for both possible human/mouse bundle orders. **Adding any other eligible source bundle changes the random stream, so this count-only bound does not apply to that larger family without recalculation.** Bundle paths and the family must still be frozen before an exact approved-stream assessment. Different methods, source membership, or seeds also require recalculation.

## Frozen sources

The cost request's two plan hashes and each plan's full and paired preflight hashes were checked against the existing JSON bytes and matched. The sibling [JSON evidence](b3-full-cohort-uncertainty-support-bound-2026-10-03.json) records all file SHA-256 values, counts, and order-specific maxima.

## Lightweight reproduction

Run from the repository root. This command uses the Python standard library and reads JSON metadata only; it does not import model/scoring modules or open referenced binary artifacts.

```bash
python - <<'PY'
import json, random
from hashlib import sha256
from itertools import combinations
from pathlib import Path

base = Path('runs/b3_pilot/full_organogenesis_v3')
request = json.loads(Path('docs/agents/b3-complete-method-cost-request-2026-10-03.json').read_text())
for ref in request['plans']:
    path = Path(ref['path'])
    assert sha256(path.read_bytes()).hexdigest() == ref['sha256']
    plan = json.loads(path.read_text())
    for prefix in ('full_preflight', 'paired_preflight'):
        assert sha256(Path(plan[prefix + '_path']).read_bytes()).hexdigest() == plan[prefix + '_sha256']

rows, sizes = {}, {}
for side in ('human', 'mouse'):
    report = json.loads((base / f'{side}_measured_zero_support/support_preflight.json').read_text())
    sizes[side] = report['n_embryos']
    rows[side] = {r['gene_id']: r for r in report['gene_support']}
    del report
assert sizes == {'human': 5, 'mouse': 43}
paired = json.loads((base / 'paired_measured_zero_support.json').read_text())
pairs = [(a, b) for a, b in paired['statistic_eligibility']['comparable_pairs']
         if rows['human'][a]['necessary_conditions_met'] and rows['mouse'][b]['necessary_conditions_met']]
assert len(pairs) == paired['possible_finite_pair_upper_bound'] == 14392
low_h = {(a, b) for a, b in pairs if rows['human'][a]['potentially_scorable_embryos'] < 3}
low_m = {(a, b) for a, b in pairs if rows['mouse'][b]['potentially_scorable_embryos'] < 3}
upper = len(pairs) - len(low_h | low_m)
assert (len(low_h), len(low_m), upper) == (97, 0, 14295)
print({'structural_pairs': len(pairs), 'excluded_human': len(low_h),
       'excluded_mouse': len(low_m), 'candidate_upper': upper,
       'denominator': paired['n_vocabulary_joined_pairs'],
       'fraction_upper': upper / 15705, 'reporting_floor': 12564,
       'all_embryo_support_pairs': sum(rows['human'][a]['potentially_scorable_embryos'] == 5
                                      and rows['mouse'][b]['potentially_scorable_embryos'] == 43
                                      for a, b in pairs)})
for order in [('human', 'mouse'), ('mouse', 'human')]:
    rng = random.Random(20260930)
    embryos = {s: list(range(sizes[s])) for s in order}
    bits = {s: [0] * sizes[s] for s in order}
    for draw in range(2000):
        for side in order:
            selected = {rng.choice(embryos[side]) for _ in embryos[side]}
            for index in selected:
                bits[side][index] |= 1 << draw
    maxima = {s: max((bits[s][i] | bits[s][j]).bit_count()
                     for i, j in combinations(range(sizes[s]), 2)) for s in order}
    assert all(value < 1900 for value in maxima.values())
    print({'order': order, 'two_embryo_support_maxima': maxima})
PY
```
