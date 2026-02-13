# pytorch-test

This repository is configured to run CI on GitHub's free default hosted runner (`ubuntu-latest`) without requiring any NPU resources.

## Workflow

- `.github/workflows/default-runner.yml`
  - runs on `push`, `pull_request`, and `workflow_dispatch`
  - uses `runs-on: ubuntu-latest`
  - includes a small Python smoke test
