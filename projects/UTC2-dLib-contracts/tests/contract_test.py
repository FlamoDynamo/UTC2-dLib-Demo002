# contract_test.py

import pytest
import base64
import requests  # For Pinata API
from algosdk import transaction
from algosdk.logic import get_application_address
from algosdk import account, mnemonic
from algosdk.v2client import algod
from pyteal import compileTeal, Mode
from dotenv import load_dotenv
import os
from smart_contracts.contract.contract import approval_program, clear_state_program

# Load environment variables
load_dotenv()

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN")
FAUCET_MNEMONIC = os.getenv("FAUCET_MNEMONIC")
PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_API_KEY = os.getenv("PINATA_SECRET_API_KEY")

PINATA_BASE_URL = "https://api.pinata.cloud"
PIN_FILE_TO_IPFS_URL = f"{PINATA_BASE_URL}/pinning/pinFileToIPFS"

@pytest.fixture(scope="module")
def algod_client():
    headers = {"X-API-Key": ALGOD_TOKEN}
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, headers)
    return client

@pytest.fixture(scope="module")
def faucet_account():
    private_key = mnemonic.to_private_key(FAUCET_MNEMONIC)
    address = account.address_from_private_key(private_key)
    return private_key, address

@pytest.fixture(scope="module")
def compiled_teal():
    approval_teal = compileTeal(approval_program(), mode=Mode.Application, version=6)
    clear_teal = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
    return approval_teal, clear_teal

def pin_file_to_ipfs(file_path):
    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_API_KEY
    }
    with open(file_path, 'rb') as file:
        response = requests.post(PIN_FILE_TO_IPFS_URL, files={"file": file}, headers=headers)
        if response.status_code == 200:
            return response.json()["IpfsHash"]
        else:
            raise Exception(f"Error uploading to IPFS: {response.text}")

def test_compile_contract(algod_client, compiled_teal):
    approval_teal, clear_teal = compiled_teal
    assert approval_teal is not None
    assert clear_teal is not None

def test_create_application(algod_client, faucet_account, compiled_teal):
    private_key, address = faucet_account
    approval_teal, clear_teal = compiled_teal

    params = algod_client.suggested_params()
    txn = transaction.ApplicationCreateTxn(
        sender=address,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=base64.b64decode(approval_teal),
        clear_program=base64.b64decode(clear_teal),
        global_schema=transaction.StateSchema(num_uints=2, num_byte_slices=4),
        local_schema=transaction.StateSchema(num_uints=1, num_byte_slices=2)
    )
    
    signed_txn = txn.sign(private_key)
    tx_id = algod_client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(algod_client, tx_id)
    
    response = algod_client.pending_transaction_info(tx_id)
    assert response.get('application-index') is not None

def test_opt_in(algod_client, faucet_account, app_id):
    private_key, address = faucet_account
    params = algod_client.suggested_params()
    
    opt_in_txn = transaction.ApplicationOptInTxn(
        sender=address,
        sp=params,
        index=app_id
    )
    signed_txn = opt_in_txn.sign(private_key)
    tx_id = algod_client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(algod_client, tx_id)
    
    local_state = algod_client.account_info(address).get('apps-local-state')
    assert any(app['id'] == app_id for app in local_state)

def test_upload_file(algod_client, faucet_account, app_id):
    private_key, address = faucet_account
    params = algod_client.suggested_params()
    
    # Upload file to IPFS via Pinata API
    file_cid = pin_file_to_ipfs("test_file.txt")

    upload_txn = transaction.ApplicationNoOpTxn(
        sender=address,
        sp=params,
        index=app_id,
        app_args=[b"upload_file", file_cid.encode()]
    )
    signed_txn = upload_txn.sign(private_key)
    tx_id = algod_client.send_transaction(signed_txn)
    transaction.wait_for_confirmation(algod_client, tx_id)
    
    global_state = algod_client.application_info(app_id).get('params').get('global-state')
    file_cid_stored = next((kv['value']['bytes'] for kv in global_state if kv['key'] == "file_cid"), None)
    
    assert file_cid_stored == file_cid