# B4 macaque and Xenopus gene-symbol bridges (candidate, 2026-09-29)

The four probe H5ADs index genes by symbol-like names, whereas the specified
ESM2 protein sources index genes by Ensembl stable IDs. I read only `var`
columns from those H5ADs and streamed the Ensembl peptide FASTAs named by the
B4 manifest plus their same-release GTFs. Each compressed source was under 20 MB;
no expression matrix, model, or GPU job was opened.
The selected column is the H5AD `var` index in all four files: `gene` (Zhai),
`gene_id` (Gong), `gene_symbol` (macaque spatial), and `gene_name` (Briggs).

| Species | Ensembl source | Peptide SHA-256 | GTF SHA-256 |
| --- | --- | --- | --- |
| *Macaca fascicularis* | [release 110 peptide FASTA](https://ftp.ensembl.org/pub/release-110/fasta/macaca_fascicularis/pep/Macaca_fascicularis.Macaca_fascicularis_6.0.pep.all.fa.gz), [release 110 GTF](https://ftp.ensembl.org/pub/release-110/gtf/macaca_fascicularis/Macaca_fascicularis.Macaca_fascicularis_6.0.110.gtf.gz) | `8f7bc5ebd229d78ea0d1eb261d292f19cd5e10590ac278ea10c736b0b13fd41a` | `27144c10fa3555c357ebef8f0c2e697963cd04b47f3a04303c2967e48deadc78` |
| *Xenopus tropicalis* | [release 113 peptide FASTA](https://ftp.ensembl.org/pub/release-113/fasta/xenopus_tropicalis/pep/Xenopus_tropicalis.UCB_Xtro_10.0.pep.all.fa.gz), [release 113 GTF](https://ftp.ensembl.org/pub/release-113/gtf/xenopus_tropicalis/Xenopus_tropicalis.UCB_Xtro_10.0.113.gtf.gz) | `203398cc98855ddf0ddb79c2bbe1a7590849b97ada176ba951d27d4c82e8a1bd` | `6995905c2b97eaf0c79c58545049bd32f44d1d260812544db3777c89494dfbd9` |

The [builder](../../scripts/build_probe_symbol_bridges.py) admits a probe key
only when it names exactly one stable gene in the peptide FASTA **and** exactly
that same one gene in the matching GTF. It preserves case and spelling;
it does not infer LOC, synonym, or orthology relationships. The resulting
per-species [macaque map](../../preprocess/gene_mappings/macaca_fascicularis_probe_symbol_to_ensmfag.json)
and [Xenopus map](../../preprocess/gene_mappings/xenopus_tropicalis_probe_symbol_to_ensxetg.json)
contain 14,570 and 9,485 distinct probe keys respectively. The exact
source and probe-key hashes are recorded in the [macaque audit](../../logs/dataset_audit/b4_macaque_symbol_bridge.json)
and [Xenopus audit](../../logs/dataset_audit/b4_xenopus_symbol_bridge.json).
Both maps are also one-to-one on target stable gene IDs; the builder rejects
any alias collision that would cause two probe keys to point to one gene.

| Probe | Accepted / all `var` genes | Maximum gene-key coverage from this bridge | Excluded multi-gene peptide symbols | LOC keys accepted |
| --- | ---: | ---: | ---: | ---: |
| macaque Zhai 2022 | 12,613 / 26,135 | 48.3% | 0 | 0 |
| macaque Gong 2023 | 14,202 / 33,960 | 41.8% | 0 | 0 |
| macaque spatial | 3,263 / 4,663 | 70.0% | 0 | 0 |
| Xenopus Briggs 2018 | 9,485 / 26,550 | 35.7% | 174 | 0 |

The Xenopus peptide source has 294 symbols naming multiple stable genes;
174 occur in the Briggs probe. They remain excluded, even if one of those
genes might appear in a later vocabulary. The peptide source has no such
symbol collisions for macaque. All retained probe pairs agree with the
corresponding GTF gene name and stable ID. These are **candidate join counts**:
neither the macaque ESM2 vocabulary nor its embeddings have been generated,
and the pre-generated Xenopus vocabulary's Ensembl release has not been
verified. A release 113 bridge cannot be assumed to join a vocabulary built
against another release. Actual vocabulary-key and post-QC coverage must be
measured before B4; the low symbol coverage especially needs an explicit
evaluation ruling or a defensible source-specific mapping for the remaining
LOC/JGI keys.

The generated JSONs are data artifacts, not a claim that the B4 gate is
complete. Rebuild them with the pinned archives and the current probe
manifest using `scripts/build_probe_symbol_bridges.py --species ... --pep ...
--gtf ... --output ... --report ...`. The builder rejects changed archive
hashes and reads only H5AD `var` names. It does not mutate probe files.
