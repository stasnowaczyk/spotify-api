import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import RedirectResponse
from spotify.service import SpotifyService
import asyncio

router = APIRouter(prefix="/spotify", tags=["spotify"])
service = SpotifyService()


class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.lock = asyncio.Lock()
        self.polling_task = None
        self.current_track_id = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
            # Start polling if this is the first connection
            if len(self.active_connections) == 1:
                self.polling_task = asyncio.create_task(self._periodic_broadcast())
        print(f"New WebSocket connection. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            try:
                self.active_connections.remove(websocket)
            except ValueError:
                pass
            # Stop polling if no connections remain
            if len(self.active_connections) == 0 and self.polling_task:
                self.polling_task.cancel()
                self.polling_task = None
                self.current_track_id = None
        print(f"WebSocket disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        async with self.lock:
            dead_connections = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"Error sending WebSocket message: {e}")
                    dead_connections.append(connection)

            # Clean up dead connections
            for connection in dead_connections:
                await self.disconnect(connection)

    async def _periodic_broadcast(self):
        """Periodically broadcast now-playing data only when there are active connections"""
        while len(self.active_connections) > 0:
            try:
                data = await service.get_now_playing()
                if data and "item" in data and "id" in data["item"]:
                    track_id = data["item"]["id"]
                    # Only broadcast if track changed
                    if track_id != self.current_track_id:
                        self.current_track_id = track_id
                        await self.broadcast(json.dumps(data))
                elif "error" in data:
                    print(f"Spotify API error: {data['error']}")
            except Exception as e:
                print(f"Broadcast error: {e}")

            await asyncio.sleep(5)  # Poll interval


manager = ConnectionManager()


@router.websocket("/ws/now-playing")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive with ping/pong
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text("ping")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@router.get("/login")
async def login():
    """Redirect to Spotify authorization page"""
    auth_url = service.get_auth_url()
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request):
    """Handle Spotify callback with authorization code"""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        await service.exchange_code(code)
        return {"status": "Successfully authenticated with Spotify!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/now-playing")
async def now_playing():
    """Get current playing track (one-time request)"""
    try:
        data = await service.get_now_playing()
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
