import json
import os
import shutil
import socket
import subprocess
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


class DiagExporter:
    def __init__(self, school_id: str, base_dir: str = "故障归档_cases") -> None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        self.dir = Path(base_dir) / f"{ts}_{school_id}"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.dir / "events.jsonl"
        self.log_path = self.dir / "runtime.log"
        self._probe_history: list[dict[str, Any]] = []
        self._portal_checks: list[dict[str, Any]] = []
        self.events_path.touch(exist_ok=True)

    def _to_jsonable(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {}
        payload: dict[str, Any] = {}
        for k, v in data.items():
            if is_dataclass(v):
                payload[k] = asdict(v)
            else:
                payload[k] = v
        return payload

    def log(self, msg: str) -> None:
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        print(line, flush=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + os.linesep)

    def event(self, phase: str, action: str, ok: bool, **extra: Any) -> None:
        rec = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": phase,
            "action": action,
            "ok": ok,
            **extra,
        }
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def dump_meta(self, meta: dict[str, Any]) -> None:
        with (self.dir / "meta.json").open("w", encoding="utf-8") as f:
            json.dump(self._to_jsonable(meta), f, ensure_ascii=False, indent=2)

    def append_probe_history(self, rows: list[dict[str, Any]]) -> None:
        self._probe_history.extend(rows)

    def append_portal_checks(self, rows: list[dict[str, Any]]) -> None:
        self._portal_checks.extend(rows)

    def dump_probe_json(self, limit: int = 30) -> None:
        data = self._probe_history[-limit:]
        with (self.dir / "probe.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def dump_portal_check_json(self) -> None:
        with (self.dir / "portal_check.json").open("w", encoding="utf-8") as f:
            json.dump(self._portal_checks, f, ensure_ascii=False, indent=2)

    def _read_dns_from_env(self) -> list[str]:
        dns = []
        raw = os.environ.get("DNS_SERVERS", "")
        for p in raw.replace(";", ",").split(","):
            x = p.strip()
            if x:
                dns.append(x)
        return dns

    def _windows_registry_net(self) -> dict[str, Any]:
        info: dict[str, Any] = {"default_gateway": [], "dns_servers": [], "interfaces": []}
        try:
            import winreg  # type: ignore
        except Exception:
            return info

        root = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as k:
                idx = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, idx)
                    except OSError:
                        break
                    idx += 1
                    row: dict[str, Any] = {"key": sub}
                    try:
                        with winreg.OpenKey(k, sub) as sk:
                            for name in ("DhcpIPAddress", "IPAddress", "DhcpDefaultGateway", "DefaultGateway", "NameServer", "DhcpNameServer"):
                                try:
                                    val, _ = winreg.QueryValueEx(sk, name)
                                    row[name] = val
                                except OSError:
                                    pass
                    except OSError:
                        continue
                    info["interfaces"].append(row)
        except OSError:
            pass

        gw: list[str] = []
        dns: list[str] = []
        for it in info["interfaces"]:
            for k in ("DhcpDefaultGateway", "DefaultGateway"):
                v = it.get(k)
                if isinstance(v, str):
                    gw.extend([x.strip() for x in v.split(",") if x.strip()])
                elif isinstance(v, list):
                    gw.extend([str(x).strip() for x in v if str(x).strip()])
            for k in ("NameServer", "DhcpNameServer"):
                v = it.get(k)
                if isinstance(v, str):
                    dns.extend([x.strip() for x in v.replace(" ", ",").split(",") if x.strip()])
        info["default_gateway"] = sorted(set(gw))
        info["dns_servers"] = sorted(set(dns))
        return info

    def dump_net_state_json(self) -> None:
        data: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "interfaces": [],
            "ipv4": [],
            "default_gateway": [],
            "dns_servers": [],
            "wifi": {"ssid": "", "interface": ""},
        }

        try:
            for _, name in socket.if_nameindex():
                data["interfaces"].append({"name": name})
        except Exception:
            pass

        try:
            addrs = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            ips = []
            for a in addrs:
                ip = a[4][0]
                if ip not in ips and not ip.startswith("127."):
                    ips.append(ip)
            data["ipv4"] = ips
        except Exception:
            pass

        reg = self._windows_registry_net()
        data["default_gateway"] = reg.get("default_gateway", [])
        dns = reg.get("dns_servers", [])
        if not dns:
            dns = self._read_dns_from_env()
        data["dns_servers"] = dns

        try:
            import pywifi  # type: ignore

            wifi = pywifi.PyWiFi()
            if wifi.interfaces():
                iface = wifi.interfaces()[0]
                data["wifi"]["interface"] = iface.name()
        except Exception:
            pass

        with (self.dir / "net_state.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def dump_system_net_diag(self, enabled: bool = False) -> None:
        if not enabled:
            return
        commands = [
            "ipconfig /all",
            "route print",
            "netsh wlan show interfaces",
        ]
        output: list[str] = []
        for cmd in commands:
            output.append(f"$ {cmd}")
            try:
                cp = subprocess.run(cmd, capture_output=True, shell=True, timeout=25)
                raw = (cp.stdout or b"") + (cp.stderr or b"")
                text = raw.decode("utf-8", "ignore")
                if not text.strip():
                    text = raw.decode("gbk", "ignore")
                output.append(text.strip())
            except Exception as e:
                output.append(f"ERROR: {type(e).__name__}: {e}")
            output.append("")
        with (self.dir / "net_diag.txt").open("w", encoding="utf-8") as f:
            f.write("\n".join(output))

    def dump_attempts_json(self, attempts: dict[str, Any]) -> None:
        with (self.dir / "attempts.json").open("w", encoding="utf-8") as f:
            json.dump(attempts, f, ensure_ascii=False, indent=2)

    def save_frames(self, page: Any) -> None:
        frames_dir = self.dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        try:
            frames = page.frames
        except Exception:
            frames = []
        for idx, fr in enumerate(frames):
            rec = {"name": fr.name, "url": fr.url}
            with (frames_dir / f"{idx:02d}_meta.json").open("w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
            try:
                html = fr.content()
                with (frames_dir / f"{idx:02d}.html").open("w", encoding="utf-8") as f:
                    f.write(html)
            except Exception:
                pass

    def save_page(self, page: Any, name: str = "final") -> None:
        try:
            page.screenshot(path=str(self.dir / f"{name}.png"), full_page=True)
        except Exception as e:
            self.log(f"保存截图失败: {e}")
        try:
            html = page.content()
            with (self.dir / f"{name}.html").open("w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            self.log(f"保存HTML失败: {e}")
    def cleanup(self) -> None:
        try:
            if self.dir.exists():
                shutil.rmtree(self.dir, ignore_errors=True)
        except Exception:
            pass
