import subprocess
import time
from typing import Callable

from 学校配置_profiles.types import SchoolProfile


def _run_netsh(args: list[str]) -> tuple[int, str]:
    cp = subprocess.run(["netsh"] + args, capture_output=True)
    raw = (cp.stdout or b"") + (cp.stderr or b"")
    txt = raw.decode("utf-8", "ignore")
    if not txt.strip():
        txt = raw.decode("gbk", "ignore")
    return cp.returncode, txt


def _wifi_info() -> tuple[bool, str, str]:
    rc, txt = _run_netsh(["wlan", "show", "interfaces"])
    if rc != 0 or not txt.strip():
        return False, "", ""
    state = ""
    ssid = ""
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.lower().startswith("state") or s.startswith("状态"):
            parts = s.split(":", 1)
            if len(parts) == 2:
                state = parts[1].strip()
        if s.lower().startswith("ssid") and "bssid" not in s.lower():
            parts = s.split(":", 1)
            if len(parts) == 2:
                ssid = parts[1].strip()
    return True, state, ssid


def _netsh_connect(ssid: str, timeout_sec: int, log: Callable[[str], None]) -> bool:
    has_wlan, state, cur_ssid = _wifi_info()
    if not has_wlan:
        log("未检测到 WLAN 网卡，跳过 Wi-Fi 重连。")
        return False

    # 校园网常见状态是“已连上目标 SSID，但未认证导致外网探针离线”。
    # 这种情况下不能反复 netsh connect，否则会把当前 Wi-Fi 拉断重连。
    if cur_ssid == ssid:
        if "connected" in state.lower() or "已连接" in state:
            log(f"Wi-Fi 已连接：{ssid}")
        else:
            log(f"Wi-Fi 当前已在目标 SSID 上，跳过重连：{ssid} ({state or 'unknown'})")
        return True

    rc, _ = _run_netsh(["wlan", "connect", f"name={ssid}"])
    log(f"netsh 连接返回码={rc}")

    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        _, state, cur_ssid = _wifi_info()
        if cur_ssid == ssid and ("connected" in state.lower() or "已连接" in state):
            log(f"Wi-Fi 连接成功：{ssid}")
            return True
        time.sleep(1)
    log("Wi-Fi 连接超时")
    return False


def _pywifi_connect(ssid: str, timeout_sec: int, log: Callable[[str], None]) -> bool:
    try:
        import pywifi
    except Exception:
        log("未安装 pywifi，跳过 Wi-Fi 重连。")
        return False

    try:
        wifi = pywifi.PyWiFi()
        if not wifi.interfaces():
            log("未检测到无线网卡接口，跳过 Wi-Fi 重连。")
            return False
        iface = wifi.interfaces()[0]
        iface.scan()
        time.sleep(2)
        for item in iface.scan_results():
            if item.ssid == ssid:
                profile = pywifi.Profile()
                profile.ssid = ssid
                profile.auth = pywifi.const.AUTH_ALG_OPEN
                tmp_profile = iface.add_network_profile(profile)
                iface.connect(tmp_profile)
                t0 = time.time()
                while time.time() - t0 < timeout_sec:
                    if iface.status() == pywifi.const.IFACE_CONNECTED:
                        log(f"Wi-Fi 连接成功：{ssid}")
                        return True
                    time.sleep(1)
                log("Wi-Fi 连接超时")
                return False
        log(f"未扫描到目标 Wi-Fi：{ssid}")
        return False
    except Exception as e:
        log(f"pywifi 连接失败: {e}")
        return False


def ensure_wifi_connected(profile: SchoolProfile, log: Callable[[str], None]) -> bool:
    provider = profile.wifi.provider
    ssid = profile.wifi.ssid
    if provider == "none" or not ssid:
        return False
    if provider == "netsh":
        return _netsh_connect(ssid, profile.wifi.connect_timeout_sec, log)
    if provider == "pywifi":
        return _pywifi_connect(ssid, profile.wifi.connect_timeout_sec, log)
    log(f"未知 Wi-Fi provider: {provider}")
    return False
