"""
Simulates Parent & Child exchange over GoPush WebSocket server.
Tests:
1. Fallback required when peer is offline
2. Successful delivery + ACK when both peers are online
"""
import asyncio
import json
import websockets

SERVER_URL = "ws://127.0.0.1:8080/ws"
ROOM_ID = "test-device-123"

async def test_flow():
    print("--- Test 1: Parent connects alone, sends signal (Should get fallback_required) ---")
    async with websockets.connect(f"{SERVER_URL}?roomId={ROOM_ID}&role=parent") as parent_ws:
        signal = {
            "signalId": "sig-001",
            "roomId": ROOM_ID,
            "target": "child",
            "payload": {"action": "start_screen"}
        }
        await parent_ws.send(json.dumps(signal))
        reply = await asyncio.wait_for(parent_ws.recv(), timeout=2)
        data = json.loads(reply)
        print("Parent received:", data)
        assert data.get("type") == "fallback_required", "Expected fallback_required!"
        assert data.get("reason") == "peer_offline", "Expected peer_offline!"
        print("Test 1 PASSED: Immediate fallback trigger working perfectly!")

    print("\n--- Test 2: Both Parent & Child connected, signal sent (Should get ACK) ---")
    async with websockets.connect(f"{SERVER_URL}?roomId={ROOM_ID}&role=child") as child_ws:
        async with websockets.connect(f"{SERVER_URL}?roomId={ROOM_ID}&role=parent") as parent_ws:
            signal = {
                "signalId": "sig-002",
                "roomId": ROOM_ID,
                "target": "child",
                "payload": {"action": "start_camera"}
            }
            await parent_ws.send(json.dumps(signal))
            
            # Parent expects ACK
            parent_reply = await asyncio.wait_for(parent_ws.recv(), timeout=2)
            parent_data = json.loads(parent_reply)
            print("Parent received:", parent_data)
            assert parent_data.get("type") == "ack", "Expected ACK!"

            # Child expects signal payload
            child_reply = await asyncio.wait_for(child_ws.recv(), timeout=2)
            child_data = json.loads(child_reply)
            print("Child received payload:", child_data.get("payload"))
            assert child_data.get("payload", {}).get("action") == "start_camera"
            print("Test 2 PASSED: Direct instant delivery + ACK working perfectly!")

if __name__ == "__main__":
    asyncio.run(test_flow())

