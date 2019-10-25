M = 20

class Address(object):
  def __init__(self, ip, port):
    self.ip = ip
    self.port = int(port)
    self.hash = abs(hash(('{}:{}'.format(self.ip, int(port))).encode())) % 2 ** M    #