"""Muse CLI-harness adapter: spec + parser over the shared base.

CLI contract (muse-harness-handoff skill): ``muse exec --json --workspace
W --worktree off --prompt-file FILE``. Discovery is binary plus
``--version`` only, so no models command exists. History continuation is
interactive-only, so fresh-only execution holds by design: the engine
fresh-runs every prompt.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .harness import CLIHarnessProvider, HarnessSpec, parse_json_object_stdout

MUSE_SPEC = HarnessSpec(
    name="muse",
    binary="muse",
    prompt_delivery="file_flag",
    prompt_file_flag="--prompt-file",
    parser="json_object",
    call_workdir=True,
    discovery_argv=None,
    model_from_route=False,
)


class MuseProvider(CLIHarnessProvider):
    def __init__(self, runner=None):
        super().__init__(MUSE_SPEC, runner=runner)

    def build_argv(
        self,
        *,
        model: str,
        prompt: str,
        prompt_file: str | None,
        workspace: Path | None = None,
        workdir: Path | None = None,
    ) -> list[str]:
        # No --model in the documented headless recipe: the CLI default serves.
        assert prompt_file is not None
        return [
            "exec",
            "--json",
            "--workspace", str(workspace or Path.cwd()),
            "--worktree", "off",
            "--prompt-file", prompt_file,
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
