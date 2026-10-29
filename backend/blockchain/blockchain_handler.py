from web3 import Web3

class BlockchainManager:
    def __init__(self, rpc_url, private_key, contract_address):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = private_key
        self.account = self.w3.eth.account.from_key(private_key)
        self.contract_address = self.w3.to_checksum_address(contract_address)
        
        self.contract_abi = [
            {
                "inputs": [{"internalType": "string", "name": "_ipfsCID", "type": "string"}],
                "name": "anchorEvidence",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

    def send_to_blockchain(self, ipfs_cid: str):
        """Broadcasts the IPFS CID to the smart contract."""
        print("Building live blockchain transaction...")
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        txn = self.contract.functions.anchorEvidence(ipfs_cid).build_transaction({
            'chainId': 80002, 
            'gas': 500000, 
            'maxFeePerGas': self.w3.to_wei('60', 'gwei'),
            'maxPriorityFeePerGas': self.w3.to_wei('30', 'gwei'),
            'nonce': nonce,
        })
        
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key=self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction Broadcasted! Tx Hash: https://amoy.polygonscan.com/tx/{tx_hash.hex()}")
        
        print("Waiting for network confirmation...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Success! CID anchored permanently on block number: {receipt.blockNumber}")