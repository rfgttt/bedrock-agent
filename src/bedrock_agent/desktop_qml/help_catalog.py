from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class HelpPreset:
    preset_id: str
    title: str
    description: str
    prompt: str
    category: str
    risk: str
    needs_approval: bool
    requirement: str = "无需额外配置"


_PRESETS = (
    HelpPreset("open_app", "打开常用应用", "从应用白名单中启动一个本地程序。", "列出我可以打开的应用，然后打开网易云音乐。", "桌面", "低", True, "先在应用页添加或发现程序"),
    HelpPreset("media", "控制音乐", "通过系统媒体键播放、暂停或切歌。", "播放或暂停当前音乐。", "桌面", "低", True),
    HelpPreset("workspace", "检查 Python 项目", "读取工作区中的项目结构并检查语法。", "检查 workspace 中 Python 项目的结构和语法错误。", "编程", "只读", False, "先把项目导入工作区"),
    HelpPreset("study_plan", "创建学习计划", "创建并保存一个可跟踪的学习计划。", "给我制定 7 天 Python 与 Agent 开发学习计划，每天 90 分钟，并保存。", "学习", "中", True),
    HelpPreset("study_log", "记录学习进度", "记录时长、主题、自信度和复习日期。", "记录今天学习 Python 函数 60 分钟，自信度 3，重点是参数和返回值。", "学习", "中", True),
    HelpPreset("web_research", "搜索并整理资料", "搜索公开网页，提取内容并保存摘要。", "搜索 5 个 pytest 入门资料，比较后把摘要保存到 workspace。", "网络", "中", True, "需要网络连接"),
    HelpPreset("organize", "整理工作区", "先预览文件整理方案，再由你审批执行。", "预览 workspace 根目录按扩展名整理的方案，不要立即执行。", "文件", "中", True),
    HelpPreset("remember", "保存长期记忆", "把重要偏好或经验保存到长期记忆。", "请记住：我的职业方向是 Agent 应用开发和 AI 应用测试。", "记忆", "中", True),
    HelpPreset("syntax", "检查语法错误", "只编译检查 Python 文件，不运行项目代码。", "检查 workspace 中所有 Python 文件的语法错误。", "编程", "只读", False),
    HelpPreset("approvals", "查看待审批任务", "打开审批中心，查看参数和风险。", "查看当前所有等待我审批的任务。", "安全", "只读", False),
    HelpPreset("mcp", "同步 MCP 工具", "检查已配置的 MCP 服务器并同步工具。", "检查 MCP 服务器连接状态，并告诉我有哪些可用工具。", "扩展", "中", True, "先在 MCP 页面导入配置"),
    HelpPreset("skill", "学习组合 Skill", "把已有工具组合成一个可复用技能。", "把“获取当前时间并写入学习笔记”设计成一个组合 Skill，先给我看方案。", "扩展", "中", True),
)


def help_presets() -> list[dict[str, object]]:
    return [asdict(item) for item in _PRESETS]
