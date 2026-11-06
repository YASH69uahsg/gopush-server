"""
Local Development WebSocket Server for GoPush Protocol.
Runs identically to services/gopush/main.go for zero-friction local testing on Windows.
"""
import asyncio
import json
import logging
import os
import urllib.parse
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# room_id -> {"parent": ws, "child": ws}
rooms = {}
rooms_lock = asyncio.Lock()

async def handler(websocket):
    raw_path = getattr(websocket, "path", None)
    if not raw_path and hasattr(websocket, "request"):
        raw_path = websocket.request.path
    if not raw_path:
        raw_path = "/"

    parsed = urllib.parse.urlparse(raw_path)
    params = urllib.parse.parse_qs(parsed.query)

    room_id = params.get("roomId", [None])[0]
    role = params.get("role", [None])[0]

    if not room_id or role not in ("parent", "child"):
        logging.warning(f"Rejecting connection: invalid roomId ({room_id}) or role ({role})")
        await websocket.close(1008, "Invalid parameters")
        return

    async with rooms_lock:
        if room_id not in rooms:
            rooms[room_id] = {}
        old_ws = rooms[room_id].get(role)
        if old_ws:
            try:
                await old_ws.close(1000, "Replaced by new connection")
            except Exception:
                pass
        rooms[room_id][role] = websocket
        logging.info(f"[Connected] Room: {room_id}, Role: {role} (Active in room: {len(rooms[room_id])})")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                signal_id = data.get("signalId")
                target_role = data.get("target")

                async with rooms_lock:
                    target_ws = rooms.get(room_id, {}).get(target_role)

                if not target_ws:
                    # Critical Fix 1: Instant Fallback Trigger
                    await websocket.send(json.dumps({
                        "type": "fallback_required",
                        "signalId": signal_id,
                        "reason": "peer_offline"
                    }))
                    continue

                try:
                    await target_ws.send(message)
                    # Delivery confirmation ACK
                    await websocket.send(json.dumps({
                        "type": "ack",
                        "signalId": signal_id
                    }))
                except Exception as e:
                    await websocket.send(json.dumps({
                        "type": "fallback_required",
                        "signalId": signal_id,
                        "reason": "send_failed"
                    }))

            except Exception as e:
                logging.error(f"Error handling message: {e}")

    except Exception as e:
        logging.info(f"Socket closed: {e}")
    finally:
        async with rooms_lock:
            if room_id in rooms and rooms[room_id].get(role) == websocket:
                del rooms[room_id][role]
                logging.info(f"[Disconnected] Room: {room_id}, Role: {role}")
                if not rooms[room_id]:
                    del rooms[room_id]

async def main():
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"GoPush Local Dev Server listening on ws://0.0.0.0:{port}/ws")
    async with websockets.serve(handler, "0.0.0.0", port, ping_interval=20, ping_timeout=45):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
