python3 CentralizedVersion/server.py -T $[1+$4] 1>server.log 2>/dev/null &
sleep 1 #wait for the server to start up
for((i = 0; i < $1; i++))
do
	python3 CentralizedVersion/client.py -p $[23333+$i] -s 127.0.0.1:18888 -i sharing_$[0+$i] -o downloads_$[0+$i] -N $2 -f $3  -T $4 1>client_$[0+$i].log 2>/dev/null &
done

