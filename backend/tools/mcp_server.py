# -*- coding: utf-8 -*-
"""
MCP Server 端点

提供 MCP 协议的工具调用接口，供 OpenCode Agent 使用。
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .mcp import get_tool_definitions, execute_tool

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    name: str
    result: Dict[str, Any]
    error: str | None = None


@router.get("/tools", summary="列出所有工具")
def list_mcp_tools() -> List[Dict[str, Any]]:
    """
    列出所有可用的 MCP 工具

    返回符合 MCP 协议的工具定义列表
    """
    return get_tool_definitions()


@router.post("/call", summary="调用工具")
def call_tool(request: ToolCallRequest) -> ToolCallResponse:
    """
    调用指定工具

    Args:
        request: 包含工具名称和参数的请求

    Returns:
        工具执行结果
    """
    result = execute_tool(request.name, request.arguments)

    error = result.pop("error", None) if isinstance(result, dict) else None

    return ToolCallResponse(
        name=request.name,
        result=result,
        error=error,
    )


@router.post("/batch", summary="批量调用工具")
def batch_call_tools(requests: List[ToolCallRequest]) -> List[ToolCallResponse]:
    """
    批量调用多个工具

    Args:
        requests: 工具调用请求列表

    Returns:
        工具执行结果列表
    """
    responses = []
    for req in requests:
        result = execute_tool(req.name, req.arguments)
        error = result.pop("error", None) if isinstance(result, dict) else None
        responses.append(ToolCallResponse(
            name=req.name,
            result=result,
            error=error,
        ))
    return responses
