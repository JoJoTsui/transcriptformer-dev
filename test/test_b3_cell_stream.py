"""Tiny CPU contract checks for auditable B3 per-cell score streaming."""

import math
from types import SimpleNamespace

import pytest
import torch

from transcriptformer.data.dataclasses import BatchData
from transcriptformer.finetune.b3_cell_stream import B3CellInput, iter_cell_impact_records


PAD = 0
END = 1
START = 6
EXCLUDED = frozenset({PAD, END, START})


class TinyGeneModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gene_vocab = SimpleNamespace(pad_idx=PAD, end_idx=END, start_idx=START)
        self.gene_id_criterion = SimpleNamespace(softcap=0, shift_right=False)
        self.forward_calls = 0
        self.grad_modes: list[bool] = []

    def forward(self, batch: BatchData, embed: bool = True) -> dict[str, torch.Tensor]:
        self.forward_calls += 1
        self.grad_modes.append(torch.is_grad_enabled())
        assert not embed
        tokens = batch.gene_token_indices
        logits = torch.zeros((*tokens.shape, 8), dtype=torch.float64)
        if int(tokens[0, 1]) == 3:
            logits[0, 2, 4] = 2.0
        targets = torch.cat((tokens[:, :-1], torch.full_like(tokens[:, :1], END)), dim=1)
        return {"gene_logit": logits, "input_gene_token_indices": targets, "mask": tokens == PAD}


def make_cell() -> B3CellInput:
    return B3CellInput(
        species="homo_sapiens",
        phase="gastrula",
        embryo_id="embryo-1",
        source_id="source-1",
        cell_id="cell-1",
        model_arm="finetuned",
        batch=BatchData(
            gene_counts=torch.tensor([[10.0, 20.0, 30.0, 40.0]]),
            gene_token_indices=torch.tensor([[2, 3, 4, 5]]),
        ),
    )


def test_stream_preserves_provenance_excludes_absent_gene_and_records_unavailable_targets() -> None:
    model = TinyGeneModel().eval()
    rows = list(
        iter_cell_impact_records(
            [make_cell()],
            model=model,
            gene_names={2: "G2", 3: "G3", 4: "G4", 5: "G5", 7: "G7"},
            excluded_gene_ids=EXCLUDED,
        )
    )

    assert [row.gene_id for row in rows] == ["G2", "G3", "G4", "G5"]
    assert [row.token_position for row in rows] == [0, 1, 2, 3]
    assert [row.n_targets for row in rows] == [2, 1, 0, 0]
    assert [row.status for row in rows] == ["scored", "scored", "no_matched_target", "no_matched_target"]
    assert rows[1].impact_bits == pytest.approx(math.log2(8 * math.exp(2) / (math.exp(2) + 7)))
    assert rows[2].impact_bits is None
    assert rows[3].impact_bits is None
    assert all(
        (row.species, row.phase, row.embryo_id, row.source_id, row.cell_id, row.model_arm)
        == ("homo_sapiens", "gastrula", "embryo-1", "source-1", "cell-1", "finetuned")
        for row in rows
    )
    # One original plus two scoreable deleted sentences. The two terminal
    # deletions have no original downstream native gene target.
    assert model.forward_calls == 3
    assert model.grad_modes == [False, False, False]


def test_stream_reuses_original_only_within_one_cell() -> None:
    model = TinyGeneModel().eval()
    first = make_cell()
    second = B3CellInput(
        species=first.species,
        phase=first.phase,
        embryo_id="embryo-2",
        source_id=first.source_id,
        cell_id="cell-2",
        model_arm=first.model_arm,
        batch=BatchData(
            gene_counts=torch.tensor([[9.0, 8.0, 7.0, 6.0]]),
            gene_token_indices=torch.tensor([[2, 3, 4, 5]]),
        ),
    )
    rows = list(
        iter_cell_impact_records(
            [first, second],
            model=model,
            gene_names={2: "G2", 3: "G3", 4: "G4", 5: "G5"},
            excluded_gene_ids=EXCLUDED,
        )
    )
    assert len(rows) == 8
    assert model.forward_calls == 6
    assert [row.embryo_id for row in rows] == ["embryo-1"] * 4 + ["embryo-2"] * 4


def test_deletion_cap_rejects_cell_before_any_model_forward() -> None:
    model = TinyGeneModel().eval()
    with pytest.raises(ValueError, match="exceeding cap 3"):
        list(
            iter_cell_impact_records(
                [make_cell()],
                model=model,
                gene_names={2: "G2", 3: "G3", 4: "G4", 5: "G5"},
                excluded_gene_ids=EXCLUDED,
                max_deletions_per_cell=3,
            )
        )
    assert model.forward_calls == 0


def test_duplicate_canonical_ids_rejected_before_any_model_forward() -> None:
    model = TinyGeneModel().eval()
    with pytest.raises(ValueError, match="duplicate canonical gene ID"):
        list(
            iter_cell_impact_records(
                [make_cell()],
                model=model,
                gene_names={2: "G2", 3: "G3", 4: "G3", 5: "G5"},
                excluded_gene_ids=EXCLUDED,
            )
        )
    assert model.forward_calls == 0
