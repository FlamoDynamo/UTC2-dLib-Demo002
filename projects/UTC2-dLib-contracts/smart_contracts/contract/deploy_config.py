from algosdk.v2client import algod
from algosdk import mnemonic
from algosdk import transaction
from algosdk import account

algod_address = "https://testnet-api.4160.nodely.dev/" # https://mainnet-api.4160.nodely.dev
algod_token = ""
mnemonic_phrase = "tree river prefer carry lift together charge priority cloud oxygen model twin hockey citizen deputy baby flip security bullet dry seat concert special about pride"

algod_client = algod.AlgodClient(algod_token, algod_address)

def get_account_info():
    account_private_key = mnemonic.to_private_key(mnemonic_phrase)
    account_address = account.address_from_private_key(account_private_key)
    return account_address, account_private_key

def deploy_application(approval_program, clear_program):
    account_address, account_private_key = get_account_info()

    txn = transaction.ApplicationCreateTxn(
        sender=account_address,
        sp=algod_client.suggested_params(),
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program
    )

    signed_txn = txn.sign(account_private_key)
    txid = algod_client.send_transaction(signed_txn)
    return txid