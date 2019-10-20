import asyncio
import json

async def tcp_echo_client(message, loop, n):
    if not n == 0:
        await asyncio.sleep(n)
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=loop)

    writer.write(message.encode())

    await writer.drain()
    writer.write_eof()
    data = await reader.read(100)
    print('Received: %r' % data.decode())

    writer.close()

loop = asyncio.get_event_loop()

tasks=[]

tasks.append(tcp_echo_client(json.dumps({'cmd':'reg','port':12345,'files':["qweqwe123","adfkyqiuhskjd"]}),loop,0))
tasks.append(tcp_echo_client(json.dumps({'cmd':'unreg','port':12345}),loop,8))
tasks.append(tcp_echo_client(json.dumps({'cmd':'search','files':["asaw41","adfkyqiuhskjd"]}),loop,2))
tasks.append(tcp_echo_client(json.dumps({'cmd':'reg','port':12346,'files':["asaw41","qqweqweqwe"]}),loop,3))
tasks.append(tcp_echo_client(json.dumps({'cmd':'search','files':["asaw41","adfkyqiuhskjd"]}),loop,4))
tasks.append(tcp_echo_client(json.dumps({'cmd':'reg','port':12347,'files':["qweqwe123","qqweqweqwe"]}),loop,4.5))
tasks.append(tcp_echo_client(json.dumps({'cmd':'search','files':["asaw41","adfkyqiuhskjd"]}),loop,5))
tasks.append(tcp_echo_client(json.dumps({'cmd':'reg','port':12348,'files':["qweqwe123","adfkyqiuhskjd"]}),loop,6.5))
tasks.append(tcp_echo_client(json.dumps({'cmd':'search','files':["asaw41","adfkyqiuhskjd"]}),loop,7))
tasks.append(tcp_echo_client(json.dumps({'cmd':'search','files':["asaw41","adfkyqiuhskjd"]}),loop,9))
tasks.append(tcp_echo_client(json.dumps({'cmd':'unreg','port':12346}),loop,10))
tasks.append(tcp_echo_client(json.dumps({'cmd':'unreg','port':12348}),loop,10))
tasks.append(tcp_echo_client(json.dumps({'cmd':'search','files':["asaw41","adfkyqiuhskjd"]}),loop,11))
loop.run_until_complete(asyncio.wait(tasks))
loop.close()