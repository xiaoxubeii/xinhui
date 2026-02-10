# -*- coding: utf-8 -*-
"""
MCP Server 端点

提供 MCP 协议的工具调用接口，供 OpenCode Agent 使用。
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..auth.security import get_current_user_from_request
from ..config import settings
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


def _inject_mcp_user(args: Dict[str, Any], user: dict | None) -> Dict[str, Any]:
    payload = dict(args or {})
    if user and isinstance(user, dict) and user.get("id"):
        payload.setdefault("__user_id", user["id"])
        return payload
    if isinstance(payload.get("user_id"), str) and payload.get("user_id"):
        payload.setdefault("__user_id", payload.get("user_id"))
    elif isinstance(payload.get("patient_id"), str) and payload.get("patient_id"):
        payload.setdefault("__user_id", payload.get("patient_id"))
    return payload


def _allow_mcp_without_user(request: Request) -> bool:
    token = request.query_params.get("token") or request.headers.get("x-mcp-token")
    if settings.mcp_token:
        return bool(token) and token == settings.mcp_token
    if request.client and request.client.host in {"127.0.0.1", "::1"}:
        return True
    return False


def get_mcp_user(request: Request) -> dict | None:
    try:
        return get_current_user_from_request(request)
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        if _allow_mcp_without_user(request):
            return None
        raise


@router.get("/tools", summary="列出所有工具")
def list_mcp_tools() -> List[Dict[str, Any]]:
    """
    列出所有可用的 MCP 工具

    返回符合 MCP 协议的工具定义列表
    """
    return get_tool_definitions()


@router.post("/call", summary="调用工具")
def call_tool(request: ToolCallRequest, user: dict | None = Depends(get_mcp_user)) -> ToolCallResponse:
    """
    调用指定工具

    Args:
        request: 包含工具名称和参数的请求

    Returns:
        工具执行结果
    """
    args = _inject_mcp_user(request.arguments or {}, user)
    result = execute_tool(request.name, args)

    error = result.pop("error", None) if isinstance(result, dict) else None

    return ToolCallResponse(
        name=request.name,
        result=result,
        error=error,
    )


@router.post("/batch", summary="批量调用工具")
def batch_call_tools(requests: List[ToolCallRequest], user: dict | None = Depends(get_mcp_user)) -> List[ToolCallResponse]:
    """
    批量调用多个工具

    Args:
        requests: 工具调用请求列表

    Returns:
        工具执行结果列表
    """
    responses = []
    for req in requests:
        args = _inject_mcp_user(req.arguments or {}, user)
        result = execute_tool(req.name, args)
        error = result.pop("error", None) if isinstance(result, dict) else None
        responses.append(ToolCallResponse(
            name=req.name,
            result=result,
            error=error,
        ))
    return responses


def _jsonrpc_error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _mcp_initialize() -> Dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
            "prompts": {},
            "resources": {},
        },
        "serverInfo": {"name": "xinhui-backend", "version": "1.0.0"},
    }


@router.post("", summary="MCP JSON-RPC endpoint")
async def mcp_rpc(request: Request, user: dict | None = Depends(get_mcp_user)):
    """
    MCP Streamable HTTP endpoint (JSON-RPC).

    Supports minimal methods: initialize, tools/list, tools/call.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"), status_code=400)

    def handle_one(obj: Any) -> Dict[str, Any] | None:
        if not isinstance(obj, dict):
            return _jsonrpc_error(None, -32600, "Invalid Request")
        req_id = obj.get("id")
        method = obj.get("method")
        params = obj.get("params") or {}

        # Notifications have no id; return None (no response).
        is_notification = req_id is None

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": _mcp_initialize()}
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            result = {"tools": get_tool_definitions()}
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        if method == "tools/call":
            if not isinstance(params, dict):
                return _jsonrpc_error(req_id, -32602, "Invalid params")
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str) or not name:
                return _jsonrpc_error(req_id, -32602, "Missing tool name")
            args = _inject_mcp_user(arguments, user)
            result = execute_tool(name, args)
            error = None
            if isinstance(result, dict):
                error = result.pop("error", None)
            content_text = ""
            try:
                import json as _json

                content_text = _json.dumps(result, ensure_ascii=False)
            except Exception:
                content_text = str(result)
            tool_result = {
                "content": [
                    {
                        "type": "text",
                        "text": content_text,
                    }
                ],
                "isError": bool(error),
            }
            if error:
                tool_result["content"].append({"type": "text", "text": f"error: {error}"})
            return {"jsonrpc": "2.0", "id": req_id, "result": tool_result}
        if method in {"prompts/list", "resources/list"}:
            return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": []} if "prompts" in method else {"resources": []}}

        if is_notification:
            return None
        return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    if isinstance(payload, list):
        responses = []
        for item in payload:
            resp = handle_one(item)
            if resp is not None:
                responses.append(resp)
        if not responses:
            return Response(status_code=204)
        return JSONResponse(responses)

    response = handle_one(payload)
    if response is None:
        return Response(status_code=204)
    return JSONResponse(response)
