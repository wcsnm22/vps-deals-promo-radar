# ILANG
# TYPE:guard ROLE:regression-check PROJECT:vps-deals
# ::RULE{某家 provider 整批抓挂⇒退出码非零 让调用方停下 不许把缩小一半的数据集当成当天的事实}
# ::RULE{基准线取 HEAD 与 origin/main 里更全的那一份⇒本地 HEAD 自己退化过时也看得出整整一家归零}
# ::BOUNDARY{never:改数据 编数据 替抓取失败圆场|scope:file}
"""发布前的退化守卫：某家 provider 整批归零就不许发。

抓取失败（证书错误、超时、被拒抓）和厂商真的整体下架，在数据里长得一样，
但后果差得远：前者会把半边数据集当成今天的事实发上线，顺带删掉整批页面。
这个判据只拦"整整一家从有到无"，因为那是抓取失败的样子——一家厂商不会
在某天同时下架全部套餐。

两条发布路径都用它，判据只有这一份：
  * `daily.py` 直接 import 这里的函数；
  * GitHub Actions（.github/workflows/update.yml）跑 `python guard.py`，
    非零退出就让整个 job 停下，后面的 commit/deploy 都不执行。

手动排查时给一个明确的豁免口：设 GUARD_FORCE=1 就跳过判断并说明原因。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFERS_REL = "data/offers.json"


def previous_offers() -> dict | None:
    """退化的基准线：取 HEAD 与 origin/main 里"更全"的那一份抓取结果。

    只拿它当基准线，不当数据来源：抓挂一家时用来看是不是整整一家归零。
    两边都看，是因为本地 HEAD 可能已经是退化过的那一份——拿它当基准，
    整整一家归零这件事在下次运行时就看不出来了。远端通常是权威且更全的。
    读不到（首次运行、浅克隆、文件不在版本库里）就返回 None，不做判断。
    """
    best: dict | None = None
    best_count = -1
    for rev in ("HEAD", "origin/main"):
        proc = subprocess.run(
            ["git", "show", f"{rev}:{OFFERS_REL}"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            continue
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            continue
        count = len(payload.get("offers", []))
        if count > best_count:
            best, best_count = payload, count
    return best


def dataset_guard(current: dict, previous: dict | None) -> tuple[int, str]:
    """某家 provider 从"有若干条"掉到"一条都没有"就判本轮抓取退化。

    只拦整整一家归零这一种情况：那是抓取失败的样子（证书错误、超时、被拒抓），
    不是厂商真的同时下架了全部套餐。少抓几条不拦——价格页本来就会变。
    判据和 ::OBJECTIVE{keep_pipeline_honest} 一致：宁可这一轮不发，
    也不要把缩小一半的数据集当作当天的事实发上线。

    返回 0/1 而不是 True/False：Python 里 False == 0 是 True，拿布尔值当退出码
    去和 0 比，判据恒真，守卫会静悄悄地失效。
    """
    if not previous:
        return 0, "[skip] no previous snapshot to compare against"
    before = Counter(item.get("provider", "?") for item in previous.get("offers", []))
    after = Counter(item.get("provider", "?") for item in current.get("offers", []))
    vanished = sorted(name for name, count in before.items() if count > 0 and after.get(name, 0) == 0)
    if not vanished:
        return 0, f"[ok] no provider lost all of its offers ({len(current.get('offers', []))} offers kept)"
    detail = ", ".join(f"{name} ({before[name]} -> 0)" for name in vanished)
    return 1, f"[fail] scrape regressed, provider(s) lost every offer: {detail}"


def main() -> int:
    if os.environ.get("GUARD_FORCE") == "1":
        print("[skip] GUARD_FORCE=1, regression check bypassed on purpose")
        return 0
    path = ROOT / OFFERS_REL
    if not path.exists():
        print(f"[skip] {OFFERS_REL} not produced yet; nothing to judge")
        return 0
    current = json.loads(path.read_text(encoding="utf-8"))
    code, message = dataset_guard(current, previous_offers())
    print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
