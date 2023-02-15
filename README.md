# Keysync CLI

Keysync CLI takes validator keys generated with staking-deposit-cli and
synchronizes them to a PostgreSQL DB for use by web3signer.

It is fork of Stakewise's Operators CLI, with most functionality removed,
and DB sync from keystore-m files added.

## Usage

### Step 1. Installation

#### Install prerequisites

```
sudo apt-get install python3-dev
pip3 install poetry
pip3 install pyinstaller
```

#### Install dependencies

`poetry install --no-interaction --no-root`

#### Make executable

Adjust `RELEASE_VERSION` and run:

```
export RELEASE_VERSION=x.x.x
export PYTHONHASHSEED=42
export BUILD_FILE_NAME=~/gd-cli-${RELEASE_VERSION}-linux-amd64;
mkdir ~/${BUILD_FILE_NAME};
poetry run pyinstaller --onefile --hidden-import multiaddr.codecs.uint16be --hidden-import multiaddr.codecs.idna --collect-data stakewise_cli ./stakewise_cli/main.py --name gd-cli --distpath ~/${BUILD_FILE_NAME}
```


### Step 2. Create keys

Use the official [staking-deposit-cli](https://github.com/ethereum/staking-deposit-cli) or any tool of your choice
that outputs standard `keystore-m` JSON files to generate staking keys. This should be done on an airgapped, ephemeral
machine, for example a Linux Live USB.

Make sure to set a withdrawal address with `--eth1_withdrawal_address 0xMYWALLET` during key generation! If this is not done, the withdrawal credentials will be a BLS key encoded by the mnemonic, and a withdrawal address would need to be set at a later date.

You will have:

- One mnemonic. Keep this safe, only ever offline. It can be used to recreate keys as well as to generate additional keys.
- Several keystore-m files encrypted with a passphrase. These will be loaded into the PostgreSQL database
- One or more deposit_data files. You can "break these up" into as many keys per part as desired. All data in deposit_data is public. This contains the withdrawal credentials: Verify they are the expected address for all keys.

**NB! You must store the generated mnemonic in a secure cold storage.
It will allow you to restore the keys in case the database will get corrupted or lost.**

### Step 3. Deploy staking infrastructure

Follow the instructions [here](https://docs.stakewise.io/node-operator/stakewise-infra-package/usage)
to deploy the staking infrastructure.

### Step 4. Sync keys to the database

You will use the keys generated in step 1. Place all keystore-m files into a directory. They all need to have the same password.

```bash
./gd-cli sync-db
```

This will synchronize all keys to the database, encrypt them at rest, and give you a decryption key.

The web3signer pods will need to be redeployed with this key and restarted, whenever keys are added.

Adding keys involves loading all keys into a fresh table: Always keep all keystore-m in the import directory, not just new keystore-m.

### Step 5. Deposit for the keys

You can safely synchronize e.g. 1,000 keys to the database and then deposit for them in batches as small as desired. To deposit, use a deposit_data JSON file that contains validators that have **not** been deposited for, and only those, at the [Ethereum launchpad](https://launchpad.ethereum.org) or with a tool of your choosing such as ethdo or a bulk deposit contract.

**NB It is possible to double-deposit. Processes should be in place to dispose of deposit_data JSON that have successfully been deposited for**

**WARNING The withdrawal address cannot be changed after deposit. Triple-check that it is an address under your control!**
 
