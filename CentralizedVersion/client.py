import asyncio
import json
import sys
import getopt
import os
import hashlib


port = 0
sharingDir = ''
downloadingDir = ''
serverAddr = ''
fileHashToFile = {}
fileList = []
M = 0
N = 0
f = 0


def print_help():
    print("python3 client.py [options]\n"
          "\t-p <local port>\n"
          "\t-s <index server address>\n"
          "\t-i <dir of files you want to share>\n"
          "\t-o <dir for downloading files from others>\n"
          "\t-M <number of files to share>\n"
          "\t-N <Number of sequential requests>\n"
          "\t-F <request interval in seconds>\n")
    return


def commandGenerator(tp,files=[],diffs={}):
    global port
    command = {'cmd':tp,'port':port}
    if tp == 'reg':
        command['files'] = files
    elif tp == 'update':
        command['diffs'] = diffs
    elif tp == 'search':
        command['files'] = files
    if tp not in ['reg','update','unreg','search','ls']:
        raise Exception('Wrong command')
    # print(command)
    return json.dumps(command)


def scanFiles(directory):
    fList = os.listdir(directory)
    return fList


async def tcp_client(message, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=loop)
    writer.write(message.encode())
    await writer.drain()
    writer.write_eof()
    data = await reader.read()
    writer.close()
    # print('Received: %r' % data.decode())
    return data

    
# regist
async def regist(loop):
    global fileList
    response = await tcp_client(commandGenerator('reg',fileList),loop)
    if response == b'\x00':
        return False
    elif response == b'\x01':
        return True
    else :
        errmsg='register failed with unexpected response:'+response.decode()
        raise Exception(errmsg)
    

# request for remote file list
async def requestRemoteFileList(loop):
    response = await tcp_client(commandGenerator('ls'),loop)
    if response == b'\x00':
        return False
    else:
        return json.loads(response.decode())


# file transfer handler
async def fileTransferHandler(data,writer):
    global fileHashToFile
    # fileList = list(fileHashToFile.keys())
    fetchList = data['fetchList']
    for f in fetchList:
        fileName = fileHashToFile[f['hash']]
        start = f['start']
        end = f['end']

    # writer.write(json.dumps({"result":fileList}).encode())
    # await writer.drain()
    # writer.close()
    return


# file sharing service handler
async def sharingHandler(reader, writer):
    data = await reader.read()  # read socket data
    addr = writer.get_extra_info('peername')  # get peer's ip
    print("Received data from ", addr)  # log request
    data = json.loads(data)  # parse the request to object
    cmd = data['cmd']  # get commond part
    # peer = addr[0] + ':' + str(data['port'])  # create peer address
    if cmd == "get":
        await regHandler(peer, data, writer)
        return
    

async def main():
    global port
    global sharingDir
    global downloadingDir
    global serverAddr
    global fileList
    global M
    global N
    global f
    #options parser
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:p:i:o:M:N:f:')
        # print(opts)
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
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
        elif opt == '-s':
            serverAddr = arg
        elif opt == '-M':
            M = int(arg)
        elif opt == '-N':
            N = int(arg)
        elif opt == '-f':
            f = float(arg)
    if sharingDir=='' or downloadingDir=='' or serverAddr=='' or port * M * N * f == 0:
        print_help()
        sys.exit()
        return
    #setup fileListCache
    fileList = scanFiles(sharingDir)  #get the list of files for sharing
    for filename in fileList:
        hash = hashlib.sha1()
        hash.update(filename.encode())
        hash = hash.hexdigest()
        fileHashToFile[hash] = filename  #create hash mapping to filenames
    # print(list(fileHashToFile.keys()))
    loop = asyncio.get_event_loop()
    connected = await regist(loop)
    if not connected:
        print('FAILED TO REGIST AT THE SERVER! STOPED')
        sys.exit()
    else:
        print('=== peer registed successfully. ===')
    remoteFileList = await requestRemoteFileList(loop)
    print(remoteFileList)
    

    # tasks = [tcp_client(json.dumps({'cmd': 'reg', 'port': 12345, 'files': ["qweqwe123", "adfkyqiuhskjd"]}), loop, 0),
    #         # tcp_client(json.dumps({'cmd': 'unreg', 'port': 12345}), loop, 8),
    #         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 2),
    #         tcp_client(json.dumps({'cmd': 'reg', 'port': 12346, 'files': ["asaw41", "qqweqweqwe"]}), loop, 3),
    #         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 4),
    #         tcp_client(json.dumps({'cmd': 'reg', 'port': 12347, 'files': ["qweqwe123", "qqweqweqwe"]}), loop, 4.5),
    #         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 5),
    #         tcp_client(json.dumps({'cmd': 'update', 'port': 12345,'diffs': {"add": ['qwghsdfasdfewrqwehagzcv123123'], "delete": ['qweqwe123']}}), loop,5),
    #         tcp_client(json.dumps({'cmd': 'reg', 'port': 12348, 'files': ["qweqwe123", "adfkyqiuhskjd"]}), loop, 6.5),
    #         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 7),
    #         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 9),
    #         tcp_client(json.dumps({'cmd': 'unreg', 'port': 12346}), loop, 10),
    #         tcp_client(json.dumps({'cmd': 'unreg', 'port': 12348}), loop, 10),
    #         tcp_client(json.dumps({'cmd': 'search', 'port': 12348, 'files': ["asaw41", "adfkyqiuhskjd"]}), loop, 11)]

    # loop.run_until_complete(asyncio.wait(tasks))
    # loop.close()


if __name__ == "__main__":
    asyncio.run(main())