import asyncio
import json
import getopt
import sys
import psutil

fileHashToPeerList = {}
peerToFileHashes = {}
stopAfter = -1

requestRcvCounter = 0
bytesRcvCounter = 0
bytesSndCounter = 0

def print_help():
    print("python3 server.py [options]\n"
          "\t-h show this help\n"
          "\t-T <stop after T seconds>(default=-1 means forever)")
    return


async def regHandler(peer, data, writer):
    global fileHashToPeerList
    global peerToFileHashes
    global bytesSndCounter
    if peer in peerToFileHashes:  # if peer already registered
        writer.write(b'\x00')  # reject using \x00
        await writer.drain()
        writer.close()
        bytesSndCounter += 1
        return

    files = data['files']  # get peer's filehash list
    for f in files:  # add peer to the index
        if f in fileHashToPeerList:  # if other peer has the file
            fileHashToPeerList[f].append(peer)  # append the peer to the peerlist
        else:  # if no one has the file
            fileHashToPeerList[f] = [peer]  # creat a new k-v index entry
    peerToFileHashes[peer] = files
    writer.write(b'\x01')  # response success using \x01
    await writer.drain()
    writer.close()
    bytesSndCounter += 1
    return


async def updateRegHandler(peer, data, writer):
    global fileHashToPeerList
    global peerToFileHashes
    global bytesSndCounter
    if peer not in peerToFileHashes:  # if peer is not registered
        writer.write(b'\x00')  # reject
        await writer.drain()
        writer.close()
        bytesSndCounter += 1
        return

    diffs = data['diffs']  # get the difference
    add = diffs['add']
    delete = diffs['delete']
    for f in add:  # search the add list
        if f in fileHashToPeerList:  # if other peer has the file
            fileHashToPeerList[f].append(peer)  # append the peer to the peerlit
        else:
            fileHashToPeerList[f] = [peer]  # create a new k-v index entry
        peerToFileHashes[peer].append(f)
    for f in delete:
        if f not in fileHashToPeerList:  # if the file wanted to remove is not in the database
            writer.write(b'\x00')  # reject
            await writer.drain()
            writer.close()
            bytesSndCounter += 1
            return
        else:  # else
            fileHashToPeerList[f].remove(peer)  # remove the peer from the peerlist of the file
        peerToFileHashes[peer].remove(f)  # remove the file from the filelist of the peer
    writer.write(b'\x01')  # response success using \x01
    await writer.drain()
    writer.close()
    bytesSndCounter += 1
    return


async def unregHandler(peer, writer):
    global fileHashToPeerList
    global peerToFileHashes
    global bytesSndCounter
    if peer not in peerToFileHashes:  # if peer hasn't registered
        writer.write(b'\x00')  # reject
        await writer.drain()
        writer.close()
        bytesSndCounter += 1
        return
    files = peerToFileHashes[peer]  # find the files store at the peer
    for f in files:
        fileHashToPeerList[f].remove(peer)  # remove the peer from the peerlist in all the file record
        if len(fileHashToPeerList[f]) == 0:  # if there isn't any more peer has the file
            del fileHashToPeerList[f]  # remove the file in file record
    del peerToFileHashes[peer]  # remove the peer in peer record
    writer.write(b'\x01')  # response success
    await writer.drain()
    writer.close()
    bytesSndCounter += 1
    return


async def searchHandler(data, writer):
    global fileHashToPeerList
    global peerToFileHashes
    global bytesSndCounter
    files = data['files']  # get the search list
    result = []  # construct the result list
    for f in files:  # for each file in the search list
        if f in fileHashToPeerList:  # search in the file records
            result.append(fileHashToPeerList[f])  # push available peers list to the result list if found
        else:
            result.append([])  # push empty list to the result list if not found
    response = json.dumps({"result": result}).encode()
    writer.write(response)  # send the result
    await writer.drain()
    writer.close()
    bytesSndCounter += len(response)
    return


async def listAllHandler(writer):
    global fileHashToPeerList
    global peerToFileHashes
    global bytesSndCounter
    fileList = list(fileHashToPeerList.keys())
    response = json.dumps({"result":fileList}).encode()
    writer.write(response)
    await writer.drain()
    writer.close()
    bytesSndCounter += len(response)
    return


async def tcp_handler(reader, writer):
    global requestRcvCounter
    global bytesRcvCounter

    requestRcvCounter += 1  #count new request
    data = await reader.read()  # read socket data
    bytesRcvCounter += len(data)  #count bytes received
    addr = writer.get_extra_info('peername')  # get peer's ip
    print("Received data from ", addr)  # log request
    data = json.loads(data)  # parse the request to object
    cmd = data['cmd']  # get commond part
    peer = addr[0] + ':' + str(data['port'])  # create peer address
    if cmd == "reg":
        await regHandler(peer, data, writer)
        return
    if cmd == "unreg":
        await unregHandler(peer, writer)
        return
    if cmd == "search":
        await searchHandler(data, writer)
        return
    if cmd == "update":
        await updateRegHandler(peer, data, writer)
        return
    if cmd == "ls":
        await listAllHandler(writer)
        return


async def printCache():
    global fileHashToPeerList
    global peerToFileHashes
    while True:
        # print('=' * 10)
        # print('File index:')
        # print(fileHashToPeerList)
        # print('-' * 10)
        # print('peer index:')
        # print(peerToFileHashes)
        await asyncio.sleep(5)


async def shutdownManager():
    global stopAfter
    if stopAfter == -1:
        return
    else:
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        while True:
            timePassed = loop.time() - start_time
            if timePassed >= stopAfter:
                loop.stop()
            await asyncio.sleep(2)

async def systemMetricCollector():
    f = open('systemMetric.csv','w')
    f.write('time,cpuUtilization,memoryUtilization\n')
    loop = asyncio.get_event_loop()
    start_time = loop.time()
    while True:
        cpuUtil = psutil.cpu_percent()
        memUtil = psutil.virtual_memory()[2]
        timePassed = loop.time()-start_time
        f.write(str(timePassed)+','+str(cpuUtil)+','+str(memUtil)+'\n')
        await asyncio.sleep(1)

async def serverMetricCollector():
    global requestRcvCounter 
    global bytesRcvCounter 
    global bytesSndCounter 
    f = open('sererMetric.csv','w')
    f.write('time,requestReceived,bytesReceived,BytedSent\n')
    _rR = requestRcvCounter
    _bR = bytesRcvCounter
    _bS = bytesSndCounter
    loop = asyncio.get_event_loop()
    start_time = loop.time()
    while True:
        timePassed = loop.time()-start_time
        f.write(str(timePassed)+','+str(requestRcvCounter-_rR)+','+str(bytesRcvCounter-_bR)+','+str(bytesSndCounter-_bS)+'\n')
        _rR = requestRcvCounter
        _bR = bytesRcvCounter
        _bS = bytesSndCounter
        await asyncio.sleep(1)


#options parser
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hT:')
    # print(opts)
except getopt.GetoptError:
    print_help()
    sys.exit(2)
for (opt, arg) in opts:
    if opt == '-h':
        print_help()
    elif opt == '-T':
        stopAfter = int(arg)


loop = asyncio.get_event_loop()
coro = asyncio.start_server(tcp_handler, '127.0.0.1', 8888, loop=loop)
server = loop.run_until_complete(coro)
loop.create_task(printCache())
loop.create_task(shutdownManager())
loop.create_task(systemMetricCollector())
loop.create_task(serverMetricCollector())
# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

f = open('server.stat','w')
f.write('========== Server statistical result ==========\n')
f.write('Request received:\t'+str(requestRcvCounter)+'\n')
f.write('Bytes Received:\t\t'+str(bytesRcvCounter)+'\n')
f.write('bytes Send:\t\t'+str(bytesSndCounter)+'\n')
f.close()
# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
