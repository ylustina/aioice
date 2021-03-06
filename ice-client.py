import aioice
import argparse
import asyncio
import colorlog
import json
import logging
import websockets


STUN_SERVER = ('stun.l.google.com', 19302)
WEBSOCKET_URI = 'ws://18.191.173.222:8765'


# COLORLOG
logger = colorlog.getLogger()
logger.setLevel(colorlog.colorlog.logging.DEBUG)
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter())
logger.addHandler(handler)

logger.debug("Debug message")
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")


# ICE client offer
async def offer(options):
    connection = aioice.Connection(ice_controlling=True,
                                   components=options.components,
                                   stun_server=STUN_SERVER)
    await connection.gather_candidates()

    websocket = await websockets.connect(WEBSOCKET_URI)

    # send offer
    await websocket.send(json.dumps({
        'candidates': [c.to_sdp() for c in connection.local_candidates],
        'password': connection.local_password,
        'username': connection.local_username,
    }))

    # await answer
    message = json.loads(await websocket.recv())
    print('received answer', message)
    connection.remote_candidates = ([aioice.Candidate.from_sdp(c) for c in message['candidates']])
    connection.remote_username = message['username']
    connection.remote_password = message['password']

    await websocket.close()

    await connection.connect()
    print('connected')

    # send data
    data = b'HELLO'
    component = 1
    print('sending %s on component %d' % (repr(data), component))
    await connection.sendto(data, component)
    data, component = await connection.recvfrom()
    print('received %s on component %d' % (repr(data), component))

    # print candidate info
    local_candidates = connection.local_candidates
    remote_candidates = connection.remote_candidates

    for candidate in local_candidates:
        logger.info(f'''local info: {candidate.host} 
                    local port: {candidate.port}
                    local type: {candidate.type}
                    local transport: {candidate.transport}
                    local priority: {candidate.priority}
                    local foundation: {candidate.foundation}
                    local component: {candidate.component}
                    ''')

    for candidate in remote_candidates:
        logger.info(f'''remote info: {candidate.host}
                    remote port: {candidate.port}
                    remote type: {candidate.type}
                    remote transport: {candidate.transport}
                    remote priority: {candidate.priority}
                    remote foundation: {candidate.foundation}
                    remote component: {candidate.component}
                    ''')

    await asyncio.sleep(5)
    await connection.close()


# ICE client answer
async def answer(options):
    connection = aioice.Connection(ice_controlling=False,
                                   components=options.components,
                                   stun_server=STUN_SERVER)
    await connection.gather_candidates()

    websocket = await websockets.connect(WEBSOCKET_URI)

    # await offer
    message = json.loads(await websocket.recv())
    print('received offer', message)
    connection.remote_candidates = [aioice.Candidate.from_sdp(c) for c in message['candidates']]
    connection.remote_username = message['username']
    connection.remote_password = message['password']

    # send answer
    await websocket.send(json.dumps({
        'candidates': [c.to_sdp() for c in connection.local_candidates],
        'password': connection.local_password,
        'username': connection.local_username,
    }))

    await websocket.close()

    await connection.connect()
    print('connected')

    # echo data back
    data, component = await connection.recvfrom()
    print('echoing %s on component %d' % (repr(data), component))
    await connection.sendto(data, component)

    # print candidate info
    local_candidates = connection.local_candidates
    remote_candidates = connection.remote_candidates

    for candidate in local_candidates:
        logger.info(f'''local info: {candidate.host} 
                    local port: {candidate.port}
                    local type: {candidate.type}
                    local transport: {candidate.transport}
                    local priority: {candidate.priority}
                    local foundation: {candidate.foundation}
                    local component: {candidate.component}
                    ''')

    for candidate in remote_candidates:
        logger.info(f'''remote info: {candidate.host}
                    remote port: {candidate.port}
                    remote type: {candidate.type}
                    remote transport: {candidate.transport}
                    remote priority: {candidate.priority}
                    remote foundation: {candidate.foundation}
                    remote component: {candidate.component}
                    ''')

    await asyncio.sleep(5)
    await connection.close()


parser = argparse.ArgumentParser(description='ICE tester')
parser.add_argument('action', choices=['offer', 'answer'])
parser.add_argument('--components', type=int, default=1)
options = parser.parse_args()

logging.basicConfig(level=logging.DEBUG)


if options.action == 'offer':
    asyncio.get_event_loop().run_until_complete(offer(options))
else:
    asyncio.get_event_loop().run_until_complete(answer(options))

