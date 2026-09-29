# B4 vocabulary-key join audit

`scripts/audit_probe_vocab_joins.py` reads only each probe H5AD `var` index and
each species vocabulary's `keys` dataset and embedding array shapes. It caps
each key list at 100,000, checks duplicate and empty keys, and never reads `X`
or embedding values. It verifies the hashes of the committed macaque/Xenopus
symbol maps and amphioxus protein bridge. For a generated vocabulary, its
output identity must match the adjacent `.parts/manifest.json`, with an exact
species source URL and (where pinned) source archive SHA-256. A legacy
vocabulary without that manifest is marked provenance-unverified even if its
keys join. Key coverage alone is not model or biological provenance.

Run from the repository root:

```bash
.venv/bin/python scripts/audit_probe_vocab_joins.py \
  --output logs/dataset_audit/b4_vocab_join_audit.json
```

Exit code 1 means at least one required vocabulary is absent or lacks a pinned,
manifest-bound source hash. As of this audit, all six B4 species vocabularies
are absent from the configured directory.
The [machine-readable report](../../logs/dataset_audit/b4_vocab_join_audit.json)
therefore records `null` for **unmeasured** joins. Its bridge-eligible counts below are
upper bounds based on gene-key mappings and do not imply an embedding exists.

| Probe | All `var` keys | Bridge-eligible keys | Ambiguous source symbols excluded | Other unmapped keys | Observed vocabulary joins |
| --- | ---: | ---: | ---: | ---: | ---: |
| Macaque Zhai | 26,135 | 12,613 | 0 | 13,522 | Unmeasured, vocabulary missing |
| Macaque Gong | 33,960 | 14,202 | 0 | 19,758 | Unmeasured, vocabulary missing |
| Macaque spatial | 4,663 | 3,263 | 0 | 1,400 | Unmeasured, vocabulary missing |
| Pig Simpson | 19,443 | 19,236 ENSSSCG direct-key candidates | 0 | 207 | Unmeasured, vocabulary missing |
| Guinea pig Canizo | 19,323 | 19,025 prefix candidates | 0 | 298 | Unmeasured, vocabulary missing |
| Xenopus Briggs | 26,550 | 9,485 | 174 | 16,891 | Unmeasured, vocabulary missing |
| Ciona Cao | 15,269 | 15,228 KH protein keys | 0 | 41 | Unmeasured, vocabulary missing |
| Amphioxus Markos | 29,726 | 26,676 protein-bearing gene keys | 0 | 3,050 | Unmeasured, vocabulary missing |

The 207 excluded pig keys are `GEO_GSE236766_unresolved_row_*` placeholders,
not ENSSSCG gene identifiers. Pig and guinea pig candidate counts are
syntax-level key matches; the
vocabulary must exist before protein-bearing coverage can be measured. The
Xenopus 174 ambiguous symbols are excluded according to the pinned peptide
audit, while other unmapped includes JGI/LOC and keys not accepted by the
same-release bridge. Amphioxus candidate keys come from the hashed same-assembly
protein bridge, and Ciona KH candidates are bound to the pinned Ghost audit.
None of these counts includes post-QC cell expression or an evaluation ruling
for the uncovered genes.
