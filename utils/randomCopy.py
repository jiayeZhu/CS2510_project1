import os
import random
import shutil

CpPossibility = 0.3


ls = os.listdir()
sharingDir = []
files = []
for item in ls:
    if 'sharing' in item:
        sharingDir.append(item)

for i in range(len(sharingDir)):
    files.append([])
    files[i] = os.listdir(sharingDir[i])

for i in range(len(sharingDir)):
    for f in files[i]:
        p = random.random()
        if p < CpPossibility:
            #decide how much copies
            copyNumber = random.randint(0,len(sharingDir)-1)
            target = list(range(len(sharingDir)))
            target.remove(i)
            target = random.sample(target,copyNumber)
            for t in target:
                shutil.copyfile(os.path.join(sharingDir[i],f),os.path.join(sharingDir[t],f))


print('done')