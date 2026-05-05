import socket
import time
from typing import Any, Callable

from 学校配置_profiles.types import SchoolProfile


def portal_reachable(host: str | None, port: int) -> bool:
    if not host:
        return True
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        return True
    except Exception:
        return False


def wait_portal_reachable(profile: SchoolProfile, log: Callable[[str], None]) -> tuple[bool, list[dict[str, Any]]]:
    host = profile.portal.reachable_host
    port = profile.portal.reachable_port
    records: list[dict[str, Any]] = []
    if not host:
        return True, records
    t0 = time.time()
    while time.time() - t0 < profile.portal.wait_sec:
        st = time.perf_counter()
        err = ""
        ok = False
        try:
            ok = portal_reachable(host, port)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            ok = False
        records.append(
            {
                "host": host,
                "port": port,
                "ok": ok,
                "err": err,
                "duration_ms": int((time.perf_counter() - st) * 1000),
                "elapsed_wait_sec": int(time.time() - t0),
            }
        )
        if ok:
            log(f"认证页可达（{host}:{port}）")
            return True, records
        log("认证页不可达，等待中...")
        time.sleep(2)
    return False, records


def safe_goto(page: Any, profile: SchoolProfile, url: str, log: Callable[[str], None]) -> tuple[bool, str]:
    last_err = ""
    for _ in range(profile.portal.goto_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=profile.timing.navigation_timeout_ms)
            return True, ""
        except Exception as e:
            last_err = str(e)
            if "ERR_INTERNET_DISCONNECTED" in last_err or "ERR_NETWORK_CHANGED" in last_err:
                log(f"打开登录页重试: {last_err}")
                time.sleep(2)
                continue
            break
    return False, last_err


def _has_login_form_hint(page: Any, profile: SchoolProfile, timeout_sec: float = 6.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        targets = [page]
        try:
            targets.extend(page.frames)
        except Exception:
            pass

        for target in targets:
            for sel in profile.selectors.username:
                try:
                    if target.locator(sel).count() > 0:
                        return True
                except Exception:
                    continue
        time.sleep(0.2)
    return False


def open_portal(
    page: Any,
    profile: SchoolProfile,
    log: Callable[[str], None],
    preferred_url: str = "",
) -> tuple[bool, str]:
    last_err = "no url candidates"
    urls = list(profile.portal.url_candidates)
    if preferred_url and preferred_url not in urls:
        urls = [preferred_url] + urls
    for u in urls:
        ok, err = safe_goto(page, profile, u, log)
        if ok:
            # Some networks return a placeholder page (for example "test as domain name")
            # at the captive portal host. Treat those as non-login pages and continue.
            if _has_login_form_hint(page, profile):
                return True, u
            last_err = f"login_form_not_found: {u}"
            log(f"打开页面非登录页，尝试下一个候选: {u}")
            continue
        last_err = err or f"goto failed: {u}"
    return False, last_err
