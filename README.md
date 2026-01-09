# TitleChain 🔐⛓️

**Self-Sovereign Identity + Agentic AI for Real Estate Title Search**

Transform the $16B title insurance industry by replacing manual processes with cryptographically verifiable, AI-automated title search.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 The Problem

| Current State | Impact |
|--------------|--------|
| 📁 3,600 fragmented county systems | No standardization |
| ⏱️ 4-6 hours per manual search | High labor costs |
| 📜 Paper-based chain of custody | Fraud vulnerability |
| 💰 $1,900 average title costs | 95% is process, 5% is risk |

## ✨ The Solution

```
┌─────────────────────────────────────────────────────────────┐
│                    TitleChain Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🤖 Agentic AI          →  Parallel agents search & analyze │
│  🔐 Self-Sovereign ID   →  Cryptographic ownership proof    │
│  ⛓️ Blockchain Anchor   →  Immutable audit trail            │
│  📊 Risk Scoring        →  ML-powered fraud detection       │
│                                                             │
│  Result: 2-3 minutes | $250 | Cryptographically verifiable │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/titlechain.git
cd titlechain

# Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the server
cd backend
python app.py

# Open in browser
# API Docs: http://localhost:8000/docs
# Demo UI:  http://localhost:8000/app
```

## 📁 Project Structure

```
titlechain/
├── CLAUDE.md                 # Context for Claude Code
├── backend/
│   ├── app.py                # FastAPI server
│   ├── did_manager.py        # DID operations
│   ├── credential_issuer.py  # Verifiable Credentials
│   ├── title_analyzer.py     # AI document parsing
│   └── agents/               # Agentic AI (to implement)
│       ├── orchestrator.py
│       ├── search_agent.py
│       ├── analysis_agent.py
│       ├── chain_builder.py
│       └── risk_agent.py
├── contracts/                # Solidity (to implement)
│   ├── TitleRegistry.sol
│   └── LienRegistry.sol
├── frontend/
│   ├── index.html
│   └── app.js
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TECHNOLOGY_DUE_DILIGENCE.md
│   └── LEARNING_AND_BUILD_GUIDE.md
├── data/sample_deeds/
└── tests/
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/identity/create` | POST | Create a new DID |
| `/identity/{user_id}` | GET | Resolve DID to document |
| `/title/upload` | POST | Upload deed for AI analysis |
| `/title/analyze/{id}` | GET | Get analysis results |
| `/credential/issue` | POST | Issue property credential |
| `/credential/verify/{id}` | GET | Verify a credential |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Consumer Layer     │  Title Agent | Lender | Buyer/Seller │
├─────────────────────────────────────────────────────────────┤
│  Agentic AI Layer   │  Search | Analysis | Risk | Cred     │
├─────────────────────────────────────────────────────────────┤
│  SSI Layer          │  DIDs | Verifiable Credentials       │
├─────────────────────────────────────────────────────────────┤
│  Blockchain Layer   │  Polygon | Smart Contracts           │
├─────────────────────────────────────────────────────────────┤
│  Data Layer         │  County APIs | Property Graph        │
└─────────────────────────────────────────────────────────────┘
```

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - Full system design with diagrams
- **[Technology Decisions](docs/TECHNOLOGY_DUE_DILIGENCE.md)** - Tech choices with pros/cons
- **[Learning Guide](docs/LEARNING_AND_BUILD_GUIDE.md)** - Video tutorials + hands-on path

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| AI/LLM | Anthropic Claude |
| Identity | W3C DID (did:web → did:polygonid) |
| Credentials | W3C Verifiable Credentials |
| Blockchain | Polygon PoS |
| Crypto | Ed25519 |

## 🗺️ Roadmap

- [x] **Phase 1**: Core MVP (DID, VC, basic AI parsing)
- [ ] **Phase 2**: Agentic AI layer (search, analysis agents)
- [ ] **Phase 3**: Chain builder + risk scoring
- [ ] **Phase 4**: Blockchain integration (Polygon)
- [ ] **Phase 5**: Production pilot

## 🤝 Contributing

This project is in active development. See [CLAUDE.md](CLAUDE.md) for development context.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Built with** FastAPI • Claude AI • W3C DID/VC • Polygon
