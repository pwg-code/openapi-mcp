"""MCP Server entry point using FastMCP."""

from __future__ import annotations

import asyncio
import logging
import sys

from mcp.server.fastmcp import FastMCP

from openapi_mcp_server.models import AppConfig
from openapi_mcp_server.registry import ProjectRegistry
from openapi_mcp_server.refresh import RefreshManager
from openapi_mcp_server.tools import detail, list_projects, list_tags, refresh, search

logger = logging.getLogger(__name__)

_SERVER_INSTRUCTIONS = """\
本服务用于发现和查询后端 OpenAPI 接口规范。

【何时使用】
当用户提出任何与后端 API / 接口相关的问题时，必须使用本服务的工具，不要通过读取代码库来查找接口定义。
典型场景包括：
- "后端有哪些接口" / "有哪些 API"
- "搜一下登录相关的接口" / "有没有用户创建的接口"
- "这个接口的参数是什么" / "这个接口怎么调"
- "接口更新了" / "找不到这个接口"

【工具调用顺序】
1. 如果不知道项目名称 -> 先调用 list_projects 获取项目列表
2. 搜索接口 -> 调用 search_endpoints（按关键词搜索）
3. 查看接口详情 -> 调用 get_endpoint_detail（获取完整参数和响应结构）
4. 按分类浏览 -> 调用 list_tags 获取标签分组
5. 接口可能已更新 -> 调用 refresh_spec 重新加载

【重要提醒】
- search_endpoints 只返回摘要信息，获取参数/请求体/响应结构必须再调用 get_endpoint_detail
- 调用任何工具都需要 project 参数，如果不确定项目名，先调用 list_projects
- 不要通过读取后端代码来查找接口定义，使用本服务的工具更快速、更准确

【项目加载状态与降级】
- 各项目的规范在后台加载，目标项目可能处于"加载中（loading）"或"失败（error）"状态
- 调用 list_projects 可查看每个项目的加载状态与失败原因，一次即可判断哪些项目当前可用
- 当目标项目未就绪时，search_endpoints / get_endpoint_detail / list_tags 会立即返回状态说明而不阻塞：
  - status=loading：规范仍在后台加载，请稍后重试同一工具
  - status=error：加载失败（返回原因），可调用 refresh_spec(project=该名称) 立即重试；
    失败项目也会按退避节奏自动重试，后端恢复后无需人工干预
- refresh_spec 可用于手动恢复失败的项目，成功后项目立即可用
"""

mcp = FastMCP("openapi-mcp", instructions=_SERVER_INSTRUCTIONS)

_registry: ProjectRegistry | None = None
_refresh_manager: RefreshManager | None = None


def _get_registry() -> ProjectRegistry:
    if _registry is None:
        raise RuntimeError("Server not initialized")
    return _registry


def _get_refresh_manager() -> RefreshManager:
    if _refresh_manager is None:
        raise RuntimeError("Server not initialized")
    return _refresh_manager


# --- Register Tools ---


@mcp.tool()
async def search_endpoints(project: str, query: str, method: str | None = None, tag: str | None = None, limit: int = 10) -> str:
    """按关键词搜索 API 端点。搜索范围包括路径、摘要、标签和 operationId。

何时使用：
- 用户想查找某个功能的接口时
- 用户询问“有没有 XXX 接口”时
- 用户想了解某类接口时

触发示例：
- “搜一下登录相关的接口”
- “有没有用户创建的接口”
- “查找订单 API”
- “怎么调用支付接口”
- “有没有删除用户的 API”

参数说明：
- project: 项目名称（如不确定，先调用 list_projects）
- query: 搜索关键词，如“登录”、“用户”、“订单”
- method: 可选，按 HTTP 方法过滤（GET/POST/PUT/DELETE）
- tag: 可选，按标签过滤（标签可通过 list_tags 获取）
- limit: 返回数量上限，默认 10

注意：本工具只返回摘要信息（路径、方法、摘要）。如需查看完整参数、请求体和响应结构，请继续调用 get_endpoint_detail。
如果目标项目处于"加载中/失败"状态，本工具会立即返回包含 status（loading/error）、失败原因与恢复建议的状态说明，请稍后重试或调用 refresh_spec(project=该名称)。
"""
    return await search.handle(_get_registry(), {
        "project": project,
        "query": query,
        "method": method,
        "tag": tag,
        "limit": limit,
    })


@mcp.tool()
async def get_endpoint_detail(project: str, path: str, method: str) -> str:
    """获取 API 端点的完整详情，包括：请求参数（必填/可选）、请求体结构、响应结构。所有 $ref 引用已内联展开。

何时使用：
- 在 search_endpoints 找到目标接口后，获取完整调用信息
- 用户询问“这个接口的参数是什么”时
- 用户需要知道接口的请求体或响应结构时
- 用户要求“帮我写这个接口的调用代码”时

触发示例：
- “这个接口的参数是什么”
- “这个接口请求体怎么传”
- “这个接口返回什么结构”
- “帮我写这个接口的前端调用代码”

参数说明：
- project: 项目名称
- path: 接口路径（从 search_endpoints 结果中获取）
- method: HTTP 方法（从 search_endpoints 结果中获取）

注意：必须先通过 search_endpoints 获取到 path 和 method，再调用本工具获取详情。
如果目标项目处于"加载中/失败"状态，本工具会立即返回包含 status（loading/error）、失败原因与恢复建议的状态说明，请稍后重试或调用 refresh_spec(project=该名称)。
"""
    return await detail.handle(_get_registry(), {
        "project": project,
        "path": path,
        "method": method,
    })


@mcp.tool(name="list_projects")
async def list_projects_tool() -> str:
    """列出所有 OpenAPI 项目（名称、版本、端点数量），并包含每个项目的加载状态（loading/loaded/error）与最近一次失败的原因。

何时使用：
- 用户不知道有哪些后端服务/项目时
- 用户询问“有哪些接口”但未指定具体项目时
- 调用其他工具前需要获取 project 参数时
- 需要判断哪些项目当前可用、哪些不可用及原因时

触发示例：
- “后端有哪些服务”
- “有哪些项目”
- “有哪些 API”
- “有哪些接口”

注意：调用 search_endpoints、get_endpoint_detail、list_tags 等工具都需要 project 参数，如果不确定项目名，请先调用本工具。
对 status=error 的项目，可通过 refresh_spec(project=该名称) 立即尝试恢复；loading 的项目请稍等片刻再使用。
"""
    return await list_projects.handle(_get_registry(), {})


@mcp.tool(name="list_tags")
async def list_tags_tool(project: str) -> str:
    """列出 API 的标签分组（如“用户管理”、“订单管理”、“认证鉴权”），显示每个分组的端点数量。

何时使用：
- 用户想按功能模块浏览接口时
- 用户想了解接口的分类结构时
- 获取标签名称后用于 search_endpoints 的 tag 参数过滤

触发示例：
- “接口有哪些分类”
- “有哪些功能模块”
- “按分组看看接口”
- “用户相关的接口有哪些”

参数说明：
- project: 项目名称（如不确定，先调用 list_projects）

注意：本工具返回标签列表和端点数量。如需查看具体端点，请使用 search_endpoints 并传入 tag 参数进行过滤。
如果目标项目处于"加载中/失败"状态，本工具会立即返回包含 status（loading/error）、失败原因与恢复建议的状态说明，请稍后重试或调用 refresh_spec(project=该名称)。
"""
    return await list_tags.handle(_get_registry(), {"project": project})


@mcp.tool()
async def refresh_spec(project: str | None = None) -> str:
    """重新从数据源加载 OpenAPI 规范。支持刷新单个项目或全部项目。

何时使用：
- 后端接口已更新，需要同步最新规范时
- search_endpoints 找不到应该存在的接口时
- 用户明确要求刷新/重载接口规范时

触发示例：
- “接口更新了，刷新一下”
- “后端加了新接口，同步一下”
- “找不到这个接口，可能更新了”
- “重新加载 API 规范”

参数说明：
- project: 可选，指定要刷新的项目名称。不传则刷新所有项目。

注意：本服务已开启自动刷新（默认每 15 秒，可通过 --refresh-interval 自定义），通常无需手动刷新。仅在自动刷新间隔内有紧急更新需求时使用。
本工具也可用于恢复加载失败的项目：对失败项目会立即触发一次加载（不受自动重试的退避节奏限制）；若该项目已有加载在进行中，则直接返回该次加载的结果，不会重复发起。
"""
    return await refresh.handle(_get_registry(), _get_refresh_manager(), {
        "project": project,
    })


# --- Server Lifecycle ---


async def run_server(config: AppConfig) -> None:
    global _registry, _refresh_manager

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    _registry = ProjectRegistry(config)
    _refresh_manager = RefreshManager(_registry)

    total = len(_registry.get_project_names())
    logger.info(
        f"OpenAPI MCP Server ready: {total} project(s) registered; "
        f"specs are loading in the background, tools serve immediately"
    )

    load_task = asyncio.create_task(_registry.load_all())
    _refresh_manager.start()

    try:
        await mcp.run_stdio_async()
    finally:
        _refresh_manager.stop()
        load_task.cancel()
        try:
            await load_task
        except asyncio.CancelledError:
            pass
