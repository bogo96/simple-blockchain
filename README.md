# simple-blockchain

### install

1. download the file

2.
```
brew install leveldb
```

3. 
```
pip3 install -r requirements.txt --user
```

### start
```
python3 route.py ip port
```

### make your own private, public key

1. Go to http://***ip:port***
2. The input value makes your own private, public key (you should remember it)

### make transaction

1. Address means your wallet address, Amount means your balance
2. recipient input means receiver's wallet address
3. amount input means money to send

### mining

your server mining every 30seconds if there are transaction

### check chain

http GET request to http://***ip:port***/chain

### adding nodes

if you want to add other nodes, then
http POST request to http://***ip:port***/nodes/register
json form should be like below
```
{
  'nodes' : [ip:port, ip:port,,,]
}
```

