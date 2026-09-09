# Bedrock v0.5.1 科技感桌面端

v0.5.1 修复了 Qt 6.11 对 QML 子对象分隔符的严格解析问题；界面设计与 v0.5.0 保持一致。

v0.5.0 将默认桌面界面从 Tkinter 替换为 **PySide6 + QML**。视觉语言参考用户提供的深色科技任务面板：深黑背景、半透明层叠卡片、荧光绿色状态、左侧导航、中央任务空间和右侧 Agent 状态栏。未复制原图品牌、头像或具体布局。

## 入口

```powershell
bedrock-desktop
```

旧界面保留为回退入口：

```powershell
bedrock-desktop-legacy
```

仅预览前端、不连接模型：

```powershell
bedrock-desktop-preview
```

## 页面

- 任务总览：统计卡、层叠任务棱镜、学习进度和审批队列；
- Agent 对话：虚拟化消息列表，工具大参数默认折叠；
- 任务管理：最近会话与执行上下文；
- 审批中心：永久可见的允许/拒绝闭环；
- 工作区：显示绝对路径、导入文件或项目；
- 应用管理：通用应用白名单与测试启动；
- 学习、Skills、MCP、记忆、运行轨迹、设置。

右上角“帮助与技能”包含 12 个预设测试卡片。点击“填入对话”只填充提示词；“直接测试”会启动 Agent，但不会绕过审批。

## 性能原则

- 页面通过 `Loader` 按需创建，隐藏页面不会常驻大量控件；
- `StableListModel` 使用内容指纹，数据不变不发 reset；
- 对话正常情况下只追加新消息；
- QML `ListView/GridView` 开启 delegate 复用和有限缓存；
- 文件扫描、模型调用和导入操作在线程池执行；
- 不使用持续粒子、实时模糊或无限动画；
- 旧 Tkinter UI 保留，以便新显卡/驱动兼容问题时回退。

## 安全

QML 只调用 `BedrockViewModel`，ViewModel 再调用 `DesktopController`。QML 无法直接访问数据库、Shell、文件系统或 MCP。现有工作区隔离、应用白名单、MCP 外部工具审批和运行轨迹全部保留。
