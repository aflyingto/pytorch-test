# NPU 环境构建与测试验证（参考 accelerator-integration-wg 思路）

> 由于当前运行环境无法直接访问 `https://github.com/pytorch-fdn/accelerator-integration-wg`，本仓库基于 AIWG 常见的“环境构建脚本 + 分层验证脚本 + CI 编排”模式落地了一个可执行的 NPU（以 Ascend/`torch-npu` 为例）方案。

## 目录结构

- `scripts/build_npu_env.sh`：NPU 训练环境构建脚本。
- `scripts/validate_npu.sh`：分层测试验证脚本（导入、算子、分布式、pytest）。
- `tests/npu_smoke.py`：可在 CI / 本地统一复用的最小冒烟用例。
- `.github/workflows/npu-validation.yml`：面向自托管 NPU Runner 的 CI 示例。

## 快速开始

```bash
# 1) 构建环境（默认创建 conda 环境 npu-ci）
bash scripts/build_npu_env.sh

# 2) 激活环境后执行验证
conda activate npu-ci
bash scripts/validate_npu.sh
```

## 设计要点

- **幂等性**：脚本支持重复执行，不会因为目录已存在而直接失败。
- **可参数化**：通过环境变量覆盖 Python 版本、PyTorch/torch-npu 分支、是否启用分布式测试等。
- **可观测性**：每个阶段都输出明确日志与失败点，便于在 CI 中快速定位。
- **分层验证**：
  1. 依赖/驱动可用性检查
  2. `torch` 与 `torch_npu` 导入
  3. 基础算子与反向传播
  4. （可选）分布式初始化检查
  5. `pytest` 冒烟

## 常用环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `NPU_CONDA_ENV` | `npu-ci` | conda 环境名 |
| `PYTHON_VERSION` | `3.10` | Python 版本 |
| `PYTORCH_REF` | `main` | PyTorch 分支/标签 |
| `TORCH_NPU_REF` | `master` | torch-npu 分支/标签 |
| `BUILD_JOBS` | `8` | 编译并行度 |
| `RUN_DIST_TEST` | `0` | 是否执行分布式测试（1=执行） |

## 与 AIWG 对齐方式

该实现与 accelerator-integration-wg 中的实践目标保持一致：

- 通过标准化脚本收敛构建步骤；
- 通过统一入口执行验证，确保不同机器可复现；
- 通过 CI 将“环境 + 验证”流程自动化。

后续如果网络可达，可将仓库中的具体模板进一步替换为 AIWG 对应目录下的原生实现。
