# BENCH — cheap vps 对 @TOP3 十页对标表

读法：三家的「前十篇」取自 `site:<域名> cheap vps` 的谷歌美区自然结果（`hl=en&gl=us`），
逐个用真实浏览器打开后保存正文再判定。判定只认页面上看得见的东西。

## 一、它们都讲了什么

| 页面主题 | us.ovhcloud.com | digitalocean.com | lowendbox.com |
|---|---|---|---|
| 套餐价格与规格卡 | 有（VPS-1..4 档，价格+内存+带宽） | 有（Droplet 各档单价起点） | 有（逐家优惠贴，含价格与配置） |
| 用「适合谁」来导购 | 有（Ideal for 2–4 players 之类） | 有（按 work load 分档） | 有（按用途/地点/虚拟化分栏） |
| 应用场景页 | 有（Windows / Ubuntu / Plesk / 游戏 / 转售） | 有（WordPress / Linux / cheap web hosting） | 有（FAQ、标签页、地区页） |
| 促销/优惠信息 | 少（页面不谈折扣） | 少 | 有（折扣码、限时价、$1/$2 专题） |
| 更新日期标注 | 无 | 无 | 有（Updated September 2026 等） |
| 第三方对比内容 | 无 | 有 1 篇《Top 10 Vultr Alternatives》 | 有（跨厂商优惠合集） |

## 二、它们全都没有的（这就是缺口）

| 缺口 | 三家十页的实测情况 |
|---|---|
| 可下载走的比价表（CSV/模板） | 三十个页面里，**没有任何一个**提供 csv/xlsx/ods/pdf 下载；lowendbox 的「表格」是 CSS 卡片网格，不是可下载文件 |
| 按单位计价的实例（每 GB 内存 / 每 vCPU / 每 TB 流量） | 三十页里只有 2 处单价数字：digitalocean 一篇对比文里的 `$0.08/GB`、lowendbox 一篇帖子里的 `.02€/GB`。**没有任何一页按「每月每 GB 内存」或「每 vCPU」把套餐横向拆开** |
| 手把手开机器的编号步骤（挑档位→开机器→连上去） | 三十页里只有 ramnode 那篇 Windows 安装文档是真编号步骤（Step 1/2/3）；三家的页面都只有「Learn more / Tutorials」这种指向别处的链接 |

## 三、我能补的独家料从哪取

| 缺口 | 填法 | 数字出处 |
|---|---|---|
| 可下载比价表 | 由 `build.py` 直接生成 `site/downloads/unit-price.csv`，随抓取自动更新 | `data/offers.json`（每次抓公开页得到），每行都带 `source_url` 与 `fetched_at` |
| 按单位计价 | 只用抓到的原文数字做除法：`价格 ÷ 页面写明的 RAM(GB)`、`价格 ÷ 页面写明的 vCPU 数`；页面上没写规格的套餐**不参与**，CSV 里留空 | 同上；公式写在 CSV 的 `unit_price_formula` 列里 |
| 编号开机步骤 | 按厂商公开文档的顺序写成 8 步，每步标注出处 | ramnode 安装文档、OVHcloud VPS 文档入口、DigitalOcean VPS 说明页 |

## 四、已知短板（不许当成已完成）

- **按单位计价的覆盖面**：当前 6 家、20 条抓取记录里，规格与价格在同一抓取块内的只有 5 条（OVHcloud 4 条 + BuyVM 1 条）。IONOS 的 RAM 在 DOM 里与价格相隔超过 11 行且中间夹着促销价，netcup 的规格不在价格行邻域内；本轮的规则选择「宁可留空也不猜」。所以 CSV 里 IONOS 与 netcup 的 `price_per_gb_ram` 是空的——这是**如实留空**，不是漏算。
- **进一步的方向**（未做）：把规格抓取从「价格行邻域」升级为「套餐卡片解析」，或给 IONOS/netcup 单独写卡片选择器；每加一个选择器都必须先跑通 `python scraper.py && python build.py` 并核对 sitemap。

## 五、排序（缺口大的先写）

1. 可下载比价表 —— 三家全缺，且我能用手里数据立刻做出来 → `site/guide/vps-comparison-table-csv`
2. 按单位计价实例 —— 三家全缺，只能对部分套餐计算，页面必须标明哪些算不出来 → `site/guide/how-vps-pricing-works`
3. 编号开机步骤 —— 只有一家有，且是第三方文档 → `site/guide/how-to-buy-and-connect-a-cheap-vps`
