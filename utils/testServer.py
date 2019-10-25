import asyncio
import json
import os
from aiomultiprocess import Worker


async def fileReader(msg):
    print('==='*10)
    msg = json.loads(msg.decode())
    print(msg)
    myChunkNumber = msg['chunk']
    totalChunkNumber = msg['total']
    filename = msg['filename']

    fileSize = os.stat(filename).st_size
    print('---'*10)
    print(fileSize)

    start = int(fileSize * myChunkNumber/totalChunkNumber)
    end = int(fileSize * (myChunkNumber+1)/totalChunkNumber)
    dataLength = end-start
    print('***'*10)
    f = open(filename,'rb')
    f.seek(start,0)
    chunk = f.read(dataLength)
    f.close()
    return chunk

async def handle_echo(reader, writer):
    addr = writer.get_extra_info('peername')
    print("Received data from ", addr)
    data = await reader.read()
    # message = data.decode()
    
    # print("Received %r from %r" % (message, addr))
    print("Received data size %f from %r" % (len(data), addr))
    

    p = Worker(target=fileReader, args=(data,))
    chunk = await p
    writer.write(chunk)
    writer.write_eof()
    await writer.drain()
    writer.close()
    return

# async def main():
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_echo, '127.0.0.1', 8888, loop=loop)
    server = loop.run_until_complete(coro)

    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

# asyncio.run(main())