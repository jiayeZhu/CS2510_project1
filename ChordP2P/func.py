from threading import Thread
from address import Address
import socket
import time

default_sleep_time = 1

class Func(Thread):
    def __init__(self, peer, state):
        super().__init__()
        self.conn = peer[0]   
        self.peer_addr = peer[1]
        self.state = state

    def run(self):
        # data = self.conn.recv(1024)
        # todo

        # keep the state of this node up-to-date.
        while True:
            print (self.conn)
            if self.state.in_ring:
                self.check_predecessor()
                self.stabilize()
                #
            time.sleep(default_sleep_time)

    def ping(self):
        print ('ping called')
        return 'Running on {}:{}'.format(self.state.ip, self.state.port)

    def create_ring(self):
        # self.state.successor = self.state.local_address                  #
        # self.state.predecessor = self.state.local_address
        self.state.finger[0] = self.state.id
        self.state.addr_dict[str(self.state.id)] = self.state.local_address
        self.state.in_ring = True
        return "New ring created"


    def send(self, remote_addr, data):
        ip, port = remote_addr.ip, remote_addr.port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, int(port)))
        s.sendall(data.encode())
        return s

    def join(self, ip, port):
        print('joining {}:{}'.format(ip, port))
        try:
            s = self.send(Address(ip, port), 'find_successor {}'.format(self.state.id))   #
            data = s.recv(1024).decode('utf-8')
            successor_ip, successor_port = data.split(':')   
            s.close()   
            self.state.lock.acquire()
            self.state.addr_dict[str(self.state.id)] = self.state.local_address
            self.state.successor = Address(successor_ip, successor_port)
            self.state.finger[0] = self.state.successor.hash
            self.state.addr_dict[str(self.state.finger[0])] = self.state.successor
            self.state.in_ring = True
            self.state.lock.release() 
            self.stabilize()           
            return 'successor found to be {}:{}'.format(successor_ip, successor_port)
        except:
            return "Error while joining the chord"

    def stabilize(self):
        try:
            s = self.send(self.state.successor, 'get_predecessor')
            res = s.recv(1024).decode('utf-8')
            s.close()
            if res != 'None':
                #the predecessor of its successor
                suc_pre_ip, suc_pre_port = res.split(':')
                suc_pre = Address(suc_pre_ip, suc_pre_port)
             #todo

    