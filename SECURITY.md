# Bedrock Security Boundary

## What is enforced

1. The HTTP API can bind only to `127.0.0.1`, `::1`, or `localhost`.
2. Every API request must come from a loopback socket peer and include the local bearer token.
3. `X-Forwarded-For` is ignored; a remote proxy cannot pretend to be localhost.
4. Bedrock checks that the process runs under the configured OS user.
5. The database, token, traces, and workspace are private directories.
6. File tools resolve the real path and reject any path escaping `workspace/`.
7. Learned recipe skills can use only tools already registered by the application.
8. Arbitrary generated Python, shell code, dependency installation, and dynamic imports are not allowed.
9. Durable memory, skill installation, writes, and external effects require explicit approval.

## Important limitation

An IP address does not identify a human. Any program running under the same local OS account may be able to read that account's files and token. Bedrock itself also runs as that account, so the operating system cannot distinguish “you” from “Bedrock” unless Bedrock is run under a separate service account, virtual machine, or container.

For the requested “my local user plus Bedrock” model, the included default is:

- deny every remote/LAN client;
- allow only the configured local OS account;
- authenticate local API calls with a private random token;
- confine Bedrock's autonomous file access to its own workspace;
- require approval for persistent or side-effecting changes.

On Windows, run `scripts/harden_windows_acl.ps1` once from PowerShell. On Linux/macOS, run `scripts/harden_posix.sh`.

## Why local-only access is not enough

A model can still make a bad decision, and untrusted web or document content can contain prompt injection. Therefore high-impact capabilities must remain separate tools with validation, logs, and approval. Do not grant unrestricted host shell or administrator access merely because the API listens on localhost.

## DeepSeek 密钥文件

v0.3.1 将 DeepSeek API Key 保存在项目根目录 `.env`。该文件被 `.gitignore` 排除，不会写入 SQLite 或运行轨迹。Windows 和 POSIX 权限加固脚本都会在文件存在时将其限制为当前本地用户（Windows 另保留 SYSTEM）可访问。首次通过桌面端保存密钥后，应再次运行对应权限加固脚本。

## v0.4 新能力安全边界

- 应用启动只接受 `private/app_allowlist.json` 中的应用标识，不接受任意路径和参数；
- 媒体控制只发送固定 Windows 媒体键；
- 网页工具在每次请求和跳转前拒绝本地、私有和保留地址，网页正文永远作为不可信数据；
- 文件整理仅限 `workspace/`，先生成计划，执行失败自动回滚，并支持撤销；
- 编程助手不提供 Shell，不导入待检查项目，精确修改前自动备份；
- 学习管理使用独立数据库；
- 应用启动、媒体控制、网络访问、文件移动、代码修改和学习数据写入均需本地审批。


## 资源与数据增长边界

- 模型上下文、桌面消息窗口、自动情景记忆和轨迹文件均有可配置上限；
- 限制只影响自动生成数据和运行窗口，不自动删除用户批准的长期经验；
- 模型与网页 HTTP 客户端在配置重载和退出时关闭，避免后台连接长期残留；
- 请求超时不会赋予额外权限，也不会自动绕过审批。

## MCP 与通用应用的新增边界

- MCP Server 导入后默认禁用；启用和测试均由桌面用户直接触发；
- MCP 工具固定使用外部风险等级，每次调用必须审批；
- stdio Server 不继承完整宿主环境；敏感变量必须在私有 MCP 配置中显式提供；
- 应用启动只接受白名单 id/别名，模型不能提供 `.exe`、`.lnk` 或命令行参数；
- 用户通过文件选择器添加应用或导入工作区，模型无法借此浏览任意主机目录。
