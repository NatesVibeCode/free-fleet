"""Cursor CLI-harness adapter: spec + parser over the shared base.

CLI contract (cursor-harness-handoff skill): ``cursor-agent --workspace W
--print --output-format json TASK`` with the prompt as ONE argv element
(the CLI advertises no prompt-file flag; long prompts travel as a single
argument, never shell text). ``--model`` selects an explicit model from
``cursor-agent models`` discovery, and ``--sandbox enabled`` is the
skill-documented lockdown for unattended runs. ``--resume`` continues an
exact chat and is documented but never executed: the engine fresh-runs
every prompt.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .harness import CLIHarnessProvider, HarnessSpec, parse_json_object_stdout

CURSOR_SPEC = HarnessSpec(
    name="cursor",
    binary="cursor-agent",
    prompt_delivery="argv_last",
    parser="json_object",
    task_config_strategy="cursor_sandbox_enabled",
    discovery_argv=["models"],
    model_from_route=True,
)


class CursorProvider(CLIHarnessProvider):
    def __init__(self, runner=None):
        super().__init__(CURSOR_SPEC, runner=runner)

    def build_argv(
        self,
        *,
        model: str,
        prompt: str,
        prompt_file: str | None,
        workspace: Path | None = None,
        workdir: Path | None = None,
    ) -> list[str]:
        return [
            "--workspace", str(workspace or Path.cwd()),
            "--sandbox", "enabled",
            "--print",
            "--output-format", "json",
            "--model", model,
            prompt,
        ]

    def parse_output(
        self,
        *,
        code: int,
        stdout: str,
        stderr: str,
        receipt: dict[str, Any],
        started: float,
    ) -> tuple[bool, str | None, dict[str, Any]]:
        if code != 0:
            err_msg = (stderr or stdout)[-500:] or f"Exit code {code}"
            receipt["error"] = err_msg
            receipt["error_type"] = (
                "rate_limit" if ("429" in err_msg.lower() or "rate limit" in err_msg.lower())
                else "inference_error"
            )
            if receipt["error_type"] == "rate_limit":
                receipt["retry_after"] = 10.0
            return False, None, receipt
        return parse_json_object_stdout(stdout, receipt=receipt)
