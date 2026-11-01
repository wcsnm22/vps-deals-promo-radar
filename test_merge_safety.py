"""临时回归测试：证明 git_sync 的合并/回退路径不会再删掉 site/（用完即删）。

复现 2026-11-01 事故的真实条件（缺一不可）：
  1. 本地工作区里躺着本轮刚构建好的 site/（未跟踪，被 .gitignore 排除）；
  2. 本地 HEAD 里 **没有** site/ —— 因为 site/ 曾经被跟踪、后来被移出版本库，
     那个"删除"已经进了提交历史；
  3. origin/main 上 **还有** 被跟踪的 site/*.html —— 远端历史提交还在。

于是 `git merge origin/main` 会把这些路径判成
"deleted in HEAD / modified in origin/main" 的 modify-delete 冲突并写回工作区，
紧接着的 `git merge --abort` 按索引恢复，就把整个 site/ 删掉，只剩 robots.txt
和 assets/ —— 发布出去就是首页 404 的空站。

用法：
  python _test_merge_safety.py              # 测修好的 daily.py，应 PASS
  TEST_ORIGINAL=1 python _test_merge_safety.py   # 对照：换回修复前的 daily.py，应 FAIL
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parent
SKIP = {".git", "site", "data", "__pycache__", ".wrangler"}


def sh(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc


def copy_worktree(dest: Path) -> None:
    """复制源码，但故意不带 site/ 和 data/ —— 那两个在后面单独造。"""
    for item in REAL.iterdir():
        if item.name in SKIP:
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.log"))
        else:
            shutil.copy2(item, target)
    (dest / "data").mkdir(exist_ok=True)
    for name in ("offers.json", "guides.json"):
        src = REAL / "data" / name
        if src.exists():
            shutil.copy2(src, dest / "data" / name)


def main() -> int:
    control = os.environ.get("TEST_ORIGINAL") == "1"
    tmp = Path(tempfile.mkdtemp(prefix="vps-deals-merge-test-"))
    try:
        work = tmp / "work"
        remote = tmp / "remote.git"
        work.mkdir()

        print("[1] 搭本地工作区")
        copy_worktree(work)
        if control:
            original = subprocess.run(
                ["git", "show", "HEAD:daily.py"], cwd=str(REAL),
                capture_output=True, text=True, encoding="utf-8", check=True).stdout
            (work / "daily.py").write_text(original, encoding="utf-8")
            print("    [对照] 已换回修复前的 daily.py")
        sh(["git", "init", "-q", "-b", "main"], work)
        sh(["git", "config", "user.name", "test"], work)
        sh(["git", "config", "user.email", "test@example.com"], work)

        print("[2] 构建 site/，并让它在第一个提交里就被跟踪（历史原貌）")
        sh(["python", "build.py"], work)
        site_before = sorted(p.relative_to(work).as_posix()
                             for p in (work / "site").rglob("*") if p.is_file())
        print(f"    site/ 文件数：{len(site_before)}")
        assert (work / "site" / "index.html").exists(), "构建后应该有 index.html"

        print("[3] 建裸远端并推上去（此时远端带着 site/）")
        sh(["git", "init", "-q", "--bare", "-b", "main", str(remote)], tmp)
        sh(["git", "add", "-A", "-f", "site"], work)
        sh(["git", "commit", "-q", "-m", "init with tracked site"], work)
        sh(["git", "remote", "add", "origin", str(remote)], work)
        sh(["git", "push", "-q", "origin", "main"], work)

        print("[4] 模拟 2026-10-20：把 site/ 移出版本库（工作区文件保留）")
        sh(["git", "rm", "-q", "-r", "--cached", "site"], work)
        (work / ".gitignore").write_text("site/\n", encoding="utf-8")
        sh(["git", "add", ".gitignore"], work)
        sh(["git", "commit", "-q", "-m", "chore: stop tracking build output"], work)
        tracked_now = sh(["git", "ls-files", "site"], work).stdout.strip()
        print(f"    本地 HEAD 里 site/ 被跟踪文件数：{len(tracked_now.splitlines()) if tracked_now else 0}")
        assert not tracked_now, "本地 HEAD 不该再跟踪 site/"

        print("[5] 模拟 Actions：远端改动被跟踪的 site/index.html 并推送")
        other = tmp / "other"
        sh(["git", "clone", "-q", str(remote), str(other)], tmp)
        sh(["git", "config", "user.name", "actions"], other)
        sh(["git", "config", "user.email", "actions@example.com"], other)
        (other / "site" / "index.html").write_text("<html>stale remote copy</html>", encoding="utf-8")
        (other / "site" / "sitemap.xml").write_text("<urlset></urlset>", encoding="utf-8")
        sh(["git", "add", "site"], other)
        sh(["git", "commit", "-q", "-m", "actions: refresh site"], other)
        sh(["git", "push", "-q", "origin", "main"], other)
        print("    远端已改 site/index.html + site/sitemap.xml")

        print("[6] 本地落后于远端 + 有待提交的数据改动 -> push 被拒，走合并路径")
        sh(["git", "fetch", "-q", "origin"], work)
        push = sh(["git", "push", "origin", "main"], work, check=False)
        print(f"    push 退出码={push.returncode}（非 0 才会走合并分支）")
        assert push.returncode != 0, "本地落后时 push 应该被拒"
        offers = work / "data" / "offers.json"
        payload = json.loads(offers.read_text(encoding="utf-8"))
        payload["test_marker"] = "merge-path-exercised"
        offers.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        print("[7] 调用 git_sync()")
        sys.path.insert(0, str(work))
        for mod in ("daily", "guard"):
            sys.modules.pop(mod, None)
        import daily  # noqa: E402

        assert daily.ROOT == work.resolve(), f"daily.ROOT 指向了 {daily.ROOT}"
        code, out = daily.git_sync("test")
        print(f"    git_sync -> {code}: {out}")

        print("[8] 核对 site/")
        site_after = sorted(p.relative_to(work).as_posix()
                            for p in (work / "site").rglob("*") if p.is_file())
        index_ok = (work / "site" / "index.html").exists()
        sitemap_ok = (work / "site" / "sitemap.xml").exists()
        worker_ok = (work / "site" / "_worker.js").exists()
        identical = site_before == site_after
        print(f"    site/ 文件数：{len(site_after)}（合并前 {len(site_before)}）")
        print(f"    index.html={index_ok} sitemap.xml={sitemap_ok} _worker.js={worker_ok}")
        print(f"    清单与合并前完全一致：{identical}")
        leftover = [p.name for p in tmp.iterdir() if p.name.startswith("vps-deals-site-")]
        print(f"    临时暂存目录残留：{leftover}")

        # 首页内容不能被远端那份 stale 副本覆盖
        stale = False
        if index_ok:
            stale = "stale remote copy" in (work / "site" / "index.html").read_text(
                encoding="utf-8", errors="replace")
        print(f"    首页被远端旧副本污染：{stale}")

        print()
        if control:
            ok = not (index_ok and sitemap_ok and worker_ok and identical)
            print("RESULT: " + ("PASS" if ok else "FAIL") + " —— 对照实验：修复前应当破坏 site/")
            return 0 if ok else 1
        if not index_ok or not sitemap_ok or not worker_ok or not identical or stale:
            print("RESULT: FAIL —— site/ 被 git 操作破坏或污染")
            return 1
        if code != 0:
            print("RESULT: FAIL —— git_sync 没有成功推送")
            return 1
        print("RESULT: PASS —— 合并路径既保住 site/ 原样，也成功推送")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
