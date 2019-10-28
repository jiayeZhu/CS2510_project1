python3 .\ChordP2P\chordNode.py -l 127.0.0.1 -p 8888 -i sharing_0 -o downloads_0 -N $2 -f $3 -T $4
for((i = 1; i < $1; i++))
do
	python3 ChordP2P/chordNode.py -l 127.0.0.1 -p $[23333+$i] -s 127.0.0.1:8888 -i sharing_$[0+$i] -o downloads_$[0+$i] -N $2 -f $3  -T $4 1>client_$[0+$i].log 2>/dev/null &
done