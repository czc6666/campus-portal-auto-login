import os
import sys
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 核心_core import run_profile, run_login_once


def _load_profile():
    profile_module = os.environ.get("PROFILE_MODULE", "学校配置_profiles.example_drcom")
    module = import_module(profile_module)
    return module.PROFILE


def main() -> None:
    profile = _load_profile()
    username = os.environ.get("CAMPUS_USERNAME", "")
    password = os.environ.get("CAMPUS_PASSWORD", "")
    once = os.environ.get("RUN_ONCE", "0") == "1"

    if not username or not password:
        raise SystemExit(
            "Missing CAMPUS_USERNAME or CAMPUS_PASSWORD. "
            "Set environment variables first."
        )

    if once:
        result = run_login_once(profile, username, password)
        print(result)
        return

    run_profile(profile, {"username": username, "password": password})


if __name__ == "__main__":
    main()
