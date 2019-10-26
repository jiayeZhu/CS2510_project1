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
N = 0
f = 0
stopAfter = -1

# requestRcvFromServerCounter = 0
requestSndToServerCounter = 0
requestRcvFromPeersCounter = 0
requestSndToPeersCounter = 0
bytesRcvFromServerCounter = 0
bytesSndToServerCounter = 0
bytesRcvFromPeersCounter = 0
bytesSndToPeersCounter = 0
serverResponseTime = 0
peersResponseTime = 0

def print_help():
    print("python3 client.py [options]\n"
          "\t-h show this help\n"
          "\t-p <local port>\n"
          "\t-s <index server address>\n"
          "\t-i <dir of files you want to share>\n"
          "\t-o <dir for downloading files from others>\n"
          "\t-N <Number of sequential requests>\n"
          "\t-f <request interval in seconds>\n"
          "\t-T <stop after T seconds>(default=-1 means forever)")
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
    global bytesSndToServerCounter
    global bytesRcvFromServerCounter
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=loop)
    writer.write(message.encode())
    bytesSndToServerCounter += len(message.encode())
    await writer.drain()
    writer.write_eof()
    data = await reader.read()
    bytesRcvFromServerCounter += len(data)
    writer.close()
    # print('Received: %r' % data.decode())
    return data


async def RequestForFile(filedata,filehash,targetAddress,loop,chunk,total):
    # print("REQUESTFORFILE__HASH:",filehash)
    # print(filedata)
    global requestSndToPeersCounter
    global bytesSndToPeersCounter
    global bytesRcvFromPeersCounter
    global peersResponseTime
    reader, writer = await asyncio.open_connection(targetAddress.split(':')[0], int(targetAddress.split(':')[1]),
                                                   loop=loop)
    print('connected to:',targetAddress)
    req = json.dumps({'cmd':'get','chunk':chunk,'total':total,'hash':filehash}).encode()
    writer.write(req)
    writer.write_eof()
    requestSndToPeersCounter += 1
    bytesSndToPeersCounter += len(req)
    await writer.drain()
    t_start = loop.time()
    first_chunk = await reader.read(1) #read the \x01 byte fro calculating the response time
    t_stop = loop.time()
    peersResponseTime += (t_stop - t_start)
    data =  await reader.read()
    bytesRcvFromPeersCounter += len(data)

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
    global bytesSndToPeersCounter

    fileName = fileHashToFile[data['hash']]
    fileName = os.path.join(sharingDir,fileName)
    myChunkNumber = data['chunk']
    totalChunkNumber = data['total']
    p = Worker(target=fileReader, args=(fileName, myChunkNumber,totalChunkNumber))
    chunk = await p
    writer.write(b'\x01')    #add one byte at head for calculating response time
    writer.write(chunk)
    writer.write_eof()
    await writer.drain()
    writer.close()
    bytesSndToPeersCounter += len(chunk)
    return

async def fileWriter(path,data):
    f = open(path,'wb')
    f.write(data)
    f.close()
    return


# file sharing service handler
async def sharingHandler(reader, writer):
    global requestRcvFromPeersCounter
    global bytesRcvFromPeersCounter
    data = await reader.read()  # read socket data
    requestRcvFromPeersCounter += 1
    bytesRcvFromPeersCounter += len(data)
    addr = writer.get_extra_info('peername')  # get peer's ip
    print("Received request from ", addr)  # log request
    data = json.loads(data)  # parse the request to object
    cmd = data['cmd']  # get commond part
    if cmd == "get":
        await fileTransferHandler(data, writer)
        return

async def shutdownManager():
    global stopAfter
    if stopAfter == -1:
        return
    else:
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        while True:
            timePassed = loop.time() - start_time
            print(timePassed)
            if timePassed >= stopAfter:
                loop.stop()
            await asyncio.sleep(2) 

async def main():
    global port
    global sharingDir
    global downloadingDir
    global serverAddr
    global serverPort
    global fileList
    global N
    global f
    global requestSndToServerCounter
    global serverResponseTime

    #setup fileListCache
    fileList = scanFiles(sharingDir)  #get the list of files for sharing
    for filename in fileList:
        hash = hashlib.sha1()
        hash.update(filename.encode())
        hash = hash.hexdigest()
        fileHashToFile[hash] = filename  #create hash mapping to filenames
    # print(list(fileHashToFile.keys()))
    loop = asyncio.get_event_loop()
    t_start = loop.time()
    connected = await regist(loop)
    t_stop = loop.time()
    serverResponseTime += (t_stop - t_start)
    requestSndToServerCounter += 1
    if not connected:
        print('FAILED TO REGIST AT THE SERVER! STOPED')
        sys.exit()
        # print('!!! ALREADY REGISTERED !!!')

    else:
        print('=== peer registed successfully. ===')

    #start intervally request for files
    while True:
        t_loopstart = loop.time()
        t_start = loop.time()
        remoteFileList = await requestRemoteFileList(loop)
        t_stop = loop.time()
        serverResponseTime += (t_stop - t_start)
        requestSndToServerCounter += 1
        remoteFileList = remoteFileList['result']
        # print(remoteFileList)
        filesToFetch = []
        for i in range(N):
            RFL_length = len(remoteFileList)
            idx = random.randint(0,RFL_length-1)
            filesToFetch.append(remoteFileList[idx])
        # print(filesToFetch)
        t_start = loop.time()
        peerListsToRequest = await searchFiles(filesToFetch)
        t_stop = loop.time()
        serverResponseTime += (t_stop - t_start)
        requestSndToServerCounter += 1
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
                requestSndToServerCounter += 1
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
        if f - (loop.time()-t_loopstart) > 0:
            await asyncio.sleep(f - (loop.time()-t_loopstart))
    

if __name__ == "__main__":
    #options parser
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:p:i:o:N:f:T:')
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
        elif opt == '-N':
            N = int(arg)
        elif opt == '-f':
            f = float(arg)
        elif opt == '-T':
            stopAfter = int(arg)
    if sharingDir=='' or downloadingDir=='' or serverAddr=='' or port  * N * f * serverPort == 0:
        print_help()
        sys.exit()

    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(sharingHandler, '127.0.0.1', port, loop=loop)
    server = loop.run_until_complete(coro)
    print('Start sharing at {}'.format(server.sockets[0].getsockname()))
    loop.create_task(main())
    loop.create_task(shutdownManager())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('client out')
        pass
    statName = hashlib.md5()
    statName.update(str(random.random()).encode())
    statName = statName.hexdigest()
    statFileName = 'client_'+statName+'.stat'
    f = open(statFileName,'w')
    f.write('========== Client statistical result ==========\n')
    f.write('Request sent to server:\t\t'+str(requestSndToServerCounter)+'\n')
    f.write('Request received from server:\t'+str(requestRcvFromPeersCounter)+'\n')
    f.write('Request sent to peers:\t\t'+str(requestSndToPeersCounter)+'\n')
    f.write('Bytes received from server:\t'+str(bytesRcvFromServerCounter)+'\n')
    f.write('Bytes sent to server:\t\t'+str(bytesSndToServerCounter)+'\n')
    f.write('Bytes received from peers:\t'+str(bytesRcvFromPeersCounter)+'\n')
    f.write('Bytes sent to peers:\t\t'+str(bytesSndToPeersCounter)+'\n')
    f.write('Avg. peer response time:\t'+str(peersResponseTime/requestSndToPeersCounter)+'\n')
    f.write('Avg. server response time:\t'+ str(serverResponseTime/requestSndToServerCounter)+'\n')
    f.close()
    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
