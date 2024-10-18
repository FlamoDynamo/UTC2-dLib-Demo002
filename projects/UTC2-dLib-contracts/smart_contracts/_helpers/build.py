from pyteal import *
from algosdk import encoding
from algosdk import account

def approval_program():
    return compileTeal(
        Seq([
            App.globalPut(Bytes("ebook_owner"), Txn.sender()),
            App.globalPut(Bytes("ebook_id"), Int(0)),
            Return(Int(1))
        ]),
        mode=Mode.Application
    )

def clear_state_program():
    return compileTeal(
        Return(Int(1)),
        mode=Mode.Application
    )