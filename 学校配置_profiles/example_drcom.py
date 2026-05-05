from 学校配置_profiles.types import (
    BrowserConfig,
    PortalConfig,
    ProbeConfig,
    SchoolProfile,
    SelectorConfig,
    SubmitConfig,
    TimingConfig,
)


PROFILE = SchoolProfile(
    id="example_drcom",
    name="Example Drcom Campus",
    portal=PortalConfig(
        url_candidates=[
            "https://auth.example.edu/3.htm?wlanacip=1.2.3.4&url=http://www.gstatic.com/generate_204",
            "https://auth.example.edu/",
        ],
        reachable_host="auth.example.edu",
        reachable_port=443,
        wait_sec=25,
        goto_retries=3,
    ),
    selectors=SelectorConfig(
        username=[
            "input[name='DDDDD']",
            "input[name='username']",
        ],
        password=[
            "input[name='upass']",
            "input[type='password']",
        ],
        login_button=[
            "input[name='0MKKey'][type='button']",
            "input[name='0MKKey']",
            "input[type='submit']",
            "button[type='submit']",
        ],
        captcha=[
            "input[name='captcha']",
            "#captcha_img",
        ],
    ),
    submit=SubmitConfig(mode="keyboard_tab_enter"),
    browser=BrowserConfig(mode="edge_only", headless=False),
    timing=TimingConfig(
        check_interval_sec=3600,
        login_wait_sec=20,
        retry_cooldown_sec=120,
        probe_timeout_sec=5,
    ),
    probe=ProbeConfig(mode="multi"),
)
