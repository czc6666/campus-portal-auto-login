from dataclasses import dataclass, field


@dataclass
class PortalConfig:
    url_candidates: list[str]
    reachable_host: str | None = None
    reachable_port: int = 80
    wait_sec: int = 25
    goto_retries: int = 3


@dataclass
class SelectorConfig:
    username: list[str]
    password: list[str]
    login_button: list[str]
    operator: list[str] = field(default_factory=list)
    captcha: list[str] = field(default_factory=list)


@dataclass
class InputConfig:
    mode: str = "fill_first"  # fill_first / js_first / keyboard


@dataclass
class SubmitConfig:
    mode: str = "click_then_enter"  # click_then_enter / keyboard_tab_enter


@dataclass
class BrowserConfig:
    mode: str = "edge_then_chromium"  # edge_only / edge_then_chromium / chromium_only
    headless: bool = False


@dataclass
class TimingConfig:
    check_interval_sec: int = 30
    login_wait_sec: int = 8
    retry_cooldown_sec: int = 30
    probe_timeout_sec: int = 6
    action_timeout_ms: int = 20000
    navigation_timeout_ms: int = 30000


@dataclass
class ProbeConfig:
    mode: str = "multi"
    urls: list[str] = field(default_factory=list)


@dataclass
class WifiConfig:
    provider: str = "none"  # none / pywifi / netsh
    ssid: str = ""
    connect_timeout_sec: int = 20


@dataclass
class FrameConfig:
    mode: str = "main"  # main / first_matching_frame


@dataclass
class SchoolProfile:
    id: str
    name: str
    portal: PortalConfig
    selectors: SelectorConfig
    input: InputConfig = field(default_factory=InputConfig)
    submit: SubmitConfig = field(default_factory=SubmitConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    probe: ProbeConfig = field(default_factory=ProbeConfig)
    wifi: WifiConfig = field(default_factory=WifiConfig)
    frame: FrameConfig = field(default_factory=FrameConfig)
    operator_value: str = ""
    export_diag_on_fail: bool = True
