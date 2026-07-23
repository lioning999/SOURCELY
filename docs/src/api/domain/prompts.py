"""Prompt 构建 — 读 System Prompt + 拼 User Prompt。

domain 层纯函数，零外部依赖（不读 DB、不调 API、不读环境变量）。
"""

import json
import os

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_system_prompt_cache: str | None = None
_optimize_prompt_cache: str | None = None
_interview_qa_prompt_cache: str | None = None
_interview_questions_prompt_cache: str | None = None

# user prompt 截断长度（字符），与 Config.RESUME_TEXT_MAX_LENGTH 对齐
# 6000→10000：避免长简历丢失信息，DeepSeek V4 128K 上下文完全够用
USER_RESUME_MAX_CHARS = 10000


def _load_system_prompt() -> str:
    """读 prompts/diagnose_system.txt。首次调用读文件，后续返回缓存。"""
    global _system_prompt_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache

    path = os.path.join(_PROMPTS_DIR, "diagnose_system.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _system_prompt_cache = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"诊断 System Prompt 文件缺失: {path}。请确认 prompts/diagnose_system.txt 存在。"
        )
    return _system_prompt_cache


def _load_optimize_prompt() -> str:
    """读 prompts/optimize_system.txt。首次调用读文件，后续返回缓存。"""
    global _optimize_prompt_cache
    if _optimize_prompt_cache is not None:
        return _optimize_prompt_cache

    path = os.path.join(_PROMPTS_DIR, "optimize_system.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _optimize_prompt_cache = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"优化 System Prompt 文件缺失: {path}。请确认 prompts/optimize_system.txt 存在。"
        )
    return _optimize_prompt_cache


def _load_interview_qa_prompt() -> str:
    """读 prompts/interview_qa_system.txt。首次调用读文件，后续返回缓存。"""
    global _interview_qa_prompt_cache
    if _interview_qa_prompt_cache is not None:
        return _interview_qa_prompt_cache

    path = os.path.join(_PROMPTS_DIR, "interview_qa_system.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _interview_qa_prompt_cache = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"追问预判 System Prompt 文件缺失: {path}。请确认 prompts/interview_qa_system.txt 存在。"
        )
    return _interview_qa_prompt_cache


def _load_interview_questions_prompt() -> str:
    """读 prompts/interview_questions_system.txt。首次调用读文件，后续返回缓存。"""
    global _interview_questions_prompt_cache
    if _interview_questions_prompt_cache is not None:
        return _interview_questions_prompt_cache

    path = os.path.join(_PROMPTS_DIR, "interview_questions_system.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _interview_questions_prompt_cache = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"模拟面试 System Prompt 文件缺失: {path}。请确认 prompts/interview_questions_system.txt 存在。"
        )
    return _interview_questions_prompt_cache


def build_diagnosis_prompt(resume_text: str, stats_text: str = "") -> list[dict]:
    """构建诊断请求的 messages（system + user）。

    Args:
        resume_text: 简历原文全文
        stats_text: 步骤③的 2 行统计文本（数字锚点率 + 自评可验证率）

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    system_prompt = _load_system_prompt()

    # 简历原文截断到 USER_RESUME_MAX_CHARS，留给 system prompt 足够 token
    truncated = resume_text[:USER_RESUME_MAX_CHARS]

    # 拼 user prompt
    user_parts = ["请诊断以下简历。", "", "## 简历原文", "", truncated]

    if stats_text:
        user_parts.extend(["", "## 系统统计数据（供参考，以简历原文为准）", "", stats_text])

    user_parts.extend(["", "请按你的诊断框架，以 JSON 格式输出完整的诊断报告。不要输出 Markdown，只要纯 JSON。"])

    user_content = "\n".join(user_parts)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_optimize_prompt(
    resume_text: str, diagnose_result: dict
) -> list[dict]:
    """构建优化请求的 messages（system + user）。

    Args:
        resume_text: 简历原文全文
        diagnose_result: 诊断结果 dict，含 fatal_issues

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    system_prompt = _load_optimize_prompt()

    truncated = resume_text[:USER_RESUME_MAX_CHARS]

    # 提取致命问题摘要（精简版，少占 token）
    fatal_summary = []
    for issue in diagnose_result.get("fatal_issues", []):
        fatal_summary.append({
            "id": issue.get("id"),
            "title": issue.get("title"),
            "description": issue.get("description", "")[:150],
            "severity": issue.get("severity"),
        })

    diagnose_brief = {
        "overall_impression": diagnose_result.get("overall_impression", "")[:200],
        "fatal_issues": fatal_summary,
    }

    user_parts = [
        "请基于诊断报告优化以下简历。",
        "",
        "## 诊断报告（精简）",
        json.dumps(diagnose_brief, ensure_ascii=False),
        "",
        "## 简历原文",
        truncated,
        "",
        "请输出优化后的完整简历 + before/after 对比。JSON 格式，不要 Markdown。",
    ]
    user_content = "\n".join(user_parts)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_interview_qa_prompt(
    resume_text: str, diagnose_result: dict, optimized_text: str
) -> list[dict]:
    """构建追问预判请求的 messages（system + user）。

    Args:
        resume_text: 简历原文
        diagnose_result: 诊断结果 dict（整体传入作参考，AI 独立扫描不局限于此）
        optimized_text: 优化后的简历全文

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    system_prompt = _load_interview_qa_prompt()

    truncated_original = resume_text[:3000]  # 原始简历截短——重点在优化后
    truncated_optimized = optimized_text[:USER_RESUME_MAX_CHARS]

    user_parts = [
        "请独立扫描以下简历（原文+优化后），按三层追问方法论生成 5-8 个面试追问靶子。",
        "诊断报告仅作参考，不要局限于其 interview_targets——你独立判断。",
        "",
        "## 诊断报告（参考）",
        json.dumps(diagnose_result, ensure_ascii=False),
        "",
        "## 简历原文",
        truncated_original,
        "",
        "## 优化后简历",
        truncated_optimized,
        "",
        "请输出追问预判。JSON 格式，不要 Markdown。",
    ]
    user_content = "\n".join(user_parts)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_interview_mock_prompt(
    resume_text: str, diagnose_result: dict, optimized_text: str
) -> list[dict]:
    """构建模拟面试请求的 messages（system + user）。

    Args:
        resume_text: 简历原文
        diagnose_result: 诊断结果 dict（整体传入作参考，AI 独立出题不局限于此）
        optimized_text: 优化后的简历全文

    Returns:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    system_prompt = _load_interview_questions_prompt()

    truncated_original = resume_text[:3000]
    truncated_optimized = optimized_text[:USER_RESUME_MAX_CHARS]

    user_parts = [
        "请基于以下候选人简历，生成 5 道模拟面试题。",
        "诊断报告仅作参考——你独立判断，根据简历内容出题。",
        "",
        "## 诊断报告（参考）",
        json.dumps(diagnose_result, ensure_ascii=False),
        "",
        "## 简历原文",
        truncated_original,
        "",
        "## 优化后简历",
        truncated_optimized,
        "",
        "请输出 5 道模拟面试题。JSON 格式，不要 Markdown。",
    ]
    user_content = "\n".join(user_parts)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
