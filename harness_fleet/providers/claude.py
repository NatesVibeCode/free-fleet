"""Claude Code CLI-harness adapter: spec + parser over the shared base.

CLI contract (claude-harness-handoff skill): ``claude -p --output-format
json`` with the prompt on stdin from a prompt file; one headless turn
returns a single JSON object (result + usage). Discovery is binary plus
``--version`` only, so no models command exists. ``--resume`` continues an
exact conversation and is documented but never executed: the engine
fresh-runs every prompt.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .harness import CLIHarnessProvider, HarnessSpec, parse_json_object_stdout

CLAUDE_SPEC = HarnessSpec(
    name="claude",
    binary="claude",
    prompt_delivery="stdin",
    parser="json_object",
    discovery_argv=None,
    model_from_route=False,
)


class ClaudeProvider(CLIHarnessProvider):
    def __init__(self, runner=None):
        super().__init__(CLAUDE_SPEC, runner=runner)

    def build_argv(
        self,
        *,
        model: str,
        prompt: str,
        prompt_file: str | None,
        workspace: Path | None = None,
        workdir: Path | None = None,
    ) -> list[str]:
        # No --model in the headless recipe: the CLI default serves the turn.
        return ["-p", "--output-format", "json"]

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
