"""Apply D1/D2/D3-manifest/species edits to conf/finetune_run_multispecies.json."""

import json
from pathlib import Path

MANIFEST = Path("conf/finetune_run_multispecies.json")

DROP_EMBRYO_IDS = {
    # D1: byte-identical / 100% barcode overlap with the gastrulation atlas archive
    "tome_e6_75", "tome_e7_0", "tome_e7_25", "tome_e7_5",
    "tome_e7_75", "tome_e8_0", "tome_e8_25", "tome_e8_5a",
    # D2: CS6 fig3 is a strict subset of fig2
    "human_cs6_fig3",
}

SPECIES_BY_VOCAB = {
    "homo_sapiens": "homo_sapiens",
    "mus_musculus": "mus_musculus",
    "danio_rerio": "danio_rerio",
    "gallus_gallus": "gallus_gallus",
    "oryctolagus_cuniculus": "oryctolagus_cuniculus",
    "drosophila_melanogaster": "drosophila_melanogaster",
    "caenorhabditis_elegans": "caenorhabditis_elegans",
    "lytechinus_variegatus": "lytechinus_variegatus",
}

manifest = json.loads(MANIFEST.read_text())
kept, dropped = [], []
for ds in manifest["datasets"]:
    if ds["embryo_id"] in DROP_EMBRYO_IDS:
        dropped.append(ds["embryo_id"])
        continue

    # D2: one shared embryo_id for the remaining CS6 fig sections
    if ds["embryo_id"] in ("human_cs6_fig1", "human_cs6_fig2"):
        ds["embryo_id"] = "human_cs6"
        ds["obs_columns"]["embryo_id"] = "=human_cs6"

    # D3: drosophila continuum is sci-RNA-seq3 and now has real cell_type obs
    if ds["embryo_id"] == "drosophila_continuum":
        ds["assay"] = "sci-RNA-seq3"
        ds["obs_columns"]["assay"] = "=sci-RNA-seq3"
        ds["cell_type"] = "mixed"
        ds["obs_columns"].pop("cell_type", None)

    # species from the vocab path
    vocab = ds.get("vocab_path", "")
    species = next((v for k, v in SPECIES_BY_VOCAB.items() if f"/{k}_gene.h5" in vocab), None)
    assert species, f"no species inferred for {ds['embryo_id']}"
    ds["species"] = species

    # rebuild dict with species right after dataset_type
    ordered = {}
    for key, value in ds.items():
        if key == "species":
            continue
        ordered[key] = value
        if key == "dataset_type":
            ordered["species"] = species
    kept.append(ordered)

manifest["datasets"] = kept
MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(f"dropped {len(dropped)}: {sorted(dropped)}")
print(f"kept {len(kept)} datasets")
