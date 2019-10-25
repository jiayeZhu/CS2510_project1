import asyncio
import json

picdata = [b'',b'']
async def tcp_echo_client(loop,chunk,total):
    global picdata
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888,
                                                   loop=loop)
    # print('Sender no.',n,'started')
    # print('Send: %r' % message)
    # writer.write(message.encode())
    print('connected')
    writer.write(json.dumps({'chunk':chunk,'total':total}).encode())
    writer.write_eof()
    await writer.drain()
    print('client written')
    data =  await reader.read()

    print('received data lens:',len(data))

    picdata[chunk]=data

    # await writer.drain()
    # writer.write_eof()
    # data = await reader.read(100)
    # print('Received: %r' % data.decode())

    # print('Close the socket')
    writer.close()
    # print('Senter no.',n,'stoped')


# message = 'Hello World!'
loop = asyncio.get_event_loop()
# f = open('testpic.jpg','rb')
# message = f.read()
tasks=[]
total = 2
for i in range(total):
    tasks.append(tcp_echo_client(loop,i,total))

loop.run_until_complete(asyncio.wait(tasks))
loop.close()

pic = picdata[0]+picdata[1]
# print(pic)
f = open('lalala.jpg','wb')
f.write(pic)
f.close()