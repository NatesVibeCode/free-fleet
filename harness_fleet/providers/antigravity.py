"""Antigravity CLI-harness adapter: spec + parser over the shared base.

CLI contract (antigravity-harness-handoff skill): ``agy --output-format
json --print TASK`` with the prompt as ONE argv element (this CLI does not
use ``--workspace`` or ``--prompt-file`` syntax). Discovery is binary plus
``--version`` only, so no models command exists. ``--conversation``
continues an exact conversation and is documented but never executed: the
engine fresh-runs every prompt. Permission-skip flags are deliberately
absent: fleet workers run tool-less JSON prompts unattended.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .harness import CLIHarnessProvider, HarnessSpec, parse_json_object_stdout

ANTIGRAVITY_SPEC = HarnessSpec(
    name="antigravity",
    binary="agy",
    prompt_delivery="argv_last",
    parser="json_object",
    discovery_argv=None,
    model_from_route=False,
)


class AntigravityProvider(CLIHarnessProvider):
    def __init__(self, runner=None):
        super().__init__(ANTIGRAVITY_SPEC, runner=runner)

    def build_argv(
        self,
        *,
        model: str,
        prompt: str,
        prompt_file: str | None,
        workspace: Path | None = None,
        workdir: Path | None = None,
    ) -> list[str]:
        # No --model in the documented one-shot recipe: the CLI default serves.
        return ["--output-format", "json", "--print", prompt]

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
