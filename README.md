# Operator CLI

Operators CLI is responsible for generating the validators keys,
deposit data required to register them and uploading the keys to the Hashicorp Vault.

## Usage

### Step 1. Installation

See [releases page](https://github.com/stakewise/cli/releases) to download and decompress the corresponding binary files.

### Step 2. Generate DAO proposal

Run the following command to generate DAO proposal:

```bash
./operator-cli generate-proposal
```

**NB! You must store the generated mnemonic in a secure cold storage.
It will allow you to restore the keys in case the Vault will get corrupted or lost.**

### Step 3. Submit DAO proposal

Create a post about joining operators set at [StakeWise Forum](https://vote.stakewise.io).
In your post you must include the `Specification` section that was generated in step 2.

### Step 4. Deploy ETH2 infrastructure

If the proposal from step 3 is approved by the DAO, follow the instructions [here](https://github.com/stakewise/helm-charts/tree/main/charts/operator#readme)
to deploy the ETH2 staking infrastructure.

### Step 5. Sync keys to the Vault

You must **use the same mnemonic** as generated in step 1.
Also, **using the same mnemonic for multiple vaults will result into validator slashing**.

Run the following command to sync new validator keys to the vault:

```bash
./operator-cli sync-vault
```

After uploading the keys, restart the validators that got new keys added.

### Step 6. Commit Operator

Once you're 100% ready for ether assignments to the validators, commit your operator:

- Go to the [Operators smart contract](https://etherscan.io/address/<address>#writeProxyContract)
- Click on `Connect to Web3` button and connect your wallet. The address must match the one used during proposal generation.
- Call `commitOperator` function. If that's your onboarding, you must deposit 1 ETH collateral together with the call.

Congratulations on becoming StakeWise Node Operator🎉.
Your validators will get ether assigned, and you can claim your operator rewards from [Farms Page](https://app.stakewise.io/farms).


### Operator CLI Environment Settings

| Variable                     | Description                                                         | Required | Default                                                                 |
|------------------------------|---------------------------------------------------------------------|----------|-------------------------------------------------------------------------|
| WITHDRAWAL_CREDENTIALS       | The withdrawal credentials of the validators used in deposit data   | No       | 0x0100000000000000000000002296e122c1a20fca3cac3371357bdad3be0df079      |
| IPFS_PIN_ENDPOINTS           | The IPFS endpoint where the deposit data will be uploaded           | No       | /dns/ipfs.infura.io/tcp/5001/https                                      |
| IPFS_FETCH_ENDPOINTS         | The IPFS endpoints from where the deposit data will be fetched      | No       | https://gateway.pinata.cloud,http://cloudflare-ipfs.com,https://ipfs.io |
| IPFS_PINATA_API_KEY          | The Pinata API key for uploading deposit data for the redundancy    | No       | -                                                                       |
| IPFS_PINATA_SECRET_KEY       | The Pinata Secret key for uploading deposit data for the redundancy | No       | -                                                                       |
| VAULT_VALIDATORS_MOUNT_POINT | The mount point in Hashicorp Vault for storing validator keys       | No       | validators                                                              |
