from threading import Thread
from address  import Address
import socket
import time
import sys
import os

default_sleep_time = 1

def between(hash1, hash2, hash3):
    if(hash2 < hash1) and (hash1 < hash3):
        return True

class Func(Thread):
    def __init__(self, peer, state, initial = False):
        
        super().__init__()
        self.state = state
        if(initial == False):
            self.conn = peer[0]   
            self.peer_addr = peer[1]
            data = self.conn.recv(1024)
            request = data.decode('utf-8').split(' ')
            print('data received : ', request)
            ans = self.check_request(request)
            if(ans == None):
                ans = self.peer_addr
            self.conn.sendall(ans.encode())
            self.conn.close()


                
    def check_request(self, request):
        try:
            if((request[0] == 'find_successor') and (len(request) == 2)):
                return (self.find_successor(int(request[1])))  

            else:
                print('Invalid function')
                return ('Invalid function')
        except Exception as e:
            print(e)

    def run(self):
        while True:
            command = input('>>')
            # print(command)
            command = command.split(' ')
            if command[0] =="create_ring":
                print(self.create_ring())
            elif command[0] =="join":
                if (len(command) != 3):
                    print("usage : join <ip> <port>")
                else:
                    return (self.join(command[1], int(command[2])))
            elif command[0] == 'ping':
                print(self.ping())
            elif command[0] == 'exit':
                # sys.exit()
                os._exit(0)
            else:
                print('-----------------------')
                print("usage : \n exit: exit the system \n ping: ping the current node \n create_ring: create a new ring \n join <ip> <port>: join an existing ring")
                print('-----------------------')
                continue

        # keep the state of this node up-to-date.
            # print (self.conn)
            # if self.state.in_ring:
            #     self.stabilize()
            # time.sleep(default_sleep_time)

    def ping(self):
        print ('ping called')
        return 'Running on {}:{}'.format(self.state.ip, self.state.port)

    def create_ring(self):
        # self.state.successor = self.state.address                  #
        # self.state.predecessor = self.state.address
        self.state.finger[0] = self.state.id
        self.state.addr_dict[str(self.state.id)] = self.state.address
        self.state.in_ring = True
        return "New ring created"


    def send(self, remote_addr, data):
        ip, port = remote_addr.ip, remote_addr.port
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print('send to : ', ip , ':' , port)
            s.connect((ip, int(port)))
            s.sendall(data.encode())
        except Exception as e:
            print(e)
        return s

    def join(self, ip, port):
        try:
            # new node requests the wizard(ip, port) to find its successor
            s = self.send(Address(ip, port), 'find_successor {}'.format(self.state.id))   
            data = s.recv(1024).decode('utf-8')
            # print('data: ' , data)
            # print("data.split(':')  " , data.split(':')  )
            successor_ip, successor_port = data.split(':')   
            print(successor_ip, '  ,', successor_port)
            s.close()
            self.state.lock.acquire()
            self.state.addr_dict[str(self.state.id)] = self.state.address
            self.state.successor = Address(successor_ip, successor_port)
            self.state.finger[0] = self.state.successor.hash
            self.state.addr_dict[str(self.state.finger[0])] = self.state.successor
            self.state.in_ring = True
            self.state.lock.release() 
            self.stabilize()        
            print("stablized is done")   
            return 'successor found to be {}:{}'.format(successor_ip, successor_port)
        except Exception as e:
            print(e)
            return "Error while joining the chord"

    def  find_successor(self, id):
        # if id should be the first node
        try:
            print('find_successor is active')
            if((id < self.state.id) and (self.state.predecessor == None)):
                return '{}:{}'.format(self.state.ip, self.state.port)
            # if id should be the last node
            elif((id > self.state.id) and (self.state.successor == None)):
                print(2)
                return None
            #else
            elif(between(id, self.state.id, self.state.successor.id)):
                print(3)
                return '{}:{}'.format(self.state.successor.address.ip, self.state.successor.address.port)
            else:
                print(4)
                for i in len(self.state.finger):
                    if(between(id, self.state.finger[i]), self.state.finger[i + 1]):
                        next_ip = self.state.addr_dict[str(self.state.finger[i])].ip
                        next_port = self.state.addr_dict[str(self.state.finger[i])].port
                        break
                s = self.send(Address(next_ip, next_port), 'find_successor {}'.format(id))
                print(5)
                return s.recv(1024).decode('utf-8')
        except Exception as e:
            print(e)

    def stabilize(self):
        try:
            #check the predecessor of its successor
            s = self.send(self.state.successor, 'check_pre_of_suc')
            res = s.recv(1024).decode('utf-8')
            s.close()
            if res != 'None':
                pre_of_suc_ip, pre_of_suc_port = res.split(':')
                #the predecessor of its successor has changed
                if(pre_of_suc_ip != self.state.ip) and (pre_of_suc_port != self.state.port):
                    self.state.successor = Address(pre_of_suc_ip, pre_of_suc_port)
                    s = self.send(self.state.successor, 'notify {}:{}'.format(self.state.successor.ip, self.state.successor.port))
        except:
            print("Failed to check the predecessor of its successor")

    def check_pre_of_suc(self):
        #check the predecessor of its successor
        if (self.state.predecessor != None):
            try:
                s = self.send(self.state.predecessor, 'ping')
                response = s.recv(1024)
                print(response)
                if (response[:7] == b'Running'):
                    ss = self.send(self.state.predecessor, 'get_successor')
                    res = ss.recv(1024).decode('utf-8')
                    if (res != 'None'):
                        pre_of_suc_ip, pre_of_suc_port = res.split(':')
                        return '{}:{}'.format(pre_of_suc_ip, pre_of_suc_port)
                else:
                    self.state.lock.acquire()
                    self.state.predecessor = None
                    self.state.lock.release()
                    print("Failed to get response from predecessor")
            except:
                print('unexpected response while ping predecessor : ' , response)
                self.state.lock.acquire()
                del self.state.addr_dict[str(self.state.predecessor.hash)]
                self.state.predecessor = None
                self.state.lock.release()
                print("Failed to get response from predecessor")

    def get_successor(self):
        return '{}:{}'.format(self.state.successor.ip, self.state.successor.port)

    def notify(self, ip, port):
        #get notified, modify its predecessor to (ip, port)
        new_pre = Address(ip, port)
        self.state.lock.acquire()  
        self.state.predecessor = new_pre
        self.state.lock.release() 