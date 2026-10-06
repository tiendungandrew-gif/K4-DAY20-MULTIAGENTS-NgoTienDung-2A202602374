"""GUIDE Phần 1 - Dựng tác tử (agent) bằng Deep Agents.   >>> SINH VIÊN CÀI ĐẶT make_backend VÀ build_agent <<<

Pseudo-code: guides/pseudocode/01_agent.md
Kiểm tra:    pytest tests/test_02_agent.py
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from .model import make_model
from .subagents import get_subagents

# ---- CÓ SẴN, KHÔNG SỬA: system prompt dùng chung cho mọi sinh viên (để đường cơ sở so sánh được) ----
PATHS_NOTE = (
    "PATHS: every path is relative to the sandbox root and never starts with '/'. "
    "The task files are in the folder workspace/ (for example workspace/app.log). "
    "Use exactly this relative form both in the file tools and in the shell (execute); "
    "the shell starts in the sandbox root. "
)
BASE_PROMPT = (
    "You are an engineering assistant working in a sandbox. "
    + PATHS_NOTE
    + "Use the shell to run Python and tests. "
    "When you are done, reply with a short summary that mentions only files you really created or changed."
)
SKILLS_NOTE = (
    " Skills are in the folder skills/ (one sub-folder per skill with a SKILL.md). "
    "As your FIRST action, read the SKILL.md of every skill whose description could apply to the task, "
    "then follow them. Never modify skills/."
)
SUBAGENTS_NOTE = (
    " You have specialised subagents (see the description of the task tool). "
    "For anything beyond a trivial step, delegate to a suitable subagent and put ALL the task rules and file paths "
    "in the delegation message, because a subagent sees only what you send. "
    "Check what a subagent returns before you rely on it."
)
# --------------------------------------------------------------------------------------------------


from deepagents.backends.protocol import ExecuteResponse


class _ShShellBackend(LocalShellBackend):
    def __init__(self, *args, sh_path: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._sh_path = sh_path

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        if not command or not isinstance(command, str):
            return super().execute(command, timeout=timeout)
        effective_timeout = timeout if timeout is not None else self._default_timeout
        if effective_timeout <= 0:
            raise ValueError(f"timeout must be positive, got {effective_timeout}")
        try:
            res = subprocess.run(
                [self._sh_path, "-c", command],
                check=False,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                text=True,
                timeout=effective_timeout,
                env=self._env,
                cwd=str(self.cwd),
            )
            output_parts = []
            if res.stdout:
                output_parts.append(res.stdout)
            if res.stderr:
                output_parts.extend(f"[stderr] {line}" for line in res.stderr.strip().split("\n") if line)
            output = "\n".join(output_parts) if output_parts else "<no output>"
            truncated = False
            if len(output) > self._max_output_bytes:
                output = output[: self._max_output_bytes] + f"\n\n... Output truncated at {self._max_output_bytes} bytes."
                truncated = True
            if res.returncode != 0:
                output = f"{output.rstrip()}\n\nExit code: {res.returncode}"
            return ExecuteResponse(output=output, exit_code=res.returncode, truncated=truncated)
        except subprocess.TimeoutExpired:
            return ExecuteResponse(output=f"Error: Command timed out after {effective_timeout} seconds.", exit_code=124, truncated=False)
        except Exception as e:
            return ExecuteResponse(output=f"Error executing command ({type(e).__name__}): {e}", exit_code=1, truncated=False)


def make_backend(sandbox: Path):
    """Tạo backend (môi trường thực thi) cho tác tử.

    Yêu cầu:
      - Thư mục gốc (root_dir) là `sandbox`; đường dẫn tương đối `workspace/...` và `skills/...`
        phải dùng được ở CẢ công cụ tệp lẫn shell (shell chạy với thư mục làm việc = `sandbox`).
      - Tác tử chạy được lệnh shell và gọi được `python` (cần đặt PATH).
      - KHÔNG chuyển biến môi trường của bạn vào shell của tác tử (khóa API không được lộ).
    """
    py_dir = str(Path(sys.executable).parent)
    paths = [py_dir]
    for tool in ("which", "env", "sh", "bash"):
        loc = shutil.which(tool)
        if loc:
            d = str(Path(loc).parent)
            if d not in paths:
                paths.append(d)
    if sys.platform == "win32":
        for d in ("C:\\Windows\\system32", "C:\\Windows"):
            if d not in paths:
                paths.append(d)
        path_str = ";".join(paths) + ":/usr/local/bin:/usr/bin:/bin"
    else:
        path_str = f"{py_dir}:/usr/local/bin:/usr/bin:/bin"

    env = {
        "PATH": path_str,
        "HOME": str(sandbox),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    sh_bin = shutil.which("sh") if sys.platform == "win32" else None
    backend_cls = _ShShellBackend if sh_bin else LocalShellBackend
    extra = {"sh_path": sh_bin} if sh_bin else {}

    return backend_cls(
        root_dir=sandbox,
        virtual_mode=True,
        inherit_env=False,
        env=env,
        timeout=120,
        **extra,
    )


def build_agent(sandbox: Path, mode: str = "single", use_skills: bool = False, model=None):
    """Tạo tác tử Deep Agents.

    Tham số:
      sandbox:    thư mục chứa `workspace/` (và `skills/` nếu có).
      mode:       "single"    -> tác tử mặc định (có subagent `general-purpose` sẵn của Deep Agents)
                  "subagents" -> thêm các subagent từ `get_subagents()` (nối PATHS_NOTE vào `system_prompt` của MỖI subagent,
                                 vì subagent không nhận BASE_PROMPT) và thêm SUBAGENTS_NOTE vào prompt chính
      use_skills: True -> nạp thư mục "/skills/" qua tham số `skills=` của create_deep_agent
                  và thêm SKILLS_NOTE vào prompt.
      model:      mô hình ngôn ngữ; None -> dùng `make_model()`.
    mode không hợp lệ -> ném ValueError.
    Trả về: đồ thị (graph) đã biên dịch, gọi bằng `.invoke({"messages": [...]})`.
    """
    if mode not in {"single", "subagents"}:
        raise ValueError(f"Unknown mode: {mode}. Must be 'single' or 'subagents'.")

    kwargs = {}
    prompt = BASE_PROMPT

    if mode == "subagents":
        kwargs["subagents"] = [
            {**sub, "system_prompt": sub["system_prompt"] + " " + PATHS_NOTE}
            for sub in get_subagents()
        ]
        prompt = prompt + SUBAGENTS_NOTE

    if use_skills:
        kwargs["skills"] = ["/skills/"]
        prompt = prompt + SKILLS_NOTE

    if model is None:
        model = make_model()
        if hasattr(model, "max_tokens") and model.max_tokens is None:
            model.max_tokens = int(os.getenv("LAB_MAX_TOKENS", "1024"))
        if hasattr(model, "_generate"):
            orig_generate = model._generate

            def _safe_generate(*args, **kwargs):
                for attempt in range(4):
                    try:
                        return orig_generate(*args, **kwargs)
                    except Exception as exc:
                        if "402" in str(exc) and attempt < 3:
                            wait_s = 35 * (attempt + 1)
                            print(f"\n[402 In-flight Limit] Waiting {wait_s}s for budget settlement (attempt {attempt + 1}/3)...", flush=True)
                            time.sleep(wait_s)
                            continue
                        raise

            model._generate = _safe_generate

    return create_deep_agent(
        model=model,
        system_prompt=prompt,
        backend=make_backend(sandbox),
        **kwargs,
    )


