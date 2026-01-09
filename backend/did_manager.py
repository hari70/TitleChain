"""
DID Manager - Decentralized Identifier Operations

Implements did:web method for self-sovereign identity.
DIDs are like self-owned usernames that you control cryptographically.

Example DID: did:web:titlechain.com:users:alice
Resolves to: https://titlechain.com/users/alice/did.json
"""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import base64
import json
import hashlib
from typing import Dict, Optional
from datetime import datetime


class DIDManager:
    """
    Manages Decentralized Identifiers (DIDs) using the did:web method.
    
    did:web is the simplest DID method - just a JSON file on a web server.
    No blockchain required for basic operation.
    
    Attributes:
        domain: The domain for DID generation (e.g., "titlechain.com")
        keys: In-memory key storage (use secure storage in production)
    """
    
    def __init__(self, domain: str = "localhost:8000"):
        """
        Initialize DID Manager.
        
        Args:
            domain: Domain for DID generation. DIDs will be formatted as
                   did:web:{domain}:users:{user_id}
        """
        self.domain = domain
        self.keys: Dict[str, dict] = {}  # In production: use encrypted storage
        self.did_documents: Dict[str, dict] = {}
        
    def create_did(self, user_id: str, did_type: str = "users") -> dict:
        """
        Create a new DID with associated key pair.
        
        This is like creating a new digital identity that the user controls.
        The private key should be stored securely by the user.
        
        Args:
            user_id: Unique identifier for the user (e.g., "alice123")
            did_type: Type prefix for the DID (e.g., "users", "property", "org")
            
        Returns:
            dict containing:
                - did: The created DID string
                - did_document: The DID Document (public information)
                - private_key_base64: Base64 encoded private key (store securely!)
                
        Example:
            >>> manager = DIDManager("titlechain.com")
            >>> result = manager.create_did("alice")
            >>> result["did"]
            'did:web:titlechain.com:users:alice'
        """
        # Generate Ed25519 key pair (fast, secure, small keys)
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Create DID string
        did = f"did:web:{self.domain}:{did_type}:{user_id}"
        
        # Create DID Document (this is what gets "published")
        did_document = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/ed25519-2020/v1"
            ],
            "id": did,
            "created": datetime.utcnow().isoformat() + "Z",
            "authentication": [{
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": self._encode_public_key(public_key)
            }],
            "assertionMethod": [{
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": self._encode_public_key(public_key)
            }],
            "service": [{
                "id": f"{did}#titlechain",
                "type": "TitleChainService",
                "serviceEndpoint": f"https://{self.domain}/api"
            }]
        }
        
        # Store keys and document (in production: encrypted database)
        self.keys[did] = {
            "private": private_key,
            "public": public_key,
            "created": datetime.utcnow().isoformat()
        }
        self.did_documents[did] = did_document
        
        return {
            "did": did,
            "did_document": did_document,
            "private_key_base64": self._encode_private_key(private_key)
        }
    
    def resolve_did(self, did: str) -> dict:
        """
        Resolve a DID to its DID Document.
        
        In production with did:web, this would fetch from the web server.
        For now, we return from local storage.
        
        Args:
            did: The DID to resolve (e.g., "did:web:titlechain.com:users:alice")
            
        Returns:
            The DID Document containing public keys and service endpoints
            
        Raises:
            ValueError: If DID is not found
        """
        if did in self.did_documents:
            return self.did_documents[did]
        
        if did in self.keys:
            return self._generate_did_document(did)
            
        raise ValueError(f"DID not found: {did}")
    
    def sign_data(self, did: str, data: bytes) -> str:
        """
        Sign data using the private key associated with a DID.
        
        Used for creating proofs in Verifiable Credentials.
        
        Args:
            did: The DID whose key should sign
            data: Raw bytes to sign
            
        Returns:
            Base64-encoded signature
            
        Raises:
            ValueError: If no keys exist for the DID
        """
        if did not in self.keys:
            raise ValueError(f"No keys for DID: {did}")
        
        private_key = self.keys[did]["private"]
        signature = private_key.sign(data)
        return base64.urlsafe_b64encode(signature).decode()
    
    def verify_signature(self, did: str, data: bytes, signature: str) -> bool:
        """
        Verify a signature using the public key from a DID.
        
        Anyone can verify without knowing the private key.
        
        Args:
            did: The DID that allegedly signed
            data: The original data that was signed
            signature: Base64-encoded signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        if did not in self.keys:
            raise ValueError(f"No keys for DID: {did}")
            
        public_key = self.keys[did]["public"]
        sig_bytes = base64.urlsafe_b64decode(signature)
        
        try:
            public_key.verify(sig_bytes, data)
            return True
        except Exception:
            return False
    
    def get_signing_key_id(self, did: str) -> str:
        """Get the key ID for signing (used in proof creation)."""
        return f"{did}#key-1"
    
    def _encode_public_key(self, public_key) -> str:
        """
        Encode public key as multibase string.
        
        Multibase format: z + base58btc encoded bytes
        We use base64 for simplicity in this MVP.
        """
        raw_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        # 'z' prefix indicates base58btc, but we use base64 for simplicity
        return "z" + base64.b64encode(raw_bytes).decode()
    
    def _encode_private_key(self, private_key) -> str:
        """Encode private key for secure storage."""
        raw_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        return base64.b64encode(raw_bytes).decode()
    
    def _generate_did_document(self, did: str) -> dict:
        """Generate DID document from stored keys."""
        if did not in self.keys:
            raise ValueError(f"No keys for DID: {did}")
            
        public_key = self.keys[did]["public"]
        return {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": did,
            "authentication": [{
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": self._encode_public_key(public_key)
            }]
        }


# Factory function for creating property DIDs
def create_property_did(manager: DIDManager, property_id: str) -> dict:
    """
    Create a DID for a property.
    
    Properties have their own DIDs separate from owners.
    This allows credentials to be issued about the property itself.
    
    Args:
        manager: DID Manager instance
        property_id: Unique property identifier (e.g., parcel number)
        
    Returns:
        DID creation result
    """
    return manager.create_did(property_id, did_type="property")


def create_organization_did(manager: DIDManager, org_id: str) -> dict:
    """
    Create a DID for an organization (title company, bank, etc.)
    
    Organizations issue credentials (e.g., lien holders, title insurers).
    """
    return manager.create_did(org_id, did_type="org")
