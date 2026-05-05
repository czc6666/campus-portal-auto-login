from 学校配置_profiles.types import (
    BrowserConfig,
    InputConfig,
    PortalConfig,
    ProbeConfig,
    SchoolProfile,
    SelectorConfig,
    TimingConfig,
)


PROFILE = SchoolProfile(
    id="example_gportal",
    name="Example Gportal Campus",
    portal=PortalConfig(
        url_candidates=[
            "http://192.168.100.3/gportal/web/login",
            "http://192.168.100.3/",
            "http://connectivitycheck.gstatic.com/generate_204",
        ],
        reachable_host=None,
        reachable_port=80,
        wait_sec=5,
        goto_retries=5,
    ),
    selectors=SelectorConfig(
        username=[
            "input#first_name[name='name']",
            "input[name='name']",
            "input[placeholder*='账号']",
        ],
        password=[
            "input#first_password[name='password']",
            "input[name='password']",
            "input[type='password']",
        ],
        login_button=[
            "#first_button",
            "input.submit_btn[type='button']",
            "input[type='button'][onclick*='login']",
        ],
        captcha=[
            "input[name='captcha']",
            "#captcha",
            "#captcha_img",
        ],
    ),
    input=InputConfig(mode="js_first"),
    browser=BrowserConfig(mode="edge_then_chromium", headless=False),
    timing=TimingConfig(
        check_interval_sec=30,
        login_wait_sec=8,
        retry_cooldown_sec=30,
        probe_timeout_sec=6,
        action_timeout_ms=20000,
        navigation_timeout_ms=30000,
    ),
    probe=ProbeConfig(mode="multi"),
)
