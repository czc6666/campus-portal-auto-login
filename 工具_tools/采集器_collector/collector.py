import json
import os
import platform
import re
import shutil
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

COLLECTOR_VERSION = "2.0.1"

# Screenshot is intentionally disabled.
# Reason: high-frequency screenshots (especially full_page) cause visible page flicker/jitter,
# which hurts end-user operation experience during login.
ENABLE_SCREENSHOT = False


class Collector:
    def __init__(self) -> None:
        self.start_ts = time.strftime("%Y%m%d_%H%M%S")
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="collector_"))
        self.collect_root = self.tmp_dir / "collect"
        self.collect_root.mkdir(parents=True, exist_ok=True)
        (self.collect_root / "frames").mkdir(parents=True, exist_ok=True)
        (self.collect_root / "snapshots").mkdir(parents=True, exist_ok=True)

        self.output_dir = self._pick_output_dir()
        self.output_zip = self.output_dir / f"portal_collect_{self.start_ts}.zip"
        self.log_path = self.collect_root / "collector.log"

        self.last_page_url = "about:blank"
        self.browser_channel = ""
        self.edge_version = ""
        self.timeline: list[dict[str, Any]] = []
        self.nav_chain: list[dict[str, Any]] = []
        self.event_seq = 0
        self.last_snapshot_dir: Path | None = None

    def _pick_output_dir(self) -> Path:
        # 固定优先输出到用户桌面，便于远程指导定位文件。
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            return desktop
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path.cwd()

    def _log(self, msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _safe_write_json(self, path: Path, data: Any) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _append_timeline(self, event_type: str, page_url: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
        self.event_seq += 1
        rec = {
            "seq": self.event_seq,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "url": page_url,
            "detail": detail or {},
        }
        self.timeline.append(rec)
        return rec

    def _sanitize_name(self, s: str) -> str:
        s = re.sub(r"[^0-9a-zA-Z_\\-]+", "_", s)
        return s[:40] if s else "event"

    def _guess_selectors_js(self) -> str:
        return """
() => {
  const all = Array.from(document.querySelectorAll('input,button,a,select'));
  const by = (p) => {
    const out = [];
    for (const el of all) {
      let txt = [
        el.id || '', el.name || '', el.placeholder || '', el.type || '',
        (el.innerText || '').trim(), (el.value || '').trim(), el.className || ''
      ].join(' ').toLowerCase();
      if (!p.some(k => txt.includes(k))) continue;
      let sel = '';
      if (el.id) sel = '#' + el.id;
      else if (el.name) sel = `${el.tagName.toLowerCase()}[name="${el.name}"]`;
      else if (el.placeholder) sel = `${el.tagName.toLowerCase()}[placeholder*="${el.placeholder.slice(0, 20)}"]`;
      else sel = el.tagName.toLowerCase();
      if (sel && !out.includes(sel)) out.push(sel);
      if (out.length >= 8) break;
    }
    return out;
  };
  return {
    username: by(['user','账号','学号','username','userid','ddddd']),
    password: by(['pass','密码','pwd','upass']),
    login: by(['登录','login','连接','认证','上网','submit']),
    operator: by(['运营商','移动','联通','电信','cmcc','unicom','telecom','net_access']),
    captcha: by(['验证码','校验码','captcha','code'])
  };
}
"""

    def _install_action_hooks(self, page) -> None:
        script = """
() => {
  if (window.__collector_installed) return;
  window.__collector_installed = true;
  window.__collector_events = [];
  window.__collector_push = (kind, e) => {
    try {
      const t = e && e.target ? e.target : null;
      const rec = {
        ts: new Date().toISOString(),
        type: kind,
        tag: t ? (t.tagName || '').toLowerCase() : '',
        id: t ? (t.id || '') : '',
        name: t ? (t.name || '') : '',
        typeAttr: t ? (t.type || '') : '',
        placeholder: t ? (t.placeholder || '') : '',
        valuePreview: t && typeof t.value === 'string' ? t.value.slice(0, 32) : '',
        textPreview: t && typeof t.innerText === 'string' ? t.innerText.slice(0, 32) : '',
      };
      window.__collector_events.push(rec);
      if (window.__collector_events.length > 2000) {
        window.__collector_events = window.__collector_events.slice(-1000);
      }
    } catch (_) {}
  };
  document.addEventListener('click', (e) => window.__collector_push('click', e), true);
  document.addEventListener('input', (e) => window.__collector_push('input', e), true);
  document.addEventListener('change', (e) => window.__collector_push('change', e), true);
  document.addEventListener('submit', (e) => window.__collector_push('submit', e), true);
};
"""
        try:
            page.evaluate(script)
        except Exception:
            pass
        try:
            for fr in page.frames:
                try:
                    fr.evaluate(script)
                except Exception:
                    pass
        except Exception:
            pass

    def _drain_action_events(self, page) -> list[dict[str, Any]]:
        js = """
() => {
  const arr = Array.isArray(window.__collector_events) ? window.__collector_events.slice() : [];
  if (Array.isArray(window.__collector_events)) window.__collector_events = [];
  return arr;
}
"""
        out: list[dict[str, Any]] = []
        try:
            rows = page.evaluate(js)
            if isinstance(rows, list):
                out.extend(rows)
        except Exception:
            pass
        try:
            for fr in page.frames:
                try:
                    rows = fr.evaluate(js)
                    if isinstance(rows, list):
                        for r in rows:
                            if isinstance(r, dict):
                                r["_frame_url"] = fr.url
                                r["_frame_name"] = fr.name
                        out.extend(rows)
                except Exception:
                    pass
        except Exception:
            pass
        return out

    def _collect_net_state(self) -> dict[str, Any]:
        from 核心_core.diag import DiagExporter

        d = DiagExporter("collector_netstate", base_dir=str(self.tmp_dir))
        d.dump_net_state_json()
        p = d.dir / "net_state.json"
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "interfaces": [],
                "ipv4": [],
                "default_gateway": [],
                "dns_servers": [],
                "wifi": {"ssid": "", "interface": ""},
            }

    def _capture_snapshot(self, page, event_rec: dict[str, Any]) -> Path:
        tag = self._sanitize_name(event_rec["event_type"])
        snap_dir = self.collect_root / "snapshots" / f"{event_rec['seq']:04d}_{tag}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        if ENABLE_SCREENSHOT:
            page.screenshot(path=str(snap_dir / "screenshot.png"), full_page=True)
        main_html = page.evaluate("document.documentElement.outerHTML")
        (snap_dir / "dom_main.html").write_text(main_html, encoding="utf-8")

        guesses = {"main": {}, "frames": []}
        try:
            guesses["main"] = page.evaluate(self._guess_selectors_js())
        except Exception as e:
            guesses["main"] = {"error": f"{type(e).__name__}: {e}"}

        frames_dir = snap_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for idx, fr in enumerate(page.frames):
            rec = {"index": idx, "name": fr.name, "url": fr.url, "dom_ok": False, "error": ""}
            try:
                html = fr.content()
                (frames_dir / f"{idx:02d}.html").write_text(html, encoding="utf-8")
                rec["dom_ok"] = True
            except Exception as e:
                rec["error"] = f"{type(e).__name__}: {e}"
            self._safe_write_json(frames_dir / f"{idx:02d}_meta.json", rec)

            fg = {"index": idx, "name": fr.name, "url": fr.url}
            try:
                fg["guess"] = fr.evaluate(self._guess_selectors_js())
            except Exception as e:
                fg["error"] = f"{type(e).__name__}: {e}"
            guesses["frames"].append(fg)

        self._safe_write_json(snap_dir / "elements_guess.json", guesses)
        self.last_snapshot_dir = snap_dir
        return snap_dir

    def _copy_latest_snapshot_to_top(self) -> None:
        if not self.last_snapshot_dir or not self.last_snapshot_dir.exists():
            return
        for name in ["dom_main.html", "elements_guess.json"]:
            src = self.last_snapshot_dir / name
            if src.exists():
                shutil.copy2(src, self.collect_root / name)
        src_frames = self.last_snapshot_dir / "frames"
        dst_frames = self.collect_root / "frames"
        if src_frames.exists():
            if dst_frames.exists():
                shutil.rmtree(dst_frames, ignore_errors=True)
            shutil.copytree(src_frames, dst_frames)

    def _write_timeline_jsonl(self) -> None:
        with (self.collect_root / "timeline.jsonl").open("w", encoding="utf-8") as f:
            for rec in self.timeline:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _write_final_files(self) -> None:
        self._safe_write_json(
            self.collect_root / "meta.json",
            {
                "collector_version": COLLECTOR_VERSION,
                "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "os": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                },
                "edge_version": self.edge_version,
                "browser_channel": self.browser_channel,
                "python": sys.version,
                "current_url": self.last_page_url,
                "timeline_event_count": len(self.timeline),
            },
        )
        self._safe_write_json(
            self.collect_root / "urls.json",
            {"current_url": self.last_page_url, "final_url": self.last_page_url, "navigation_chain": self.nav_chain},
        )
        self._safe_write_json(self.collect_root / "net_state.json", self._collect_net_state())
        self._write_timeline_jsonl()
        self._copy_latest_snapshot_to_top()

    def _zip_collect(self) -> None:
        with zipfile.ZipFile(self.output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in self.collect_root.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(self.collect_root))

    def run(self) -> int:
        playwright = None
        browser = None
        context = None
        page = None
        try:
            self._log("采集器启动")
            self._log(f"临时目录: {self.tmp_dir}")
            self._log(f"输出压缩包: {self.output_zip}")
            self._log("正在启动浏览器...")

            from playwright.sync_api import sync_playwright

            playwright = sync_playwright().start()
            try:
                browser = playwright.chromium.launch(channel="msedge", headless=False)
                self.browser_channel = "msedge"
            except Exception:
                browser = playwright.chromium.launch(headless=False)
                self.browser_channel = "chromium_fallback"

            try:
                self.edge_version = browser.version
            except Exception:
                self.edge_version = ""

            context = browser.new_context()
            page = context.new_page()
            page.goto("about:blank", wait_until="domcontentloaded")
            self.last_page_url = page.url

            def on_framenavigated(frame):
                if frame == page.main_frame:
                    self.last_page_url = frame.url
                    nav = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "url": frame.url, "event": "main_frame_navigated"}
                    self.nav_chain.append(nav)
                    rec = self._append_timeline("navigate", frame.url, nav)
                    try:
                        self._capture_snapshot(page, rec)
                        rec["snapshot"] = str((self.last_snapshot_dir or Path("")).relative_to(self.collect_root))
                    except Exception as e:
                        rec["snapshot_error"] = f"{type(e).__name__}: {e}"

            page.on("framenavigated", on_framenavigated)
            start = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "url": page.url,
                "event": "browser_started",
                "browser_channel": self.browser_channel,
            }
            self.nav_chain.append(start)
            rec0 = self._append_timeline("browser_started", page.url, start)
            self._capture_snapshot(page, rec0)
            rec0["snapshot"] = str((self.last_snapshot_dir or Path("")).relative_to(self.collect_root))

            self._log("浏览器已打开。请按平时习惯操作并在完成后关闭浏览器。")

            last_tick = 0.0
            last_tick_url = ""
            empty_pages_since = None
            while browser.is_connected():
                pages = context.pages
                if pages:
                    empty_pages_since = None
                    page = pages[-1]
                    self.last_page_url = page.url
                else:
                    if empty_pages_since is None:
                        empty_pages_since = time.time()
                        self._log("检测到浏览器页面已全部关闭，等待最终确认...")
                    elif time.time() - empty_pages_since >= 2.0:
                        self._log("确认所有页面已关闭，准备结束采集。")
                        break

                if page and not page.is_closed():
                    self._install_action_hooks(page)
                    actions = self._drain_action_events(page)
                    for a in actions:
                        detail = {
                            "action": a.get("type", ""),
                            "tag": a.get("tag", ""),
                            "id": a.get("id", ""),
                            "name": a.get("name", ""),
                            "typeAttr": a.get("typeAttr", ""),
                            "placeholder": a.get("placeholder", ""),
                            "valuePreview": a.get("valuePreview", ""),
                            "textPreview": a.get("textPreview", ""),
                            "frame_url": a.get("_frame_url", ""),
                            "frame_name": a.get("_frame_name", ""),
                            "source_ts": a.get("ts", ""),
                        }
                        rec = self._append_timeline("action", self.last_page_url, detail)
                        try:
                            self._capture_snapshot(page, rec)
                            rec["snapshot"] = str((self.last_snapshot_dir or Path("")).relative_to(self.collect_root))
                        except Exception as e:
                            rec["snapshot_error"] = f"{type(e).__name__}: {e}"

                now = time.time()
                need_tick = (self.last_page_url != last_tick_url) or (now - last_tick >= 2.0)
                if page and not page.is_closed() and need_tick:
                    rec = self._append_timeline("tick", self.last_page_url, {"reason": "periodic_or_url_changed"})
                    try:
                        self._capture_snapshot(page, rec)
                        rec["snapshot"] = str((self.last_snapshot_dir or Path("")).relative_to(self.collect_root))
                    except Exception as e:
                        rec["snapshot_error"] = f"{type(e).__name__}: {e}"
                    last_tick = now
                    last_tick_url = self.last_page_url

                time.sleep(0.35)

            self._append_timeline("browser_closed", self.last_page_url, {})
            self._log("浏览器已关闭，正在生成采集包...")
            self._write_final_files()
            self._zip_collect()
            self._log(f"采集完成，压缩包已生成：{self.output_zip}")
            return 0
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            self._log(f"采集过程出现异常: {err}")
            self._log(traceback.format_exc())
            try:
                self._safe_write_json(self.collect_root / "collector_error.json", {"error": err, "traceback": traceback.format_exc()})
                self._write_final_files()
                self._zip_collect()
                self._log(f"已输出部分结果：{self.output_zip}")
            except Exception as inner:
                self._log(f"异常收尾失败: {inner}")
            return 1
        finally:
            try:
                if context:
                    context.close()
            except Exception:
                pass
            try:
                if browser:
                    browser.close()
            except Exception:
                pass
            try:
                if playwright:
                    playwright.stop()
            except Exception:
                pass


def main() -> None:
    code = Collector().run()
    # 给用户留 2 秒看到结果，然后自动关闭控制台
    time.sleep(2)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
