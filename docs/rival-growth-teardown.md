# 对手生长拆解：页面矩阵、词清单、选题队列
_生成时间 2026-10-03T12:44:36Z（UTC）· 数据源 data/rival-matrix.json、data/rival-depth.json、data/rival-brands.json、data/rival-topic-queue.json_

这份报告只做三件事：看清对手的页面怎么铺、他们靠哪些词吃饭、把差距排成我明天写哪一篇。

两条自定的规矩，写在最前面：

- **不碰第三方估算**：没有任何 Ahrefs / Semrush / AITDK / sitedata 的搜索量或流量数字，排序只用三个能复核的信号（我们写没写过、公开补全里的名次、几家对手在做）。
- **不抄原文**：报告里不出现对手页面的句子，只出现结构指标（几个小标题、几张表、多少字）和从地址里读出来的词。

## 1. 挑样本：三个对手，能抓到什么、抓不到什么

| 对手 | robots.txt | 可抓范围 | sitemap 里的 URL | 我实际拿到了什么 |
|---|---|---|---|---|
| lowendbox.com | robots.txt 允许抓取 | sitemap 可读 | 12572 | 12572 条地址分进 7 类（博客文章页 6314、标签归档页 6042、教程帮助页 156、比较与榜单页 37） |
| vpsfilter.com | robots.txt 读不到（404 HTTP 404）：按允许处理 | sitemap 可读 | 2 | 2 条地址分进 2 类（核心工具页 1、其他 1） |
| www.pcmag.com | robots.txt 返回 403：这家明确拒绝自动访问，整站跳过 | **整站跳过** | — | 只记下拒绝这件事，一个页面都没抓 |

为什么样本就是这三个：命令给的 @TOP3 就是它们（老牌优惠站 lowendbox / 工具站 vpsfilter / 大媒体 pcmag），
我没有自己去加名单——加名单会让“我拿谁当标尺”这件事变得不可复核。

年龄我只用两个能复核的口径：sitemap 里最早一条 lastmod，以及 Wayback 的快照时间。
Wayback 这次两个接口都返回 429（被限流），所以那一列照实写“没拿到”，不用估算补。

现在的规模对比（同一时刻的一次快照，不是趋势）：

| 站点 | sitemap URL 数 | 最早一条 lastmod | 最新一条 lastmod | Wayback 最早快照 |
|---|---|---|---|---|
| 我们 vpsdealsradar.com | 56 个 HTML 文件 | — | — | — |
| lowendbox.com | 12572 | 2008-02-04 | 2026-10-03 | 没拿到（接口 429） |
| vpsfilter.com | 2 | — | — | 没拿到（接口 429） |

## 2. 看它靠哪些词吃饭

口径（重要）：这一节列的是**需求信号**，不是流量数字。

- 词来自两处：对手 sitemap 地址里他们自己写的词组（公开可查），以及公开搜索补全接口返回的真人查询原话。
- 信号 = 在补全列表里排第几位。排第 1 位就是“人一打这个词，前几个建议里就有它”。
- 本次补全抓取时间 2026-10-03T12:09:27Z，种子查询 15 个，失败 0 个。

补全里最靠前的 15 条真人查询（原始记录，未加工）：

| 名次 | 查询原话 | 在哪些种子下出现 |
|---|---|---|
| 1 | cheap vps | cheap vps |
| 1 | cheap vps hosting | cheap vps、cheap vps hosting |
| 1 | cheap windows vps | cheap windows vps |
| 1 | cheap linux vps | cheap linux vps |
| 1 | best cheap vps | best cheap vps |
| 1 | vps under $5 | vps under $5 |
| 1 | vps with ipv4 | vps with ipv4 |
| 1 | unmetered vps | unmetered vps |
| 1 | vps storage | vps storage |
| 1 | vps for beginners | vps for beginners |
| 1 | vps comparison | vps comparison |
| 1 | vps coupon code hostinger | vps coupon |
| 1 | cheap dedicated server | cheap dedicated server |
| 1 | vps vs shared hosting | vps vs shared hosting |
| 1 | how much does a vps cost | how much does a vps cost |

**还没拿到的**：谷歌搜索控制台里“我自己站”的真实点击与曝光词。
原因：没有 gsc-queries.csv（需要从 Search Console 导出）。

怎么给我（一分钟）：打开 Search Console → 效果 → 查询 → 右上角导出 → CSV，
存成 `data/gsc-queries.csv`，然后跑 `python rival_queue.py --offline && python rival_report.py`。
脚本 `rival_queue.load_gsc_queries()` 会自动按“展示次数”重排整个选题队列——第一判据就换成真流量。
我不会拿第三方估算的数字假装成流量，所以这一节现在只给需求信号，不给流量归因。

## 3. 拆页面矩阵：他们把什么页面铺成规模

| 对手 | 页面类型 | URL 数 | 占它自己 sitemap 的比例 |
|---|---|---|---|
| lowendbox.com | 博客文章页 | 6314 | 50.2% |
| lowendbox.com | 标签归档页 | 6042 | 48.1% |
| lowendbox.com | 教程帮助页 | 156 | 1.2% |
| lowendbox.com | 比较与榜单页 | 37 | 0.3% |
| lowendbox.com | 其他 | 17 | 0.1% |
| lowendbox.com | 场景页 | 4 | 0.0% |
| lowendbox.com | 核心工具页 | 2 | 0.0% |
| vpsfilter.com | 核心工具页 | 1 | 50.0% |
| vpsfilter.com | 其他 | 1 | 50.0% |
| www.pcmag.com | — | — | 整站跳过（robots.txt 拒绝） |

### 抽样页面的结构指标（每类取最近更新与最早的几页，只量结构）

| 对手 | 页面类型 | 正文词数(均) | H2(均) | H3(均) | 问句式小标题(均) | 表格(均) | 列表(均) | 站内链接(均) |
|---|---|---|---|---|---|---|---|---|
| lowendbox.com | 博客文章页 | 1291.7 | 9.3 | 6.0 | 1.0 | 0.0 | 10.3 | 66.0 |
| lowendbox.com | 标签归档页 | 1110.3 | 10.0 | 8.0 | 0.3 | 0.0 | 7.0 | 62.3 |
| lowendbox.com | 教程帮助页 | 2125.7 | 11.0 | 7.7 | 1.3 | 0.0 | 12.3 | 65.3 |
| lowendbox.com | 比较与榜单页 | 2917.0 | 1.0 | 3.7 | 0.0 | 1.3 | 27.7 | 58.7 |
| lowendbox.com | 其他 | 1213.3 | 1.0 | 4.3 | 0.0 | 0.0 | 16.0 | 50.7 |
| lowendbox.com | 场景页 | 1449.3 | 7.0 | 6.0 | 0.0 | 0.0 | 9.0 | 67.7 |
| lowendbox.com | 核心工具页 | 3188.0 | 33.0 | 13.0 | 3.0 | 1.0 | 22.0 | 117.0 |
| vpsfilter.com | 核心工具页 | 773.0 | 0.0 | 1.0 | 0.0 | 0.0 | 2.0 | 5.0 |
| vpsfilter.com | 其他 | 534.0 | 17.0 | 0.0 | 0.0 | 2.0 | 0.0 | 2.0 |

标题写法（同样的抽样）：

| 对手 | 标题带年份 | 标题带价格 | 标题带 update 字样 | 描述长度(均) | 有可见 datePublished 的页 | 有可见 dateModified 的页 |
|---|---|---|---|---|---|---|
| lowendbox.com | 2/19 | 1/19 | 1/19 | 130.8 | 15/19 | 8/19 |
| vpsfilter.com | 0/2 | 0/2 | 0/2 | 69.0 | 0/2 | 0/2 |

## 4. 看多语言

我用两种方式判：地址里有没有语言路径，页面里有没有 `hreflang` 标注。

| 对手 | 地址里的语言路径 | 页面里的 hreflang | 判定 |
|---|---|---|---|
| lowendbox.com | 有语言样式路径（6042 个标签归档页） | 无 | 没有做多语言：那些两字母段是 `tag/` 归档（域名后缀、缩写），不是语言目录；页面里也没有 hreflang |
| vpsfilter.com | 无 | 无 | 没有做多语言：地址里没有语言目录，页面里也没有 hreflang |
| www.pcmag.com | — | — | 整站跳过，无从判断 |

结论：**这三个对手都没做真正的多语言**。lowendbox 的 6042 个 `标签归档页` 是 `tag/` 归档
（`/tag/io/`、`/tag/me/` 这种域名后缀标签），不是 `de/`、`fr/` 那种语言目录。
所以“多语言”这一条对我们没有可抄的动作，我不把它写成任务。

## 5. 看产品策略：他们把哪门生意当成主线

口径：只数对手 sitemap 地址里点名的厂商与技术词（地址是他们自己给的，公开可查）。

| 对手 | 地址里点名的厂商/技术数 | 出现最多的 8 个 | 根级独立页数 |
|---|---|---|---|
| lowendbox.com | 58 | openvz 1475、kvm 695、xen 384、racknerd 183、cpanel 104、ryzen 59、quickweb 33、quadranet 32 | 18 |
| vpsfilter.com | 0 | — | 1 |
| www.pcmag.com | — | — | — |

lowendbox 的根级常青页（不在 `/blog/` 下，说明这是他们当门面的页）：

- https://lowendbox.com/best-cheap-amd-ryzen-vps-hosting/
- https://lowendbox.com/best-cheap-nvme-storage-vps-hosting/
- https://lowendbox.com/best-cheap-vps-hosting-updated-2020/
- https://lowendbox.com/best-cheap-windows-vps-hosting/
- https://lowendbox.com/cheap-gpu-list-nvidia-gpus-for-ai-training-llm-models-and-more/
- https://lowendbox.com/comment-subscriptions/
- https://lowendbox.com/community-deals-on-cheap-vpn-cheap-vps-and-cheap-everything/
- https://lowendbox.com/hosting-offers-archive/
- https://lowendbox.com/irc-rules/
- https://lowendbox.com/openvz-xen-and-kvm-the-differences-the-advantages-a-comparison/
- https://lowendbox.com/racknerd-halloween-giveaway-secret-code/
- https://lowendbox.com/racknerd-winter-giveaway-secret-code/

读法：他们的规模在 `/blog/` 下的**按时间发的优惠单页**（6314 条），但真正的门面是少数几个根级榜单页。
对我们这一条的直接含义：我现在的 25 个 `/deal/*` 页相当于他们的优惠单页，缺的是根级榜单页。

## 6. 拆外部渠道（能看多少看多少）

我能复核的只有一件事：对手页面自己往外链了哪些站（这能看出它把内容分发到哪）。

| 对手 | 抽样页面里出现的站外域名（前 12） |
|---|---|
| lowendbox.com | alphavps.com(19)、api.fontshare.com(19)、bmail.ag(19)、cheapforexvps.com(19)、cloudlinux.com(19)、clouvider.com(19)、cplicense.net(19)、dedirock.com(19)、digitalcloud.pro(19)、facebook.com(19)、just.hosting(19)、koanode.com(19) |
| vpsfilter.com | image.thum.io(1)、tierhive.com(1) |
| www.pcmag.com | —（整站跳过） |

我没做的事：不去扒他们的社媒粉丝数、邮件列表规模、外链数——这些数字我复核不了，写进来就是估算。
所以这一节只交付“他们往哪些站导流”这一层，剩下的标成没拿到。

## 7. GEO 检查：这些页能不能被 AI 直接引用

判据用的是页面自己印出来的东西：问答式小标题、表格、发布/更新日期、结构化数据类型。

| 对手 | 抽样页数 | 有问句式小标题的页 | 有表格的页 | 有 dateModified 的页 | 结构化数据类型 |
|---|---|---|---|---|---|
| lowendbox.com | 19 | 6/19 | 2/19 | 8/19 | Article、BreadcrumbList、CollectionPage、ImageObject、Person、WebPage、WebSite |
| vpsfilter.com | 2 | 0/2 | 1/2 | 0/2 | WebSite |
| www.pcmag.com | — | — | — | — | —（整站跳过） |

对比我们现在的页：每篇指南都有 5 条问答 + `FAQPage` JSON-LD + 可见的 `Published / prices last read`，
首页第一屏有答案框和数字。这一项我们不落后。

## 7.5 自查：我们没有抄（可复核的重合率）

方法：把双方页面去掉标签后切成 5 个词一段的碎片（5-gram），算我们每一页和对手每一页的重合率。
对手正文只在内存里参与计算，**一个字的原文都不落盘**。

- 比对规模：对手 8 页 × 我们 56 页（其中内容页 55 页）
- 最高的一处重合：**3.7037%**（6 个 5-gram 相同，出现在我们的 `/404.html`）
- 只看内容页（排除只有导航页脚的 `404.html` 这类模板页）：**0.9524%**（6 个 5-gram，出现在我们的 `/about.html`）
- 逐条明细：data/rival-overlap.json

结论：即使是最高的那一处也是零头，来源是 `the best cheap vps` 这类行业里谁都得用的搭配；
没有任何一段成句的搬运。谁想复核，跑 `python rival_teardown.py overlap` 就能重算。

## 8. 变成选题队列（这就是明天要写的清单）

共抽到词组 1628 条，按下面的规则筛出 54 条入队；
排序口径：先看我们写没写过，再看公开补全里的名次，再看几家对手在做；没有任何第三方搜索量估算。

| 优先级 | 词组 | 做这个词的对手 | 需求信号 | 我们写过没 | 动作 | 对手的样例地址 |
|---|---|---|---|---|---|---|
| 1 | vps storage | 1 家 / 14 个地址 | 补全第 1 位（vps storage） | 没有 | 补这一篇 | https://lowendbox.com/blog/advantagecom-60year-512mb-xen-vps-with-199gb-storage/ |
| 2 | unmetered vps | 1 家 / 13 个地址 | 补全第 1 位（unmetered vps） | 没有 | 补这一篇 | https://lowendbox.com/blog/delimiter-usa-6-unmetered-vps/ |
| 3 | best cheap | 1 家 / 11 个地址 | 补全第 1 位（best cheap vps） | 没有 | 补这一篇 | https://lowendbox.com/blog/the-best-cheap-vps-hosting-in-review-2020-edition/ |
| 4 | best cheap vps | 1 家 / 5 个地址 | 补全第 1 位（best cheap vps） | 没有 | 补这一篇 | https://lowendbox.com/blog/the-best-cheap-vps-hosting-in-review-2020-edition/ |
| 5 | free vps | 1 家 / 25 个地址 | 补全第 2 位（free vps with ipv4） | 没有 | 补这一篇 | https://lowendbox.com/blog/amazon-free-ec2-micro-instance-613mb-xen-vps-for-1-year/ |
| 6 | best vps | 1 家 / 5 个地址 | 补全第 3 位（best vps for beginners） | 没有 | 补这一篇 | https://lowendbox.com/blog/2019-best-vps-provider-as-voted-by-the-low-end-talk-community/ |
| 7 | server usa | 1 家 / 5 个地址 | 补全第 3 位（cheap dedicated server usa） | 没有 | 补这一篇 | https://lowendbox.com/blog/serverleased-6-99month-512mb-openvz-server-in-the-usa-and-the-netherlands/ |
| 8 | dedicated server usa | 1 家 / 4 个地址 | 补全第 3 位（cheap dedicated server usa） | 没有 | 补这一篇 | https://lowendbox.com/blog/citywidehost-49month-quad-core-16gb-dedicated-server-in-phoenix-az-usa/ |
| 9 | storage cheap | 1 家 / 2 个地址 | 补全第 3 位（vps storage cheap） | 没有 | 补这一篇 | https://lowendbox.com/blog/dedirock-launches-storage-wars-get-ultra-cheap-and-we-do-mean-ultra-cheap-pricing-on-huge-storage-boxes/ |
| 10 | vps uk | 1 家 / 156 个地址 | 补全第 4 位（cheap windows vps uk） | 没有 | 补这一篇 | https://lowendbox.com/blog/hws-hosting-4-gbp-openvz-vps-in-uk/ |
| 11 | windows vps uk | 1 家 / 1 个地址 | 补全第 4 位（cheap windows vps uk） | 没有 | 补这一篇 | https://lowendbox.com/blog/veeble-three-offers-including-7month-512mb-windows-vps-in-uk/ |
| 12 | vps netherlands | 1 家 / 76 个地址 | 补全第 5 位（unmetered vps netherlands） | 没有 | 补这一篇 | https://lowendbox.com/blog/serverffs-5-35-64mb-openvz-vps-in-netherlands/ |
| 13 | vps usa | 1 家 / 34 个地址 | 补全第 6 位（unmetered vps usa） | 没有 | 补这一篇 | https://lowendbox.com/blog/easevps-7-00month-1024mb-openvz-vps-in-kansas-city-and-jacksonville-usa-or-manchester-uk/ |
| 14 | vps europe | 1 家 / 6 个地址 | 补全第 6 位（best cheap vps europe） | 没有 | 补这一篇 | https://lowendbox.com/blog/domvps-com-6-04month-256mb-openvz-vps-in-europe-usa/ |
| 15 | dedicated server uk | 1 家 / 3 个地址 | 补全第 6 位（cheap dedicated server uk） | 没有 | 补这一篇 | https://lowendbox.com/blog/poundhost-25month-2gb-ram-320gb-hdd-dedicated-server-in-maidenhead-uk/ |
| 16 | cheap vps europe | 1 家 / 2 个地址 | 补全第 6 位（best cheap vps europe） | 没有 | 补这一篇 | https://lowendbox.com/blog/eurovm-unlimited-bandwidth-cheap-vps-in-europe-for-e26-40-year-ddos-protection-and-ipv6-included/ |
| 17 | unmetered vps usa | 1 家 / 2 个地址 | 补全第 6 位（unmetered vps usa） | 没有 | 补这一篇 | https://lowendbox.com/blog/vpscheap-net-unmetered-1000mbps-vps-from-15year-in-chicago-usa/ |
| 18 | vps ipv4 | 1 家 / 2 个地址 | 补全第 6 位（vps ipv4 vs ipv6） | 没有 | 补这一篇 | https://lowendbox.com/tag/vps-change-ipv4-feature/ |
| 19 | ipv6 vps | 1 家 / 10 个地址 | 补全第 7 位（ipv4 ipv6 vps） | 没有 | 补这一篇 | https://lowendbox.com/blog/fitvps-10quarter-128mb-openvz-ipv6-only-vps-in-bulgaria/ |
| 20 | ipv4 ipv6 | 1 家 / 2 个地址 | 补全第 7 位（ipv4 ipv6 vps） | 没有 | 补这一篇 | https://lowendbox.com/blog/route48-org-free-ipv4-to-ipv6-tunnel-broker-service-plus-much-more/ |
| 21 | server europe | 1 家 / 3 个地址 | 补全第 8 位（cheap dedicated server europe） | 没有 | 补这一篇 | https://lowendbox.com/blog/vmdeploy-fully-managed-ssd-cloud-server-in-europe-with-competitive-pricing-9-separate-kvm-plans/ |
| 22 | dedicated server europe | 1 家 / 2 个地址 | 补全第 8 位（cheap dedicated server europe） | 没有 | 补这一篇 | https://lowendbox.com/blog/its-a-wait-is-this-a-typo-kind-of-deal-from-avahost-cheap-dedicated-server-in-europe/ |
| 23 | best price | 1 家 / 1 个地址 | 补全第 9 位（vps best price） | 没有 | 补这一篇 | https://lowendbox.com/blog/black-friday-deal-servermania-e3-servers-from-45-mo-best-price-ever/ |
| 24 | unmetered bandwidth | 1 家 / 42 个地址 | 补全第 10 位（vps unmetered bandwidth） | 没有 | 补这一篇 | https://lowendbox.com/blog/123com-4-256mb-openvz-vps-in-scranton-france-and-germany-with-unmetered-bandwidth/ |
| 25 | vps unmetered | 1 家 / 20 个地址 | 补全第 10 位（vps unmetered bandwidth） | 没有 | 补这一篇 | https://lowendbox.com/blog/rethinkvps-5-95-128mb-openvz-vps-with-gbps-unmetered/ |
| 26 | vps unmetered bandwidth | 1 家 / 12 个地址 | 补全第 10 位（vps unmetered bandwidth） | 没有 | 补这一篇 | https://lowendbox.com/blog/rawsrv-now-in-miami-2gb-vps-with-unmetered-bandwidth-for-9-50-mo/ |
| 27 | hosting europe | 1 家 / 2 个地址 | 补全第 10 位（cheap vps hosting europe） | 没有 | 补这一篇 | https://lowendbox.com/blog/one-euro-hosting-myrootpw-has-shared-hosting-in-us-or-europe-for-1-e-first-year-10-e-year-after-that/ |
| 28 | cheap vps | 1 家 / 290 个地址 | 补全第 1 位（cheap vps） | 有（17 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/cheap-vps-llc-8-quarter-512mb-and-48-year-1gb-ovz-in-san-jose/ |
| 29 | dedicated server | 1 家 / 151 个地址 | 补全第 1 位（cheap dedicated server） | 有（14 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/olmnet-2995-refurbished-dedicated-server/ |
| 30 | windows vps | 1 家 / 79 个地址 | 补全第 1 位（cheap windows vps） | 有（6 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/yardvps-6-71-512mb-windows-vps-chinese-new-year-promo/ |
| 31 | cheap dedicated | 1 家 / 66 个地址 | 补全第 1 位（cheap dedicated server） | 有（14 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/dedicated-server-hosting-find-cheap-dedicated-servers-on-lowendbox/ |
| 32 | vps hosting | 1 家 / 61 个地址 | 补全第 1 位（cheap vps hosting） | 有（23 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/budget-vps-hosting-specials/ |
| 33 | linux vps | 1 家 / 36 个地址 | 补全第 1 位（cheap linux vps） | 有（27 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/alvotech-e19-50-512mb-linux-vserver-vps-in-germany/ |
| 34 | cheap windows | 1 家 / 25 个地址 | 补全第 1 位（cheap windows vps） | 有（6 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/cheap-windows-vps-5-25month-768mb-windows-kvm-and-more-in-the-usa/ |
| 35 | cheap windows vps | 1 家 / 20 个地址 | 补全第 1 位（cheap windows vps） | 有（6 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/cheap-windows-vps-5-25month-768mb-windows-kvm-and-more-in-the-usa/ |
| 36 | coupon code | 1 家 / 16 个地址 | 补全第 1 位（vps coupon code hostinger） | 有（1 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/serversgalore-1gb-kvm-sale-with-coupon-code-for-30-off-for-life/ |
| 37 | cheap vps hosting | 1 家 / 8 个地址 | 补全第 1 位（cheap vps hosting） | 有（17 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/the-best-cheap-vps-hosting-in-review-2020-edition/ |
| 38 | cheap linux | 1 家 / 6 个地址 | 补全第 1 位（cheap linux vps） | 有（17 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/cheap-linux-vps-for-just-1-month-only-at-lowendbox/ |
| 39 | cheap linux vps | 1 家 / 5 个地址 | 补全第 1 位（cheap linux vps） | 有（17 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/cheap-linux-vps-for-just-1-month-only-at-lowendbox/ |
| 40 | code hosting | 1 家 / 2 个地址 | 补全第 1 位（vps coupon code hostinger） | 有（4 页里出现） | 已有，检查够不够深 | https://lowendbox.com/blog/defined-code-hosting-openvz-vps-starting-at-2year-in-the-netherlands-and-france/ |

### 数据边界（这一节是这份报告的诚信部分）

- `www.pcmag.com`：`robots.txt` 返回 403，明确拒绝自动访问 → 整站跳过，一个页面都没抓。命令里有它，但我不会为了凑数翻墙绕它。
- `vpsfilter.com`：`robots.txt` 不存在（404），sitemap 里只有 2 条地址，首页是 JS 渲染的空壳（我们的规矩是不执行站外脚本），所以它这一家只有“页面数”这一个结论。
- 真实流量词：**没拿到**。命令规定 @GSC / @GA4 是唯一数据源，而 GSC 需要登录本机 Chrome
  （当前 Chrome 没开调试端口、profile 被进程锁住），所以第 2 节给的是公开补全信号，不是流量归因。
  拿到导出表后跑 `python rival_queue.py --offline && python rival_report.py`，这里会自动换成真数字。
- 对手的收入、佣金、外链数：没拿到，也不猜。

