"""
County Connector Base Classes

Abstract base classes for connecting to county land record systems.
Supports multiple access methods: API, web scraping, direct database.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio


class DocumentType(Enum):
    """Types of land record documents."""
    DEED = "deed"
    MORTGAGE = "mortgage"
    LIEN = "lien"
    RELEASE = "release"
    EASEMENT = "easement"
    PLAT = "plat"
    JUDGMENT = "judgment"
    UCC = "ucc"
    OTHER = "other"


class AccessMethod(Enum):
    """Method used to access county data."""
    REST_API = "rest_api"
    SOAP_API = "soap_api"
    WEB_SCRAPER = "web_scraper"
    FTP = "ftp"
    DATABASE = "database"
    MOCK = "mock"


@dataclass
class LandRecordDocument:
    """Represents a land record document from a county system."""

    # Identifiers
    document_id: str
    county: str
    state: str

    # Recording information
    book: Optional[str] = None
    page: Optional[str] = None
    instrument_number: Optional[str] = None
    recording_date: Optional[datetime] = None

    # Document details
    document_type: DocumentType = DocumentType.OTHER
    document_subtype: Optional[str] = None

    # Parties
    grantor: Optional[List[str]] = None
    grantee: Optional[List[str]] = None

    # Property
    parcel_number: Optional[str] = None
    property_address: Optional[str] = None
    legal_description: Optional[str] = None

    # Financial
    consideration: Optional[float] = None

    # Document content
    document_url: Optional[str] = None
    document_content: Optional[bytes] = None
    document_text: Optional[str] = None

    # Metadata
    retrieved_at: datetime = None
    source_system: Optional[str] = None
    confidence_score: float = 1.0

    def __post_init__(self):
        if self.retrieved_at is None:
            self.retrieved_at = datetime.utcnow()


@dataclass
class SearchCriteria:
    """Criteria for searching land records."""

    # Property identifiers
    parcel_number: Optional[str] = None
    property_address: Optional[str] = None

    # Party search
    owner_name: Optional[str] = None
    grantor_name: Optional[str] = None
    grantee_name: Optional[str] = None

    # Document reference
    book: Optional[str] = None
    page: Optional[str] = None
    instrument_number: Optional[str] = None

    # Date range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Document types
    document_types: Optional[List[DocumentType]] = None

    # Limits
    max_results: int = 100
    include_images: bool = False


class CountyConnectorBase(ABC):
    """
    Abstract base class for county land record connectors.

    Each county implementation must provide methods to:
    - Authenticate with the county system
    - Search for documents by various criteria
    - Retrieve document details and images
    - Handle rate limiting and caching
    """

    def __init__(
        self,
        county: str,
        state: str,
        access_method: AccessMethod,
        config: Optional[Dict[str, Any]] = None
    ):
        self.county = county
        self.state = state
        self.access_method = access_method
        self.config = config or {}
        self._authenticated = False
        self._session = None

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the county system.

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    async def search_by_parcel(self, parcel_number: str) -> List[LandRecordDocument]:
        """
        Search for all documents related to a parcel number.

        Args:
            parcel_number: The parcel/tax account number

        Returns:
            List of documents found
        """
        pass

    @abstractmethod
    async def search_by_address(self, address: str) -> List[LandRecordDocument]:
        """
        Search for documents by property address.

        Args:
            address: Property address

        Returns:
            List of documents found
        """
        pass

    @abstractmethod
    async def search_by_owner(self, owner_name: str) -> List[LandRecordDocument]:
        """
        Search for documents by owner/grantee name.

        Args:
            owner_name: Name of property owner or grantee

        Returns:
            List of documents found
        """
        pass

    @abstractmethod
    async def search_by_instrument(
        self,
        book: Optional[str] = None,
        page: Optional[str] = None,
        instrument_number: Optional[str] = None
    ) -> Optional[LandRecordDocument]:
        """
        Search for a specific document by book/page or instrument number.

        Args:
            book: Book number
            page: Page number
            instrument_number: Instrument/document number

        Returns:
            Document if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_document_image(self, document_id: str) -> Optional[bytes]:
        """
        Retrieve the image/PDF of a document.

        Args:
            document_id: Unique document identifier

        Returns:
            Document content as bytes, or None if not available
        """
        pass

    async def search(self, criteria: SearchCriteria) -> List[LandRecordDocument]:
        """
        Unified search method using SearchCriteria.

        Args:
            criteria: Search criteria object

        Returns:
            List of matching documents
        """
        results = []

        # Search by parcel
        if criteria.parcel_number:
            results.extend(await self.search_by_parcel(criteria.parcel_number))

        # Search by address
        if criteria.property_address:
            results.extend(await self.search_by_address(criteria.property_address))

        # Search by owner
        if criteria.owner_name:
            results.extend(await self.search_by_owner(criteria.owner_name))

        # Search by instrument reference
        if criteria.book or criteria.page or criteria.instrument_number:
            doc = await self.search_by_instrument(
                book=criteria.book,
                page=criteria.page,
                instrument_number=criteria.instrument_number
            )
            if doc:
                results.append(doc)

        # Filter by document type
        if criteria.document_types:
            results = [
                doc for doc in results
                if doc.document_type in criteria.document_types
            ]

        # Filter by date range
        if criteria.start_date:
            results = [
                doc for doc in results
                if doc.recording_date and doc.recording_date >= criteria.start_date
            ]

        if criteria.end_date:
            results = [
                doc for doc in results
                if doc.recording_date and doc.recording_date <= criteria.end_date
            ]

        # Remove duplicates (by document_id)
        seen = set()
        unique_results = []
        for doc in results:
            if doc.document_id not in seen:
                seen.add(doc.document_id)
                unique_results.append(doc)

        # Limit results
        return unique_results[:criteria.max_results]

    async def close(self):
        """Close any open connections or sessions."""
        if self._session:
            try:
                await self._session.close()
            except:
                pass
        self._authenticated = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} county={self.county}, state={self.state}, method={self.access_method.value}>"


class MockCountyConnector(CountyConnectorBase):
    """
    Mock connector for testing and development.

    Returns sample data without connecting to real systems.
    """

    def __init__(self, county: str = "Test County", state: str = "MD"):
        super().__init__(
            county=county,
            state=state,
            access_method=AccessMethod.MOCK
        )
        self._mock_data = self._generate_mock_data()

    def _generate_mock_data(self) -> List[LandRecordDocument]:
        """Generate sample land records for testing."""
        return [
            LandRecordDocument(
                document_id="mock-001",
                county=self.county,
                state=self.state,
                book="1234",
                page="567",
                instrument_number="2024-0001",
                recording_date=datetime(2024, 3, 15),
                document_type=DocumentType.DEED,
                grantor=["John Doe", "Jane Doe"],
                grantee=["Alice Smith"],
                parcel_number="12-345-6789",
                property_address="123 Main St",
                legal_description="LOT 1, BLOCK A",
                consideration=500000.0,
                source_system="Mock System"
            ),
            LandRecordDocument(
                document_id="mock-002",
                county=self.county,
                state=self.state,
                book="1234",
                page="789",
                instrument_number="2024-0002",
                recording_date=datetime(2024, 1, 10),
                document_type=DocumentType.MORTGAGE,
                grantor=["Alice Smith"],
                grantee=["First National Bank"],
                parcel_number="12-345-6789",
                property_address="123 Main St",
                consideration=400000.0,
                source_system="Mock System"
            )
        ]

    async def authenticate(self) -> bool:
        """Mock authentication always succeeds."""
        await asyncio.sleep(0.1)  # Simulate network delay
        self._authenticated = True
        return True

    async def search_by_parcel(self, parcel_number: str) -> List[LandRecordDocument]:
        """Return mock documents for the parcel."""
        await asyncio.sleep(0.2)
        return [doc for doc in self._mock_data if doc.parcel_number == parcel_number]

    async def search_by_address(self, address: str) -> List[LandRecordDocument]:
        """Return mock documents for the address."""
        await asyncio.sleep(0.2)
        return [doc for doc in self._mock_data if address.lower() in (doc.property_address or "").lower()]

    async def search_by_owner(self, owner_name: str) -> List[LandRecordDocument]:
        """Return mock documents for the owner."""
        await asyncio.sleep(0.2)
        results = []
        for doc in self._mock_data:
            if doc.grantee and any(owner_name.lower() in name.lower() for name in doc.grantee):
                results.append(doc)
        return results

    async def search_by_instrument(
        self,
        book: Optional[str] = None,
        page: Optional[str] = None,
        instrument_number: Optional[str] = None
    ) -> Optional[LandRecordDocument]:
        """Return mock document by reference."""
        await asyncio.sleep(0.2)
        for doc in self._mock_data:
            if instrument_number and doc.instrument_number == instrument_number:
                return doc
            if book and page and doc.book == book and doc.page == page:
                return doc
        return None

    async def get_document_image(self, document_id: str) -> Optional[bytes]:
        """Return mock document image."""
        await asyncio.sleep(0.3)
        return b"MOCK_PDF_CONTENT_FOR_" + document_id.encode()
