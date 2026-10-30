import os
from dotenv import load_dotenv
from ipfs_handler import IPFSManager
from blockchain_handler import BlockchainManager

# Load keys securely from .env file
load_dotenv()

AMOY_RPC = os.getenv("AMOY_RPC")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PINATA_JWT = os.getenv("PINATA_JWT")

def process_and_anchor_evidence(file_path: str):
    """
    Main entry point for Project CIPHER. 
    Accepts an image (.jpg) or video (.mp4) path, uploads to IPFS, and anchors to Polygon.
    """
    print(f"\n[Project CIPHER] Initiating Edge-to-Ledger Protocol for: {file_path}")
    
    # Initialize separate handlers
    ipfs = IPFSManager(PINATA_JWT)
    ledger = BlockchainManager(AMOY_RPC, PRIVATE_KEY, CONTRACT_ADDRESS)
    
    try:
        # Step 1: Decentralized Storage
        cid = ipfs.upload_to_ipfs(file_path)
        
        # Step 2: Blockchain Anchoring
        ledger.send_to_blockchain(cid)
        
        print(f"[Project CIPHER] Protocol Complete. Evidence secured on-chain.")
        return cid
        
    except Exception as e:
        print(f"[Project CIPHER] Pipeline Failed: {e}")
        return None

if __name__ == "__main__":
    # Test with a frame or clip
    process_and_anchor_evidence("test_clip.mp4")