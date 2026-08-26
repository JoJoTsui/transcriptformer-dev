"""Tests for GPU preflight and batch planning."""

from __future__ import annotations

from unittest import mock

from transcriptformer.finetune.gpu import derive_batch_plan, select_gpus


def test_select_gpus_filters_utilized_or_low_vram(monkeypatch) -> None:
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)

    class Memory:
        def __init__(self, free: int):
            self.free = free

    class Utilization:
        def __init__(self, gpu: int):
            self.gpu = gpu

    handles = [object(), object(), object()]

    with (
        mock.patch("pynvml.nvmlInit"),
        mock.patch("pynvml.nvmlDeviceGetCount", return_value=3),
        mock.patch("pynvml.nvmlDeviceGetHandleByIndex", side_effect=lambda index: handles[index]),
        mock.patch(
            "pynvml.nvmlDeviceGetMemoryInfo",
            side_effect=lambda handle: {
                id(handles[0]): Memory(10 * 1024**3),
                id(handles[1]): Memory(30 * 1024**3),
                id(handles[2]): Memory(40 * 1024**3),
            }[id(handle)],
        ),
        mock.patch(
            "pynvml.nvmlDeviceGetUtilizationRates",
            side_effect=lambda handle: {
                id(handles[0]): Utilization(10),
                id(handles[1]): Utilization(10),
                id(handles[2]): Utilization(90),
            }[id(handle)],
        ),
    ):
        selection = select_gpus(
            max_gpus=2,
            min_free_vram_gb=20.0,
            max_utilization=50,
        )

    assert selection.physical_indices == [1]
    assert selection.min_free_vram_gb == 30.0


def test_derive_batch_plan_scales_with_vram_and_global_batch() -> None:
    plan = derive_batch_plan(
        min_free_vram_gb=24.0,
        num_gpus=2,
        requested_batch_size=8,
        global_batch_size=8,
    )
    assert plan["batch_size"] == 2
    assert plan["grad_accumulation"] == 2
    assert plan["num_gpus"] == 2


def test_derive_batch_plan_falls_back_without_gpus() -> None:
    plan = derive_batch_plan(
        min_free_vram_gb=0.0,
        num_gpus=0,
        requested_batch_size=4,
        global_batch_size=16,
    )
    assert plan["batch_size"] == 4
    assert plan["grad_accumulation"] == 1
