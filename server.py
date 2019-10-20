import asyncio
import json


fileHashToPeerList = {}
peerToFileHashes = {}

async def regHandler(peer,data,writer):
    global fileHashToPeerList
    global peerToFileHashes
    if peer in peerToFileHashes:                    #if peer already registered
        writer.write(b'\x00')                       #reject using \x00
        await writer.drain()
        writer.close()
        return 

    files = data['files']                           #get peer's filehash list
    for f in files:                                 #add peer to the index
        if f in fileHashToPeerList:                 #if other peer has the file
            fileHashToPeerList[f].append(peer)      #append the peer to the peerlist
        else:                                       #if no one has the file
            fileHashToPeerList[f]=[peer]            #creat a new k-v index entry
    peerToFileHashes[peer]=files
    writer.write(b'\x01')                           #response success using \x01
    await writer.drain()
    writer.close()
    return

async def unregHandler(peer,writer):
    global fileHashToPeerList
    global peerToFileHashes
    if peer not in peerToFileHashes:                #if peer hasn't registered
        writer.write(b'\x00')                       #reject
        await writer.drain()
        writer.close()
        return
    files = peerToFileHashes[peer]                  #find the files store at the peer
    for f in files:
        fileHashToPeerList[f].remove(peer)          #remove the peer from the peerlist in all the file record
        if len(fileHashToPeerList[f]) == 0:         #if there isn't any more peer has the file
            del fileHashToPeerList[f]               #remove the file in file record
    del peerToFileHashes[peer]                      #remove the peer in peer record
    writer.write(b'\x01')                           #response success
    await writer.drain()
    writer.close()
    return

async def searchHandler(data,writer):
    global fileHashToPeerList
    global peerToFileHashes
    files = data['files']                                   #get the search list
    result = []                                             #construct the result list
    for f in files:                                         #for each file in the search list
        if f in fileHashToPeerList:                         #search in the file records
            result.append(fileHashToPeerList[f])            #push available peers list to the result list if found
        else:
            result.append([])                               #push empty list to the result list if not found
    writer.write(json.dumps({"result":result}).encode())    #send the result
    await writer.drain()
    writer.close()
    return

async def tcp_handler(reader, writer):
    data = await reader.read()                          #read socket data
    addr = writer.get_extra_info('peername')            #get peer's ip
    print("Received data from " ,addr)                  #log request
    data = json.loads(data)                             #parse the request to object
    cmd = data['cmd']                                   #get commond part
    if cmd == "reg":                                    #if commond = register
        peer = addr[0]+':'+str(data['port'])            #create peer address
        await regHandler(peer,data,writer)
        return
    if cmd == "unreg":
        peer = addr[0]+':'+str(data['port'])            #create peer address
        await unregHandler(peer,writer)
        return
    if cmd == "search":
        await searchHandler(data,writer)
        return        

async def printCache():
    global fileHashToPeerList
    global peerToFileHashes
    while True:
        print('='*10)
        print('File index:')
        print(fileHashToPeerList)
        print('-'*10)
        print('peer index:')
        print(peerToFileHashes)
        await asyncio.sleep(5)


loop = asyncio.get_event_loop()
coro = asyncio.start_server(tcp_handler, '127.0.0.1', 8888, loop=loop)
server = loop.run_until_complete(coro)
loop.create_task(printCache())
# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()