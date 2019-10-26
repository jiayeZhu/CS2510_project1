python3 CentralizedVersion/server.py > server.log &

for((i = 0; i < $1; i++))
do
	python3 CentralizedVersion/client.py -p $[23333+$i] -s 127.0.0.1:8888 -i sharing_$[0+$i] -o downloads_$[0+$i] -N $2 -f $3 > client_$[0+$i].log &
done

