import requests

class IPFSManager:
    def __init__(self, pinata_jwt):
        self.pinata_jwt = pinata_jwt

    def upload_to_ipfs(self, file_path: str) -> str:
        """Uploads a file (image or video) to IPFS and returns the CID."""
        print(f"Uploading '{file_path}' to IPFS...")
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        headers = {"Authorization": f"Bearer {self.pinata_jwt}"}
        
        with open(file_path, "rb") as f:
            response = requests.post(url, files={"file": f}, headers=headers)
            
        if response.status_code == 200:
            ipfs_hash = response.json()["IpfsHash"]
            print(f"IPFS Upload Success! CID: {ipfs_hash}")
            return ipfs_hash
        else:
            raise Exception(f"IPFS Upload Failed: {response.text}")