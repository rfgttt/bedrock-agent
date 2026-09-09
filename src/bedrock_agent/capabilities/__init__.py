from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bedrock_agent.capabilities.apps import ApplicationCatalog, ApplicationLauncher, build_application_tools
from bedrock_agent.capabilities.coding import CodingWorkspace, build_coding_tools
from bedrock_agent.capabilities.file_organizer import FileOrganizer, build_file_organizer_tools
from bedrock_agent.capabilities.learning_manager import LearningManager, build_learning_tools
from bedrock_agent.capabilities.media import WindowsMediaController, build_media_tools
from bedrock_agent.capabilities.web import SafeWebClient, build_web_tools
from bedrock_agent.capabilities.workspace_import import WorkspaceImportService
from bedrock_agent.tools.base import Tool
from bedrock_agent.tools.builtin import Workspace


@dataclass(slots=True)
class CapabilitySuite:
    applications: ApplicationCatalog
    launcher: ApplicationLauncher
    media: WindowsMediaController
    web: SafeWebClient
    organizer: FileOrganizer
    coding: CodingWorkspace
    learning: LearningManager
    workspace_import: WorkspaceImportService

    def status(self, *, force_refresh: bool = False) -> list[dict[str, object]]:
        apps = self.applications.list_apps(force_refresh=force_refresh)
        return [
            {
                "id": "applications",
                "name": "白名单应用启动",
                "ready": any(row["available"] for row in apps),
                "detail": f"{sum(bool(row['available']) for row in apps)}/{len(apps)} 个应用可用，可添加任意可信 .exe/.lnk",
                "tools": ["list_allowed_apps", "launch_allowed_app"],
            },
            {
                "id": "workspace_import",
                "name": "工作区导入",
                "ready": True,
                "detail": "由本地文件选择器把文件或项目复制进隔离工作区",
                "tools": [],
            },
            {
                "id": "media",
                "name": "系统媒体控制",
                "ready": True,
                "detail": "播放/暂停、上一首、下一首、音量与静音",
                "tools": ["control_system_media"],
            },
            {
                "id": "web",
                "name": "安全网页检索",
                "ready": True,
                "detail": "公共网页搜索与正文读取，阻止私网访问",
                "tools": ["search_public_web", "read_public_web_page"],
            },
            {
                "id": "files",
                "name": "可撤销文件整理",
                "ready": True,
                "detail": "先预览计划，再审批应用，可撤销",
                "tools": ["plan_workspace_organization", "apply_workspace_organization", "undo_workspace_organization"],
            },
            {
                "id": "coding",
                "name": "安全编程助手",
                "ready": True,
                "detail": "结构分析、文本搜索、语法检查、精确替换与备份恢复",
                "tools": ["inspect_code_project", "search_code_text", "check_python_syntax", "replace_code_text_exact", "restore_code_backup"],
            },
            {
                "id": "learning",
                "name": "学习管理",
                "ready": True,
                "detail": "学习计划、学习记录、仪表盘和复习队列",
                "tools": ["create_study_plan", "record_study_session", "get_learning_dashboard", "get_review_queue"],
            },
        ]


def build_capability_suite(*, workspace_path: Path, data_dir: Path) -> tuple[CapabilitySuite, list[Tool]]:
    workspace = Workspace(workspace_path)
    applications = ApplicationCatalog(data_dir / "app_allowlist.json")
    launcher = ApplicationLauncher(applications)
    media = WindowsMediaController()
    web = SafeWebClient()
    organizer = FileOrganizer(workspace, data_dir / "file_plans")
    coding = CodingWorkspace(workspace, data_dir / "code_backups")
    learning = LearningManager(data_dir / "learning.db")
    workspace_import = WorkspaceImportService(workspace)
    suite = CapabilitySuite(applications, launcher, media, web, organizer, coding, learning, workspace_import)
    tools: list[Tool] = []
    tools.extend(build_application_tools(applications, launcher))
    tools.extend(build_media_tools(media))
    tools.extend(build_web_tools(web))
    tools.extend(build_file_organizer_tools(organizer))
    tools.extend(build_coding_tools(coding))
    tools.extend(build_learning_tools(learning))
    return suite, tools


__all__ = ["CapabilitySuite", "build_capability_suite"]
