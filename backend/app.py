"""
TitleChain API - Main FastAPI Application

Self-Sovereign Identity + AI-Powered Title Search Platform

Endpoints:
- /identity/* - DID creation and resolution
- /title/* - Document upload and analysis
- /credential/* - VC issuance and verification
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from did_manager import DIDManager, create_property_did
from credential_issuer import CredentialIssuer, compute_credential_hash
from title_analyzer import TitleAnalyzer, MockTitleAnalyzer

# Import Search Agent and Blockchain routers
from agents.api_endpoints import router as agent_router, blockchain_router

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


# =============================================================================
# Application Setup
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    print("🚀 TitleChain API starting...")
    print(f"   Issuer DID: {ISSUER_DID}")
    print(f"   Using {'real' if USE_REAL_AI else 'mock'} AI analyzer")
    yield
    # Shutdown
    print("👋 TitleChain API shutting down...")


app = FastAPI(
    title="TitleChain API",
    description="Self-Sovereign Identity + AI-Powered Title Search",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Search Agent and Blockchain routers
app.include_router(agent_router)
app.include_router(blockchain_router)


# =============================================================================
# Service Initialization
# =============================================================================

# DID Manager
did_domain = os.getenv("DID_DOMAIN", "localhost:8000")
did_manager = DIDManager(domain=did_domain)

# Create platform issuer DID
issuer_result = did_manager.create_did("platform", did_type="org")
ISSUER_DID = issuer_result["did"]

# Credential Issuer
credential_issuer = CredentialIssuer(did_manager, ISSUER_DID)

# Title Analyzer (real or mock based on API key)
api_key = os.getenv("ANTHROPIC_API_KEY", "")
USE_REAL_AI = api_key and not api_key.startswith("sk-ant-xxx")

if USE_REAL_AI:
    title_analyzer = TitleAnalyzer(api_key)
else:
    title_analyzer = MockTitleAnalyzer()
    print("⚠️  No API key found - using mock analyzer")


# =============================================================================
# In-Memory Storage (Replace with database in production)
# =============================================================================

users: Dict[str, dict] = {}
properties: Dict[str, dict] = {}
analyses: Dict[str, dict] = {}


# =============================================================================
# Pydantic Models
# =============================================================================

class CreateIdentityRequest(BaseModel):
    """Request to create a new identity."""
    user_id: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = None
    email: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "alice123",
                "name": "Alice Smith",
                "email": "alice@example.com"
            }
        }


class CreateIdentityResponse(BaseModel):
    """Response after creating an identity."""
    did: str
    did_document: dict
    message: str


class CreatePropertyRequest(BaseModel):
    """Request to register a property."""
    property_id: str
    address: Optional[str] = None
    parcel_number: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None


class IssueCredentialRequest(BaseModel):
    """Request to issue a credential."""
    user_id: str
    analysis_id: str


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", tags=["Info"])
async def root():
    """API information and available endpoints."""
    return {
        "name": "TitleChain API",
        "version": "0.1.0",
        "description": "Self-Sovereign Identity + AI-Powered Title Search",
        "issuer_did": ISSUER_DID,
        "using_real_ai": USE_REAL_AI,
        "endpoints": {
            "identity": {
                "POST /identity/create": "Create a new DID",
                "GET /identity/{user_id}": "Get user's DID document"
            },
            "property": {
                "POST /property/register": "Register a property DID",
                "GET /property/{property_id}": "Get property DID document"
            },
            "title": {
                "POST /title/upload": "Upload deed for AI analysis",
                "GET /title/analyze/{id}": "Get analysis results"
            },
            "credential": {
                "POST /credential/issue": "Issue property credential",
                "GET /credential/verify/{id}": "Verify a credential",
                "GET /credential/{id}": "Get raw credential"
            },
            "search_agent": {
                "POST /agent/search": "Automated multi-county title search",
                "GET /agent/search/{id}": "Get search results",
                "GET /agent/counties": "List available counties",
                "GET /agent/coverage": "Coverage statistics"
            },
            "blockchain": {
                "POST /blockchain/anchor": "Anchor credential to Polygon",
                "GET /blockchain/verify/{hash}": "Verify blockchain anchor",
                "GET /blockchain/estimate-cost": "Estimate anchoring cost"
            }
        },
        "docs": "/docs",
        "features": {
            "agentic_ai": "Autonomous title search across 3,600+ US counties",
            "blockchain": "Polygon blockchain anchoring for immutable proof",
            "real_time": "Real-time data from Montgomery County, MD (+ more coming)",
            "ssi": "Self-sovereign identity with W3C DIDs and VCs"
        }
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# =============================================================================
# Identity Endpoints
# =============================================================================

@app.post(
    "/identity/create",
    response_model=CreateIdentityResponse,
    tags=["Identity"]
)
async def create_identity(request: CreateIdentityRequest):
    """
    Create a new self-sovereign identity (DID).
    
    A DID is like a digital passport you control. No company can revoke it.
    
    - **user_id**: Unique identifier (letters, numbers, underscores)
    - **name**: Optional display name
    - **email**: Optional email
    
    Returns the DID and DID Document. Store the DID securely!
    """
    if request.user_id in users:
        raise HTTPException(
            status_code=400,
            detail="User ID already exists. Choose a different ID."
        )
    
    # Create DID
    result = did_manager.create_did(request.user_id)
    
    # Store user info
    users[request.user_id] = {
        "did": result["did"],
        "name": request.name,
        "email": request.email,
        "credentials": [],
        "properties": []
    }
    
    return CreateIdentityResponse(
        did=result["did"],
        did_document=result["did_document"],
        message="Identity created successfully! This DID is cryptographically yours."
    )


@app.get("/identity/{user_id}", tags=["Identity"])
async def get_identity(user_id: str):
    """
    Get a user's DID document (public information).
    
    Anyone can resolve a DID to verify keys and service endpoints.
    """
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    did = users[user_id]["did"]
    did_doc = did_manager.resolve_did(did)
    
    return {
        "did": did,
        "did_document": did_doc,
        "credentials_count": len(users[user_id]["credentials"]),
        "properties_count": len(users[user_id]["properties"])
    }


# =============================================================================
# Property Endpoints
# =============================================================================

@app.post("/property/register", tags=["Property"])
async def register_property(request: CreatePropertyRequest):
    """
    Register a property with its own DID.
    
    Properties have separate DIDs from owners, allowing credentials
    to be issued about the property itself.
    """
    if request.property_id in properties:
        raise HTTPException(status_code=400, detail="Property already registered")
    
    # Create property DID
    result = create_property_did(did_manager, request.property_id)
    
    properties[request.property_id] = {
        "did": result["did"],
        "address": request.address,
        "parcel_number": request.parcel_number,
        "county": request.county,
        "state": request.state,
        "credentials": []
    }
    
    return {
        "property_did": result["did"],
        "did_document": result["did_document"],
        "message": "Property registered with its own DID"
    }


@app.get("/property/{property_id}", tags=["Property"])
async def get_property(property_id: str):
    """Get a property's DID and information."""
    if property_id not in properties:
        raise HTTPException(status_code=404, detail="Property not found")
    
    prop = properties[property_id]
    did_doc = did_manager.resolve_did(prop["did"])
    
    return {
        "property_id": property_id,
        "did": prop["did"],
        "did_document": did_doc,
        "address": prop["address"],
        "parcel_number": prop["parcel_number"],
        "credentials": prop["credentials"]
    }


# =============================================================================
# Title Analysis Endpoints
# =============================================================================

@app.post("/title/upload", tags=["Title"])
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Query(None, description="User ID for association")
):
    """
    Upload a deed document for AI analysis.
    
    Supported formats: PDF, PNG, JPG, TXT
    
    The AI will:
    1. Extract text (OCR if needed)
    2. Parse parties, property, dates, amounts
    3. Analyze for risk factors
    
    Returns an analysis_id to retrieve results.
    """
    # Validate file type
    allowed_types = ['.pdf', '.png', '.jpg', '.jpeg', '.txt', '.tiff']
    ext = os.path.splitext(file.filename or "")[1].lower()
    
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_types}"
        )
    
    # Read file content
    content = await file.read()
    
    # Generate analysis ID
    analysis_id = str(uuid.uuid4())
    
    try:
        # Run analysis
        result = await title_analyzer.analyze_document(content, file.filename or "document.txt")
        
        analyses[analysis_id] = {
            "status": "complete",
            "filename": file.filename,
            "user_id": user_id,
            "result": result
        }
        
        return {
            "analysis_id": analysis_id,
            "status": "complete",
            "message": "Document analyzed successfully",
            "preview": {
                "document_type": result["parsed_deed"].get("document_type"),
                "parties": result["parsed_deed"].get("parties"),
                "risk_score": result["analysis"].get("risk_score"),
                "risk_level": result["analysis"].get("risk_level")
            }
        }
        
    except Exception as e:
        analyses[analysis_id] = {
            "status": "error",
            "error": str(e)
        }
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/title/analyze/{analysis_id}", tags=["Title"])
async def get_analysis(analysis_id: str):
    """
    Get the full results of a title analysis.
    
    Returns parsed deed data, risk assessment, and recommendations.
    """
    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analyses[analysis_id]
    
    if analysis["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=analysis.get("error", "Analysis failed")
        )
    
    return {
        "analysis_id": analysis_id,
        "status": analysis["status"],
        "filename": analysis.get("filename"),
        "parsed_deed": analysis["result"]["parsed_deed"],
        "risk_analysis": analysis["result"]["analysis"],
        "documents_analyzed": analysis["result"]["documents_count"]
    }


# =============================================================================
# Credential Endpoints
# =============================================================================

@app.post("/credential/issue", tags=["Credentials"])
async def issue_credential(
    user_id: str = Query(..., description="User ID of property owner"),
    analysis_id: str = Query(..., description="Analysis ID to base credential on")
):
    """
    Issue a Verifiable Credential for property ownership.
    
    Creates a cryptographically signed proof that anyone can verify
    without contacting the issuer.
    
    The credential includes:
    - Property information
    - Owner information
    - Title analysis results
    - Risk assessment
    """
    # Validate user
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate analysis
    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = analyses[analysis_id]
    if analysis["status"] != "complete":
        raise HTTPException(status_code=400, detail="Analysis not complete")
    
    # Get user's DID
    subject_did = users[user_id]["did"]
    
    # Extract property data from analysis
    parsed = analysis["result"]["parsed_deed"]
    property_data = {
        "address": parsed.get("property", {}).get("address", ""),
        "legal_description": parsed.get("property", {}).get("legal_description", ""),
        "parcel_number": parsed.get("property", {}).get("parcel_number", ""),
        "county": parsed.get("property", {}).get("county", ""),
        "state": parsed.get("property", {}).get("state", "")
    }
    
    # Build title analysis for credential
    risk_analysis = analysis["result"]["analysis"]
    grantee = parsed.get("parties", {}).get("grantee", {})
    
    title_analysis = {
        "owner_did": subject_did,
        "owner_name": ", ".join(grantee.get("names", ["Unknown"])),
        "ownership_type": grantee.get("vesting", "fee_simple"),
        "chain_complete": True,  # Single doc = assume complete for MVP
        "ownership_chain": [{
            "owner": ", ".join(grantee.get("names", ["Unknown"])),
            "from_date": parsed.get("recording_info", {}).get("date"),
            "document_ref": f"Book {parsed.get('recording_info', {}).get('book')}, "
                          f"Page {parsed.get('recording_info', {}).get('page')}"
        }],
        "gaps": [],
        "is_marketable": risk_analysis.get("is_marketable", False),
        "issues": risk_analysis.get("marketability_issues", []),
        "encumbrances": [e.get("description", "") for e in risk_analysis.get("encumbrances", [])],
        "risk_score": risk_analysis.get("risk_score", 0.5),
        "risk_factors": risk_analysis.get("risk_factors", []),
        "documents_count": 1,
        "sources": ["county_recorder"]
    }
    
    # Issue the credential
    credential = credential_issuer.issue_property_credential(
        subject_did=subject_did,
        property_data=property_data,
        title_analysis=title_analysis
    )
    
    # Store reference
    users[user_id]["credentials"].append(credential["id"])
    
    # Compute hash for potential blockchain anchoring
    cred_hash = compute_credential_hash(credential)
    
    return {
        "credential": credential,
        "credential_hash": cred_hash,
        "verification_url": f"/credential/verify/{credential['id'].split(':')[-1]}",
        "message": "Credential issued successfully. Anyone can verify this cryptographically."
    }


@app.get("/credential/verify/{credential_id}", tags=["Credentials"])
async def verify_credential(credential_id: str):
    """
    Verify a credential's authenticity.
    
    Checks:
    - Cryptographic signature validity
    - Expiration status
    - Revocation status
    - Issuer trust
    
    Anyone can call this without special permissions.
    """
    full_id = f"urn:uuid:{credential_id}"
    
    if full_id not in credential_issuer.issued_credentials:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential = credential_issuer.issued_credentials[full_id]
    verification = credential_issuer.verify_credential(credential)
    
    return {
        "credential_id": full_id,
        "verification_result": verification,
        "credential_summary": {
            "type": credential.get("type", [])[-1],
            "subject": credential["credentialSubject"]["id"],
            "property": credential["credentialSubject"].get("propertyAddress"),
            "issued": credential["issuanceDate"],
            "expires": credential.get("expirationDate"),
            "risk_level": credential["credentialSubject"]["riskAssessment"]["level"],
            "is_marketable": credential["credentialSubject"]["titleStatus"]["isMarketable"]
        }
    }


@app.get("/credential/{credential_id}", tags=["Credentials"])
async def get_credential(credential_id: str):
    """Get the raw JSON-LD credential."""
    full_id = f"urn:uuid:{credential_id}"
    
    credential = credential_issuer.get_credential(full_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    return credential


@app.post("/credential/revoke/{credential_id}", tags=["Credentials"])
async def revoke_credential(credential_id: str):
    """
    Revoke a credential.
    
    Revoked credentials will fail verification.
    This is irreversible.
    """
    full_id = f"urn:uuid:{credential_id}"
    
    if full_id not in credential_issuer.issued_credentials:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    credential_issuer.revoke_credential(full_id)
    
    return {
        "credential_id": full_id,
        "status": "revoked",
        "message": "Credential has been revoked and will no longer verify"
    }


# =============================================================================
# Static Files (Frontend)
# =============================================================================

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")
    
    @app.get("/app", tags=["Frontend"])
    async def serve_frontend():
        """Serve the demo frontend application."""
        return FileResponse(str(frontend_path / "index.html"))


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                     TitleChain API                            ║
╠═══════════════════════════════════════════════════════════════╣
║  🚀 Server:    http://{host}:{port}                          
║  📚 API Docs:  http://{host}:{port}/docs                     
║  🌐 Frontend:  http://{host}:{port}/app                      
║  🔐 Issuer:    {ISSUER_DID[:50]}...
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run("app:app", host=host, port=port, reload=debug)
