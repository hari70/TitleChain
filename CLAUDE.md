# CLAUDE.md - Project Context for Claude Code

## Project Overview

**TitleChain** is a blockchain-based self-sovereign identity (SSI) platform for real estate title search and verification. It combines Agentic AI for automation with decentralized identity for trust.

### Vision
Replace the traditional title search process (4-6 hours, $1,900) with an automated system (2-3 minutes, $250) using:
- **Agentic AI**: Autonomous agents that search, analyze, and assess title documents
- **SSI/DIDs**: Decentralized identifiers for properties, people, and organizations
- **Verifiable Credentials**: Cryptographically signed proofs of ownership and liens
- **Blockchain**: Immutable audit trail and timestamp anchoring (Polygon)

## Architecture Summary

```
Consumer Layer      →  Portals for title agents, lenders, buyers/sellers
Agentic AI Layer    →  Search, Analysis, Chain Builder, Risk, Credential agents
SSI/Identity Layer  →  DIDs (did:web), Verifiable Credentials, Wallets
Blockchain Layer    →  Credential anchoring, Smart contracts, Revocation
Data Layer          →  County connectors, Property graph DB, Document store
```

## Current Implementation Status

### ✅ Completed (MVP Foundation)
- `backend/did_manager.py` - DID creation and resolution (did:web)
- `backend/credential_issuer.py` - W3C Verifiable Credential issuance
- `backend/title_analyzer.py` - AI-powered document parsing with Claude
- `backend/app.py` - FastAPI server with all endpoints
- `frontend/` - Demo UI for the 3-step flow
- Sample deed document for testing

### 🔲 To Be Implemented
1. **Search Agent** - County connector framework, parallel document retrieval
2. **Chain Builder Agent** - Graph-based ownership chain construction
3. **Risk Agent** - Pattern detection, fraud scoring, ML models
4. **Orchestrator Agent** - Workflow planning and agent coordination
5. **Smart Contracts** - TitleRegistry.sol, LienRegistry.sol on Polygon
6. **Blockchain Integration** - Credential anchoring, event monitoring

## Tech Stack

| Layer | Technology | Status |
|-------|------------|--------|
| Backend | FastAPI (Python 3.11+) | ✅ |
| AI/LLM | Anthropic Claude API | ✅ |
| Identity | did:web (W3C DID) | ✅ |
| Credentials | W3C VC with JWT | ✅ |
| Crypto | Ed25519 | ✅ |
| Blockchain | Polygon PoS | 🔲 |
| Frontend | HTML/JS + Tailwind | ✅ |
| Database | PostgreSQL (planned) | 🔲 |

## Key Files to Understand

```
docs/
├── ARCHITECTURE.md          # Full system architecture with diagrams
├── TECHNOLOGY_DUE_DILIGENCE.md  # Tech choices with pros/cons
└── LEARNING_AND_BUILD_GUIDE.md  # Learning path + implementation guide

backend/
├── app.py                   # Main FastAPI application
├── did_manager.py           # DID operations (create, resolve, sign)
├── credential_issuer.py     # VC issuance and verification
└── title_analyzer.py        # LLM-powered document analysis

contracts/                   # Solidity smart contracts (to implement)
├── TitleRegistry.sol
└── LienRegistry.sol
```

## Development Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add ANTHROPIC_API_KEY

# Run backend
cd backend
python app.py
# Or: uvicorn app:app --reload --port 8000

# Access
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Frontend: http://localhost:8000/app
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/identity/create` | POST | Create new DID |
| `/identity/{user_id}` | GET | Get DID document |
| `/title/upload` | POST | Upload deed for AI analysis |
| `/title/analyze/{id}` | GET | Get analysis results |
| `/credential/issue` | POST | Issue property credential |
| `/credential/verify/{id}` | GET | Verify credential |

## Coding Conventions

- **Python**: Follow PEP 8, use type hints
- **Async**: Use async/await for I/O operations
- **Error Handling**: Raise HTTPException with clear messages
- **Logging**: Use structured logging (to be added)
- **Testing**: Pytest (to be added)

## Domain Concepts

### DID (Decentralized Identifier)
Self-owned identifier: `did:web:titlechain.com:users:alice`
- User controls private key
- DID Document contains public key for verification
- No central authority can revoke

### Verifiable Credential (VC)
Signed claim about a subject:
```json
{
  "type": ["VerifiableCredential", "PropertyTitleCredential"],
  "issuer": "did:web:titlechain.com",
  "credentialSubject": {
    "id": "did:web:titlechain.com:property:123main",
    "owner": "did:web:titlechain.com:person:alice"
  },
  "proof": { "type": "Ed25519Signature2020", ... }
}
```

### Chain of Title
Sequence of ownership transfers, each linked to previous:
```
Genesis → Owner1 → Owner2 → Owner3 (current)
```
Each transfer is a VC with `previousCredential` pointer.

## Priority Implementation Order

1. **Search Agent** (Week 1-2)
   - Create county connector base class
   - Implement LA County adapter (has API)
   - Add document download and queuing

2. **Analysis Agent Enhancement** (Week 2-3)
   - Improve OCR (Google Document AI)
   - Refine extraction prompts
   - Add confidence scoring

3. **Chain Builder** (Week 3-4)
   - Name matching (fuzzy + ML)
   - Graph construction (NetworkX)
   - Gap detection

4. **Risk Agent** (Week 4-5)
   - Rule engine
   - Pattern detection
   - Risk scoring

5. **Orchestrator** (Week 5-6)
   - Task planning
   - Parallel execution
   - Result aggregation

6. **Blockchain** (Week 6-8)
   - Deploy contracts to Polygon Mumbai
   - Integrate anchoring
   - Add verification

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-xxx     # Required for AI analysis
OPENAI_API_KEY=sk-xxx            # Optional alternative
DID_DOMAIN=localhost:8000        # Domain for DIDs
DATABASE_URL=                    # PostgreSQL (future)
POLYGON_RPC_URL=                 # Polygon node (future)
POLYGON_PRIVATE_KEY=             # Deployer key (future)
```

## Testing Strategy

- **Unit**: Test each agent independently
- **Integration**: Test agent orchestration
- **E2E**: Full title search flow
- **Sample Data**: Use `data/sample_deeds/` for consistent testing

## Resources

- [W3C DID Spec](https://www.w3.org/TR/did-core/)
- [W3C VC Spec](https://www.w3.org/TR/vc-data-model/)
- [Polygon Docs](https://docs.polygon.technology/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

## Notes for Claude Code

When implementing new features:
1. Check `docs/ARCHITECTURE.md` for the full design
2. Follow existing patterns in `backend/` modules
3. Use async where appropriate
4. Add type hints
5. Update this CLAUDE.md with new components

The founder (Hari) prefers:
- Learning through video tutorials and hands-on coding
- Simple analogies for complex concepts
- Visual explanations where possible
- Practical implementation over theoretical depth
