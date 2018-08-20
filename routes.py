import json
import binascii
import sys
import hashlib
from flask import Flask, jsonify, request, render_template
from blockchain import Blockchain
from uuid import uuid4
from levelpy import leveldb
from ecdsa import SigningKey, NIST384p
from apscheduler.schedulers.background import BackgroundScheduler

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
host = sys.argv[1]
port = sys.argv[2]

# Instantiate the Blockchain
blockchain = Blockchain()
blockchain.register_node(host+':'+port)

# Create levelDB
db = leveldb.LevelDB('./db/'+port, create_if_missing=True)

scheduler = BackgroundScheduler()

privkey = b''
pubkey = b''
wallet = ''

# @app.route('/mine', methods=['GET'])
def mine():
    if not blockchain.current_signatures:
        return

    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    first_hash = blockchain.hash({'sender': '0', 'recipient': node_identifier, 'amount': 1})
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
        hash=first_hash
    )

    # Check validation of transactions
    blockchain.valid_transaction()

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    # Put DB
    db.Put(('block-' + str(block['index'])).encode(), json.dumps(block, sort_keys=True).encode())
    print(db.Get(('block-' + str(block['index'])).encode()).decode())

    # response = {
    #     'message': "New Block Forged",
    #     'index': block['index'],
    #     'transactions': block['transactions'],
    #     'proof': block['proof'],
    #     'previous_hash': block['previous_hash'],
    # }
    # return jsonify(response), 200


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/wallet')
def wallet():
    return render_template('wallet.html')


@app.route('/login', methods=['POST'])
def login():
    global privkey, pubkey, wallet
    print(request.form['keyword'])
    keyword = request.form['keyword']


    # Create privatekey, publickey
    keywordByte = binascii.hexlify(keyword.encode())

    while len(keywordByte) < 48:
        keywordByte = keywordByte + b'0'
    privkey = SigningKey.from_string(keywordByte, curve=NIST384p)
    pubkey = privkey.get_verifying_key()

    wallet = hashlib.sha256(keyword.encode()).hexdigest()
    # for b in pubkey.to_string():
    #     wallet += "%02x" % b

    return jsonify({}), 200


@app.route('/getAddr', methods=['GET'])
def getAddr():
    global wallet
    response = {'pubkey': wallet}

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    global privkey, pubkey
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount', 'keyword']
    if not all(k in values for k in required):
        return 'Missing values', 400

    transaction_hash = blockchain.hash(values)
    values_string = json.dumps({
        "sender": values['sender'],
        "recipient": values['recipient'],
        "amount": values['amount'],
        "hash": transaction_hash,
        # "keyword": values['keyword']
    }, sort_keys=True).encode()

    # Create privatekey, publickey
    # keyword = binascii.hexlify(values['keyword'].encode())
    # while len(keyword)<48:
    #     keyword = keyword + b'0'
    # privkey = SigningKey.from_string(keyword, curve=NIST384p)
    # pubkey = privkey.get_verifying_key()

    # Transaction Signature
    sig = privkey.sign(values_string)

    # Create a new Transaction
    index = blockchain.new_signature(sig, values_string, pubkey)
    # index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():

    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    # import pdb; pdb.set_trace()
    replaced = blockchain.resolve_conflicts(host+':'+port)
    print(replaced)
    if replaced:
        # delete all
        for key, value in db.items():
            db.Delete(key)

        # put all blocks of new chain
        for block in blockchain.chain:
            db.Put(('block-' + str(block['index'])).encode(), str(block).encode())

        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


@app.route('/deleteDB', methods=['GET'])
def deleteAll():
    for key, value in db.items():
        db.Delete(key)

    response = {
        'message': 'Our db is removed',
    }

    return jsonify(response), 200


scheduler.add_job(mine, 'interval', seconds=60)
scheduler.start()

for key, value in db.items():
    blockchain.chain.append(json.loads(value))
    print(json.loads(value))

if __name__ == '__main__':
    app.run(host=host, port=int(port))
