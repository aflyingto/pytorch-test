#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[build-npu-env] %s\n' "$*"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

NPU_CONDA_ENV="${NPU_CONDA_ENV:-npu-ci}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
PYTORCH_REF="${PYTORCH_REF:-main}"
TORCH_NPU_REF="${TORCH_NPU_REF:-master}"
BUILD_JOBS="${BUILD_JOBS:-8}"
WORKDIR="${WORKDIR:-$PWD/.workspace}"

log "target conda env: ${NPU_CONDA_ENV}"
log "python version: ${PYTHON_VERSION}"
log "pytorch ref: ${PYTORCH_REF}"
log "torch-npu ref: ${TORCH_NPU_REF}"

require_cmd conda
require_cmd git
require_cmd python

# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"

if conda env list | awk '{print $1}' | grep -qx "${NPU_CONDA_ENV}"; then
  log "conda env ${NPU_CONDA_ENV} already exists, reusing"
else
  log "creating conda env ${NPU_CONDA_ENV}"
  conda create -y -n "${NPU_CONDA_ENV}" "python=${PYTHON_VERSION}"
fi

conda activate "${NPU_CONDA_ENV}"

log "installing base dependencies"
pip install -U pip setuptools wheel ninja cmake pytest

mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

if [[ ! -d pytorch ]]; then
  log "cloning pytorch"
  git clone https://github.com/pytorch/pytorch.git
fi

if [[ ! -d torch-npu ]]; then
  log "cloning torch-npu"
  git clone https://github.com/Ascend/pytorch.git torch-npu
fi

log "checkout pytorch ${PYTORCH_REF}"
git -C pytorch fetch --all --tags
git -C pytorch checkout "${PYTORCH_REF}"

log "checkout torch-npu ${TORCH_NPU_REF}"
git -C torch-npu fetch --all --tags
git -C torch-npu checkout "${TORCH_NPU_REF}"

log "building pytorch from source"
cd pytorch
git submodule sync
git submodule update --init --recursive
MAX_JOBS="${BUILD_JOBS}" USE_CUDA=0 USE_ROCM=0 python setup.py develop

log "building torch-npu from source"
cd "${WORKDIR}/torch-npu"
MAX_JOBS="${BUILD_JOBS}" python setup.py develop

log "environment build completed"
