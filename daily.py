# ILANG
# TYPE:schedule ROLE:daily-run PROJECT:vps-deals
# ::RULE{每天跑一次 先抓后建⇒抓不到就照实跳过 不许补数}
# ::RULE{每次都要写一行日志⇒日期 篇数 缺口 结果 地址}
# ::RULE{通过自查就提交并推回 origin⇒本地和 Actions 永远构建同一棵树 不许只留在本地}
# ::RULE{某家 provider 整批抓挂⇒本轮判 failed 不提交不发布 留待下次重抓 不许把缩小一半的数据集当成当天的事实}
# ::RULE{发布前确认 site/ 产物完整⇒缺首页或 sitemap 就不发 线上留上一版}
# ::RULE{git 动作不许改 site/⇒合并前后内容一致 构建产物不归版本库管}
# ::RULE{日志的 status⇒覆盖抓取 建模 自查 退化守卫 提交 发布 核对每一步 任一步非零就记 failed 不许只报前半段}
# ::BOUNDARY{never:编价格 编索引数|scope:file}
"""每天的自动任务：抓公开页 -> 重建站点 -> 更新指南栏 -> 写日志。

零依赖，只用 Python 标准库。调度器每天调用一次：python daily.py
"""
from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# 退化守卫只此一份：Actions 跑 `python guard.py` 用的是同一对函数，
# 两条发布路径不会因为判据抄了两遍而各说各话。
from guard import dataset_guard, previous_offers

# 子进程的 stdout 被管道接住时，Python 默认按系统编码写字节（Windows 是 GBK），
# 父进程按 UTF-8 解码就得到替换字符，日志里的中文会变成读不懂的乱码。
# 统一让子进程写 UTF-8，和下面 run() 的 encoding="utf-8" 对上。
os.environ["PYTHONIOENCODING"] = "utf-8"

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "data"
LOG_PATH = LOG_DIR / "daily-log.jsonl"
# 构建产物目录。它是 .gitignore 排除的、却又躺在工作区里，凡是动 git 的地方
# 都要先把它挪开——理由见 git_sync()。
SITE_DIR = ROOT / "site"

# push 失败的两种原因长得不一样，处理方式也相反：远端抢先（可合并重试）与
# 凭据失效（合并无用，只会白搅工作区）。靠 git 的输出把后者认出来。
AUTH_FAILURE_RE = re.compile(
    r"could not read Username|Authentication failed|Permission denied \(publickey\)"
    r"|terminal prompts disabled|failed to execute prompt script|invalid credentials"
    r"|Support for password authentication was removed",
    re.I,
)


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

    ::RULE{本机是唯一的生产发布者⇒必须带 --branch=production}
    2026-10-20 的事故：GitHub Actions 每 6 小时用 origin/main 的旧内容发一次
    production，把本机刚发的页面盖回旧版（线上指南只剩 24 篇）。所以项目里的
    生产分支改名成 production，Actions 那个 main 分支的部署只落在预览地址上。
    """
    import os

    if os.environ.get("PAGES_DEPLOY", "1") != "1":
        return 0, "[skip] PAGES_DEPLOY=0, built but not published"
    import shutil
    if os.name == "nt":
        wrangler = Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "wrangler" / "bin" / "wrangler.js"
        node = "node.exe"
        if not wrangler.exists():
            return 1, f"[fail] wrangler not found at {wrangler}"
        cmd = [node, str(wrangler)]
    else:
        # Linux / VPS: npm -g 装的 wrangler 本身可执行, 直接走 PATH
        wrangler = shutil.which("wrangler")
        if not wrangler:
            return 1, "[fail] wrangler not found in PATH"
        cmd = [wrangler]
    branch = os.environ.get("PAGES_BRANCH", "production")
    proc = subprocess.run(
        cmd + ["pages", "deploy", "site",
               "--project-name=vps-deals-promo-radar", f"--branch={branch}", "--commit-dirty=true"],
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


def git_sync(ran_tag: str) -> tuple[int, str]:
    """把本次产出提交并推回 origin，让 Actions 和本地永远构建同一棵树。

    推不上去（远端刚被 Actions 刷新过等竞态）就先合一下再推；还不行就照实返回
    非零记进日志，内容留在本地，下一次运行重试——不为了同步去改写远端历史。

    ::RULE{git 的合并与回退不许碰 site/⇒动手前把它挪开 收工后再挪回来}
    site/ 已被 .gitignore 排除，但仍躺在工作区里，而 origin/main 上还留着历史
    提交过的同名文件（site/ 是 2026-10-20 之后才移出版本库的）。于是
    `git merge origin/main` 会把这些文件判成 "deleted in HEAD / modified in
    origin/main" 的 modify-delete 冲突并写回工作区；紧接着的 `git merge --abort`
    按索引恢复，就把**整个 site/ 删掉**——2026-11-01 的事故正是如此：本轮构建的
    首页、sitemap、compare、provider 页全没了，只剩 robots.txt 和 assets/，
    发布出去就是一个空站（线上首页 404）。挪开 site/ 再动 git，冲突不再产生，
    构建产物也绝不会被版本库操作牵连。
    """

    def git(*args: str) -> tuple[int, str]:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    # site/ 是构建产物、已移出版本库（.gitignore 里有）：两边各自重建，
    # 只提交数据，提交历史里就不会再出现"本机与 Actions 改同一个 HTML"的冲突。
    # 2026-10-20 之前 site/ 是被跟踪的，那次 Actions 拿旧 commit 覆盖线上就跟这个有关。
    add_code, add_out = git("add", "data")
    if add_code != 0:
        return 1, "[fail] git add: " + " ".join(add_out.strip().splitlines()[-1:])
    staged_code, _ = git("diff", "--staged", "--quiet")  # 0=无改动 1=有改动
    if staged_code == 0:
        return 0, "[skip] nothing to commit"
    commit_code, commit_out = git("commit", "-m", f"daily: refresh {ran_tag}")
    if commit_code != 0:
        return 1, "[fail] git commit: " + " ".join(commit_out.strip().splitlines()[-1:])
    push_code, push_out = git("push", "origin", "main")
    if push_code != 0:
        # 先分清"推不上去"是哪一种。凭据失效时合并毫无意义——合完再推还是失败，
        # 却白白把远端那棵树合进本地、把工作区搅一遍。2026-10 那阵子本机凭据就
        # 一直是坏的（gh 的 token 失效），于是每天都白走一遍合并，最后把 site/
        # 删没了。凭据问题照实记进日志、原地返回，一个字都不改本地。
        if AUTH_FAILURE_RE.search(push_out):
            return 1, "[fail] git push: credentials unavailable; not merging (fix git auth): " + \
                " ".join(push_out.strip().splitlines()[-1:])
        # 远端被 Actions 抢先刷新：先把远端合进来再推一次。
        # 冲突一律取远端版本（-X theirs）——远端那棵是同一套流水线刚发过的树，
        # 而"抢先"本身就说明它比本地新。反过来用 -X ours 会拿本地这份去覆盖，
        # 上一次就是这么把一整家 provider 从 30 条压成 20 条的。
        #
        # 合并前把 site/ 挪到工作区外：否则 origin/main 上的旧 site/ 文件会以
        # modify-delete 冲突的形式写回工作区，随后的 --abort 会连整个 site/ 一起删掉。
        with shelved_site():
            git("fetch", "origin")
            merge_code, merge_out = git("merge", "origin/main", "-X", "theirs", "--no-edit")
            if merge_code != 0:
                # -X theirs 只解决"两边都改了同一段内容"，解决不了 modify-delete：
                # HEAD 已把 site/ 移出版本库，origin/main 上还留着历史提交过的同名
                # 文件，于是每一个都判成冲突。这些路径是构建产物，正确的解法就是
                # "删掉"——保留远端那份等于把已移出版本库的目录又塞回去，下一轮
                # 又要再冲突一次。只自动处理 site/ 下的；别的路径一律不猜。
                _, unmerged = git("diff", "--name-only", "--diff-filter=U")
                site_conflicts = [
                    line.strip() for line in unmerged.splitlines()
                    if line.strip().startswith("site/")
                ]
                if site_conflicts:
                    git("rm", "-f", "--quiet", "--", *site_conflicts)
                    commit_code, commit_out = git("commit", "--no-edit")
                    if commit_code != 0:
                        git("merge", "--abort")
                        return 1, "[fail] merge commit after push race: " + " ".join(
                            commit_out.strip().splitlines()[-1:])
                    merge_out = ""
                # 还有别处没合上就退回合并前：别留一个停在半路的 MERGE_HEAD，
                # 那个状态会让下一次运行的 git add/commit 全部失败。
                _, still = git("diff", "--name-only", "--diff-filter=U")
                if still.strip():
                    git("merge", "--abort")
                    return 1, "[fail] merge after push race: " + " ".join(
                        (merge_out or still).strip().splitlines()[-1:])
            push_code, push_out = git("push", "origin", "main")
            if push_code != 0:
                return 1, "[fail] git push: " + " ".join(push_out.strip().splitlines()[-1:])
    return 0, "[ok] committed and pushed to origin/main"


@contextlib.contextmanager
def shelved_site():
    """把 site/ 临时挪出工作区，退出时原样搬回。

    用"移动"而不是"复制+删除"：site/ 里都是本次刚构建好的页面，挪回来必须是
    逐字节相同的那一份，不能依赖任何重建。万一挪动失败，宁可让整个 git 同步
    失败，也不能在 site/ 状态不明的情况下继续——那正是要防的事故。
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="vps-deals-site-"))
    stash = tmp_root / "site"
    moved = False
    try:
        if SITE_DIR.exists():
            shutil.move(str(SITE_DIR), str(stash))
            moved = True
        yield stash
    finally:
        # 无论正常返回、抛异常还是提前 return，都要把 site/ 放回原位。
        if moved:
            if SITE_DIR.exists():
                # 理论上不会发生；真发生了说明 git 又写回了文件，以挪走的那份为准。
                shutil.rmtree(SITE_DIR)
            shutil.move(str(stash), str(SITE_DIR))
        shutil.rmtree(tmp_root, ignore_errors=True)


def site_complete() -> tuple[int, str]:
    """发布前确认 site/ 里本轮该有的页面真的都在磁盘上。

    只看 build.py 的退出码是不够的：2026-11-01 那次 build.py 返回 0，site/ 却
    在之后被 git 操作删空，残骸照样发了出去。这里按"这次构建必须产出的文件"逐个
    核对——首页、sitemap、robots、每个 provider 页、每个 deal 页、指南页、CSV。
    少任何一个都不发：线上留上一版，总好过发一个打不开的站。

    返回 0/1 而不是 True/False：Python 里 False == 0 是 True，拿布尔值当退出码
    去和 0 比，判据恒真，守卫会静悄悄地失效。
    """
    import json

    missing: list[str] = []
    for name in ("index.html", "sitemap.xml", "robots.txt", "compare.html",
                 "about.html", "methodology.html", "privacy.html", "contact.html",
                 "404.html", "guide.html", "_worker.js", "downloads/unit-price.csv"):
        if not (SITE_DIR / name).exists():
            missing.append(name)

    data_path = ROOT / "data" / "offers.json"
    if data_path.exists():
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        for provider in payload.get("providers", []):
            slug = re.sub(r"[^a-z0-9]+", "-", provider["name"].lower()).strip("-")
            if not (SITE_DIR / "provider" / f"{slug}.html").exists():
                missing.append(f"provider/{slug}.html")
        deal_count = len(list((SITE_DIR / "deal").glob("*.html")))
        if deal_count == 0 and payload.get("offers"):
            missing.append("deal/*.html (all deal pages missing)")

    if missing:
        preview = ", ".join(missing[:5]) + ("..." if len(missing) > 5 else "")
        return 1, f"[fail] site/ is incomplete ({len(missing)} missing): {preview}"
    return 0, f"[ok] site/ complete ({len(list(SITE_DIR.rglob('*.html')))} html pages on disk)"


def main() -> int:
    started = datetime.now(timezone.utc)
    scrape_code, scrape_out = run("scraper.py")
    # 先决定今天补哪个缺口：guides.py 一天只加一篇，加过就跳过
    guides_code, guides_out = run("guides.py")
    build_code, build_out = run("build.py")
    # 写稿判据自查：第一屏有答案、独家≥30%、无中文残留/视频痕迹。不合格照实记，
    # 不因此停下循环（页面已经生成，判据结果用于次日修正）。
    check_code, check_out = run("content_check.py")
    # 退化的抓取结果不许发：某家 provider 整批归零是抓取失败（证书、超时、被拒抓），
    # 不是厂商当天同时下架了全部套餐。放它过去就等于把半边数据集当成今天的事实。
    data_path = ROOT / "data" / "offers.json"
    current_snapshot = None
    guard_code, guard_out = 1, "[skip] no offers.json produced this run"
    if data_path.exists():
        import json

        current_snapshot = json.loads(data_path.read_text(encoding="utf-8"))
        guard_code, guard_out = dataset_guard(current_snapshot, previous_offers())
    # 发布前确认本次构建的产物是完整的：2026-11-01 那次事故里 build.py 明明成功，
    # 但 site/ 被随后的 git merge --abort 删空，deploy() 照样把残骸发了出去，
    # 线上首页变成 404。所以不能只看 build.py 的退出码，要真的确认页面在磁盘上。
    site_code, site_out = site_complete()
    # 通过自查、本轮数据没退化、且产物完整，才推回远端：Actions 由此永远构建同一棵树
    # （分叉就是这一步从前缺失）。任一条不过就不推——和"不发布"同一个口径，
    # 内容只留本地等次日修正。
    publishable = check_code == 0 and guard_code == 0 and site_code == 0
    if publishable:
        git_code, git_out = git_sync(started.strftime("%Y-%m-%d"))
    elif site_code != 0:
        git_code, git_out = 1, "[skip] site/ incomplete; not syncing to git"
    elif guard_code != 0:
        git_code, git_out = 1, "[skip] dataset regressed; not syncing to git"
    else:
        git_code, git_out = 1, "[skip] content_check failed; not syncing to git"
    # git_sync() 是上一次真正删掉 site/ 的那一步，所以产物完整性必须在它之后再核一遍。
    # 只在前头核等于把"git 没动过构建产物"当成前提——那正是出事时被推翻的假设。
    # 这一遍不过就绝不发布：线上留上一版，好过发一个打不开的站。
    if publishable:
        site_after_code, site_after_out = site_complete()
        if site_after_code != 0:
            site_code, site_out = site_after_code, "[after git] " + site_after_out
            publishable = False
    # 发布：都过才发；否则线上保持上一版
    if publishable:
        deploy_code, deploy_out = deploy()
        # 发布成功后再核一遍线上内容是不是本次构建：自定义域名有传播窗口，
        # 不核就等于把"上传成功"当成"已经生效"。
        if deploy_code == 0:
            verify_code, verify_out = run("verify_deploy.py")
        else:
            verify_code, verify_out = 1, "[skip] deploy failed; nothing to verify"
    elif site_code != 0:
        deploy_code, deploy_out = 1, f"[skip] site/ incomplete; not publishing this build: {site_out}"
        verify_code, verify_out = 1, "[skip] nothing published"
    elif guard_code != 0:
        deploy_code, deploy_out = 1, "[skip] dataset regressed; not publishing this build"
        verify_code, verify_out = 1, "[skip] nothing published"
    else:
        deploy_code, deploy_out = 1, "[skip] content_check failed; not publishing this build"
        verify_code, verify_out = 1, "[skip] nothing published"

    offers = 0
    priced = 0
    if current_snapshot is not None:
        offers = len(current_snapshot.get("offers", []))
        priced = sum(1 for item in current_snapshot.get("offers", []) if item.get("price") is not None)

    guides_path = ROOT / "data" / "guides.json"
    guide_count = 0
    if guides_path.exists():
        import json

        guide_count = len(json.loads(guides_path.read_text(encoding="utf-8")))

    # status 必须覆盖整条链：从前只看 scraper/guides/build，于是"同步失败"和
    # "数据集退化"都会被记成 ok，恰好是这两种故障最难在日志里发现。
    steps_ok = (
        scrape_code == 0
        and guides_code == 0
        and build_code == 0
        and check_code == 0
        and guard_code == 0
        and site_code == 0
        and git_code == 0
        and deploy_code == 0
        and verify_code == 0
    )
    record = {
        "ran_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scraper_exit": scrape_code,
        "guides_exit": guides_code,
        "build_exit": build_code,
        "content_check_exit": check_code,
        "guard_exit": guard_code,
        "site_exit": site_code,
        "git_exit": git_code,
        "deploy_exit": deploy_code,
        "verify_exit": verify_code,
        "offers": offers,
        "priced": priced,
        "guides": guide_count,
        "status": "ok" if steps_ok else "failed",
        # 数据退化守卫的结果原样留证：拦下的是哪一家、从几条掉到几条
        "guard_tail": guard_out.strip().splitlines()[-2:],
        # 产物完整性核对的结果原样留证：少了哪几个文件
        "site_tail": site_out.strip().splitlines()[-2:],
        # 失败原因原样记 不美化
        "scraper_tail": scrape_out.strip().splitlines()[-3:] if scrape_code else [],
        "guides_tail": guides_out.strip().splitlines()[-2:] if guides_out else [],
        "build_tail": build_out.strip().splitlines()[-3:] if build_code else [],
        # 判据自查结果原样留证：哪几篇没过、为什么
        "content_check_tail": [
            line for line in check_out.strip().splitlines() if line.startswith("[FAIL]") or line.strip().startswith("-")
        ][:6],
        # git 同步结果原样留证：push 失败就写失败原因，下一次运行会重试
        "git_tail": git_out.strip().splitlines()[-2:],
        # 发布结果原样留证：成功会带 pages.dev 地址，失败带原因
        "deploy_tail": deploy_out.strip().splitlines()[-3:],
        "verify_tail": verify_out.strip().splitlines()[-2:],
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        import json

        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    # 日志文件永远写 UTF-8；这一行只是给人看的回显，遇到终端编码装不下的字符
    # （Windows 控制台是 GBK）不该把整次成功的运行变成退出码 1。
    try:
        print(json.dumps(record, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(record, ensure_ascii=True))
    return 0 if record["status"] == "ok" else 1

if __name__ == "__main__":
    raise SystemExit(main())
