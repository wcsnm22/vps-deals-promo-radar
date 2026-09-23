# CJ 广告主申请记录

- 账号：VPS Deals Radar（Publisher ID 8078058 / CID 7766004）
- 促销资产：VPS Deals Radar - Daily VPS Price Tracker（Property ID 101887599，Website，主模型 Product Comparison, Reviews, or Discovery，状态 Active）

## 一、收款与税务（2026-09-22 已配置）

| 项目 | 实际值 |
|---|---|
| 税表 | IRS Form W-8BEN，提交日期 2026-09-22；Name: Shoufu Tang；Part II 未主张税收协定优惠 |
| 收款方式 | Payment by Direct Deposit |
| 银行 | Citibank（Payoneer 提供的美元收款账户），Account Type Checking |
| 账号 | Routing 尾号 09 / Account 尾号 3766，Holder: Shoufu Tang |
| 最低打款额 | 100.00 USD |

## 二、已提交的申请（2026-09-22，全部为人工审核）

| 广告主 ID | 广告主 | 类目 | 佣金 | 状态 |
|---|---|---|---|---|
| 4639721 | Contabo COM | Web Hosting/Servers | 0.00–250.00 EUR / 新客户 | **已批准 → My Advertisers (Active)** |
| 3812192 | (IS) Interserver Webhosting and VPS | Web Hosting/Servers | 100.00 USD / 单 | Pending Application |
| 6652708 | Ultahost | Web Hosting/Servers | 40% | Pending Application |
| 5331920 | Sucuri | Web Tools | 57.25–137.25 USD / 单 | Pending Application |

- 提交入口：`GET https://members.cj.com/member/accounts/publisher/affiliations/joinprograms.do?onJoin=clickSearch&advertiserId=<ID>&publisherId=8078058&norefresh=true`
- 页面上的 `APPLY TO PROGRAM` 按钮实际调用 `window.open(..., 'applyToProgramPopup')`；脚本触发时 `userGesture: false`，弹窗被浏览器拦截，所以直接访问该 URL 完成提交。
- 核对：`Advertisers → Pending Applications` 显示 **4 Results**，与上表一致（2026-09-22 实测）。

## 三、已知条款风险

- **Contabo**：条款原文 "We do not accept cash-back, coupon and voucher sites to participate in the Affiliate Program."。本站不做返现、不做优惠券，是按各商家已发布价格做比价并标注读取时间；若被追问按此说明。另有品牌词竞价禁令，两次违规即终止并追回已赚佣金。
- Contabo 佣金按"新客户"定义结算，首单 30 天内取消则不计佣。

## 四、B 档申请结果（2026-09-22 提交）

已提交、等待人工审核：

| 广告主 ID | 广告主 | 佣金 |
|---|---|---|
| 1513033 | GoDaddy.com | 10% |
| 4660055 | Dynadot.com | 20%–25%、0.00–20.00 USD |
| 7122185 | Turbify | 3% |
| 6798066 | Elementor | 45% |
| 3838098 | HOSTING.co.uk | 50% |
| 3022407 | (eUK) eUKhost Ltd | 40.00 GBP |
| 3192429 | Easyspace | 10%–30% |
| 1838477 | One.com | Lead 5.00 EUR |
| 6298339 | Velia | 30% |
| 7742241 | Gandi | 5% |

当场被拒（返回页标题即 `Application declined`，不用等）：

| 广告主 ID | 广告主 | 目录里的预警 |
|---|---|---|
| 4055157 | Namecheap | Lower application approval odds |
| 2188468 | Hostpapa | Lower application approval odds |

这两家在目录里本来就标着 "Lower application approval odds"，实测确实秒拒 —— 说明这个标记是可信的筛选信号，以后优先投标 "Manual application review" 的。

不投：CJ 内的 Hostinger(5173193) 仅 10%，低于 Hostinger 直客计划的 40%+，两道并行会让订单归属打架。

## 五、审核进度（2026-09-22 实测，Contabo 批准后复核）

| 状态 | 数量 | 明细 |
|---|---|---|
| **Active（已加入）** | **1** | Contabo COM (4639721) |
| Pending Applications | 13 | eUKhost / Interserver / Dynadot / Easyspace / Elementor / Gandi / GoDaddy / HOSTING.co.uk / One.com / Sucuri / Turbify / Ultahost / Velia |
| Declined Applications | 2 | Hostpapa (2188468)、Namecheap (4055157) |

- 1 + 13 + 2 = **16**，与提交记录一一对应，无多投、无误投。
- Contabo 的 Links & Products 里可用素材：**195 条**（含 Banner，例如 Link ID `17141390` 250x360、`17141387` 160x600），落地页指向 `https://contabo.com/en/dedicated-servers/?utm_source=cj&utm_medium=affiliate&utm_campaign=server`。
- 尚未取用：Contabo 的点击追踪链接（click URL）还未生成，也未接入站点配置。
- 另有 **Pending Offers 1 条**：`7804601 GearUP` —— 广告主主动发来的邀约，非我方申请。类目与佣金未取到（该行页面返回 CJ 错误页，按 ID 与名称搜索均为 0 结果），故不记录任何推断值。

## 六、待办

- [ ] 核对税表地址邮编：系统读数为 `120`（中国邮编应为 6 位）
- [ ] 跟踪 14 家审核结果（人工审核，通常数天到数周；中国 publisher 可能因地域被拒）
- [ ] 批准后到 `Links & Products` 取追踪链接，按 Hostwinds 的格式写进 `.ilang/site.ilang` 的 PROVIDERS 行
- [ ] Hostinger 直客申请：产品栏由 `Website Builder` 改为 VPS，流量数据如实填写
