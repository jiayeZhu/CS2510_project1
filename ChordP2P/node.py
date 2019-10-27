from threading import Lock
import socket
import sys
import os
from func import Func
from address import Address
from state import State

M = 20

class Node:
    def start(self, port):
        self = State(port)

        # bind socket
        try:
          ip = self.ip
          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          s.bind((ip, port))
          s.listen()
          self.sock = s
          print('Listening on {}:{}'.format(ip, port))
        except Exception as e:
          print(e)

        # print the usage of this system
        print('-----------------------')
        print("usage : \n ping: ping the current node \n create_ring: create a new ring \n join <ip> <port>: join an existing ring \n exit: exit the system ")
        print('-----------------------')

        # keep the state of this node up-to-date.
        Func([None,None], self, True).start()
        #keep accepting new command
        while True:
          peer = s.accept()
          print ("after accept")
          Func(peer, self, False).start()
          print ("after func")

        s.close()

if __name__ == "__main__":
  if len(sys.argv) > 1:
    Node().start(int(sys.argv[1]))
  else:
    Node().start(8000)  