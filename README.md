[English](README_EN.md) | 中文

# OpenAPI MCP Server

> 让 Claude Code 等 AI 编码助手**直接读懂你的后端 API**，不再手动喂文档、不再废 token 翻代码库。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green)](https://modelcontextprotocol.io)
[![OpenAPI 3.x](https://img.shields.io/badge/OpenAPI-3.x-orange)](https://swagger.io/specification/)

**OpenAPI MCP Server** 是一个基于 [MCP (Model Context Protocol)](https://modelcontextprotocol.io) 的轻量级服务，将后端 OpenAPI / Swagger 规范转化为 AI Agent 可直接调用的工具。配置一次，AI 助手即可**搜索端点、查看参数、理解响应结构**——你再也不用手动维护 API 文档给 AI 看。

**关键词**：`Claude Code` `MCP Server` `OpenAPI` `Swagger` `API Discovery` `AI Coding Assistant` `Cursor` `Windsurf` `Model Context Protocol`

---

## 我的痛点

我是个全栈开发，前后端分离项目。开发前端时，AI 编程助手（Claude Code、Cursor 等）根本不知道后端有哪些接口，每次都卡在这一步。

我试过几种办法，都不好使：

**让 AI 自己探索后端代码库？** 太慢了，而且疯狂烧 token。AI 要读 Controller、读 Service、读 DTO，一个接口定义散落在好几个文件里，读完了还不一定理解对。一个中等项目的后端代码库，AI 光是"了解接口"就要消耗几万 token，还不算理解错误的返工。

**手动写一份 API 文档给 AI？** 能用，但后端一更新，文档就过期了。改一个字段名、加一个参数、调整一个响应结构——文档都得同步改。后端迭代快的时候，文档永远滞后于代码，AI 拿着过期文档写出来的前端代码，跑起来就是 bug。

**每次对话都复制粘贴 Swagger UI 的内容？** 更痛苦。一个接口的参数、请求体、响应结构，复制过来就是一大坨 JSON，对话里贴几个接口，上下文窗口就占满了。

**我真正想要的很简单**：AI 助手能**自己查**后端有哪些接口、每个接口怎么调，而且后端更新了它也能**自动知道**。我不该当 AI 和后端之间的"人肉文档搬运工"。

这就是 OpenAPI MCP Server 做的事——**把后端 API 规范变成 AI 的原生能力**。

---

## 快速使用

### 拉取项目

```bash
git clone https://github.com/pwg-code/openapi-mcp.git
cd openapi-mcp
```

### 安装依赖

使用 [uv](https://docs.astral.sh/uv/)（推荐）：

```bash
uv pip install -e .
```

或使用 pip：

```bash
pip install -e .
```

---

## Claude Code 配置

MCP Server 由客户端自动启动，你只需要在配置文件中声明即可。

### 项目级配置

在项目根目录创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "openapi": {
      "command": "<OPENAPI_MCP_PATH>",
      "args": [
        "serve",
        "--url", "user-service=https://api.example.com/v3/api-docs",
        "--url", "order-service=https://order.internal/api-docs",
        "--file", "petstore=./specs/petstore.json"
      ]
    }
  }
}
```

> `<OPENAPI_MCP_PATH>` 替换为 `openapi-mcp` 可执行文件的完整路径，例如 `D:/project/private/openapi-mcp/.venv/Scripts/openapi-mcp.exe`

### 全局配置

在用户目录 `~/claude.json` 中添加，所有项目共享：

```json
{
  "mcpServers": {
    "openapi": {
      "command": "<OPENAPI_MCP_PATH>",
      "args": [
        "serve",
        "--url", "suibian=http://localhost:8000/openapi.json",
        "--file", "petstore=./specs/petstore.json"
      ]
    }
  }
}
```

配置完成后，Claude Code 会自动启动 MCP Server，你可以直接用自然语言：

```
> 后端用户服务有哪些接口？
> 搜一下登录相关的接口
> 这个接口的请求参数是什么？
> 帮我写这个接口的前端调用代码
```

## OpenCode 配置

在项目根目录创建 `opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "openapi": {
      "type": "local",
      "enabled": true,
      "command": [
        "<OPENAPI_MCP_PATH>",
        "serve",
        "--url",
        "suibian=http://localhost:8000/openapi.json"
      ]
    }
  }
}
```

> `<OPENAPI_MCP_PATH>` 替换为 `openapi-mcp` 可执行文件的完整路径，例如 `D:/project/private/openapi-mcp/.venv/Scripts/openapi-mcp.exe`

AI 会自动调用以下工具获取接口信息，无需你手动操作：

| Tool | 用途 |
|------|------|
| `search_endpoints` | 按关键词搜索端点（匹配路径、摘要、Tag、OperationId） |
| `get_endpoint_detail` | 获取端点完整信息：参数、请求体、响应（`$ref` 自动展开） |
| `list_projects` | 列出所有已加载的项目及状态 |
| `list_tags` | 按功能模块浏览端点分组 |
| `refresh_spec` | 手动触发刷新，重新加载 API 规范 |

---

## 配置参数参考表

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--url NAME=URL` | string | — | 远程 OpenAPI 规范地址，可重复指定多个 |
| `--file NAME=PATH` | string | — | 本地 OpenAPI 规范文件路径，可重复指定多个 |
| `--refresh-interval` | int | `300` | 自动刷新间隔（秒），`0` 禁用自动刷新 |
| `--request-timeout` | int | `30` | 远程请求超时（秒） |

### 刷新机制

| 来源类型 | 变更检测方式 | 说明 |
|----------|-------------|------|
| 本地文件 (`--file`) | SHA-256 哈希比对 | 每次检查读取文件计算哈希，无变更则跳过 |
| 远程 URL (`--url`) | ETag + If-None-Match 条件请求 | 304 响应表示无变更，否则哈希比对 |

- 刷新失败不影响当前缓存数据，服务持续可用
- `--refresh-interval 0` 禁用自动刷新，仍可通过 `refresh_spec` 手动触发

---

## 系统要求

- Python >= 3.10
- OpenAPI 3.x（3.0 / 3.1）

---

如果你也受够了当 AI 和后端之间的文档搬运工，给个 Star 吧。有问题或想法，欢迎提 Issue，一起让它更好用。
