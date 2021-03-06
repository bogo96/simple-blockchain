import hashlib
import json
import requests
from time import time


class Blockchain(object):

    def __init__(self):
        self.difficulty = 4
        self.chain = []
        self.current_transactions = []
        self.current_signatures = []
        self.nodes = set()

        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []
        self.current_signatures = []

        self.chain.append(block)
        return block

    def valid_transaction(self):
        for signature in self.current_signatures:
            sig, data, pubkey = signature
            if pubkey.verify(sig, data):
                data = json.loads(data)
                transaction = {
                    "sender": data['sender'],
                    "recipient": data['recipient'],
                    "amount": data['amount'],
                }
                if data['hash'] == self.hash(transaction):
                    self.new_transaction(data['sender'], data['recipient'],
                                         data['amount'], data['hash'], sig)

    def new_signature(self, sig, data, publickey):
        """
        Creates a new transaction to go into the next mined Block

        :param sig: sign to transaction
        :param data: <str> transaction json
        :param publickey: publickey
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_signatures.append(
            (sig, data, publickey)
        )

        return self.last_block['index'] + 1

    def new_transaction(self, sender, recipient, amount, hash, sig):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'hash': hash,
            'signature': str(sig)
        })

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered,
        # or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof, self.difficulty) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof, difficulty):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:difficulty] == "0" * difficulty

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        self.nodes.add(address)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'],
                                    block['proof'],
                                    self.difficulty):
                return False

            last_block = block
            current_index += 1

        return True

    def difference_chain(self, chain):
        small_len = len(self.chain)
        for i in range(small_len-1, -1, -1):
            if chain[i]['previous_hash'] == self.chain[i]['previous_hash']:
                break

        return i

    def resolve_conflicts(self, current):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            if current == node:
                continue
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['chain_length']
                nodes_length = response.json()['nodes_length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
                    index = self.difference_chain(chain)
                elif length == max_length \
                        and nodes_length > len(self.nodes) \
                        and self.valid_chain(chain):
                    new_chain = chain
                    index = self.difference_chain(chain)

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True, index

        return False, 0
