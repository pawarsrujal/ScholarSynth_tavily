"""In-memory task event hub for live SSE updates."""

from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, DefaultDict, Dict, List


class EventHub:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[asyncio.Queue[Dict[str, Any]]]] = defaultdict(list)
        self._lock = threading.RLock()

    async def publish(self, task_id: str, event: str, data: Dict[str, Any] | None = None) -> None:
        payload = {
            "event": event,
            "task_id": task_id,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            queues = list(self._subscribers.get(task_id, []))
        for queue in queues:
            await queue.put(payload)

    def subscribe(self, task_id: str) -> asyncio.Queue[Dict[str, Any]]:
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        with self._lock:
            self._subscribers[task_id].append(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue[Dict[str, Any]]) -> None:
        with self._lock:
            queues = self._subscribers.get(task_id)
            if not queues:
                return
            if queue in queues:
                queues.remove(queue)
            if not queues:
                self._subscribers.pop(task_id, None)


event_hub = EventHub()
