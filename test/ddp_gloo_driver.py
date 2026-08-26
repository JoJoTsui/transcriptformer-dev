"""Clean-subprocess driver for the CPU gloo DDP smoke test.

The smoke test in test_train.py runs this module as a separate process because
fork-based DDP children cannot use autograd once the parent pytest process has
already executed backward() (https://github.com/pytorch/pytorch/wiki/Autograd-and-Fork).
"""

import os
import sys
from pathlib import Path


def main() -> None:
    tmp_path = Path(sys.argv[1])

    import transcriptformer.finetune.train as train_module
    from test.test_train import _make_cfg, _make_gene_vocab, _make_tiny_model, _write_training_files

    manifest, report = _write_training_files(tmp_path)
    output_dir = tmp_path / "run"
    output_dir.mkdir()

    # Patch before forking so the DDP children inherit the stand-in model.
    train_module._load_model = lambda path, **kwargs: (_make_tiny_model(), _make_cfg(), _make_gene_vocab(), None)

    # Record each rank's post-training weight sum; DDP gradient synchronization
    # must leave both ranks with identical weights.
    original_loop = train_module._run_training_loop

    def recording_loop(model, *args, **kwargs):
        summary = original_loop(model, *args, **kwargs)
        weight_sum = sum(float(p.detach().sum()) for p in model.parameters())
        (output_dir / f"rank_weight_{os.getpid()}.txt").write_text(f"{weight_sum:.10f}")
        return summary

    train_module._run_training_loop = recording_loop

    summary = train_module.train_finetune(
        manifest,
        output_dir,
        report,
        checkpoint_path="unused",
        max_steps=2,
        batch_size=2,
        lr=1e-3,
        epochs=1,
        device="cpu",
        precision="32",
        num_gpus=2,
        backend="gloo",
        resume=False,
    )
    assert summary["steps"] >= 1, summary
    assert summary["last_loss"] is not None, summary
    assert (output_dir / "training_summary.json").is_file()
    assert (output_dir / "model_weights.pt").is_file()
    # Gradient synchronization: identical initial weights (fork) + all-reduced
    # gradients must leave both ranks with bit-identical parameters.
    rank_weights = sorted(f.read_text() for f in output_dir.glob("rank_weight_*.txt"))
    assert len(rank_weights) == 2 and rank_weights[0] == rank_weights[1], rank_weights


if __name__ == "__main__":
    main()
