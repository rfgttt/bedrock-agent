from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from bedrock_agent.security import make_private_file
from bedrock_agent.tools.base import RiskLevel, Tool


@dataclass(frozen=True, slots=True)
class AppDefinition:
    app_id: str
    display_name: str
    aliases: tuple[str, ...]
    candidates: tuple[str, ...]
    executable_names: tuple[str, ...] = ()
    registry_markers: tuple[str, ...] = ()


_BUILTIN_APPS = (
    AppDefinition(
        "netease_cloud_music",
        "网易云音乐",
        ("网易云", "网易云音乐", "cloudmusic", "netease"),
        (
            r"%LOCALAPPDATA%\NetEase\CloudMusic\cloudmusic.exe",
            r"%LOCALAPPDATA%\Programs\NetEase\CloudMusic\cloudmusic.exe",
            r"%APPDATA%\NetEase\CloudMusic\cloudmusic.exe",
            r"%PROGRAMFILES%\NetEase\CloudMusic\cloudmusic.exe",
            r"%PROGRAMFILES(X86)%\NetEase\CloudMusic\cloudmusic.exe",
            r"%PROGRAMFILES%\CloudMusic\cloudmusic.exe",
            r"%PROGRAMFILES(X86)%\CloudMusic\cloudmusic.exe",
        ),
        executable_names=("cloudmusic.exe",),
        registry_markers=("网易云音乐", "netease cloud music", "cloudmusic"),
    ),
    AppDefinition(
        "notepad",
        "记事本",
        ("记事本", "notepad"),
        ("notepad.exe",),
        executable_names=("notepad.exe",),
    ),
    AppDefinition(
        "calculator_app",
        "Windows 计算器",
        ("计算器", "calc"),
        ("calc.exe",),
        executable_names=("calc.exe",),
    ),
    AppDefinition(
        "explorer",
        "文件资源管理器",
        ("资源管理器", "文件管理器", "explorer"),
        ("explorer.exe",),
        executable_names=("explorer.exe",),
    ),
    AppDefinition(
        "vscode",
        "Visual Studio Code",
        ("vscode", "vs code", "code"),
        (
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES(X86)%\Microsoft VS Code\Code.exe",
            "code.exe",
        ),
        executable_names=("Code.exe",),
        registry_markers=("visual studio code", "microsoft visual studio code"),
    ),
    AppDefinition(
        "wechat",
        "微信",
        ("微信", "wechat", "weixin"),
        (
            r"%PROGRAMFILES%\Tencent\WeChat\WeChat.exe",
            r"%PROGRAMFILES(X86)%\Tencent\WeChat\WeChat.exe",
            r"%LOCALAPPDATA%\Tencent\WeChat\WeChat.exe",
        ),
        executable_names=("WeChat.exe",),
        registry_markers=("微信", "wechat"),
    ),
    AppDefinition(
        "qq",
        "QQ",
        ("qq", "腾讯qq"),
        (
            r"%PROGRAMFILES%\Tencent\QQNT\QQ.exe",
            r"%PROGRAMFILES(X86)%\Tencent\QQNT\QQ.exe",
            r"%LOCALAPPDATA%\Programs\Tencent\QQ\QQ.exe",
        ),
        executable_names=("QQ.exe",),
        registry_markers=("腾讯qq", "qq"),
    ),
    AppDefinition(
        "chrome",
        "Google Chrome",
        ("chrome", "谷歌浏览器", "google chrome"),
        (
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        ),
        executable_names=("chrome.exe",),
        registry_markers=("google chrome",),
    ),
    AppDefinition(
        "edge",
        "Microsoft Edge",
        ("edge", "微软浏览器", "microsoft edge"),
        (
            r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe",
            r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe",
        ),
        executable_names=("msedge.exe",),
        registry_markers=("microsoft edge",),
    ),
    AppDefinition(
        "steam",
        "Steam",
        ("steam",),
        (
            r"%PROGRAMFILES(X86)%\Steam\steam.exe",
            r"%PROGRAMFILES%\Steam\steam.exe",
        ),
        executable_names=("steam.exe",),
        registry_markers=("steam",),
    ),
    AppDefinition(
        "windows_terminal",
        "Windows Terminal",
        ("terminal", "windows terminal", "终端"),
        ("wt.exe",),
        executable_names=("wt.exe",),
        registry_markers=("windows terminal",),
    ),
    AppDefinition(
        "obsidian",
        "Obsidian",
        ("obsidian", "黑曜石"),
        (r"%LOCALAPPDATA%\Obsidian\Obsidian.exe",),
        executable_names=("Obsidian.exe",),
        registry_markers=("obsidian",),
    ),
)


def _deduplicate(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = os.path.normcase(os.path.normpath(str(value).strip()))
        if not value or normalized in seen:
            continue
        seen.add(normalized)
        result.append(str(value).strip())
    return result


def _registry_executable(value: str) -> str:
    """Normalize DisplayIcon/App Paths registry values into an executable path."""

    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith('"'):
        end = cleaned.find('"', 1)
        if end > 1:
            return cleaned[1:end]
    # DisplayIcon commonly ends with `,0`. Avoid splitting a legitimate comma
    # inside a quoted path (already handled above).
    if "," in cleaned:
        head, tail = cleaned.rsplit(",", 1)
        if tail.strip().lstrip("-").isdigit():
            cleaned = head.strip()
    return cleaned.strip('"')


class WindowsApplicationDiscovery:
    """Read trusted Windows registration metadata without executing anything.

    Discovery only returns candidate executable paths. The catalog still checks
    that the path exists and is a file before exposing it to the launcher.
    """

    def __init__(self, *, platform_name: str | None = None) -> None:
        self.platform_name = platform_name or sys.platform

    def candidates(self, definition: AppDefinition) -> list[str]:
        if not self.platform_name.startswith("win"):
            return []
        try:
            import winreg  # type: ignore
        except ImportError:
            return []

        values: list[str] = []
        executable_names = definition.executable_names or tuple(
            Path(candidate).name
            for candidate in definition.candidates
            if Path(candidate).suffix.casefold() == ".exe"
        )
        roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
        views = [0]
        for flag_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
            flag = getattr(winreg, flag_name, 0)
            if flag and flag not in views:
                views.append(flag)

        # App Paths is the most reliable source for applications that register
        # their executable with Windows.
        for executable_name in executable_names:
            key_path = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"
            for root in roots:
                for view in views:
                    try:
                        with winreg.OpenKey(root, key_path, 0, winreg.KEY_READ | view) as key:
                            raw, _kind = winreg.QueryValueEx(key, None)
                            candidate = _registry_executable(raw)
                            if candidate:
                                values.append(candidate)
                    except OSError:
                        continue

        # Some installers do not create App Paths but do publish their install
        # directory or icon in the Uninstall registry.
        markers = tuple(marker.casefold() for marker in definition.registry_markers)
        uninstall_paths = (
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
            r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        if markers:
            for root in roots:
                for uninstall_path in uninstall_paths:
                    for view in views:
                        try:
                            with winreg.OpenKey(root, uninstall_path, 0, winreg.KEY_READ | view) as parent:
                                subkey_count = winreg.QueryInfoKey(parent)[0]
                                for index in range(subkey_count):
                                    try:
                                        name = winreg.EnumKey(parent, index)
                                        with winreg.OpenKey(parent, name) as item:
                                            try:
                                                display_name = str(winreg.QueryValueEx(item, "DisplayName")[0])
                                            except OSError:
                                                display_name = ""
                                            if not any(marker in display_name.casefold() for marker in markers):
                                                continue
                                            try:
                                                display_icon = _registry_executable(
                                                    str(winreg.QueryValueEx(item, "DisplayIcon")[0])
                                                )
                                            except OSError:
                                                display_icon = ""
                                            if display_icon:
                                                values.append(display_icon)
                                            try:
                                                install_location = str(
                                                    winreg.QueryValueEx(item, "InstallLocation")[0]
                                                ).strip()
                                            except OSError:
                                                install_location = ""
                                            if install_location:
                                                for executable_name in executable_names:
                                                    values.append(str(Path(install_location) / executable_name))
                                    except OSError:
                                        continue
                        except OSError:
                            continue
        return _deduplicate(values)


class ApplicationCatalog:
    """Owns the application allowlist and executable resolution.

    The model can choose only an app id/alias already present in this catalog.
    It can never provide an arbitrary executable path or command line.
    """

    def __init__(
        self,
        config_path: Path,
        *,
        path_exists: Callable[[Path], bool] | None = None,
        which: Callable[[str], str | None] = shutil.which,
        platform_name: str | None = None,
        discovered_candidates: Callable[[AppDefinition], Iterable[str]] | None = None,
        status_cache_ttl: float = 60.0,
    ) -> None:
        self.config_path = config_path
        self._path_exists = path_exists or Path.exists
        self._which = which
        self.platform_name = platform_name or sys.platform
        self._discovery = WindowsApplicationDiscovery(platform_name=self.platform_name)
        self._discovered_candidates = discovered_candidates or self._discovery.candidates
        self._definitions: dict[str, AppDefinition] = {}
        self._status_cache_ttl = max(0.0, status_cache_ttl)
        self._status_cache: tuple[float, list[dict[str, Any]]] | None = None
        self._ensure_user_config()
        self.reload()

    def _ensure_user_config(self) -> None:
        if self.config_path.exists():
            return
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "note": "Only executables listed here may be launched. Keep paths explicit and trusted.",
            "apps": [],
        }
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        make_private_file(self.config_path)

    def _read_payload(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid app allowlist: {self.config_path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid app allowlist root: {self.config_path}")
        if not isinstance(payload.get("apps", []), list):
            raise ValueError(f"Invalid app allowlist apps: {self.config_path}")
        return payload

    def reload(self) -> None:
        self._status_cache = None
        self._definitions = {app.app_id: app for app in _BUILTIN_APPS}
        payload = self._read_payload()
        for item in payload.get("apps", []):
            if not isinstance(item, dict):
                continue
            app_id = str(item.get("id", "")).strip()
            display_name = str(item.get("name", "")).strip()
            paths = item.get("paths", [])
            aliases = item.get("aliases", [])
            if not app_id or not display_name or not isinstance(paths, list):
                continue
            previous = self._definitions.get(app_id)
            self._definitions[app_id] = AppDefinition(
                app_id=app_id,
                display_name=display_name,
                aliases=tuple(str(value).strip() for value in aliases if str(value).strip()),
                candidates=tuple(str(value).strip() for value in paths if str(value).strip()),
                executable_names=previous.executable_names if previous else (),
                registry_markers=previous.registry_markers if previous else (),
            )

    @staticmethod
    def _expand(candidate: str) -> str:
        return os.path.expandvars(os.path.expanduser(candidate))

    def resolve_definition(self, query: str) -> AppDefinition:
        normalized = query.strip().casefold()
        for definition in self._definitions.values():
            values = (definition.app_id, definition.display_name, *definition.aliases)
            if normalized in {value.casefold() for value in values}:
                return definition
        raise KeyError(f"Application is not in the allowlist: {query}")

    def candidate_paths(self, definition: AppDefinition) -> list[str]:
        dynamic = list(self._discovered_candidates(definition))
        return _deduplicate((*definition.candidates, *dynamic))

    def resolve_executable(self, definition: AppDefinition) -> str:
        for candidate in self.candidate_paths(definition):
            expanded = self._expand(candidate)
            if not Path(expanded).is_absolute():
                resolved = self._which(expanded)
                if resolved:
                    return resolved
                continue
            path = Path(expanded)
            if self._path_exists(path) and path.is_file():
                return str(path)
        raise FileNotFoundError(
            f"No executable found for {definition.display_name}. "
            f"Use the desktop Capability Center to choose its trusted .exe, or edit {self.config_path}."
        )

    @staticmethod
    def _validate_launch_target(executable: Path) -> Path:
        resolved = executable.expanduser().resolve()
        if not resolved.is_absolute() or resolved.suffix.casefold() not in {".exe", ".lnk"}:
            raise ValueError("The selected application must be an absolute .exe or .lnk file")
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Application target does not exist: {resolved}")
        return resolved

    def _write_user_app(self, definition: AppDefinition, resolved: Path) -> None:
        payload = self._read_payload()
        apps = [
            item
            for item in payload.get("apps", [])
            if not (isinstance(item, dict) and str(item.get("id", "")).strip() == definition.app_id)
        ]
        apps.append(
            {
                "id": definition.app_id,
                "name": definition.display_name,
                "aliases": list(definition.aliases),
                "paths": [str(resolved)],
            }
        )
        payload["apps"] = apps
        temporary = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.config_path)
        make_private_file(self.config_path)
        self.reload()

    def set_explicit_path(self, app: str, executable: Path) -> dict[str, Any]:
        definition = self.resolve_definition(app)
        resolved = self._validate_launch_target(executable)
        self._write_user_app(definition, resolved)
        return self.app_status(definition.app_id)

    def add_custom_app(
        self,
        display_name: str,
        executable: Path,
        *,
        aliases: Iterable[str] = (),
    ) -> dict[str, Any]:
        display_name = display_name.strip()
        if not display_name or len(display_name) > 80:
            raise ValueError("Application name must be 1-80 characters")
        resolved = self._validate_launch_target(executable)
        clean_aliases = tuple(
            value.strip() for value in (str(item) for item in aliases) if value.strip()
        )
        normalized = re.sub(r"[^a-z0-9]+", "_", display_name.casefold()).strip("_")[:24]
        digest = hashlib.sha256(f"{display_name}|{resolved}".encode("utf-8")).hexdigest()[:10]
        app_id = f"custom_{normalized or 'app'}_{digest}"
        definition = AppDefinition(
            app_id=app_id,
            display_name=display_name,
            aliases=clean_aliases,
            candidates=(str(resolved),),
        )
        self._write_user_app(definition, resolved)
        return self.app_status(app_id)

    def remove_custom_app(self, app: str) -> None:
        definition = self.resolve_definition(app)
        if not definition.app_id.startswith("custom_"):
            raise ValueError("Built-in applications cannot be removed; their explicit path can be replaced")
        payload = self._read_payload()
        payload["apps"] = [
            item
            for item in payload.get("apps", [])
            if not (isinstance(item, dict) and str(item.get("id", "")).strip() == definition.app_id)
        ]
        temporary = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.config_path)
        make_private_file(self.config_path)
        self.reload()

    def app_status(self, app: str) -> dict[str, Any]:
        definition = self.resolve_definition(app)
        try:
            executable = self.resolve_executable(definition)
            available = True
        except FileNotFoundError:
            executable = ""
            available = False
        return {
            "id": definition.app_id,
            "name": definition.display_name,
            "aliases": list(definition.aliases),
            "available": available,
            "executable": executable,
        }

    def list_apps(self, *, force_refresh: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if (
            not force_refresh
            and self._status_cache is not None
            and now - self._status_cache[0] < self._status_cache_ttl
        ):
            return [dict(row) for row in self._status_cache[1]]
        rows = [
            self.app_status(definition.app_id)
            for definition in sorted(self._definitions.values(), key=lambda item: item.display_name)
        ]
        self._status_cache = (now, [dict(row) for row in rows])
        return rows


class ApplicationLauncher:
    def __init__(
        self,
        catalog: ApplicationCatalog,
        *,
        popen: Callable[..., Any] = subprocess.Popen,
        platform_name: str | None = None,
    ) -> None:
        self.catalog = catalog
        self._popen = popen
        self.platform_name = platform_name or sys.platform

    def launch(self, app: str) -> dict[str, Any]:
        if not self.platform_name.startswith("win"):
            raise OSError("The application launcher currently supports Windows only")
        definition = self.catalog.resolve_definition(app)
        executable = self.catalog.resolve_executable(definition)
        if Path(executable).suffix.casefold() == ".lnk":
            os.startfile(executable)  # type: ignore[attr-defined]
            pid = None
        else:
            process = self._popen(
                [executable],
                shell=False,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            pid = getattr(process, "pid", None)
        return {
            "app_id": definition.app_id,
            "name": definition.display_name,
            "executable": executable,
            "pid": pid,
        }


def build_application_tools(catalog: ApplicationCatalog, launcher: ApplicationLauncher) -> list[Tool]:
    return [
        Tool(
            name="list_allowed_apps",
            description="List applications in the local launch allowlist and whether each one is available.",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            handler=lambda _arguments: catalog.list_apps(),
        ),
        Tool(
            name="launch_allowed_app",
            description=(
                "Launch a Windows application only if it is in the local allowlist. "
                "Never accepts an executable path or command arguments. Requires local approval."
            ),
            parameters={
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
                "additionalProperties": False,
            },
            handler=lambda arguments: launcher.launch(arguments["app"]),
            risk=RiskLevel.EXTERNAL,
        ),
    ]
