"""Rules 提取 — 纯正则统计，零 LLM，毫秒级。

提取两类数据作为 AI 诊断的数据附件：
  数字统计 — 数字总数 + 有锚点比例
  自评统计 — 能力声称总数 + 可验证比例

为什么只传 2 行统计？HR 经验：数字精确计数是 LLM 弱项，传统计。
技能、证书、动词——Pro 读原文比正则更准，不传。传多了反而干扰。
"""

import re

# ── 数字锚点正则 ──────────────────────────────
# 三类锚点：时间、对比、来源
_ANCHOR_PATTERNS = [
    # 时间锚点："在3个月内完成"、"2020年至今"、"3年经验"
    re.compile(r"(在|历时|耗时|为期|用了|花了)\s*\d+"),
    re.compile(r"\d+\s*(个月|年|周|天|小时|分钟|季度|学期)"),
    re.compile(r"\d{4}\s*[年\./]\s*\d{1,2}[月\./]?\s*[至到\-~—]\s*"),
    # 对比锚点："提升30%"、"相比上季度"、"同比增长"
    re.compile(r"(提升|增长|增加|提高|降低|减少|下降|优化|改善|压缩|缩短|节省|节约|超出|超过|超额)\s*\d+"),
    re.compile(r"(同比|环比|相比|较|比)\s*[一-龥]*\s*\d+"),
    # 来源锚点："通过用户调研""经XX认证""根据XX数据"
    re.compile(r"(通过|经|根据|基于|从|来自|调研|调查|分析|统计|监测)\s*[一-龥]{2,10}(发现|显示|得出|获得|收集|汇总)"),
    re.compile(r"(调研|问卷|访谈|采集|抓取|爬取|统计|监测)\s*\d+"),
]

# 匹配信息数字（带单位或量词的数字，排除纯年份/电话号码）
_NUMBER_PATTERN = re.compile(
    r"\d+\.?\d*\s*[%％万wW人个次篇家项倍月日天年元块亿千万百十kKmMbB]|"
    r"\d+\.?\d*\s*[份张页条笔轮场届期组套批次版台件颗段句位级别代]|"
    r"\d+\s*[-~至到]\s*\d+|"
    r"(?<!\d)\d{1,3}(?:,\d{3})+(?!\d)|"  # 带逗号的数字 1,500
    r"\d+\.\d+(?!\d)"  # 小数（非日期）
)

# 排除模式：不是信息数字
_NOT_NUMBER = re.compile(
    r"^\d{4}$|"           # 纯年份
    r"^\d{4}[\./]\d{1,2}$|"  # 年月
    r"^\d{11,}$|"         # 电话号码
    r"^\d{6,10}$"         # QQ号/邮编
)


def count_digits(text: str) -> dict:
    """统计信息数字及锚点率。

    Returns:
        {total: int, anchored: int, anchored_pct: int}
    """
    # 提取所有候选数字
    candidates: list[str] = []
    for m in _NUMBER_PATTERN.finditer(text):
        candidates.append(m.group())

    # 过滤非信息数字
    numbers = [n for n in candidates if not _NOT_NUMBER.match(n)]
    total = len(numbers)

    if total == 0:
        return {"total": 0, "anchored": 0, "anchored_pct": 0}

    # 检查每个数字是否有锚点（任一锚点模式匹配数字附近的上下文）
    anchored = 0
    for n in numbers:
        # 找到数字在原文中的位置
        idx = text.find(n)
        if idx == -1:
            continue
        # 取数字前后各 50 字符作为上下文
        start = max(0, idx - 50)
        end = min(len(text), idx + len(n) + 50)
        context = text[start:end]

        # 检查是否匹配任一锚点模式
        for pattern in _ANCHOR_PATTERNS:
            if pattern.search(context):
                anchored += 1
                break

    pct = round(anchored / total * 100)
    return {"total": total, "anchored": anchored, "anchored_pct": pct}


# ── 自评声称正则 ──────────────────────────────

# 软技能/性格描述关键词（不可验证）
_SOFT_SKILL_KEYWORDS = [
    "性格", "开朗", "细心", "负责", "认真", "踏实",
    "沟通", "团队", "协作", "合作", "协调",
    "学习能力", "适应", "抗压", "主动", "热忱",
    "好奇心", "耐心", "吃苦", "上进", "积极",
    "乐观", "稳重", "踏实肯干", "努力", "勤奋",
    "善于沟通", "团队精神", "抗压能力", "责任心",
    "执行力", "工作态度", "敬业", "诚实", "正直",
]

# 可验证声称关键词（技能/经验/领域知识）
_VERIFIABLE_KEYWORDS = [
    "擅长", "精通", "熟悉", "掌握", "了解", "具备",
    "有", "拥有", "具有", "积累",
]

# 自评段落定位
_SELF_ASSESSMENT_HEADERS = [
    "自我评价", "自我介绍", "个人评价", "自评",
    "关于我", "个人简介", "个人特质",
]


def _extract_self_assessment(text: str) -> str:
    """从简历中提取自我评价段落。"""
    for header in _SELF_ASSESSMENT_HEADERS:
        pattern = re.compile(
            rf"(?:^|\n)\s*{re.escape(header)}\s*[：:]*\s*\n?(.*?)(?=\n\s*(?:技能|证书|项目|工作|实习|教育|[A-Za-z])|\Z)",
            re.DOTALL | re.IGNORECASE
        )
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    # 未找到明确标题，取后 1/3 段落
    lines = text.split("\n")
    third = len(lines) * 2 // 3
    return "\n".join(lines[third:]).strip()


def _split_claims(self_text: str) -> list[str]:
    """将自评段落拆分为声称列表。按句号、分号、换行拆分。"""
    # 先按换行拆，再按句子标点拆
    raw = re.split(r"[。；;，,\n]", self_text)
    claims = []
    for s in raw:
        s = s.strip()
        # 过滤过短或纯标点的片段
        if len(s) >= 4 and not re.match(r'^[\s、，,。；;·]+$', s):
            claims.append(s)
    return claims


def count_self_claims(text: str) -> dict:
    """统计自评声称的可验证率。

    从自我评价段拆句 → 逐条判断是"可验证声称"还是"软技能形容词"。

    Returns:
        {total: int, verifiable: int, unverifiable: int, verifiable_pct: int}
    """
    self_text = _extract_self_assessment(text)
    if not self_text:
        return {"total": 0, "verifiable": 0, "unverifiable": 0, "verifiable_pct": 0}

    claims = _split_claims(self_text)
    if not claims:
        return {"total": 0, "verifiable": 0, "unverifiable": 0, "verifiable_pct": 0}

    verifiable = 0
    unverifiable = 0

    for claim in claims:
        # 检查是否含软技能关键词
        is_soft = any(kw in claim for kw in _SOFT_SKILL_KEYWORDS)
        # 检查是否含可验证关键词
        has_verifiable = any(kw in claim for kw in _VERIFIABLE_KEYWORDS)

        if is_soft and not has_verifiable:
            unverifiable += 1
        elif has_verifiable:
            verifiable += 1
        else:
            # 既不含软技能词也不含可验证词——偏可验证（可能是直接陈述）
            verifiable += 1

    total = verifiable + unverifiable
    pct = round(verifiable / total * 100) if total > 0 else 0
    return {
        "total": total,
        "verifiable": verifiable,
        "unverifiable": unverifiable,
        "verifiable_pct": pct,
    }


# ── 传输噪声清洗 ────────────────────────────


def clean_resume_text(text: str) -> str:
    """清洗传输噪声：乱码碎片、编码断裂、多余空行。只归档，不删原文。"""
    import re
    # 连续 3+ 非正常字符的乱码碎片 → 删除
    text = re.sub(
        r'[^一-鿿㐀-䶿豈-﫿#\w\s\d.,;:!?()（）【】《》、。，；：！？·\-+%/@\n#&*]+',
        '', text,
    )
    # 连续空行合并为单空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 行首尾空白清理
    text = '\n'.join(line.strip() for line in text.split('\n'))
    return text.strip()


# ── 出口安全网：自评权力词扫描 ──────────────

# 自评重写是 AI 整段生成的，不走 _sanitize_pairs 的 before/after 框架。
# 这里做纯文本扫描，防止自评里出现权力越界词。
_SELF_EVAL_POWER_FIX: dict[str, str] = {
    "独立完成": "完成",
    "独立负责": "承担",
    "主导": "参与",
    "牵头": "配合",
    "统筹": "协调",
}


def sanitize_self_evaluation(text: str) -> str:
    """扫描自评段，替换权力越界词。纯文本，零依赖。"""
    import re
    match = re.search(
        r'(?:^|\n)\s*[（(]?[五5][）)、]\s*自[我评]评价[^\n]*\n(.*?)(?=\n[（(]?[六6][）)、]|\n（注[：:]|\Z)',
        text, re.DOTALL,
    )
    if not match:
        return text
    se = match.group(0)
    for forbidden, safe in _SELF_EVAL_POWER_FIX.items():
        se = se.replace(forbidden, safe)
    return text.replace(match.group(0), se)


# ── 格式化 ────────────────────────────────────

def format_rules_stats(numbers: dict, claims: dict) -> str:
    """格式化为 user prompt 附件（≈150 字符）。

    例：
        数字统计：14 个信息数字，4 个有锚点（28%）
        自评统计：2 条能力声称，2 条可验证（100%），0 条为性格描述/软技能形容词（不可验证）
    """
    lines = [
        f"数字统计：{numbers['total']} 个信息数字，"
        f"{numbers['anchored']} 个有锚点（{numbers['anchored_pct']}%）",
        f"自评统计：{claims['total']} 条能力声称，"
        f"{claims['verifiable']} 条可验证（{claims['verifiable_pct']}%），"
        f"{claims['unverifiable']} 条为性格描述/软技能形容词（不可验证）",
    ]
    return "\n".join(lines)
