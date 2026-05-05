import time
from typing import Any

from playwright.sync_api import sync_playwright

from 核心_core.actions import captcha_detected, choose_operator, set_input, submit_login, wait_for_login_form
from 核心_core.browser import launch_browser
from 核心_core.diag import DiagExporter
from 核心_core.portal import open_portal, wait_portal_reachable
from 核心_core.probe import check_online, check_online_detailed
from 核心_core.types import LoginResult
from 核心_core.wifi import ensure_wifi_connected
from 学校配置_profiles.types import SchoolProfile


def _extract_captive_url(reason: str) -> str:
    marker = "captive redirect "
    if not reason:
        return ""
    pos = reason.lower().find(marker)
    if pos < 0:
        return ""
    url = reason[pos + len(marker) :].strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return ""


def _page_shows_auth_failure(page: Any) -> tuple[bool, str]:
    try:
        text = page.locator("body").inner_text(timeout=2000)
    except Exception:
        return False, ""

    normalized = text.replace(" ", "").replace("\r", "").replace("\n", "")
    markers = [
        "AC认证失败",
        "认证失败",
        "登录失败",
        "用户名或密码错误",
        "密码错误",
    ]
    for marker in markers:
        if marker in normalized:
            return True, marker
    return False, ""


def _maybe_finish_post_submit_service_selection(
    page: Any,
    profile: SchoolProfile,
    diag: DiagExporter,
    attempts: dict[str, Any],
) -> tuple[bool, str]:
    if not profile.operator_value or not profile.selectors.operator:
        return True, "skip"

    deadline = time.time() + 8
    while time.time() < deadline:
        current_url = ""
        body_text = ""
        try:
            current_url = page.url or ""
        except Exception:
            current_url = ""
        try:
            body_text = page.locator("body").inner_text(timeout=1000)
        except Exception:
            body_text = ""

        if "serviceSelection" not in current_url and "请选择服务" not in body_text:
            time.sleep(0.3)
            continue

        op_ok, op_why = choose_operator(page, profile)
        diag.event("operator", "choose_post_submit", op_ok, detail=op_why)
        attempts["steps"].append({"phase": "operator_post_submit", "ok": op_ok, "detail": op_why})
        if not op_ok:
            return False, "post_submit_operator_failed"

        page.wait_for_timeout(500)

        submit_ok, submit_why = submit_login(page, profile)
        diag.event("submit", "confirm_service", submit_ok, detail=submit_why)
        attempts["steps"].append({"phase": "submit_post_submit", "ok": submit_ok, "detail": submit_why})
        if not submit_ok:
            return False, "post_submit_confirm_failed"

        return True, "service_selection_confirmed"

    return True, "skip"


def _event(diag: DiagExporter, phase: str, action: str, fn):
    t0 = time.perf_counter()
    try:
        ret = fn()
        diag.event(phase, action, True, duration_ms=int((time.perf_counter() - t0) * 1000))
        return ret
    except Exception as e:
        diag.event(phase, action, False, error=f"{type(e).__name__}: {e}", duration_ms=int((time.perf_counter() - t0) * 1000))
        raise


def _finalize_diag(diag: DiagExporter, page: Any = None, attempts: dict[str, Any] | None = None, system_cmd_enabled: bool = False):
    diag.dump_probe_json()
    diag.dump_portal_check_json()
    diag.dump_net_state_json()
    if attempts:
        diag.dump_attempts_json(attempts)
    if page is not None:
        diag.save_page(page)
        diag.save_frames(page)
    diag.dump_system_net_diag(enabled=system_cmd_enabled)


def _fail(
    diag: DiagExporter,
    profile: SchoolProfile,
    phase: str,
    reason: str,
    page: Any = None,
    needs_manual: bool = False,
    attempts: dict[str, Any] | None = None,
    system_cmd_enabled: bool = False,
) -> LoginResult:
    if not profile.export_diag_on_fail:
        diag.log(f"❌ {phase}: {reason}")
        diag.log("已关闭故障归档导出")
        diag.cleanup()
        return LoginResult(False, phase, reason, "", needs_manual)

    _finalize_diag(diag, page=page, attempts=attempts, system_cmd_enabled=system_cmd_enabled)
    if page is not None:
        diag.event(phase, "browser_artifacts", True, detail="final.png/final.html/frames")
    diag.log(f"❌ {phase}: {reason}")
    diag.log(f"DIAG导出: {diag.dir}")
    return LoginResult(False, phase, reason, str(diag.dir), needs_manual)


def run_login_once(profile: SchoolProfile, username: str, password: str, allow_system_net_diag: bool = False) -> LoginResult:
    diag = DiagExporter(profile.id)
    diag.dump_meta({"profile": profile, "username": username})
    diag.log(f"开始登录流程: {profile.name}")
    diag.event("init", "login_start", True, school=profile.id)

    attempts: dict[str, Any] = {"steps": []}
    pre_probe, pre_probe_rows = check_online_detailed(profile, limit=8)
    preferred_portal_url = _extract_captive_url(pre_probe.reason)
    diag.append_probe_history(pre_probe_rows)
    diag.event("probe", "pre_login", pre_probe.online, reason=pre_probe.reason)
    attempts["steps"].append({"phase": "probe_pre", "ok": pre_probe.online, "reason": pre_probe.reason})

    portal_ok, portal_rows = wait_portal_reachable(profile, diag.log)
    diag.append_portal_checks(portal_rows)
    diag.event(
        "portal_wait",
        "reachable_check",
        portal_ok,
        attempts=len(portal_rows),
        timeout_sec=profile.portal.wait_sec,
    )
    attempts["steps"].append({"phase": "portal_wait", "ok": portal_ok, "attempts": len(portal_rows)})
    if not portal_ok:
        diag.event("timeout", "portal_wait_timeout", False, waited_sec=profile.portal.wait_sec)
        return _fail(
            diag,
            profile,
            "portal",
            "portal_not_reachable",
            attempts=attempts,
            system_cmd_enabled=allow_system_net_diag,
        )

    page = None
    browser = None
    try:
        with sync_playwright() as p:
            browser, browser_name = _event(
                diag, "browser", "launch", lambda: launch_browser(p, profile.browser.mode, profile.browser.headless)
            )
            browser_obj, browser_kind = browser, browser_name
            browser = browser_obj
            diag.log(f"当前浏览器: {browser_kind}")

            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(profile.timing.action_timeout_ms)
            page.set_default_navigation_timeout(profile.timing.navigation_timeout_ms)

            ok, detail = _event(
                diag,
                "portal",
                "open",
                lambda: open_portal(page, profile, diag.log, preferred_url=preferred_portal_url),
            )
            attempts["steps"].append({"phase": "portal_open", "ok": ok, "detail": detail})
            if not ok:
                return _fail(
                    diag,
                    profile,
                    "portal",
                    detail,
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )
            diag.log(f"打开登录页: {detail}")

            found, target, hit = wait_for_login_form(page, profile, profile.timing.action_timeout_ms)
            if not found:
                attempts["steps"].append({"phase": "selectors", "ok": False, "detail": "username_selector_not_found"})
                return _fail(
                    diag,
                    profile,
                    "selectors",
                    "username_selector_not_found",
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )
            diag.event("selectors", "wait_login_form", True, selector=hit)
            attempts["steps"].append({"phase": "selectors", "ok": True, "selector": hit})

            u_ok, u_why = set_input(target, profile.selectors.username, username, profile.input.mode)
            diag.event("fill", "username", u_ok, detail=u_why)
            if not u_ok:
                attempts["steps"].append({"phase": "fill_username", "ok": False, "detail": u_why})
                return _fail(
                    diag,
                    profile,
                    "fill",
                    "fill_username_failed",
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )
            attempts["steps"].append({"phase": "fill_username", "ok": True, "detail": u_why})

            p_ok, p_why = set_input(target, profile.selectors.password, password, profile.input.mode)
            diag.event("fill", "password", p_ok, detail=p_why)
            if not p_ok:
                attempts["steps"].append({"phase": "fill_password", "ok": False, "detail": p_why})
                return _fail(
                    diag,
                    profile,
                    "fill",
                    "fill_password_failed",
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )
            attempts["steps"].append({"phase": "fill_password", "ok": True, "detail": p_why})

            op_ok, op_why = choose_operator(target, profile)
            diag.event("operator", "choose", op_ok, detail=op_why)
            attempts["steps"].append({"phase": "operator", "ok": op_ok, "detail": op_why})

            if captcha_detected(target, profile):
                attempts["steps"].append({"phase": "captcha", "ok": False, "detail": "captcha_detected"})
                return _fail(
                    diag,
                    profile,
                    "captcha",
                    "captcha_detected",
                    page=page,
                    needs_manual=True,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )

            submit_ok, submit_why = submit_login(target, profile)
            diag.event("submit", "login", submit_ok, detail=submit_why)
            if not submit_ok:
                attempts["steps"].append({"phase": "submit", "ok": False, "detail": submit_why})
                return _fail(
                    diag,
                    profile,
                    "submit",
                    submit_why,
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )
            attempts["steps"].append({"phase": "submit", "ok": True, "detail": submit_why})

            post_service_ok, post_service_why = _maybe_finish_post_submit_service_selection(page, profile, diag, attempts)
            if not post_service_ok:
                return _fail(
                    diag,
                    profile,
                    "service_selection",
                    post_service_why,
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )

            page.wait_for_timeout(profile.timing.login_wait_sec * 1000)
            diag.event("wait", "post_login", True, seconds=profile.timing.login_wait_sec)
            attempts["steps"].append({"phase": "wait_post_login", "ok": True, "seconds": profile.timing.login_wait_sec})

            auth_fail, auth_fail_marker = _page_shows_auth_failure(page)
            diag.event("page_check", "auth_failure", not auth_fail, detail=auth_fail_marker or "not_detected")
            if auth_fail:
                attempts["steps"].append({"phase": "page_auth_fail", "ok": False, "detail": auth_fail_marker})
                return _fail(
                    diag,
                    profile,
                    "page",
                    auth_fail_marker,
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )

            probe, probe_rows = check_online_detailed(profile, limit=8)
            diag.append_probe_history(probe_rows)
            diag.event("probe", "post_login", probe.online, reason=probe.reason)
            if not probe.online:
                attempts["steps"].append({"phase": "probe_post", "ok": False, "reason": probe.reason})
                return _fail(
                    diag,
                    profile,
                    "probe",
                    probe.reason,
                    page=page,
                    attempts=attempts,
                    system_cmd_enabled=allow_system_net_diag,
                )
            attempts["steps"].append({"phase": "probe_post", "ok": True, "reason": probe.reason})

            diag.log("✅ 登录成功")
            diag.cleanup()
            return LoginResult(True, "done", probe.reason, "", False)
    except Exception as e:
        attempts["steps"].append({"phase": "exception", "ok": False, "detail": f"{type(e).__name__}: {e}"})
        return _fail(
            diag,
            profile,
            "exception",
            f"{type(e).__name__}: {e}",
            page=page,
            attempts=attempts,
            system_cmd_enabled=allow_system_net_diag,
        )
    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass


def run_profile(profile: SchoolProfile, creds: dict[str, str], once: bool = False) -> None:
    last_state = None
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 启动完成，正在检测网络状态...",
        flush=True,
    )
    while True:
        probe = check_online(profile)
        state = "ONLINE" if probe.online else "OFFLINE"
        if state != last_state:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 网络状态变化: {state} ({probe.reason})", flush=True)
            last_state = state
        else:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 网络状态: {state} ({probe.reason})",
                flush=True,
            )

        if not probe.online:
            ensure_wifi_connected(profile, lambda m: print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {m}", flush=True))
            result = run_login_once(profile, creds["username"], creds["password"])
            if not result.success:
                time.sleep(profile.timing.retry_cooldown_sec)

        if once:
            return
        time.sleep(profile.timing.check_interval_sec)
