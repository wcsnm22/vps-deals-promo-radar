ILANG
TYPE:agents PROJECT:vps-deals LANG:zh

::STATE{@PROJECT, name:vps-deals-promo-radar, kind:静态优惠站, runtime:纯Python, deploy:Cloudflare Pages, cost:零}

::OBJECTIVE{keep_pipeline_honest}
  target: 让这个仓库长期自动更新 并且永远不出现假数据
  ACCEPT: 抓取和构建都能跑通 页面上的每个数字都能追到某个 provider 公开页面的某一次抓取
  NON_GOALS: 编数据 刷量 引入收费依赖 引入运行时模型调用

::RULE{配置唯一来源是 .ilang/site.ilang⇒改厂商清单 改词表 改渲染参数都改那里 不许在 py 里另写一份}
::RULE{抓不到 price⇒不写 price 字段 也不写进结构化数据}
::RULE{找不到可信产品名⇒这条不收录 宁缺毋滥}
::RULE{抓取前读 robots.txt⇒Disallow 就跳过并写进 data/offers.json 的 providers 报告}
::RULE{只抓公开页面⇒不登录 不绕反爬 不伪装登录态 不改 UA 冒充浏览器}
::RULE{改动后必须本地跑一遍 python scraper.py && python build.py⇒再检查 site/ 里的 canonical sitemap 和 JSON-LD}
::BOUNDARY{never:编优惠 编价格 编有效期 编佣金 编评分|scope:permanent}
::BOUNDARY{never:往仓库里放密钥⇒令牌只进 GitHub Secrets|scope:permanent}

::MODULE{FILES|title:每个文件管什么}
  scraper.py | 读 site.ilang 抓公开页 写 data/offers.json；不负责渲染
  build.py | 读 offers.json 和 site.ilang 渲染 site/；不负责抓取
  templates/ | index provider deal compare 四个页面模板 占位符是 {{name}}
  data/offers.json | 数据集 每次工作流覆盖 是页面数字的唯一出处
  .github/workflows/update.yml | 每 6 小时 抓 + 建 + 提交 + 部署
  site/ | 构建产物 提交进仓库 也是部署内容

::MODULE{FIELDS|title:offers.json 里每条优惠的字段}
  provider title price currency offer_url valid_until source_url fetched_at
  # price 和 valid_until 可能不存在 不存在就是抓不到 页面必须照实省略 不许补

::MODULE{ALLOWED|title:接手这个仓库时允许做的动作}
  加一家厂商 在 site.ilang 的 PROVIDERS 里加一行
  删一家厂商 删掉那一行 并删掉 site/ 和 data/ 里对应的旧文件
  调词表 改 FILLER SPECWORD TITLEHINT EXCLUDE SKIPPRICE
  改模板 只改外观 不许改动"数字从哪来"的那部分说明文字
  改抓取频率 改 update.yml 的 cron

::MODULE{FORBIDDEN|title:绝对不许做的动作}
  为了让页面好看而给某个优惠补一个价格
  把源页面已经下架的优惠继续留在页面上
  把价格换算成别的货币 或者加"约等于"
  把别的站的优惠抄过来冒充这个 provider 的
  把 Cloudflare 令牌或任何密钥写进代码 提交历史 或 issue
