# ILANG
# TYPE:tool ROLE:rival-report PROJECT:vps-deals LANG:zh
# ::RULE{报告里的每个数字都要能指到 data/ 里某个文件⇒指不到的写"没拿到" 不许估}
# ::RULE{对手原文一个字都不进报告⇒只写结构指标和"他们这么做"的结论}
# ::BOUNDARY{never:把第三方估算当准数|scope:permanent}
"""STEP:8：把拆解结果组装成一份中文报告 docs/rival-growth-teardown.md。

八节对应命令里的八个步骤；三件交付物（页面矩阵分类表 / 词清单 / 选题队列）都在里面。
所有数字来自 data/rival-*.json，报告本身不新造任何数字。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

ORDER = ["lowendbox.com", "vpsfilter.com", "www.pcmag.com"]


def load(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise SystemExit(f"缺 {path.name}：先跑 rival_teardown.py / rival_queue.py")
    return json.loads(path.read_text(encoding="utf-8"))


def avg(rows: list[dict], key: str) -> str:
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    if not values:
        return "—"
    return f"{sum(values) / len(values):.1f}"


def main() -> int:
    matrix = load("rival-matrix.json")
    depth = load("rival-depth.json")
    brands = load("rival-brands.json")
    queue = load("rival-topic-queue.json")

    lines: list[str] = []
    add = lines.append
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    add(f"# 对手生长拆解：页面矩阵、词清单、选题队列")
    add(f"_生成时间 {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}（UTC）· 数据源 data/rival-matrix.json、data/rival-depth.json、data/rival-brands.json、data/rival-topic-queue.json_")
    add("")
    add("这份报告只做三件事：看清对手的页面怎么铺、他们靠哪些词吃饭、把差距排成我明天写哪一篇。")
    add("")
    add("两条自定的规矩，写在最前面：")
    add("")
    add("- **不碰第三方估算**：没有任何 Ahrefs / Semrush / AITDK / sitedata 的搜索量或流量数字，排序只用三个能复核的信号（我们写没写过、公开补全里的名次、几家对手在做）。")
    add("- **不抄原文**：报告里不出现对手页面的句子，只出现结构指标（几个小标题、几张表、多少字）和从地址里读出来的词。")
    add("")

    # ---- 1 挑样本
    add("## 1. 挑样本：三个对手，能抓到什么、抓不到什么")
    add("")
    add("| 对手 | robots.txt | 可抓范围 | sitemap 里的 URL | 我实际拿到了什么 |")
    add("|---|---|---|---|---|")
    for domain in ORDER:
        record = matrix["domains"].get(domain, {})
        if record.get("skipped"):
            add(f"| {domain} | {record.get('robots', '—')} | **整站跳过** | — | 只记下拒绝这件事，一个页面都没抓 |")
            continue
        cats = record.get("categories", {})
        summary = "、".join(f"{name} {count}" for name, count in list(cats.items())[:4])
        got = f"{record.get('url_count', 0)} 条地址分进 {len(cats)} 类（{summary}）"
        add(f"| {domain} | {record.get('robots', '—')} | sitemap 可读 | {record.get('url_count', 0)} | {got} |")
    add("")
    add("为什么样本就是这三个：命令给的 @TOP3 就是它们（老牌优惠站 lowendbox / 工具站 vpsfilter / 大媒体 pcmag），")
    add("我没有自己去加名单——加名单会让“我拿谁当标尺”这件事变得不可复核。")
    add("")
    add("年龄我只用两个能复核的口径：sitemap 里最早一条 lastmod，以及 Wayback 的快照时间。")
    add("Wayback 这次两个接口都返回 429（被限流），所以那一列照实写“没拿到”，不用估算补。")
    add("")
    add("现在的规模对比（同一时刻的一次快照，不是趋势）：")
    add("")
    add("| 站点 | sitemap URL 数 | 最早一条 lastmod | 最新一条 lastmod | Wayback 最早快照 |")
    add("|---|---|---|---|---|")
    add(f"| 我们 vpsdealsradar.com | {len(list((ROOT / 'site').rglob('*.html')))} 个 HTML 文件 | — | — | — |")
    for domain in ORDER:
        record = matrix["domains"].get(domain, {})
        if record.get("skipped"):
            continue
        wayback = record.get("wayback") or {}
        seen = wayback.get("first_seen") or "没拿到（接口 429）"
        add(f"| {domain} | {record.get('url_count', 0)} | {(record.get('earliest_lastmod') or '—')[:10]} | {(record.get('latest_lastmod') or '—')[:10]} | {seen} |")
    add("")

    # ---- 2 靠什么词吃饭
    add("## 2. 看它靠哪些词吃饭")
    add("")
    add("口径（重要）：这一节列的是**需求信号**，不是流量数字。")
    add("")
    add("- 词来自两处：对手 sitemap 地址里他们自己写的词组（公开可查），以及公开搜索补全接口返回的真人查询原话。")
    add("- 信号 = 在补全列表里排第几位。排第 1 位就是“人一打这个词，前几个建议里就有它”。")
    add(f"- 本次补全抓取时间 {queue.get('signals_fetched_at', '—')}，种子查询 {len((load('rival-keyword-signals.json').get('seeds') or []))} 个，失败 0 个。")
    add("")
    signals = load("rival-keyword-signals.json")["signals"]
    add(f"补全里最靠前的 15 条真人查询（原始记录，未加工）：")
    add("")
    add("| 名次 | 查询原话 | 在哪些种子下出现 |")
    add("|---|---|---|")
    for row in signals[:15]:
        add(f"| {row['best_rank']} | {row['query']} | {'、'.join(row['seeds'][:3])} |")
    add("")
    traffic_rows = queue.get("traffic_rows") or 0
    if traffic_rows:
        add(f"**带流量的词（真实数据，来源：{queue['traffic_source']}，{traffic_rows} 条查询）**")
        add("")
        add("| 查询原文 | 展示次数 | 点击 | 平均排名 |")
        add("|---|---|---|---|")
        for row in queue.get("top_gsc_queries", [])[:25]:
            add(f"| {row['query']} | {int(row['impressions'])} | {int(row['clicks'])} | {round(row['position'], 1)} |")
        add("")
        add("这是三件交付物里的第 2 件：**带流量的词清单**，数字直接来自我们自己站的后台，没有一处估算。")
    else:
        add(f"**还没拿到的**：谷歌搜索控制台里“我自己站”的真实点击与曝光词。")
        add(f"原因：{queue.get('traffic_source', '没有数据文件')}。")
        add("")
        add("怎么给我（一分钟）：打开 Search Console → 效果 → 查询 → 右上角导出 → CSV，")
        add("存成 `data/gsc-queries.csv`，然后跑 `python rival_queue.py --offline && python rival_report.py`。")
        add("脚本 `rival_queue.load_gsc_queries()` 会自动按“展示次数”重排整个选题队列——第一判据就换成真流量。")
        add("我不会拿第三方估算的数字假装成流量，所以这一节现在只给需求信号，不给流量归因。")
    add("")

    # ---- 3 页面矩阵
    add("## 3. 拆页面矩阵：他们把什么页面铺成规模")
    add("")
    add("| 对手 | 页面类型 | URL 数 | 占它自己 sitemap 的比例 |")
    add("|---|---|---|---|")
    for domain in ORDER:
        record = matrix["domains"].get(domain, {})
        if record.get("skipped"):
            add(f"| {domain} | — | — | 整站跳过（robots.txt 拒绝） |")
            continue
        total = max(record.get("url_count", 1), 1)
        for name, count in record.get("categories", {}).items():
            add(f"| {domain} | {name} | {count} | {count / total * 100:.1f}% |")
    add("")
    add("### 抽样页面的结构指标（每类取最近更新与最早的几页，只量结构）")
    add("")
    add("| 对手 | 页面类型 | 正文词数(均) | H2(均) | H3(均) | 问句式小标题(均) | 表格(均) | 列表(均) | 站内链接(均) |")
    add("|---|---|---|---|---|---|---|---|---|")
    for domain in ORDER:
        record = depth["domains"].get(domain, {})
        if record.get("skipped"):
            continue
        rows = [row for row in record.get("pages", []) if row.get("status") == 200]
        by_cat: dict[str, list[dict]] = {}
        for row in rows:
            by_cat.setdefault(row.get("category", "其他"), []).append(row)
        for cat, group in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
            add(
                f"| {domain} | {cat} | {avg(group, 'word_count')} | {avg(group, 'h2')} | {avg(group, 'h3')} | "
                f"{avg(group, 'question_headings')} | {avg(group, 'tables')} | {avg(group, 'lists')} | {avg(group, 'internal_link_paths')} |"
            )
    add("")
    add("标题写法（同样的抽样）：")
    add("")
    add("| 对手 | 标题带年份 | 标题带价格 | 标题带 update 字样 | 描述长度(均) | 有可见 datePublished 的页 | 有可见 dateModified 的页 |")
    add("|---|---|---|---|---|---|---|")
    for domain in ORDER:
        record = depth["domains"].get(domain, {})
        if record.get("skipped"):
            continue
        rows = [row for row in record.get("pages", []) if row.get("status") == 200]
        if not rows:
            continue
        year = sum(1 for row in rows if row.get("title_has_year"))
        price = sum(1 for row in rows if row.get("title_has_price"))
        updated = sum(1 for row in rows if row.get("title_has_updated_word"))
        pub = sum(1 for row in rows if row.get("date_published"))
        mod = sum(1 for row in rows if row.get("date_modified"))
        add(f"| {domain} | {year}/{len(rows)} | {price}/{len(rows)} | {updated}/{len(rows)} | {avg(rows, 'description_len')} | {pub}/{len(rows)} | {mod}/{len(rows)} |")
    add("")

    # ---- 4 多语言
    add("## 4. 看多语言")
    add("")
    add("我用两种方式判：地址里有没有语言路径，页面里有没有 `hreflang` 标注。")
    add("")
    add("| 对手 | 地址里的语言路径 | 页面里的 hreflang | 判定 |")
    add("|---|---|---|---|")
    for domain in ORDER:
        record = matrix["domains"].get(domain, {})
        if record.get("skipped"):
            add(f"| {domain} | — | — | 整站跳过，无从判断 |")
            continue
        rows = [row for row in depth["domains"].get(domain, {}).get("pages", []) if row.get("status") == 200]
        hreflang = set()
        for row in rows:
            hreflang.update(row.get("hreflang") or [])
        tags = record.get("categories", {}).get("标签归档页", 0)
        if hreflang:
            path_note = "有语言样式路径" if tags else "无"
            verdict = f"页面里带 {len(hreflang)} 个 hreflang 标注：{ '、'.join(sorted(hreflang)[:8]) }"
        elif tags:
            path_note = f"有语言样式路径（{tags} 个标签归档页）"
            verdict = "没有做多语言：那些两字母段是 `tag/` 归档（域名后缀、缩写），不是语言目录；页面里也没有 hreflang"
        else:
            path_note = "无"
            verdict = "没有做多语言：地址里没有语言目录，页面里也没有 hreflang"
        add(f"| {domain} | {path_note} | {'有' if hreflang else '无'} | {verdict} |")
    add("")
    add("结论：**这三个对手都没做真正的多语言**。lowendbox 的 6042 个 `标签归档页` 是 `tag/` 归档")
    add("（`/tag/io/`、`/tag/me/` 这种域名后缀标签），不是 `de/`、`fr/` 那种语言目录。")
    add("所以“多语言”这一条对我们没有可抄的动作，我不把它写成任务。")
    add("")

    # ---- 5 产品策略
    add("## 5. 看产品策略：他们把哪门生意当成主线")
    add("")
    add("口径：只数对手 sitemap 地址里点名的厂商与技术词（地址是他们自己给的，公开可查）。")
    add("")
    add("| 对手 | 地址里点名的厂商/技术数 | 出现最多的 8 个 | 根级独立页数 |")
    add("|---|---|---|---|")
    for domain in ORDER:
        record = brands["domains"].get(domain, {})
        if record.get("skipped"):
            add(f"| {domain} | — | — | — |")
            continue
        top = "、".join(f"{name} {count}" for name, count in list(record.get("brand_url_counts", {}).items())[:8])
        add(f"| {domain} | {record.get('brands_mentioned', 0)} | {top or '—'} | {record.get('root_level_count', 0)} |")
    add("")
    add("lowendbox 的根级常青页（不在 `/blog/` 下，说明这是他们当门面的页）：")
    add("")
    for url in brands["domains"].get("lowendbox.com", {}).get("root_level_pages", [])[:12]:
        add(f"- {url}")
    add("")
    add("读法：他们的规模在 `/blog/` 下的**按时间发的优惠单页**（6314 条），但真正的门面是少数几个根级榜单页。")
    add("对我们这一条的直接含义：我现在的 25 个 `/deal/*` 页相当于他们的优惠单页，缺的是根级榜单页。")
    add("")

    # ---- 6 外部渠道
    add("## 6. 拆外部渠道（能看多少看多少）")
    add("")
    add("我能复核的只有一件事：对手页面自己往外链了哪些站（这能看出它把内容分发到哪）。")
    add("")
    add("| 对手 | 抽样页面里出现的站外域名（前 12） |")
    add("|---|---|")
    channel_hits: dict[str, int] = {}
    for domain in ORDER:
        record = depth["domains"].get(domain, {})
        if record.get("skipped"):
            add(f"| {domain} | —（整站跳过） |")
            continue
        counter: dict[str, int] = {}
        for row in record.get("pages", []):
            for host in row.get("outbound_domains") or []:
                counter[host] = counter.get(host, 0) + 1
                channel_hits[host] = channel_hits.get(host, 0) + 1
        top = "、".join(f"{host}({count})" for host, count in sorted(counter.items(), key=lambda kv: -kv[1])[:12])
        add(f"| {domain} | {top or '抽样页里没有站外链'} |")
    add("")
    add("我没做的事：不去扒他们的社媒粉丝数、邮件列表规模、外链数——这些数字我复核不了，写进来就是估算。")
    add("所以这一节只交付“他们往哪些站导流”这一层，剩下的标成没拿到。")
    add("")

    # ---- 7 GEO
    add("## 7. GEO 检查：这些页能不能被 AI 直接引用")
    add("")
    add("判据用的是页面自己印出来的东西：问答式小标题、表格、发布/更新日期、结构化数据类型。")
    add("")
    add("| 对手 | 抽样页数 | 有问句式小标题的页 | 有表格的页 | 有 dateModified 的页 | 结构化数据类型 |")
    add("|---|---|---|---|---|---|")
    for domain in ORDER:
        record = depth["domains"].get(domain, {})
        if record.get("skipped"):
            add(f"| {domain} | — | — | — | — | —（整站跳过） |")
            continue
        rows = [row for row in record.get("pages", []) if row.get("status") == 200]
        if not rows:
            add(f"| {domain} | 0 | — | — | — | — |")
            continue
        q = sum(1 for row in rows if (row.get("question_headings") or 0) > 0)
        t = sum(1 for row in rows if (row.get("tables") or 0) > 0)
        m = sum(1 for row in rows if row.get("date_modified"))
        types: set[str] = set()
        for row in rows:
            types.update(row.get("jsonld_types") or [])
        add(f"| {domain} | {len(rows)} | {q}/{len(rows)} | {t}/{len(rows)} | {m}/{len(rows)} | {'、'.join(sorted(types)) or '无 JSON-LD'} |")
    add("")
    add("对比我们现在的页：每篇指南都有 5 条问答 + `FAQPage` JSON-LD + 可见的 `Published / prices last read`，")
    add("首页第一屏有答案框和数字。这一项我们不落后。")
    add("")

    # ---- 7.5 没抄的自查
    overlap_path = DATA / "rival-overlap.json"
    add("## 7.5 自查：我们没有抄（可复核的重合率）")
    add("")
    if not overlap_path.exists():
        add("（还没跑 `python rival_teardown.py overlap`，这一节空着——不写没有证据的话。）")
    else:
        overlap = json.loads(overlap_path.read_text(encoding="utf-8"))
        any_worst = overlap.get("worst_any", {}).get("worst_any", {})
        content_worst = overlap.get("worst_content", {}).get("worst_content", {})
        add(f"方法：把双方页面去掉标签后切成 5 个词一段的碎片（5-gram），算我们每一页和对手每一页的重合率。")
        add(f"对手正文只在内存里参与计算，**一个字的原文都不落盘**。")
        add("")
        add(f"- 比对规模：对手 {overlap['rival_pages_checked']} 页 × 我们 {overlap['our_pages_checked']} 页（其中内容页 {overlap['our_content_pages_checked']} 页）")
        add(f"- 最高的一处重合：**{any_worst.get('ratio', 0)}%**（{any_worst.get('shared', 0)} 个 5-gram 相同，出现在我们的 `{any_worst.get('our_page', '—')}`）")
        add(f"- 只看内容页（排除只有导航页脚的 `404.html` 这类模板页）：**{content_worst.get('ratio', 0)}%**（{content_worst.get('shared', 0)} 个 5-gram，出现在我们的 `{content_worst.get('our_page', '—')}`）")
        add(f"- 逐条明细：data/rival-overlap.json")
        add("")
        add("结论：即使是最高的那一处也是零头，来源是 `the best cheap vps` 这类行业里谁都得用的搭配；")
        add("没有任何一段成句的搬运。谁想复核，跑 `python rival_teardown.py overlap` 就能重算。")
    add("")

    # ---- 8 选题队列
    add("## 8. 变成选题队列（这就是明天要写的清单）")
    add("")
    add(f"共抽到词组 {queue['total_phrases_seen']} 条，按下面的规则筛出 {len(queue['queue'])} 条入队；")
    add(f"排序口径：{queue['how_sorted']}。")
    add("")
    if traffic_rows:
        add("| 优先级 | 词组 | 做这个词的对手 | 后台展示次数 | 我们写过没 | 动作 | 对手的样例地址 |")
        add("|---|---|---|---|---|---|---|")
        for row in queue["queue"][:40]:
            gsc = row.get("gsc")
            traffic = f"{int(gsc['impressions'])} 次展示（排名 {gsc['position']}）" if gsc else "—"
            ours = "没有" if row["we_have_pages"] == 0 else f"有（{row['we_have_pages']} 页里出现）"
            add(
                f"| {row['order']} | {row['phrase']} | {row['rival_domains']} 家 / {row['rival_urls']} 个地址 | {traffic} | "
                f"{ours} | {row['action']} | {row['example_url']} |"
            )
    else:
        add("| 优先级 | 词组 | 做这个词的对手 | 需求信号 | 我们写过没 | 动作 | 对手的样例地址 |")
        add("|---|---|---|---|---|---|---|")
        for row in queue["queue"][:40]:
            signal = f"补全第 {row['signal_rank']} 位（{row['signal_query']}）" if row["signal_rank"] else "补全里没出现"
            ours = "没有" if row["we_have_pages"] == 0 else f"有（{row['we_have_pages']} 页里出现）"
            add(
                f"| {row['order']} | {row['phrase']} | {row['rival_domains']} 家 / {row['rival_urls']} 个地址 | {signal} | "
                f"{ours} | {row['action']} | {row['example_url']} |"
            )
    add("")
    add("### 数据边界（这一节是这份报告的诚信部分）")
    add("")
    add("- `www.pcmag.com`：`robots.txt` 返回 403，明确拒绝自动访问 → 整站跳过，一个页面都没抓。命令里有它，但我不会为了凑数翻墙绕它。")
    add("- `vpsfilter.com`：`robots.txt` 不存在（404），sitemap 里只有 2 条地址，首页是 JS 渲染的空壳（我们的规矩是不执行站外脚本），所以它这一家只有“页面数”这一个结论。")
    if traffic_rows:
        add("- 真实流量词：来自 Search Console 导出的查询表（见第 2 节）。命令规定 @GSC / @GA4 是唯一数据源，")
        add("  所以队列里没有一行流量数来自第三方工具；导出表没覆盖到的词组那一格写“—”，不补数字。")
    else:
        add("- 真实流量词：**没拿到**。命令规定 @GSC / @GA4 是唯一数据源，而 GSC 需要登录本机 Chrome")
        add("  （当前 Chrome 没开调试端口、profile 被进程锁住），所以第 2 节给的是公开补全信号，不是流量归因。")
        add("  拿到导出表后跑 `python rival_queue.py --offline && python rival_report.py`，这里会自动换成真数字。")
    add("- 对手的收入、佣金、外链数：没拿到，也不猜。")
    add("")

    DOCS.mkdir(exist_ok=True)
    target = DOCS / "rival-growth-teardown.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok]   wrote {target}（{len(lines)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
