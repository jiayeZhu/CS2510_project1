from threading import Lock
import socket
import sys
import os
from func import Func
from address import Address

M = 20

class State:
  def __init__(self, port=8000):
    # initialize the state of a new node
    self.in_ring = False
    # self.ip = ''
    self.ip = socket.gethostbyname(socket.gethostname())
    self.port = port
    self.address = Address(self.ip, self.port)
    self.id = self.address.hash
    # self.id = abs(hash(('{}:{}'.format(self.ip, int(port))).encode())) % 2 ** M
    self.predecessor = None
    self.successor = None
    self.finger = {}  # contains finger nodes' Chord ids
    self.addr_dict = {}  # key: a Chord id; value: corresponding Address (IP/port) 
    self.i = 1
    self.lock = Lock()