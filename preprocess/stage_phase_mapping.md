# Native Stage → Developmental Phase Mapping (DRAFT for review)

Universal phase vocabulary (CONTEXT.md): `blastula`, `gastrula`, `neurula`, `organogenesis`
(`fetal` reserved, currently unused). Invertebrates have no true neurula — the
phylotypic/morphogenesis period is mapped to `neurula` for cross-species alignment.

These mappings become per-dataset `stage_mapping` dicts in the run manifest.

## Vertebrates

| Dataset | Native stage(s) | Phase |
|---|---|---|
| Human CS6 Stereo-seq (fig1–3) | CS6 | gastrula |
| Human CS7 (Tyser sc + spatial) | CS7 | gastrula |
| Human CS8 spatial | CS8 | neurula |
| Human CS9 Stereo, CS10 | CS9, CS10 (`PCW3 / CS10`) | neurula |
| Human CS12–16 | CS12, CS13-14, CS15-16 | organogenesis |
| Mouse TOME | E3.5, E4.5, E5.25, E5.5 | blastula |
| | E6.25, E6.5, E6.75, E7.0, E7.25, E7.5, E7.75 | gastrula |
| | E8.0, E8.25, E8.5a, E8.5b | neurula |
| | E9.5, E10.5, E11.5, E12.5, E13.5 | organogenesis |
| Mouse gastrulation atlas | E6.5–E7.75, mixed_gastrulation | gastrula |
| | E8.0, E8.25, E8.5 | neurula |
| Mouse single-embryo timecourse | developmental_time < 8.0 | gastrula |
| | developmental_time ≥ 8.0 | neurula |
| Rabbit atlas | GD7 | gastrula |
| | GD8 | neurula |
| | GD9 | organogenesis |
| Zebrafish (Wagner 2018) | 4hpf | blastula |
| | 6hpf, 8hpf, 10hpf | gastrula |
| | 14hpf, 18hpf | neurula |
| | 24hpf | organogenesis |
| Chicken (eLife 2022) | HH4 | gastrula |
| | HH5, HH6, HH7 | neurula |

## Invertebrates

| Dataset | Native stage(s) | Phase |
|---|---|---|
| Drosophila continuum | hrs_00_02, hrs_01_03 | blastula |
| | hrs_02_04, hrs_03_07 | gastrula |
| | hrs_04_08, hrs_06_10 (extended germ band) | neurula |
| | hrs_08_12, hrs_10_14, hrs_12_16, hrs_14_18, hrs_16_20 | organogenesis |
| C. elegans (embryo.time.bin, min) | < 100, 100-130 | blastula |
| | 130-170, 170-210, 210-270 | gastrula |
| | 270-330, 330-390 (comma/morphogenesis) | neurula |
| | 390-450, 450-510, 510-580, 580-650, > 650 | organogenesis |
| Sea urchin (hpf) | 2, 3, 4, 5, 6, 7, 8, 9 | blastula |
| | 10, 11, 12, 13, 14, 15, 16 | gastrula |
| | 18, 20, 24 (prism/early larva) | organogenesis |

## Boundary calls to double-check

- Human CS8–CS10 → neurula (CS8 = neural plate, CS9–10 = neural tube/early somites)
- Rabbit GD9 → organogenesis (vs neurula)
- Zebrafish 14–18hpf → neurula (vs gastrula tail-bud or organogenesis)
- Mouse E8.0–8.5 → neurula (vs late gastrula)
- Treating fly extended germ band / worm comma stage as `neurula` (phylotypic alignment)
