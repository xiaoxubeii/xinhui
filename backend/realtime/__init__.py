# -*- coding: utf-8 -*-
"""
实时模块
"""

from .websocket import RealtimeManager, realtime_manager, websocket_endpoint

__all__ = [
    'RealtimeManager',
    'realtime_manager',
    'websocket_endpoint',
]
