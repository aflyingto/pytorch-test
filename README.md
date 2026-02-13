# pytorch-test

This repository is configured to run CI on GitHub's free default hosted runner (`ubuntu-latest`) without requiring any NPU resources.

## Workflow

- `.github/workflows/default-runner.yml`
  - runs on `push`, `pull_request`, and `workflow_dispatch`
  - uses `runs-on: ubuntu-latest`
  - includes a small Python smoke test

- `.github/workflows/ai-code-detection.yml`
  - runs on `pull_request` (opened/synchronize/reopened/ready_for_review) and `workflow_dispatch`
  - uses GitHub official `github/codeql-action` to scan GitHub Actions workflows in this repository
  - configured with `languages: actions` (suitable for this repo, which currently has no Python source tree)
  - no external API key is required
