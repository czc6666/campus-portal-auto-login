from dataclasses import dataclass


@dataclass
class ProbeResult:
    online: bool
    reason: str


@dataclass
class LoginResult:
    success: bool
    phase: str
    reason: str
    diag_dir: str | None = None
    needs_manual: bool = False
