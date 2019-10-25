from threading import Lock
import socket
import sys
import os
from func import Func
from address import Address

M = 20

class Node:
    def start(self, port):

        # initialize the state of a new node
        self.in_ring = False
        self.ip = socket.gethostbyname(socket.gethostname())
        self.port = port
        self.local_address = Address(self.ip, self.port)
        self.id = self.local_address.hash
        # self.id = abs(hash(('{}:{}'.format(self.ip, int(port))).encode())) % 2 ** M
        self.predecessor = None
        self.successor = None
        self.finger = [None] * M  # contains finger nodes' Chord ids
        self.addr_dict = {}  # key: a Chord id; value: corresponding Address (IP/port) 
        self.i = 1
        self.lock = Lock()

        # bind socket
        ip = self.ip
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((ip, port))
        s.listen()
        print('Listening on {}:{}'.format(ip, port))
        

    # keep the state of this node up-to-date.
        Func([None,None], self).start()
        print ("-------")

        while True:
            print ("accept")
            peer = s.accept()
            print ("after accept")
            Func(peer, self).start()
            print ("after func")

        s.close()

if __name__ == "__main__":
  if len(sys.argv) > 1:
    Node().start(int(sys.argv[1]))
  else:
    Node().start(8000)  