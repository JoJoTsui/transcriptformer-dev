"""Evidence required to resume the same optimization and observation stream."""

from copy import deepcopy
from pathlib import Path
from typing import Any

from transcriptformer.finetune.prepare import _hash_file


def build_resume_contract(manifest: dict, prepared_report: dict, checkpoint_path: Path, **training: Any) -> dict:
    """Bind semantic preparation evidence and training settings, not output paths.

    Re-preparing identical sources may produce different HDF5 bytes, so output
    hashes remain the artifact gate's responsibility. Budget (epochs/max_steps)
    and checkpoint frequency are deliberately absent: they may be extended.
    """
    source_keys = (
        "source_path",
        "sha256",
        "survivor_digest",
        "survivor_count",
        "split",
        "embryo_ids",
        "n_obs",
        "n_genes",
        "dataset_type",
        "species",
    )
    sources = [{key: entry.get(key) for key in source_keys} for entry in prepared_report["datasets"]]
    # Preserve report order: it defines concatenated row offsets in the loader.
    files = [checkpoint_path / "config.json", checkpoint_path / "model_weights.pt"]
    files += sorted(path for path in (checkpoint_path / "vocabs").rglob("*") if path.is_file())
    for path in files:
        if not path.is_file():
            raise ValueError(f"Missing base checkpoint asset for resume identity: {path}")
    return deepcopy(
        {
            "version": 1,
            "preparation": prepared_report["preparation_fingerprint"],
            "sources": sources,
            "sampling": manifest.get("sampling", {}),
            "seed": int(manifest.get("seed", 0)),
            "dataloader": manifest.get("dataloader", {}),
            "base_checkpoint": {str(path.relative_to(checkpoint_path)): _hash_file(path) for path in files},
            "training": training,
        }
    )


def validate_resume_contract(state: dict, expected: dict) -> None:
    actual = state.get("resume_contract")
    if actual is None or state.get("loop_state") is None:
        raise ValueError("Legacy checkpoint lacks resume evidence; use a new output directory for a fresh run")
    if actual != expected:
        changed = sorted(key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key))
        raise ValueError(f"Incompatible resume contract ({', '.join(changed)}); use a new output directory")
