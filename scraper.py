# ILANG
# TYPE:module ROLE:scraper PROJECT:vps-deals
# ::RULE{配置来自 .ilang/site.ilang⇒本文件不许硬编码厂商清单或词表 改了配置行为就要变}
# ::RULE{抓不到 price⇒这条不写 price 字段 不许拿估的填}
# ::RULE{找不到可信产品名⇒这条不收录 宁缺毋滥}
# ::RULE{抓取前读 robots.txt⇒Disallow 的路径跳过并记录}
# ::RULE{只抓公开页面⇒不登录 不绕反爬 不伪装登录态}
# ::BOUNDARY{never:编优惠 编价格 编佣金|scope:file}
"""抓各家主机商的公开优惠页 -> data/offers.json

零依赖：只用 Python 标准库。运行时无推理、无密钥、确定性。
用法：python scraper.py [配置文件路径]
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / ".ilang" / "site.ilang"
OUT_PATH = ROOT / "data" / "offers.json"
USER_AGENT = "vps-deals-radar/1.0 (+static deal aggregator; contact via repo issues)"
FETCH_TIMEOUT = 25
MAX_OFFERS_PER_PROVIDER = 40

# ---------------------------------------------------------------- I-Lang 配置

MODULE_LINE = re.compile(r"^::([A-Z_]+)\{(.*)\}$")


def _words(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        out.extend(w for w in re.split(r"[\s,]+", line.strip().lower()) if w)
    return out


def parse_ilang(text: str) -> dict:
    """把 site.ilang 解析成 dict。这是配置的唯一入口，代码里不许另写一份词表。"""
    state: dict[str, str] = {}
    modules: dict[str, list[str]] = {}
    rules: list[str] = []
    boundaries: list[str] = []
    current: str | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "ILANG":
            continue
        if line.upper().startswith("TYPE:"):
            continue
        match = MODULE_LINE.match(line)
        if match:
            kind, body = match.group(1), match.group(2)
            if kind == "STATE":
                for part in [p.strip() for p in body.split(",")][1:]:
                    if ":" in part:
                        key, value = part.split(":", 1)
                        state[key.strip()] = value.strip()
            elif kind == "MODULE":
                current = body.split("|")[0].strip()
                modules.setdefault(current, [])
            elif kind == "RULE":
                rules.append(body.strip())
                current = None
            elif kind == "BOUNDARY":
                boundaries.append(body.strip())
                current = None
            else:
                current = None
            continue
        if current is not None:
            modules[current].append(line)

    providers = []
    for line in modules.get("PROVIDERS", []):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3 or not parts[0] or parts[0].startswith("#"):
            continue
        entry = {
            "name": parts[0],
            "homepage": parts[1],
            "deals_url": parts[2],
            "affiliate_url": parts[3] if len(parts) > 3 else "",
            "kind": "page",
            "currency": state.get("currency", "USD"),
        }
        for option in parts[4:]:
            if "=" in option:
                key, value = option.split("=", 1)
                entry[key.strip()] = value.strip()
        providers.append(entry)

    return {
        "site": state,
        "providers": providers,
        "fields": (modules.get("FIELDS") or [[]])[0],
        "title_hints": _words(modules.get("TITLEHINT", [])),
        "spec_words": _words(modules.get("SPECWORD", [])),
        "filler": set(_words(modules.get("FILLER", []))),
        "skip_price": _words(modules.get("SKIPPRICE", [])),
        "exclude": _words(modules.get("EXCLUDE", [])),
        "rules": rules,
        "boundaries": boundaries,
    }


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict:
    config = parse_ilang(Path(path).read_text(encoding="utf-8"))
    if not config["providers"]:
        raise SystemExit("site.ilang lists no provider; stopping instead of guessing")
    return config


# ------------------------------------------------------------------ 抓取层

_robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def robots_allows(url: str) -> tuple[bool, str]:
    parsed = urllib.parse.urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _robots_cache:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")
        try:
            parser.read()
        except Exception:  # noqa: BLE001
            parser = None
        _robots_cache[origin] = parser
    parser = _robots_cache[origin]
    if parser is None:
        return True, "robots.txt could not be read; treated as allowed"
    try:
        allowed = parser.can_fetch(USER_AGENT, url)
    except Exception:  # noqa: BLE001
        return True, "robots.txt could not be parsed; treated as allowed"
    return allowed, "" if allowed else "skipped: robots.txt disallows this path"


def fetch(url: str) -> tuple[int, str, str]:
    """返回 (http_status, text, error)。只请求一次，不对别人服务器反复重试。"""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return response.status, raw.decode(charset, errors="replace"), ""
    except urllib.error.HTTPError as exc:
        return exc.code, "", f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return 0, "", f"{type(exc).__name__}: {exc}"[:120]


# ------------------------------------------------------------------ 解析层

BLOCK_TAGS = (
    "div|p|li|ul|ol|tr|td|th|table|section|article|aside|header|footer|main|nav|"
    "h1|h2|h3|h4|h5|h6|br|hr|form|button|label|dt|dd|figure|figcaption|option|"
    "script|style|noscript|template|select|textarea|iframe"
)
BLOCK_RE = re.compile(rf"</?(?:{BLOCK_TAGS})\b[^>]*>", re.I)
TAG_RE = re.compile(r"<[^>]+>")
ANCHOR_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
PRICE_RE = re.compile(r"(?P<cur>US\$|\$|€|EUR|USD|£|GBP)\s?(?P<amt>\d{1,4}(?:[.,]\d{1,2})?)", re.I)
DATE_RE = re.compile(
    r"(?:valid\s+(?:until|through)|until|ends?|expires?|expiry)\s*:?\s*"
    r"([A-Z][a-z]{2,8}\.?\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})",
    re.I,
)
CURRENCY_SYMBOLS = {
    "$": "USD",
    "us$": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "usd": "USD",
}


def rendered_lines(html: str) -> list[str]:
    text = BLOCK_RE.sub("\n", html)
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    lines = []
    for raw in text.split("\n"):
        line = " ".join(raw.split())
        if line:
            lines.append(line)
    return lines


def anchors(html: str, base_url: str) -> list[tuple[str, str]]:
    out = []
    for href, label in ANCHOR_RE.findall(html):
        clean = " ".join(TAG_RE.sub(" ", unescape(label)).split())
        if clean:
            out.append((clean.lower(), urllib.parse.urljoin(base_url, href)))
    return out


def normalize_amount(raw: str, max_price: float) -> float | None:
    value = raw.replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(",", "")
    elif "," in value:
        head, _, tail = value.partition(",")
        value = f"{head}.{tail}" if len(tail) <= 2 else value.replace(",", "")
    try:
        amount = float(value)
    except ValueError:
        return None
    return amount if 0 < amount <= max_price else None


def strip_filler(text: str, filler: set[str]) -> str:
    """把首尾的填充词去掉，例如 'Starting at' / 'From' / 'Details >'。"""
    title = " ".join(text.split())
    changed = True
    while changed and title:
        changed = False
        for phrase in sorted(filler, key=len, reverse=True):
            if not phrase:
                continue
            lowered = title.lower()
            if lowered == phrase:
                return ""
            if lowered.startswith(phrase):
                title = title[len(phrase) :].lstrip(" -–—|/·:>")
                changed = True
            if title.lower().endswith(phrase):
                title = title[: -len(phrase)].rstrip(" -–—|/·:>")
                changed = True
    return " ".join(title.split()).strip(" -–—|/·:>")


def title_score(line: str, config: dict) -> int:
    """给候选标题打分。分数低说明这行不是产品名，宁可不收也不冒充。"""
    if not line:
        return -99
    lowered = line.lower()
    if PRICE_RE.search(line):
        return -99
    if lowered in config["filler"]:
        return -99
    if sum(ch.isalpha() for ch in line) < 2:
        return -99
    tokens = re.findall(r"[a-z0-9]+", lowered)
    if not tokens or len(tokens) > 6:  # 超过 6 个词基本是句子/说明文字，不是产品名
        return -99
    if len(tokens) < 2 and not re.search(r"\d", lowered):
        return -99  # 单个词（From / Unmetered / Details）不是产品名
    score = 0
    if any(hint in lowered for hint in config["title_hints"]):
        score += 3
    if any(word in tokens for word in config["spec_words"]) or re.search(r"\d\s?(gb|tb|mb)\b", lowered):
        score -= 3
    if re.search(r"\d", lowered):
        score += 2
    if 3 <= len(line) <= 60:
        score += 1
    if len(tokens) <= 5:
        score += 1
    if any(word in lowered for word in config["exclude"]):
        return -99
    return score


def clean_title(text: str) -> str:
    title = re.sub(r"[\s\-\u2013\u2014|/·:>,]+$", "", text.strip())
    return " ".join(title.split())[:80]


def match_anchor(title: str, anchor_list: list[tuple[str, str]], fallback: str) -> str:
    tokens = {t for t in re.findall(r"[a-z0-9]{3,}", title.lower())}
    if not tokens:
        return fallback
    best, best_score = fallback, 0.0
    for label, href in anchor_list:
        label_tokens = {t for t in re.findall(r"[a-z0-9]{3,}", label)}
        if not label_tokens:
            continue
        score = len(tokens & label_tokens) / len(tokens)
        if score > best_score:
            best, best_score = href, score
    return best if best_score >= 0.6 else fallback


def extract_page_offers(html: str, source_url: str, provider: dict, config: dict) -> list[dict]:
    lines = rendered_lines(html)
    anchor_list = anchors(html, source_url)
    lookback = int(config["site"].get("lookback_lines", 12))
    max_price = float(config["site"].get("max_price", 5000))
    found: dict[tuple, dict] = {}
    skipped_no_title = 0

    for index, line in enumerate(lines):
        if any(word in line.lower() for word in config["skip_price"]):
            continue  # 同行出现 per hour / setup fee 之类，说明这个价格不是套餐月费
        for match in PRICE_RE.finditer(line):
            amount = normalize_amount(match.group("amt"), max_price)
            if amount is None:
                continue

            # 候选标题：本行价格前面的文字 + 往上若干行里最像产品名的那一行
            candidates: list[tuple[int, str]] = []
            prefix = strip_filler(clean_title(line[: match.start()]), config["filler"])
            candidates.append((title_score(prefix, config), prefix))
            for back in range(1, lookback + 1):
                if index - back < 0:
                    break
                raw = strip_filler(clean_title(lines[index - back]), config["filler"])
                score = title_score(raw, config)
                if score > 0:
                    candidates.append((score - back * 0.1, raw))
            candidates.sort(key=lambda item: item[0], reverse=True)
            best_score, title = candidates[0] if candidates else (-99, "")

            if best_score < 2 or not title:
                skipped_no_title += 1
                continue

            currency = CURRENCY_SYMBOLS.get(match.group("cur").lower(), provider.get("currency", "USD"))
            key = (title.lower(), amount, currency)
            if key in found:
                continue
            record = {
                "provider": provider["name"],
                "title": title,
                "price": amount,
                "currency": currency,
                "offer_url": match_anchor(title, anchor_list, source_url),
                "source_url": source_url,
            }
            date_match = DATE_RE.search(" ".join(lines[max(0, index - 1) : index + 2]))
            if date_match:
                record["valid_until"] = date_match.group(1)
            found[key] = record
            if len(found) >= MAX_OFFERS_PER_PROVIDER:
                break
    provider["_skipped_no_title"] = skipped_no_title
    return list(found.values())


def extract_feed_offers(xml: str, source_url: str, provider: dict, config: dict) -> list[dict]:
    out: dict[tuple, dict] = {}
    max_price = float(config["site"].get("max_price", 5000))
    for item in re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", xml, re.I | re.S):
        title_match = re.search(r"<title[^>]*>(.*?)</title>", item, re.I | re.S)
        link_match = re.search(r"<link[^>]*href=[\"']([^\"']+)[\"']", item, re.I) or re.search(
            r"<link[^>]*>(.*?)</link>", item, re.I | re.S
        )
        if not title_match or not link_match:
            continue
        title = strip_filler(clean_title(unescape(TAG_RE.sub("", title_match.group(1)))), config["filler"])
        if title_score(title, config) < 2:
            continue
        record = {
            "provider": provider["name"],
            "title": title,
            "offer_url": urllib.parse.urljoin(source_url, link_match.group(1).strip()),
            "source_url": source_url,
        }
        price_match = PRICE_RE.search(title)
        if price_match:
            amount = normalize_amount(price_match.group("amt"), max_price)
            if amount is not None:
                record["price"] = amount
                record["currency"] = CURRENCY_SYMBOLS.get(price_match.group("cur").lower(), provider.get("currency", "USD"))
        date_match = DATE_RE.search(item)
        if date_match:
            record["valid_until"] = date_match.group(1)
        out[(record["title"].lower(), record.get("price"))] = record
        if len(out) >= MAX_OFFERS_PER_PROVIDER:
            break
    return list(out.values())


def extract_sitemap_offers(xml: str, source_url: str, provider: dict, config: dict) -> list[dict]:
    out = []
    for loc, lastmod in re.findall(
        r"<url>.*?<loc>(.*?)</loc>(?:.*?<lastmod>(.*?)</lastmod>)?.*?</url>", xml, re.I | re.S
    ):
        url = loc.strip()
        slug = urllib.parse.urlsplit(url).path.strip("/").split("/")[-1]
        title = clean_title(slug.replace("-", " ").replace("_", " "))
        if title_score(title, config) < 2:
            continue
        record = {"provider": provider["name"], "title": title, "offer_url": url, "source_url": source_url}
        if lastmod:
            record["valid_until"] = lastmod.strip()
        out.append(record)
        if len(out) >= MAX_OFFERS_PER_PROVIDER:
            break
    return out


# ------------------------------------------------------------------ 主流程

def main() -> int:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG
    config = load_config(config_path)
    site = config["site"]
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    offers: list[dict] = []
    report: list[dict] = []

    for provider in config["providers"]:
        url = provider["deals_url"]
        allowed, why = robots_allows(url)
        row = {
            "name": provider["name"],
            "homepage": provider["homepage"],
            "deals_url": url,
            "affiliate_url": provider.get("affiliate_url", ""),
            "kind": provider.get("kind", "page"),
            "currency": provider.get("currency", site.get("currency", "USD")),
            "http": 0,
            "offers": 0,
            "priced": 0,
            "note": "",
        }
        if not allowed:
            row["note"] = why
            report.append(row)
            print(f"[skip] {provider['name']}: {why}")
            continue

        status, body, error = fetch(url)
        row["http"] = status
        if error or not body:
            row["note"] = error or "empty response"
            report.append(row)
            print(f"[fail] {provider['name']}: {row['note']}")
            continue

        kind = row["kind"]
        if kind == "feed":
            found = extract_feed_offers(body, url, provider, config)
        elif kind == "sitemap":
            found = extract_sitemap_offers(body, url, provider, config)
        else:
            found = extract_page_offers(body, url, provider, config)

        for record in found:
            record["fetched_at"] = fetched_at
        row["offers"] = len(found)
        row["priced"] = sum(1 for record in found if "price" in record)
        skipped = provider.pop("_skipped_no_title", 0)
        if skipped:
            row["note"] = f"{skipped} further price(s) were found without a trustworthy plan name and left out"
        if not found and not row["note"]:
            row["note"] = "no offer could be extracted from this page; nothing was invented"
        report.append(row)
        offers.extend(found)
        print(f"[ok]   {provider['name']}: kept {len(found)} offer(s), {row['priced']} with a price")
        time.sleep(1)

    payload = {
        "generated_at": fetched_at,
        "brand": site.get("brand"),
        "niche": site.get("niche"),
        "site_title": site.get("title"),
        "tagline": site.get("tagline"),
        "locale": site.get("locale", "en-US"),
        "base_currency": site.get("currency", "USD"),
        "fields": config["fields"],
        "rules": config["rules"],
        "boundaries": config["boundaries"],
        "providers": report,
        "offers": offers,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT_PATH.name}: {len(offers)} offers from {len(report)} providers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
