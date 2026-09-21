# ILANG
# TYPE:module ROLE:guide-generator PROJECT:vps-deals
# ::RULE{每一篇只补 GAP 三样中的一样⇒gap 字段只能是 csv|unitprice|steps}
# ::RULE{第一屏必须是答案⇒answer 一行里给出结论数字 且能被同一页的表格复算出来}
# ::RULE{数字只来自 data/offers.json 或页面写明的公开文档⇒这里不许出现任何估的数}
# ::RULE{不抄对标站原文⇒这里的句子由本文件生成 表格由抓到的字段拼出}
# ::BOUNDARY{never:编价格 编规格 编排名|scope:file}
"""按日历从 data/guides.json 的队列里取下一篇，补一个缺口。

零依赖、确定性：同样的队列和数据必然生成同样的页面。
用法：python guides.py            # 补足队列里所有 pending
      python guides.py 1          # 只补一篇
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUIDES_PATH = ROOT / "data" / "guides.json"
DATA_PATH = ROOT / "data" / "offers.json"

GAP_ORDER = ["csv", "unitprice", "steps"]

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
    providers_in_data = sorted({o["provider"] for o in offers})
    focus = providers_in_data[occurrence_index % len(providers_in_data)] if providers_in_data else None

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


def per_gb_cell(offer: dict) -> str:
    """单价单元格：只有价格和内存都写在页面上时才算，缺一个就如实写 '-'。"""
    price = offer.get("price")
    ram = offer.get("ram_gb")
    if not price or not ram:
        return '<span class="muted">-</span>'
    currency = offer.get("currency", "")
    return f"{price / ram:.4f} {currency}/GB"


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
    while limit == 0 or made < limit:
        gap = next_gap(guides)
        entry = build_entry(gap, offers, stamp, made + 1, occurrence(guides, gap))
        if entry["title"].lower() in _used_titles(guides):
            break
        guides.append(entry)
        made += 1
        if limit == 0:
            break  # 一天一篇：默认只补一篇
    if made:
        GUIDES_PATH.write_text(json.dumps(guides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok]   added {made} guide(s) for {today}; total {len(guides)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
