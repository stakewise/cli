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


### Not yet updated beyond here

### Step 2. Create Deposit Data

Run the following command to create deposit data and DAO proposal specification:

```bash
./operator-cli create-deposit-data
```

**NB! You must store the generated mnemonic in a secure cold storage.
It will allow you to restore the keys in case the Vault will get corrupted or lost.**

### Step 3. Submit DAO proposal

Create a post about joining operators set at [StakeWise Forum](https://vote.stakewise.io).
In your post you must include the `Specification` section that was generated in the previous step.

### Step 4. Deploy ETH2 infrastructure

If the proposal from the previous step got approved by the DAO, follow the instructions [here](https://docs.stakewise.io/node-operator/stakewise-infra-package/usage)
to deploy the ETH2 staking infrastructure.

### Step 5. Sync keys to the Vault or locally

You must **use the same mnemonic** as generated in step 1.
**NB! Using the same mnemonic for multiple vaults will result into validators slashings**.

Run the following command to sync new validator keys to the vault:

```bash
./operator-cli sync-vault
```

or to sync them locally

```bash
./operator-cli sync-local
```

After fetching the keys, make sure you have the right number of validators running and restart those that got new keys added.

### Step 6. Commit Operator

Once you're 100% ready for Ether assignments, commit your operator:

- Go to the Operators smart contract ([Goerli](https://goerli.etherscan.io/address/0x0d92156861a0BC7037cC21470327Bd3Bc750EB1D#writeProxyContract), [Harbour Goerli](https://goerli.etherscan.io/address/0x7C27896338e3130036E53BCC0f013cB20e21991c#writeProxyContract), [Mainnet](https://etherscan.io/address/0x002932e11E95DC84C17ed5f94a0439645D8a97BC), [Harbour Mainnet](https://etherscan.io/address/0x270ad793b7bb315a9fd07f1fffd8ab1e3621df7e))
- Click on `Connect to Web3` button and connect your wallet. The address must match the one used during proposal generation.
- Call `commitOperator` function. If that's your onboarding, you must deposit 1 ETH (specified in Wei) collateral together with the call.

Congratulations on becoming StakeWise Node Operator🎉.
Your validators will get ether assigned, and you can claim your operator rewards from [Farms Page](https://app.stakewise.io/farms).


### Operator CLI Environment Settings

| Variable                       | Description                                                                | Required | Default                                                                 |
|--------------------------------|----------------------------------------------------------------------------|----------|-------------------------------------------------------------------------|
| INFURA_IPFS_CLIENT_ENDPOINT    | The http://infura.io IPFS endpoint where the deposit data will be uploaded | No       | /dns/ipfs.infura.io/tcp/5001/https                                      |
| INFURA_IPFS_CLIENT_USERNAME    | The http://infura.io IPFS account username                                 | No       | -                                                                       |
| INFURA_IPFS_CLIENT_PASSWORD    | The http://infura.io IPFS account password                                 | No       | -                                                                       |
| LOCAL_IPFS_CLIENT_ENDPOINT     | The local IPFS endpoints from where the deposit data will be uploaded      | No       | -                                                                       |
| IPFS_EXTRA_FETCH_ENDPOINTS     | The extra IPFS endpoints from where the deposit data will be fetched       | No       | https://gateway.pinata.cloud,http://cloudflare-ipfs.com,https://ipfs.io |
| IPFS_PINATA_API_KEY            | The Pinata API key for uploading deposit data for the redundancy           | No       | -                                                                       |
| IPFS_PINATA_SECRET_KEY         | The Pinata Secret key for uploading deposit data for the redundancy        | No       | -                                                                       |
| VAULT_VALIDATORS_MOUNT_POINT   | The mount point in Hashicorp Vault for storing validator keys              | No       | validators                                                              |
