# ILANG
# TYPE:tool ROLE:rival-queue PROJECT:vps-deals LANG:zh
# ::RULE{词的"饭碗"口径只来自官方或公开接口⇒谷歌搜索控制台的自家数据、公开搜索补全；不买 Ahrefs/Semrush}
# ::RULE{排序不用第三方估算的搜索量⇒用"补全里排第几"+"几家对手在做"+"我们有没有"三个可复核的信号}
# ::RULE{每一条选题都要能指到对手的具体 URL⇒指不到的不进队列}
# ::BOUNDARY{never:把 AITDK / sitedata 这类估算当判据|scope:permanent}
# ::BOUNDARY{never:照抄对手页面原文|scope:permanent}
"""STEP:2 / STEP:8：把"对手靠什么词吃饭"变成"我明天写哪一篇"。

三件事：
  1. 从对手 sitemap 的 URL slug 里抽出词组（他们自己写在地址里的词，公开可查）；
  2. 从公开搜索补全接口拿真人查询原话作为需求信号（不买 Ahrefs/Semrush，不碰第三方搜索量估算）；
  3. 和我们自己已发布的页面比对，找出"对手有、我们没有"的那一类，排成选题队列。

用法：python rival_queue.py            # 刷新补全信号并重算队列
      python rival_queue.py --offline  # 不联网，用 data/rival-keyword-signals.json 里的旧信号重算
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from rival_teardown import read_url_cache

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE_DIR = ROOT / "site"
UA = "Mozilla/5.0 (compatible; vps-deals-keyword-queue/1.0; +https://vpsdealsradar.com/about)"
SUGGEST = "https://suggestqueries.google.com/complete/search"

# 只在这个生意范围内的词算"饭碗"。不在表里的 slug 段（作者名、页码、无关话题）不算。
NICHE_WORDS = {
    "vps", "server", "servers", "hosting", "host", "cloud", "dedicated", "kvm",
    "cheap", "budget", "windows", "linux", "storage", "bandwidth", "ipv4", "ipv6",
    "price", "pricing", "cost", "deal", "deals", "offer", "offers", "coupon", "code",
    "provider", "providers", "compare", "comparison", "best", "review", "reviews",
    "unmetered", "backup", "panel", "cpanel", "plesk", "ubuntu", "debian",
    "docker", "minecraft", "game", "gaming", "seedbox", "vpn", "proxy", "reseller",
    "ram", "memory", "cpu", "core", "cores", "disk", "ssd", "nvme", "location",
    "locations", "usa", "europe", "asia", "germany", "netherlands", "uk", "japan",
    "free", "trial", "setup", "lifetime", "monthly", "yearly", "annual",
}

# 站点结构用的 slug 段，不是选题。
NOISE_SEGMENTS = {
    "blog", "post", "posts", "article", "articles", "news", "page", "pages", "author",
    "category", "categories", "tag", "tags", "feed", "wp-admin", "wp-content",
    "privacy", "terms", "contact", "about", "legal", "sitemap", "readme", "refer",
    "index", "home", "search", "comment", "comments", "amp", "en", "fr", "de", "es",
}

# 这些词只会修饰别人，不会单独当查询：词组以它们结尾就不当作一条查询。
TAIL_MODIFIERS = {"cheap", "best", "top", "budget", "free", "unmetered", "affordable", "lowcost"}

SEED_QUERIES = [
    "cheap vps", "cheap vps hosting", "cheap windows vps", "cheap linux vps",
    "best cheap vps", "vps under $5", "vps with ipv4", "unmetered vps",
    "vps storage", "vps for beginners", "vps comparison", "vps coupon",
    "cheap dedicated server", "vps vs shared hosting", "how much does a vps cost",
]


def suggest(query: str) -> list[str]:
    params = urllib.parse.urlencode({"client": "firefox", "hl": "en", "gl": "us", "q": query})
    request = urllib.request.Request(f"{SUGGEST}?{params}", headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    return [item for item in payload[1] if isinstance(item, str)]


def refresh_signals() -> dict:
    """公开补全接口：记录每个查询在哪个种子下排第几。这是需求信号，不是搜索量。"""
    signals: dict[str, dict] = {}
    failures: list[str] = []
    for seed in SEED_QUERIES:
        try:
            for rank, text in enumerate(suggest(seed), start=1):
                key = re.sub(r"\s+", " ", text.strip().lower())
                if not key:
                    continue
                entry = signals.setdefault(key, {"query": key, "best_rank": rank, "seeds": []})
                entry["best_rank"] = min(entry["best_rank"], rank)
                if seed not in entry["seeds"]:
                    entry["seeds"].append(seed)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{seed}: {type(exc).__name__}")
        time.sleep(0.8)
    return {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "公开搜索补全接口（拿到的是真人查询原话与名次，不是搜索量估算）",
        "seeds": SEED_QUERIES,
        "signals": sorted(signals.values(), key=lambda row: row["best_rank"]),
        "failures": failures,
    }


def slug_phrases(url: str) -> list[str]:
    """把一个 URL 拆成词组候选。

    规则：只在**连续**的词窗口上取词组，且窗口里每个词都必须是这个生意的词
    （`hosting` `vps` `cheap` `windows` …），带数字的窗口直接跳过。
    这样 `cheap-vps-llc-8-quarter-512mb…` 只会产出 `cheap vps`，
    不会把被数字隔开的两个词拼成 `cheap vp` 这种不存在的查询。
    """
    path = urllib.parse.urlparse(url).path.strip("/").lower()
    phrases: list[str] = []
    for segment in path.split("/"):
        if not segment or segment in NOISE_SEGMENTS or segment.isdigit():
            continue
        tokens = [token for token in re.split(r"[-_+.]", segment) if token]
        if not tokens:
            continue
        pool = [token for token in tokens if token.isdigit() or token in NICHE_WORDS]
        for size in (3, 2):
            for start in range(0, len(pool) - size + 1):
                window = pool[start:start + size]
                if any(token.isdigit() for token in window):
                    continue
                if not any(token in NICHE_WORDS for token in window):
                    continue
                phrases.append(" ".join(window))
    return phrases


def rival_phrases() -> dict[str, dict]:
    """对手在用的词组——用 rival_teardown.py 存下来的 URL 缓存，不回头重抓别人的 sitemap。"""
    matrix_path = DATA / "rival-matrix.json"
    if not matrix_path.exists():
        raise SystemExit("先跑 python rival_teardown.py matrix")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    cached = read_url_cache()
    phrases: dict[str, dict] = {}
    for domain, record in matrix.get("domains", {}).items():
        if record.get("skipped"):
            continue
        rows = cached.get(domain) or []
        if not rows:
            raise SystemExit(f"{domain} 的 URL 缓存是空的：先重跑 python rival_teardown.py matrix")
        for row in rows:
            for phrase in slug_phrases(row["loc"]):
                entry = phrases.setdefault(phrase, {"phrase": phrase, "domains": {}, "example_url": row["loc"]})
                entry["domains"][domain] = entry["domains"].get(domain, 0) + 1
    return drop_fragments(phrases)


def drop_fragments(phrases: dict[str, dict]) -> dict[str, dict]:
    """去掉"某条词组的碎片"。两条规则，都只为了不把 slug 的切片当成查询：

    1. 结尾是修饰词的（`best cheap`、`storage cheap`）：没人这么搜；
    2. 一条词的对手集合与地址数都不超过另一条、且字面上被它包含（`best cheap vps` ⊃ `cheap vps`）。
    """
    keep: dict[str, dict] = {}
    items = sorted(phrases.items(), key=lambda kv: -len(kv[0]))
    for phrase, record in items:
        words = phrase.split()
        if len(words) < 2 or words[-1] in TAIL_MODIFIERS or words[0] in TAIL_MODIFIERS and len(words) == 1:
            continue
        redundant = False
        for longer, longer_record in keep.items():
            if phrase not in longer:
                continue
            dominated = all(count <= longer_record["domains"].get(domain, 0) for domain, count in record["domains"].items())
            if dominated and sum(record["domains"].values()) <= sum(longer_record["domains"].values()):
                redundant = True
                break
        if not redundant:
            keep[phrase] = record
    return keep


def our_coverage() -> dict[str, int]:
    """我们自己的页面已经覆盖了哪些词（标题 + URL + 正文里出现就算）。"""
    coverage: dict[str, int] = {}
    for path in sorted(SITE_DIR.rglob("*.html")):
        text = path.read_text(encoding="utf-8").lower()
        for word in set(re.findall(r"[a-z]{3,}", text)):
            coverage[word] = coverage.get(word, 0) + 1
    return coverage


def phrase_covered(phrase: str, coverage: dict[str, int]) -> int:
    """整条词组必须每个词都在我们站上出现过，才算"我们写过这个话题"。"""
    words = [word for word in phrase.split() if word not in {"the", "a", "for", "and", "with", "of", "to"}]
    if not words:
        return 0
    hits = [coverage.get(word, 0) for word in words]
    return min(hits)


def signal_for(phrase: str, signal_index: dict[str, dict]) -> tuple[int | None, str, str]:
    """给一个词组找需求信号：先找完全一致的查询，再找包含这条词组的查询。"""
    if phrase in signal_index:
        row = signal_index[phrase]
        return row["best_rank"], row["query"], "完全一致"
    best: tuple[int, str] | None = None
    for query, row in signal_index.items():
        if phrase in query:
            if best is None or row["best_rank"] < best[0]:
                best = (row["best_rank"], query)
    if best:
        return best[0], best[1], "包含该词组"
    return None, "", ""


def load_gsc_queries(path: Path) -> dict:
    """读用户从 Search Console 导出的查询表（CSV），拿到真流量词。

    只认"我们自己站的后台导出的数字"这一种来源：不估算、不换算、
    读不到就照实说没有（命令里 @GSC 是唯一数据源）。
    导出方式：GSC → 效果 → 查询 → 右上角导出 CSV，丢到 data/gsc-queries.csv。
    """
    if not path.exists():
        return {"available": False, "reason": f"没有 {path.name}（需要从 Search Console 导出）", "rows": [], "with_impressions": 0}
    import csv

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    header_at = -1
    for index, line in enumerate(lines[:12]):
        lowered = line.lower()
        if "query" in lowered or "queries" in lowered or "查询" in lowered:
            header_at = index
            break
    if header_at < 0:
        return {"available": False, "reason": f"{path.name} 里找不到表头（要有 query 那一列）", "rows": [], "with_impressions": 0}
    reader = csv.DictReader(lines[header_at:])
    rows: list[dict] = []

    def number(value: str, percent: bool = False) -> float:
        cleaned = (value or "").replace(",", "").replace("%", "").strip()
        try:
            got = float(cleaned)
        except ValueError:
            return 0.0
        return got / 100 if percent else got

    for raw in reader:
        item = {(key or "").strip().lower(): (value or "") for key, value in raw.items()}
        query = (item.get("query") or item.get("top queries") or item.get("查询") or item.get("查询词") or "").strip()
        if not query:
            continue
        rows.append(
            {
                "query": query,
                "clicks": number(item.get("clicks") or item.get("点击次数") or item.get("点击")),
                "impressions": number(item.get("impressions") or item.get("展示次数") or item.get("展示")),
                "ctr": number(item.get("ctr") or item.get("点击率"), percent=True),
                "position": number(item.get("position") or item.get("平均排名")),
            }
        )
    rows.sort(key=lambda row: (-row["impressions"], -row["clicks"], row["query"]))
    return {
        "available": True,
        "source": f"Search Console 导出（{path.name}）",
        "rows": rows,
        "with_impressions": sum(1 for row in rows if row["impressions"] > 0),
    }


def gsc_for(phrase: str, gsc_rows: list[dict]) -> dict | None:
    """给词组找真实流量：先找完全一致的查询，再找包含它的查询（按展示次数最高的那条）。"""
    hits = [row for row in gsc_rows if row["query"] == phrase] or [row for row in gsc_rows if phrase in row["query"]]
    if not hits:
        return None
    hits.sort(key=lambda row: (-row["impressions"], -row["clicks"]))
    top = hits[0]
    return {
        "query": top["query"],
        "impressions": round(top["impressions"]),
        "clicks": round(top["clicks"]),
        "position": round(top["position"], 1),
        "matched_queries": len(hits),
    }


def build_queue(offline: bool = False, gsc_path: Path | None = None) -> dict:
    signals_path = DATA / "rival-keyword-signals.json"
    if offline and signals_path.exists():
        signals = json.loads(signals_path.read_text(encoding="utf-8"))
    else:
        signals = refresh_signals()
        signals_path.write_text(json.dumps(signals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"       补全信号 {len(signals['signals'])} 条（{signals['fetched_at']}），失败 {len(signals['failures'])} 个种子")

    phrases = rival_phrases()
    coverage = our_coverage()
    signal_index = {row["query"]: row for row in signals["signals"]}
    gsc = load_gsc_queries(gsc_path or (DATA / "gsc-queries.csv"))
    gsc_rows = gsc["rows"] if gsc.get("available") else []

    rows: list[dict] = []
    for phrase, record in phrases.items():
        rank, query, how = signal_for(phrase, signal_index)
        pages = phrase_covered(phrase, coverage)
        rows.append(
            {
                "phrase": phrase,
                "words": len(phrase.split()),
                "rival_domains": len(record["domains"]),
                "rival_urls": sum(record["domains"].values()),
                "example_url": record["example_url"],
                "signal_rank": rank,
                "signal_query": query,
                "signal_match": how,
                "we_have_pages": pages,
                "gsc": gsc_for(phrase, gsc_rows),
            }
        )

    # 宁缺毋滥：只留有需求信号、或至少两家对手都在做的词组。
    ranked = [row for row in rows if row["signal_rank"] is not None or row["rival_domains"] >= 2]
    # 有真流量数据时，第一判据换成"我们自己后台看到的展示次数"——这是唯一真实的"带流量的词"。
    if gsc_rows:
        ranked = [row for row in ranked if row["gsc"] or row["we_have_pages"] == 0]
        ranked.sort(
            key=lambda row: (
                0 if row["we_have_pages"] == 0 else 1,
                -(row["gsc"]["impressions"] if row["gsc"] else -1),
                -row["rival_domains"],
                row["phrase"],
            )
        )
    else:
        ranked.sort(
            key=lambda row: (
                0 if row["we_have_pages"] == 0 else 1,          # 我们先没写过的优先
                row["signal_rank"] if row["signal_rank"] is not None else 999,  # 补全里名次靠前的优先
                -row["rival_domains"],                          # 越多对手在做越是硬需求
                -row["rival_urls"],
                row["phrase"],
            )
        )
    for index, row in enumerate(ranked, start=1):
        row["order"] = index
        row["action"] = "补这一篇" if row["we_have_pages"] == 0 else "已有，检查够不够深"
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "how_sorted": (
            "先看我们写没写过，再按 Search Console 导出的展示次数排（真实流量），再看几家对手在做"
            if gsc_rows
            else "先看我们写没写过，再看公开补全里的名次，再看几家对手在做；没有任何第三方搜索量估算"
        ),
        "signals_fetched_at": signals["fetched_at"],
        "signals_source": signals["source"],
        "traffic_source": gsc.get("source") if gsc_rows else gsc.get("reason"),
        "traffic_rows": len(gsc_rows),
        "top_gsc_queries": gsc_rows[:40],
        "total_phrases_seen": len(rows),
        "queue": ranked,
    }


def main() -> int:
    offline = "--offline" in sys.argv
    gsc_path = None
    if "--gsc" in sys.argv:
        gsc_path = Path(sys.argv[sys.argv.index("--gsc") + 1]).resolve()
    payload = build_queue(offline=offline, gsc_path=gsc_path)
    target = DATA / "rival-topic-queue.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = [row for row in payload["queue"] if row["we_have_pages"] == 0]
    print(f"[ok]   wrote {target}")
    print(f"       流量数据：{payload['traffic_source']}（{payload['traffic_rows']} 条查询）")
    print(f"       抽到词组 {payload['total_phrases_seen']} 条，入队 {len(payload['queue'])} 条，其中我们没有的 {len(missing)} 条")
    for row in payload["queue"][:15]:
        signal = f"补全第 {row['signal_rank']} 位（{row['signal_query']}）" if row["signal_rank"] else "补全里没出现"
        traffic = f"GSC 展示 {row['gsc']['impressions']}" if row["gsc"] else "无后台流量数据"
        print(
            f"      {row['order']:3d}. {row['phrase']:<34} 对手 {row['rival_domains']} 家 "
            f"| {signal} | {traffic} | 我们 {row['we_have_pages']} 页"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
