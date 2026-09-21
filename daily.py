# ILANG
# TYPE:schedule ROLE:daily-run PROJECT:vps-deals
# ::RULE{每天跑一次 先抓后建⇒抓不到就照实跳过 不许补数}
# ::RULE{每次都要写一行日志⇒日期 篇数 缺口 结果 地址}
# ::BOUNDARY{never:编价格 编索引数|scope:file}
"""每天的自动任务：抓公开页 -> 重建站点 -> 更新指南栏 -> 写日志。

零依赖，只用 Python 标准库。调度器每天调用一次：python daily.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "data"
LOG_PATH = LOG_DIR / "daily-log.jsonl"


def run(script: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def deploy() -> tuple[int, str]:
    """把 site/ 直接发到 Cloudflare Pages。

    发布用的 wrangler 走 node 入口：wrangler.ps1 会被 PowerShell 执行策略拦住。
    想只重建不发线上，设 PAGES_DEPLOY=0 再跑。
    """
    import os

    if os.environ.get("PAGES_DEPLOY", "1") != "1":
        return 0, "[skip] PAGES_DEPLOY=0, built but not published"
    wrangler = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "wrangler" / "bin" / "wrangler.js"
    if not wrangler.exists():
        return 1, f"[fail] wrangler not found at {wrangler}"
    node = "node.exe"
    proc = subprocess.run(
        [node, str(wrangler), "pages", "deploy", "site",
         "--project-name=vps-deals-promo-radar", "--commit-dirty=true"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    # 日志里只留可读的 ASCII：wrangler 的 emoji 在部分终端编码下会变成乱码，别写进日志
    cleaned = []
    for line in out.splitlines():
        ascii_line = " ".join("".join(ch for ch in line if ord(ch) < 128).split())
        if ascii_line:
            cleaned.append(ascii_line)
    return proc.returncode, "\n".join(cleaned[-4:])


def main() -> int:
    started = datetime.now(timezone.utc)
    scrape_code, scrape_out = run("scraper.py")
    # 先决定今天补哪个缺口：guides.py 一天只加一篇，加过就跳过
    guides_code, guides_out = run("guides.py")
    build_code, build_out = run("build.py")
    # 写稿判据自查：第一屏有答案、独家≥30%、无中文残留/视频痕迹。不合格照实记，
    # 不因此停下循环（页面已经生成，判据结果用于次日修正）。
    check_code, check_out = run("content_check.py")
    # 发布：自查通过才发；被判不合格就只留在本地，线上保持上一版
    if check_code == 0:
        deploy_code, deploy_out = deploy()
        # 发布成功后再核一遍线上内容是不是本次构建：自定义域名有传播窗口，
        # 不核就等于把"上传成功"当成"已经生效"。
        if deploy_code == 0:
            verify_code, verify_out = run("verify_deploy.py")
        else:
            verify_code, verify_out = 1, "[skip] deploy failed; nothing to verify"
    else:
        deploy_code, deploy_out = 1, "[skip] content_check failed; not publishing this build"
        verify_code, verify_out = 1, "[skip] nothing published"

    offers = 0
    priced = 0
    data_path = ROOT / "data" / "offers.json"
    if data_path.exists():
        import json

        payload = json.loads(data_path.read_text(encoding="utf-8"))
        offers = len(payload.get("offers", []))
        priced = sum(1 for item in payload.get("offers", []) if item.get("price") is not None)

    guides_path = ROOT / "data" / "guides.json"
    guide_count = 0
    if guides_path.exists():
        import json

        guide_count = len(json.loads(guides_path.read_text(encoding="utf-8")))

    record = {
        "ran_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scraper_exit": scrape_code,
        "guides_exit": guides_code,
        "build_exit": build_code,
        "content_check_exit": check_code,
        "deploy_exit": deploy_code,
        "verify_exit": verify_code,
        "offers": offers,
        "priced": priced,
        "guides": guide_count,
        "status": "ok" if scrape_code == 0 and guides_code == 0 and build_code == 0 else "failed",
        # 失败原因原样记 不美化
        "scraper_tail": scrape_out.strip().splitlines()[-3:] if scrape_code else [],
        "guides_tail": guides_out.strip().splitlines()[-2:] if guides_out else [],
        "build_tail": build_out.strip().splitlines()[-3:] if build_code else [],
        # 判据自查结果原样留证：哪几篇没过、为什么
        "content_check_tail": [
            line for line in check_out.strip().splitlines() if line.startswith("[FAIL]") or line.strip().startswith("-")
        ][:6],
        # 发布结果原样留证：成功会带 pages.dev 地址，失败带原因
        "deploy_tail": deploy_out.strip().splitlines()[-3:],
        "verify_tail": verify_out.strip().splitlines()[-2:],
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        import json

        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
