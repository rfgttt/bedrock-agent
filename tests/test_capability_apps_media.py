from __future__ import annotations

import json
from pathlib import Path

import pytest

from bedrock_agent.capabilities.apps import ApplicationCatalog, ApplicationLauncher
from bedrock_agent.capabilities.media import WindowsMediaController


class FakeProcess:
    pid = 4321


def test_application_launcher_uses_only_allowlisted_app(tmp_path: Path) -> None:
    executable = tmp_path / "cloudmusic.exe"
    executable.write_bytes(b"fake")
    config = tmp_path / "private" / "app_allowlist.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "apps": [
                    {
                        "id": "my_netease",
                        "name": "我的网易云",
                        "aliases": ["网易云测试"],
                        "paths": [str(executable)],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    catalog = ApplicationCatalog(config, platform_name="win32", which=lambda _name: None)
    calls = []

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    launcher = ApplicationLauncher(catalog, popen=fake_popen, platform_name="win32")
    result = launcher.launch("网易云测试")

    assert result["pid"] == 4321
    assert calls[0][0] == [str(executable)]
    assert calls[0][1]["shell"] is False
    with pytest.raises(KeyError):
        launcher.launch(r"C:\Windows\System32\cmd.exe")


def test_media_controller_sends_only_known_media_keys() -> None:
    sent = []
    controller = WindowsMediaController(key_sender=sent.append, platform_name="win32")

    result = controller.control("volume_up", repeat=3)

    assert result["sent"] is True
    assert len(sent) == 3
    with pytest.raises(ValueError):
        controller.control("open_shell")


def test_application_catalog_uses_discovered_windows_candidate(tmp_path: Path) -> None:
    executable = tmp_path / "custom" / "cloudmusic.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"fake")
    config = tmp_path / "private" / "app_allowlist.json"

    catalog = ApplicationCatalog(
        config,
        platform_name="win32",
        which=lambda _name: None,
        discovered_candidates=lambda definition: [str(executable)]
        if definition.app_id == "netease_cloud_music"
        else [],
    )

    status = catalog.app_status("网易云")

    assert status["available"] is True
    assert status["executable"] == str(executable)


def test_application_catalog_persists_user_selected_executable(tmp_path: Path) -> None:
    executable = tmp_path / "apps" / "cloudmusic.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"fake")
    config = tmp_path / "private" / "app_allowlist.json"
    catalog = ApplicationCatalog(
        config,
        platform_name="win32",
        which=lambda _name: None,
        discovered_candidates=lambda _definition: [],
    )

    saved = catalog.set_explicit_path("netease_cloud_music", executable)
    reloaded = ApplicationCatalog(
        config,
        platform_name="win32",
        which=lambda _name: None,
        discovered_candidates=lambda _definition: [],
    )

    assert saved["available"] is True
    assert reloaded.resolve_executable(reloaded.resolve_definition("网易云音乐")) == str(executable.resolve())


def test_application_catalog_adds_and_removes_any_user_approved_program(tmp_path: Path) -> None:
    executable = tmp_path / "tools" / "MyTool.exe"
    executable.parent.mkdir()
    executable.write_bytes(b"fake")
    config = tmp_path / "private" / "app_allowlist.json"
    catalog = ApplicationCatalog(
        config,
        platform_name="win32",
        which=lambda _name: None,
        discovered_candidates=lambda _definition: [],
    )

    saved = catalog.add_custom_app("我的工具", executable, aliases=["my tool", "工具"])
    assert saved["available"] is True
    assert catalog.resolve_definition("工具").app_id.startswith("custom_")

    catalog.remove_custom_app(saved["id"])
    with pytest.raises(KeyError):
        catalog.resolve_definition("我的工具")
