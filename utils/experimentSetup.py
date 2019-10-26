import sys
import os
import getopt
import hashlib
import random

M = 0
MIN = 1
MAX = 4096
n=0


def print_help():
    print("python3 experimentSetup.py\n"
          "\t-M <number of files you want to generate for each peer>\n"
          "\t-n <number of peers you want to setup>\n"
          "\t--min=<min size in bytes>(default=1)\n"
          "\t--max=<max size>(default=4096)\n")
    return

def genFiles(_dir_,M=0, MIN=0, MAX=1024):
    for i in range(M):
        hash = hashlib.md5()
        _ = str(random.random())
        hash.update(_.encode())
        filename = 'file_' + hash.hexdigest() + '.bin'
        with open(os.path.join(_dir_,filename), 'wb') as fout:
            fout.write(os.urandom(random.randint(MIN, MAX + 1)))
            fout.close()

try:
    opts, args = getopt.getopt(sys.argv[1:], 'hM:n:N:f:', ['min=', 'max='])
except getopt.GetoptError:
    print_help()
for (opt, arg) in opts:
    if opt == '-h':
        print_help()
        sys.exit()
    elif opt == '-M':
        M = int(arg)
    elif opt == '-n':
        n = int(arg)
    elif opt == '--min':
        MIN = int(arg)
    elif opt == '--max':
        MAX = int(arg)
if M * n == 0 :
    print_help()
    sys.exit()



# os.system('python3 ./CentralizedVersion/server.py > server.log &')

baseSharingDirName = 'sharing'
baseDownloadingDirName = 'downloads'
startPort = 23333
for i in range(n):
    sharingDir = baseSharingDirName+'_'+str(i)
    downloadingDir = baseDownloadingDirName+'_'+str(i)
    os.mkdir(sharingDir)
    os.mkdir(downloadingDir)
    genFiles(sharingDir,M,MIN,MAX)
    # os.system('python3 ./CentralizedVersion/client.py -p '+str(startPort+i)+' -s 127.0.0.1:8888 -i '+sharingDir+' -o '+downloadingDir+' -N '+str(N)+' -f'+str(f)+' > client_'+str(i)+'.log &')

