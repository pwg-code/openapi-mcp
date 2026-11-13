"""Shared helper for tool responses when a project exists but is not ready."""

from __future__ import annotations

from openapi_mcp_server.models import ProjectNotReadyStatus, ProjectStatus
from openapi_mcp_server.registry import ProjectRegistry


def not_ready_response(registry: ProjectRegistry, name: str) -> str | None:
    """Build a structured status payload for a project whose spec is loading or failed.

    Returns None when the project is ready (or unknown), so callers can proceed
    with their normal flow or unknown-project error.
    """
    entry = registry.get_entry(name)
    if entry is None:
        return None

    if entry.status == ProjectStatus.LOADING:
        payload = ProjectNotReadyStatus(
            project=name,
            status=ProjectStatus.LOADING.value,
            message=f"项目 '{name}' 的 OpenAPI 规范正在后台加载，尚未就绪。",
            suggestion=(
                f"请稍后重试该工具；或调用 refresh_spec(project='{name}') 立即尝试加载。"
                "可通过 list_projects 查看所有项目的加载状态与失败原因。"
            ),
        )
        return payload.model_dump_json(indent=2)

    if entry.status == ProjectStatus.ERROR:
        reason = entry.error_message or "unknown error"
        payload = ProjectNotReadyStatus(
            project=name,
            status=ProjectStatus.ERROR.value,
            message=f"项目 '{name}' 的 OpenAPI 规范加载失败：{reason}",
            suggestion=(
                f"可调用 refresh_spec(project='{name}') 立即重试加载；"
                "失败项目也会按退避节奏自动重试，后端恢复后会自动变为可用。"
                "可通过 list_projects 查看所有项目的加载状态与失败原因。"
            ),
        )
        return payload.model_dump_json(indent=2)

    return None
