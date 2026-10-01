# ILANG
# TYPE:tool ROLE:keyword-bank PROJECT:vps-deals
# ::RULE{词库只收公开的搜索补全接口返回的原话⇒不估搜索量 不估难度 不编出价}
# ::RULE{抓之前读 robots.txt⇒不允许就整轮跳过 并原样记下来}
# ::RULE{同一轮内同一查询只请求一次⇒不对别人服务器反复打}
# ::BOUNDARY{never:编搜索量 难度 出价 或把补全当成搜索量|scope:file}
"""每天往弹药库里填东西：把搜索补全接口返回的真实查询存成清单。

这个文件只做两件事：
  1. 拿公开的 suggest 接口（返回的就是真人在搜的查询原话），按 @KEYWORD 和疑问词前缀各抓一轮；
  2. 存成 data/keyword-bank.json，并把**问句形态**的那部分单独列出来——
     疑问词开头的查询本身就是"老外真在纠结什么"，可以直接当标题用。

不估搜索量（那是群里的事），不写排名，不碰站点构建。
用法：python keyword_bank.py           # 抓一轮并合并进词库
      python keyword_bank.py --list    # 只看词库里已经有什么
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / ".ilang" / "site.ilang"
BANK_PATH = ROOT / "data" / "keyword-bank.json"
SUGGEST = "https://suggestqueries.google.com/complete/search"
USER_AGENT = "vps-deals-keyword-bank/1.0 (+https://vpsdealsradar.com/about)"
TIMEOUT = 20

# 疑问词前缀：用它们拼出的建议就是"一句话问句"，直接能做标题（第 10 步 T3/T4 要的东西）。
QUESTION_PREFIXES = ["how", "what", "which", "is", "does", "can", "why", "are", "do"]
QUESTION_RE = re.compile(r"^(how|what|which|is|does|can|why|are|do|should|where|when)\b", re.I)

# 一档一批：主词 + 主词的常见限定词 + 疑问词前缀。别把请求铺太大。
MODIFIERS = ["", "cheap", "best", "for beginners", "with windows", "reddit", "usa"]


def read_keyword() -> str:
    """@KEYWORD 只从配置里读。配置里没有就问，不许自己估一个。

    认两种写法：`::STATE{@KEYWORD, value:cheap vps, ...}` 和 `KEYWORD | cheap vps`。
    值为空（`value:,`）等于还没定，按没有处理。注释行（# 开头）不参与匹配——
    注释里举例写过 `value:...`，不排掉就会把例子当成真值。
    """
    text = CONFIG_PATH.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    body = "\n".join(lines)
    match = re.search(r"@KEYWORD[^\n]*?value\s*:\s*([^,}\n]+)", body)
    if match and match.group(1).strip():
        return match.group(1).strip()
    match = re.search(r"KEYWORD\s*\|[^|\n]*\|?\s*([^|\n]+)", body)
    value = match.group(1).strip() if match else ""
    return value if value and "第" not in value else ""


def robots_allows(url: str) -> tuple[bool, str]:
    parser = urllib.robotparser.RobotFileParser()
    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    parser.set_url(f"{origin}/robots.txt")
    try:
        parser.read()
    except Exception as exc:  # noqa: BLE001
        return True, f"robots.txt 读不到（{type(exc).__name__}）：按允许处理"
    allowed = parser.can_fetch(USER_AGENT, url) or parser.can_fetch("*", url)
    return allowed, "" if allowed else "robots.txt 不允许这个路径"


def suggest(query: str) -> list[str]:
    """公开补全接口：返回的就是真人正在搜的查询原话。一次一个查询。"""
    params = urllib.parse.urlencode({"client": "firefox", "hl": "en", "gl": "us", "q": query})
    request = urllib.request.Request(
        f"{SUGGEST}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    return [item for item in payload[1] if isinstance(item, str)]


def queries_for(keyword: str) -> list[str]:
    out: list[str] = []
    for modifier in MODIFIERS:
        out.append(" ".join(part for part in (modifier, keyword) if part))
    for prefix in QUESTION_PREFIXES:
        out.append(f"{prefix} {keyword}")
        out.append(f"{prefix} {keyword} cost")
    seen: dict[str, None] = {}
    for query in out:
        seen.setdefault(query.lower(), None)
    return list(seen)


def merge(bank: dict, suggestions: dict[str, list[str]], stamp: str) -> dict:
    """把这一轮的结果并进词库：老词保留首次出现时间，新词记这一轮的时间。"""
    entries: dict[str, dict] = {item["query"]: item for item in bank.get("queries", [])}
    rounds = bank.get("rounds", [])
    for query, results in suggestions.items():
        for text in results:
            key = text.strip()
            if not key:
                continue
            item = entries.get(key)
            if item is None:
                entries[key] = {
                    "query": key,
                    "first_seen": stamp,
                    "last_seen": stamp,
                    "from": [query],
                    "question": bool(QUESTION_RE.match(key)),
                }
            else:
                item["last_seen"] = stamp
                if query not in item["from"]:
                    item["from"].append(query)
                item["question"] = bool(QUESTION_RE.match(key))
    rounds.append({"ran_at": stamp, "queries": len(suggestions), "found": sum(len(v) for v in suggestions.values())})
    return {
        "generated_at": stamp,
        "note": "查询原话来自公开的搜索补全接口，不是估的搜索量；这里没有搜索量、难度或出价。",
        "queries": sorted(entries.values(), key=lambda item: item["query"]),
        "rounds": rounds[-40:],
    }


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8")) if BANK_PATH.exists() else {"queries": [], "rounds": []}

    if "--list" in sys.argv:
        questions = [item for item in bank.get("queries", []) if item.get("question")]
        print(f"词库共 {len(bank.get('queries', []))} 条，其中问句 {len(questions)} 条（抓取轮次 {len(bank.get('rounds', []))}）")
        for item in questions[:40]:
            print(f"  [{item['first_seen'][:10]}] {item['query']}")
        return 0

    keyword = read_keyword()
    if not keyword:
        print("[skip] 配置里没有 @KEYWORD：先在第 7 步把词定下来，这里不自己估一个")
        return 1
    allowed, why = robots_allows(f"{SUGGEST}?q={urllib.parse.quote(keyword)}")
    if not allowed:
        print(f"[skip] {why}")
        return 1

    suggestions: dict[str, list[str]] = {}
    failed: list[str] = []
    for query in queries_for(keyword):
        try:
            suggestions[query] = suggest(query)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{query}: {type(exc).__name__}")
    if not suggestions:
        print("[fail] 一个查询都没拿到：" + "; ".join(failed[:5]))
        return 1

    merged = merge(bank, suggestions, stamp)
    BANK_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    questions = [item for item in merged["queries"] if item["question"]]
    print(f"[ok]   抓了 {len(suggestions)} 个查询，词库 {len(merged['queries'])} 条（问句 {len(questions)} 条）")
    if failed:
        print(f"[warn] {len(failed)} 个查询没拿到：" + "; ".join(failed[:3]))
    for item in questions[:5]:
        print(f"      问句示例：{item['query']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
