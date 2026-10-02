# ILANG
# TYPE:module ROLE:deploy-check PROJECT:vps-deals
# ::RULE{部署后必须核对线上内容==本次构建⇒不一致就带重试 直到一致或超时}
# ::RULE{传播延迟不是失败⇒只在超时后才报 stale}
# ::BOUNDARY{never:把"部署成功"当成"内容已生效"|scope:file}
"""部署后验证：线上某页内容是否已等于本次构建。

Cloudflare Pages 的自定义域名在部署后有几秒到几十秒的传播窗口，
刚发完立刻抓会拿到上一版；这里带退避重试，避免把传播延迟误判成缓存错误。

用法：python verify_deploy.py [本地文件相对路径] [线上路径]
  默认核对 site/sitemap.xml 与 /sitemap.xml
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://vpsdealsradar.com"


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "vps-deals-radar/1.0 (+deploy verification)",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def fingerprint(text: str) -> set[str]:
    """只比会随构建变化的关键片段，避免整页对比被时间戳噪声干扰。

    除了指南的 lastmod 和资源版本号，还要把 sitemap 的**网址清单**纳入比对：
    否则"新增了一个页面但线上还是旧版"这种情况会被判为通过
    （旧版和构建版的 guide lastmod 是一样的，比不出来）。
    """
    import re

    out = set(re.findall(r"guide/[a-z0-9-]+</loc><lastmod>[^<]+", text))
    out |= set(re.findall(r'assets/style\.css\?v=[0-9A-Za-z]+', text))
    locs = re.findall(r"<loc>([^<]+)</loc>", text)
    if locs:
        out.add(f"urlcount={len(locs)}")
        out |= {f"loc={url}" for url in locs}
    return out


def configured_measurement_id() -> str:
    """从 .ilang/site.ilang 读 GA4 衡量 ID；没配就返回空串。"""
    import re

    config = (ROOT / ".ilang" / "site.ilang").read_text(encoding="utf-8")
    match = re.search(r"ga4_measurement_id:([^,}]*)", config)
    return (match.group(1).strip() if match else "")


def check_live_page(local_rel: str, online_path: str, label: str) -> tuple[bool, str]:
    """线上某个页面必须带着本地这次构建的那段内容。

    为什么要有这一步：sitemap 一致只说明"构建过"，不说明"这一页也上线了"。
    2026-10-01 就踩过一次——模板被回退、只部署了指南页，首页还是旧版，
    而 sitemap 核对照样通过。首页有没有带上这次构建的答案框，这里专门查一遍。
    """
    local_path = ROOT / local_rel
    if not local_path.exists():
        return True, f"[skip] 本地没有 {local_rel}，跳过 {label} 核对"
    local = local_path.read_text(encoding="utf-8")
    marker = 'class="answer"'
    if marker not in local:
        return True, f"[skip] 本次构建的 {local_rel} 里没有答案框，跳过 {label} 核对"
    try:
        live = fetch(BASE + online_path)
    except Exception as exc:  # noqa: BLE001
        return False, f"[fail] {label} 抓取失败：{type(exc).__name__}: {exc}"
    if marker not in live:
        return False, f"[fail] {label} 线上还是旧版：没有本次构建的答案框（{online_path}）"
    return True, f"[ok]   {label} 线上带着本次构建的内容（{online_path}）"


def check_tag(live_home: str, measurement_id: str) -> tuple[bool, str]:
    """线上首页必须真的带着配置里那个衡量 ID，否则统计会静默断掉。"""
    if not measurement_id:
        return True, "[skip] 未配置 ga4_measurement_id，跳过统计标签检查"
    if measurement_id not in live_home:
        return False, f"[fail] 线上首页没有配置里的衡量 ID {measurement_id}：统计会静默收不到数"
    if "googletagmanager.com/gtag/js" not in live_home:
        return False, "[fail] 首页有 ID 但没有 gtag 脚本地址，标签没真正加载"
    return True, f"[ok]   线上首页带着 gtag 与衡量 ID {measurement_id}"


def main() -> int:
    local_rel = sys.argv[1] if len(sys.argv) > 1 else "site/sitemap.xml"
    online_path = sys.argv[2] if len(sys.argv) > 2 else "/sitemap.xml"
    local = (ROOT / local_rel).read_text(encoding="utf-8")
    want = fingerprint(local)
    if not want:
        print(f"[warn] {local_rel} 里没有可核对片段，改用整页对比")
        want = {local.strip()}

    measurement_id = configured_measurement_id()
    tag_checked = False
    last = ""
    for attempt in range(1, 9):
        try:
            live = fetch(BASE + online_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[{attempt}] 抓取失败：{type(exc).__name__}: {exc}")
            time.sleep(5 + attempt * 3)
            continue
        have = fingerprint(live) or {live.strip()}
        if have == want:
            print(f"[ok]   第 {attempt} 次核对：线上 {online_path} 与本次构建一致（{len(want)} 个片段）")
            # 内容一致后再确认统计标签；只查一次
            if not tag_checked:
                tag_checked = True
                try:
                    ok, message = check_tag(fetch(BASE + "/"), measurement_id)
                    print("      " + message)
                    if not ok:
                        return 1
                except Exception as exc:  # noqa: BLE001
                    print(f"      [warn] 统计标签检查没能完成：{type(exc).__name__}: {exc}")
                ok, message = check_live_page("site/index.html", "/", "首页")
                print("      " + message)
                if not ok:
                    return 1
            return 0
        last = f"线上片段 {len(have)} 个，期望 {len(want)} 个；差集 {sorted(have ^ want)[:3]}"
        print(f"[{attempt}] 还不一致：{last}")
        time.sleep(5 + attempt * 3)

    print(f"[fail] 重试后仍不一致：{last}")
    print("       这可能是部署未生效，或自定义域名仍在传播；过一会儿再跑一次。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
