"""WebSocket chat interface to communicate with the OpenClaw agent."""

import json
import logging

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import OPENCLAW_GATEWAY_URL

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with the JobPilot agent."""
    await websocket.accept()
    logger.info("WebSocket chat client connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            user_text = message.get("text", "")

            if not user_text:
                await websocket.send_json({"type": "error", "text": "Empty message"})
                continue

            await websocket.send_json({"type": "thinking", "text": "Processing..."})

            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(
                        f"{OPENCLAW_GATEWAY_URL}/v1/chat/completions",
                        json={
                            "messages": [{"role": "user", "content": user_text}],
                            "stream": False,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    assistant_text = result.get("choices", [{}])[0].get("message", {}).get("content", "No response")
                    await websocket.send_json({
                        "type": "message",
                        "role": "assistant",
                        "text": assistant_text,
                    })

            except httpx.ConnectError:
                await websocket.send_json({
                    "type": "error",
                    "text": "OpenClaw gateway not running. Start it with: openclaw gateway",
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "text": f"Error communicating with agent: {str(e)}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket chat client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
