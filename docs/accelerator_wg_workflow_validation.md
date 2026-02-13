# accelerator-integration-wg 工作流分析与逐项验证记录

## 当前状态

当前环境访问 GitHub 受限（HTTPS CONNECT 403），因此**无法在本环境内完成远端 submodule 拉取**，也无法读取目标仓库的真实 workflow 文件做逐项实证验证。

## 阻塞复现

```bash
git ls-remote https://github.com/pytorch-fdn/accelerator-integration-wg.git -h refs/heads/main
# fatal: unable to access ... CONNECT tunnel failed, response 403
```

## 正确接入方式（在可访问 GitHub 的环境）

```bash
./scripts/link_accelerator_submodule.sh
```

该脚本会执行：

1. `git submodule add https://github.com/pytorch-fdn/accelerator-integration-wg.git third_party/accelerator-integration-wg`
2. `git submodule sync --recursive`
3. `git submodule update --init --recursive`

## 逐项验证流程（拉取成功后）

```bash
# 1) 枚举所有 workflow
find third_party/accelerator-integration-wg/.github/workflows -type f \( -name '*.yml' -o -name '*.yaml' \) | sort

# 2) 逐个检查触发器 / runner / action 版本
#    建议重点检查:
#    - on: push/pull_request/workflow_dispatch/schedule
#    - jobs.<job>.runs-on
#    - uses: <action>@<ref> 是否固定到 tag/SHA

# 3) 如果仓库提供 lint/test 命令，逐项执行并记录结果
```

## 说明

上一次提交中的 submodule gitlink 指向了本地临时仓库提交，可能导致 PR 校验状态异常。本次已移除该无效 gitlink，改为仅保留可复现的“正确接入与验证流程”。
