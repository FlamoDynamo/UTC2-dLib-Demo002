# deploy.py

import os
import sys
import json
import base64
import traceback
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk import transaction
from algosdk.logic import get_application_address
from pyteal import compileTeal, Mode

# Thêm đường dẫn đến thư mục contract
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'contract')))

# Import từ contract.py
from contract import approval_program, clear_state_program

# Load environment variables
load_dotenv()

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN")
FAUCET_MNEMONIC = os.getenv("FAUCET_MNEMONIC")
APPROVAL_FILE = "approval.teal"
CLEAR_FILE = "clear_state.teal"
APP_ID_FILE = "app_id.json"

def get_algod_client():
    try:
        headers = {"X-API-Key": ALGOD_TOKEN}
        client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, headers)
        return client
    except Exception as e:
        print(f"Error creating Algod client: {e}")
        sys.exit(1)

def get_faucet_account():
    try:
        private_key = mnemonic.to_private_key(FAUCET_MNEMONIC)
        address = account.address_from_private_key(private_key)
        return private_key, address
    except Exception as e:
        print(f"Error converting mnemonic to private key: {e}")
        traceback.print_exc()
        sys.exit(1)

def compile_program(client, source_code):
    try:
        compile_response = client.compile(source_code)
        return compile_response['result']
    except Exception as e:
        print(f"Error compiling program: {e}")
        traceback.print_exc()
        sys.exit(1)

def write_teal_files():
    try:
        approval_teal = compileTeal(approval_program(), mode=Mode.Application, version=6)
        clear_teal = compileTeal(clear_state_program(), mode=Mode.Application, version=6)

        with open(APPROVAL_FILE, "w") as f:
            f.write(approval_teal)
        with open(CLEAR_FILE, "w") as f:
            f.write(clear_teal)
        print(f"Compiled TEAL programs written to {APPROVAL_FILE} and {CLEAR_FILE}")
    except Exception as e:
        print(f"Error writing TEAL files: {e}")
        traceback.print_exc()
        sys.exit(1)

def create_app(client, creator_private_key, approval_program_compiled, clear_program_compiled):
    try:
        params = client.suggested_params()
        txn = transaction.ApplicationCreateTxn(
            sender=account.address_from_private_key(creator_private_key),
            sp=params,
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=base64.b64decode(approval_program_compiled),
            clear_program=base64.b64decode(clear_program_compiled),
            global_schema=transaction.StateSchema(num_uints=2, num_byte_slices=4),
            local_schema=transaction.StateSchema(num_uints=1, num_byte_slices=2)
        )
        signed_txn = txn.sign(creator_private_key)
        tx_id = client.send_transaction(signed_txn)
        print(f"Sent transaction with txID: {tx_id}")
        transaction.wait_for_confirmation(client, tx_id, 4)
        response = client.pending_transaction_info(tx_id)
        app_id = response['application-index']
        print(f"Created new app with App ID: {app_id}")
        return app_id
    except Exception as e:
        print(f"Error creating application: {e}")
        traceback.print_exc()
        sys.exit(1)

def save_app_id(app_id):
    try:
        with open(APP_ID_FILE, "w") as f:
            json.dump({"app_id": app_id}, f)
        print(f"App ID saved to {APP_ID_FILE}")
    except Exception as e:
        print(f"Error saving App ID: {e}")
        traceback.print_exc()
        sys.exit(1)

def fund_application_account(client, sender_private_key, app_id, amount):
    try:
        app_address = get_application_address(app_id)
        params = client.suggested_params()
        txn = transaction.PaymentTxn(
            sender=account.address_from_private_key(sender_private_key),
            sp=params,
            receiver=app_address,
            amt=amount  # Số lượng Algos muốn gửi (microAlgos)
        )
        signed_txn = txn.sign(sender_private_key)
        tx_id = client.send_transaction(signed_txn)
        transaction.wait_for_confirmation(client, tx_id, 4)
        print(f"Funded {amount} Algos to application account {app_address}. Transaction ID: {tx_id}")
    except Exception as e:
        print(f"Error funding application account: {e}")
        traceback.print_exc()
        sys.exit(1)

def main():
    # Kiểm tra xem các biến môi trường đã được đặt chưa
    if not all([ALGOD_ADDRESS, ALGOD_TOKEN, FAUCET_MNEMONIC]):
        print("Please set ALGOD_ADDRESS, ALGOD_TOKEN, and FAUCET_MNEMONIC in the .env file")
        sys.exit(1)
    
    client = get_algod_client()
    faucet_private_key, faucet_address = get_faucet_account()
    print(f"Faucet Address: {faucet_address}")
    
    # Compile and write TEAL files
    write_teal_files()
    
    # Read TEAL source code
    try:
        with open(APPROVAL_FILE, "r") as f:
            approval_source = f.read()
        with open(CLEAR_FILE, "r") as f:
            clear_source = f.read()
    except Exception as e:
        print(f"Error reading TEAL files: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Compile TEAL programs
    approval_compiled = compile_program(client, approval_source)
    clear_compiled = compile_program(client, clear_source)
    
    # Create the application
    app_id = create_app(client, faucet_private_key, approval_compiled, clear_compiled)
    
    # Fund the application account
    fund_application_account(client, faucet_private_key, app_id, 1000000)  # Nạp 1 ALGO
    
    # Save the App ID
    save_app_id(app_id)
    
    print("Deployment successful!")

if __name__ == "__main__":
    main()