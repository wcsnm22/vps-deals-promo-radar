# ILANG
# TYPE:module ROLE:report PROJECT:vps-deals
# ::RULE{三个数要么来自官方 API 要么来自操作者从 GSC/GA4 后台复制的原值⇒两者都没有就报读不到}
# ::RULE{每一个数都要记下它从哪来⇒api / operator，来源差异不许抹平}
# ::RULE{报告五行以内⇒第几轮 索引 点击 排名 访客数 + 当期篇数}
# ::BOUNDARY{never:编造索引数 点击数 排名 或用估算冒充实测|scope:file}
"""每 28 天读一次 GSC 与 GA4 的数字，压成五行以内的报告。

两条取数路径，来源在输出里标明：
  1) API：--creds <服务账号 JSON> --gsc <属性> --ga4 <属性ID>
     —— Search Analytics（点击、平均排名）和 GA4 Data API（活跃用户）都能直连。
     —— 「已编入索引」Search Console 的 API 不暴露，只能走第 2 条。
  2) 操作者手贴：--indexed/--clicks/--clicks-prev/--position/--position-prev/--active-users
     —— 数值一律从 GSC/GA4 后台复制，脚本只做压缩，不改数、不补数。

用法：
  python report.py --creds sa.json --gsc https://vpsdealsradar.com/ --ga4 123456789 --indexed 42
  python report.py --indexed 42 --clicks 7 --clicks-prev 3 --position 18.4 --position-prev 21.9 --active-users 5
  python report.py            # 什么都没有：只列出缺什么
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS_DIR = ROOT / "data" / "reports"
ROUNDS_PATH = ROOT / "data" / "report-rounds.json"

GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="28 天一轮的 GSC / GA4 数字报告")
    parser.add_argument("--creds", help="Google 服务账号 JSON 路径")
    parser.add_argument("--gsc", help="Search Console 属性，例如 https://vpsdealsradar.com/")
    parser.add_argument("--ga4", help="GA4 的【数字属性 ID】（管理→属性设置里那串纯数字），Data API 用它取数")
    parser.add_argument("--ga4-measurement", help="GA4 的【衡量 ID】（G-XXXXXXXXXX），装站上采集用；本脚本不消费，仅记入报告来源")
    parser.add_argument("--fromfile", help="从 JSON 文件读手贴的数字（键名同下面的参数名，可省 --）")
    parser.add_argument("--indexed", type=int, help="GSC 后台「已编入索引」页数（API 不提供，需手贴）")
    parser.add_argument("--clicks", type=float, help="GSC 效果 点击（本 7 天）")
    parser.add_argument("--clicks-prev", type=float, help="GSC 效果 点击（上一个 7 天）")
    parser.add_argument("--position", type=float, help="GSC 效果 平均排名（最近 24 小时）")
    parser.add_argument("--position-prev", type=float, help="GSC 效果 平均排名（前一天）")
    parser.add_argument("--active-users", type=float, help="GA4 近 7 天日均活跃用户")
    parser.add_argument("--next-window", action="store_true",
                        help="不取数，只打印这一期该在后台选哪几个日期区间（照着抄就行）")
    return parser


def print_windows() -> None:
    """把这一期每个数该用的日期区间算出来，供操作者在后台照着选。

    日期是算出来的（今天推 28 天/7 天/昨天），不是从任何地方抄来的。
    """
    today = date.today()
    d = lambda offset: (today - timedelta(days=offset)).isoformat()
    print(f"今天：{today.isoformat()}（以下区间按此推算）\n")
    print("Search Console → 索引 → 网页")
    print(f"  已编入索引：直接读当前页数（索引数是累积量，窗口 {d(28)} → {d(1)} 仅供标注）\n")
    print("Search Console → 效果 → 搜索结果 → 日期范围选「自定义」")
    print(f"  clicks      本期：{d(7)} → {d(1)}     （近 7 天）")
    print(f"  clicks_prev 上期：{d(14)} → {d(8)}    （再往前 7 天）")
    print(f"  position    最近 24 小时：{d(1)} → {d(1)}")
    print(f"  position_prev 前一天   ：{d(2)} → {d(2)}\n")
    print("GA4 → 报告 → 用户（活跃用户）")
    print(f"  active_users 近 7 天：{d(7)} → {today.isoformat()}\n")
    print("填进一个 JSON 文件后运行：")
    print('  python report.py --fromfile numbers.json')
    print('  文件内容：{"indexed": 数字, "clicks": 数字, "clicks_prev": 数字, "position": 数字, "position_prev": 数字, "active_users": 数字}')
    print("  读不到的字段留 null —— 脚本会照实写「读不到」，不会猜。")


def apply_fromfile(args: argparse.Namespace) -> None:
    """支持把数字写进一个 JSON 文件，省得每次拼一长串命令行。

    文件里只放你从后台复制的原值；脚本不改数、不补数。
    例：{"indexed": 42, "clicks": 7, "clicks_prev": 3, "position": 18.4, "position_prev": 21.9, "active_users": 5}
    """
    if not args.fromfile:
        return
    # 用 utf-8-sig：Windows 记事本 / PowerShell 存的 JSON 常带 BOM，别为这个报错。
    payload = json.loads(Path(args.fromfile).read_text(encoding="utf-8-sig"))
    mapping = {
        "indexed": "indexed",
        "clicks": "clicks",
        "clicks_prev": "clicks_prev",
        "position": "position",
        "position_prev": "position_prev",
        "active_users": "active_users",
    }
    for key, attr in mapping.items():
        if getattr(args, attr) is None and key in payload:
            setattr(args, attr, payload[key])


def from_api(args: argparse.Namespace) -> dict:
    """只从官方 API 取数；取不到的字段留 None，绝不用别的东西顶替。"""
    import json as _json

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    # 自己读凭据文件：Google 库的 from_service_account_file 不接受带 BOM 的 JSON，
    # 而 Windows 上用记事本/PowerShell 存出来的 JSON 往往带 BOM，逐字读会直接报错。
    key_path = Path(args.creds)
    try:
        key_info = _json.loads(key_path.read_text(encoding="utf-8-sig"))
    except _json.JSONDecodeError as exc:
        raise SystemExit(f"凭据文件不是合法 JSON：{key_path}（{exc}）") from exc
    if key_info.get("type") != "service_account":
        raise SystemExit(f'凭据文件的 type 不是 service_account，而是 {key_info.get("type")!r}')
    creds = service_account.Credentials.from_service_account_info(key_info, scopes=[GSC_SCOPE, GA4_SCOPE])
    gsc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    today = date.today()

    def rows_range(start: date, end: date) -> list[dict]:
        return gsc.searchanalytics().query(
            siteUrl=args.gsc,
            body={"startDate": start.isoformat(), "endDate": end.isoformat(), "rowLimit": 1},
        ).execute().get("rows", [])

    def pick(data: list[dict], key: str):
        return data[0].get(key) if data else None

    # 口径照第 10 步：点击按 7 天对 7 天；排名按最近 24 小时对前一天；索引按 28 天对 28 天。
    numbers = {
        "clicks": pick(rows_range(today - timedelta(days=7), today - timedelta(days=1)), "clicks"),
        "clicks_prev": pick(rows_range(today - timedelta(days=14), today - timedelta(days=8)), "clicks"),
        "position": pick(rows_range(today - timedelta(days=1), today - timedelta(days=1)), "position"),
        "position_prev": pick(rows_range(today - timedelta(days=2), today - timedelta(days=2)), "position"),
        "indexed_window": [
            (today - timedelta(days=28)).isoformat(),
            (today - timedelta(days=1)).isoformat(),
        ],
        "window": {
            "current": [(today - timedelta(days=7)).isoformat(), (today - timedelta(days=1)).isoformat()],
            "previous": [(today - timedelta(days=14)).isoformat(), (today - timedelta(days=8)).isoformat()],
        },
    }

    if args.ga4:
        ga4 = build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
        report = ga4.properties().runReport(
            property=f"properties/{args.ga4}",
            body={"dateRanges": [{"startDate": (today - timedelta(days=7)).isoformat(), "endDate": today.isoformat()}],
                  "metrics": [{"name": "activeUsers"}]},
        ).execute()
        numbers["active_users"] = (
            int(report["rows"][0]["metricValues"][0]["value"]) if report.get("rows") else 0
        )
    else:
        numbers["active_users"] = None

    # 索引数：GSC API 不暴露，只能由操作者从后台读；没给就留 None。
    numbers["indexed"] = args.indexed
    return numbers


def from_paste(args: argparse.Namespace) -> dict:
    today = date.today()
    return {
        "indexed": args.indexed,
        "clicks": args.clicks,
        "clicks_prev": args.clicks_prev,
        "position": args.position,
        "position_prev": args.position_prev,
        "active_users": args.active_users,
        "window": {
            "current": [(today - timedelta(days=7)).isoformat(), (today - timedelta(days=1)).isoformat()],
            "previous": [(today - timedelta(days=14)).isoformat(), (today - timedelta(days=8)).isoformat()],
        },
        "indexed_window": [
            (today - timedelta(days=28)).isoformat(),
            (today - timedelta(days=1)).isoformat(),
        ],
    }


def missing(args: argparse.Namespace) -> list[str]:
    """说清缺什么才出得了数。缺什么要什么，不自己补。"""
    has_api = bool(args.creds and args.gsc)
    gaps: list[str] = []
    if args.creds and not Path(args.creds).exists():
        gaps.append(f"--creds 指向的文件不存在：{args.creds}")
    # GA4 的两种 ID 容易混：这里在"还没连任何服务"之前就把错的挑出来，
    # 否则要等到建凭据、发请求才报，用户看到的是无关的密码学报错。
    if args.ga4 and not str(args.ga4).isdigit():
        gaps.append(
            f"--ga4 要的是【数字属性 ID】（例如 123456789），你给的是 {args.ga4!r}。"
            "G- 开头的是衡量 ID（装网站采集用），属性 ID 在 GA4 → 管理 → 属性设置"
        )
    if not has_api and not any(
        value is not None
        for value in (args.indexed, args.clicks, args.position, args.active_users)
    ):
        gaps.append("要么给 API 凭据（--creds + --gsc，可选 --ga4），要么直接从后台复制数字贴进来")
    if has_api:
        try:
            import google.oauth2.service_account  # noqa: F401
            import googleapiclient.discovery  # noqa: F401
        except Exception:  # noqa: BLE001
            gaps.append("Python 包：pip install google-auth google-api-python-client")
    if args.indexed is None:
        gaps.append("--indexed：GSC 后台「索引 → 网页 → 已编入索引」的页数（API 不给这个数，必须手贴）")
    return gaps


def fmt(value, digits: int = 0) -> str:
    if value is None:
        return "读不到"
    if isinstance(value, float):
        return f"{value:.{digits}f}" if digits else f"{value:.0f}"
    return str(value)


def format_report(round_no: int, numbers: dict, published: int, source: str) -> str:
    window = numbers["window"]["current"]
    lines = [
        f'第 {round_no} 期｜点击窗口 {window[0]} → {window[1]}｜取数来源：{source}',
        f'索引：{fmt(numbers["indexed"])}（窗口 {numbers["indexed_window"][0]} → {numbers["indexed_window"][1]}）'
        f'｜点击：{fmt(numbers["clicks"])} ← 上 7 天 {fmt(numbers["clicks_prev"])}',
        f'平均排名：{fmt(numbers["position"], 2)} ← 前一天 {fmt(numbers["position_prev"], 2)}',
        f'近 7 天日均活跃用户：{fmt(numbers["active_users"])}｜当期发布 {published} 篇',
    ]
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    if args.next_window:
        print_windows()
        return 0
    apply_fromfile(args)
    gaps = missing(args)
    # 只差 indexed 的话不拦路：先出报告，把那格标成读不到，并说明怎么补。
    blocking = [gap for gap in gaps if not gap.startswith("--indexed")]
    if blocking:
        print("读不到：还缺下面这些输入，缺一个都不出数（不估算、不填占位）：")
        for gap in blocking:
            print("  - " + gap)
        return 2

    if args.creds and args.gsc:
        numbers = from_api(args)
        source = "GSC API + GA4 API" + ("（索引数由操作者手贴）" if args.indexed is not None else "")
    else:
        numbers = from_paste(args)
        source = "操作者从 GSC/GA4 后台复制"

    guides = json.loads((ROOT / "data" / "guides.json").read_text(encoding="utf-8"))
    today = date.today()
    start = today - timedelta(days=28)
    published = len([
        g for g in guides
        if g.get("published", "")[:10] and start.isoformat() <= g["published"][:10] <= today.isoformat()
    ])

    rounds = json.loads(ROUNDS_PATH.read_text(encoding="utf-8")) if ROUNDS_PATH.exists() else []
    round_no = len(rounds) + 1
    text = format_report(round_no, numbers, published, source)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"round-{round_no}-{today.isoformat()}.txt"
    out.write_text(text + "\n", encoding="utf-8")
    rounds.append({
        "round": round_no,
        "ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "numbers": numbers,
        "published_pages": published,
        "file": out.name,
    })
    ROUNDS_PATH.write_text(json.dumps(rounds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(text)
    for gap in gaps:
        print("  ! " + gap)
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
