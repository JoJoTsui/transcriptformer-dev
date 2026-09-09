# Multi-Species Embryogenesis Finetuning Strategy

**Status:** accepted (supersedes ADR 0001)

We will finetune the TranscriptFormer TF-Metazoa checkpoint on multi-species embryogenesis data (human, mouse, zebrafish, chicken, rabbit, fruit fly, C. elegans, sea urchin) using the generative pretraining objective, natural sampling weighting, a coarse universal developmental-phase vocabulary, and per-species embryo-level splits — then use the model for phase-resolved in-silico perturbation and zero-shot cross-species comparison on species never seen in training (macaque, pig, guinea pig, Xenopus tropicalis, ciona, amphioxus).

## Considered Options

- **Zebrafish-only vs multi-species scope**: the zebrafish-only plan (ADR 0001) was superseded because the project's goals — cross-species same-phase regulation comparison and phase-specific perturbation — are impossible with one species.
- **Training on all species vs in-vocabulary species only**: out-of-vocabulary species (macaque, pig, etc.) were kept out of training and reserved as zero-shot probes, preserving a clean generalization benchmark (e.g. macaque vs human gastrulation) untainted by training exposure. Xenopus tropicalis joins the probe set because the model vocabulary is X. laevis.
- **Supervised vs generative objective**: pure generative finetuning was chosen; an auxiliary stage-prediction head is deferred and will only be added if holdout evaluation shows inadequate stage structure, since label heads can distort general representations and add nothing to perturbation capability.
- **Balanced vs natural sampling**: per-species balancing was rejected for now because TF-Metazoa itself was pretrained on an unbalanced, human/mouse-dominated corpus (~89% of the local corpus is mouse, mirroring this); balancing is the documented fallback if holdout metrics show mouse-bias artifacts.
- **Stage harmonization**: a fine-grained cross-species stage correspondence table was deferred as a large literature-curation effort; a coarse universal phase vocabulary (blastula/gastrula/neurula/organogenesis/fetal) is mapped from native labels via the manifest `stage_mapping`, with native labels preserved so a fine-grained mapping can be added later.
- **Split design**: cell-level splitting for single-embryo datasets (human CS7, spatial sections) was rejected due to same-embryo leakage; those datasets are train-only. Dataset-level holdout was rejected because it would remove entire stages from some species' training. Splits are per-species embryo-level (~70/20/10).
- **Full finetuning vs LoRA**: full finetuning is the default (single RTX 3090, gradient checkpointing + accumulation, verified by smoke test); LoRA is the fallback, matching ADR 0001's fallback clause.
- **Perturbation depth**: a tiered approach was chosen — genome-wide likelihood-drop impact scoring first (cheap, rankable by gene × phase), then counterfactual generation only for top hits; embedding-shift-only analysis was rejected as too weak to name impacted genes.

## Consequences

- Non-embryo datasets in the corpus (sponge juvenile, yeast, trichoplax, nematostella) are excluded entirely.
- Evaluation uses a four-metric scorecard on the final holdout: generative likelihood vs the base Metazoa model, embedding stage separation, cross-species same-phase alignment, and a perturbation sanity check (known essential embryogenesis genes must rank high in impact scores).
- Zero-shot probe species require ESM2 protein embeddings: pig and Xenopus tropicalis are downloadable pre-generated; macaque fascicularis, ciona, and amphioxus must be generated locally via `preprocess/protein_embedding.py`.
- Dataset preparation must produce model-ready H5ADs with Ensembl gene IDs per species, raw counts, `embryo_id`, native stage labels plus mapped developmental phase, and harmonized `cell_type` for evaluation metadata.
