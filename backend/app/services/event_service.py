"""Event broker for real-time Server-Sent Events (SSE) and database event persistence."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.database.session import SessionLocal
from app.repositories.screening_repo import ScreeningRepository
from app.core.logging import get_logger

logger = get_logger("event_service")


class EventBroker:
    """Publish-subscribe broker for real-time SSE streaming."""

    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Register a new SSE client subscriber."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.append(queue)
        logger.info("SSE client subscribed (active listeners: %d)", len(self._subscribers))
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unregister an SSE client."""
        async with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
        logger.info("SSE client unsubscribed (remaining listeners: %d)", len(self._subscribers))

    async def emit(
        self,
        event_type: str,
        message: str,
        run_id: Optional[int] = None,
        candidate_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Broadcast an event to all connected SSE clients and persist to SQLite.
        """
        # 1. Persist to SQLite
        try:
            db = SessionLocal()
            try:
                repo = ScreeningRepository(db)
                repo.record_activity_event(
                    event_type=event_type,
                    message=message,
                    run_id=run_id,
                    candidate_id=candidate_id,
                    metadata=metadata,
                )
            finally:
                db.close()
        except Exception as exc:
            logger.error("Failed to persist activity event to SQLite: %s", exc)

        # 2. Broadcast to live SSE clients
        payload = {
            "event_type": event_type,
            "message": message,
            "run_id": run_id,
            "candidate_id": candidate_id,
            "metadata": metadata or {},
        }
        json_data = json.dumps(payload)

        async with self._lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(json_data)
                except asyncio.QueueFull:
                    dead_queues.append(q)

            for dq in dead_queues:
                if dq in self._subscribers:
                    self._subscribers.remove(dq)


# Singleton broker instance
event_broker = EventBroker()


async def event_generator() -> AsyncGenerator[str, None]:
    """Async generator yielding SSE formatted data packets."""
    queue = await event_broker.subscribe()
    try:
        while True:
            data = await queue.get()
            yield f"data: {data}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        await event_broker.unsubscribe(queue)
