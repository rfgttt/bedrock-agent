# Project Bedrock v0.5.2

Bedrock 是一个本地桌面 Agent：DeepSeek 模型、持久记忆、受控 Skills、工作区隔离、通用应用白名单、MCP Tools、人工审批与运行轨迹。

## v0.5.2：可交互 3D 任务棱镜

- 将任务棱镜从静态错位卡片替换为 `PathView` 3D 卡片轮播；
- 支持鼠标拖拽、触控板/滚轮、左右方向键和前后按钮；
- 当前卡居中放大，侧卡沿 Y 轴翻转并降低透明度，切换时平滑插值；
- 当前卡提供明确的“打开会话”入口和页码指示；
- 最多只实例化 7 张可见卡片，无数据变化时不触发模型重置，也没有持续动画。

## v0.5.1：QML 语法兼容修复

- 修复 QML 子对象之间错误使用分号导致 Qt 6.11 无法解析的问题。
- 新增 QML 静态语法守卫测试，避免同类错误再次进入补丁。

## v0.5.0：QML 科技感桌面端

默认前端已重构为 **PySide6 + QML**：

- 深黑科技视觉、玻璃卡片、荧光绿色状态；
- 左侧导航、中央任务/对话区、右侧 Agent 状态栏；
- 任务棱镜层叠卡片与轻量动画；
- 固定“帮助与技能”入口，内置 12 个可直接测试的预设；
- 工作区、应用、审批、学习、Skills、MCP、记忆和轨迹均有独立页面；
- 页面按需加载，数据无变化不重绘，对话优先增量追加；
- 旧 Tkinter 前端保留为 `bedrock-desktop-legacy`。

详细说明见 [FRONTEND.md](FRONTEND.md)。

## 安装

Python 3.11 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,mcp,desktop]"
copy .env.example .env
bedrock-desktop
```

仅查看新界面、不调用 DeepSeek：

```powershell
bedrock-desktop-preview
```

旧界面回退：

```powershell
bedrock-desktop-legacy
```

## 主要安全边界

- 桌面端进程内调用，不开放网络端口；
- 文件能力仅在 `workspace/` 内操作；
- 应用只能从用户白名单启动；
- 写入、启动应用、网页访问和 MCP 调用仍需审批；
- Skill 只能组合已注册工具，不执行任意生成代码；
- 模型、文件导入和扫描均在后台执行，界面线程不承担重任务。

## 测试

```powershell
pytest
bedrock-desktop --ui-smoke
```

完整文档：`CAPABILITIES.md`、`DESKTOP.md`、`FRONTEND.md`、`MCP.md`、`PERFORMANCE.md`、`SECURITY.md`、`WORKSPACE.md`。
