import os
import getopt
import sys
import random
import hashlib


def print_help():
    print("python3 filesGenerator.py -M <number of files you want to generate> -d <directory> --min=<min size> --max=<max size>")
    return


M = 0
MIN = 0
MAX = 0
_dir_ = ''
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hd:M:', ['min=', 'max='])
except getopt.GetoptError:
    print_help()
for (opt, arg) in opts:
    if opt == '-h':
        print_help()
        sys.exit()
    elif opt == '-M':
        M = int(arg)
    elif opt == '-d':
        _dir_ = arg
    elif opt == '--min':
        MIN = int(arg)
    elif opt == '--max':
        MAX = int(arg)
if M * MAX * MIN <= 0 or _dir_ == '':
    print_help()
    sys.exit()


def genFiles(M=0, MIN=0, MAX=1024):
    global _dir_
    for i in range(M):
        hash = hashlib.md5()
        _ = str(random.random())
        hash.update(_.encode())
        filename = 'file_' + hash.hexdigest() + '.bin'
        print(filename)
        with open(os.path.join(_dir_,filename), 'wb') as fout:
            fout.write(os.urandom(random.randint(MIN, MAX + 1)))
            fout.close()


genFiles(M, MIN, MAX)
