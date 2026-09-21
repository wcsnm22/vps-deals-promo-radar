# ILANG
# TYPE:module ROLE:content-check PROJECT:vps-deals
# ::RULE{每篇必须第一屏给答案⇒lede 里要有可复算的数字或明确结论}
# ::RULE{独家≥30%⇒与对标站语料的连续词重叠必须低于 30%}
# ::RULE{不许有中文残留 视频标题 频道名⇒出现就判不合格}
# ::BOUNDARY{never:为了让检查通过而改数字|scope:file}
"""检查已生成的指南页是否满足第 8 步写稿判据。

用法：
  python content_check.py [对标语料目录]
  对标语料目录默认 ..\\bench（前面 BENCH 阶段抓下来的三家页面正文）
退出码：有任意一篇不合格则 1，否则 0。
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUIDE_DIR = ROOT / "site" / "guide"

MIN_SHINGLE_OVERLAP = 0.30  # 与对标站重叠超过这个比例就判"抄"
SHINGLE = 5
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
VIDEO_RE = re.compile(r"\b(youtube|youtu\.be|subscribe|channel|watch the video|video below|\bhd\b)\b", re.I)


def text_of(html: str) -> str:
    body = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html, flags=re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def shingles(text: str, size: int = SHINGLE) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i:i + size]) for i in range(max(0, len(words) - size + 1))}


def corpus_shingles(bench_dir: Path) -> set[str]:
    out: set[str] = set()
    patterns = ["text_*.txt", "page_*.txt"]
    for pattern in patterns:
        for path in glob.glob(str(bench_dir / "**" / pattern), recursive=True):
            out |= shingles(Path(path).read_text(encoding="utf-8", errors="replace"))
    return out


def check_page(path: Path, bench: set[str]) -> list[str]:
    html = path.read_text(encoding="utf-8")
    text = text_of(html)
    problems: list[str] = []

    lede = re.search(r'<p class="lede">(.*?)</p>', html, re.S)
    if not lede:
        problems.append("没有 lede：第一屏看不到答案")
    else:
        answer = text_of(lede.group(1))
        if not re.search(r"\d", answer):
            problems.append("lede 里没有任何数字：第一屏没有可核对的答案")

    if CJK_RE.search(text):
        problems.append("正文出现中文残留")

    match = VIDEO_RE.search(text)
    if match:
        problems.append(f"出现视频/频道痕迹：{match.group(0)!r}")

    own = shingles(text)
    if own and bench:
        overlap = len(own & bench) / len(own)
        if overlap > MIN_SHINGLE_OVERLAP:
            problems.append(f"与对标站语料重叠 {overlap:.1%}（阈值 {MIN_SHINGLE_OVERLAP:.0%}）")
    else:
        overlap = 0.0

    return problems


def main() -> int:
    bench_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\新建文件夹 (2)\bench")
    bench = corpus_shingles(bench_dir) if bench_dir.exists() else set()
    pages = sorted(GUIDE_DIR.glob("*.html"))
    if not pages:
        print("没有找到指南页：先跑 python build.py")
        return 1
    print(f"对标语料 shingle 数：{len(bench)}（来自 {bench_dir}）")
    failed = 0
    for page in pages:
        problems = check_page(page, bench)
        status = "OK  " if not problems else "FAIL"
        if problems:
            failed += 1
        print(f"[{status}] {page.name}")
        for problem in problems:
            print(f"        - {problem}")
    print(f"\n{len(pages) - failed}/{len(pages)} 篇通过")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
