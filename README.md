# pytorch-test

This repository is configured to run CI on GitHub's free default hosted runner (`ubuntu-latest`) without requiring any NPU resources.

## Workflow

- `.github/workflows/default-runner.yml`
  - runs on `push`, `pull_request`, and `workflow_dispatch`
  - uses `runs-on: ubuntu-latest`
  - includes a small Python smoke test

- `.github/workflows/ai-code-detection.yml`
  - runs on `pull_request` (opened/synchronize/reopened/ready_for_review) and `workflow_dispatch`
  - uses `anc95/ChatGPT-CodeReview` to perform AI-assisted code detection/review on PR changes
  - requires repository secret `OPENAI_API_KEY`
