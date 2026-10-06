"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    """
    return [
        {
            "name": "explorer",
            "description": (
                "Delegate to explorer when you need to inspect files, read instructions, examine directory "
                "structures, read README or docstrings, check sample data, or analyze error logs before making changes. "
                "Explorer inspects and reports factual findings without modifying any files."
            ),
            "system_prompt": (
                "You are an exploration subagent. Your role is to explore the workspace, inspect files, read docstrings, "
                "examine raw data and log formats, and report clear, factual observations back to the main agent. "
                "Do NOT modify or create any files."
            ),
        },
        {
            "name": "implementer",
            "description": (
                "Delegate to implementer when you need to perform concrete changes: edit code, fix bugs, clean or "
                "transform data, process logs, or run verification scripts via shell. "
                "Implementer performs the modifications and reports the result."
            ),
            "system_prompt": (
                "You are an implementation subagent. Your role is to make targeted code or data modifications, "
                "apply fixes, and run commands in the sandbox shell to verify your implementation. "
                "Report exactly what changes were made and whether tests pass."
            ),
        },
        {
            "name": "reviewer",
            "description": (
                "Delegate to reviewer after changes are implemented to perform independent verification against all "
                "specifications, check edge cases, verify data formats, and run test suites. "
                "Reviewer inspects files and runs tests without modifying any files."
            ),
            "system_prompt": (
                "You are a reviewer subagent. Your role is to independently verify that solutions satisfy all requirements, "
                "specifications, edge cases, and grading criteria. Run tests and validate outputs. "
                "Do NOT modify any files."
            ),
        },
    ]

