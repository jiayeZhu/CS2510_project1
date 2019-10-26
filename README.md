# CS2510_project1
p2p file sharing system

# how to use
```
python3 utils/experimentSetup.py
    -h show this help
    -M <number of files you want to generate for each peer>
    -n <number of peers you want to setup>
    --min=<min size in bytes>(default=1)
    --max=<max size>(default=4096)
```
example: `python3 utils/experimentSetup.py -M 1000 -n 10 --min=1 --max=4096`

```
bash utils/start.bash <Number of peers> <number of sequential request every period> <interval of file requst to other peers> <Time of the experiment in seconds>
```
example: `bash utils/start.bash 10 10 3 30` means start a 30 seconds experiment with 10 peers and request for 10 files every 3 seconds

After the experiment, use `bash utils/cleanup.bash` to cleanup directory.

*.stat files are the statistical results