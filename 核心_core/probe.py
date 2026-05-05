import json
import time
import urllib.parse
import urllib.request
from typing import Any

from 核心_core.types import ProbeResult
from 学校配置_profiles.types import SchoolProfile


def _host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").lower()


def _http_get(url: str, timeout_sec: int):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    return urllib.request.urlopen(req, timeout=timeout_sec)


def check_online_detailed(profile: SchoolProfile, limit: int = 8) -> tuple[ProbeResult, list[dict[str, Any]]]:
    timeout_sec = profile.timing.probe_timeout_sec
    mode = profile.probe.mode
    attempts: list[dict[str, Any]] = []

    if mode == "single" and profile.probe.urls:
        url = profile.probe.urls[0]
        t0 = time.perf_counter()
        try:
            r = _http_get(url, timeout_sec)
            code = getattr(r, "status", 200)
            ok = code in (200, 204, 301, 302)
            reason = f"single:{code}"
            attempts.append(
                {
                    "url": url,
                    "ok": ok,
                    "reason": reason,
                    "duration_ms": int((time.perf_counter() - t0) * 1000),
                }
            )
            return ProbeResult(ok, reason), attempts[-limit:]
        except Exception as e:
            reason = f"single:{type(e).__name__}: {e}"
            attempts.append(
                {
                    "url": url,
                    "ok": False,
                    "reason": reason,
                    "duration_ms": int((time.perf_counter() - t0) * 1000),
                }
            )
            return ProbeResult(False, reason), attempts[-limit:]

    t = int(time.time())
    probes = [
        ("g204", "http://connectivitycheck.gstatic.com/generate_204", "generate_204", "code204"),
        ("bili_api", f"https://api.bilibili.com/x/web-interface/nav?ts={t}", "api.bilibili.com", "json"),
        ("bili_web", f"https://www.bilibili.com/?ts={t}", "www.bilibili.com", "html"),
        ("baidu", f"https://www.baidu.com/?ts={t}", "baidu.com", "code"),
    ]
    if profile.probe.urls:
        probes = [("custom", profile.probe.urls[0], _host(profile.probe.urls[0]), "code")] + probes

    last_err = "all probes failed"
    portal_host = (profile.portal.reachable_host or "").lower()
    g204_tentative = False
    bili_ok = False
    baidu_ok = False

    def online_reason() -> str | None:
        if bili_ok and baidu_ok:
            return "bili+baidu:ok" if not g204_tentative else "g204+bili+baidu:ok"
        return None

    for name, url, expect_host, kind in probes:
        t0 = time.perf_counter()
        try:
            r = _http_get(url, timeout_sec)
            code = getattr(r, "status", 200)
            final_url = getattr(r, "geturl", lambda: url)()
            final_host = _host(final_url)
            ctype = (r.headers.get("Content-Type") or "").lower()
            duration_ms = int((time.perf_counter() - t0) * 1000)

            if portal_host and portal_host in final_host:
                last_err = f"{name}: captive redirect {final_url}"
                attempts.append(
                    {
                        "url": url,
                        "ok": False,
                        "reason": last_err,
                        "duration_ms": duration_ms,
                    }
                )
                return ProbeResult(False, last_err), attempts[-limit:]
            if "portal" in final_url or "webauth" in final_url or "drcom" in final_url or "srun" in final_url:
                last_err = f"{name}: captive redirect {final_url}"
                attempts.append(
                    {
                        "url": url,
                        "ok": False,
                        "reason": last_err,
                        "duration_ms": duration_ms,
                    }
                )
                return ProbeResult(False, last_err), attempts[-limit:]
            if expect_host and expect_host not in final_host and kind != "code204":
                last_err = f"{name}: redirected to {final_host or final_url}"
                attempts.append(
                    {
                        "url": url,
                        "ok": False,
                        "reason": last_err,
                        "duration_ms": duration_ms,
                    }
                )
                continue

            if kind == "code204":
                if code == 204:
                    g204_tentative = True
                    attempts.append(
                        {
                            "url": url,
                            "ok": True,
                            "reason": f"{name}:204_tentative",
                            "duration_ms": duration_ms,
                        }
                    )
                    continue
                last_err = f"{name}: http {code}"
                attempts.append(
                    {
                        "url": url,
                        "ok": False,
                        "reason": last_err,
                        "duration_ms": duration_ms,
                    }
                )
                continue

            body = r.read(2000)
            duration_ms = int((time.perf_counter() - t0) * 1000)

            if kind == "json":
                if "json" not in ctype:
                    last_err = f"{name}: content-type {ctype or 'unknown'}"
                    attempts.append(
                        {
                            "url": url,
                            "ok": False,
                            "reason": last_err,
                            "duration_ms": duration_ms,
                        }
                    )
                    continue
                data = json.loads(body.decode("utf-8", "ignore"))
                if isinstance(data, dict) and data.get("code") == 0:
                    bili_ok = True
                    reason = online_reason() or f"{name}:code=0"
                    attempts.append(
                        {
                            "url": url,
                            "ok": True,
                            "reason": reason,
                            "duration_ms": duration_ms,
                        }
                    )
                    if reason.endswith(":ok"):
                        return ProbeResult(True, reason), attempts[-limit:]
                    continue
                last_err = f"{name}: bad json code"
                attempts.append(
                    {
                        "url": url,
                        "ok": False,
                        "reason": last_err,
                        "duration_ms": duration_ms,
                    }
                )
                continue

            if kind == "html":
                text = body.decode("utf-8", "ignore").lower()
                if "bilibili" in text:
                    bili_ok = True
                    reason = online_reason() or f"{name}:html"
                    attempts.append(
                        {
                            "url": url,
                            "ok": True,
                            "reason": reason,
                            "duration_ms": duration_ms,
                        }
                    )
                    if reason.endswith(":ok"):
                        return ProbeResult(True, reason), attempts[-limit:]
                    continue
                last_err = f"{name}: html mismatch"
                attempts.append(
                    {
                        "url": url,
                        "ok": False,
                        "reason": last_err,
                        "duration_ms": duration_ms,
                    }
                )
                continue

            if code in (200, 204, 301, 302):
                if name == "baidu":
                    baidu_ok = True
                reason = online_reason() or f"{name}:http={code}"
                attempts.append(
                    {
                        "url": url,
                        "ok": True,
                        "reason": reason,
                        "duration_ms": duration_ms,
                    }
                )
                if reason.endswith(":ok"):
                    return ProbeResult(True, reason), attempts[-limit:]
                continue

            last_err = f"{name}: http {code}"
            attempts.append(
                {
                    "url": url,
                    "ok": False,
                    "reason": last_err,
                    "duration_ms": duration_ms,
                }
            )
        except Exception as e:
            last_err = f"{name}: {type(e).__name__}: {e}"
            attempts.append(
                {
                    "url": url,
                    "ok": False,
                    "reason": last_err,
                    "duration_ms": int((time.perf_counter() - t0) * 1000),
                }
            )

    if g204_tentative:
        if bili_ok and not baidu_ok:
            last_err = "g204+bili_without_baidu"
        elif baidu_ok and not bili_ok:
            last_err = "g204+baidu_without_bili"
        else:
            last_err = "g204_without_bili_and_baidu"
        attempts.append(
            {
                "url": "http://connectivitycheck.gstatic.com/generate_204",
                "ok": False,
                "reason": last_err,
                "duration_ms": 0,
            }
        )
    elif bili_ok and not baidu_ok:
        last_err = "bili_without_baidu"
    elif baidu_ok and not bili_ok:
        last_err = "baidu_without_bili"

    return ProbeResult(False, last_err), attempts[-limit:]


def check_online(profile: SchoolProfile) -> ProbeResult:
    result, _ = check_online_detailed(profile)
    return result
