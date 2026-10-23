#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anti-Slop 机械自检器（AI Reader）

依据：`DESIGN.md` v1.1.0 章节「Anti-Slop 机械自检」的 10 项清单。
目标：把「反 AI 皮」的可证伪项交给脚本，而非修辞。

用法：
    python3 scripts/anti_slop_check.py \
        hs_dev_docs/_02_feature_spec/_03_prototype_html/ai_reader_prototype.html

    # 递归扫描目录下全部 .html / .css
    python3 scripts/anti_slop_check.py --root hs_dev_docs

退出码：0 = 全部可机械判定项 PASS；1 = 存在违规（RUNTIME 项不计入失败）。

说明：本器为**静态**预检（扫描 HTML 结构与 `<style>`）。原型界面由 JS 模板渲染，
因此 #1（emoji）与 #10（符号越界）另需在浏览器**运行态**遍历全部 界面 × 四态
复核 `#frame` 渲染文本，二者互为补充；#4/#8 亦为运行态项。
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

# --------------------------------------------------------------------------- #
# 白名单：DESIGN.md「Symbol & Empty-State Language」封闭枚举
# --------------------------------------------------------------------------- #
SYMBOL_WHITELIST = set("✕●◐○•—↗→▸▾□■≡")
# 排版字符（非 emoji、非 UI 符号，出现在正文里合法）
TYPO_WHITELIST = set("·|!※…“”‘’「」『』—–-（）：；，。、《》？！")

# Extended_Pictographic（Unicode 15 emoji-data，近似）
EP_RANGES = [
    (0x00A9, 0x00A9), (0x00AE, 0x00AE), (0x203C, 0x203C), (0x2049, 0x2049),
    (0x2122, 0x2122), (0x2139, 0x2139), (0x2194, 0x2199), (0x21A9, 0x21AA),
    (0x231A, 0x231B), (0x2328, 0x2328), (0x23CF, 0x23CF), (0x23E9, 0x23F3),
    (0x23F8, 0x23FA), (0x24C2, 0x24C2), (0x25AA, 0x25AB), (0x25B6, 0x25B6),
    (0x25C0, 0x25C0), (0x25FB, 0x25FE), (0x2600, 0x2605), (0x2607, 0x2612),
    (0x2614, 0x2685), (0x2690, 0x2705), (0x2708, 0x2712), (0x2714, 0x2714),
    (0x2716, 0x2716), (0x271D, 0x271D), (0x2721, 0x2721), (0x2728, 0x2728),
    (0x2733, 0x2734), (0x2744, 0x2744), (0x2747, 0x2747), (0x274C, 0x274C),
    (0x274E, 0x274E), (0x2753, 0x2755), (0x2757, 0x2757), (0x2763, 0x2767),
    (0x2795, 0x2797), (0x27A1, 0x27A1), (0x27B0, 0x27B0), (0x27BF, 0x27BF),
    (0x2934, 0x2935), (0x2B05, 0x2B07), (0x2B1B, 0x2B1C), (0x2B50, 0x2B50),
    (0x2B55, 0x2B55), (0x3030, 0x3030), (0x303D, 0x303D), (0x3297, 0x3297),
    (0x3299, 0x3299), (0x1F000, 0x1F0FF), (0x1F10D, 0x1F10F), (0x1F12F, 0x1F12F),
    (0x1F16C, 0x1F171), (0x1F17E, 0x1F17F), (0x1F18E, 0x1F18E), (0x1F191, 0x1F19A),
    (0x1F1AD, 0x1F1E5), (0x1F201, 0x1F20F), (0x1F21A, 0x1F21A), (0x1F22F, 0x1F22F),
    (0x1F232, 0x1F23A), (0x1F23C, 0x1F23F), (0x1F249, 0x1F3FA), (0x1F400, 0x1F53D),
    (0x1F546, 0x1F64F), (0x1F680, 0x1F6FF), (0x1F774, 0x1F77F), (0x1F7D5, 0x1F7FF),
    (0x1F80C, 0x1F80F), (0x1F848, 0x1F84F), (0x1F85A, 0x1F85F), (0x1F888, 0x1F88F),
    (0x1F8AE, 0x1F8FF), (0x1F90C, 0x1F93A), (0x1F93C, 0x1F945), (0x1F947, 0x1FAFF),
    (0x1FC00, 0x1FFFD),
]
# 需要纳入「符号越界」检查的符号区段（UI 字形高发区）
SYMBOL_BLOCKS = [
    (0x2190, 0x21FF),  # arrows
    (0x2200, 0x22FF),  # math operators
    (0x2300, 0x23FF),  # misc technical
    (0x25A0, 0x25FF),  # geometric shapes
    (0x2600, 0x26FF),  # misc symbols
    (0x2700, 0x27BF),  # dingbats
    (0x2B00, 0x2BFF),  # misc symbols and arrows
]

ALLOWED_RADIUS = {0.0, 4.0, 6.0, 8.0, 12.0, 20.0}
RADIUS_VAR = {"--r-xs": 4.0, "--r-sm": 6.0, "--r-md": 8.0, "--r-lg": 12.0, "--r-pill": 20.0}
FAKE_PATTERNS = [r"lorem ipsum", r"\bTODO\b", r"\bFIXME\b", r"\bXXX\b", r"占位文本", r"示例见证"]
# 功能性阴影白名单（焦点环 / 毛玻璃光晕），非装饰性
SHADOW_WHITELIST = [
    re.compile(r"^0\s+0\s+0\s+\d+px"),        # 焦点环
    re.compile(r"^inset\b"),                    # 内阴影（如高亮）
]


def in_ranges(cp: int, ranges) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def strip_to_text(html: str) -> str:
    t = re.sub(r"<style\b.*?</style>", "", html, flags=re.S | re.I)
    t = re.sub(r"<script\b.*?</script>", "", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return t


def extract_style(html: str) -> str:
    return "\n".join(re.findall(r"<style\b.*?</style>", html, flags=re.S | re.I))


def resolve_radius(v: str) -> float | None:
    v = v.strip()
    if v.endswith("%"):
        return None  # 圆/椭圆（50%）单独豁免
    m = re.match(r"var\((--r-[a-z]+)\)", v)
    if m:
        return RADIUS_VAR.get(m.group(1))
    m = re.match(r"(-?[\d.]+)px", v)
    if m:
        return float(m.group(1))
    return None


def check_file(path: pathlib.Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    text = strip_to_text(html)
    css = extract_style(html)
    errs: list[str] = []

    # 1. emoji
    bad = {c for c in text if in_ranges(ord(c), EP_RANGES) and c not in SYMBOL_WHITELIST}
    if bad:
        errs.append(f"[1] emoji 违规: {' '.join(f'{c}(U+{ord(c):04X})' for c in sorted(bad))}")

    # 2. 装饰性阴影
    shadows = re.findall(r"box-shadow\s*:\s*([^;}\n]+)", css)
    deco = [s.strip() for s in shadows if s.strip() != "none"
            and not any(p.search(s.strip()) for p in SHADOW_WHITELIST)]
    if deco:
        errs.append(f"[2] 装饰性 box-shadow: {deco}")

    # 3. 渐变
    grads = re.findall(r"(?:linear|radial)-gradient", css)
    if grads:
        errs.append(f"[3] 渐变出现 {len(grads)} 处")

    # 5. 圆角取值
    radii = set()
    for raw in re.findall(r"border-radius\s*:\s*([^;}\n]+)", css):
        for part in raw.split():
            r = resolve_radius(part)
            if r is not None:
                radii.add(r)
    bad_radius = radii - ALLOWED_RADIUS
    if bad_radius:
        errs.append(f"[5] 圆角越界: {sorted(bad_radius)}（白名单 {sorted(ALLOWED_RADIUS)}）")

    # 6. 字体族
    families = set()
    for fam in re.findall(r"font-family\s*:\s*([^;}\n]+)", css):
        fam = fam.lower()
        if "monospace" in fam:
            families.add("mono")
        elif "serif" in fam and "sans-serif" not in fam:
            families.add("serif")
        else:
            families.add("sans")
    if len(families) > 3:
        errs.append(f"[6] 字体族类别 {len(families)} > 3: {families}")

    # 7. 版心行宽
    m = re.search(r"max-width\s*:\s*(\d+)px", css)
    widths = [int(w) for w in re.findall(r"max-width\s*:\s*(\d+)px", css)]
    body_w = [w for w in widths if 600 <= w <= 800]
    if not any(680 <= w <= 720 for w in widths):
        errs.append(f"[7] 未发现 680–720px 版心（max-width 列表: {sorted(set(widths))}）")

    # 9. 假内容
    low = text.lower()
    for pat in FAKE_PATTERNS:
        if re.search(pat, low if pat.islower() else text):
            errs.append(f"[9] 疑似假内容/占位: {pat}")

    # 10. 符号越界
    out = set()
    for c in text:
        cp = ord(c)
        if cp in (0x00D7, 0x00F7):
            out.add(c)
        elif in_ranges(cp, SYMBOL_BLOCKS) and c not in SYMBOL_WHITELIST:
            out.add(c)
    if out:
        errs.append(f"[10] 符号越界: {' '.join(f'{c}(U+{ord(c):04X})' for c in sorted(out))}")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="Anti-Slop 机械自检（DESIGN.md v1.1.0）")
    ap.add_argument("paths", nargs="*", type=pathlib.Path)
    ap.add_argument("--root", type=pathlib.Path, default=None)
    args = ap.parse_args()

    targets: list[pathlib.Path] = list(args.paths)
    if args.root:
        targets += sorted(
            p for p in args.root.rglob("*") if p.suffix.lower() in (".html", ".css")
        )
    if not targets:
        ap.error("请给出文件路径或 --root 目录")

    failed = 0
    for p in targets:
        errs = check_file(p)
        status = "PASS" if not errs else "FAIL"
        print(f"[{status}] {p}")
        for e in errs:
            print(f"        {e}")
        failed += bool(errs)

    print("-" * 60)
    print("[4] 强调色预算 / [8] 对比度 = RUNTIME 项："
          "需在浏览器运行态按屏统计（见 qa_log_002 运行态实测证据）。")
    print(f"结论：{len(targets)} 文件，{failed} 违规。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
