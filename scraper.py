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
            "layout": "card",
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

# 规格提取：只从"价格附近的那几行"里取，取的必须是页面上本来就写着的数字。
# ::RULE{规格只从价格上下邻域提取⇒找不到就整条不写规格字段 不许拿别的行凑}
# ::RULE{单位换算一律不做⇒页面上写 GB 就记 GB 数值 不替它换成别的单位}
SPEC_LOOKBACK = 5
SPEC_LOOKAHEAD = 8
RAM_RE = re.compile(r"(?<![0-9a-z])(\d{1,4})\s?gb\s*(?:ram|memory|ddr\d?|ecc)\b", re.I)
RAM_RE_ALT = re.compile(r"\b(?:ram|memory|ddr\d?|ecc)\b[^0-9\n]{0,12}(?<![0-9a-z])(\d{1,4})\s?gb\b", re.I)
# 只认真的 CPU 计数：不能把促销语 "with a 1-year term" 里的 1 当成 1 个核。
VCPU_RE = re.compile(r"(?<![0-9a-z-])(\d{1,3})\s*(?:x\s*)?(?:vcpus?|vcores?|v-cores?)\b|\b(\d{1,3})\s+(?:cpu\s+)?cores?\b", re.I)
DISK_RE = re.compile(r"(?<![0-9a-z])(\d{1,5})\s?(gb|tb)\s*(?:ssd|nvme|storage|disk|raid\d*)\b", re.I)


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


def title_key(text: str) -> str:
    """把标题压成可比较的 key，用来判断"这是不是另一个套餐"。"""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _specs_from(window: list[str]) -> dict:
    specs: dict = {}
    for line in window:
        if "ram_gb" not in specs:
            match = RAM_RE.search(line) or RAM_RE_ALT.search(line)
            if match:
                specs["ram_gb"] = int(match.group(1))
        if "vcpu" not in specs:
            match = VCPU_RE.search(line)
            if match:
                specs["vcpu"] = int(match.group(1) or match.group(2))
        if "disk_gb" not in specs:
            match = DISK_RE.search(line)
            if match:
                amount = int(match.group(1))
                specs["disk_gb"] = amount * 1024 if match.group(2).lower() == "tb" else amount
    return specs


def _is_other_plan(line: str, config: dict, current_key: str) -> bool:
    candidate = strip_filler(clean_title(line), config["filler"])
    lowered = candidate.lower()
    return (
        title_score(candidate, config) >= 2
        and any(hint in lowered for hint in config["title_hints"])
        and title_key(candidate) != current_key
    )


SPEC_OWNERSHIP_REACH = 12


def spec_clusters(lines: list[str], config: dict) -> list[dict]:
    """把页面切成"规格块"：连续若干行里带单位数字（GB / cores / NVMe ...），允许夹一个非规格行。

    归属规则（对两种真实卡片布局都成立）：
      1. 一个规格块优先归"紧跟它下面、且距离最近"的那个套餐价格
         —— netcup / BuyVM 是这种布局（规格在上面，价格在下面）。
      2. 如果它下面没有在 SPEC_OWNERSHIP_REACH 行内的价格，就归它上面最近的那个价格
         —— IONOS / OVHcloud 是这种布局（价格在上面，规格在下面）。
      3. 同一个价格名下只留距离最近的那个块。
    只认套餐月费行：带 "per hour / hourly / setup fee" 的行（netcup 的 €0.052 per hour）
    不参与归属，否则会把规格块拽到小时价上。
    """
    def is_spec(line: str) -> bool:
        return bool(
            RAM_RE.search(line) or RAM_RE_ALT.search(line) or VCPU_RE.search(line) or DISK_RE.search(line)
        )

    def is_plan_price(line: str) -> bool:
        if not PRICE_RE.search(line):
            return False
        lowered = line.lower()
        return not any(word in lowered for word in config["skip_price"])

    clusters: list[dict] = []
    current: list[int] = []
    gap = 0
    for index, line in enumerate(lines):
        if is_spec(line) and not PRICE_RE.search(line):
            current.append(index)
            gap = 0
            continue
        if current and gap == 0 and not PRICE_RE.search(line):
            gap = 1  # 容忍一行间隔
            continue
        if current:
            clusters.append({"start": current[0], "end": current[-1],
                             "specs": _specs_from([lines[i] for i in current])})
            current = []
            gap = 0
    if current:
        clusters.append({"start": current[0], "end": current[-1],
                         "specs": _specs_from([lines[i] for i in current])})

    price_indices = [i for i, line in enumerate(lines) if is_plan_price(line)]
    for cluster in clusters:
        following = [p for p in price_indices if p > cluster["end"] and p - cluster["end"] <= SPEC_OWNERSHIP_REACH]
        if following:
            owner = min(following, key=lambda p: p - cluster["end"])
            distance = owner - cluster["end"]
        else:
            preceding = [p for p in price_indices if p < cluster["start"]]
            if not preceding:
                cluster["owner"] = None
                cluster["distance"] = None
                continue
            owner = max(preceding)
            distance = cluster["start"] - owner
        cluster["owner"] = owner
        cluster["distance"] = distance
    return clusters


def specs_by_price(lines: list[str], config: dict) -> dict[int, dict]:
    """算出每个价格行该拿到哪份规格：同一价格名下距离最近的那个规格块胜出。"""
    out: dict[int, dict] = {}
    for cluster in spec_clusters(lines, config):
        owner = cluster["owner"]
        if owner is None:
            continue
        current = out.get(owner)
        if current is None or cluster["distance"] < current["distance"]:
            out[owner] = cluster
    return {price: cluster["specs"] for price, cluster in out.items()}


# 这些词出现在套餐名里等于没信息：OVHcloud 的 "VPS-1" 只抽出 {vps}，
# 于是页面上每个带 vps 的导航链接都同分（1.00），谁先出现谁赢——
# 实测结果是把按钮指到了 /en/bare-metal/（裸金属页），完全不是这个套餐。
# 规则：套餐名只剩这类通用词时，不去猜具体页面，直接回落到抓取来源页。
GENERIC_TITLE_TOKENS = {
    "vps", "vserver", "server", "servers", "plan", "plans", "cloud", "hosting",
    "virtual", "private", "instance", "instances", "package",
}


def match_anchor(title: str, anchor_list: list[tuple[str, str]], fallback: str) -> str:
    tokens = {t for t in re.findall(r"[a-z0-9]{3,}", title.lower())}
    if not tokens or tokens <= GENERIC_TITLE_TOKENS:
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


def promo_pair_indices(lines: list[str]) -> set[int]:
    """找出"原价行 + 紧跟着的促销价行"里的原价行，把它们排除。

    卡片通常两行相邻给价：上面是常规价，下面一行是促销价（$6 然后 $ 2）。同一个套餐只留
    促销价那一行，否则同一套餐会产出两条记录、而且规格只挂在其中一条上。
    """
    skip: set[int] = set()
    for index, line in enumerate(lines):
        if not PRICE_RE.search(line):
            continue
        for forward in (1, 2, 3):
            if index + forward >= len(lines):
                break
            following = lines[index + forward]
            if not PRICE_RE.search(following):
                continue
            first = PRICE_RE.search(line)
            second = PRICE_RE.search(following)
            a = normalize_amount(first.group("amt"), 1e9)
            b = normalize_amount(second.group("amt"), 1e9)
            if a is not None and b is not None and b < a:
                skip.add(index)
            break
    return skip


PLAN_STOPWORDS = {
    "at", "the", "is", "are", "for", "and", "or", "with", "from", "your", "our", "we", "you",
    "hosting", "server", "servers", "price", "prices", "plans", "plan", "more", "learn", "read",
    "details", "order", "buy", "now", "get", "started", "starting", "monthly", "month", "year",
    "per", "hour", "included", "unbeatable", "powerful", "flexible", "affordable", "cheap",
}


def plan_title_line(line: str, config: dict) -> str:
    """这一行是不是"套餐名"（用来切分套餐区块）。

    认的是产品名形态：短、不是句子、带产品名词，且不含英文虚词。
    "VPS-1" / "VPS 500 G12" / "VPS S+" / "HIGH VOLUME VPS" 都算；
    "VPS hosting at an unbeatable price" / "Explore our Windows VPS servers" 不算。
    """
    candidate = strip_filler(clean_title(line), config["filler"])
    if not candidate or len(candidate) > 40 or PRICE_RE.search(candidate):
        return ""
    lowered = candidate.lower()
    if not re.search(r"\b(?:vps|vserver|v-?server|kvm|slice)\b", lowered):
        return ""
    words = re.findall(r"[a-z]+", lowered)
    if any(word in PLAN_STOPWORDS for word in words):
        return ""
    if len(words) > 4:
        return ""
    return candidate


def plan_segment_offers(lines: list[str], config: dict) -> list[tuple[str, int, dict]]:
    """按套餐名切段，每段内部把价格和规格配成对。

    为什么必须切段：跨套餐做"最近价格"匹配时，两种布局都会互相抢
    （OVHcloud 的规格块离下一个套餐的价格更近；IONOS 的规格块离下一个套餐的价格也更近），
    只有先框定一个套餐的范围，规格才不会被邻档认领。
    """
    titles = [(index, plan_title_line(line, config)) for index, line in enumerate(lines)]
    titles = [(index, name) for index, name in titles if name]
    results: list[tuple[str, int, dict]] = []
    for position, (start, name) in enumerate(titles):
        end = titles[position + 1][0] if position + 1 < len(titles) else len(lines)
        segment = []
        for index in range(start, end):
            line = lines[index]
            if index > start and plan_title_line(line, config):
                break
            segment.append((index, line))
        prices = [(index, line) for index, line in segment if PRICE_RE.search(line)
                  and not any(word in line.lower() for word in config["skip_price"])]
        specs = [
            (index, line) for index, line in segment
            if index > start
            and (RAM_RE.search(line) or RAM_RE_ALT.search(line) or VCPU_RE.search(line) or DISK_RE.search(line))
            and not PRICE_RE.search(line)
        ]
        if not prices or not specs:
            continue
        # 贪心就近配对：先配距离最近的一对，配过的两边都不再参与。
        # 这样 "规格在价格上面"（netcup / BuyVM）和"规格在价格下面"（IONOS / OVHcloud）
        # 都能各自配上，且不会像逐行方向判断那样错位到邻档。
        candidates = []
        for price_index, price_line in prices:
            for spec_index, _spec_line in specs:
                candidates.append((abs(spec_index - price_index), price_index, spec_index))
        candidates.sort(key=lambda item: (item[0], item[1]))
        taken_prices: set[int] = set()
        taken_specs: set[int] = set()
        for _distance, price_index, spec_index in candidates:
            if price_index in taken_prices or spec_index in taken_specs:
                continue
            # 这个规格行所属的整个规格块
            block_start = spec_index
            while block_start - 1 >= start and any(
                RAM_RE.search(lines[block_start - 1]) or RAM_RE_ALT.search(lines[block_start - 1])
                or VCPU_RE.search(lines[block_start - 1]) or DISK_RE.search(lines[block_start - 1])
                for _ in (0,)
            ) and not PRICE_RE.search(lines[block_start - 1]):
                block_start -= 1
            block_end = spec_index
            while block_end + 1 < end and any(
                RAM_RE.search(lines[block_end + 1]) or RAM_RE_ALT.search(lines[block_end + 1])
                or VCPU_RE.search(lines[block_end + 1]) or DISK_RE.search(lines[block_end + 1])
                for _ in (0,)
            ) and not PRICE_RE.search(lines[block_end + 1]):
                block_end += 1
            given = _specs_from([lines[i] for i in range(block_start, block_end + 1)])
            if not given:
                continue
            taken_prices.add(price_index)
            taken_specs.update(range(block_start, block_end + 1))
            results.append((name, price_index, given))
    return results



# 竖排规格表布局（Hostwinds 这类）：每个套餐是
#   CPU / 值 / RAM / 值 / Storage / 值 / Bandwidth / 值 / Price / 价格
# 规格与标签分列，且**页面上没有套餐名，只有规格数字**。
# 因此名字只能由已公布的规格拼出（例如 "Unmanaged Linux VPS - 1 CPU / 1 GB / 30 GB"），
# 这不违反"找不到可信产品名就不收录"：块本身就是产品，规格就是它的唯一标识。
# ::RULE{表布局只在 site.ilang 里 layout=table 的厂商上启用⇒不在代码里写死厂商名}
_TABLE_LABELS = {"cpu": "vcpu", "ram": "ram_gb", "storage": "disk_gb"}


def extract_table_offers(html: str, source_url: str, provider: dict, config: dict) -> list[dict]:
    lines = rendered_lines(html)
    max_price = float(config["site"].get("max_price", 5000))
    # 取页面上方那行 H1 作为产品名（例如 "Unmanaged Linux VPS Hosting"）。
    # 只在前 60 行里找，且排除含 "|" 的站点标题行——否则会抓到页脚那句带竖线的句子。
    product = ""
    for line in lines[:60]:
        lowered = line.lower()
        if "|" in line:
            continue
        if lowered.endswith("vps hosting") or lowered.endswith("cloud servers"):
            product = clean_title(line)
            break

    def spec_number(text: str, kind: str) -> int | None:
        match = re.search(r"(\d{1,5})\s*(gb|tb)", text, re.I)
        if match:
            value = int(match.group(1))
            return value * 1024 if match.group(2).lower() == "tb" else value
        match = re.search(r"(\d{1,3})\s*cpu", text, re.I)
        return int(match.group(1)) if match else None

    found: list[dict] = []
    for index, line in enumerate(lines):
        if line.strip().lower() != "price":
            continue
        match = PRICE_RE.search(lines[index + 1]) if index + 1 < len(lines) else None
        if not match:
            continue
        amount = normalize_amount(match.group("amt"), max_price)
        if amount is None:
            continue
        specs: dict = {}
        for back in range(1, 13):
            position = index - back
            if position < 1:
                break
            label = lines[position - 1].strip().lower()
            if label in _TABLE_LABELS:
                value = spec_number(lines[position], label)
                if value is not None:
                    specs.setdefault(_TABLE_LABELS[label], value)
        currency = CURRENCY_SYMBOLS.get(match.group("cur").lower(), provider.get("currency", "USD"))
        bits = []
        if specs.get("vcpu"):
            bits.append(f"{specs['vcpu']} CPU")
        if specs.get("ram_gb"):
            bits.append(f"{specs['ram_gb']} GB RAM")
        if specs.get("disk_gb"):
            bits.append(f"{specs['disk_gb']} GB")
        if not bits:
            continue
        title = f"{product} - {' / '.join(bits)}" if product else " / ".join(bits)
        record = {
            "provider": provider["name"],
            "title": title,
            "price": amount,
            "currency": currency,
            "offer_url": provider.get("affiliate_url") or source_url,
            "source_url": source_url,
        }
        record.update(specs)
        key = (record["title"].lower(), amount)
        if any(r["title"].lower() == record["title"].lower() and r["price"] == amount for r in found):
            continue
        found.append(record)
        if len(found) >= MAX_OFFERS_PER_PROVIDER:
            break
    return found


def extract_page_offers(html: str, source_url: str, provider: dict, config: dict) -> list[dict]:
    # 布局由 site.ilang 的 layout= 决定，默认 card（价格与规格在同一个卡片内的布局）
    if (provider.get("layout") or "card").lower() == "table":
        return extract_table_offers(html, source_url, provider, config)
    lines = rendered_lines(html)
    skip_lines = promo_pair_indices(lines)
    # 规格归属按"套餐区块"算：先切段再配对，避免邻档互相抢规格。
    # 用价格行号做键，绝不用标题字符串做键（抓到的标题和区块标题不保证逐字相同）。
    segment_specs = {index: specs for _name, index, specs in plan_segment_offers(lines, config)}
    anchor_list = anchors(html, source_url)
    lookback = int(config["site"].get("lookback_lines", 12))
    max_price = float(config["site"].get("max_price", 5000))
    found: dict[tuple, dict] = {}
    skipped_no_title = 0

    for index, line in enumerate(lines):
        if index in skip_lines:
            continue
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
            record.update(segment_specs.get(index, {}))
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
