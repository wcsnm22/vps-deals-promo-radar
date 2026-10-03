# ILANG
# TYPE:tool ROLE:rival-teardown PROJECT:vps-deals LANG:zh
# ::RULE{只读公开的 robots.txt / sitemap / 页面本身⇒不登录 不绕反爬 不伪装浏览器 UA}
# ::RULE{robots.txt 读不到或被拒⇒整站跳过并照实记原因 不换招数硬抓}
# ::RULE{只存结构指标⇒标题长度 小标题层级 链接数 语言标注；一个字的正文都不落盘}
# ::BOUNDARY{never:照抄对手页面原文|scope:permanent}
# ::BOUNDARY{never:把 AITDK / sitedata 这类第三方估算当判据|scope:permanent}
"""STEP:1-3：拆对手靠什么词吃饭、页面怎么铺。

只做三件事：
  1. 拉对手公开的 sitemap，按 URL 形状给页面分类（核心工具页/功能页/语言组合页/场景页/模板页/
     比较页/帮助页/博客）；
  2. 每类抽几个页面，量结构指标（标题写法、H1/H2 层级、站内链接数、hreflang 语言数）——
     存指标，不存正文；
  3. 用 Wayback CDX 查每个域名最早的一次快照，作为"这个站什么时候起来的"的参考时间。

用法：
  python rival_teardown.py matrix            # 跑页面矩阵，写 data/rival-matrix.json
  python rival_teardown.py matrix --domain lowendbox.com
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.robotparser
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
UA = "Mozilla/5.0 (compatible; vps-deals-rival-teardown/1.0; +https://vpsdealsradar.com/about)"
TIMEOUT = 25

DOMAINS = ["lowendbox.com", "vpsfilter.com", "www.pcmag.com"]

# 页面分类：按 URL 形状判定，不用正文。顺序就是判断顺序。
CATEGORY_RULES: list[tuple[str, str]] = [
    ("标签归档页", r"^/(?:tag|tags|category|categories|author)/"),
    ("比较与榜单页", r"/(?:compare|comparison|vs|versus|alternative|best|top|review|reviews)[-/]"),
    ("模板页", r"/(?:template|templates|example|examples|sample)[-/]"),
    ("场景页", r"/(?:for|use-case|use-cases|solutions?|scenario)[-/]"),
    ("教程帮助页", r"/(?:help|faq|docs?|support|how-to|guide|tutorial|learn|kb|knowledge)[-/]"),
    ("工具与定价页", r"/(?:features?|pricing|plans?|products?|cart|checkout|tool|tools|calculator|filter|api|status)[-/]"),
    ("博客文章页", r"^/(?:blog|post|posts|article|articles|news|archive)/"),
    ("核心工具页", r"^/?$"),
]

BROWSERISH_RE = re.compile(r"mozilla|chrome|firefox|safari", re.I)


def fetch(url: str, accept: str = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8") -> tuple[int, str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": accept, "Accept-Encoding": "identity", "Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, raw.decode(charset, errors="replace"), ""
    except urllib.error.HTTPError as exc:
        return exc.code, "", f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return 0, "", f"{type(exc).__name__}: {exc}"[:160]


def robots_state(domain: str, path: str = "/") -> tuple[bool, str]:
    """返回 (能不能继续, 说明)。

    自己解析 robots.txt，不用 RobotFileParser：标准库那套对 "User-Agent: * / Allow: /"
    这种最宽松写法给出过拒绝的结论（lowendbox.com 实测），而它其实是允许的。
    只认两条：哪个 UA 段适用于我们、那个段里有没有 Disallow 命中 path。
    """
    status, text, err = fetch(f"https://{domain}/robots.txt", accept="text/plain")
    if status in (401, 403, 429):
        return False, f"robots.txt 返回 {status}：这家明确拒绝自动访问，整站跳过"
    if status != 200:
        return True, f"robots.txt 读不到（{status} {err}）：按允许处理"

    groups: list[tuple[list[str], list[str]]] = []
    agents: list[str] = []
    rules: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if agents and rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif field == "disallow" and agents:
            rules.append(value)
    if agents:
        groups.append((agents, rules))

    ua = UA.lower()
    applicable: list[str] = []
    for names, disallows in groups:
        exact = [name for name in names if name != "*" and name in ua]
        if exact or "*" in names:
            applicable += disallows
    if not applicable:
        return True, "robots.txt 允许抓取（没有命中任何 Disallow）"
    for rule in applicable:
        if rule and path.startswith(rule):
            return False, f"robots.txt Disallow: {rule}"
    return True, "robots.txt 允许抓取"


def sitemaps_from_robots(domain: str) -> list[str]:
    status, text, err = fetch(f"https://{domain}/robots.txt", accept="text/plain")
    if status != 200:
        return []
    return [line.split(":", 1)[1].strip() for line in text.splitlines() if line.lower().startswith("sitemap:")]


def sitemap_urls(entry: str, depth: int = 0, seen: set[str] | None = None) -> list[dict]:
    """递归展开 sitemap_index，返回 [{loc,lastmod}]。只展开，不抓页面。"""
    seen = seen if seen is not None else set()
    if entry in seen or depth > 2:
        return []
    seen.add(entry)
    status, body, err = fetch(entry, accept="application/xml,text/xml,*/*")
    if status != 200:
        print(f"   [warn] sitemap {entry} -> {status} {err}")
        return []
    rows: list[dict] = []
    for block in re.findall(r"<url>(.*?)</url>", body, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block, re.S)
        lastmod = re.search(r"<lastmod>(.*?)</lastmod>", block, re.S)
        if loc:
            rows.append({"loc": loc.group(1).strip(), "lastmod": (lastmod.group(1).strip() if lastmod else "")})
    for child in re.findall(r"<sitemap>(.*?)</sitemap>", body, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", child, re.S)
        if loc:
            rows += sitemap_urls(loc.group(1).strip(), depth + 1, seen)
    return rows


def categorize(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    for label, pattern in CATEGORY_RULES:
        if re.search(pattern, path, re.I):
            return label
    return "其他"


def structure_metrics(domain: str, url: str) -> dict:
    """量结构，不存正文。

    存的是：标题怎么写、小标题几层、正文多长、几张表、几个问答式小标题、
    对外链去了哪些站（只记域名，用来判它有没有做外部渠道）、结构化数据的类型、
    以及页面自己印出来的发布/更新日期。正文一个字都不落盘。
    """
    status, html, err = fetch(url)
    if status != 200:
        return {"url": url, "status": status, "error": err}
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.S | re.I)
    h1 = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.S | re.I)
    h2 = re.findall(r"<h2\b[^>]*>(.*?)</h2>", html, re.S | re.I)
    h3 = re.findall(r"<h3\b[^>]*>(.*?)</h3>", html, re.S | re.I)
    tables = len(re.findall(r"<table\b", html, re.I))
    lists = len(re.findall(r"<ul\b|<ol\b", html, re.I))
    hreflang = sorted(set(re.findall(r'hreflang=["\']([a-zA-Z-]+)["\']', html)))
    internal = set()
    outbound: set[str] = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', html):
        host = urllib.parse.urlparse(href).netloc.lower()
        if not host:
            internal.add(urllib.parse.urlparse(href).path or "/")
            continue
        host = host[4:] if host.startswith("www.") else host
        if host == domain or host.endswith("." + domain.replace("www.", "")):
            internal.add(urllib.parse.urlparse(href).path or "/")
        elif host not in {"fonts.googleapis.com", "fonts.gstatic.com", "googletagmanager.com",
                          "google-analytics.com", "www.googletagmanager.com", "gstatic.com",
                          "ajax.googleapis.com", "cdn.jsdelivr.net", "w.org"}:
            outbound.add(host)
    jsonld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I)
    jsonld_types: set[str] = set()
    for block in jsonld:
        try:
            payload = json.loads(block.strip())
        except ValueError:
            continue
        for item in payload if isinstance(payload, list) else [payload]:
            if not isinstance(item, dict):
                continue
            kind = item.get("@type")
            if isinstance(kind, list):
                jsonld_types.update(str(entry) for entry in kind)
            elif kind:
                jsonld_types.add(str(kind))
            graph = item.get("@graph")
            if isinstance(graph, list):
                for node in graph:
                    if isinstance(node, dict) and node.get("@type"):
                        jsonld_types.add(str(node["@type"]))
    published = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html) or re.search(
        r'property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)', html)
    modified = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html)
    text_of = lambda raw: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()
    body = re.sub(r"<(script|style|nav|footer|header)[\s\S]*?</\1>", " ", html, flags=re.I)
    body_text = text_of(body)
    question_headings = sum(1 for heading in h2 + h3 if text_of(heading).endswith("?"))
    return {
        "url": url,
        "status": status,
        "title_len": len(text_of(title.group(1))) if title else 0,
        "title_has_year": bool(re.search(r"20\d\d", title.group(1))) if title else False,
        "title_has_price": bool(re.search(r"[$€£]\s?\d", title.group(1))) if title else False,
        "title_has_updated_word": bool(re.search(r"update", title.group(1), re.I)) if title else False,
        "description_len": len(text_of(desc.group(1))) if desc else 0,
        "h1": len(h1),
        "h2": len(h2),
        "h3": len(h3),
        "question_headings": question_headings,
        "tables": tables,
        "lists": lists,
        "word_count": len(body_text.split()),
        "download_links": len(re.findall(r'href=["\'][^"\']+\.(?:csv|xlsx?|pdf|ods)["\']', html, re.I)),
        "internal_link_paths": len(internal),
        "outbound_domains": sorted(outbound),
        "jsonld_types": sorted(jsonld_types),
        "hreflang": hreflang,
        "date_published": published.group(1)[:10] if published else "",
        "date_modified": modified.group(1)[:10] if modified else "",
        "first_h2_len": len(text_of(h2[0])) if h2 else 0,
    }


def wayback_first_seen(domain: str, attempts: int = 3) -> dict:
    """这个域名最早的一次快照。

    Wayback 有两个接口，且会 429：先 CDX，被限流就退到 availability API，每次之间等一等。
    拿到的时间只当"这个站大概什么时候起来的"参考，不当判据（课程要求）。
    """
    query = urllib.parse.urlencode(
        {"url": domain, "output": "json", "fl": "timestamp", "filter": "statuscode:200",
         "collapse": "timestamp:6", "limit": "3"}
    )
    for attempt in range(1, attempts + 1):
        status, body, err = fetch(f"https://web.archive.org/cdx/search/cdx?{query}", accept="application/json")
        if status == 200:
            try:
                rows = json.loads(body)
            except ValueError:
                rows = []
            if len(rows) >= 2:
                stamp = rows[1][0]
                return {"first_seen": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}", "source": "cdx",
                        "sampled_snapshots": len(rows) - 1}
        time.sleep(6 * attempt)  # 429 就等久一点，别连着打
    status, body, err = fetch(
        f"https://archive.org/wayback/available?url={urllib.parse.quote(domain)}", accept="application/json"
    )
    if status == 200:
        try:
            payload = json.loads(body)
        except ValueError:
            payload = {}
        closest = (payload.get("archived_snapshots") or {}).get("closest") or {}
        if closest.get("timestamp"):
            stamp = closest["timestamp"]
            return {"first_seen": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}", "source": "availability"}
    return {"first_seen": "", "error": f"Wayback 两个接口都没拿到（最后一次 {status} {err}）"}


def build_matrix(domains: list[str]) -> dict:
    out: dict = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "domains": {}}
    category_examples: dict[str, list[str]] = {}
    url_export: dict[str, list[dict]] = {}
    for domain in domains:
        print(f"== {domain}")
        allowed, why = robots_state(domain)
        record: dict = {"robots": why, "sitemap_entries": [], "url_count": 0, "categories": {}, "samples": []}
        if not allowed:
            record["skipped"] = True
            out["domains"][domain] = record
            print("   skipped:", why)
            continue
        entries = sitemaps_from_robots(domain) or [f"https://{domain}/sitemap.xml"]
        rows: list[dict] = []
        for entry in entries:
            got = sitemap_urls(entry)
            record["sitemap_entries"].append({"entry": entry, "urls": len(got)})
            rows += got
        if not rows:
            record["skipped"] = True
            record["reason"] = "sitemap 抓不到或为空"
            out["domains"][domain] = record
            print("   skipped: sitemap 抓不到")
            continue
        record["url_count"] = len(rows)
        # URL 清单不进矩阵文件（1.2 万条会把 2MB 塞进仓库），单独压缩存到
        # data/rival-urls.json.gz；后面的队列/复盘只读这份缓存，
        # 不再回头对别人的服务器重复拉一遍 sitemap。
        url_export[domain] = [{"loc": row["loc"], "lastmod": row["lastmod"], "category": categorize(row["loc"])} for row in rows]
        categories: dict[str, list[str]] = {}
        for row in rows:
            categories.setdefault(categorize(row["loc"]), []).append(row["loc"])
        record["categories"] = {name: len(urls) for name, urls in sorted(categories.items(), key=lambda kv: -len(kv[1]))}
        record["earliest_lastmod"] = min((row["lastmod"] for row in rows if row["lastmod"]), default="")
        record["latest_lastmod"] = max((row["lastmod"] for row in rows if row["lastmod"]), default="")
        # 每类抽两个样本量结构指标（存指标，不存正文）
        for name, urls in sorted(categories.items(), key=lambda kv: -len(kv[1])):
            for url in urls[:2]:
                metrics = structure_metrics(domain, url)
                metrics["category"] = name
                record["samples"].append(metrics)
                category_examples.setdefault(name, []).append(url)
                time.sleep(1.0)
        record["wayback"] = wayback_first_seen(domain)
        out["domains"][domain] = record
        print(f"   urls={record['url_count']} categories={record['categories']}")
    out["category_examples"] = category_examples
    # 地址清单压缩存盘（见 data/rival-urls.json.gz）
    cache = write_url_cache(url_export)
    print(f"[ok]   url cache -> {cache}")
    return out


def depth_scan(domains: list[str], per_category: int = 6) -> dict:
    """对每个对手的每类页面各抽几页，量"页面怎么铺"：标题写法、小标题层级、正文长度、内链、语言。

    只存指标，不存正文——学的是结构和角度，原文一个字都不落盘。
    """
    matrix_path = DATA / "rival-matrix.json"
    if not matrix_path.exists():
        raise SystemExit("先跑 python rival_teardown.py matrix")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    cached_urls = read_url_cache()
    out: dict = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "domains": {}}
    total = 0
    for domain in domains:
        record = matrix.get("domains", {}).get(domain, {})
        if record.get("skipped"):
            out["domains"][domain] = {"skipped": True, "reason": record.get("reason") or record.get("robots")}
            continue
        examples = {}
        for category, urls in (matrix.get("category_examples") or {}).items():
            examples.setdefault(category, urls)
        # 分类样本从本地缓存补齐（不重抓 sitemap）
        rows = cached_urls.get(domain) or []
        by_cat: dict[str, list[str]] = {}
        for row in rows:
            by_cat.setdefault(categorize(row["loc"]), []).append(row["loc"])
        pages: list[dict] = []
        for category, urls in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
            # 每类里挑"最近更新的两页 + 最早的页面"，能同时看到现在的做法和最早的做法
            dated = [(row["lastmod"], row["loc"]) for row in rows if categorize(row["loc"]) == category]
            dated.sort(reverse=True)
            picks = [loc for _ts, loc in dated[:2]] + [loc for _ts, loc in dated[-1:]]
            seen_picks: set[str] = set()
            for url in picks[:per_category]:
                if url in seen_picks:
                    continue
                seen_picks.add(url)
                metrics = structure_metrics(domain, url)
                metrics["category"] = category
                pages.append(metrics)
                total += 1
                time.sleep(1.0)
        out["domains"][domain] = {"pages": pages, "by_category": {k: len(v) for k, v in by_cat.items()}}
    out["page_count"] = total
    return out


# 产品策略：数它们在 sitemap 的地址里点名了哪些厂商。只数地址，不抓页面。
KNOWN_BRANDS = [
    "digitalocean", "vultr", "linode", "hetzner", "ovhcloud", "ovh", "netcup", "ionos",
    "hostwinds", "buyvm", "racknerd", "hosthatch", "contabo", "namecheap", "cloudways",
    "kamatera", "scaleway", "oracle", "aws", "amazon", "azure", "google-cloud", "gcp",
    "ramnode", "prometeus", "greencloud", "interserver", "milehigh", "virmach", "alphavps",
    "nexusbytes", "hostens", "futureshosting", "dedipath", "quadranet", "serverhub",
    "reprise", "quickweb", "bhost", "kimsufi", "so-you-start", "onehostcloud", "hostinger",
    "godaddy", "bluehost", "liquidweb", "akamai", "fastly", "cloudflare", "backblaze",
    "wasabi", "minio", "onlyoffice", "cpanel", "plesk", "cyberpanel", "virtualizor",
    "proxmox", "openvz", "kvm", "xen", "vmware", "nvidia", "ryzen", "epyc", "intel",
]


def brand_scan() -> dict:
    """产品策略：它们在地址里点名了哪些厂商/技术，以及哪几页是根级常青页。"""
    matrix_path = DATA / "rival-matrix.json"
    if not matrix_path.exists():
        raise SystemExit("先跑 python rival_teardown.py matrix")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    cached_urls = read_url_cache()
    out: dict = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "domains": {}}
    for domain, record in matrix.get("domains", {}).items():
        if record.get("skipped"):
            out["domains"][domain] = {"skipped": True, "reason": record.get("reason") or record.get("robots")}
            continue
        counts: Counter = Counter()
        evergreens: list[str] = []
        for row in cached_urls.get(domain) or []:
            path = urllib.parse.urlparse(row["loc"]).path.lower()
            slug = path.strip("/")
            for brand in KNOWN_BRANDS:
                if re.search(rf"(?:^|[-/]){re.escape(brand)}(?:$|[-/])", path):
                    counts[brand] += 1
            if slug and "/" not in slug and not re.match(r"^(?:privacy|terms|about|contact|advertise)", slug):
                evergreens.append(row["loc"])
        out["domains"][domain] = {
            "brand_url_counts": dict(counts.most_common(30)),
            "brands_mentioned": len(counts),
            "root_level_pages": sorted(evergreens),
            "root_level_count": len(evergreens),
        }
    return out


def ngrams(text: str, size: int = 5) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i:i + size]) for i in range(max(len(words) - size + 1, 0))}


def overlap_check(local_sample: int = 12, rival_sample: int = 6) -> dict:
    """自查：我们站上的字，和对手页面有没有整句重合。

    对手正文只进内存用来算 5-gram 重合率，**一个字的原文都不落盘**。
    这就是命令里 NON_GOALS "不许照抄对手原文" 的可复核证据。

    `404.html` 这类模板页只有导航和页脚，不算内容页，单独记一份，
    否则结论会被"页脚长得像"污染。
    """
    data = json.loads((DATA / "rival-depth.json").read_text(encoding="utf-8"))
    boilerplate = {"404"}
    ours: list[dict] = []
    for path in sorted((ROOT / "site").rglob("*.html"))[:400]:
        text = path.read_text(encoding="utf-8", errors="replace")
        body = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", text, flags=re.I)
        rel = "/" + path.relative_to(ROOT / "site").as_posix()
        ours.append({
            "page": rel,
            "is_boilerplate": path.stem in boilerplate,
            "grams": ngrams(re.sub(r"<[^>]+>", " ", body)),
        })
    results: list[dict] = []
    for domain, record in data.get("domains", {}).items():
        if record.get("skipped"):
            continue
        pages = [row for row in record.get("pages", []) if row.get("status") == 200][:rival_sample]
        for row in pages:
            status, html, _err = fetch(row["url"])
            if status != 200:
                continue
            body = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html, flags=re.I)
            rival_grams = ngrams(re.sub(r"<[^>]+>", " ", body))
            worst_any = {"our_page": "", "shared": 0, "ratio": 0.0}
            worst_content = {"our_page": "", "shared": 0, "ratio": 0.0}
            for page in ours:
                shared = len(page["grams"] & rival_grams)
                ratio = shared / max(len(page["grams"]), 1)
                if ratio > worst_any["ratio"]:
                    worst_any = {"our_page": page["page"], "shared": shared, "ratio": round(ratio * 100, 4)}
                if not page["is_boilerplate"] and ratio > worst_content["ratio"]:
                    worst_content = {"our_page": page["page"], "shared": shared, "ratio": round(ratio * 100, 4)}
            results.append({"rival_url": row["url"], "rival_grams": len(rival_grams),
                            "worst_any": worst_any, "worst_content": worst_content})
            time.sleep(1.0)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "把双方页面去标签后切成 5-gram，算我们每页与对手每页的重合率；对手原文不落盘",
        "our_pages_checked": len(ours),
        "our_content_pages_checked": sum(1 for page in ours if not page["is_boilerplate"]),
        "rival_pages_checked": len(results),
        "worst_any": max(results, key=lambda item: item["worst_any"]["ratio"], default={"worst_any": {"ratio": 0.0}}),
        "worst_content": max(results, key=lambda item: item["worst_content"]["ratio"], default={"worst_content": {"ratio": 0.0}}),
        "results": results,
    }


def write_url_cache(domains_urls: dict[str, list[dict]]) -> Path:
    """URL 清单单独压缩存：全量清单有 1.2 万条、近 2MB，直接进仓库太占地方。"""
    target = DATA / "rival-urls.json.gz"
    payload = json.dumps(domains_urls, ensure_ascii=False).encode("utf-8")
    with gzip.open(target, "wb") as handle:
        handle.write(payload)
    return target


def read_url_cache() -> dict[str, list[dict]]:
    """读 URL 清单缓存（rival_queue.py / brand_scan 用），只读本地文件，不重抓别人的 sitemap。"""
    target = DATA / "rival-urls.json.gz"
    if not target.exists():
        raise SystemExit(f"缺 {target.name}：先跑 python rival_teardown.py matrix")
    with gzip.open(target, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def main() -> int:
    what = sys.argv[1] if len(sys.argv) > 1 else "matrix"
    domains = DOMAINS
    if "--domain" in sys.argv:
        domains = [sys.argv[sys.argv.index("--domain") + 1]]
    DATA.mkdir(exist_ok=True)
    if what == "matrix":
        payload = build_matrix(domains)
        target = DATA / "rival-matrix.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok]   wrote {target}")
        return 0
    if what == "depth":
        payload = depth_scan(domains)
        target = DATA / "rival-depth.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ok]   wrote {target}（{payload['page_count']} 页结构指标）")
        return 0
    if what == "brands":
        payload = brand_scan()
        target = DATA / "rival-brands.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for domain, record in payload["domains"].items():
            if record.get("skipped"):
                print(f"       {domain}: 跳过")
                continue
            print(f"       {domain}: 点名厂商 {record['brands_mentioned']} 个，根级页 {record['root_level_count']} 个")
            print(f"          top: {list(record['brand_url_counts'].items())[:8]}")
        print(f"[ok]   wrote {target}")
        return 0
    if what == "overlap":
        payload = overlap_check()
        target = DATA / "rival-overlap.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        worst = payload["worst_content"]["worst_content"]
        print(f"       比对 {payload['rival_pages_checked']} 个对手页面 × 我们 {payload['our_content_pages_checked']} 个内容页")
        print(f"       内容页最高重合：{worst.get('ratio', 0)}%（{worst.get('shared', 0)} 个 5-gram，我们的 {worst.get('our_page', '')}）")
        print(f"[ok]   wrote {target}")
        return 0
    print("用法：python rival_teardown.py matrix|depth|brands|overlap [--domain x.com]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
