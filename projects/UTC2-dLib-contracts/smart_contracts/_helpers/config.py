from algosdk.v2client import algod

ALGORAND_ADDRESS = "https://testnet-api.4160.nodely.dev/" # https://mainnet-api.4160.nodely.dev
ALGORAND_TOKEN = ""

def get_algod_client():
    return algod.AlgodClient(ALGORAND_TOKEN, ALGORAND_ADDRESS)