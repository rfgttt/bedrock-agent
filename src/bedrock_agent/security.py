from __future__ import annotations

import getpass
import ipaddress
import os
import secrets
import stat
from pathlib import Path


_LOOPBACK_NAMES = {"localhost", "ip6-localhost"}


def is_loopback(value: str | None) -> bool:
    if not value:
        return False
    host = value.strip().strip("[]").lower()
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_loopback_bind(host: str) -> None:
    if not is_loopback(host):
        raise ValueError(
            "Bedrock server may bind only to a loopback address (127.0.0.1 or ::1). "
            "Remote/LAN binding is intentionally disabled."
        )


def require_owner_user(expected_user: str | None) -> str:
    current = getpass.getuser()
    if expected_user and current.casefold() != expected_user.casefold():
        raise PermissionError(
            f"Bedrock is configured for OS user {expected_user!r}, but is running as {current!r}"
        )
    return current


def make_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(stat.S_IRWXU)
    return path


def make_private_file(path: Path) -> Path:
    if path.exists() and os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


class LocalTokenStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_or_create(self) -> str:
        make_private_dir(self.path.parent)
        if self.path.exists():
            token = self.path.read_text(encoding="utf-8").strip()
            if len(token) < 32:
                raise ValueError("Local API token file is invalid or too short")
            make_private_file(self.path)
            return token
        token = secrets.token_urlsafe(48)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(self.path, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(token)
        make_private_file(self.path)
        return token
