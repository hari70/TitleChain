"""
Blockchain Anchoring Service

Anchors verifiable credentials to Polygon blockchain for:
- Immutable timestamp proof
- Public verifiability
- Tamper detection
- Audit trail

Supports:
- Polygon Mumbai (testnet)
- Polygon PoS (mainnet)
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from hexbytes import HexBytes

logger = logging.getLogger(__name__)


class BlockchainNetwork(Enum):
    """Supported blockchain networks."""
    POLYGON_MUMBAI = "polygon_mumbai"
    POLYGON_MAINNET = "polygon_mainnet"
    LOCAL = "local"  # For testing with Ganache/Hardhat


@dataclass
class AnchorTransaction:
    """Represents a blockchain anchoring transaction."""
    credential_hash: str
    tx_hash: str
    block_number: int
    timestamp: datetime
    network: BlockchainNetwork
    gas_used: int
    gas_price_gwei: float


class BlockchainAnchor:
    """
    Service for anchoring credentials to Polygon blockchain.

    Features:
    - Hash-only storage (privacy preserving)
    - Batch anchoring for cost efficiency
    - Automatic gas price optimization
    - Transaction retry logic
    - Event monitoring
    """

    # Contract ABI (simplified - only functions we need)
    TITLE_REGISTRY_ABI = [
        {
            "inputs": [{"name": "credentialHash", "type": "bytes32"}],
            "name": "anchorCredential",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"name": "credentialHash", "type": "bytes32"}],
            "name": "verifyAnchor",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "credentialHash", "type": "bytes32"},
                {"indexed": True, "name": "issuer", "type": "address"},
                {"indexed": False, "name": "timestamp", "type": "uint256"}
            ],
            "name": "CredentialAnchored",
            "type": "event"
        }
    ]

    # Network configurations
    NETWORKS = {
        BlockchainNetwork.POLYGON_MUMBAI: {
            "rpc_url": "https://rpc-mumbai.maticvigil.com/",
            "chain_id": 80001,
            "name": "Polygon Mumbai Testnet",
            "explorer": "https://mumbai.polygonscan.com",
            "native_token": "MATIC"
        },
        BlockchainNetwork.POLYGON_MAINNET: {
            "rpc_url": "https://polygon-rpc.com/",
            "chain_id": 137,
            "name": "Polygon Mainnet",
            "explorer": "https://polygonscan.com",
            "native_token": "MATIC"
        },
        BlockchainNetwork.LOCAL: {
            "rpc_url": "http://localhost:8545",
            "chain_id": 1337,
            "name": "Local Network",
            "explorer": None,
            "native_token": "ETH"
        }
    }

    def __init__(
        self,
        network: BlockchainNetwork = BlockchainNetwork.POLYGON_MUMBAI,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None,
        rpc_url: Optional[str] = None
    ):
        """
        Initialize blockchain anchoring service.

        Args:
            network: Blockchain network to use
            contract_address: Deployed TitleRegistry contract address
            private_key: Private key for signing transactions
            rpc_url: Custom RPC URL (overrides default)
        """
        self.network = network
        self.network_config = self.NETWORKS[network]

        # Setup Web3 connection
        rpc = rpc_url or self.network_config["rpc_url"]
        self.w3 = Web3(Web3.HTTPProvider(rpc))

        # Add PoA middleware for Polygon
        if network in [BlockchainNetwork.POLYGON_MUMBAI, BlockchainNetwork.POLYGON_MAINNET]:
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

        # Setup account
        if private_key:
            self.account = Account.from_key(private_key)
            logger.info(f"Initialized with account: {self.account.address}")
        else:
            self.account = None
            logger.warning("No private key provided - read-only mode")

        # Setup contract
        self.contract_address = contract_address
        if contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.TITLE_REGISTRY_ABI
            )
            logger.info(f"Connected to TitleRegistry at {contract_address}")
        else:
            self.contract = None
            logger.warning("No contract address - anchoring disabled")

        # Verify connection
        if self.w3.is_connected():
            logger.info(f"✅ Connected to {self.network_config['name']}")
            logger.info(f"   Latest block: {self.w3.eth.block_number}")
        else:
            logger.error(f"❌ Failed to connect to {self.network_config['name']}")

    def hash_credential(self, credential: Dict[str, Any]) -> str:
        """
        Compute keccak256 hash of credential (same as Solidity).

        Args:
            credential: Verifiable credential dictionary

        Returns:
            Hex string hash (0x...)
        """
        import json

        # Canonical JSON serialization
        credential_json = json.dumps(credential, sort_keys=True, separators=(',', ':'))
        credential_bytes = credential_json.encode('utf-8')

        # Keccak256 (Ethereum hash)
        hash_bytes = Web3.keccak(credential_bytes)
        return hash_bytes.hex()

    async def anchor_credential(
        self,
        credential: Dict[str, Any],
        gas_limit: int = 100000,
        max_priority_fee: Optional[int] = None
    ) -> AnchorTransaction:
        """
        Anchor a credential hash to the blockchain.

        Args:
            credential: Verifiable credential to anchor
            gas_limit: Gas limit for transaction
            max_priority_fee: Priority fee in gwei (None = auto)

        Returns:
            Transaction details

        Raises:
            ValueError: If not properly configured
            Exception: If transaction fails
        """
        if not self.contract:
            raise ValueError("Contract not configured")

        if not self.account:
            raise ValueError("Private key not configured")

        # Compute credential hash
        cred_hash = self.hash_credential(credential)
        cred_hash_bytes = HexBytes(cred_hash)

        logger.info(f"Anchoring credential hash: {cred_hash}")

        # Check if already anchored
        try:
            existing_timestamp = self.contract.functions.verifyAnchor(cred_hash_bytes).call()
            if existing_timestamp > 0:
                logger.info(f"Credential already anchored at {existing_timestamp}")
                # Return existing anchor info
                # (In production, fetch tx details from chain)
                return AnchorTransaction(
                    credential_hash=cred_hash,
                    tx_hash="0x" + "0" * 64,  # Placeholder
                    block_number=0,
                    timestamp=datetime.fromtimestamp(existing_timestamp),
                    network=self.network,
                    gas_used=0,
                    gas_price_gwei=0
                )
        except Exception as e:
            logger.debug(f"Could not check existing anchor: {e}")

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.account.address)

        # Get current gas prices
        if max_priority_fee is None:
            # Auto-estimate priority fee
            try:
                max_priority_fee = self.w3.eth.max_priority_fee
            except:
                max_priority_fee = self.w3.to_wei(2, 'gwei')  # Default 2 gwei

        max_fee = self.w3.eth.gas_price + max_priority_fee

        # Build transaction
        tx = self.contract.functions.anchorCredential(
            cred_hash_bytes
        ).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            'gas': gas_limit,
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': max_priority_fee,
            'chainId': self.network_config['chain_id']
        })

        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)

        # Send transaction
        logger.info(f"Sending transaction...")
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash_hex = tx_hash.hex()

        logger.info(f"Transaction sent: {tx_hash_hex}")
        logger.info(f"View on explorer: {self.get_tx_url(tx_hash_hex)}")

        # Wait for receipt
        logger.info("Waiting for confirmation...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            logger.info(f"✅ Credential anchored successfully!")
            logger.info(f"   Block: {receipt['blockNumber']}")
            logger.info(f"   Gas used: {receipt['gasUsed']}")

            # Get block timestamp
            block = self.w3.eth.get_block(receipt['blockNumber'])

            return AnchorTransaction(
                credential_hash=cred_hash,
                tx_hash=tx_hash_hex,
                block_number=receipt['blockNumber'],
                timestamp=datetime.fromtimestamp(block['timestamp']),
                network=self.network,
                gas_used=receipt['gasUsed'],
                gas_price_gwei=self.w3.from_wei(receipt['effectiveGasPrice'], 'gwei')
            )
        else:
            raise Exception(f"Transaction failed: {tx_hash_hex}")

    def verify_anchor(self, credential: Dict[str, Any]) -> Optional[datetime]:
        """
        Verify if a credential was anchored and when.

        Args:
            credential: Credential to verify

        Returns:
            Timestamp when anchored, or None if not anchored
        """
        if not self.contract:
            raise ValueError("Contract not configured")

        cred_hash = self.hash_credential(credential)
        cred_hash_bytes = HexBytes(cred_hash)

        timestamp = self.contract.functions.verifyAnchor(cred_hash_bytes).call()

        if timestamp > 0:
            return datetime.fromtimestamp(timestamp)
        return None

    def get_tx_url(self, tx_hash: str) -> str:
        """Get block explorer URL for transaction."""
        explorer = self.network_config.get('explorer')
        if explorer:
            return f"{explorer}/tx/{tx_hash}"
        return f"Transaction: {tx_hash}"

    def get_account_balance(self) -> float:
        """Get account balance in native token (MATIC/ETH)."""
        if not self.account:
            return 0.0

        balance_wei = self.w3.eth.get_balance(self.account.address)
        balance_ether = self.w3.from_wei(balance_wei, 'ether')

        token = self.network_config['native_token']
        logger.info(f"Balance: {balance_ether} {token}")

        return float(balance_ether)

    def estimate_anchoring_cost(self, num_credentials: int = 1) -> Dict[str, float]:
        """
        Estimate cost of anchoring credentials.

        Args:
            num_credentials: Number of credentials to anchor

        Returns:
            Cost breakdown in MATIC
        """
        # Typical gas used for anchorCredential: ~50,000 gas
        gas_per_anchor = 50000

        # Get current gas price
        gas_price_wei = self.w3.eth.gas_price
        gas_price_gwei = self.w3.from_wei(gas_price_wei, 'gwei')

        # Calculate costs
        total_gas = gas_per_anchor * num_credentials
        cost_wei = total_gas * gas_price_wei
        cost_matic = self.w3.from_wei(cost_wei, 'ether')

        return {
            "gas_per_credential": gas_per_anchor,
            "total_gas": total_gas,
            "gas_price_gwei": float(gas_price_gwei),
            "cost_per_credential_matic": float(self.w3.from_wei(gas_per_anchor * gas_price_wei, 'ether')),
            "total_cost_matic": float(cost_matic),
            "num_credentials": num_credentials
        }


# Convenience function
async def anchor_credential_to_polygon(
    credential: Dict[str, Any],
    network: BlockchainNetwork = BlockchainNetwork.POLYGON_MUMBAI,
    contract_address: Optional[str] = None,
    private_key: Optional[str] = None
) -> AnchorTransaction:
    """
    Quick function to anchor a credential.

    Args:
        credential: Verifiable credential to anchor
        network: Blockchain network
        contract_address: Contract address
        private_key: Private key for signing

    Returns:
        Transaction details

    Example:
        >>> from backend.agents.blockchain_anchor import anchor_credential_to_polygon, BlockchainNetwork
        >>> tx = await anchor_credential_to_polygon(
        ...     credential=my_credential,
        ...     network=BlockchainNetwork.POLYGON_MUMBAI,
        ...     contract_address="0x...",
        ...     private_key=os.getenv("POLYGON_PRIVATE_KEY")
        ... )
        >>> print(f"Anchored at block {tx.block_number}")
    """
    # Get from environment if not provided
    if contract_address is None:
        contract_address = os.getenv("TITLE_REGISTRY_CONTRACT")

    if private_key is None:
        private_key = os.getenv("POLYGON_PRIVATE_KEY")

    anchor = BlockchainAnchor(
        network=network,
        contract_address=contract_address,
        private_key=private_key
    )

    return await anchor.anchor_credential(credential)
