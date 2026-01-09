"""
Montgomery County, Maryland Land Records Connector

Connects to Maryland Land Records system (landrec.msa.maryland.gov)
for Montgomery County property records.

Access Method: Web scraping with authentication
Data Source: Maryland State Archives Land Records System
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import asyncio
from bs4 import BeautifulSoup
import logging

from .county_connector import (
    CountyConnectorBase,
    LandRecordDocument,
    DocumentType,
    AccessMethod
)

logger = logging.getLogger(__name__)


class MontgomeryCountyMDConnector(CountyConnectorBase):
    """
    Connector for Montgomery County, Maryland land records.

    Uses the Maryland State Archives Land Records system:
    - URL: https://landrec.msa.maryland.gov/
    - Authentication: Email/password login
    - Search: By name, book/page, parcel number
    - Format: HTML pages with embedded document images
    """

    BASE_URL = "https://landrec.msa.maryland.gov"
    LOGIN_URL = f"{BASE_URL}/Account/Login"
    SEARCH_URL = f"{BASE_URL}/Search"

    def __init__(self, email: str, password: str):
        """
        Initialize Montgomery County connector.

        Args:
            email: MDLandRec account email
            password: MDLandRec account password
        """
        super().__init__(
            county="Montgomery",
            state="MD",
            access_method=AccessMethod.WEB_SCRAPER,
            config={"email": email, "password": password}
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper headers."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "TitleChain/1.0 (Automated Title Search)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
            )
        return self._client

    async def authenticate(self) -> bool:
        """
        Authenticate with MDLandRec system.

        Returns:
            True if authentication successful

        Raises:
            ValueError: If credentials are invalid
            httpx.HTTPError: If connection fails
        """
        try:
            client = await self._get_client()

            # Get login page to extract CSRF token
            logger.info("Fetching login page...")
            response = await client.get(self.LOGIN_URL)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = None

            # Look for anti-forgery token
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            if token_input:
                csrf_token = token_input.get('value')

            # Prepare login data
            login_data = {
                "Email": self.config["email"],
                "Password": self.config["password"],
                "RememberMe": "false"
            }

            if csrf_token:
                login_data["__RequestVerificationToken"] = csrf_token

            # Submit login
            logger.info("Submitting login credentials...")
            response = await client.post(self.LOGIN_URL, data=login_data)

            # Check if login was successful
            # Success typically redirects to home page or doesn't contain "Invalid" error
            if "Invalid" in response.text or "incorrect" in response.text.lower():
                logger.error("Authentication failed: Invalid credentials")
                return False

            self._authenticated = True
            logger.info("✅ Authentication successful")
            return True

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during authentication: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            raise

    async def search_by_parcel(self, parcel_number: str) -> List[LandRecordDocument]:
        """
        Search by parcel/tax account number.

        Args:
            parcel_number: The parcel number (format varies)

        Returns:
            List of documents found for this parcel
        """
        if not self._authenticated:
            await self.authenticate()

        try:
            client = await self._get_client()

            # Montgomery County MD search
            # Note: The actual search parameters depend on the site structure
            search_params = {
                "County": "Montgomery",
                "SearchType": "Parcel",
                "ParcelNumber": parcel_number
            }

            logger.info(f"Searching for parcel: {parcel_number}")
            response = await client.get(self.SEARCH_URL, params=search_params)
            response.raise_for_status()

            # Parse results
            documents = self._parse_search_results(response.text)
            logger.info(f"Found {len(documents)} documents for parcel {parcel_number}")

            return documents

        except Exception as e:
            logger.error(f"Error searching by parcel: {e}")
            return []

    async def search_by_address(self, address: str) -> List[LandRecordDocument]:
        """
        Search by property address.

        Note: Address search may require geocoding to parcel number first.

        Args:
            address: Property address

        Returns:
            List of documents found
        """
        if not self._authenticated:
            await self.authenticate()

        logger.warning("Address search not directly supported - would need SDAT integration for address-to-parcel lookup")
        return []

    async def search_by_owner(self, owner_name: str) -> List[LandRecordDocument]:
        """
        Search by owner/grantee name.

        Args:
            owner_name: Name to search for

        Returns:
            List of documents found
        """
        if not self._authenticated:
            await self.authenticate()

        try:
            client = await self._get_client()

            search_params = {
                "County": "Montgomery",
                "SearchType": "Name",
                "Name": owner_name
            }

            logger.info(f"Searching for owner: {owner_name}")
            response = await client.get(self.SEARCH_URL, params=search_params)
            response.raise_for_status()

            documents = self._parse_search_results(response.text)
            logger.info(f"Found {len(documents)} documents for {owner_name}")

            return documents

        except Exception as e:
            logger.error(f"Error searching by owner: {e}")
            return []

    async def search_by_instrument(
        self,
        book: Optional[str] = None,
        page: Optional[str] = None,
        instrument_number: Optional[str] = None
    ) -> Optional[LandRecordDocument]:
        """
        Search by book/page or instrument number.

        Args:
            book: Liber/book number
            page: Folio/page number
            instrument_number: Instrument number

        Returns:
            Document if found, None otherwise
        """
        if not self._authenticated:
            await self.authenticate()

        try:
            client = await self._get_client()

            if instrument_number:
                search_params = {
                    "County": "Montgomery",
                    "SearchType": "Instrument",
                    "InstrumentNumber": instrument_number
                }
            elif book and page:
                search_params = {
                    "County": "Montgomery",
                    "SearchType": "BookPage",
                    "Book": book,
                    "Page": page
                }
            else:
                logger.warning("Must provide either instrument_number or both book and page")
                return None

            logger.info(f"Searching for instrument: {search_params}")
            response = await client.get(self.SEARCH_URL, params=search_params)
            response.raise_for_status()

            documents = self._parse_search_results(response.text)

            return documents[0] if documents else None

        except Exception as e:
            logger.error(f"Error searching by instrument: {e}")
            return None

    async def get_document_image(self, document_id: str) -> Optional[bytes]:
        """
        Retrieve document image/PDF.

        Args:
            document_id: Document identifier (typically a URL or image ID)

        Returns:
            Document bytes (usually PDF or TIFF)
        """
        if not self._authenticated:
            await self.authenticate()

        try:
            client = await self._get_client()

            # Document ID might be a relative URL
            if document_id.startswith('http'):
                url = document_id
            else:
                url = f"{self.BASE_URL}{document_id}"

            logger.info(f"Fetching document image from: {url}")
            response = await client.get(url)
            response.raise_for_status()

            return response.content

        except Exception as e:
            logger.error(f"Error fetching document image: {e}")
            return None

    def _parse_search_results(self, html: str) -> List[LandRecordDocument]:
        """
        Parse HTML search results into LandRecordDocument objects.

        This is a template implementation - actual parsing depends on
        the site structure which may change.

        Args:
            html: HTML content from search results page

        Returns:
            List of parsed documents
        """
        documents = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find result rows (structure may vary)
            # This is a generic pattern - adjust based on actual HTML
            result_rows = soup.find_all('tr', class_='result-row') or soup.find_all('div', class_='document-result')

            for row in result_rows:
                try:
                    doc = self._parse_result_row(row)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.warning(f"Failed to parse result row: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing search results: {e}")

        return documents

    def _parse_result_row(self, row) -> Optional[LandRecordDocument]:
        """
        Parse a single result row into a LandRecordDocument.

        Args:
            row: BeautifulSoup element containing a single result

        Returns:
            Parsed document or None if parsing fails
        """
        try:
            # Extract data from row
            # This is template code - adjust selectors based on actual HTML structure

            # Look for common fields
            doc_id = row.get('data-id') or row.find('a', class_='doc-link').get('href', '')

            # Extract book/page
            book_page_text = row.find(text=re.compile(r'\d+/\d+'))
            book, page = None, None
            if book_page_text:
                match = re.search(r'(\d+)/(\d+)', book_page_text)
                if match:
                    book, page = match.groups()

            # Extract instrument number
            instrument_elem = row.find('span', class_='instrument')
            instrument_number = instrument_elem.text.strip() if instrument_elem else None

            # Extract date
            date_elem = row.find('span', class_='date')
            recording_date = None
            if date_elem:
                try:
                    recording_date = datetime.strptime(date_elem.text.strip(), '%m/%d/%Y')
                except:
                    pass

            # Extract parties
            grantor_elem = row.find('span', class_='grantor')
            grantee_elem = row.find('span', class_='grantee')

            grantor = [grantor_elem.text.strip()] if grantor_elem else []
            grantee = [grantee_elem.text.strip()] if grantee_elem else []

            # Determine document type
            doc_type_elem = row.find('span', class_='doc-type')
            doc_type_text = doc_type_elem.text.strip().upper() if doc_type_elem else ""

            document_type = self._map_document_type(doc_type_text)

            # Create document object
            document = LandRecordDocument(
                document_id=doc_id,
                county=self.county,
                state=self.state,
                book=book,
                page=page,
                instrument_number=instrument_number,
                recording_date=recording_date,
                document_type=document_type,
                grantor=grantor if grantor else None,
                grantee=grantee if grantee else None,
                source_system="MDLandRec",
                confidence_score=0.85  # Moderate confidence due to web scraping
            )

            return document

        except Exception as e:
            logger.warning(f"Failed to parse result row: {e}")
            return None

    def _map_document_type(self, type_text: str) -> DocumentType:
        """Map document type string to DocumentType enum."""
        type_text = type_text.upper()

        if 'DEED' in type_text:
            return DocumentType.DEED
        elif 'MORTGAGE' in type_text or 'MTG' in type_text:
            return DocumentType.MORTGAGE
        elif 'LIEN' in type_text:
            return DocumentType.LIEN
        elif 'RELEASE' in type_text or 'SATISFACTION' in type_text:
            return DocumentType.RELEASE
        elif 'EASEMENT' in type_text:
            return DocumentType.EASEMENT
        elif 'PLAT' in type_text:
            return DocumentType.PLAT
        elif 'JUDGMENT' in type_text:
            return DocumentType.JUDGMENT
        elif 'UCC' in type_text:
            return DocumentType.UCC
        else:
            return DocumentType.OTHER

    async def close(self):
        """Close HTTP client and cleanup."""
        if self._client:
            await self._client.aclose()
            self._client = None
        await super().close()
