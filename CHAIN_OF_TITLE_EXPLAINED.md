# Chain of Title & Credential Supersession - Explained

## Real-World Scenario: Divorce and Property Transfer

### Timeline
```
2015-06-15: John & Jane Smith buy property together
            → Deed recorded: Book 12345, Page 678
            → Both are joint owners (tenants by entirety)

2020-03-22: Divorce finalized
            → Jane quitclaims her interest to John
            → New deed recorded: Book 23456, Page 891
            → John becomes sole owner

2026-01-09: Jane shows up with old 2015 deed claiming ownership
            → How do we prove she no longer owns it?
```

---

## Solution 1: Chain of Title Credentials

Each deed gets its own credential, linked in a chain:

### Credential #1 (2015 Purchase)
```json
{
  "@context": "https://www.w3.org/2018/credentials/v1",
  "id": "urn:uuid:abc-2015-purchase",
  "type": ["VerifiableCredential", "PropertyTitleCredential"],
  "issuer": "did:web:titlechain.com:issuer",
  "issuanceDate": "2015-06-15T14:30:00Z",

  "credentialSubject": {
    "id": "did:web:titlechain.com:property:123main",
    "propertyAddress": "123 Main St, Montgomery County, MD",
    "parcelNumber": "03-12345678",

    "currentOwner": [
      {
        "id": "did:web:titlechain.com:person:john-smith",
        "name": "John Michael Smith"
      },
      {
        "id": "did:web:titlechain.com:person:jane-smith",
        "name": "Jane Elizabeth Smith"
      }
    ],

    "ownershipType": "tenants_by_entirety",
    "ownershipPercentage": {"John Smith": 50, "Jane Smith": 50},

    "documentReference": {
      "county": "Montgomery",
      "state": "MD",
      "book": "12345",
      "page": "678",
      "recordingDate": "2015-06-15",
      "instrumentNumber": "2015-067890",
      "documentType": "warranty_deed"
    },

    "chainPosition": {
      "sequenceNumber": 1,
      "previousCredential": null,  // First in chain
      "nextCredential": null  // Will be updated when superseded
    }
  },

  "credentialStatus": {
    "id": "https://titlechain.com/api/revocation/abc-2015-purchase",
    "type": "RevocationList2020",
    "revoked": false  // Active at time of issuance
  }
}
```

### Credential #2 (2020 Quitclaim)
```json
{
  "@context": "https://www.w3.org/2018/credentials/v1",
  "id": "urn:uuid:def-2020-quitclaim",
  "type": ["VerifiableCredential", "PropertyTitleCredential"],
  "issuer": "did:web:titlechain.com:issuer",
  "issuanceDate": "2020-03-22T10:15:00Z",

  "credentialSubject": {
    "id": "did:web:titlechain.com:property:123main",
    "propertyAddress": "123 Main St, Montgomery County, MD",
    "parcelNumber": "03-12345678",

    "currentOwner": [
      {
        "id": "did:web:titlechain.com:person:john-smith",
        "name": "John Michael Smith"
      }
      // Jane is no longer an owner
    ],

    "ownershipType": "fee_simple",
    "ownershipPercentage": {"John Smith": 100},

    "grantor": [
      {
        "id": "did:web:titlechain.com:person:jane-smith",
        "name": "Jane Elizabeth Smith",
        "consideration": "$1.00 and other valuable consideration"
      }
    ],

    "grantee": [
      {
        "id": "did:web:titlechain.com:person:john-smith",
        "name": "John Michael Smith"
      }
    ],

    "documentReference": {
      "county": "Montgomery",
      "state": "MD",
      "book": "23456",
      "page": "891",
      "recordingDate": "2020-03-22",
      "instrumentNumber": "2020-089123",
      "documentType": "quitclaim_deed"
    },

    "chainPosition": {
      "sequenceNumber": 2,
      "previousCredential": "urn:uuid:abc-2015-purchase",  // Links to previous
      "supersedes": "urn:uuid:abc-2015-purchase",  // Explicitly supersedes
      "nextCredential": null  // Current end of chain
    }
  },

  "credentialStatus": {
    "id": "https://titlechain.com/api/revocation/def-2020-quitclaim",
    "type": "RevocationList2020",
    "revoked": false  // Currently active
  }
}
```

---

## Solution 2: Automatic Revocation

When Credential #2 is issued, Credential #1 is **automatically revoked**:

### Revocation Entry
```json
{
  "revocationList": {
    "id": "https://titlechain.com/api/revocation/list/2020-03",
    "issuer": "did:web:titlechain.com:issuer",
    "revokedCredentials": [
      {
        "credentialId": "urn:uuid:abc-2015-purchase",
        "revokedAt": "2020-03-22T10:15:00Z",
        "reason": "superseded",
        "supersededBy": "urn:uuid:def-2020-quitclaim",
        "blockchainProof": {
          "network": "Polygon",
          "transactionHash": "0x789abc...",
          "blockNumber": 12345678,
          "timestamp": "2020-03-22T10:16:30Z"
        }
      }
    ]
  }
}
```

### Blockchain Anchoring
```javascript
// Both credential hashes are stored on Polygon blockchain

// Credential #1 hash (revoked)
{
  "credentialHash": "0xabc123def456...",
  "timestamp": "2015-06-15T14:31:00Z",
  "blockNumber": 8901234,
  "status": "REVOKED",  // Updated when revoked
  "revokedAt": "2020-03-22T10:16:30Z"
}

// Credential #2 hash (active)
{
  "credentialHash": "0xdef456abc789...",
  "timestamp": "2020-03-22T10:16:30Z",
  "blockNumber": 12345678,
  "status": "ACTIVE"
}

// Smart contract on Polygon stores:
mapping(bytes32 => CredentialStatus) public credentials;
mapping(bytes32 => bytes32) public supersededBy;  // old hash => new hash
```

---

## Solution 3: Verification API

Anyone can verify which credential is current:

### API Call 1: Verify Old Deed (2015)
```bash
curl http://localhost:8000/credential/verify/abc-2015-purchase
```

**Response:**
```json
{
  "valid": false,
  "credentialId": "urn:uuid:abc-2015-purchase",
  "checks": {
    "signature_valid": true,
    "issuer_trusted": true,
    "not_expired": true,
    "not_revoked": false  // ❌ REVOKED!
  },
  "errors": [
    "Credential has been revoked on 2020-03-22",
    "Superseded by urn:uuid:def-2020-quitclaim",
    "See: https://landrec.msa.maryland.gov Book 23456, Page 891"
  ],
  "revocationDetails": {
    "revokedAt": "2020-03-22T10:15:00Z",
    "reason": "superseded",
    "supersededBy": "urn:uuid:def-2020-quitclaim",
    "blockchainProof": "0x789abc..."
  },
  "currentCredential": {
    "id": "urn:uuid:def-2020-quitclaim",
    "currentOwner": ["John Michael Smith"]
  }
}
```

### API Call 2: Verify New Deed (2020)
```bash
curl http://localhost:8000/credential/verify/def-2020-quitclaim
```

**Response:**
```json
{
  "valid": true,
  "credentialId": "urn:uuid:def-2020-quitclaim",
  "checks": {
    "signature_valid": true,
    "issuer_trusted": true,
    "not_expired": true,
    "not_revoked": true  // ✅ VALID!
  },
  "errors": [],
  "credentialSubject": {
    "propertyAddress": "123 Main St",
    "currentOwner": ["John Michael Smith"],
    "recordingDate": "2020-03-22"
  },
  "chainOfTitle": [
    {
      "sequenceNumber": 1,
      "date": "2015-06-15",
      "owners": ["John Michael Smith", "Jane Elizabeth Smith"],
      "status": "REVOKED"
    },
    {
      "sequenceNumber": 2,
      "date": "2020-03-22",
      "owners": ["John Michael Smith"],
      "status": "ACTIVE"  // ← Current
    }
  ]
}
```

---

## Solution 4: Query Current Owner

### API: Get Current Owner
```bash
curl http://localhost:8000/property/current-owner?address=123+Main+St
```

**Response:**
```json
{
  "propertyAddress": "123 Main St, Montgomery County, MD",
  "parcelNumber": "03-12345678",
  "currentOwner": {
    "names": ["John Michael Smith"],
    "ownershipType": "fee_simple",
    "since": "2020-03-22"
  },
  "activeCredential": "urn:uuid:def-2020-quitclaim",
  "chainOfTitle": [
    {
      "date": "2015-06-15",
      "owners": ["John & Jane Smith"],
      "credential": "urn:uuid:abc-2015-purchase",
      "status": "REVOKED",
      "supersededBy": "2020-03-22 quitclaim"
    },
    {
      "date": "2020-03-22",
      "owners": ["John Smith"],
      "credential": "urn:uuid:def-2020-quitclaim",
      "status": "ACTIVE"
    }
  ],
  "verificationSources": [
    "TitleChain credential verification",
    "Montgomery County land records (landrec.msa.maryland.gov)",
    "Polygon blockchain anchoring (tx: 0x789abc...)"
  ]
}
```

---

## Why This Prevents Fraud

### When Jane Shows Up with Old Deed:

1. **She presents**: 2015 deed + credential `abc-2015-purchase`

2. **Buyer/Bank verifies**:
   ```bash
   curl http://localhost:8000/credential/verify/abc-2015-purchase
   ```

3. **System responds**:
   ```
   ❌ REVOKED on 2020-03-22
   ❌ Superseded by quitclaim deed (Book 23456, Page 891)
   ✅ Current owner: John Smith (sole owner)
   ✅ Blockchain proof: 0x789abc...
   ```

4. **Three Independent Sources Confirm**:
   - **TitleChain credentials**: Old credential revoked, new one active
   - **County records**: Quitclaim deed recorded in 2020
   - **Blockchain**: Immutable timestamp proof on Polygon

5. **Jane's claim is rejected** - She cannot forge or hide the 2020 quitclaim because:
   - It's recorded at the county (public record)
   - It's in the blockchain (immutable)
   - The credential is cryptographically signed

---

## The Key Innovation: Temporal Truth

Traditional title search answers: **"Who owns this NOW?"**

TitleChain credentials answer: **"Who owned this AT TIME X, and has that changed?"**

Each credential is a **historical attestation**:
- 2015 credential: "On June 15, 2015, John & Jane owned the property" ← TRUE (historically)
- 2020 credential: "On March 22, 2020, Jane transferred to John" ← TRUE (supersedes previous)

Both statements are true! But only the 2020 credential is **currently active**.

---

## Implementation in TitleChain

### Current Code (Partial)
```python
# File: backend/credential_issuer.py

def revoke_credential(self, credential_id: str, reason: str = "superseded"):
    """Revoke a credential (e.g., when superseded by new deed)."""
    self.revoked.add(credential_id)
    # In production: update blockchain, publish revocation list

def verify_credential(self, credential: dict):
    """Verify credential and check revocation status."""
    credential_id = credential.get("id")

    # Check if revoked
    if credential_id in self.revoked:
        return {
            "valid": False,
            "errors": ["Credential has been revoked"]
        }

    # Check signature, expiration, etc.
    # ...
```

### What Needs to Be Added:

1. **Chain Linking**: `previousCredential` and `supersedes` fields
2. **Blockchain Revocation**: Update Polygon smart contract when revoking
3. **Query API**: Get current owner by traversing chain
4. **Revocation Registry**: Public list of revoked credentials

---

## Summary

**Your original question**: How do we prevent wife from using old deed?

**Answer**:
1. Each deed = separate credential
2. New deed **revokes** old credential
3. Revocation is **publicly verifiable** (blockchain + county records)
4. Anyone can check which credential is current
5. Old credential fails verification with error: "Superseded by [new deed]"

**The credential doesn't expire**, but it can be **revoked** when facts change (new owner). This is the correct SSI approach!

---

**Next Steps**: Want me to implement the full chain-of-title linking and revocation system?
