"""
Title Analyzer - AI-Powered Document Analysis

Uses LLMs (Claude) to extract structured data from deed documents
and analyze title chains for risks.

This is where the magic happens - converting messy PDFs into
machine-verifiable data.
"""

import anthropic
import json
import re
import io
from typing import Optional, List, Dict, Any
from PIL import Image
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    """Types of real estate documents."""
    WARRANTY_DEED = "warranty_deed"
    QUITCLAIM_DEED = "quitclaim_deed"
    GRANT_DEED = "grant_deed"
    TRUST_DEED = "trust_deed"
    MORTGAGE = "mortgage"
    LIEN = "lien"
    RELEASE = "release"
    OTHER = "other"


@dataclass
class ExtractionResult:
    """Result of document extraction."""
    document_type: str
    recording_info: dict
    parties: dict
    property: dict
    consideration: dict
    encumbrances: List[str]
    confidence: float
    notes: List[str]
    raw_text: str


class TitleAnalyzer:
    """
    AI-powered title document analyzer.
    
    Uses Claude to:
    1. Extract structured data from deed documents
    2. Build chain of title from multiple documents
    3. Assess risk factors
    4. Generate reports
    """
    
    def __init__(self, anthropic_api_key: str):
        """
        Initialize analyzer with Anthropic API key.
        
        Args:
            anthropic_api_key: API key from console.anthropic.com
        """
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"  # Good balance of speed/quality
        
    async def analyze_document(
        self, 
        file_content: bytes, 
        filename: str
    ) -> Dict[str, Any]:
        """
        Main entry point: analyze a deed document.
        
        Pipeline:
        1. Extract text (OCR if needed)
        2. Parse with LLM
        3. Analyze for risks
        
        Args:
            file_content: Raw file bytes (PDF, image, or text)
            filename: Original filename for type detection
            
        Returns:
            Complete analysis including parsed data and risk assessment
        """
        # Step 1: Extract text from document
        text = await self._extract_text(file_content, filename)
        
        # Step 2: Parse deed with LLM
        parsed = await self._parse_deed(text)
        
        # Step 3: Analyze for risks
        analysis = await self._analyze_risks(parsed)
        
        return {
            "raw_text": text[:1000] + "..." if len(text) > 1000 else text,
            "parsed_deed": parsed,
            "analysis": analysis,
            "documents_count": 1
        }
    
    async def build_chain_of_title(
        self, 
        parsed_deeds: List[dict]
    ) -> Dict[str, Any]:
        """
        Build chain of title from multiple parsed deeds.
        
        Connects grantees to grantors across documents to show
        ownership history and identify gaps.
        
        Args:
            parsed_deeds: List of parsed deed data
            
        Returns:
            Chain of title with gaps and issues identified
        """
        prompt = f"""Analyze these deed records and build a chain of title.

DEED RECORDS:
{json.dumps(parsed_deeds, indent=2)}

TASK:
1. Order the deeds chronologically by recording date
2. Connect each transfer (grantee of one deed should be grantor of next)
3. Identify any gaps or breaks in the chain
4. Note any potential issues (name variations, short ownership periods)

OUTPUT FORMAT (JSON only, no other text):
{{
    "chain": [
        {{
            "owner": "name",
            "from_date": "YYYY-MM-DD or null",
            "to_date": "YYYY-MM-DD or null",
            "how_acquired": "deed type",
            "document_ref": "recording info"
        }}
    ],
    "chain_complete": true/false,
    "gaps": [
        {{
            "between": ["owner1", "owner2"],
            "description": "what's missing",
            "severity": "low|medium|high"
        }}
    ],
    "issues": [
        {{
            "type": "issue type",
            "description": "details",
            "risk_level": "low|medium|high"
        }}
    ],
    "total_transfers": number,
    "earliest_date": "YYYY-MM-DD",
    "latest_date": "YYYY-MM-DD"
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._extract_json(response.content[0].text)
    
    async def _extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Extract text from document file.
        
        Supports:
        - PDF: Uses pdf2image + tesseract (or pymupdf)
        - Images: Direct tesseract OCR
        - Text: Direct decode
        """
        ext = filename.lower().split('.')[-1]
        
        if ext == 'pdf':
            return await self._extract_from_pdf(file_content)
        elif ext in ['png', 'jpg', 'jpeg', 'tiff']:
            return await self._extract_from_image(file_content)
        elif ext == 'txt':
            return file_content.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    async def _extract_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF."""
        try:
            # Try pdf2image + tesseract first
            from pdf2image import convert_from_bytes
            import pytesseract
            
            images = convert_from_bytes(content)
            texts = []
            for img in images:
                texts.append(pytesseract.image_to_string(img))
            return "\n\n".join(texts)
        except ImportError:
            pass
        
        try:
            # Fallback: PyMuPDF
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except ImportError:
            pass
        
        raise ValueError(
            "PDF processing requires: pip install pdf2image pytesseract "
            "OR pip install pymupdf"
        )
    
    async def _extract_from_image(self, content: bytes) -> str:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            img = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(img)
        except ImportError:
            raise ValueError("Image OCR requires: pip install pytesseract")
    
    async def _parse_deed(self, text: str) -> dict:
        """
        Use LLM to extract structured data from deed text.
        
        This is the core extraction logic - converting unstructured
        legal text into structured JSON.
        """
        prompt = f"""You are a title examiner assistant. Extract information from this deed document.

DOCUMENT TEXT:
{text}

EXTRACTION RULES:
1. Names: Extract exactly as written, note any "aka" or variations
2. Legal Description: Include full text
3. If information is unclear or missing, mark as null
4. Be precise with recording information
5. Identify the deed type based on language used

OUTPUT FORMAT (JSON only, no other text):
{{
    "document_type": "warranty_deed|quitclaim_deed|grant_deed|trust_deed|mortgage|other",
    "recording_info": {{
        "date": "YYYY-MM-DD or null",
        "book": "string or null",
        "page": "string or null",
        "document_number": "string or null",
        "county": "string",
        "state": "string"
    }},
    "parties": {{
        "grantor": {{
            "names": ["list of full legal names"],
            "type": "individual|married_couple|corporation|trust|estate|other"
        }},
        "grantee": {{
            "names": ["list of full legal names"],
            "type": "individual|married_couple|corporation|trust|estate|other",
            "vesting": "joint_tenants|tenants_in_common|community_property|sole|other"
        }}
    }},
    "property": {{
        "legal_description": "full text of legal description",
        "parcel_number": "APN/parcel ID if present or null",
        "address": "street address if mentioned or null",
        "county": "county name",
        "state": "state"
    }},
    "consideration": {{
        "amount": number or null,
        "type": "cash|nominal|love_and_affection|exchange|other"
    }},
    "encumbrances_mentioned": ["list any liens, easements, restrictions, exceptions"],
    "special_clauses": ["any notable clauses or conditions"],
    "notarization": {{
        "date": "YYYY-MM-DD or null",
        "notary_name": "string or null",
        "commission_expires": "date or null"
    }},
    "extraction_confidence": 0.0-1.0,
    "notes": ["any important observations or uncertainties"]
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._extract_json(response.content[0].text)
    
    async def _analyze_risks(self, parsed_deed: dict) -> dict:
        """
        Analyze parsed deed for potential title risks.
        
        Checks for common issues that could affect marketability
        or indicate fraud.
        """
        prompt = f"""Analyze this parsed deed for title risks.

PARSED DEED:
{json.dumps(parsed_deed, indent=2)}

RISK FACTORS TO EVALUATE:
1. Deed type strength (warranty > grant > quitclaim)
2. Consideration amount ($10 or "love and affection" = gift, potential issues)
3. Party types (trusts/corporations need proper authorization)
4. Vesting type clarity
5. Mentioned encumbrances
6. Any unusual patterns or red flags

COMMON RED FLAGS:
- Quitclaim deeds in chain (weaker title)
- Nominal consideration ($1, $10) outside family transfers
- Missing spousal signatures on homestead
- Corporate/trust parties without proper documentation reference
- Recent foreclosure language
- Lis pendens references
- Federal tax lien mentions

OUTPUT FORMAT (JSON only):
{{
    "risk_score": 0.0-1.0,
    "risk_level": "LOW|MEDIUM|HIGH",
    "risk_factors": [
        {{
            "factor": "name",
            "description": "details",
            "severity": "low|medium|high",
            "recommendation": "what to do about it"
        }}
    ],
    "is_marketable": true/false,
    "marketability_issues": ["list if not marketable"],
    "recommended_actions": ["list of next steps for examiner"],
    "encumbrances": [
        {{
            "type": "lien|easement|restriction|covenant|other",
            "description": "details",
            "affects_marketability": true/false,
            "clears_at_closing": true/false/unknown
        }}
    ],
    "title_quality": "good|fair|poor|defective",
    "summary": "One paragraph summary of title status"
}}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._extract_json(response.content[0].text)
    
    def _extract_json(self, text: str) -> dict:
        """
        Extract JSON from LLM response.
        
        Handles cases where the model includes extra text around the JSON.
        """
        # Try parsing entire response first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON block in response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Return error structure
        return {
            "error": "Could not parse LLM response as JSON",
            "raw_response": text[:500]
        }


class MockTitleAnalyzer:
    """
    Mock analyzer for testing without API key.
    
    Returns realistic sample data so you can test the full
    flow without consuming API credits.
    """
    
    async def analyze_document(
        self, 
        file_content: bytes, 
        filename: str
    ) -> Dict[str, Any]:
        """Return mock analysis data."""
        return {
            "raw_text": file_content.decode('utf-8', errors='ignore')[:500],
            "parsed_deed": {
                "document_type": "warranty_deed",
                "recording_info": {
                    "date": "2024-03-18",
                    "book": "1234",
                    "page": "567",
                    "document_number": "2024-0123456",
                    "county": "Travis",
                    "state": "Texas"
                },
                "parties": {
                    "grantor": {
                        "names": ["Robert James Johnson", "Mary Ann Johnson"],
                        "type": "married_couple"
                    },
                    "grantee": {
                        "names": ["John Michael Smith", "Jane Elizabeth Smith"],
                        "type": "married_couple",
                        "vesting": "joint_tenants"
                    }
                },
                "property": {
                    "legal_description": "LOT 15, BLOCK 3, SUNSET HILLS SUBDIVISION, "
                                        "according to the plat thereof recorded in "
                                        "Volume 45, Page 123 of the Plat Records of "
                                        "Travis County, Texas.",
                    "parcel_number": "123-456-789-000",
                    "address": "123 Main Street, Austin, TX 78701",
                    "county": "Travis",
                    "state": "Texas"
                },
                "consideration": {
                    "amount": 350000,
                    "type": "cash"
                },
                "encumbrances_mentioned": [
                    "General and special taxes for 2024",
                    "Easement for public utilities along rear 10 feet"
                ],
                "special_clauses": [],
                "extraction_confidence": 0.95,
                "notes": ["Clean warranty deed with standard covenants"]
            },
            "analysis": {
                "risk_score": 0.15,
                "risk_level": "LOW",
                "risk_factors": [
                    {
                        "factor": "Utility Easement",
                        "description": "Standard utility easement on rear of property",
                        "severity": "low",
                        "recommendation": "Review easement terms for any building restrictions"
                    }
                ],
                "is_marketable": True,
                "marketability_issues": [],
                "recommended_actions": [
                    "Verify current property tax status",
                    "Confirm no additional easements recorded since"
                ],
                "encumbrances": [
                    {
                        "type": "easement",
                        "description": "Public utility easement - rear 10 feet",
                        "affects_marketability": False,
                        "clears_at_closing": False
                    }
                ],
                "title_quality": "good",
                "summary": "This is a standard warranty deed conveying property "
                          "between married couples with typical consideration. "
                          "The only encumbrance is a standard utility easement "
                          "which does not affect marketability. Title appears "
                          "good and marketable subject to standard exceptions."
            },
            "documents_count": 1
        }
    
    async def build_chain_of_title(self, parsed_deeds: List[dict]) -> dict:
        """Return mock chain of title."""
        return {
            "chain": [
                {
                    "owner": "State of Texas",
                    "from_date": None,
                    "to_date": "1925-01-15",
                    "how_acquired": "patent",
                    "document_ref": "Patent Grant"
                },
                {
                    "owner": "Original Subdivision LLC",
                    "from_date": "1925-01-15",
                    "to_date": "1960-06-01",
                    "how_acquired": "warranty_deed",
                    "document_ref": "Book 100, Page 50"
                },
                {
                    "owner": "Robert James Johnson",
                    "from_date": "1960-06-01",
                    "to_date": "2024-03-18",
                    "how_acquired": "warranty_deed",
                    "document_ref": "Book 500, Page 200"
                },
                {
                    "owner": "John Michael Smith",
                    "from_date": "2024-03-18",
                    "to_date": None,
                    "how_acquired": "warranty_deed",
                    "document_ref": "Book 1234, Page 567"
                }
            ],
            "chain_complete": True,
            "gaps": [],
            "issues": [],
            "total_transfers": 4,
            "earliest_date": "1925-01-15",
            "latest_date": "2024-03-18"
        }
