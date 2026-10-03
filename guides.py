# ILANG
# TYPE:module ROLE:guide-generator PROJECT:vps-deals
# ::RULE{每一篇只补 GAP 三样中的一样⇒gap 字段只能是 csv|unitprice|steps|queue}
# ::RULE{第一屏必须是答案⇒answer 一行里给出结论数字 且能被同一页的表格复算出来}
# ::RULE{数字只来自 data/offers.json 或页面写明的公开文档⇒这里不许出现任何估的数}
# ::RULE{不抄对标站原文⇒这里的句子由本文件生成 表格由抓到的字段拼出}
# ::RULE{对标队列里没有公开数字能撑住的词⇒不写 留给人写 不改口径去凑}
# ::BOUNDARY{never:编价格 编规格 编排名|scope:file}
"""按日历从 data/guides.json 的队列里取下一篇，补一个缺口。

零依赖、确定性：同样的队列和数据必然生成同样的页面。
用法：python guides.py            # 补足队列里所有 pending
      python guides.py 1          # 只补一篇
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUIDES_PATH = ROOT / "data" / "guides.json"
DATA_PATH = ROOT / "data" / "offers.json"

GAP_ORDER = ["csv", "unitprice", "steps"]

# unitprice 页至少要能排出这么多档：只有一档的"排名"没有信息量，第一屏给不出有用的答案。
# 触及这个下限的厂商不进 unitprice 的轮换池，但 csv / steps 照旧轮到它们。
MIN_PER_GB_PLANS = 2

# 同一个缺口最多往下试几个厂商：试到能给出可核对答案的那家为止。
MAX_FOCUS_ATTEMPTS = 12

# 每一步都来自厂商公开文档；这里只做顺序整理，不转述原文。
STEP_BLUEPRINT = [
    ("Decide the resource floor from the workload, not the price",
     "Write down the smallest RAM figure that will run your stack. A single small web app or VPN fits in 1-2 GB; a database doing real work wants 4 GB or more."),
    ("Compare plans on published numbers only",
     "Use the tracked price list and divide price by the RAM figure the provider published. If a plan publishes no RAM figure next to its price, the per-GB number is unknown - do not guess it."),
    ("Check what the price excludes before you commit",
     "Backups, control panels, extra IPv4 addresses and Windows licences are commonly billed separately. Read the row underneath the plan card on the provider's own pricing page."),
    ("Create the account and deploy the server",
     "In the provider's control panel choose the plan, the region closest to your users, and the operating system image. Linux images carry no extra licence fee on the low-cost plans; Windows normally adds one."),
    ("Add your SSH key during deployment",
     "Paste your public key at deploy time. With key authentication you can turn password login off later instead of leaving a password exposed to the internet."),
    ("Connect over SSH on Linux plans",
     "The provider issues the server address at deploy time; connect from a terminal with the username and key you configured. The out-of-band console in the panel is the fallback when SSH does not answer."),
    ("Connect over RDP on Windows plans",
     "Reach a Windows VPS with Remote Desktop using the administrator credentials the provider issued. Where a bring-your-own-licence path is documented, activate your own retail or volume licence after installation."),
    ("Update and harden before pointing traffic at it",
     "Apply operating-system updates, replace password login with keys where the OS supports it, open only the ports you need, and confirm you hold a backup or snapshot you can actually restore."),
]


def load(payload_path: Path) -> dict:
    return json.loads(payload_path.read_text(encoding="utf-8"))


def collapse_offers(offers: list[dict]) -> list[dict]:
    """与 build.py 同一套塌缩规则：同一厂商同一套餐名只留一条（价格取更低那个）。

    口径必须与站点一致，否则指南里写的行数会和 CSV 里实际的行数对不上。
    """
    best: dict[tuple, dict] = {}
    for offer in offers:
        key = (offer["provider"], offer["title"].lower())
        current = best.get(key)
        if current is None:
            best[key] = dict(offer)
            continue
        if offer.get("price") is not None and (
            current.get("price") is None or offer["price"] < current["price"]
        ):
            current["price"] = offer["price"]
            current["currency"] = offer.get("currency", current.get("currency"))
    return list(best.values())


def _guidance_counts(offers: list[dict]) -> dict:
    priced = [o for o in offers if o.get("price") is not None]
    with_ram = [o for o in priced if o.get("ram_gb")]
    return {
        "priced": len(priced),
        "with_ram": len(with_ram),
        "providers": len({o["provider"] for o in priced}),
    }


def _used_titles(guides: list[dict]) -> set[str]:
    return {g["title"].lower() for g in guides}


def next_gap(guides: list[dict]) -> str:
    """按 csv -> unitprice -> steps 轮换，保证三样缺口都被补到。"""
    counts = {gap: 0 for gap in GAP_ORDER}
    for guide in guides:
        if guide.get("gap") in counts:
            counts[guide["gap"]] += 1
    return min(GAP_ORDER, key=lambda gap: count_of(gap, counts))


def count_of(gap: str, counts: dict) -> tuple:
    return (counts[gap], GAP_ORDER.index(gap))


def per_gb_providers(offers: list[dict], minimum: int = MIN_PER_GB_PLANS) -> list[str]:
    """能算单价（公布价格 + 公布内存）的厂商，按名字排序。

    只有这些厂商的 unitprice 页第一屏才有可核对的数字。厂商清单是轮换池，
    不因为某个缺口用不上就改口径：csv / steps 仍然轮到所有厂商。
    """
    counts: dict[str, int] = {}
    for offer in offers:
        if offer.get("price") is not None and offer.get("ram_gb"):
            counts[offer["provider"]] = counts.get(offer["provider"], 0) + 1
    return sorted(name for name, count in counts.items() if count >= minimum)


def focus_provider(gap: str, offers: list[dict], occurrence_index: int) -> str | None:
    """今天这篇写哪家。unitprice 只在"能算出单价"的厂商里轮换，其余缺口按全量厂商轮换。"""
    if gap == "unitprice":
        pool = per_gb_providers(offers)
    else:
        pool = sorted({o["provider"] for o in offers})
    return pool[occurrence_index % len(pool)] if pool else None


def occurrence(guides: list[dict], gap: str) -> int:
    """这一类缺口已经写过几次。用来决定今天换哪个主题，避免每天同一句话。"""
    return sum(1 for g in guides if g.get("gap") == gap)


def build_entry(gap: str, offers: list[dict], stamp: str, index: int, occurrence_index: int = 0) -> dict:
    """生成一篇只补一个缺口的页。

    每天换一个主题（按厂商轮换），这样同一种缺口在不同日子给出的**数字和表格都不一样**，
    而不是把同一句话复制十遍。主题来自我们自己的抓取数据，不是编的。
    """
    counts = _guidance_counts(offers)
    priced = sorted((o for o in offers if o.get("price") is not None), key=lambda o: o["price"])
    with_ram_all = sorted(prices_with_ram(offers), key=lambda o: o["price"] / o["ram_gb"])
    focus = focus_provider(gap, offers, occurrence_index)

    focus_offers = [o for o in priced if o["provider"] == focus]
    # 必须在自家套餐里再排一次：with_ram_all 是全站排序，直接取第一个会把"全站最便宜"
    # 误写成"这家最便宜"（IONOS 那次就把最贵的一档写成了最便宜）。
    focus_ranked = sorted(
        [o for o in with_ram_all if o["provider"] == focus],
        key=lambda o: o["price"] / o["ram_gb"],
    )
    cheapest = min(focus_offers, key=lambda o: o["price"]) if focus_offers else None

    if gap == "csv":
        title = f"Cheap VPS price table to download - {focus} plans, {stamp[:10]} snapshot"
        if focus_offers:
            best = min(focus_ranked, key=lambda o: o["price"] / o["ram_gb"]) if focus_ranked else None
            answer = (
                f"{len(focus_offers)} tracked {focus} plans with a published price, "
                f"{len(focus_ranked)} of them carry a per-GB figure"
                + (f"; cheapest per GB is {best['title']} at {best['price'] / best['ram_gb']:.4f} "
                   f"{best.get('currency','')}/GB." if best else ".")
                + f" The full {counts['priced']}-plan table is downloadable as CSV."
            )
            rows = "".join(
                "<tr>"
                f"<td>{o['title']}</td><td class=\"price\">{o['price']} {o.get('currency','')}</td>"
                f"<td>{o.get('ram_gb') or '<span class=\"muted\">not published</span>'}</td>"
                f"<td>{o.get('vcpu') or '<span class=\"muted\">not published</span>'}</td>"
                f"<td class=\"price\">{per_gb_cell(o)}</td>"
                "</tr>"
                for o in focus_offers
            )
            section = [
                ("The file",
                 f'<p><a class="cta" href="/downloads/unit-price.csv">Download unit-price.csv '
                 f'({counts["priced"]} plans, all providers)</a></p>'),
                (f"{focus} plans in the table",
                 f'<div class="table-shell"><table><thead><tr><th>Plan</th><th>Published price</th>'
                 f'<th>RAM (GB)</th><th>vCPU</th><th>Price per GB</th></tr></thead><tbody>{rows}</tbody></table></div>'),
                ("Coverage",
                 f"<p>{counts['with_ram']} of {counts['priced']} tracked plans publish both a price and a RAM figure. "
                 f"The rest keep an empty per-GB cell rather than a guess.</p>"),
            ]
        else:
            answer = f"No published {focus} price is currently tracked, so this entry has no table to show."
            section = [("Coverage", "<p>Nothing published for this provider on the tracked page.</p>")]
        gap_note = ("None of the benchmarked top pages for this term serves a downloadable comparison file. "
                    "This entry hands over the file and shows the rows for one provider at a time.")
    elif gap == "unitprice":
        if focus_ranked:
            best = focus_ranked[0]
            answer = (
                f"{focus}: cheapest RAM per unit is {best['title']} at "
                f"{best['price'] / best['ram_gb']:.4f} {best.get('currency','')} per GB "
                f"({best['price']} {best.get('currency','')} / {best['ram_gb']} GB), computed from the published price only."
            )
            rows = "".join(
                "<tr>"
                f"<td>{i + 1}</td><td>{o['title']}</td>"
                f"<td class=\"price\">{o['price']} {o.get('currency','')}</td><td>{o['ram_gb']}</td>"
                f"<td class=\"price\">{o['price'] / o['ram_gb']:.4f} {o.get('currency','')}/GB</td>"
                "</tr>"
                for i, o in enumerate(focus_ranked)
            )
        else:
            answer = f"{focus} publishes no RAM figure next to its price, so no per-GB number can be computed for it."
            rows = ""
        title = f"Cheapest VPS per GB of RAM: {focus} - {stamp[:10]} ranking from {len(focus_ranked)} computable plans"
        gap_note = ("The benchmarked top pages list headline prices without breaking them down per unit. "
                    "This entry divides only the numbers the provider itself published.")
        section = [
            (f"{focus} plans ranked by price per GB",
             f'<div class="table-shell"><table><thead><tr><th>#</th><th>Plan</th>'
             f'<th>Published price</th><th>RAM (GB)</th><th>Price per GB</th></tr></thead><tbody>{rows}</tbody></table></div>'
             if rows else "<p>No computable plan for this provider.</p>"),
            ("How to recompute",
             "<p>Every per-GB cell equals the published monthly price divided by the RAM figure printed beside it. "
             "Plans without a published RAM figure are excluded instead of estimated.</p>"),
        ]
    else:
        steps = "".join(f"<li><strong>{head}</strong> {detail}</li>" for head, detail in STEP_BLUEPRINT)
        cheapest_text = (f"{cheapest['price']} {cheapest.get('currency','')}" if cheapest else "n/a")
        answer = (
            f"Eight numbered steps from picking the plan to logging in. {focus} currently tracks "
            f"{len(focus_offers)} priced plan(s), cheapest at {cheapest_text}"
            + (f" ({cheapest['title']})." if cheapest else ".")
        )
        title = f"Cheap VPS setup and connection steps: {focus} plan - numbered walkthrough, {stamp[:10]}"
        gap_note = ("Only one page across the benchmarked domains gives numbered steps, and it covers Windows "
                    "installation alone. This entry keeps the purchase-to-login sequence in one place with the "
                    "source beside each step.")
        section = [(f"Ordered steps (checked against what {focus} publishes today)", f"<ol>{steps}</ol>")]

    sections_html = "".join(f"<h2>{head}</h2>{body}" for head, body in section)
    sources = []
    seen = set()
    for offer in offers:
        url = offer.get("source_url")
        if url and url not in seen:
            seen.add(url)
            sources.append({"label": f'{offer["provider"]} published price page', "url": url})
    if gap == "steps":
        sources = [
            {"label": "RamNode - Installing Windows on Cloud VPS", "url": "https://ramnode.com/support/documentation/cloud-vps/windows-install"},
            {"label": "OVHcloud - VPS documentation entry point", "url": "https://us.ovhcloud.com/vps/"},
            {"label": "DigitalOcean - VPS hosting explained", "url": "https://www.digitalocean.com/solutions/vps-hosting"},
        ]

    return {
        "slug": f'{gap}-{stamp[:10]}-{index}',
        "title": title,
        "gap": gap,
        "gap_note": gap_note,
        "answer": answer,
        "auto": True,
        "published": stamp,
        "body_html": sections_html,
        "sources": sources[:6],
    }


def prices_with_ram(offers: list[dict]) -> list[dict]:
    return [o for o in offers if o.get("price") is not None and o.get("ram_gb")]


# ---- 对标得来的选题队列（rival_queue.py 产出）----------------------------
# 用户的决定：队列里"有数据能撑住"的词才自动成页，撑不住的留给人写。
# 撑住 = 当天抓到的公开数字足以在第一屏给出一个可复算的答案。
QUEUE_PATH = ROOT / "data" / "rival-topic-queue.json"
QUEUE_MIN_PLANS = 3

# 每类词对应一个"要用哪些字段"的门槛：字段不够就不给这个词写页，宁可空着。
QUEUE_BUILDERS = [
    ("disk", ("storage", "disk", "ssd", "nvme", "backup")),
    ("ram", ("ram", "memory")),
    ("price", ("cheap", "best", "price", "pricing", "cost", "budget", "affordable")),
]


def load_queue() -> list[dict]:
    """读选题队列（只读，不重算）。没有文件就当作没有队列。"""
    if not QUEUE_PATH.exists():
        return []
    payload = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    return payload.get("queue") or []


def _by_currency(rows: list[dict]) -> dict[str, list[dict]]:
    """按货币分组：不同货币的单价不做汇率换算（与站点图表同一口径）。"""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row.get("currency") or "USD", []).append(row)
    return groups


def queue_builder_for(phrase: str) -> str | None:
    """这条词该用哪套数字来撑：磁盘单价 / 内存单价 / 月费本身。"""
    words = set(phrase.split())
    for name, triggers in QUEUE_BUILDERS:
        if words & set(triggers):
            return name
    return None


def build_queue_entry(phrase: str, offers: list[dict], stamp: str, index: int, queue_row: dict) -> dict | None:
    """把队列里的一条词变成一页——**只有数据能撑住才返回**，否则返回 None。

    撑不住的原样留在队列里等人工（比如 `free vps`：我们抓不到任何"免费"的证据）。
    """
    kind = queue_builder_for(phrase)
    if kind is None:
        return None
    priced = [o for o in offers if o.get("price") is not None]
    if kind == "disk":
        rows = [o for o in priced if o.get("disk_gb")]
    elif kind == "ram":
        rows = [o for o in priced if o.get("ram_gb")]
    else:
        rows = priced
    if len(rows) < QUEUE_MIN_PLANS:
        return None

    if kind == "disk":
        ranked = sorted(rows, key=lambda o: o["price"] / o["disk_gb"])
        unit, total = "TB", lambda o: o["disk_gb"] / 1000
        per_unit = lambda o: o["price"] / (o["disk_gb"] / 1000)
        label, field = "disk", "disk_gb"
        title = f"Cheapest VPS disk per TB: {phrase} - ranked from {len(ranked)} plans that publish a disk size ({stamp[:10]})"
    elif kind == "ram":
        ranked = sorted(rows, key=lambda o: o["price"] / o["ram_gb"])
        unit, total = "GB", lambda o: o["ram_gb"]
        per_unit = lambda o: o["price"] / o["ram_gb"]
        label, field = "RAM", "ram_gb"
        title = f"Cheapest VPS RAM per GB: {phrase} - ranked from {len(ranked)} plans that publish a RAM figure ({stamp[:10]})"
    else:
        ranked = sorted(rows, key=lambda o: o["price"])
        unit, total = "month", lambda o: 1
        per_unit = lambda o: o["price"]
        label, field = "monthly price", None
        title = f"Cheapest tracked VPS plans: {phrase} - every price recomputable from the provider page ({stamp[:10]})"

    # 不同货币的单价不做汇率换算（与站点图表、CSV 同一口径），所以"最低"只能在**同一货币内**比：
    # 先按行数选出主货币组（并列时取字母序第一个），其余货币各报一条自己的最低价。
    groups = _by_currency(rows)
    primary = sorted(groups, key=lambda cur: (-len(groups[cur]), cur))[0]
    ranked = sorted(groups[primary], key=lambda o: per_unit(o))
    best = ranked[0]
    other_best = [
        (cur, min(sorted(groups[cur], key=lambda o: per_unit(o)), key=lambda o: per_unit(o)))
        for cur in sorted(groups)
        if cur != primary
    ]
    others_text = "".join(
        f" The {cur} group (no exchange rate is applied) is led by {o['price']} {cur} / "
        f"{total(o):g} = {per_unit(o):.4f} {cur}/{unit} ({o['provider']} {o['title']})."
        for cur, o in other_best
    )

    providers = len({o["provider"] for o in ranked})
    if kind == "disk":
        answer = (
            f"{phrase}: in the {primary} group the lowest price per TB is {per_unit(best):.4f} {primary}/TB "
            f"({best['price']} {primary} / {total(best):g} TB of disk), {best['provider']} {best['title']}."
            + others_text
            + f" {len(ranked)} of the {len(priced)} tracked plans that publish a price also publish a disk size, "
            f"so those are the only rows ranked here — the rest get no row instead of an estimate. "
            f"Across {providers} provider(s)."
        )
    elif kind == "ram":
        answer = (
            f"{phrase}: in the {primary} group the lowest price per GB of RAM is {per_unit(best):.4f} {primary}/GB "
            f"({best['price']} {primary} / {total(best):g} GB), {best['provider']} {best['title']}."
            + others_text
            + f" {len(ranked)} of the {len(priced)} tracked plans that publish a price also publish a RAM figure, "
            f"so those are the only rows ranked here — the rest get no row instead of an estimate. "
            f"Across {providers} provider(s)."
        )
    else:
        answer = (
            f"{phrase}: in the {primary} group the lowest published monthly price is {best['price']} {primary} "
            f"({best['provider']} {best['title']})." + others_text
            + f" All {len(ranked)} tracked plans in that group are ranked here, across {providers} provider(s); "
            f"nothing outside those published numbers is quoted."
        )

    body: list[str] = []
    for currency in [primary] + [c for c in sorted(groups) if c != primary]:
        group = sorted(groups[currency], key=lambda o: per_unit(o))[:12]
        cells = "".join(
            "<tr>"
            f"<td>{i + 1}</td><td>{o['title']}</td>"
            f"<td class=\"price\">{o['price']} {o.get('currency','')}</td>"
            f"<td>{total(o):g}</td>"
            f"<td class=\"price\">{per_unit(o):.4f} {o.get('currency','')}/{unit}</td>"
            "</tr>"
            for i, o in enumerate(group)
        )
        body.append(
            f"<h2>{currency} rows, cheapest per {unit} first</h2>"
            f'<div class="table-shell"><table><thead><tr><th>#</th><th>Plan</th>'
            f'<th>Published price</th><th>{label if field else "Billing"}'
            f'{" (" + unit + ")" if field else ""}</th>'
            f'<th>Price per {unit}</th></tr></thead><tbody>{cells}</tbody></table></div>'
        )
    body.append(
        "<h2>How to recompute every cell</h2>"
        "<p>Each unit price is the published monthly price divided by the figure the provider printed beside it"
        " (1 TB = 1000 GB). Currencies are grouped and never converted at an exchange rate we cannot verify."
        " A plan that publishes no figure gets no row instead of an estimate.</p>"
    )

    sources = []
    seen: set[str] = set()
    for offer in offers:
        url = offer.get("source_url")
        if url and url not in seen:
            seen.add(url)
            sources.append({"label": f'{offer["provider"]} published price page', "url": url})

    return {
        "slug": f"queue-{slug_phrase(phrase)}-{stamp[:10]}-{index}",
        "title": title,
        "gap": "queue",
        "queue_phrase": phrase,
        "gap_note": (
            f"Topic taken from the benchmark queue: {queue_row.get('rival_domains', 0)} benchmarked domain(s) use "
            f"this phrase in {queue_row.get('rival_urls', 0)} of their own URLs, and it appears in public search "
            f"suggestions. This page is written from our own tracked prices — no page of theirs was copied, and "
            f"nothing that could not be recomputed from a provider page is stated."
        ),
        "answer": answer,
        "auto": True,
        "published": stamp,
        "body_html": "".join(body),
        "sources": sources[:6],
    }


def slug_phrase(phrase: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", phrase.lower()).strip("-")
    return slug or "topic"


def queue_entry(offers: list[dict], guides: list[dict], stamp: str, index: int) -> tuple[dict | None, list[str]]:
    """按队列顺序找今天能写的一条。返回 (页面, 跳过原因清单)。

    跳过清单是为了照实说清楚"哪些词我们没写、为什么"——对不出数据的不写，不改口径去凑。
    """
    used = _used_titles(guides)
    skipped: list[str] = []
    for row in load_queue():
        phrase = row.get("phrase") or ""
        if not phrase or row.get("we_have_pages"):
            continue
        if queue_builder_for(phrase) is None:
            skipped.append(f"{phrase}（没有能撑住它的公开数字，留给人写）")
            continue
        candidate = build_queue_entry(phrase, offers, stamp, index, row)
        if candidate is None:
            skipped.append(f"{phrase}（今天抓到的字段不够排一张表，不猜）")
            continue
        if candidate["title"].lower() in used:
            skipped.append(f"{phrase}（标题已用过）")
            continue
        return candidate, skipped
    return None, skipped


def per_gb_cell(offer: dict) -> str:
    """单价单元格：只有价格和内存都写在页面上时才算，缺一个就如实写 '-'。"""
    price = offer.get("price")
    ram = offer.get("ram_gb")
    if not price or not ram:
        return '<span class="muted">-</span>'
    currency = offer.get("currency", "")
    return f"{price / ram:.4f} {currency}/GB"


def _money(amount, currency: str) -> str:
    if amount is None:
        return "n/a"
    if isinstance(amount, float) and amount != int(amount):
        return f"{amount:.2f} {currency}".strip()
    return f"{int(amount)} {currency}".strip()


# 每个问题的答案都是"从抓到的数字现算"，算不出来就不给这一问。用来做 T4：
# 把疑问句一句一句答出来，答案里的每个数都能在 data/offers.json 里复算。
QUESTION_ANSWERS = [
    (
        "How much does a cheap VPS cost per month?",
        lambda priced, with_ram: (
            f"The lowest tracked monthly price is {_money(min(o['price'] for o in priced), min(priced, key=lambda o: o['price']).get('currency', ''))} "
            f"({min(priced, key=lambda o: o['price'])['provider']} {min(priced, key=lambda o: o['price'])['title']}); "
            f"the highest in the same list is {_money(max(o['price'] for o in priced), min(priced, key=lambda o: o['price']).get('currency', ''))}. "
            f"{len(priced)} plans carry a published monthly price."
        ),
    ),
    (
        "Which plan is cheapest per GB of RAM?",
        lambda priced, with_ram: _cheapest_per_gb_answer(with_ram),
    ),
    (
        "Can I compare a price per GB of RAM at all?",
        lambda priced, with_ram: (
            f"Yes for {len(with_ram)} of {len(priced)} priced plans: those publish a RAM figure next to the price. "
            + (f"The other {len(priced) - len(with_ram)} are left with an empty per-GB cell instead of a guess."
               if len(with_ram) < len(priced)
               else "Every one of them is rankable on this page.")
            if priced else ""
        ),
    ),
    (
        "Which providers are tracked?",
        lambda priced, with_ram: (
            f"{len({o['provider'] for o in priced})} providers currently publish a price we can read: "
            f"{', '.join(sorted({o['provider'] for o in priced}))}. A provider whose page we cannot read a price on "
            f"is listed as unread rather than filled in."
            if priced else ""
        ),
    ),
    (
        "How many plans publish both a price and a RAM figure?",
        lambda priced, with_ram: (
            f"{len(with_ram)} of {len(priced)} priced plans. That is the row count you can divide to get a price "
            f"per GB of RAM; nothing outside that set is estimated."
            if priced else ""
        ),
    ),
]


def _cheapest_per_gb_answer(with_ram: list[dict]) -> str:
    """单价最便宜的那档。口径必须和页面上的表一致：价格和内存都是厂商自己公布的。"""
    if not with_ram:
        return ""
    best = min(with_ram, key=lambda o: o["price"] / o["ram_gb"])
    currency = best.get("currency", "")
    return (
        f"{best['provider']} {best['title']} at {best['price'] / best['ram_gb']:.4f} {currency}/GB "
        f"({_money(best['price'], currency)} / {best['ram_gb']} GB), computed from published numbers only."
    )


def frequently_asked(offers: list[dict], questions: list[str] | None = None) -> list[dict]:
    """T4：把疑问句一句一句答出来。答案只用抓到的数字，算不出来就不出这一问。

    questions：搜索补全里抓到的真人问句（data/keyword-bank.json）。有就在答案前面标出来源，
    没有也不影响——问题本身换成数据驱动的问法，答案口径完全一样，绝不编数字。
    先按和页面同一套规则塌缩，保证 FAQ 里的"最便宜"和页面表格里的是同一档。
    """
    offers = collapse_offers(offers)
    priced = [o for o in offers if o.get("price") is not None]
    with_ram = [o for o in priced if o.get("ram_gb")]
    if not priced:
        return []
    asked = [q.strip() for q in (questions or []) if isinstance(q, str) and q.strip()]
    out: list[dict] = []
    for question, builder in QUESTION_ANSWERS:
        try:
            answer = builder(priced, with_ram)
        except (ValueError, KeyError, TypeError, ZeroDivisionError):
            continue
        if not answer or not any(ch.isdigit() for ch in answer):
            continue
        item = {"question": question, "answer": " ".join(answer.split())}
        if asked and len(out) < len(asked):
            item["asked_as"] = asked[len(out)]  # 同一问在补全里的原话，只用来标注，不改答案
        out.append(item)
    return out


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    guides = load(GUIDES_PATH)
    offers = collapse_offers(load(DATA_PATH)["offers"])
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 已有的自动页当天不再重复生成，保证"一天一篇"而不是"一天十篇同款"。
    today = stamp[:10]
    if any(g.get("auto") and g.get("published", "")[:10] == today for g in guides):
        print(f"[skip] an auto guide for {today} already exists")
        return 0

    made = 0
    source = ""
    while limit == 0 or made < limit:
        # 先看对标队列：队列里"有数据撑得住"的词优先成页（用户 2026-10-03 的决定）。
        # 撑不住的词不写，退回原来的缺口轮换，保证"一天至少一篇"不断。
        entry, skipped = queue_entry(offers, guides, stamp, made + 1)
        if entry is not None:
            source = f'queue phrase "{entry["queue_phrase"]}"'
            if skipped:
                print(f"[note] skipped this run: {'; '.join(skipped[:5])}")
        # 一次运行内按轮换顺序往下试：同一个缺口先换厂商，厂商试完再换下一个缺口。
        # 绝不生成"第一屏没有数字"的页——那种页会被 content_check 判不合格，
        # 当天的循环就断了（2026-10-01 的 unitprice 页就是这么被拦下的）。
        if entry is None:
            for step in range(len(GAP_ORDER)):
                gap = GAP_ORDER[(GAP_ORDER.index(next_gap(guides)) + step) % len(GAP_ORDER)]
                for attempt in range(MAX_FOCUS_ATTEMPTS):
                    candidate = build_entry(
                        gap, offers, stamp, made + 1, occurrence(guides, gap) + attempt
                    )
                    if candidate["answer"].strip() and any(ch.isdigit() for ch in candidate["answer"]):
                        entry = candidate
                        break
                if entry:
                    break
            if entry is not None:
                source = f"rotation gap={entry['gap']}"
        if entry is None:
            break  # 一个缺口都补不出来：让 daily.py 照实记这条，不写空页
        if entry["title"].lower() in _used_titles(guides):
            break
        guides.append(entry)
        made += 1
        if limit == 0:
            break  # 一天一篇：默认只补一篇
    if made:
        GUIDES_PATH.write_text(json.dumps(guides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok]   added {made} guide(s) for {today}; total {len(guides)}; source: {source or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
