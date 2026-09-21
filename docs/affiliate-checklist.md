# 联盟申请清单（vps-deals）

用途：按这张单子逐家申请，拿到链接后交回，我填进配置并逐个核对线上按钮真的带上了追踪参数。

**纪律**：本表只写我核实过的内容；没核实的标「未确认」，不替平台或厂商编入口、编佣金。

---

## 一、填哪里（技术侧已就绪）

文件：`.ilang/site.ilang` 的 `PROVIDERS` 段，每行第 4 段就是联盟链接列：

```
# 每行: 名称 | 官网 | 优惠页 | 联盟链接(留空则用裸链) | kind=page | currency=USD
OVHcloud | https://www.ovhcloud.com | https://www.ovhcloud.com/en/vps/ |  | kind=page | currency=USD
```

**填了第 4 段 → 该厂商所有按钮自动换成你的联盟链接；留空 → 用裸链。**
构建时 `build.py` 里 `affiliate_for()` 优先取联盟链接，取不到才回落到抓到的裸链。

**建议**：每家给**一条「联盟首页链接」**就够，不必找每个套餐的联盟深链——硬拼深链容易追踪失效。若某家提供深链且你确认可用，也可以，但要在单子里注明。

---

## 二、申请前准备（各家大概率都会要）

| 要准备的信息 | 说明 |
|---|---|
| 站点网址 | `https://vpsdealsradar.com` |
| 推广方式 | 内容站 / 比价站，自然搜索流量 |
| 账号邮箱 | 收款与对账用 |
| 收款方式 | PayPal / 银行 / 平台钱包（**实名与税务信息只能你自己填，我不经手**） |
| 站点现状说明 | 建议如实说：新站、每天更新、当前收录页数少（别夸大，审核会查） |

---

## 三、逐家清单

「✅已核实」= 我这次真的打开/查到了；「未确认」= 我没查到，**请自行在官网底部或帮助中心搜** `affiliate` / `partner` / `referral`。

| # | 厂商 | 官网 | 申请入口（我核实的部分） | 申请状态 | 拿到的联盟链接 |
|---|---|---|---|---|---|
| 1 | DigitalOcean | https://www.digitalocean.com | ✅ **走 Awin 平台**（非官网自助）：[Awin 商户页](https://ui.awin.com/merchant-profile/123996)；条款：[联盟协议](https://www.digitalocean.com/legal/affiliate-program-agreement) | ☐ 未申请 | |
| 2 | OVHcloud | https://www.ovhcloud.com | ⚠️ 只有协议文档可查：[OVHcloud Affiliates 协议](https://www.ovh.ie/support/termsofservice/OVHcloud%20Affiliates.pdf)（PDF，我没读到内容）；**申请入口未确认** | ☐ 未申请 | |
| 3 | netcup | https://www.netcup.com | ✅ 有帮助中心页面：[Affiliate Program（英）](https://www.netcup.com/en/helpcenter/documentation/general/affiliate-program)、[Partnerprogramm（德）](https://www.netcup.com/de/helpcenter/dokumentation/general/partnerprogramm)（**页面是 JS 渲染，内容我没读到**） | ☐ 未申请 | |
| 4 | IONOS | https://www.ionos.com | ✅ 走「Agency Partner」体系：[afiliado 页（西语）](https://www.ionos.es/agency-partner/afiliado)、[Agency Partner 注册说明](https://www.ionos.es/ayuda/programas-ionos-partner/primeros-pasos-en-el-portal-ionos-agency-partner/) | ☐ 未申请 | |
| 5 | BuyVM | https://buyvm.net | ❌ **未查到**第一方联盟计划 | ☐ 未申请 | |
| 6 | Hetzner | https://www.hetzner.com | ❌ **未查到**第一方联盟计划；仅见第三方汇总页 [xAmplify](https://xamplify.com/partner-programs/hetzner/)（未核实） | ☐ 未申请 | |

### 补充：不在抓取名单里、但值得考虑的一家

| # | 厂商 | 情况 | 申请状态 | 联盟链接 |
|---|---|---|---|---|
| 7 | RackNerd | 有「Promote Like a Nerd」推广门户，[官方博客文章](https://blog.racknerd.com/how-to-use-racknerds-promote-like-a-nerd-portal-to-earn-recurring-commissions/)提到 **recurring（持续性）佣金**。**该文章我没能打开原文核实（返回 403）**，请自行确认 | ☐ 未申请 | |

> 如果 RackNerd 要加进站里，不是填链接就行——得在 `site.ilang` 的 `PROVIDERS` 里**新增一行**（名称 | 官网 | 优惠页 | 联盟链接 | kind | currency），我才能抓到它的价格并出套餐页。

---

## 四、你拿到链接后，我做什么

1. 填进 `site.ilang` 对应那一列
2. `python scraper.py && python build.py`（抓取 + 重建）
3. **逐个核对**：把线上页面里的出站按钮抓出来，确认目标 URL 带上了你的追踪参数（不是"填了就算"）
4. 发布并核验线上（`daily.py` 会顺带跑内容判据与线上核验）

---

## 五、当前状态（2026-09-21 实测）

| 项 | 值 |
|---|---|
| 六家联盟链接列 | **全部为空** → 线上零联盟参数 |
| 全站出站链接 | 17 条，其中 **带联盟参数的 0 条** |
| 站点可点击转化入口 | 全站 45 个按钮 |
| 自然搜索点击（7 天） | **0**（GSC 实测） |
| 被收录页数 | **2**（我们站共 32 页） |
| 结论 | **当前收益为 0，且是结构性的 0**：既没有联盟链接，也还没有流量 |

## 六、不要做的事

- 不要为了好看往链接里塞一个猜的参数（我不会做，也不会替你拼）
- 不要夸大站点流量去骗过审——审下来后数据对不上，账号会被封
- 不要在多个平台重复注册同一家厂商的计划（容易触发风控）
