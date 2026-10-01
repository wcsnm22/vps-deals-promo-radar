# 为什么这三家排在我们前面 —— 只看页面上看得见的结构

本文只读本机已保存的文件，不联网。每一行的判断都在「出处」列写明是哪个文件。

## 0. 口径与样本

| 项 | 内容 | 出处 |
|---|---|---|
| 对标的三家 | `us.ovhcloud.com/vps/cheap-vps/`、`digitalocean.com/solutions/vps-hosting`、`lowendbox.com/best-cheap-vps-hosting-updated-2020/` | `pages/visits.json`（第 2/3/4 条 `finalUrl`、`title`） |
| 这三页的本地快照 | `pages/page_02.html`（OVH）、`pages/page_03.html`（DO）、`pages/page_04.html`（LEB） | 三者字节数与 `pages/visits.json` 记录一致（358884 / 186227 / 142497） |
| 正文纯文本 | `pages/text_2.txt`、`pages/text_3.txt`、`pages/text_4.txt` | 目录清单 |
| 排名数字 | 本文出现的「第 2/3/4 名」只是本地浏览器抓取名单里的序号，**不是**我在 SERP 文件里读到的排名 | `cheap-vps-top10-audit.md` 第 5–16 行（作者已声明排名来自本机 Chrome 渲染的 DOM，且剔除广告） |
| 我们的页面 | `site/guide/` 下 14 个 html（3 个常青页 + 4×`csv-*` + 4×`unitprice-*` + 3×`steps-*`） | 目录清单；`site/sitemap.xml` 收录了其中全部 14 个 |

---

## 1. 表一：它这篇为什么排前面

| 对标站 / 文件 | 标题写法 | 第一屏怎么组织 | 表格 / 清单 / 比较维度 | 更新日期 | 内链结构 | 页面类型 |
|---|---|---|---|---|---|---|
| **lowendbox**<br>`pages/page_04.html`<br>`pages/text_4.txt` | 标题里塞了年份与更新月：「Best Cheap VPS Hosting - Updated **September 2026**」（`<title>`；`text_4.txt` 第 1、28 行）。搜索结果摘要里也带得出 `Updated September 2026`（`pages/visits.json` 第 147–151 行 `dates` 数组） | H2 之后立刻是一段**场景导语**：「Perhaps you're currently on a shared hosting environment and you are looking to move your websites to a VPS for better performance? Or maybe you're a developer or hobbyist…」（`text_4.txt` 第 29 行）。紧接着第二段给**入选标准**：「Criteria for providers mentioned in this post include overall reputation within our community, reported user experiences, and provider's attentiveness to reported issues.」（`text_4.txt` 第 31 行）——先讲怎么选，再上名单 | 没有 `<table>`（`page_04.html` 内 `<table` 计数 0），但每个供应商是一套**固定七件套**：H2「Best Cheap VPS Hosting: 品牌名」→ 星级『LowEnd Score:⭐⭐⭐⭐⭐』→ 品牌散文 → 配置清单（`1x vCPU Core` / `2GB RAM` / `30GB …` / `1 Dedicated IPv4 Address` …）→ 价格 `Pricing: $2.00/month (75% off)` → 折扣码 `Coupon Code: 2LEB` → `[ ORDER HERE ]`（`text_4.txt` 第 32–45、46–60、61–75 行）。同一形状可逐家横向读 | 有，且**同一页出现三个不同月份**：`Updated September 2026` / `updated as of August 2026` / `Updated July 2026`（`text_4.txt` 第 28、29、108、110 行）。JSON-LD 亦带 `"datePublished":"2025-04-25T18:07:19+00:00"`、`"dateModified":"2026-09-14T18:06:39+00:00"`（`page_04.html` 内 `application/ld+json`） | 116 个带 href 的 a 标签，其中 17 个站内路径、15 个唯一路径，覆盖 `/category/virtual-servers/`、`/category/tutorials/`、`/virtual-private-server-frequently-asked-questions-vps-faq/`、`/hosting-offers-archive/`、`/blog/1-vps-1-usd-vps-per-month/`；`canonical` 指向自身（`page_04.html`） | 列表页 / 导购清单（榜单式长文），不是文档页 |
| **ovhcloud**<br>`pages/page_02.html`<br>`pages/text_2.txt` | 标题只有 13 个字符：「Low-cost VPS」（`<title>`）。**不含年份、不含价格**。把「关键词同义改写」写进 H1 与 meta description：「Enjoy a low-cost, high-performance VPS with OVHcloud. 1vCore, 2 GB RAM, 20 GB SSD, 100 Mbps. Ideal for small businesses and personal projects.」（`page_02.html` 的 `meta[name=description]`） | H2「VPS 1: A Low-cost VPS, with Uncompromised Quality」（`text_2.txt` 第 433 行）+ H3「Combining high performance with low prices」（第 437 行）之后，第一屏给的是**三条卖点清单**（不是段落）：「Your server at a competitive price / Full admin access / Unlimited ingress and egress traffic*」（第 434–436 行），然后才是一段厂商自述（第 438 行） | 没有 `<table>`（`<table` 计数 0），用 **81 个 `<ul>`** 承载。真正的比较维度是套餐卡片清单：VPS-1/2/3 每张卡固定列出 `vCores / GB RAM / GB SSD NVMe / Daily backup / Unlimited traffic / Mbps public bandwidth` 六项（`text_2.txt` 第 456–488 行）。另有 **8 条 FAQ 用 H3 切成问句**：`What is a VPS?`、`Why choose a low-cost VPS?`、`What is the difference between a cheap VPS and a VPS Pro?`、`What is the difference between a VPS and an SSD VPS?`…（`text_2.txt` 第 490–505 行） | **无**。整份 HTML 里 `Updated`、`Last modified`、`datePublished`、`20xx-xx-xx` 的出现次数都是 0 | 192 个带 href 的 a 标签，**全部**是绝对 URL，站内路径覆盖 `/vps/`、`/vps/os/vps-ubuntu/`、`/vps/os/vps-windows/`、`/vps/vps-reseller/`、`/vps/dayz-vps/`、`/vps/uc-vps-game/`、`/learn/what-is-hypervisor/`、`/bare-metal/prices/` 等；`canonical` = 自身（`page_02.html`） | 产品/落地页（厂商自营），兼 FAQ 块 |
| **digitalocean**<br>`pages/page_03.html`<br>`pages/text_3.txt` | 标题把**价格写进标题**：「VPS Hosting Plans - **Starting at $4/mo** \| DigitalOcean」（`<title>`）。description 给的是速度承诺 + 配置枚举：「Spin up your choice of VPS hosting in **55 seconds**. Basic, General Purpose, CPU-Optimized, or Memory-Optimized configurations available.」（`page_03.html` 的 `meta[name=description]`） | H1「VPS hosting on DigitalOcean」下一句就定性：『DigitalOcean provides a wide range of VPS hosting options suited to every need.』，紧跟一个 `Get Started` 按钮；再往下 H2「VPS hosting options」**用一整段说明怎么挑**：「You can choose between shared CPU offerings and dedicated CPU offerings based on your anticipated usage. Learn more about how to select the right VPS offering for your use case.」（`text_3.txt`，H1 之后） | 没有 `<table>`（`<table` 计数 0），用**分类树**当比较维度：H2『Shared CPU Droplets』→ H3『Regular / Premium Shared CPU』；H2『Dedicated CPU Droplets』→ H3『General Purpose / CPU-Optimized / Memory-Optimized / Storage-Optimized』（`page_03.html`，全部 h2/h3 列表）。每一类都带**「起点价 + 规格 + 适用负载」三元组**，例如『General Purpose Droplets start at $63/month for 8GB memory, 25GB SSD, and 4TB transfer』、『CPU-Optimized … start at $42/month for 4GB memory…』、『ideal for workloads including medium-to-high-traffic web servers, eCommerce sites…』（`pages/text_3.txt` 第 126、128 行；`pages/evidence.json` 第 49–52 行 `conversions` 字段亦逐条收录同句） | **无**。`Updated`、`datePublished`、`Last updated` 计数均为 0（`page_03.html` 内出现的 63 处 `20xx-xx-xx` 全是定价/区域无关的页脚与脚本片段，正文无更新日） | 201 个带 href 的 a 标签，含 `/products/droplets/resources/choose-plan/`、`/products/`、`/reference/api` 等站内路径；`canonical` = 自身。页面本身处在 Solutions→产品→文档的导航树里（顶部 Products/Solutions/Developers/Partners 四组 H3，`page_03.html`） | 产品方案页 / 文档式导购页，末尾带 FAQ |

---

## 2. 表二：我那篇差在哪

对照的是我们自己的三个常青页加三个抽样的按日快照页。

| # | 我们的页面 / 文件 | 我们实际写的是（原文） | 对照谁 | 缺的具体是哪一块 |
|---|---|---|---|---|
| 1 | `site/guide/how-vps-pricing-works.html` 第 39 行 | 第一屏第一句就是结论：「Cheapest RAM per unit today is IONOS VPS XXL+ at 0.8333 USD per GB (20.0 USD / 24 GB) — computed only from numbers the provider published.」 | DO `text_3.txt`（H1 后先讲「怎么按用量挑 shared/dedicated CPU」，再给价） | **第一屏只有结论、没有场景**。没有一处写「你是什么人、什么项目该看这一页」，也没有 OVH 那种「Ideal for …」的适用人群句 |
| 2 | 同上，第 42 行 | 章节顺序是：`Why the headline price cannot rank plans` → `The three inputs a per-GB number needs` → `What this site does not do`。全部是**方法论与自我约束** | LEB `text_4.txt` 第 31 行先给「入选标准」，第 32 行起才上名单；DO 用「Shared / Dedicated → 四小类」铺开 | **没有比较维度**。整页只有「每 GB 内存」一个维度，没有并发/流量/备份/面板/操作系统这些可以横向看的列；DO 那一页有 4 大类 × 4 小类的分档维度 |
| 3 | 同上，第 42 行 | 只有 6 个 `<h2>` + 5 个 `<h3>`；H3 全部是 FAQ 问句，正文段落是「两句话一段」的抽象论述，全文 0 个 `<table>`、1 个 `<ul>`、1 个 `<ol>` | OVH `text_2.txt` 第 490–505 行：8 个 H3 问句，每个问题下是一整段成体系的回答；DO `text_3.txt` 第 136–149 行：5 个问句，第 137 行『What is VPS?』从「virtual machine that mimics…」讲到「much more cost-effective… than buying, configuring, and maintaining physical servers」 | **没有把一个问题拆成几段**。OVH 的『What is a VPS?』（第 491 行）是一整段从定义讲到「介于共享主机和物理机之间」；我们对应的问句只有一句「The lowest tracked monthly price is 2 USD…」就算答完 |
| 4 | `site/guide/unitprice-2026-10-01-1.html` 第 39 行 | 第一屏是「结论 + 三张 SVG 图」：「Hostwinds: cheapest RAM per unit is … 3.3592 USD per GB」后面直接挂 `/assets/per-gb-cheapest.svg`、`/assets/per-gb-hostwinds.svg`、`/assets/monthly-vs-ram-hostwinds.svg` | LEB 用「品牌卡 + 星级 + 散文 + 配置清单 + 价格 + 折扣码」的**七件套**把每家切成一块 | 我们有数据可视化，**但没有「一家一块、形状一致」的卡片节奏**。读者要横向比 Hostwinds 的 10 个套餐，只能读我们那张表的 5 列，看不到容量/带宽/备份等别的维度 |
| 5 | `site/guide/vps-comparison-table-csv.html` 第 39、42 行 | 第一屏写「The CSV hands over the table itself.」，正文花整节解释列名：`provider, plan, price, currency, ram_gb, vcpu, disk_gb, price_per_gb_ram, price_per_vcpu, unit_price_formula, source_url, fetched_at` | DO 把价格三元组直接写进分类小节；OVH 把 VPS-1..3 的六项规格直接铺在卡里 | **把最能打的东西（价格表）藏在第二屏之后**：第一屏没有一行具体价格数字，价格表要先点进页面往下翻、或者去下载 CSV 才看得到。三家对标站在第一屏就至少给了一个价格锚点（OVH `Starting at $4.54 /month`，DO `Starting at $4/mo`，LEB `Pricing: $2.00/month`） |
| 6 | 全部 14 个 `site/guide/*.html` | 每页只有 2–3 个站内链接，且全是资产或下载文件（`/assets/favicon.svg`、`/assets/style.css`、`/downloads/unit-price.csv`）；快照页之间**没有任何一页互相链接** | LEB 116 个 a 标签 / 15 个唯一站内路径；OVH 192 个 a 标签，站内覆盖 8 个 VPS 子页；DO 201 个 a 标签 | **内链结构是散的**。我们 14 个同题材页面靠 `sitemap.xml` 串起来，页面上彼此不指路；对标站的每篇都是从列表页/产品页/FAQ 页可达的节点 |
| 7 | `site/guide/how-vps-pricing-works.html` 第 27 行 | JSON-LD 里只有 `"datePublished":"2026-10-01"`，**没有 `dateModified`**，正文与页脚也没有 `Updated on …` 字样（`<time>` 计数 0） | LEB：正文三处月份 + JSON-LD 同时带 `datePublished` 与 `dateModified` | **更新日期只有机器能看、人看不到**。LEB 的三个月份一个在标题、一个在首段、一个在内链锚文本里，是肉眼可见的复访理由；我们的日期只在 HTML head 里 |
| 8 | `site/guide/how-to-buy-and-connect-a-cheap-vps.html` 第 39、42、45 行 | 有 8 步编号（`<ol>`），第一屏写「Eight numbered steps from picking the plan to logging in, each sourced to provider documentation.」；来源列了 RamNode / OVHcloud / DigitalOcean 三条外链 | OVH 与 DO **都没有**编号步骤，它们只有 FAQ + 指向别处的链接 | 这一步我们不缺，反而是我们独有的（见第 4 节）。但它同样落在「第一屏只有承诺、没有一步具体动作」的模式里：8 步要往下滚才看到 |
| 9 | `site/guide/csv-2026-09-30-1.html` 第 39、42 行 | 第一屏：「5 tracked netcup plans with a published price, 0 of them carry a per-GB figure.」表里 netcup 五行 `RAM` 列全部写 `<span class="muted">not published</span>`、`Price per GB` 列写 `-` | LEB 对每家给的是**完整可下单的一手信息**（价格 + 优惠码 + `[ ORDER HERE ]`）；DO 给「起点价 + 规格 + 适用负载」 | **快照页对读者是「负结论」**。「0 of them carry a per-GB figure」对我们自己是在守诚实线（`AGENTS.md` 的 `BOUNDARY{never:编价格}`），但页面上没有任何一条能让人拿走的可比较信息 |

---

## 3. 表三：我该学它哪一点

只写结构和角度，每条注明学的是哪一家的哪一处。序号对应表二。

| # | 可复制项 | 学哪一家的哪一处结构 |
|---|---|---|
| 1 | 第一屏改成「结论 + 适用人群」两句：先给人话结论，再补一句「什么样的项目/预算该看这页」。 | digitalocean `text_3.txt`：H1 后紧接『DigitalOcean provides a wide range of VPS hosting options suited to every need.』再上 `Get Started`（第 111–113 行）；分类小节里每类都以 `ideal for …` 收尾，如第 126 行『… are ideal for workloads including medium-to-high-traffic web servers, eCommerce sites…』、第 128 行 CPU-Optimized 的同类句 |
| 2 | 在按 GB 计价之外，加一条**横向比较轴**：把「每 GB 价格」和「带宽 / 备份 / 是否含 Windows 授权 / 控制面板」并排成可比较的列。 | OVH `text_2.txt` 第 456–488 行：VPS-1/2/3 每张卡固定六项规格，横向对齐 |
| 3 | 把长答案按「一问一节」切开：每个 H3 一个问题，答案写满一段（定义 → 对比 → 限制），而不是一句话结论。 | OVH `text_2.txt` 第 490–505 行的 8 个 FAQ H3；DO `text_3.txt` 第 136–149 行『Frequently Asked Questions (FAQ)』下的 5 问 |
| 4 | 给每家/每个维度做「形状一致的一块」：固定字段、固定顺序，让读者扫三行就能比。 | lowendbox `text_4.txt` 第 32–45 行起的「品牌名 → 星级 → 散文 → 配置清单 → 价格 → 折扣码 → 按钮」七件套 |
| 5 | **把价格表提到第一屏之前**：第一屏至少出现一个具体价格锚点（例如「最低 $2/月，25 个套餐可算」并直接给 Top-3 行），再放解释性文字。 | OVH `text_2.txt` 第 457 行 `Starting at $4.54 /month`；DO 标题 `Starting at $4/mo`；LEB `text_4.txt` 第 42 行 `Pricing: $2.00/month (75% off)` |
| 6 | **把 14 个 guide 页面互相串起来**：常青页底部列出对应的 date 快照页；每个快照页回指常青页与 `/guide` 索引；再加一条「按厂商」聚合页。 | lowendbox `page_04.html`：站内链接覆盖 `/category/virtual-servers/`、`/virtual-private-server-frequently-asked-questions-vps-faq/`、`/hosting-offers-archive/`、`/blog/1-vps-1-usd-vps-per-month/` 四个不同层级；OVH `page_02.html`：从本页可达 8 个 VPS 子页 |
| 7 | **给出人眼可见的日期模块**：在 H1 下加一行 `Updated 2026-10-01 · <下一次抓取时间>`，并同步补 JSON-LD 的 `dateModified`。 | lowendbox：正文三处月份（`text_4.txt` 第 28、29、108 行）+ JSON-LD `datePublished`/`dateModified` 双字段（`page_04.html`） |
| 8 | 保留我们已有的编号步骤，但**把第 1 步提到第一屏**，并把「一共 8 步」改成「前 3 步可先做完」。 | 这一条学的是我们自己的 `how-to-buy-and-connect-a-cheap-vps.html` 第 42 行的 `<ol>`，借 DO 的「先给最短路径 + 一个按钮」顺序（`text_3.txt`：H1 → 一句话 → `Get Started`） |
| 9 | 给「算不出来」的页面配一个可带走的替代答案：既然 netcup 没有 RAM，就补一列「已公布的 vCPU / 价格」，让读者至少能带走一个能比的数。 | OVH 拿不到每 GB 数据时用的是「列出全部可公布规格」而不是留空；LEB 对每家都给价格与配置清单（`text_4.txt` 第 49–58 行） |
| 10 | 结论段落**标注来源链接**：每个数字旁边直接给该供应商自己的公开价目页，不用等页面底部的 Sources 汇总。 | OVH 的套餐卡每张都带 `Configure` 动作指向订购流程（`text_2.txt` 第 459、470、481 行）；LEB 每一家后面都是 `[ ORDER HERE ]`（`text_4.txt` 第 44 行） |

---

## 4. 我们没有抄

这一节列的是**我核对过的、我们页面上与对标站不重合的具体做法**，以及核对方式。结论是：`site/guide/` 下 14 个页面与这三页对标 HTML 的文字**没有任何 5-gram 重合**。

### 4.1 机器核对：5-gram 与 8-gram 比对

核对方式：把 `pages/page_02.html`、`pages/page_03.html`、`pages/page_04.html` 三页各自剥掉 `<script>`/`<style>`/标签、解码实体、只保留字母数字、转小写、按空格切词，取所有连续 N 词作为集合，取三页的并集；再把 `site/guide/` 下 14 个 html 逐个做同样处理，统计交集。

先做了方法自检：拿 `page_02.html` 与它自己做同一比对，`shared = 3085 / 3085`（100%），说明比对方法本身有效；而 `page_02.html` 对 `page_03.html` 只共享 2 个 5-gram（`identity and access management iam`、`what is the difference between`），`page_02.html` 对 `page_04.html` 只共享 1 个（`to provide you with the`）——都是通用短语。

| 我们的页面 | 5-gram 重合 / 总数 | 8-gram 重合 / 总数 |
|---|---|---|
| `csv-2026-09-21-1.html` | 0 / 508 | 0 / 528 |
| `csv-2026-09-24-1.html` | 0 / 513 | 0 / 536 |
| `csv-2026-09-27-1.html` | 0 / 506 | 0 / 525 |
| `csv-2026-09-30-1.html` | 0 / 501 | 0 / 520 |
| `how-to-buy-and-connect-a-cheap-vps.html` | 0 / 793 | 0 / 803 |
| `how-vps-pricing-works.html` | 0 / 589 | 0 / 597 |
| `steps-2026-09-23-1.html` | 0 / 740 | 0 / 748 |
| `steps-2026-09-26-1.html` | 0 / 731 | 0 / 739 |
| `steps-2026-09-29-1.html` | 0 / 731 | 0 / 739 |
| `unitprice-2026-09-22-1.html` | 0 / 643 | 0 / 669 |
| `unitprice-2026-09-25-1.html` | 0 / 499 | 0 / 519 |
| `unitprice-2026-09-28-1.html` | 0 / 491 | 0 / 508 |
| `unitprice-2026-10-01-1.html` | 0 / 643 | 0 / 669 |
| `vps-comparison-table-csv.html` | 0 / 572 | 0 / 576 |
| **合计** | **0** | **0** |

标注：本轮的 N-gram 比对脚本是**临时文件**，未落进 `vps-deals-promo-radar/`，运行完即删（这一轮只新建本文这一个 md）。比对只覆盖 `site/guide/` 目录，`site/index.html`、`site/compare.html`、`site/provider/*`、`site/deal/*` 未纳入，见第 5 节。

### 4.2 逐段人工比对：三个维度是我们自己长出来的

以下几个做法，我在三页对标 HTML 里逐段找过，**找不到对应结构**：

| 我们的做法 | 页面上的原文 | 核对方式 |
|---|---|---|
| **按单位计价（价格 ÷ 已公布 RAM）** | `unitprice-2026-10-01-1.html` 第 42 行：表头 `# / Plan / Published price / RAM (GB) / Price per GB`，第 1 行 `3.3592 USD/GB`；`how-vps-pricing-works.html` 第 42 行明写公式与边界「Dividing the published price by the published RAM figure is the only comparison that needs no assumption.」 | 在 `page_02/03/04.html` 全文检索「per GB」「/GB」「÷」「divided by」，正文无一处；三页 `<table` 计数均为 0（`pages/evidence.json` 的 `tableCount` 亦为 0/0/0）。`docs/bench-cheap-vps.md` 第 21–22 行独立得出同一结论：三十页里只有 2 处单价数字，没有任何一页按「每月每 GB 内存」拆开 |
| **可下载的比价表（CSV）** | `vps-comparison-table-csv.html` 第 42 行：`Download unit-price.csv`，并逐字列出 12 个列名；实际文件 `site/downloads/unit-price.csv` 存在 | 在 `page_02/03/04.html` 里检索 `href` 指向 `.csv/.xlsx/.ods/.pdf/.zip` 的链接数：三页**各为 0**。`docs/bench-cheap-vps.md` 第 21 行记录了同一结果 |
| **编号开机步骤（买→连→加固）** | `how-to-buy-and-connect-a-cheap-vps.html` 第 42 行：8 个 `<li>`，第 6、7 步分别写 SSH 与 RDP 的连接路径 | `page_02/03/04.html` 里 `<ol>` 计数分别为 0 / 0 / 0；三页正文的 `steps` 字段（`pages/evidence.json`）全部是 `configure`/`Install`/`Tutorial`/`Learn more` 这类**指向别处**的词，不是本页步骤。`docs/bench-cheap-vps.md` 第 23 行独立得出同一结论 |
| **「算不出来就留空」的显式标注** | `csv-2026-09-30-1.html` 第 42 行：netcup 五行的 RAM 列写 `not published`、Price per GB 列写 `-`；第 42 行后半写「The rest keep an empty per-GB cell rather than a guess.」 | 三页对标 HTML 里都不存在「数据缺失标注」这种结构；LEB 对每家都给完整价格与配置，OVH/DO 只列自家产品，所以**没有可比较的缺失格子**，也就没有对应写法 |

### 4.3 我们**没有**做、也不需要学的做法

（记下来是为了说明我们没有模仿，不是评价它们好坏。）

- 我们没有星级评分体系（LEB 的 `LowEnd Score:⭐⭐⭐⭐⭐`，`text_4.txt` 第 33、47 行）。
- 我们没有折扣码 / 限时优惠位（LEB `Coupon Code: 2LEB`、`Coupon Code: LEB50`、`Coupon Code: 50LEB`，`text_4.txt` 第 43、89、104 行）。
- 我们没有「谁是第一」的排名声明（LEB 的 `Best Cheap VPS Hosting: 品牌名` 顺序本身即排名，`text_4.txt` 第 32 行起）。
- 我们不做跨厂商并列推荐，只做同厂商套餐内部按单位价的排序（`unitprice-2026-10-01-1.html` 第 42 行的表只含 Hostwinds）。
- 我们不做评测/用户评价引用（DO 与 OVH 页面上也没有；三家均未见我们这种「来源 + UTC 读取时间」逐条标注的做法）。

---

## 5. 资料缺口

以下判断在本地文件里**找不到证据**，所以文中留空或未下结论，没有补想象。

| 缺什么证据 | 具体缺到什么程度 | 影响的结论 |
|---|---|---|
| **搜索结果页的真实排名与结果列表** | `serp2/serp.json` 的 `winner.results` 是空数组（第 30 行），`log[0].count` = 0（第 9 行）；`serp2/pass2_gbv.html` 是 Google 的 `sorry/index` 拦截页（第 15 行）；`serp3/serp_refetch.json` 的 `blocked` = `true`、`rows` 为空数组（第 5、8 行）；`serp_cwv/serp.json` 的 `winner.results` 同样为空 | 本文只敢写「本地抓取名单里的第 2/3/4 位」，**无法**核对它们真实的 SERP 排名位置，也无法统计这一页在 SERP 上占了几个位置 |
| **搜索量 / 关键词难度 / 外链数 / 流量** | 本地任何文件中都没有这几类字段：`serp*/**.json` 只有 `title`/`url`/`blocked`/`bodyStart`；`pages/visits.json` 只有 `textLen`、`counts`、`elapsedMs`。`cheap-vps-top10-audit.md` 第 52–54 行也明确声明不含这些 | 本文**不含**任何搜索量、难度、外链数、流量数字。表一里「为什么排前面」只写页面上看得见的结构原因 |
| **两页对不上的站内链接全貌** | OVH 页 192 个 a 标签全部是绝对 URL，我按域名过滤后统计了路径；但页面导航含多层 `Back to menu` 结构，**无法**判断哪些链接在实际渲染中可见、哪些只在折叠菜单里 | 表一「内链结构」写的是「带 href 的 a 标签数 + 站内路径覆盖」，**没有**写「可见导航链接数」 |
| **LEB 那 45 张图的语义** | 我只读到了 `alt` 属性（前 12 个为 `ServerHost - Your Value Host Leader`、`RackNerd VPS Hosting`、`CloudServer - Inexpensive Cloud and VPS Hosting Services` 等），**没有**读到图片本身，无法判断它们是品牌卡截图、评分徽章还是别的 | 表一没有把「图片使用」列为 LEB 的结构优势；表三里与之相关的一条（第 4 条卡片节奏）只用文字清单作证据 |
| **DigitalOcean 那 63 处 `20xx-xx-xx` 的性质** | 用正则命中 63 处，但**没有**逐条定位到正文可见区域；`visits.json` 的 `dates` 数组为空（第 105 行） | 表一里 DO 的「更新日期」写「无」，依据是 `Updated`/`datePublished`/`Last updated`/`<time>` 四项计数为 0，**不是**否定了那 63 处全部 |
| **`bench/` 语料的完整比对** | 本轮 5-gram 比对只覆盖 `pages/page_02|03|04.html` 三页。`bench/leb/`、`bench/do/`、`bench/ovh/` 各 10 页正文（共 30 页）**未纳入** N-gram 比对；`docs/bench-cheap-vps.md` 是对这 30 页的人工结论，可作参考但不能替代机器比对 | 第 4 节的「0 重合」结论**只对这三页成立**，不对 `bench/` 下的 30 页成立 |
| **我们其余页面的比对** | 本轮 N-gram 比对只跑 `site/guide/`。`site/index.html`、`site/compare.html`、`site/provider/*.html`（7 个）、`site/deal/*.html`（25 个）**未跑** | 第 4 节不能推广成「整站无重合」 |
| **「为什么它排前面」的排序因素** | 本地没有这三页的抓取频次、索引时间、外链或站点权重数据；`pages/evidence.json` 里 OVH 与 LEB 的 `dated` 字段为空数组（第 28、77 行之外无值），DO 也是空 | 表一只写**页面自身的结构性差异**，凡是需要站外数据才能解释的部分一律不写 |

---

## 附：本文引用到的本地文件

`pages/visits.json`、`pages/evidence.json`、`pages/page_02.html`、`pages/page_03.html`、`pages/page_04.html`、`pages/text_2.txt`、`pages/text_3.txt`、`pages/text_4.txt`、`bench/leb/read.json`、`bench/do/read.json`、`bench/ovh/read.json`、`bench/domains.json`、`serp2/serp.json`、`serp3/serp_refetch.json`、`serp_cwv/serp.json`、`cheap-vps-top10-audit.md`、`vps-deals-promo-radar/docs/bench-cheap-vps.md`、`vps-deals-promo-radar/site/sitemap.xml`、`vps-deals-promo-radar/site/guide/` 下 14 个 html。
