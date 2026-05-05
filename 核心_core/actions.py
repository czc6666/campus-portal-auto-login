import time
from typing import Any

from 学校配置_profiles.types import SchoolProfile


def _iter_targets(page: Any, profile: SchoolProfile):
    yield page
    if profile.frame.mode != "first_matching_frame":
        return
    try:
        for fr in page.frames:
            yield fr
    except Exception:
        return


def _visible_count(target: Any, selector: str) -> int:
    try:
        loc = target.locator(selector)
        cnt = loc.count()
        if cnt > 0 and loc.first.is_visible():
            return cnt
    except Exception:
        return 0
    return 0


def wait_for_login_form(page: Any, profile: SchoolProfile, timeout_ms: int) -> tuple[bool, Any, str]:
    end = time.time() + timeout_ms / 1000.0
    while time.time() < end:
        for target in _iter_targets(page, profile):
            for sel in profile.selectors.username:
                if _visible_count(target, sel) > 0:
                    return True, target, sel
        time.sleep(0.3)
    return False, page, ""


def _set_by_js(target: Any, selector: str, value: str) -> bool:
    try:
        return bool(
            target.evaluate(
                """(p)=>{
                    const el=document.querySelector(p.sel);
                    if(!el) return false;
                    el.focus();
                    el.value=p.val;
                    el.dispatchEvent(new Event('input',{bubbles:true}));
                    el.dispatchEvent(new Event('change',{bubbles:true}));
                    return true;
                }""",
                {"sel": selector, "val": value},
            )
        )
    except Exception:
        return False


def set_input(target: Any, selectors: list[str], value: str, mode: str) -> tuple[bool, str]:
    for sel in selectors:
        try:
            if mode == "js_first":
                if _set_by_js(target, sel, value):
                    return True, f"js:{sel}"
                if _visible_count(target, sel) == 0:
                    continue
                target.fill(sel, value)
                return True, f"fill:{sel}"

            if _visible_count(target, sel) == 0:
                continue

            if mode == "keyboard":
                loc = target.locator(sel).first
                loc.click(timeout=2000)
                loc.press("Control+A", timeout=2000)
                loc.type(value, delay=40, timeout=4000)
                return True, f"kbd:{sel}"

            try:
                target.fill(sel, value)
                return True, f"fill:{sel}"
            except Exception:
                if _set_by_js(target, sel, value):
                    return True, f"js:{sel}"
        except Exception:
            continue
    return False, ""


def choose_operator(target: Any, profile: SchoolProfile) -> tuple[bool, str]:
    if not profile.operator_value or not profile.selectors.operator:
        return True, "skip"

    # Common eportal pages render service options inside a collapsed panel and
    # expose a selectService(...) helper instead of plain visible controls.
    try:
        target.evaluate(
            """() => {
                const openers = [
                    '#serviceShowHideTop',
                    '#defaultService',
                    '#selectDisname',
                    '#xiala',
                    '#service_left',
                ];
                for (const sel of openers) {
                    const el = document.querySelector(sel);
                    if (el) {
                        try { el.click(); } catch (_) {}
                    }
                }
            }"""
        )
    except Exception:
        pass

    for sel in profile.selectors.operator:
        try:
            if "{value}" in sel:
                sel = sel.replace("{value}", profile.operator_value)
            if _visible_count(target, sel) > 0:
                try:
                    target.check(sel, timeout=3000)
                except Exception:
                    target.click(sel, timeout=3000)
                return True, sel
        except Exception:
            continue

    try:
        ok = bool(
            target.evaluate(
                """(p) => {
                    const label = p.label || '';
                    const indexMap = { '校园网': '0', '移动': '1', '联通': '2', '电信': '3' };
                    const serviceName = label === '校园网' ? 'default' : label;
                    const idx = indexMap[label];
                    if (typeof window.selectService === 'function' && idx != null) {
                        try {
                            window.selectService(serviceName, label, idx);
                        } catch (_) {
                            return false;
                        }
                    } else {
                        const hidden = document.querySelector('#net_access_type, input[name="net_access_type"]');
                        if (!hidden) return false;
                        hidden.value = serviceName;
                        const dis = document.querySelector('#selectDisname');
                        if (dis) dis.textContent = label;
                    }
                    const hidden = document.querySelector('#net_access_type, input[name="net_access_type"]');
                    return !!hidden && hidden.value === serviceName;
                }""",
                {"label": profile.operator_value},
            )
        )
        if ok:
            return True, f"js:selectService:{profile.operator_value}"
    except Exception:
        pass
    return False, "operator_not_found"


def captcha_detected(target: Any, profile: SchoolProfile) -> bool:
    for sel in profile.selectors.captcha:
        if _visible_count(target, sel) > 0:
            return True
    return False


def submit_login(target: Any, profile: SchoolProfile) -> tuple[bool, str]:
    if profile.submit.mode == "keyboard_tab_enter":
        def _get_keyboard() -> Any | None:
            kb = getattr(target, "keyboard", None)
            if kb is not None:
                return kb
            try:
                return target.page.keyboard
            except Exception:
                return None

        def _active_is_login_button() -> bool:
            try:
                return bool(
                    target.evaluate(
                        """(p) => {
                            const active = document.activeElement;
                            if (!active) return false;
                            for (const sel of (p.selectors || [])) {
                                const btn = document.querySelector(sel);
                                if (btn && (active === btn || btn.contains(active))) return true;
                            }
                            const hint = `${active.getAttribute('value') || ''} ${active.innerText || ''} ${active.textContent || ''}`.toLowerCase();
                            if (hint.includes('登录')) return true;
                            const oc = (active.getAttribute('onclick') || '').toLowerCase();
                            if (oc.includes('ee(')) return true;
                            return false;
                        }""",
                        {"selectors": profile.selectors.login_button},
                    )
                )
            except Exception:
                return False

        try:
            kb = _get_keyboard()
            if kb is None:
                return False, "keyboard_no_driver"

            if _active_is_login_button():
                kb.press("Enter")
                return True, "keyboard_focus_enter"

            for i in range(8):
                kb.press("Tab")
                time.sleep(0.06)
                if _active_is_login_button():
                    kb.press("Enter")
                    return True, f"keyboard_tab_enter:{i + 1}"

            kb.press("Enter")
            return True, "keyboard_enter_fallback"
        except Exception:
            return False, "keyboard_tab_enter_fail"

    def _press_enter_on_password() -> bool:
        try:
            target.locator("input[type=password], #pwd, #password, input[name='upass']").first.press("Enter", timeout=1500)
            return True
        except Exception:
            return False

    def _dispatch_dom_click(sel: str) -> bool:
        try:
            return bool(
                target.evaluate(
                    """(p) => {
                        const el = document.querySelector(p.sel);
                        if (!el) return false;
                        try { el.focus(); } catch (_) {}
                        try { el.click(); } catch (_) {}
                        try { el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window })); } catch (_) {}
                        const oc = (el.getAttribute('onclick') || '').trim();
                        if (oc) {
                            try {
                                const code = oc.replace(/^javascript\\s*:/i, '');
                                (new Function(code))();
                            } catch (_) {}
                        }
                        return true;
                    }""",
                    {"sel": sel},
                )
            )
        except Exception:
            return False

    def _invoke_portal_login_script() -> bool:
        try:
            return bool(
                target.evaluate(
                    """() => {
                        if (typeof window.ee === 'function') {
                            try { window.ee(1); return true; } catch (_) {}
                        }
                        return false;
                    }"""
                )
            )
        except Exception:
            return False

    for sel in profile.selectors.login_button:
        try:
            if _visible_count(target, sel) > 0:
                try:
                    target.locator(sel).first.click(timeout=5000)
                except Exception:
                    if not _dispatch_dom_click(sel):
                        continue

                # Some portals on specific machines need an additional trigger
                # (DOM click/onclick or Enter) even when Playwright click succeeds.
                if profile.submit.mode == "click_then_enter":
                    _dispatch_dom_click(sel)
                    _invoke_portal_login_script()
                    _press_enter_on_password()
                return True, f"click:{sel}"
        except Exception:
            continue
    if _invoke_portal_login_script():
        return True, "invoke:ee(1)"
    if _press_enter_on_password():
        return True, "enter_on_password"
    return False, "submit_failed"
