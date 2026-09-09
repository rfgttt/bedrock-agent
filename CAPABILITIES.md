# Bedrock v0.4 能力包

v0.4 在不改变 `AgentRunner` 核心循环的前提下，增加六个彼此独立的能力模块。每个模块拥有自己的服务、工具构建器、验证逻辑和测试；模块之间只通过统一的 `Tool` 协议接入运行时。

## 1. 白名单应用启动

工具：

- `list_allowed_apps`
- `launch_allowed_app`

模型只能提交应用名称或别名，不能提交 `.exe` 路径、命令参数或 Shell 命令。默认尝试识别网易云音乐、记事本、Windows 计算器、文件资源管理器和 VS Code。

首次启动后会生成：

```text
private/app_allowlist.json
```

网易云未被自动识别时，打开桌面端“能力中心”，点击“选择网易云程序…”，选择可信的 `cloudmusic.exe`。路径会写入本机私有的 `private/app_allowlist.json`，无需手工编辑 JSON，也无需重启。启动应用属于外部动作，每次执行都需要本地审批。

## 2. Windows 媒体控制

工具：`control_system_media`

支持：

- `play_pause`
- `next`
- `previous`
- `volume_up`
- `volume_down`
- `mute`
- `stop`

它发送 Windows 系统媒体键，不接触任意命令行。网易云、浏览器和其他响应系统媒体键的播放器均可能受控。执行前需要审批。

## 3. 安全网页检索

工具：

- `search_public_web`
- `read_public_web_page`

安全边界：

- 只允许 `http` 和 `https`；
- DNS 解析到 localhost、局域网、链路本地、保留地址时拒绝；
- 每次跳转重新检查目标；
- 禁止 URL 内嵌账号密码；
- 单次响应最多 1 MB，正文最多 5 万字符；
- 搜索结果和网页正文始终视为不可信数据；
- 网络访问需要本地审批。

当前搜索后端使用 DuckDuckGo HTML 页面。如果所在网络无法访问该站，工具会明确报错，不会伪造搜索结果。

## 4. 可撤销文件整理

工具：

- `plan_workspace_organization`
- `apply_workspace_organization`
- `undo_workspace_organization`

仅处理 `workspace/` 内指定目录的第一层文件。支持按扩展名或修改月份整理。

流程：

```text
生成预览计划 → 返回全部移动项 → 本地审批 → 执行移动 → 可按 plan_id 撤销
```

计划保存在 `private/file_plans/`，带完整性摘要。遇到中途错误时会回滚已经完成的移动。

## 5. 安全编程助手

工具：

- `inspect_code_project`
- `search_code_text`
- `check_python_syntax`
- `replace_code_text_exact`
- `restore_code_backup`

该模块不会运行任意 Shell，也不会导入项目代码。Python 语法检查只调用 `compile()`，不会执行模块顶层语句。

代码修改必须提供精确的旧文本、预期出现次数和新文本；次数不一致则拒绝。修改前的文件自动保存到：

```text
private/code_backups/<backup_id>/
```

修改和恢复都需要审批。

## 6. 学习管理

工具：

- `create_study_plan`
- `record_study_session`
- `get_learning_dashboard`
- `get_review_queue`

数据独立保存在 `private/learning.db`，不与 Agent 会话数据库耦合。可保存每日计划、学习时长、自信度和间隔复习时间。

桌面端“能力中心”会显示近 30 天学习次数、总分钟数和待复习项目。

## 建议测试语句

```text
请列出允许启动的应用。
请打开网易云音乐。
请切换当前音乐的播放或暂停。
搜索 Python pytest 入门资料，列出 5 个结果。
预览 workspace 根目录按扩展名整理的方案，不要直接执行。
检查 workspace 中 Python 项目的结构和语法错误。
给我制定 30 天 Python 与 Agent 开发学习计划，每天 90 分钟，并保存。
```

## v0.4.4 工作区导入与通用应用

“能力中心”会显示工作区绝对路径，并提供文件/文件夹导入。应用白名单支持用户选择任意可信 `.exe` 或 `.lnk`，模型只能使用保存后的应用名称，不能自己提供路径；每次启动仍需审批。

## MCP 与 Skill

Bedrock 的原生 Skill 是受约束的工具配方，可把已有工具组合为可复用流程。MCP 则连接外部 Server 并动态发现工具。两者最终都进入统一 `ToolRegistry`，所以仍使用同一套参数校验、风险策略、审批和轨迹系统。
