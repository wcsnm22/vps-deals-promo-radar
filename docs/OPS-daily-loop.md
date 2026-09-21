# OPS — 每天一篇的循环怎么跑、怎么发、怎么报数

这份是把目标落地需要的全部命令。数字全部来自抓取或官方后台，本文不含任何估数。

## 一、每天自动跑什么

Windows 计划任务 `vps-deals-daily`，每天 09:00，执行 `daily-run.cmd`：

```
python scraper.py        # 抓 6 家公开价格页 -> data/offers.json（robots.txt 不允许的跳过并记录）
python guides.py         # 按缺口轮换补一篇（csv -> unitprice -> steps），一天只加一篇
python build.py          # 渲染 site/：指南栏、CSV、sitemap、_worker.js 合法路径
python content_check.py  # 写稿判据自查：第一屏要答案、与对标站重叠<30%、无中文/视频痕迹
node <wrangler.js> pages deploy site   # 直接把 site/ 发到 Cloudflare Pages
```

发布这一步只在自查通过时执行：`content_check` 不为 0 就只留在本地，线上保持上一版。
想只重建不发线上，设环境变量 `PAGES_DEPLOY=0` 再跑 `python daily.py`。

每次运行追加一行到 `data/daily-log.jsonl`：

```json
{"ran_at":"...","scraper_exit":0,"guides_exit":0,"build_exit":0,"content_check_exit":0,"deploy_exit":0,
 "offers":15,"priced":15,"guides":4,"status":"ok","content_check_tail":[],
 "deploy_tail":["Deployment complete! Take a peek over at https://<hash>.vps-deals-promo-radar-e18.pages.dev"]}
```

`status` 只在所有步骤全 0 时为 `ok`；`content_check_tail` 原样留下没过的篇目和原因；
`deploy_tail` 留下本次部署地址，便于回查到具体哪一版。

## 二、这一篇到底补了什么（三个缺口的实测来源）

| 缺口 | 对标结果（三域名 × 前十页） | 我们的填法 | 数字出处 |
|---|---|---|---|
| 可下载比价表 | 30 页里 0 个提供 csv/xlsx/pdf | `site/downloads/unit-price.csv`，随抓取更新 | `data/offers.json` |
| 按单位计价 | 只有 2 处单价数字，没有按每月每 GB 横向拆解 | 只用页面原文数字做除法：`价格 ÷ 页面写明的 RAM(GB)` | 同上，公式写在 CSV 的 `unit_price_formula` 列 |
| 编号开机步骤 | 只有第三方 ramnode 文档是编号步骤 | 8 步序列，每步挂厂商文档链接 | RamNode / OVHcloud / DigitalOcean 文档 |

## 三、怎么发布

**当前方式：本机 wrangler 直接发**（已上线，2026-09-21 验证）

```powershell
cd 'D:\新建文件夹 (2)\vps-deals-promo-radar'
node "$env:APPDATA\npm\node_modules\wrangler\bin\wrangler.js" pages deploy site `
  --project-name=vps-deals-promo-radar --commit-dirty=true
```

注意：`wrangler.ps1` 会被 PowerShell 执行策略挡住，所以上面用 `node` 直接调 js 入口。
这一条已经写进 `daily.py`，每天 09:00 任务会自动执行。

**备选方式：走仓库 Actions**

```powershell
git add -A
git commit -m "feat: daily guide pipeline + downloadable CSV + unit-price coverage"
git push origin main          # 推上去后 .github/workflows/update.yml 会部署
```

上线后的核验（这三条已实测通过）：

1. `https://vpsdealsradar.com/guide` → 200，列出当期篇目
2. `https://vpsdealsradar.com/downloads/unit-price.csv` → 200，`content-type: text/csv`，15 行
3. 任意指南页第一屏就是带数字的答案；不存在的路径返回**真 404**（不是回落到首页）
4. `*.pages.dev` 预览地址 301 到 `vpsdealsradar.com`（`_worker.js` 保证只有一个地址）

## 四、每 28 天报数

### 先确认这两样装上了（否则报数永远是空的）

**Search Console：这个域名已经验证过了**（2026-09-21 用 DNS 查到，可自行复核）：

```
Resolve-DnsName -Name vpsdealsradar.com -Type TXT
→ google-site-verification=V3aiVOSnL8VFTpyz2igejUoZLIruAoBN72wrZVlWVGo
```

TXT 记录存在，说明用的是「网域资源」DNS 验证方式，属性已经在某个 Search Console 账号下。
所以**不需要**再配 `gsc_verification` meta；三个数可以直接在 GSC 后台读。

**GA4：目前没有任何统计脚本**（2026-09-21 实测线上首页无 gtag / GTM）。
所以「访客数」这一格在装 GA4 之前必然是空的——不是脚本读不到，是没在采集。

装 GA4 只需在 `.ilang/site.ilang` 的 `@SITE` 那一行填一个值：

```
ga4_measurement_id:G-XXXXXXXXXX
```

- 填了 → 每个页面出现 gtag 脚本；**同时隐私政策自动改口**，从「No first-party analytics」
  换成明确写出「装了 GA4，ID 是 xxx，会设 cookie」
- 留空 → 页面里干干净净，隐私政策照实说没有（当前线上就是这个状态）
- GA4 ID 格式不对（不是 `G-` 开头）时 `build.py` 直接报错停构建，不会把坏 ID 发上去
- 如果你更想用 GSC meta 方式（比如换账号重新验证），填 `gsc_verification:<content 值>` 也会自动注入

改完跑一次 `python daily.py` 就会带上并发布。

### 出报告

先把这一期该用的日期区间打出来（照着在后台选，不用自己算）：

```powershell
python report.py --next-window
```

然后把你从后台读到的原值填进一个 JSON 文件：

```json
{"indexed": 2, "clicks": 0, "clicks_prev": null, "position": 0, "position_prev": null, "active_users": null}
```

```powershell
python report.py --fromfile numbers.json
```

**这一期要用的账号信息（2026-09-21 建好并验证）**：

| 项 | 值 |
|---|---|
| Search Console 属性 | `https://vpsdealsradar.com/`（DNS 方式已验证；网域资源） |
| GA4 衡量 ID（装在站上采集） | `G-9EKG14K2LL` |
| GA4 **数字属性 ID**（`--ga4` 用这个） | `555210738` |
| GA4 账号 ID | `408899555` |

如果用 API 取数（服务账号方式）：

```powershell
python report.py --creds <服务账号.json> --gsc https://vpsdealsradar.com/ --ga4 555210738 --indexed <后台页数>
```
```powershell
# 路线 1：从 GSC/GA4 后台复制数字，写进一个 JSON 文件（推荐，最省事）
#   文件内容示例（只放你复制的原值，脚本不改数、不补数）：
#   {"indexed": 42, "clicks": 7, "clicks_prev": 3, "position": 18.4, "position_prev": 21.9, "active_users": 5}
python report.py --fromfile numbers.json

# 路线 2：命令行长参数
python report.py --indexed 42 --clicks 7 --clicks-prev 3 --position 18.4 --position-prev 21.9 --active-users 5

# 路线 3：有服务账号 JSON 时（索引数仍要手贴，API 不给）
python report.py --creds C:\path\sa.json --gsc https://vpsdealsradar.com/ --ga4 <GA4属性ID> --indexed 42
```

**服务账号一次性的准备**（2026-09-21 已在本机装好客户端库，不再需要 pip）：

1. Google Cloud Console 建服务账号 → 「密钥 → 添加密钥 → 创建新密钥」选 **JSON**（不是 P12），把下载到的文件放到这台机器上任意路径
2. 该服务账号邮箱（JSON 里的 `client_email`，形如 `名字@项目ID.iam.gserviceaccount.com`）在
   Search Console 里加为 **受限（Restricted）** —— 这是只读权限，不要给「完全（Full）」
3. 要用 GA4 的话：GA4 → 管理 → 属性访问管理，给同一邮箱 **Viewer**；另外把 `G-` 衡量 ID 一并给我
4. 凭据文件带不带 BOM 都能读；`type` 不是 `service_account` 会被明确拒绝，不会继续往下跑
5. 不要把这个文件的内容贴进聊天，只需要给路径

不装任何东西也能出报告：走路线 1 手贴。

输出四行，可直接贴回群里。**口径**（照第 10 步）：

| 行 | 口径 |
|---|---|
| 索引 | GSC 后台「已编入索引」页数，窗口 = 近 28 天 |
| 点击 | GSC 效果 点击，本 7 天 ← 上一个 7 天 |
| 平均排名 | GSC 效果 平均排名，最近 24 小时 ← 前一天 |
| 访客 | GA4 近 7 天日均活跃用户 |

缺哪一格就写「读不到」，不会用别的数顶上；`--fromfile` 支持部分字段，只给 `--indexed` 也能出报告。

历史存 `data/report-rounds.json`，单期文本存 `data/reports/`。

**已知限制（不许糊过去）**：

- 「已编入索引」页数 **GSC API 不暴露**（Search Analytics 无此字段，Sitemaps 只给「已提交」），必须从后台手贴 `--indexed`
- 没给任何输入时脚本退出码 2 并列出缺什么，**不填占位、不估算**

## 五、当前数据状态（可复算）

| 项 | 值 |
|---|---|
| 抓取记录（去重后即站点套餐） | 15 |
| 其中有价格 | 15 |
| 同时有价格和 RAM 规格 | 15 / 15 |
| CSV 里带 `price_per_gb_ram` 的行 | 15 |
| 覆盖厂商 | OVHcloud 4、netcup 5、BuyVM 1、IONOS 5；DigitalOcean 被 robots.txt 拒绝跳过；Hetzner 页面抓不到价格 |
| 已发布指南页 | 4（手写 3 + 自动 1，自动页逐日新增） |

抓取报告里还记着各家"价格找到了但没有可信产品名，因此没收录"的条数（OVHcloud 2、netcup 1、BuyVM 13、IONOS 5）——这是宁缺毋滥的结果，不是丢数据。

## 六、故障怎么查

| 症状 | 先看哪 |
|---|---|
| 计划任务没跑 | `Get-ScheduledTaskInfo -TaskName vps-deals-daily`，再看 `data/daily-run.log` |
| 价格抓不到 | `data/offers.json` 的 `providers[].note`，里面写了 HTTP 状态或 robots 拒绝原因 |
| 规格读错 | 跑 `python -c "import json;print(json.load(open('data/offers.json'))['offers'])"` 看每条的 `ram_gb/vcpu/disk_gb`，与厂商页面逐档核对 |
| 页面被判不合格 | 看 `data/daily-log.jsonl` 最后一行 `content_check_tail` |
| 线上是旧的 | 说明只跑了抓取+构建，没发布（第三节） |
