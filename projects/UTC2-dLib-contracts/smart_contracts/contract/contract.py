from pyteal import *

# Constants for keys in the global state
FILE_CID_KEY = Bytes("file_cid")  # Global key to store the latest file CID uploaded to IPFS

# Constants for keys in the local state
USER_FILE_CID_KEY = Bytes("user_file_cid")  # Local key to store the user's latest file CID

# The maximum allowed length for the CID (string length in bytes)
MAX_CID_LENGTH = Int(46)  # CID strings are typically 46 characters

# Approval Program for the smart contract
def approval_program():
    
    # On creation, initialize global state variables
    on_create = Seq([
        App.globalPut(FILE_CID_KEY, Bytes("")),  # Initialize with empty CID
        Return(Int(1))
    ])

    # Handle OptIn: Initialize local state variables for a user
    on_opt_in = Seq([
        App.localPut(Txn.sender(), USER_FILE_CID_KEY, Bytes("")),  # Initialize with empty CID
        Return(Int(1))
    ])

    # Handle file upload by storing CID in the global state and local state
    upload_file = Seq([
        # Ensure exactly 1 argument is passed (the CID)
        Assert(Txn.application_args.length() == Int(2)),

        # Validate CID length
        Assert(Len(Txn.application_args[1]) <= MAX_CID_LENGTH),

        # Store the file CID in the global state
        App.globalPut(FILE_CID_KEY, Txn.application_args[1]),

        # Store the file CID in the user's local state
        App.localPut(Txn.sender(), USER_FILE_CID_KEY, Txn.application_args[1]),

        Return(Int(1))
    ])

    # The on_noop handler will check the first argument to determine the function being called
    on_noop = Cond(
        [Txn.application_args[0] == Bytes("upload_file"), upload_file]
    )

    # The main program logic: determine the type of call being made
    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.OptIn, on_opt_in],
        [Txn.on_completion() == OnComplete.NoOp, on_noop]
    )

    return program

# Clear State Program
def clear_state_program():
    return Return(Int(1))

# Compile and write the programs to files
if __name__ == "__main__":
    approval_teal = compileTeal(approval_program(), mode=Mode.Application, version=6)
    with open("approval.teal", "w") as f:
        f.write(approval_teal)

    clear_teal = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
    with open("clear_state.teal", "w") as f:
        f.write(clear_teal)