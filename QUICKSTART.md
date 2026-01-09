# TitleChain - Quick Start Guide

## 🚀 The UI is Now Working!

Visit **http://localhost:8000/app** to see the full 3-step demo.

---

## 📋 Step-by-Step Walkthrough

### **Step 1: Create Your Digital Identity (DID)**

1. Go to http://localhost:8000/app
2. Enter a user ID (e.g., "alice123")
3. Optionally enter your name
4. Click **"Create My Identity"**

**What happens:**
- A unique Ed25519 key pair is generated (public + private)
- Your DID is created: `did:web:localhost:8000:person:alice123`
- The DID and keys are stored in the backend (in-memory for now)
- Step 2 automatically unlocks

**Where is it stored?**
- **Current**: In-memory Python dictionary (`users: Dict[str, dict]` in app.py line 103)
- **Production**: Would use PostgreSQL or decentralized storage (IPFS, Ceramic)

---

### **Step 2: Upload & Analyze a Deed**

1. Click **"Choose File"** and select a deed document
   - **Test file**: `/Users/harit/AI Projects/TitleChain/data/sample_deeds/sample_deed.txt`
   - Or upload any PDF/image of a deed
2. Click **"Upload & Analyze"**

**What happens:**
- File is sent to backend
- Claude AI analyzes the document:
  - Extracts parties (grantor → grantee)
  - Identifies property address
  - Calculates risk score
  - Detects liens, encumbrances
- Analysis is saved with a unique ID
- Step 3 automatically unlocks

**Where is it stored?**
- **Current**: In-memory dict (`analyses: Dict[str, dict]` in app.py line 105)
- **Production**: PostgreSQL + S3 for document images

---

### **Step 3: Issue Verifiable Credential**

1. Click **"Issue My Property Credential"**
2. A cryptographically signed credential is created

**What happens:**
- Your DID + property data + analysis → combined into a W3C Verifiable Credential
- TitleChain's private key **signs** the credential (Ed25519 signature)
- A **SHA-256 hash** is computed: `sha256(JSON.stringify(credential))`
- Credential is issued with:
  - Issuer: `did:web:localhost:8000:org:platform`
  - Subject: Your DID
  - Expiration date: 1 year
  - Cryptographic proof

**The Cryptographic Proof:**
```json
{
  "type": "Ed25519Signature2020",
  "created": "2026-01-09T...",
  "verificationMethod": "did:web:localhost:8000:org:platform#key-1",
  "proofPurpose": "assertionMethod",
  "proofValue": "z58DAdF...base58-encoded-signature"
}
```

**How Verification Works:**
1. Take the credential JSON (without the proof)
2. Hash it with SHA-256
3. Verify the signature using TitleChain's **public key** from its DID Document
4. If signature matches → credential is valid and untampered
5. If tampered → hash changes → signature verification fails

**Where is it stored?**
- **Current**: In-memory dict (`issued_credentials: Dict[str, dict]` in credential_issuer.py)
- **Production**: PostgreSQL + optional blockchain anchoring (Polygon)

---

## 🔐 Understanding the Crypto

### **Ed25519 Keys**
- **Private Key**: 256-bit secret, never shared, signs credentials
- **Public Key**: Published in DID Document, anyone can verify signatures
- **Algorithm**: Edwards-curve Digital Signature Algorithm (EdDSA)

### **SHA-256 Hash**
- One-way cryptographic hash function
- Input: Credential JSON → Output: 64-character hex string
- Used for:
  - Blockchain anchoring (stores hash, not full credential)
  - Integrity verification
  - Change detection (1 byte change = completely different hash)

### **Verifiable Credential Signature**
```
Sign(SHA256(credential_data), private_key) = signature
Verify(signature, SHA256(credential_data), public_key) = true/false
```

---

## 🧪 Test the Full Flow Right Now

### **Option 1: With Sample Deed (2 minutes)**

```bash
# 1. Open the app
open http://localhost:8000/app

# 2. Create identity
User ID: "testuser123"
Name: "Test User"
Click "Create My Identity"

# 3. Upload sample deed
Choose file: data/sample_deeds/sample_deed.txt
Click "Upload & Analyze"

# 4. Issue credential
Click "Issue My Property Credential"

# 5. Verify
Click "Verify Credential"
```

You'll see: ✅ All checks passed!

### **Option 2: Via API (Command Line)**

```bash
# Step 1: Create Identity
curl -X POST http://localhost:8000/identity/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": "api_test", "name": "API Test User"}'

# Response: {"did": "did:web:localhost:8000:person:api_test", ...}

# Step 2: Upload Deed
curl -X POST http://localhost:8000/title/upload?user_id=api_test \
  -F "file=@data/sample_deeds/sample_deed.txt"

# Response: {"analysis_id": "abc123...", ...}

# Step 3: Issue Credential
curl -X POST "http://localhost:8000/credential/issue?user_id=api_test&analysis_id=abc123"

# Response: {"credential": {...}, "credential_hash": "sha256:..."}

# Step 4: Verify (use credential ID from response)
curl http://localhost:8000/credential/verify/CREDENTIAL_ID
```

---

## 🔍 Where to Find Things

### **Identity Storage (DIDs)**
```python
# File: backend/app.py, line 103
users: Dict[str, dict] = {}

# Example entry:
users["alice123"] = {
    "did": "did:web:localhost:8000:person:alice123",
    "name": "Alice",
    "credentials": ["urn:uuid:abc123"],
    "properties": []
}
```

### **DID Document Storage**
```python
# File: backend/did_manager.py, line 27
self.did_documents: Dict[str, dict] = {}
self.private_keys: Dict[str, SigningKey] = {}

# DID Document contains:
{
  "@context": "https://www.w3.org/ns/did/v1",
  "id": "did:web:localhost:8000:person:alice123",
  "verificationMethod": [{
    "id": "did:web:...#key-1",
    "type": "Ed25519VerificationKey2020",
    "publicKeyMultibase": "z6Mk..." # Base58-encoded public key
  }]
}
```

### **Credential Storage**
```python
# File: backend/credential_issuer.py, line 30
self.issued_credentials: Dict[str, dict] = {}

# Credential structure (W3C VC):
{
  "@context": [...],
  "id": "urn:uuid:abc123",
  "type": ["VerifiableCredential", "PropertyTitleCredential"],
  "issuer": "did:web:localhost:8000:org:platform",
  "issuanceDate": "2026-01-09T...",
  "credentialSubject": {
    "id": "did:web:localhost:8000:person:alice123",
    "propertyAddress": "123 Main St",
    ...
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "proofValue": "z58D..." # Signature
  }
}
```

### **Hash Computation**
```python
# File: backend/credential_issuer.py, line 180
import hashlib
import json

def compute_credential_hash(credential: dict) -> str:
    """Compute SHA-256 hash for blockchain anchoring."""
    # Remove proof before hashing (proof signs the content, not itself)
    cred_copy = {k: v for k, v in credential.items() if k != 'proof'}

    # Canonical JSON (sorted keys for consistent hashing)
    canonical = json.dumps(cred_copy, sort_keys=True)

    # SHA-256 hash
    hash_bytes = hashlib.sha256(canonical.encode()).digest()
    return hash_bytes.hex()
```

---

## 🎯 Summary

**The UI is fully functional now!** The JavaScript was not loading before (wrong path), but now it works perfectly.

### **What You Can Do:**
1. ✅ Create DIDs (digital identities)
2. ✅ Upload deed documents
3. ✅ Get AI analysis (via Claude)
4. ✅ Issue verifiable credentials
5. ✅ Verify credentials cryptographically
6. ✅ Copy credentials as JSON
7. ✅ See SHA-256 hashes for blockchain anchoring

### **What's Stored Where:**
- **DIDs**: In-memory dict (backend/app.py)
- **Private Keys**: In-memory dict (backend/did_manager.py)
- **Credentials**: In-memory dict (backend/credential_issuer.py)
- **Analysis Results**: In-memory dict (backend/app.py)

### **In Production:**
- DIDs → PostgreSQL + DID resolver endpoint
- Private Keys → Hardware Security Module (HSM) or AWS KMS
- Credentials → PostgreSQL + blockchain anchoring on Polygon
- Analysis → PostgreSQL + S3 for document images

---

## 🐛 Troubleshooting

**Buttons are still disabled:**
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Clear browser cache
- Check browser console (F12) for JavaScript errors

**"API not available" error:**
- Make sure backend is running: `cd backend && python app.py`
- Check http://localhost:8000/health returns `{"status": "healthy"}`

**Upload fails:**
- Check file size < 10MB
- Supported formats: PDF, PNG, JPG, TXT
- Make sure ANTHROPIC_API_KEY is set in .env

---

**Ready to test?** Go to http://localhost:8000/app and try it now! All 3 steps should work perfectly.
