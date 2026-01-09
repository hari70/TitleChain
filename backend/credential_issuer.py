"""
Credential Issuer - Verifiable Credential Operations

Issues W3C Verifiable Credentials for property ownership, liens, and transfers.
Credentials are cryptographically signed proofs that anyone can verify.

Think of it like a notarized certificate that verifies itself mathematically.
"""

from datetime import datetime, timedelta
import json
import hashlib
import uuid
from typing import Dict, List, Optional, Any

from did_manager import DIDManager


class CredentialIssuer:
    """
    Issues and verifies W3C Verifiable Credentials.
    
    A Verifiable Credential is a tamper-evident claim about a subject
    that can be cryptographically verified without contacting the issuer.
    
    Attributes:
        did_manager: DID Manager for signing operations
        issuer_did: DID of this issuing authority
        issued_credentials: Storage for issued credentials
        revoked: Set of revoked credential IDs
    """
    
    def __init__(self, did_manager: DIDManager, issuer_did: str):
        """
        Initialize Credential Issuer.
        
        Args:
            did_manager: DID Manager instance for cryptographic operations
            issuer_did: The DID that will sign credentials
        """
        self.did_manager = did_manager
        self.issuer_did = issuer_did
        self.issued_credentials: Dict[str, dict] = {}
        self.revoked: set = set()
        
    def issue_property_credential(
        self,
        subject_did: str,
        property_data: dict,
        title_analysis: dict,
        expiration_days: int = 365
    ) -> dict:
        """
        Issue a Property Title Verifiable Credential.
        
        This is the main credential that proves property ownership
        and title status.
        
        Args:
            subject_did: DID of the property (not the owner)
            property_data: Property information (address, legal description)
            title_analysis: AI analysis results (chain, risk, liens)
            expiration_days: How long until credential expires
            
        Returns:
            Signed Verifiable Credential
        """
        credential_id = f"urn:uuid:{uuid.uuid4()}"
        
        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://schema.org/",
                {
                    "PropertyTitleCredential": "https://titlechain.com/schemas/PropertyTitleCredential",
                    "propertyAddress": "https://schema.org/address",
                    "legalDescription": "https://titlechain.com/schemas/legalDescription",
                    "chainOfTitle": "https://titlechain.com/schemas/chainOfTitle",
                    "titleStatus": "https://titlechain.com/schemas/titleStatus",
                    "riskAssessment": "https://titlechain.com/schemas/riskAssessment",
                    "currentOwner": "https://titlechain.com/schemas/currentOwner"
                }
            ],
            "id": credential_id,
            "type": ["VerifiableCredential", "PropertyTitleCredential"],
            "issuer": {
                "id": self.issuer_did,
                "name": "TitleChain Verification Service"
            },
            "issuanceDate": datetime.utcnow().isoformat() + "Z",
            "expirationDate": (datetime.utcnow() + timedelta(days=expiration_days)).isoformat() + "Z",
            "credentialSubject": {
                "id": subject_did,
                "type": "RealProperty",
                "propertyAddress": property_data.get("address", ""),
                "legalDescription": property_data.get("legal_description", ""),
                "parcelNumber": property_data.get("parcel_number", ""),
                "currentOwner": {
                    "id": title_analysis.get("owner_did", ""),
                    "name": title_analysis.get("owner_name", ""),
                    "ownershipType": title_analysis.get("ownership_type", "fee_simple")
                },
                "chainOfTitle": {
                    "isComplete": title_analysis.get("chain_complete", False),
                    "ownershipHistory": title_analysis.get("ownership_chain", []),
                    "gaps": title_analysis.get("gaps", []),
                    "searchDepth": title_analysis.get("search_depth", "60 years")
                },
                "titleStatus": {
                    "isMarketable": title_analysis.get("is_marketable", False),
                    "issues": title_analysis.get("issues", []),
                    "encumbrances": title_analysis.get("encumbrances", [])
                },
                "riskAssessment": {
                    "score": title_analysis.get("risk_score", 0),
                    "level": self._risk_level(title_analysis.get("risk_score", 0)),
                    "factors": title_analysis.get("risk_factors", [])
                },
                "verificationMetadata": {
                    "verificationDate": datetime.utcnow().isoformat() + "Z",
                    "documentsAnalyzed": title_analysis.get("documents_count", 0),
                    "sourcesChecked": title_analysis.get("sources", [])
                }
            },
            "credentialStatus": {
                "id": f"https://titlechain.com/api/revocation/{credential_id.split(':')[-1]}",
                "type": "RevocationList2020"
            }
        }
        
        # Sign the credential
        proof = self._create_proof(credential)
        credential["proof"] = proof
        
        # Store credential
        self.issued_credentials[credential_id] = credential
        
        return credential
    
    def issue_lien_credential(
        self,
        property_did: str,
        holder_did: str,
        lien_data: dict
    ) -> dict:
        """
        Issue a Lien Verifiable Credential.
        
        Issued by lien holders (banks, IRS, etc.) to record encumbrances.
        
        Args:
            property_did: DID of the property
            holder_did: DID of the lien holder
            lien_data: Lien information
            
        Returns:
            Signed Lien Credential
        """
        credential_id = f"urn:uuid:{uuid.uuid4()}"
        
        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                {
                    "LienCredential": "https://titlechain.com/schemas/LienCredential"
                }
            ],
            "id": credential_id,
            "type": ["VerifiableCredential", "LienCredential"],
            "issuer": {
                "id": holder_did,
                "name": lien_data.get("holder_name", "")
            },
            "issuanceDate": datetime.utcnow().isoformat() + "Z",
            "credentialSubject": {
                "id": f"{credential_id}#lien",
                "type": lien_data.get("lien_type", "Lien"),
                "property": property_did,
                "holder": holder_did,
                "originalAmount": lien_data.get("original_amount"),
                "currentBalance": lien_data.get("current_balance"),
                "priority": lien_data.get("priority", 1),
                "recordedDate": lien_data.get("recorded_date"),
                "recordingInfo": lien_data.get("recording_info", {}),
                "status": lien_data.get("status", "active"),
                "maturityDate": lien_data.get("maturity_date")
            }
        }
        
        proof = self._create_proof(credential)
        credential["proof"] = proof
        
        self.issued_credentials[credential_id] = credential
        return credential
    
    def issue_transfer_credential(
        self,
        property_did: str,
        from_owner_did: str,
        to_owner_did: str,
        transfer_data: dict,
        previous_credential_id: Optional[str] = None
    ) -> dict:
        """
        Issue an Ownership Transfer Verifiable Credential.
        
        Records a change in ownership, linking to the previous credential
        to create a cryptographic chain of title.
        
        Args:
            property_did: DID of the property
            from_owner_did: DID of the seller/transferor
            to_owner_did: DID of the buyer/transferee
            transfer_data: Transfer details
            previous_credential_id: ID of the previous ownership credential
            
        Returns:
            Signed Transfer Credential
        """
        credential_id = f"urn:uuid:{uuid.uuid4()}"
        
        credential = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                {
                    "OwnershipTransferCredential": "https://titlechain.com/schemas/OwnershipTransferCredential"
                }
            ],
            "id": credential_id,
            "type": ["VerifiableCredential", "OwnershipTransferCredential"],
            "issuer": {
                "id": self.issuer_did,
                "name": "TitleChain Verification Service"
            },
            "issuanceDate": datetime.utcnow().isoformat() + "Z",
            "credentialSubject": {
                "id": f"{credential_id}#transfer",
                "type": "RealPropertyTransfer",
                "property": property_did,
                "transferor": {
                    "id": from_owner_did,
                    "name": transfer_data.get("from_name", "")
                },
                "transferee": {
                    "id": to_owner_did,
                    "name": transfer_data.get("to_name", "")
                },
                "instrument": {
                    "type": transfer_data.get("deed_type", "warranty_deed"),
                    "consideration": transfer_data.get("consideration"),
                    "executedDate": transfer_data.get("executed_date"),
                    "recordedDate": transfer_data.get("recorded_date")
                },
                "recording": transfer_data.get("recording_info", {}),
                "previousCredential": previous_credential_id
            }
        }
        
        proof = self._create_proof(credential)
        credential["proof"] = proof
        
        self.issued_credentials[credential_id] = credential
        return credential
    
    def verify_credential(self, credential: dict) -> dict:
        """
        Verify a credential's authenticity and validity.
        
        Checks:
        1. Signature validity (cryptographic)
        2. Expiration status
        3. Revocation status
        4. Issuer trust
        
        Args:
            credential: The credential to verify
            
        Returns:
            Verification result with checks and any errors
        """
        errors = []
        checks = {
            "signature": False,
            "not_expired": False,
            "not_revoked": False,
            "issuer_trusted": False
        }
        
        # Check expiration
        try:
            exp_str = credential.get("expirationDate", "")
            if exp_str:
                exp_date = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
                checks["not_expired"] = datetime.now(exp_date.tzinfo) < exp_date
                if not checks["not_expired"]:
                    errors.append("Credential has expired")
            else:
                checks["not_expired"] = True  # No expiration = valid
        except Exception as e:
            errors.append(f"Invalid expiration date: {e}")
        
        # Check revocation
        credential_id = credential.get("id", "")
        checks["not_revoked"] = credential_id not in self.revoked
        if not checks["not_revoked"]:
            errors.append("Credential has been revoked")
        
        # Check issuer
        issuer = credential.get("issuer", {})
        issuer_id = issuer.get("id", "") if isinstance(issuer, dict) else issuer
        checks["issuer_trusted"] = issuer_id == self.issuer_did
        if not checks["issuer_trusted"]:
            errors.append(f"Issuer not trusted: {issuer_id}")
        
        # Verify signature
        try:
            proof = credential.get("proof", {})
            checks["signature"] = self._verify_proof(credential, proof)
            if not checks["signature"]:
                errors.append("Invalid signature")
        except Exception as e:
            errors.append(f"Signature verification failed: {str(e)}")
        
        return {
            "valid": all(checks.values()),
            "checks": checks,
            "errors": errors
        }
    
    def revoke_credential(self, credential_id: str) -> bool:
        """
        Revoke a credential by adding it to the revocation registry.
        
        Revoked credentials will fail verification.
        
        Args:
            credential_id: The credential ID to revoke
            
        Returns:
            True if revocation was successful
        """
        self.revoked.add(credential_id)
        return True
    
    def get_credential(self, credential_id: str) -> Optional[dict]:
        """Get a credential by ID."""
        return self.issued_credentials.get(credential_id)
    
    def _create_proof(self, credential: dict) -> dict:
        """
        Create a cryptographic proof (signature) for a credential.
        
        Uses Ed25519 signature over the canonical JSON representation.
        """
        # Remove any existing proof for signing
        cred_copy = {k: v for k, v in credential.items() if k != "proof"}
        
        # Canonicalize (deterministic JSON serialization)
        canonical = json.dumps(cred_copy, sort_keys=True, separators=(',', ':'))
        message_hash = hashlib.sha256(canonical.encode()).digest()
        
        # Sign with issuer's key
        signature = self.did_manager.sign_data(self.issuer_did, message_hash)
        
        return {
            "type": "Ed25519Signature2020",
            "created": datetime.utcnow().isoformat() + "Z",
            "verificationMethod": f"{self.issuer_did}#key-1",
            "proofPurpose": "assertionMethod",
            "proofValue": signature
        }
    
    def _verify_proof(self, credential: dict, proof: dict) -> bool:
        """Verify a credential's proof signature."""
        # Remove proof for verification
        cred_copy = {k: v for k, v in credential.items() if k != "proof"}
        
        # Canonicalize
        canonical = json.dumps(cred_copy, sort_keys=True, separators=(',', ':'))
        message_hash = hashlib.sha256(canonical.encode()).digest()
        
        # Get verifier DID from proof
        verifier_did = proof.get("verificationMethod", "").split("#")[0]
        
        return self.did_manager.verify_signature(
            verifier_did,
            message_hash,
            proof.get("proofValue", "")
        )
    
    def _risk_level(self, score: float) -> str:
        """Convert numeric risk score to level."""
        if score < 0.3:
            return "LOW"
        elif score < 0.7:
            return "MEDIUM"
        else:
            return "HIGH"


def compute_credential_hash(credential: dict) -> str:
    """
    Compute hash of a credential for blockchain anchoring.
    
    This hash can be stored on-chain as proof of existence
    without revealing the credential contents.
    """
    # Remove proof before hashing (proof is added after issuance)
    cred_copy = {k: v for k, v in credential.items() if k != "proof"}
    canonical = json.dumps(cred_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()
