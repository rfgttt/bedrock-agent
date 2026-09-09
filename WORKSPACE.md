# Bedrock 工作区

默认 `.env` 配置为：

```env
AGENT_WORKSPACE=./workspace
```

因此从项目目录启动时，工作区就在项目下的 `workspace` 文件夹。例如项目位于：

```text
D:\agent专区\Project_Bedrock_Agent_v0.3.1
```

工作区就是：

```text
D:\agent专区\Project_Bedrock_Agent_v0.3.1\workspace
```

## 图形化导入

进入 **能力中心 → 工作区**：

- “打开工作区”：用资源管理器打开真实目录；
- “导入文件…”：选择一个或多个文件；
- “导入文件夹…”：复制整个项目。

导入目标默认是 `workspace/imports/`。Bedrock 只复制，不移动或删除原文件；同名文件自动使用 `(1)`、`(2)` 后缀。符号链接和 Windows 重解析点会被拒绝，防止无意中越过工作区边界。
