from typing import Dict, List, NamedTuple, NewType, TypedDict

from eth_typing import HexStr

BLSPrivkey = NewType("BLSPrivkey", int)
Bytes32 = NewType("Bytes32", bytes)
Bytes4 = NewType("Bytes4", bytes)
Gwei = NewType("Gwei", int)


class KeyPair(TypedDict):
    public_key: HexStr
    private_key: BLSPrivkey


class MerkleDepositData(TypedDict):
    public_key: HexStr
    signature: HexStr
    amount: str
    withdrawal_credentials: HexStr
    deposit_data_root: HexStr
    proof: List[HexStr]


class VaultKeystore(TypedDict):
    validator_name: str
    keystore: str


class SigningKey(NamedTuple):
    path: str
    key: BLSPrivkey


class DatabaseKeyRecord(TypedDict):
    public_key: HexStr
    private_key: str
    nonce: str
    validator_index: int


class MigrationKey(TypedDict):
    public_key: str
    validators_count: int


VaultState = Dict[HexStr, VaultKeystore]
