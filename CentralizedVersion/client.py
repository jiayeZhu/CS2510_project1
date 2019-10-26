import asyncio
import json
import sys
import getopt
import os
import hashlib
import random
from aiomultiprocess import Worker


port = 0
sharingDir = ''
downloadingDir = ''
serverAddr = ''
serverPort = 0
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

#sub process for nonblocking file reading
async def fileReader(filename,myChunkNumber,totalChunkNumber):
    # print('FILENAME:',filename)
    fileSize = os.stat(filename).st_size
    start = int(fileSize * myChunkNumber/totalChunkNumber)
    end = int(fileSize * (myChunkNumber+1)/totalChunkNumber)
    dataLength = end-start
    f = open(filename,'rb')
    f.seek(start,0)
    chunk = f.read(dataLength)
    f.close()
    return chunk


async def tcp_client(message, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=loop)
    writer.write(message.encode())
    await writer.drain()
    writer.write_eof()
    data = await reader.read()
    writer.close()
    # print('Received: %r' % data.decode())
    return data


async def RequestForFile(filedata,filehash,targetAddress,loop,chunk,total):
    # print("REQUESTFORFILE__HASH:",filehash)
    # print(filedata)
    reader, writer = await asyncio.open_connection(targetAddress.split(':')[0], int(targetAddress.split(':')[1]),
                                                   loop=loop)
    print('connected to:',targetAddress)
    writer.write(json.dumps({'cmd':'get','chunk':chunk,'total':total,'hash':filehash}).encode())
    writer.write_eof()
    await writer.drain()
    data =  await reader.read()

    # print('chunk number:',chunk,' received data lens:',len(data))

    filedata[chunk]=data

    writer.close()



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


 # search
async def searchFiles(filesToFetch):
    loop = asyncio.get_event_loop()
    response = await tcp_client(commandGenerator('search',filesToFetch),loop)
    return json.loads(response.decode())


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
    global sharingDir

    fileName = fileHashToFile[data['hash']]
    fileName = os.path.join(sharingDir,fileName)
    myChunkNumber = data['chunk']
    totalChunkNumber = data['total']
    p = Worker(target=fileReader, args=(fileName, myChunkNumber,totalChunkNumber))
    chunk = await p
    writer.write(chunk)
    writer.write_eof()
    await writer.drain()
    writer.close()
    # writer.write(json.dumps({"result":fileList}).encode())
    # await writer.drain()
    # writer.close()
    return

async def fileWriter(path,data):
    f = open(path,'wb')
    f.write(data)
    f.close()
    return


# file sharing service handler
async def sharingHandler(reader, writer):
    data = await reader.read()  # read socket data
    addr = writer.get_extra_info('peername')  # get peer's ip
    print("Received request from ", addr)  # log request
    data = json.loads(data)  # parse the request to object
    cmd = data['cmd']  # get commond part
    # peer = addr[0] + ':' + str(data['port'])  # create peer address
    if cmd == "get":
        await fileTransferHandler(data, writer)
        return
    

async def main():
    global port
    global sharingDir
    global downloadingDir
    global serverAddr
    global serverPort
    global fileList
    global M
    global N
    global f
    
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
        # print('FAILED TO REGIST AT THE SERVER! STOPED')
        # sys.exit()
        print('!!! ALREADY REGISTERED !!!')

    else:
        print('=== peer registed successfully. ===')

    #start intervally request for files
    while True:
        remoteFileList = await requestRemoteFileList(loop)
        remoteFileList = remoteFileList['result']
        # print(remoteFileList)
        filesToFetch = []
        for i in range(N):
            RFL_length = len(remoteFileList)
            idx = random.randint(0,RFL_length-1)
            filesToFetch.append(remoteFileList[idx])
        # print(filesToFetch)
        peerListsToRequest = await searchFiles(filesToFetch)
        peerListsToRequest = peerListsToRequest['result']

        tasks = []
        files = []
        for i in range(N):
            peerList = peerListsToRequest[i]
            fileHash = hashlib.sha1()
            fileHash.update(filesToFetch[i].encode())
            fileHash = fileHash.hexdigest()
            # print(fileHash)
            files.append([])
            for j in range(len(peerList)):
                files[i].append(b'')
            for j in range(len(peerList)):
                peer = peerList[j]
                tasks.append(RequestForFile(files[i],fileHash,peer,loop,j,len(peerList)))
        all_task = asyncio.wait(tasks)
        await loop.create_task(all_task)
        writerWorkers = []
        for i in range(N):
            _file_ = b''
            for j in range(len(files[i])):
                _file_ += files[i][j]
            files[i] = _file_
            # print(len(files[i]))
            writerWorkers.append(Worker(target=fileWriter, args=(os.path.join(downloadingDir,filesToFetch[i]), files[i])))
        await loop.create_task(asyncio.wait(writerWorkers))
        print('written')
        await asyncio.sleep(f)
    

if __name__ == "__main__":
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
            serverAddr = arg.split(':')[0]
            serverPort = int(arg.split(':')[1])
        elif opt == '-M':
            M = int(arg)
        elif opt == '-N':
            N = int(arg)
        elif opt == '-f':
            f = float(arg)
    if sharingDir=='' or downloadingDir=='' or serverAddr=='' or port * M * N * f * serverPort == 0:
        print_help()
        sys.exit()

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(sharingHandler, '127.0.0.1', port, loop=loop)
    server = loop.run_until_complete(coro)
    print('Start sharing at {}'.format(server.sockets[0].getsockname()))
    loop.create_task(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
