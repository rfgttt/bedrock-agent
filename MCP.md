# Bedrock MCP 连接器（v0.4.5）

Bedrock 现在可以把外部 MCP Server 暴露的 **Tools** 转换成本地 Agent 工具。

## 安装官方 SDK

MCP 是可选依赖，不安装也不影响 Bedrock 的聊天、记忆、文件和应用能力：

```powershell
python -m pip install -e ".[mcp]"
```

Bedrock 使用官方 MCP Python SDK v2。依赖范围为 `mcp>=2.0.0rc1,<3`：当软件源尚未同步正式 v2 时可以安装 `2.0.0rc1`，同步后则可自动使用兼容的正式 2.x 版本。

MCP 连接不会在桌面启动阶段自动发生，避免某个失效的 Server 让首屏卡死。

## 导入配置

桌面端进入 **MCP** 页面，点击“导入 MCP 配置…”。支持 Claude Desktop 风格：

```json
{
  "mcpServers": {
    "demo-server": {
      "command": "python",
      "args": ["D:/mcp/demo_server.py"],
      "env": {
        "DEMO_KEY": "local-secret"
      }
    }
  }
}
```

也支持 HTTP：

```json
{
  "mcpServers": {
    "remote-docs": {
      "url": "https://example.com/mcp"
    }
  }
}
```

导入后服务器默认关闭。启用时 Bedrock 会再次询问；同步工具后，工具以 `mcp_<server>_<tool>` 命名。

## 安全规则

- MCP 配置保存在 `private/mcp_servers.json`；
- stdio Server 只得到配置中明确写出的环境变量，不继承 Bedrock 的 DeepSeek 密钥；
- 远程明文 HTTP 只允许 localhost，外部地址必须 HTTPS；
- 所有 MCP 工具一律标记为 `external`，每次执行都需要本地审批；
- 当前仅接入 Tools，Resources 和 Prompts 尚未进入模型上下文；
- 每次发现或调用后连接立即关闭，避免长期子进程和 socket 泄漏；
- MCP Server 本身属于第三方代码，启用前仍需自行确认来源。
