import pytest
from algosdk.v2client import algod
from algosdk import mnemonic, account

@pytest.fixture(scope="module")
def algod_client():
    algod_address = "https://testnet-api.4160.nodely.dev/" # https://mainnet-api.4160.nodely.dev
    algod_token = ""
    
    return algod.AlgodClient(algod_token, algod_address)

@pytest.fixture(scope="module")
def account_info():
    mnemonic_phrase = "tree river prefer carry lift together charge priority cloud oxygen model twin hockey citizen deputy baby flip security bullet dry seat concert special about pride"
    account_private_key = mnemonic.to_private_key(mnemonic_phrase)
    account_address = account.address_from_private_key(account_private_key)
    return account_address, account_private_key