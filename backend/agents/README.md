# TitleChain Search Agent & Blockchain Anchoring

Autonomous AI agent system for nationwide title search with blockchain anchoring.

## Features

### 🤖 Agentic AI Search
- **Autonomous Operation**: Agent plans and executes multi-county searches
- **Parallel Processing**: Searches up to 5 counties simultaneously
- **Intelligent Caching**: Results cached for 1 hour
- **Automatic Failover**: Falls back to mock data if county system unavailable
- **Progress Tracking**: Real-time status updates

### 🌎 Nationwide Scale
- **Architecture**: Designed for 3,600+ US counties
- **Extensible**: Easy to add new counties
- **Registry System**: Central configuration for all counties
- **Factory Pattern**: Automatic connector instantiation
- **Rate Limiting**: Respects county system limits

### ⛓️ Blockchain Anchoring
- **Network**: Polygon PoS (Mumbai testnet & Mainnet)
- **Privacy**: Only hashes stored on-chain
- **Cost**: ~$0.0001-0.001 per credential
- **Verifiable**: Public verification without issuer
- **Immutable**: Tamper-proof timestamp proof

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Search Agent                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. County Registry (3,600+ counties)                       │
│     └─> Factory creates appropriate connector               │
│                                                             │
│  2. Connector Layer                                         │
│     ├─> Montgomery County MD (Web Scraper)                  │
│     ├─> Los Angeles County CA (API - TODO)                  │
│     └─> Mock Connector (Fallback)                           │
│                                                             │
│  3. Search Orchestrator                                     │
│     ├─> Parallel execution (max 5 concurrent)               │
│     ├─> Rate limiting                                       │
│     ├─> Result caching                                      │
│     └─> Error handling & retry                              │
│                                                             │
│  4. Document Cache                                          │
│     └─> In-memory (1 hour TTL)                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Blockchain Anchoring Service                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Credential Hashing (Keccak256)                          │
│  2. Transaction Building (EIP-1559)                         │
│  3. Gas Price Optimization                                  │
│  4. On-chain Anchoring (Polygon)                            │
│  5. Event Monitoring                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Current County Coverage

### ✅ Implemented
- **Montgomery County, MD** - Web scraper for MDLandRec system
  - Population: 1,062,061
  - Method: Web scraping with authentication
  - Cost: Free (requires email registration)

### 🔲 Planned (High Priority)
- **Los Angeles County, CA** - Public API available
- **Cook County, IL** - Public data portal
- **Harris County, TX** - Online records
- **Maricopa County, AZ** - Public access

## API Usage

### Starting a Title Search

```bash
curl -X POST http://localhost:8000/agent/search \
  -H "Content-Type: application/json" \
  -d '{
    "parcel_number": "12-345-6789",
    "counties": [
      {"county": "Montgomery", "state": "MD"}
    ],
    "years_back": 60,
    "credentials": {
      "montgomery_md": {
        "email": "your-email@example.com",
        "password": "your-password"
      }
    }
  }'
```

Response:
```json
{
  "search_id": "abc123...",
  "status": "completed",
  "started_at": "2026-01-08T20:00:00Z",
  "completed_at": "2026-01-08T20:00:03Z",
  "counties_searched": 1,
  "counties_succeeded": 1,
  "total_documents": 15
}
```

### Getting Search Results

```bash
curl http://localhost:8000/agent/search/abc123...
```

### List Available Counties

```bash
curl http://localhost:8000/agent/counties?state=MD
```

### Check Coverage Stats

```bash
curl http://localhost:8000/agent/coverage
```

Response:
```json
{
  "total_counties": 3,
  "counties_with_online_access": 3,
  "counties_with_api": 0,
  "counties_with_scraper": 1,
  "mock_only": 2,
  "states_covered": 3,
  "coverage_percentage": 0.10
}
```

## Blockchain Anchoring

### Anchor a Credential

```bash
curl -X POST http://localhost:8000/blockchain/anchor \
  -H "Content-Type: application/json" \
  -d '{
    "credential": { ... },
    "network": "polygon_mumbai"
  }'
```

Response:
```json
{
  "success": true,
  "credential_hash": "0x1234...",
  "tx_hash": "0xabcd...",
  "block_number": 12345678,
  "timestamp": "2026-01-08T20:00:00Z",
  "explorer_url": "https://mumbai.polygonscan.com/tx/0xabcd...",
  "gas_used": 48523,
  "cost_matic": 0.000024
}
```

### Estimate Anchoring Cost

```bash
curl "http://localhost:8000/blockchain/estimate-cost?num_credentials=100"
```

## Adding New Counties

### 1. Create Connector Class

```python
# backend/agents/my_county_connector.py
from .county_connector import CountyConnectorBase, LandRecordDocument

class MyCountyConnector(CountyConnectorBase):
    async def authenticate(self) -> bool:
        # Implement authentication
        pass

    async def search_by_parcel(self, parcel_number: str):
        # Implement parcel search
        pass

    # ... implement other required methods
```

### 2. Register Connector

```python
# In county_registry.py _register_builtin_connectors()
from .my_county_connector import MyCountyConnector
self.register_connector_class("my_county", MyCountyConnector)
```

### 3. Add County Configuration

```python
# In county_registry.py _load_default_configs()
self.add_county(CountyConfig(
    county="My County",
    state="CA",
    fips_code="06123",
    connectors=[
        {
            "connector_type": "my_county",
            "priority": ConnectorPriority.PRIMARY.value,
            "access_method": AccessMethod.REST_API.value,
            "requires_auth": True,
            "base_url": "https://mycounty.gov/api"
        }
    ],
    has_online_access=True,
    website_url="https://mycounty.gov",
    last_updated="2026-01-08"
))
```

## Environment Configuration

Add to `.env`:

```bash
# Montgomery County MD
MONTGOMERY_MD_EMAIL=your-email@example.com
MONTGOMERY_MD_PASSWORD=your-password

# Blockchain (Polygon Mumbai Testnet)
POLYGON_RPC_URL=https://rpc-mumbai.maticvigil.com/
TITLE_REGISTRY_CONTRACT=0x... # Deployed contract address
POLYGON_PRIVATE_KEY=0x...     # Private key for signing

# For mainnet (production):
# POLYGON_RPC_URL=https://polygon-rpc.com/
# POLYGON_PRIVATE_KEY=0x...
```

## Smart Contract Deployment

### 1. Install Hardhat/Foundry

```bash
npm install --save-dev hardhat
# or
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### 2. Deploy to Mumbai

```bash
cd contracts
npx hardhat run scripts/deploy.js --network polygonMumbai
```

### 3. Update .env

```bash
TITLE_REGISTRY_CONTRACT=0xYourDeployedContractAddress
```

## Testing

### Unit Tests

```bash
cd backend
pytest tests/test_search_agent.py -v
```

### Integration Test

```python
from agents.search_agent import search_title

# Test with mock data
result = await search_title(
    parcel_number="12-345-6789",
    counties=[("Test County", "MD")]
)

assert result.status == SearchStatus.COMPLETED
assert len(result.all_documents) > 0
```

### Blockchain Test

```python
from agents.blockchain_anchor import BlockchainAnchor, BlockchainNetwork

anchor = BlockchainAnchor(
    network=BlockchainNetwork.POLYGON_MUMBAI,
    contract_address=os.getenv("TITLE_REGISTRY_CONTRACT"),
    private_key=os.getenv("POLYGON_PRIVATE_KEY")
)

# Check balance
balance = anchor.get_account_balance()
print(f"Balance: {balance} MATIC")

# Estimate cost
cost = anchor.estimate_anchoring_cost(num_credentials=1)
print(f"Cost per credential: {cost['cost_per_credential_matic']} MATIC")
```

## Performance

### Search Agent
- **Concurrent Counties**: 5 (configurable)
- **Cache TTL**: 1 hour
- **Average Search Time**: 2-5 seconds per county
- **Throughput**: ~12 counties/minute

### Blockchain
- **Anchoring Time**: 2-15 seconds (Mumbai), 10-60 seconds (Mainnet)
- **Gas Used**: ~50,000 gas per credential
- **Cost**: $0.0001-0.001 USD per credential (at $1 MATIC)
- **Batch Support**: Coming soon

## Roadmap

### Phase 1 (Current) ✅
- [x] County registry system
- [x] Montgomery County MD connector
- [x] Search Agent orchestrator
- [x] Polygon blockchain anchoring
- [x] API endpoints

### Phase 2 (Next 2 weeks)
- [ ] Add 10 more high-priority counties
- [ ] Batch blockchain anchoring
- [ ] PostgreSQL persistence
- [ ] Chain Builder Agent integration
- [ ] Risk scoring integration

### Phase 3 (Month 2)
- [ ] 50-county coverage
- [ ] Real-time webhook notifications
- [ ] Advanced caching (Redis)
- [ ] Multi-chain support (Ethereum, Arbitrum)
- [ ] API rate limiting & quotas

### Phase 4 (Month 3)
- [ ] 500+ county coverage
- [ ] ML-powered name matching
- [ ] Automated county connector generation
- [ ] SaaS pricing tiers
- [ ] Production deployment

## Security Considerations

1. **Credentials**: County credentials stored encrypted (TODO)
2. **Private Keys**: Never commit private keys - use environment variables
3. **Rate Limiting**: Respect county system rate limits
4. **Caching**: Sensitive data cached in memory only (1 hour)
5. **Blockchain**: Use testnet for development, mainnet for production only

## Support

- **Documentation**: See `/docs/ARCHITECTURE.md`
- **Issues**: https://github.com/hari70/TitleChain/issues
- **Email**: Contact via GitHub

## License

MIT - See LICENSE file

---

**Built with** FastAPI • Claude AI • Web3.py • BeautifulSoup • Polygon
