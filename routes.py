import os
import json
import binascii
import sys
import hashlib
import ast
import requests
from flask import Flask, jsonify, request, render_template,\
    session, redirect, url_for
from blockchain import Blockchain
from uuid import uuid4
from levelpy import leveldb
from ecdsa import SigningKey, VerifyingKey, NIST384p
from apscheduler.schedulers.background import BackgroundScheduler

# Instantiate our Node
app = Flask(__name__)
app.secret_key = b'z*\x82\xa2\x1c\x8cT\x92\x0e\x0c@\x16\x06\xe2?\x9c'
scheduler = BackgroundScheduler()

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')
ip = sys.argv[1]
port = sys.argv[2]
host = ip+":"+port

# Instantiate the Blockchain
blockchain = Blockchain()

# Create levelDB
if not os.path.isdir('./db/account'):
    os.mkdir('./db')
    os.mkdir('./db/account')

db = leveldb.LevelDB('./db/'+host, create_if_missing=True)
accountdb = leveldb.LevelDB('./db/account/'+host, create_if_missing=True)


def mine():
    if not blockchain.current_signatures:
        return

    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # Check validation of transactions
    blockchain.valid_transaction()

    # chain resolve
    replaced, index = blockchain.resolve_conflicts(host)
    if replaced:
        update_db(index)

    # Update account DB
    for transaction in blockchain.current_transactions:
        send_money = transaction['amount']
        for key, value in accountdb.items():
            recipient_key = transaction['recipient'].encode()
            sender_key = transaction['sender'].encode()

            if key == recipient_key:
                recipient_money = accountdb.Get(recipient_key)
                accountdb.put(recipient_key,
                              int(recipient_money) + int(send_money))
            elif key == sender_key:
                sender_money = accountdb.Get(sender_key)
                accountdb.put(sender_key,
                              int(sender_money) - int(send_money))

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    first_hash = blockchain.hash({
        'sender': '0',
        'recipient': node_identifier,
        'amount': 1
    })
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
        hash=first_hash,
        sig=port
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    # Put DB
    db.Put(('block-' + str(block['index'])).encode(),
           json.dumps(block, sort_keys=True).encode())


def add_nodes(nodes):
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)


def update_db(index):
    for i in range(index, len(blockchain.chain)):
        db.Put(('block-' + str(i)).encode(),
               json.dumps(blockchain.chain[index], sort_keys=True).encode())


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/wallet')
def wallet():
    return render_template('wallet.html')


@app.route('/login', methods=['POST'])
def login():
    keyword = request.form['keyword']

    # Create private key, public key
    keyword_byte = binascii.hexlify(keyword.encode())

    while len(keyword_byte) < 48:
        keyword_byte = keyword_byte + b'0'
    privkey = SigningKey.from_string(keyword_byte, curve=NIST384p)
    pubkey = privkey.get_verifying_key()

    wallet = hashlib.sha256(keyword.encode()).hexdigest()

    session['wallet'] = wallet
    session['pubkey'] = pubkey.to_string()
    session['privkey'] = privkey.to_string()

    return jsonify(), 200


@app.route('/info', methods=['GET'])
def get_info():
    amount = -1

    if 'wallet' in session:
        wallet = session['wallet']
    else:
        return jsonify(), 404

    for key, value in accountdb.items():
        if key == wallet.encode():
            amount = int(value)

    if amount == -1:
        amount = 100
        accountdb.put(wallet.encode(), 100)

    return redirect(url_for('spread_info', amount=amount))


@app.route('/spread_info', methods=['POST', 'GET'], endpoint='spread_info')
def spread_info():
    if request.method == 'GET':
        amount = request.args.get('amount')
        wallet = session['wallet']
        data = {'wallet': wallet, 'amount': amount, 'node': host}

        new_nodes = set()
        for node in blockchain.nodes:
            if node == host:
                continue
            response = requests.post("http://"+node+"/spread_info", data=data)
            for res_node in json.loads(response.text)['nodes']:
                if node != host:
                    new_nodes.add(res_node)

        add_nodes(new_nodes)
        return jsonify(data), 200

    elif request.method == 'POST':
        accountdb.put(request.form['wallet'].encode(), request.form['amount'])
        response = {'nodes': list(blockchain.nodes)}
        blockchain.register_node(request.form['node'])
        return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def make_signature():
    privkey_string = session['privkey']
    privkey = SigningKey.from_string(privkey_string, curve=NIST384p)
    wallet = session['wallet']
    values = request.form

    # Check that the required fields are in the POST'ed data
    required = ['recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    transaction_hash = blockchain.hash({
        'sender': wallet,
        'recipient': values['recipient'],
        'amount': values['amount']
    })
    values_string = json.dumps({
        "sender": wallet,
        "recipient": values['recipient'],
        "amount": values['amount'],
        "hash": transaction_hash,
    }, sort_keys=True).encode()

    # Transaction Signature
    sig = privkey.sign(values_string)
    req = {"sig": sig, "values_string": values_string}
    return redirect(url_for('spread_transaction', req=req))


@app.route('/transactions/spread',
           methods=['POST', 'GET'],
           endpoint='spread_transaction')
def spread_transaction():
    if request.method == 'GET':
        req = request.args.get('req')
        sig = ast.literal_eval(req)['sig']
        values_string = ast.literal_eval(req)['values_string']
        pubkey_string = session['pubkey']
        pubkey = VerifyingKey.from_string(pubkey_string, curve=NIST384p)

        data = {
            'sig': sig.hex(),
            'values_string': values_string,
            'pubkey': pubkey_string.hex()
        }
        for node in blockchain.nodes:
            if node != host:
                requests.post("http://" + node + "/transactions/spread",
                              data=data)

    elif request.method == 'POST':
        sig = bytes.fromhex(request.form['sig'])
        values_string = request.form['values_string'].encode()
        pubkey_string = bytes.fromhex(request.form['pubkey'])
        pubkey = VerifyingKey.from_string(pubkey_string, curve=NIST384p)

    # Create a new Transaction
    index = blockchain.new_signature(sig, values_string, pubkey)
    response = {'message': f'Transaction will be added to Block {index}'}

    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():

    response = {
        'chain': blockchain.chain,
        'chain_length': len(blockchain.chain),
        'nodes_length': len(blockchain.nodes)
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.form['nodes']
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
    replaced, index = blockchain.resolve_conflicts(host)

    if replaced:
        # delete all
        for key, value in db.items():
            db.Delete(key)

        # put all blocks of new chain
        for block in blockchain.chain:
            db.Put(('block-' + str(block['index'])).encode(),
                   str(block).encode())

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


if __name__ == '__main__':
    scheduler.add_job(mine, 'interval', seconds=30)
    scheduler.start()

    for key, value in db.items():
        blockchain.chain.append(json.loads(value))

    app.run(host=ip, port=int(port))
