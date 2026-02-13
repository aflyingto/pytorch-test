# accelerator-integration-wg 工作流执行与编排说明

## 目标

通过当前主仓的 workflow 直接拉起 `pytorch-fdn/accelerator-integration-wg` 的全部 workflow 执行，并在主仓内展示清晰的任务依赖和执行汇总。

## 主仓内编排 DAG

主仓 workflow：`.github/workflows/accelerator-wg-workflow-validation.yml`

DAG：

1. `discover-accelerator-wg-workflows`
   - 使用 `scripts/dispatch_accelerator_wg_workflows.py list` 调 GitHub Actions API 枚举上游全部 workflow。
   - 产出 matrix（workflow id/name/path）。
2. `execute-accelerator-wg-workflows`（matrix）
   - 对每个上游 workflow 并行执行：`run-one`（dispatch + monitor）。
   - 每个 matrix 项都会上传一份 `result-<workflow_id>.json` 结果。
3. `summarize-accelerator-wg-orchestration`
   - 汇总所有 matrix 结果。
   - 打印每个 workflow 的 `status/run_id/conclusion`。
   - 任一失败即让主仓 workflow fail。

## 运行前提

需要在主仓配置 secret：`ACCELERATOR_WG_GH_TOKEN`。

该 token 需要对 `pytorch-fdn/accelerator-integration-wg` 具备触发和读取 Actions 的权限（例如可用 fine-grained PAT，包含 Actions 读写与仓库内容只读）。

## 手动触发

在主仓 Actions 页面手动运行 `accelerator-wg-workflow-validation`，可选 `upstream_ref`（默认 `main`）。

## 脚本能力

`scripts/dispatch_accelerator_wg_workflows.py` 支持：

- `list`: 列出 workflow（JSON，可直接用于 matrix）
- `run-one`: 执行单个 workflow（dispatch + wait）
- `run-all`: 串行执行全部 workflow

示例：

```bash
export GITHUB_TOKEN=<token>
python scripts/dispatch_accelerator_wg_workflows.py list
python scripts/dispatch_accelerator_wg_workflows.py run-all --ref main
```

## 当前环境限制（本容器）

本容器到 GitHub 出口存在 `CONNECT tunnel failed, response 403`，因此无法在本地容器内真实访问 GitHub API 或拉取上游仓库；但主仓 CI 在 GitHub runner 中可按上述方式真实执行。
