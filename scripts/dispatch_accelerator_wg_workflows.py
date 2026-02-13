#!/usr/bin/env python3
"""Utilities to orchestrate accelerator-integration-wg workflows via GitHub Actions API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

API = "https://api.github.com"


@dataclass
class WorkflowResult:
    workflow: str
    workflow_id: int
    run_id: int | None
    status: str
    conclusion: str | None
    note: str = ""


def api_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "accelerator-wg-dispatch-script",
    }

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        parsed = None
        if body:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"message": body}
        return e.code, parsed
    except urllib.error.URLError as e:
        return 0, {"message": str(e)}


def list_workflows(owner: str, repo: str, token: str) -> list[dict[str, Any]]:
    url = f"{API}/repos/{owner}/{repo}/actions/workflows?per_page=100"
    status, payload = api_request("GET", url, token)
    if status != 200:
        raise RuntimeError(f"Failed to list workflows: HTTP {status} payload={payload}")
    return payload.get("workflows", [])


def latest_run_id(owner: str, repo: str, token: str, workflow_id: int, branch: str) -> int | None:
    q = urllib.parse.urlencode({"branch": branch, "per_page": 1})
    url = f"{API}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs?{q}"
    status, payload = api_request("GET", url, token)
    if status != 200:
        return None
    runs = payload.get("workflow_runs", [])
    return runs[0]["id"] if runs else None


def dispatch_workflow(owner: str, repo: str, token: str, workflow_id: int, ref: str) -> tuple[bool, str]:
    url = f"{API}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
    status, payload = api_request("POST", url, token, payload={"ref": ref})
    if status == 204:
        return True, ""
    msg = payload.get("message") if isinstance(payload, dict) else str(payload)
    return False, f"HTTP {status}: {msg}"


def wait_run(owner: str, repo: str, token: str, run_id: int, timeout_s: int, interval_s: int) -> tuple[str, str | None]:
    deadline = time.time() + timeout_s
    url = f"{API}/repos/{owner}/{repo}/actions/runs/{run_id}"
    while time.time() < deadline:
        status, payload = api_request("GET", url, token)
        if status != 200:
            return "unknown", None
        run_status = payload.get("status", "unknown")
        conclusion = payload.get("conclusion")
        if run_status == "completed":
            return run_status, conclusion
        time.sleep(interval_s)
    return "timed_out", None


def require_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")
    return token


def cmd_list(args: argparse.Namespace) -> int:
    token = require_token()
    workflows = list_workflows(args.owner, args.repo, token)
    matrix = [
        {
            "id": wf["id"],
            "name": wf["name"],
            "path": wf["path"],
            "state": wf.get("state", "unknown"),
        }
        for wf in workflows
    ]
    print(json.dumps(matrix, ensure_ascii=False))
    return 0


def execute_one(owner: str, repo: str, ref: str, timeout: int, interval: int, workflow_id: int, workflow_name: str, workflow_path: str) -> WorkflowResult:
    token = require_token()
    before = latest_run_id(owner, repo, token, workflow_id, ref)
    ok, note = dispatch_workflow(owner, repo, token, workflow_id, ref)
    if not ok:
        return WorkflowResult(f"{workflow_name} ({workflow_path})", workflow_id, None, "not_dispatched", None, note)

    run_id = None
    for _ in range(30):
        rid = latest_run_id(owner, repo, token, workflow_id, ref)
        if rid is not None and rid != before:
            run_id = rid
            break
        time.sleep(2)

    if run_id is None:
        return WorkflowResult(f"{workflow_name} ({workflow_path})", workflow_id, None, "dispatch_sent", None, "Run id not observed")

    status, conclusion = wait_run(owner, repo, token, run_id, timeout, interval)
    return WorkflowResult(f"{workflow_name} ({workflow_path})", workflow_id, run_id, status, conclusion)


def cmd_run_one(args: argparse.Namespace) -> int:
    result = execute_one(
        owner=args.owner,
        repo=args.repo,
        ref=args.ref,
        timeout=args.timeout,
        interval=args.interval,
        workflow_id=args.workflow_id,
        workflow_name=args.workflow_name,
        workflow_path=args.workflow_path,
    )

    payload = asdict(result)
    print(json.dumps(payload, ensure_ascii=False))
    if args.result_file:
        with open(args.result_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")

    if result.status in {"not_dispatched", "timed_out", "unknown"}:
        return 1
    if result.status == "completed" and result.conclusion != "success":
        return 1
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    token = require_token()
    workflows = list_workflows(args.owner, args.repo, token)
    if not workflows:
        print("No workflows found")
        return 1

    results: list[WorkflowResult] = []
    for wf in workflows:
        result = execute_one(
            owner=args.owner,
            repo=args.repo,
            ref=args.ref,
            timeout=args.timeout,
            interval=args.interval,
            workflow_id=wf["id"],
            workflow_name=wf["name"],
            workflow_path=wf["path"],
        )
        results.append(result)

    failed = False
    print("\n=== Workflow execution summary ===")
    for r in results:
        line = f"- {r.workflow}: status={r.status}"
        if r.run_id is not None:
            line += f", run_id={r.run_id}"
        if r.conclusion is not None:
            line += f", conclusion={r.conclusion}"
        if r.note:
            line += f", note={r.note}"
        print(line)

        if r.status in {"not_dispatched", "timed_out", "unknown"}:
            failed = True
        if r.status == "completed" and r.conclusion != "success":
            failed = True

    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--owner", default="pytorch-fdn")
    common.add_argument("--repo", default="accelerator-integration-wg")

    list_p = sub.add_parser("list", parents=[common], help="List workflows as JSON matrix")
    list_p.set_defaults(func=cmd_list)

    run_common = argparse.ArgumentParser(add_help=False)
    run_common.add_argument("--owner", default="pytorch-fdn")
    run_common.add_argument("--repo", default="accelerator-integration-wg")
    run_common.add_argument("--ref", default="main")
    run_common.add_argument("--timeout", type=int, default=1800)
    run_common.add_argument("--interval", type=int, default=10)

    one_p = sub.add_parser("run-one", parents=[run_common], help="Dispatch and wait for one workflow")
    one_p.add_argument("--workflow-id", type=int, required=True)
    one_p.add_argument("--workflow-name", required=True)
    one_p.add_argument("--workflow-path", required=True)
    one_p.add_argument("--result-file", default="")
    one_p.set_defaults(func=cmd_run_one)

    all_p = sub.add_parser("run-all", parents=[run_common], help="Dispatch and wait for all workflows")
    all_p.set_defaults(func=cmd_run_all)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
