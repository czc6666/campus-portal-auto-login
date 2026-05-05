from 学校配置_profiles.types import (
    BrowserConfig,
    PortalConfig,
    ProbeConfig,
    SchoolProfile,
    SelectorConfig,
    TimingConfig,
    WifiConfig,
)


PROFILE = SchoolProfile(
    id="example_srun",
    name="Example Srun Campus",
    portal=PortalConfig(
        url_candidates=["http://10.0.0.55/srun_portal_pc?ac_id=8&theme=campus"],
        reachable_host="10.0.0.55",
        reachable_port=80,
        wait_sec=25,
        goto_retries=3,
    ),
    selectors=SelectorConfig(
        username=["#username"],
        password=["#password"],
        login_button=["#login"],
    ),
    browser=BrowserConfig(mode="edge_then_chromium", headless=False),
    timing=TimingConfig(
        check_interval_sec=30,
        login_wait_sec=8,
        retry_cooldown_sec=30,
        probe_timeout_sec=6,
    ),
    probe=ProbeConfig(mode="multi"),
    wifi=WifiConfig(provider="netsh", ssid="CAMPUS-WIFI", connect_timeout_sec=20),
)
