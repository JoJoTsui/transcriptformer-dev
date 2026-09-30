"""Clean-subprocess, bounded two-rank stochastic resume reproduction."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch


class DropoutTiny(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear_in = torch.nn.Linear(1, 8)
        self.dropout = torch.nn.Dropout(0.5)
        self.linear_out = torch.nn.Linear(8, 1)
        self.criterion = lambda mu, input_counts, mask: torch.mean((mu - input_counts) ** 2)
        self.loss_config = SimpleNamespace(gene_id_loss_weight=0)

    def forward(self, batch):
        counts = batch.gene_counts.sum(dim=1, keepdim=True)
        values = self.linear_out(self.dropout(self.linear_in(counts)))
        return {"mu": values, "input_counts": counts, "mask": None}


def main() -> None:
    tmp_path = Path(sys.argv[1])

    import transcriptformer.finetune.train as train_module
    from test.fixtures import make_synthetic_h5ad
    from test.test_train import _make_cfg, _make_gene_vocab, _write_training_files
    from transcriptformer.finetune.prepare import prepare_run

    manifest, legacy_report = _write_training_files(tmp_path)
    validation_source = make_synthetic_h5ad(
        tmp_path / "multi_embryo.h5ad",
        embryo_ids=[f"cohort_{embryo}" for embryo in ("a", "b", "c") for _ in range(4)],
    )
    manifest["datasets"].append(
        {
            "path": str(validation_source),
            "species": "synthetic",
            "dataset_type": "single_cell",
        }
    )
    manifest["datasets"].append(
        {
            "path": legacy_report["datasets"][-1]["path"],
            "dataset_type": "spatial",
        }
    )
    manifest["seed"] = 71
    report = prepare_run(manifest, tmp_path / "preparation")

    checkpoint = tmp_path / "checkpoint"
    (checkpoint / "vocabs").mkdir(parents=True)
    (checkpoint / "config.json").write_text("{}")
    (checkpoint / "model_weights.pt").write_bytes(b"dropout-tiny-test-double")
    (checkpoint / "vocabs" / "assay_vocab.json").write_text("{}")

    train_module._load_model = lambda path, **kwargs: (
        DropoutTiny(),
        _make_cfg(),
        _make_gene_vocab(),
        None,
    )
    original_loop = train_module._run_training_loop

    def recording_loop(model, *args, **kwargs):
        summary, best_state = original_loop(model, *args, **kwargs)
        rank = torch.distributed.get_rank()
        (kwargs["output_dir"] / f"rank_{rank}.json").write_text(
            json.dumps(
                {
                    "losses": summary["losses"],
                    "steps": summary["steps"],
                }
            )
        )
        return summary, best_state

    train_module._run_training_loop = recording_loop

    def run(output: Path, steps: int, resume: bool):
        output.mkdir(exist_ok=True)
        return train_module.train_finetune(
            manifest,
            output,
            report,
            checkpoint_path=str(checkpoint),
            max_steps=steps,
            batch_size=2,
            lr=1e-3,
            epochs=2,
            device="cpu",
            precision="32",
            num_gpus=2,
            backend="gloo",
            grad_accumulation=2,
            checkpoint_interval=0,
            resume=resume,
        )

    full_dir = tmp_path / "full"
    split_dir = tmp_path / "split"
    full = run(full_dir, 3, False)
    interrupted = run(split_dir, 1, False)
    assert interrupted["steps"] == 1
    resumed = run(split_dir, 3, True)
    assert full["steps"] == resumed["steps"] == 3

    full_state = torch.load(full_dir / "terminal_state.pt", weights_only=False, map_location="cpu")
    split_state = torch.load(split_dir / "terminal_state.pt", weights_only=False, map_location="cpu")
    assert len(full_state["rank_rng"]) == len(split_state["rank_rng"]) == 2
    assert not torch.equal(full_state["rank_rng"][0]["torch"], full_state["rank_rng"][1]["torch"])
    for rank in (0, 1):
        assert json.loads((full_dir / f"rank_{rank}.json").read_text()) == json.loads(
            (split_dir / f"rank_{rank}.json").read_text()
        )
        assert torch.equal(full_state["rank_rng"][rank]["torch"], split_state["rank_rng"][rank]["torch"])
    assert full["losses"] == resumed["losses"]
    assert full_state["model"].keys() == split_state["model"].keys()
    for key in full_state["model"]:
        assert torch.equal(full_state["model"][key], split_state["model"][key]), key


if __name__ == "__main__":
    main()
