import asyncio
import websockets
import json

async def test():
    uri = 'wss://gopush-server.onrender.com/ws?roomId=YiPbXSjfVjajifPiSg7LUPjW1CW2&role=parent'
    print(f'Connecting to {uri}...')
    try:
        async with websockets.connect(uri, open_timeout=15) as ws:
            print('Connected successfully!')
            msg = {
                'roomId': 'YiPbXSjfVjajifPiSg7LUPjW1CW2',
                'target': 'child',
                'signalId': 'sig-live-test',
                'payload': {'type': 'ping'}
            }
            await ws.send(json.dumps(msg))
            reply = await asyncio.wait_for(ws.recv(), timeout=5)
            print('Reply received:', reply)
    except Exception as e:
        print('Error:', type(e), e)

if __name__ == '__main__':
    asyncio.run(test())

