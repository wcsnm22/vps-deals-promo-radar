# 外观改了什么（T1）

做法：把站甩给 AI 看，它说什么就改什么；改完截图，前后各留一张在 `docs/design-review/`。

| 文件 | 什么时候的 |
|---|---|
| `docs/design-review/before-desktop.png` | 改之前的首页（1440 宽） |
| `docs/design-review/before-mobile.png` | 改之前的首页（390 宽） |
| `docs/design-review/after-desktop.png` | 改之后的首页（1440 宽） |

截图是本地 `site/` 起一个静态服务后用 Chrome 无头模式拍的，拍的是真实渲染结果，不是设计稿。

## 一、第一屏：从"有标题"改成"先给答案"

改之前，首页第一屏是标题 + 一句 tagline + 三个统计框，**没有任何一个具体价格**。
改之后，第一屏多了一段答案框，句子里的数字都是 `data/offers.json` 现算的：

> Lowest published monthly price right now: $2 (IONOS VPS S+). Lowest published price per GB of RAM:
> 0.8333 USD per GB (IONOS VPS XXL+, $20 / 24 GB). 25 of 25 tracked plans publish a price; …

这条改动是照着对标站学的：三家对标页的第一屏都至少有一个价格锚点
（OVH `Starting at $4.54/month`、DigitalOcean 标题里的 `Starting at $4/mo`、lowendbox `$2.00/month`），
见 `docs/why-they-outrank-us.md` 表三第 5 条。

## 二、第一屏之后：直接放图

首页在答案框下面加了一张"每 GB 内存月费"的图（`/assets/per-gb-cheapest.svg`，
由 `chart_assets.py` 从抓到的数字现画）。图上按货币分组，不做汇率换算——不同货币的行不并排比长短。

## 三、手机（390 宽）

- 表格改成卡片式：一行一块，按钮铺满整行，手指点得到（原来按钮是窄条，手机上容易点空）。
- 标题、答案框、分子框在小屏上缩小字号并允许换行；380 宽以下统计框改成一列。
- 全局 `img, svg { max-width:100% }` 和 `overflow-x:hidden`，防止长图把整页撑宽。

核对方式：把首页放进一个 390 宽的 iframe 里拍图，正文正常换行、没有横向溢出。
（直接用 `--window-size=390` 拍，Chrome 无头会按更大的布局宽度渲染再裁切，看起来像被切断，
那不是页面的问题——所以用 iframe 的方式核。）

## 四、导航和互链

- 顶部导航原来只有 首页 / Compare all / 7 个厂商页。现在加了 **Guides** 和 **Price table (CSV)**
  两个入口——这两个页面一直都在，只是从导航里点不到。
- 每个指南页底部加了 **More on this site**：同缺口最近 3 篇 + 最近 2 篇 + 指南索引 + CSV 下载。
  原来 14 个指南页之间零互链，只能靠 `sitemap.xml` 被发现。

## 五、日期让人看得见

指南页在 H1 下面多了一行人眼可见的日期：

> Published 2026-10-01 · prices last read from the providers 2026-10-01T05:07:09Z (UTC).

同时 JSON-LD 补了 `dateModified`，`datePublished` 改成用这一篇自己的发布日期（原来用的是构建时间，
每重建一次"发布日期"就会变一次）。lowendbox 就是靠正文里可见的月份做复访理由的。

## 六、这次没做的

- 没换配色和字体：现在的深底 + 橙色强调在对比度上没问题，换字体是纯口味问题，没人说不好看就先不动。
- 没有给 `compare.html` 和厂商页加同一套答案框：那两页本来第一屏就有价格表，缺的不是锚点。
- 首页那个小动物（`pets.js`）没动。
