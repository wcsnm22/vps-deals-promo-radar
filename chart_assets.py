# ILANG
# TYPE:module ROLE:chart-assets PROJECT:vps-deals
# ::RULE{图里的每个数字都来自 data/offers.json⇒图上没有估的值 没有装饰性数字}
# ::RULE{价格和内存缺一个就不进图⇒宁可少一根柱子 不许补一根}
# ::RULE{输出纯 SVG 文本⇒零依赖 零外部字体 零外部请求}
# ::BOUNDARY{never:改数字让图好看|scope:file}
"""把抓到的价格画成可以直接插进页面的 SVG 图（第 10 步 T5 的"套图"）。

每张图只画一个口径：每 GB 内存的月费 = 厂商公布的价格 ÷ 厂商公布的内存。
读不出内存的套餐不进图，图上留白也不补柱子。
用法：python chart_assets.py [输出目录，默认 site/assets]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

WIDTH = 760
ROW_HEIGHT = 34
PADDING = 24
BAR_HEIGHT = 18
LABEL_WIDTH = 300

BACKGROUND = "#0f172a"
BAR = "#38bdf8"
BAR_ALT = "#22d3ee"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
GRID = "#1e293b"


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slug(text: str) -> str:
    """和 build.py 的 slugify 同一套规则：页面里拼图片名时两边必须一致。"""
    import re

    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "item"


def _money(price, currency: str) -> str:
    if isinstance(price, float) and price != int(price):
        return f"{price:.2f} {currency}".strip()
    return f"{int(price)} {currency}".strip()


def per_gb_rows(offers: list[dict], provider: str | None = None) -> list[dict]:
    """能算单价的套餐，按单价从低到高。加 provider 就只看那一家。"""
    rows = []
    for offer in offers:
        if provider and offer.get("provider") != provider:
            continue
        if offer.get("price") is None or not offer.get("ram_gb"):
            continue
        rows.append(
            {
                "label": f"{offer['provider']} {offer['title']}",
                "per_gb": offer["price"] / offer["ram_gb"],
                "price": offer["price"],
                "ram_gb": offer["ram_gb"],
                "currency": offer.get("currency", ""),
            }
        )
    return sorted(rows, key=lambda row: row["per_gb"])


def per_gb_chart(rows: list[dict], title: str, subtitle: str, limit: int = 12) -> str:
    rows = rows[:limit]
    # 不同货币的每一行都只是"厂商印在页面上的那个数"：不换算、不合并。为了不让人把
    # 两条不同货币的柱子直接比长短，按货币分块：同一货币的内部排序才是可比的。
    # 组间顺序按各组最低单价，组内按单价升序。
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["currency"], []).append(row)
    blocks = sorted(
        (sorted(items, key=lambda item: item["per_gb"]) for items in grouped.values()),
        key=lambda items: items[0]["per_gb"],
    )
    height = PADDING * 3 + 46 + (ROW_HEIGHT * len(rows) + 44 * max(0, len(blocks) - 1))
    top = PADDING + 52
    chart_left = PADDING + LABEL_WIDTH
    chart_width = WIDTH - chart_left - PADDING - 130
    worst = max((row["per_gb"] for row in rows), default=1.0) or 1.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" height="{height}" '
        f'role="img" aria-label="{escape(title)}">',
        f'<rect width="{WIDTH}" height="{height}" fill="{BACKGROUND}" rx="10"/>',
        f'<text x="{PADDING}" y="{PADDING + 18}" fill="{TEXT}" font-family="system-ui,sans-serif" '
        f'font-size="20" font-weight="600">{escape(title)}</text>',
        f'<text x="{PADDING}" y="{PADDING + 40}" fill="{MUTED}" font-family="system-ui,sans-serif" '
        f'font-size="13">{escape(subtitle)}</text>',
    ]
    y = top
    drawn = 0
    for block_index, block in enumerate(blocks):
        if block_index:
            y += 20
        if len(blocks) > 1:
            parts.append(
                f'<text x="{PADDING}" y="{y + 12}" fill="{MUTED}" font-family="system-ui,sans-serif" '
                f'font-size="12" font-weight="600">{escape(block[0]["currency"] or "listed currency")} rows</text>'
            )
            y += 24
        for row in block:
            width = max(2.0, chart_width * (row["per_gb"] / worst))
            colour = BAR if drawn % 2 == 0 else BAR_ALT
            label = row["label"] if len(row["label"]) <= 42 else row["label"][:39] + "..."
            parts.append(
                f'<text x="{PADDING}" y="{y + 14}" fill="{TEXT}" font-family="system-ui,sans-serif" '
                f'font-size="13">{escape(label)}</text>'
            )
            parts.append(
                f'<rect x="{chart_left}" y="{y + 2}" width="{width:.1f}" height="{BAR_HEIGHT}" fill="{colour}" rx="3"/>'
            )
            parts.append(
                f'<text x="{chart_left + width + 8:.1f}" y="{y + 15}" fill="{MUTED}" '
                f'font-family="ui-monospace,monospace" font-size="12">{row["per_gb"]:.4f} {escape(row["currency"])}/GB</text>'
            )
            parts.append(
                f'<text x="{PADDING}" y="{y + 28}" fill="{BACKGROUND}" font-family="system-ui,sans-serif" font-size="1">'
                f'{_money(row["price"], row["currency"])} / {row["ram_gb"]} GB</text>'
            )
            y += ROW_HEIGHT
            drawn += 1
    parts.append("</svg>")
    return "\n".join(parts)


def split_chart(rows: list[dict], title: str, subtitle: str, limit: int = 6) -> str:
    """把"月费"和"每 GB 摊到多少"并排画出来：一眼看出贵在哪。"""
    rows = rows[:limit]
    height = PADDING * 3 + 46 + ROW_HEIGHT * len(rows)
    top = PADDING + 52
    chart_left = PADDING + LABEL_WIDTH
    chart_width = WIDTH - chart_left - PADDING - 120
    worst = max((row["price"] for row in rows), default=1.0) or 1.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" height="{height}" '
        f'role="img" aria-label="{escape(title)}">',
        f'<rect width="{WIDTH}" height="{height}" fill="{BACKGROUND}" rx="10"/>',
        f'<text x="{PADDING}" y="{PADDING + 18}" fill="{TEXT}" font-family="system-ui,sans-serif" '
        f'font-size="20" font-weight="600">{escape(title)}</text>',
        f'<text x="{PADDING}" y="{PADDING + 40}" fill="{MUTED}" font-family="system-ui,sans-serif" '
        f'font-size="13">{escape(subtitle)}</text>',
    ]
    for index, row in enumerate(rows):
        y = top + index * ROW_HEIGHT
        width = max(2.0, chart_width * (row["price"] / worst))
        label = row["label"] if len(row["label"]) <= 42 else row["label"][:39] + "..."
        parts.append(
            f'<text x="{PADDING}" y="{y + 14}" fill="{TEXT}" font-family="system-ui,sans-serif" '
            f'font-size="13">{escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{chart_left}" y="{y + 2}" width="{width:.1f}" height="{BAR_HEIGHT}" fill="{BAR}" rx="3"/>'
        )
        parts.append(
            f'<text x="{chart_left + width + 8:.1f}" y="{y + 15}" fill="{MUTED}" '
            f'font-family="ui-monospace,monospace" font-size="12">'
            f'{_money(row["price"], row["currency"])} = {row["ram_gb"]} GB RAM</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def build_all(offers: list[dict], out_dir: Path) -> list[str]:
    """写出所有图，返回写出的文件名。调用方负责把文件名插进页面。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    every = per_gb_rows(offers)
    if every:
        name = "per-gb-cheapest.svg"
        (out_dir / name).write_text(
            per_gb_chart(
                every,
                "Cheapest RAM per GB by currency",
                "Each row is one provider's published monthly price divided by the RAM it printed beside it. "
                "Groups are ordered by their own cheapest row and never converted between currencies; a plan "
                "without a published RAM figure is not drawn.",
            ),
            encoding="utf-8",
        )
        written.append(name)
    providers = sorted({offer["provider"] for offer in offers})
    for provider in providers:
        rows = per_gb_rows(offers, provider)
        if len(rows) < 2:
            continue
        name = f"per-gb-{slug(provider)}.svg"
        (out_dir / name).write_text(
            per_gb_chart(
                rows,
                f"{provider}: monthly price per GB of RAM",
                f"{len(rows)} plans from {provider} publish both a price and a RAM figure. "
                "Computed, not quoted.",
            ),
            encoding="utf-8",
        )
        written.append(name)
        split_name = f"monthly-vs-ram-{slug(provider)}.svg"
        (out_dir / split_name).write_text(
            split_chart(
                rows,
                f"{provider}: what the monthly fee buys",
                "Bar length is the published monthly price; the number beside it is the RAM it includes.",
            ),
            encoding="utf-8",
        )
        written.append(split_name)
    return written


def main() -> int:
    import json

    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site" / "assets"
    payload = json.loads((ROOT / "data" / "offers.json").read_text(encoding="utf-8"))
    import guides

    offers = guides.collapse_offers(payload["offers"])
    written = build_all(offers, out_dir)
    print(f"[ok]   wrote {len(written)} chart(s) into {out_dir}")
    for name in written:
        print(f"      {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
