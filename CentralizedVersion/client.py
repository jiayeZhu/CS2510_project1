import asyncio
import json
import sys
import getopt


def print_help():
    print("python3 client.py -p <local port> -s <index server address> -i <dir of files you want to share> -o <dir "
          "for downloading files from others>")
    return


port = -1
sharingDir = './sharing'
downloadingDir = './downloading'
requiredOpts = ['-s', '-p']
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hs:p:i:o:')
    print(opts)
except getopt.GetoptError:
    print_help()
for (opt, arg) in opts:
    if opt == '-h':
        print_help()
        sys.exit()
    elif opt == '-p':
        port = int(arg)
    elif opt == '-i':
        sharingDir = arg
    elif opt == '-o':
        downloadingDir = arg



async def tcp_client(message, loop, n):
    if not n == 0:
        await asyncio.sleep(n)
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=loop)

    writer.write(message.encode())

    await writer.drain()
    writer.write_eof()
    data = await reader.read(100)
    print('Received: %r' % data.decode())

    writer.close()


# async def registerAt(serverAddr):


loop = asyncio.get_event_loop()

tasks = [tcp_client(json.dumps({'cmd': 'reg', 'port': 12345, 'files': ["qweqwe123", "adfkyqiuhskjd"]}), loop, 0),
         # tcp_client(json.dumps({'cmd': 'unreg', 'port': 12345}), loop, 8),
         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 2),
         tcp_client(json.dumps({'cmd': 'reg', 'port': 12346, 'files': ["asaw41", "qqweqweqwe"]}), loop, 3),
         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 4),
         tcp_client(json.dumps({'cmd': 'reg', 'port': 12347, 'files': ["qweqwe123", "qqweqweqwe"]}), loop, 4.5),
         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 5),
         tcp_client(json.dumps({'cmd': 'update', 'port': 12345,
                                'diffs': {"add": ['qwghsdfasdfewrqwehagzcv123123'], "delete": ['qweqwe123']}}), loop,
                    5),
         tcp_client(json.dumps({'cmd': 'reg', 'port': 12348, 'files': ["qweqwe123", "adfkyqiuhskjd"]}), loop, 6.5),
         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 7),
         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 9),
         tcp_client(json.dumps({'cmd': 'unreg', 'port': 12346}), loop, 10),
         tcp_client(json.dumps({'cmd': 'unreg', 'port': 12348}), loop, 10),
         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 11)]

loop.run_until_complete(asyncio.wait(tasks))
loop.close()
