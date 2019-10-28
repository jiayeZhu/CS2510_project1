import asyncio
import json
import sys
import getopt
import os
import hashlib
import random

localIp = '127.0.0.1'
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
pre = None
suc = None
localAddress=''
isSmallest = False
isBiggest = False
filesInDownloading = []

statName = hashlib.md5()
statName.update(str(random.random()).encode())
statName = statName.hexdigest()

requestRcvFromPeersCounter = 0
requestSndToPeersCounter = 0
bytesRcvFromPeersCounter = 0
bytesSndToPeersCounter = 0
peersResponseTime = 0

def print_help():
    print("python3 client.py [options]\n"
          "\t-h show this help\n"
          "\t-l <local ip>(default 127.0.0.1)\n"
          "\t-p <local port>\n"
          "\t-s <one available peer address>\n"
          "\t-i <dir of files you want to share>\n"
          "\t-o <dir for downloading files from others>\n"
          "\t-N <Number of sequential requests>\n"
          "\t-f <request interval in seconds>\n"
          "\t-T <stop after T seconds>(default=-1 means forever)")
    return

# def commandGenerator(tp,files=[],diffs={}):
#     global port
#     command = {'cmd':tp,'port':port}
#     if tp == 'reg':
#         command['files'] = files
#     elif tp == 'update':
#         command['diffs'] = diffs
#     elif tp == 'search':
#         command['files'] = files
#     if tp not in ['reg','update','unreg','search','ls']:
#         raise Exception('Wrong command')
#     # print(command)
#     return json.dumps(command)


def scanFiles(directory):
    fList = os.listdir(directory)
    return fList

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

#TODO: 没做peer resposne time机算
async def tcp_client(peerAddress,message):
    global bytesSndToPeersCounter
    global bytesRcvFromPeersCounter
    loop = asyncio.get_event_loop()
    reader, writer = await asyncio.open_connection(peerAddress.split(':')[0],peerAddress.split(':')[1], loop=loop)
    writer.write(message.encode())
    bytesSndToPeersCounter += len(message.encode())
    writer.write_eof()
    await writer.drain()
    #TODO: 要等消息吗？？
    # data = await reader.read()
    # bytesRcvFromPeersCounter += len(data)
    writer.close()
    # print('Received: %r' % data.decode())
    # return data
    return


async def RequestForFile(filedata,fileName,targetAddress,chunk,total):
    global requestSndToPeersCounter
    global bytesSndToPeersCounter
    global bytesRcvFromPeersCounter
    global peersResponseTime

    loop = asyncio.get_event_loop()
    reader, writer = await asyncio.open_connection(targetAddress.split(':')[0], int(targetAddress.split(':')[1]),
                                                   loop=loop)
    print('connected to:',targetAddress,' for downloading file')
    req = json.dumps({'cmd':'get','chunk':chunk,'total':total,'file':fileName}).encode()
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

#DONE
def getHashPos(content):
    # print('getHashPos:',content)
    h = hashlib.sha1()
    h.update(content.encode())
    pos = int.from_bytes(h.digest(),'big')
    return pos

def checkSmallestOrBiggest():
    global isSmallest
    global isBiggest
    global pre
    global suc
    global localAddress

    if getHashPos(suc) < getHashPos(localAddress):
        isBiggest = True
    elif getHashPos(pre) > getHashPos(localAddress):
        isSmallest = True
    else:
        isSmallest = False
        isBiggest = False

#DONE
async def joinHandler(peerAddress):
    global suc
    global pre
    global localIp
    global port
    global localAddress
    global isSmallest
    global isBiggest
    
    if suc == None and pre == None:  # this is the case that I'm the only node for now
        suc = peerAddress
        pre = peerAddress
        await tcp_client(peerAddress,json.dumps({'cmd':'SETPOS','suc':localAddress, 'pre':localAddress}))
        # await fileSync()
        return
    else:  # as long as there are two nodes or more, it's this case
        preHash = getHashPos(pre)
        localHash = getHashPos(localAddress)
        sucHash = getHashPos(suc)
        PeerHash = getHashPos(peerAddress)
        if not isSmallest and not isBiggest:
            if PeerHash > sucHash:
                await tcp_client(suc,json.dumps({'cmd':'join','sourcePeer':peerAddress}))
                return
            elif PeerHash < sucHash and PeerHash > localHash:
                await tcp_client(peerAddress,json.dumps({'cmd':'SETPOS','suc':suc,'pre':localAddress}))
                await tcp_client(suc,json.dumps({'cmd':'SETPRE','pre':peerAddress}))
                suc = peerAddress
                return
            elif PeerHash < localHash and PeerHash > preHash:
                await tcp_client(peerAddress,json.dumps({'cmd':'SETPOS','suc':localAddress,'pre':pre}))
                await tcp_client(pre,json.dumps({'cmd':'SETSUC','suc':peerAddress}))
                pre = peerAddress
                return
            else:
                await tcp_client(pre,json.dumps({'cmd':'join','sourcePeer':peerAddress})) 
                return
        elif isSmallest:
            await tcp_client(peerAddress,json.dumps({'cmd':'SETPOS','suc':localAddress,'pre':pre}))
            await tcp_client(pre,json.dumps({'cmd':'SETSUC','suc':peerAddress}))
            pre = peerAddress
            return
        elif isBiggest:
            await tcp_client(peerAddress,json.dumps({'cmd':'SETPOS','suc':suc,'pre':localAddress}))
            await tcp_client(suc,json.dumps({'cmd':'SETPRE','pre':peerAddress}))
            suc = peerAddress
            return

#send sync message to the target peers
async def fileSync():
    global sharingDir
    global localAddress
    global pre
    global suc
    global port

    preHash = getHashPos(pre)
    localHash = getHashPos(localAddress)
    sucHash = getHashPos(suc)


    filesIHave = scanFiles(sharingDir)
    for f in filesIHave:
        f_hash = getHashPos(f)
        # if not isSmallest and not isBiggest:
        if f_hash > localHash:
            await tcp_client(suc,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':f,'port':port}))
        elif f_hash < localHash:
            await tcp_client(pre,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':f,'port':port}))


#list all files
async def LS(fList):
    global sharingDir
    global localAddress
    global pre
    global suc
    global port
    global fileList

    preHash = getHashPos(pre)
    localHash = getHashPos(localAddress)
    sucHash = getHashPos(suc)

    fSet = set(fList)
    filesIHave = scanFiles(sharingDir)
    fSet.update(filesIHave)
    fileList = list(fSet)
    await tcp_client(suc,json.dumps({'cmd':'LS','sourcePeer':localAddress,'fileList':fileList,'port':port}))


async def fileSyncHandler(peerAddress,fileName,msgFrom):
    global sharingDir
    global localAddress
    global pre
    global suc
    global filesInDownloading

    preHash = getHashPos(pre)
    localHash = getHashPos(localAddress)
    sucHash = getHashPos(suc)
    filesIHave = scanFiles(sharingDir)
    
    f_hash = getHashPos(fileName)
    if not isSmallest and not isBiggest:
        if f_hash < preHash :  #msg must come from successor
            await tcp_client(pre,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':fileName,'port':port}))
            return
        elif f_hash > preHash and f_hash < localHash:
            if not msgFrom == pre:
                await tcp_client(pre,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':fileName,'port':port}))
            if fileName not in filesIHave and fileName not in filesInDownloading:
                filesInDownloading.append(fileName)
                fileData = [b'']
                await RequestForFile(fileData,fileName,peerAddress,0,1)
                await fileWriter(os.path.join(sharingDir,fileName),fileData[0])
                filesInDownloading.remove(fileName)
            return
        elif f_hash > localHash and f_hash < sucHash:
            if not msgFrom == suc:
                await tcp_client(suc,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':fileName,'port':port}))
            if fileName not in filesIHave and fileName not in filesInDownloading:
                filesInDownloading.append(fileName)
                fileData = [b'']
                await RequestForFile(fileData,fileName,peerAddress,0,1)
                await fileWriter(os.path.join(sharingDir,fileName),fileData[0])
                filesInDownloading.remove(fileName)
            return
        elif f_hash > sucHash:
            await tcp_client(suc,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':fileName,'port':port}))
            return
    elif isSmallest:
        if f_hash < sucHash:  #must come from successor
            if f_hash < localHash:
                await tcp_client(pre,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':fileName,'port':port}))
            if fileName not in filesIHave and fileName not in filesInDownloading:
                filesInDownloading.append(fileName)
                fileData = [b'']
                await RequestForFile(fileData,fileName,peerAddress,0,1)
                await fileWriter(os.path.join(sharingDir,fileName),fileData[0])
                filesInDownloading.remove(fileName)
            return
        elif f_hash > preHash: # must come from predecessor
            if fileName not in filesIHave and fileName not in filesInDownloading:
                filesInDownloading.append(fileName)
                fileData = [b'']
                await RequestForFile(fileData,fileName,peerAddress,0,1)
                await fileWriter(os.path.join(sharingDir,fileName),fileData[0])
                filesInDownloading.remove(fileName)
            return
    elif isBiggest:
        if f_hash > preHash:  #must come from predecessor
            if f_hash > localHash:
                await tcp_client(suc,json.dumps({'cmd':'sync','sourcePeer':localAddress,'file':fileName,'port':port}))
            if fileName not in filesIHave and fileName not in filesInDownloading:
                filesInDownloading.append(fileName)
                fileData = [b'']
                await RequestForFile(fileData,fileName,peerAddress,0,1)
                await fileWriter(os.path.join(sharingDir,fileName),fileData[0])
                filesInDownloading.remove(fileName)
            return
        elif f_hash < sucHash: # must come from successor
            if fileName not in filesIHave and fileName not in filesInDownloading:
                filesInDownloading.append(fileName)
                fileData = [b'']
                await RequestForFile(fileData,fileName,peerAddress,0,1)
                await fileWriter(os.path.join(sharingDir,fileName),fileData[0])
                filesInDownloading.remove(fileName)
            return

#TODO: search file
async def search(filehash):
    pass

# file transfer handler
async def fileTransferHandler(data,writer):
    global fileHashToFile
    global sharingDir
    global bytesSndToPeersCounter

    fileName = data['file']
    fileName = os.path.join(sharingDir,fileName)
    myChunkNumber = data['chunk']
    totalChunkNumber = data['total']
    chunk = await fileReader(fileName, myChunkNumber,totalChunkNumber)
    # chunk = await p
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
            # print(timePassed)
            if timePassed >= stopAfter:
                loop.stop()
            await asyncio.sleep(2) 

async def clientMetricCollector():
    # global requestSndToServerCounter
    global requestRcvFromPeersCounter
    global requestSndToPeersCounter
    # global bytesRcvFromServerCounter
    # global bytesSndToServerCounter
    global bytesRcvFromPeersCounter
    global bytesSndToPeersCounter
    # global serverResponseTime
    global peersResponseTime 
    f = open('client_'+statName+'_metric.csv','w')
    f.write('Time,RequestReceivedFromPeers,RequestSentToPeers,BytesReceivedFromPeer,BytesSentToPeer,PeersResponseTime\n')
    # _rSTS = requestSndToServerCounter
    _rRFP = requestRcvFromPeersCounter
    _rSTP = requestSndToPeersCounter
    # _bRFS = bytesRcvFromServerCounter
    # _bSTS = bytesSndToServerCounter
    _bRFP = bytesRcvFromPeersCounter
    _bSTP = bytesSndToPeersCounter
    # _sRT = serverResponseTime
    _pRT = peersResponseTime
    loop = asyncio.get_event_loop()
    start_time = loop.time()
    while True:
        timePassed = loop.time()-start_time
        # new_rSTS = requestSndToServerCounter - _rSTS
        new_rRFP = requestRcvFromPeersCounter - _rRFP
        new_rSTP = requestSndToPeersCounter - _rSTP
        # new_bRFS = bytesRcvFromServerCounter - _bRFS
        # new_bSTS = bytesSndToServerCounter - _bSTS
        new_bRFP = bytesRcvFromPeersCounter - _bRFP
        new_bSTP = bytesSndToPeersCounter - _bSTP
        # new_sRT = serverResponseTime - _sRT
        new_pRT = peersResponseTime - _pRT
        # realSRT = 0 if new_rSTS == 0 else new_sRT/new_rSTS
        realPRT = 0 if new_rSTP == 0 else new_pRT/new_rSTP
        f.write('{},{},{},{},{},{}\n'.format(timePassed,new_rRFP,new_rSTP,new_bRFP,new_bSTP,realPRT))
        # _rSTS = requestSndToServerCounter
        _rRFP = requestRcvFromPeersCounter
        _rSTP = requestSndToPeersCounter
        # _bRFS = bytesRcvFromServerCounter
        # _bSTS = bytesSndToServerCounter
        _bRFP = bytesRcvFromPeersCounter
        _bSTP = bytesSndToPeersCounter
        # _sRT = serverResponseTime
        _pRT = peersResponseTime
        await asyncio.sleep(5)

#TODO: finish it
async def main():
    global port
    global sharingDir
    global downloadingDir
    global serverAddr
    global serverPort
    global fileList
    global N
    global f
    global suc
    global pre
    global localAddress

    isFirstNode = False

    #step1 join
    if not serverAddr == '':
        print('try to join using node:{}:{}'.format(serverAddr,serverPort))
        await tcp_client('{}:{}'.format(serverAddr,serverPort),json.dumps({'cmd':'join','port':port}))
    while pre == None or suc == None:
        print('waiting peers...')
        isFirstNode = True
        await asyncio.sleep(1)
    checkSmallestOrBiggest()
    # print('finish join')
    #step2 file syncing
    print(localAddress)
    if isFirstNode:
        fileList = scanFiles(sharingDir) if len(fileList)==0 else fileList
        await LS(fileList)
    await tcp_client(suc,json.dumps({'cmd':'NEEDSYNC','sourcePeer':localAddress}))
    print('syncing')
    #ready for sharing
    last_suc = suc
    last_pre = pre
    while True:
        # if (not pre == last_pre) or (not suc == last_suc):
        # print('suc: {}, pre: {}, localAddress: {}, local Hash:{}'.format(suc,pre,localAddress,getHashPos(localAddress)))
            # last_suc = suc
            # last_pre = pre
        await asyncio.sleep(1)


# main server router
async def peerHandler(reader,writer):
    global requestRcvFromPeersCounter
    global bytesRcvFromPeersCounter
    global suc
    global pre
    global localAddress

    requestRcvFromPeersCounter += 1  #count new request
    data = await reader.read()  # read socket data
    bytesRcvFromPeersCounter += len(data)  #count bytes received
    addr = writer.get_extra_info('peername')  # get peer's ip
    # print("Received data from ", addr)  # log request
    data = json.loads(data)  # parse the request to object
    cmd = data['cmd']  # get commond part
    if cmd == "join":
        peer = ''
        if 'sourcePeer' in data.keys():
            peer = data['sourcePeer']
        else:
            peer = addr[0] + ':' + str(data['port'])  # create peer address
        await joinHandler(peer)
        return
    if cmd == "SETPOS":
        suc = data['suc']
        pre = data['pre']
        checkSmallestOrBiggest()
        return
    if cmd == 'SETPRE':
        pre = data['pre']
        checkSmallestOrBiggest()
        return
    if cmd == 'SETSUC':
        suc = data['suc']
        checkSmallestOrBiggest()
        return
    if cmd == 'sync':
        peer = ''
        if 'sourcePeer' in data.keys():
            peer = data['sourcePeer']
        else:
            peer = addr[0] + ':' + str(data['port'])  # create peer address
        await fileSyncHandler(peer,data['file'],addr[0] + ':' + str(data['port']))
        return
    if cmd == 'NEEDSYNC':
        peer = ''
        if 'sourcePeer' in data.keys():
            peer = data['sourcePeer']
        else:
            peer = addr[0] + ':' + str(data['port'])  # create peer address
        if not peer == localAddress:
            await tcp_client(suc,json.dumps(data))
            await fileSync()
        return
    if cmd == 'LS':
        if isSmallest:
            await asyncio.sleep(2)
        fList = data['fileList']
        await LS(fList)
        return
    if cmd == "get":
        await fileTransferHandler(data, writer)
        return
    # if cmd == "unreg":
    #     await unregHandler(peer, writer)
    #     return
    # if cmd == "search":
    #     await searchHandler(data, writer)
    #     return
    # if cmd == "update":
    #     await updateRegHandler(peer, data, writer)
    #     return
    # if cmd == "ls":
    #     await listAllHandler(writer)
    #     return


async def lsManager():
    global fileList

    while True:
        print('Current file list:',fileList)
        await asyncio.sleep(2)


if __name__ == "__main__":
    #options parser
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:p:i:o:N:f:T:l:')
        # print(opts)
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    for (opt, arg) in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt == '-l':
            localIp = arg
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
    if sharingDir=='' or downloadingDir=='' or port  * N * f == 0:
        print_help()
        sys.exit()
    localAddress = '{}:{}'.format(localIp,port)
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(peerHandler, localIp, port, loop=loop)
    server = loop.run_until_complete(coro)
    print('Start sharing at {}'.format(server.sockets[0].getsockname()))
    loop.create_task(main())
    loop.create_task(shutdownManager())
    # loop.create_task(lsManager())
    # loop.create_task(clientMetricCollector())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('client out')
        pass
    # statFileName = 'Node_'+statName+'.stat'
    # f = open(statFileName,'w')
    # f.write('========== Client statistical result ==========\n')
    # f.write('Request received from server:\t'+str(requestRcvFromPeersCounter)+'\n')
    # f.write('Request sent to peers:\t\t'+str(requestSndToPeersCounter)+'\n')
    # f.write('Bytes received from peers:\t'+str(bytesRcvFromPeersCounter)+'\n')
    # f.write('Bytes sent to peers:\t\t'+str(bytesSndToPeersCounter)+'\n')
    # f.write('Avg. peer response time:\t'+str(peersResponseTime/requestSndToPeersCounter)+'\n')
    # f.close()
    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
