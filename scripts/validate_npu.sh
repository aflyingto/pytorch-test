#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[validate-npu] %s\n' "$*"
}

NPU_CONDA_ENV="${NPU_CONDA_ENV:-npu-ci}"
RUN_DIST_TEST="${RUN_DIST_TEST:-0}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_cmd conda

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${NPU_CONDA_ENV}"

log "python and pip versions"
python --version
pip --version

if command -v npu-smi >/dev/null 2>&1; then
  log "npu-smi detected, dumping topology"
  npu-smi info || true
else
  log "npu-smi not found; continue for software-level validation"
fi

log "running inline import/op/autograd validation"
python - <<'PY'
import torch

print("torch:", torch.__version__)

try:
    import torch_npu  # noqa: F401
except Exception as exc:
    raise SystemExit(f"failed to import torch_npu: {exc}")

if not hasattr(torch, "npu"):
    raise SystemExit("torch.npu is missing")

if not torch.npu.is_available():
    raise SystemExit("NPU is not available")

x = torch.randn(4, 4, device="npu", requires_grad=True)
y = torch.randn(4, 4, device="npu")
z = (x @ y).sum()
z.backward()
print("basic matmul+backward passed")
PY

if [[ "${RUN_DIST_TEST}" == "1" ]]; then
  log "running distributed initialization test"
  python - <<'PY'
import os
import tempfile

import torch
import torch.distributed as dist

backend = "hccl"
if not torch.npu.is_available():
    raise SystemExit("NPU unavailable for distributed test")

with tempfile.TemporaryDirectory() as d:
    init_file = os.path.join(d, "dist_init")
    dist.init_process_group(
        backend=backend,
        init_method=f"file://{init_file}",
        world_size=1,
        rank=0,
    )
    dist.destroy_process_group()

print("distributed init passed")
PY
else
  log "skip distributed test, set RUN_DIST_TEST=1 to enable"
fi

log "running pytest smoke"
pytest -q tests/npu_smoke.py

log "all validation checks passed"
