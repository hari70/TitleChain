"""
FastAPI endpoints for Search Agent and Blockchain Anchoring

New endpoints:
- POST /agent/search - Execute title search across counties
- GET /agent/search/{search_id} - Get search results
- GET /agent/counties - List available counties
- POST /blockchain/anchor - Anchor credential to blockchain
- GET /blockchain/verify/{hash} - Verify credential anchoring
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .search_agent import (
    SearchAgent,
    TitleSearchRequest,
    TitleSearchResult,
    SearchStatus
)
from .county_connector import DocumentType
from .county_registry import get_global_registry
from .blockchain_anchor import (
    BlockchainAnchor,
    BlockchainNetwork,
    anchor_credential_to_polygon
)

import logging
import os

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/agent", tags=["Search Agent"])
blockchain_router = APIRouter(prefix="/blockchain", tags=["Blockchain"])

# In-memory storage for search results (TODO: Replace with Redis/DB)
search_results_store: Dict[str, TitleSearchResult] = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class CountyInput(BaseModel):
    """County and state tuple."""
    county: str = Field(..., example="Montgomery")
    state: str = Field(..., min_length=2, max_length=2, example="MD")


class TitleSearchRequestModel(BaseModel):
    """Request for title search."""
    parcel_number: Optional[str] = Field(None, example="12-345-6789")
    property_address: Optional[str] = Field(None, example="123 Main St")
    current_owner: Optional[str] = Field(None, example="John Smith")

    counties: List[CountyInput] = Field(
        ...,
        min_items=1,
        example=[{"county": "Montgomery", "state": "MD"}]
    )

    years_back: int = Field(60, ge=1, le=100, example=60)
    include_mortgages: bool = True
    include_liens: bool = True
    include_easements: bool = True
    retrieve_images: bool = False
    max_documents: int = Field(1000, ge=1, le=10000)

    # Credentials for county systems
    credentials: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        example={
            "montgomery_md": {
                "email": "user@example.com",
                "password": "password123"
            }
        }
    )


class SearchStatusResponse(BaseModel):
    """Status of a search request."""
    search_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    counties_searched: int = 0
    counties_succeeded: int = 0
    counties_failed: int = 0
    total_documents: int = 0


class CountyInfo(BaseModel):
    """Information about a county's land records access."""
    county: str
    state: str
    fips_code: str
    has_online_access: bool
    requires_subscription: bool
    website_url: Optional[str] = None
    population: Optional[int] = None
    notes: Optional[str] = None


class AnchorCredentialRequest(BaseModel):
    """Request to anchor a credential."""
    credential: Dict[str, Any] = Field(..., description="Verifiable Credential to anchor")
    network: str = Field("polygon_mumbai", example="polygon_mumbai")


class AnchorResponse(BaseModel):
    """Response from anchoring."""
    success: bool
    credential_hash: str
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: Optional[datetime] = None
    explorer_url: Optional[str] = None
    gas_used: Optional[int] = None
    cost_matic: Optional[float] = None


# =============================================================================
# Search Agent Endpoints
# =============================================================================

@router.post("/search", response_model=SearchStatusResponse)
async def start_title_search(
    request: TitleSearchRequestModel,
    background_tasks: BackgroundTasks
):
    """
    Start an automated title search across multiple counties.

    This endpoint uses the Search Agent to:
    1. Connect to county land record systems
    2. Search for documents related to the property
    3. Retrieve ownership history
    4. Cache results for fast access

    Returns immediately with a search_id. Use GET /agent/search/{search_id}
    to check progress and retrieve results.
    """
    try:
        # Convert request to internal format
        search_request = TitleSearchRequest(
            parcel_number=request.parcel_number,
            property_address=request.property_address,
            current_owner=request.current_owner,
            counties=[(c.county, c.state) for c in request.counties],
            years_back=request.years_back,
            include_mortgages=request.include_mortgages,
            include_liens=request.include_liens,
            include_easements=request.include_easements,
            retrieve_images=request.retrieve_images,
            max_documents=request.max_documents
        )

        # Create search agent
        agent = SearchAgent(credentials=request.credentials or {})

        # Start search in background
        async def run_search():
            try:
                result = await agent.search(search_request)
                search_results_store[result.request_id] = result
                logger.info(f"Search {result.request_id} completed")
            except Exception as e:
                logger.error(f"Search failed: {e}")
            finally:
                await agent.close()

        # Create placeholder result
        result = TitleSearchResult(
            request_id="temp",
            status=SearchStatus.PENDING,
            started_at=datetime.utcnow()
        )

        # Run search
        result = await agent.search(search_request)
        await agent.close()

        # Store result
        search_results_store[result.request_id] = result

        return SearchStatusResponse(
            search_id=result.request_id,
            status=result.status.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            counties_searched=result.counties_searched,
            counties_succeeded=result.counties_succeeded,
            counties_failed=result.counties_failed,
            total_documents=result.total_documents
        )

    except Exception as e:
        logger.error(f"Failed to start search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/{search_id}")
async def get_search_results(search_id: str):
    """
    Get results of a title search.

    Returns the current status and all documents found so far.
    """
    if search_id not in search_results_store:
        raise HTTPException(status_code=404, detail="Search not found")

    result = search_results_store[search_id]

    return {
        "search_id": search_id,
        "status": result.status.value,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "counties_searched": result.counties_searched,
        "counties_succeeded": result.counties_succeeded,
        "counties_failed": result.counties_failed,
        "total_documents": result.total_documents,
        "documents": [
            {
                "document_id": doc.document_id,
                "county": doc.county,
                "state": doc.state,
                "document_type": doc.document_type.value,
                "recording_date": doc.recording_date,
                "book": doc.book,
                "page": doc.page,
                "instrument_number": doc.instrument_number,
                "grantor": doc.grantor,
                "grantee": doc.grantee,
                "parcel_number": doc.parcel_number,
                "property_address": doc.property_address,
                "consideration": doc.consideration,
            }
            for doc in result.all_documents
        ],
        "errors": result.errors
    }


@router.get("/counties", response_model=List[CountyInfo])
async def list_counties(
    state: Optional[str] = None,
    has_online_access: Optional[bool] = None
):
    """
    List all available counties in the system.

    Filter by state code or online access availability.
    """
    registry = get_global_registry()
    counties = registry.list_counties(state=state, has_online_access=has_online_access)

    return [
        CountyInfo(
            county=c.county,
            state=c.state,
            fips_code=c.fips_code,
            has_online_access=c.has_online_access,
            requires_subscription=c.requires_subscription,
            website_url=c.website_url,
            population=c.population,
            notes=c.notes
        )
        for c in counties
    ]


@router.get("/coverage")
async def get_coverage_stats():
    """
    Get statistics about county coverage.

    Shows how many counties are available, which have APIs, etc.
    """
    registry = get_global_registry()
    return registry.get_coverage_stats()


# =============================================================================
# Blockchain Endpoints
# =============================================================================

@blockchain_router.post("/anchor", response_model=AnchorResponse)
async def anchor_credential(request: AnchorCredentialRequest):
    """
    Anchor a verifiable credential to the blockchain.

    This creates an immutable timestamp proof on Polygon blockchain,
    enabling public verification without revealing credential contents.

    Cost: ~0.0001-0.001 MATIC per credential (depending on gas prices)
    """
    try:
        # Map network string to enum
        network_map = {
            "polygon_mumbai": BlockchainNetwork.POLYGON_MUMBAI,
            "polygon_mainnet": BlockchainNetwork.POLYGON_MAINNET,
            "local": BlockchainNetwork.LOCAL
        }

        network = network_map.get(request.network, BlockchainNetwork.POLYGON_MUMBAI)

        # Get configuration from environment
        contract_address = os.getenv("TITLE_REGISTRY_CONTRACT")
        private_key = os.getenv("POLYGON_PRIVATE_KEY")

        if not contract_address:
            raise HTTPException(
                status_code=503,
                detail="Blockchain anchoring not configured - missing contract address"
            )

        if not private_key:
            raise HTTPException(
                status_code=503,
                detail="Blockchain anchoring not configured - missing private key"
            )

        # Anchor credential
        tx = await anchor_credential_to_polygon(
            credential=request.credential,
            network=network,
            contract_address=contract_address,
            private_key=private_key
        )

        return AnchorResponse(
            success=True,
            credential_hash=tx.credential_hash,
            tx_hash=tx.tx_hash,
            block_number=tx.block_number,
            timestamp=tx.timestamp,
            explorer_url=f"https://mumbai.polygonscan.com/tx/{tx.tx_hash}" if network == BlockchainNetwork.POLYGON_MUMBAI else None,
            gas_used=tx.gas_used,
            cost_matic=tx.gas_used * tx.gas_price_gwei / 1e9
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anchoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@blockchain_router.get("/verify/{credential_hash}")
async def verify_anchor(credential_hash: str):
    """
    Verify if a credential was anchored and when.

    Args:
        credential_hash: The credential hash (with or without 0x prefix)

    Returns:
        Anchoring information if found
    """
    try:
        contract_address = os.getenv("TITLE_REGISTRY_CONTRACT")

        if not contract_address:
            raise HTTPException(
                status_code=503,
                detail="Blockchain verification not configured"
            )

        # Create read-only anchor instance
        anchor = BlockchainAnchor(
            network=BlockchainNetwork.POLYGON_MUMBAI,
            contract_address=contract_address
        )

        # For verification, we need the actual credential
        # This endpoint is simplified - in production, store hash mappings
        raise HTTPException(
            status_code=501,
            detail="Direct hash verification not yet implemented - use /credential/verify endpoint"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@blockchain_router.get("/estimate-cost")
async def estimate_cost(num_credentials: int = 1):
    """
    Estimate the cost of anchoring credentials to blockchain.

    Args:
        num_credentials: Number of credentials to estimate for

    Returns:
        Cost breakdown in MATIC
    """
    try:
        anchor = BlockchainAnchor(
            network=BlockchainNetwork.POLYGON_MUMBAI
        )

        cost = anchor.estimate_anchoring_cost(num_credentials)

        return {
            "network": "Polygon Mumbai",
            "num_credentials": num_credentials,
            "gas_per_credential": cost["gas_per_credential"],
            "total_gas": cost["total_gas"],
            "current_gas_price_gwei": cost["gas_price_gwei"],
            "cost_per_credential_matic": cost["cost_per_credential_matic"],
            "total_cost_matic": cost["total_cost_matic"],
            "note": "Prices are estimates and may vary based on network congestion"
        }

    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
