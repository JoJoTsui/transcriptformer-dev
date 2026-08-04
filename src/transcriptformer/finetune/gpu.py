"""GPU preflight and batch-planning helpers for shared-node finetuning."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass


@dataclass
class GpuSelection:
    physical_indices: list[int]
    min_free_vram_gb: float


def select_gpus(
    max_gpus: int = 4,
    min_free_vram_gb: float = 20.0,
    max_utilization: int = 50,
) -> GpuSelection:
    """Select usable GPUs based on free VRAM and current utilization."""
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible:
        try:
            indices = [int(part) for part in visible.split(",") if part.strip()]
            if indices:
                return GpuSelection(indices, min_free_vram_gb)
        except ValueError:
            pass

    try:
        import pynvml

        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
    except Exception:
        try:
            import torch

            if torch.cuda.is_available():
                count = min(max_gpus, torch.cuda.device_count())
                return GpuSelection(list(range(count)), 0.0)
        except Exception:
            pass
        return GpuSelection([], 0.0)

    candidates: list[tuple[float, int]] = []
    for index in range(device_count):
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(index)
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            free_gb = memory.free / (1024**3)
            if free_gb >= min_free_vram_gb and utilization.gpu <= max_utilization:
                candidates.append((free_gb, index))
        except Exception:
            continue

    candidates.sort(reverse=True)
    selected = [index for _, index in candidates[:max_gpus]]
    min_free = candidates[-1][0] if candidates else 0.0
    return GpuSelection(selected, min_free)


def derive_batch_plan(
    min_free_vram_gb: float,
    num_gpus: int,
    requested_batch_size: int,
    global_batch_size: int | None = None,
) -> dict:
    """Derive per-GPU batch size and gradient accumulation from free VRAM."""
    if num_gpus <= 0:
        return {
            "batch_size": requested_batch_size,
            "grad_accumulation": 1,
            "num_gpus": 1,
        }

    if min_free_vram_gb <= 0:
        per_gpu_batch = requested_batch_size
    else:
        per_gpu_batch = max(1, int((min_free_vram_gb - 8) // 8))
        per_gpu_batch = min(per_gpu_batch, requested_batch_size)

    grad_accumulation = 1
    if global_batch_size and global_batch_size > 0:
        effective_batch = per_gpu_batch * num_gpus
        grad_accumulation = max(1, math.ceil(global_batch_size / effective_batch))

    return {
        "batch_size": per_gpu_batch,
        "grad_accumulation": grad_accumulation,
        "num_gpus": num_gpus,
    }
