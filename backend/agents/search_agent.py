"""
Search Agent - Agentic AI for Title Search Automation

Autonomous agent that:
1. Plans multi-county searches
2. Executes parallel document retrieval
3. Manages rate limits and failover
4. Caches results
5. Assembles complete ownership chains

Designed for nationwide scale (3,600+ counties).
"""

from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import hashlib
from collections import defaultdict

from .county_connector import (
    CountyConnectorBase,
    LandRecordDocument,
    SearchCriteria,
    DocumentType
)
from .county_registry import (
    CountyRegistry,
    CountyConnectorFactory,
    get_global_registry
)

logger = logging.getLogger(__name__)


class SearchStatus(Enum):
    """Status of a search task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some counties succeeded, others failed


@dataclass
class SearchTask:
    """Represents a single search task for one county."""
    task_id: str
    county: str
    state: str
    criteria: SearchCriteria
    status: SearchStatus = SearchStatus.PENDING
    results: List[LandRecordDocument] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class TitleSearchRequest:
    """Request for a complete title search."""

    # Property identification
    parcel_number: Optional[str] = None
    property_address: Optional[str] = None

    # Current owner (to build chain backwards)
    current_owner: Optional[str] = None

    # Geographic scope
    counties: List[tuple[str, str]] = field(default_factory=list)  # [(county, state), ...]

    # Search parameters
    years_back: int = 60  # How many years to search back
    document_types: Optional[List[DocumentType]] = None

    # Options
    include_mortgages: bool = True
    include_liens: bool = True
    include_easements: bool = True
    retrieve_images: bool = False

    # Limits
    max_documents: int = 1000
    timeout_seconds: int = 300


@dataclass
class TitleSearchResult:
    """Result of a complete title search."""
    request_id: str
    status: SearchStatus
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results by county
    documents_by_county: Dict[str, List[LandRecordDocument]] = field(default_factory=dict)
    all_documents: List[LandRecordDocument] = field(default_factory=list)

    # Ownership chain (will be built by chain_builder agent)
    ownership_chain: Optional[List[Dict[str, Any]]] = None

    # Metadata
    counties_searched: int = 0
    counties_succeeded: int = 0
    counties_failed: int = 0
    total_documents: int = 0

    # Errors
    errors: List[Dict[str, str]] = field(default_factory=list)


class DocumentCache:
    """
    In-memory cache for land record documents.

    TODO: Replace with Redis or database for production.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple[datetime, List[LandRecordDocument]]] = {}

    def get(self, cache_key: str) -> Optional[List[LandRecordDocument]]:
        """Get cached documents if not expired."""
        if cache_key in self._cache:
            cached_at, documents = self._cache[cache_key]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.ttl_seconds):
                logger.debug(f"Cache hit: {cache_key}")
                return documents
            else:
                # Expired
                del self._cache[cache_key]

        logger.debug(f"Cache miss: {cache_key}")
        return None

    def set(self, cache_key: str, documents: List[LandRecordDocument]):
        """Cache documents."""
        self._cache[cache_key] = (datetime.utcnow(), documents)
        logger.debug(f"Cached {len(documents)} documents under key: {cache_key}")

    def _make_key(self, county: str, state: str, criteria: SearchCriteria) -> str:
        """Generate cache key from search parameters."""
        key_parts = [
            county,
            state,
            criteria.parcel_number or "",
            criteria.property_address or "",
            criteria.owner_name or "",
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()


class SearchAgent:
    """
    Autonomous agent for title search automation.

    Capabilities:
    - Multi-county parallel search
    - Intelligent rate limiting
    - Automatic failover
    - Document caching
    - Progress tracking
    """

    def __init__(
        self,
        registry: Optional[CountyRegistry] = None,
        credentials: Optional[Dict[str, Any]] = None,
        max_concurrent_counties: int = 5
    ):
        """
        Initialize Search Agent.

        Args:
            registry: County registry (uses global if None)
            credentials: Credentials for county systems
            max_concurrent_counties: Max counties to search in parallel
        """
        self.registry = registry or get_global_registry()
        self.factory = CountyConnectorFactory(self.registry, credentials or {})
        self.max_concurrent_counties = max_concurrent_counties
        self.cache = DocumentCache(ttl_seconds=3600)  # 1 hour cache

        # Track active connectors
        self._connectors: Dict[str, CountyConnectorBase] = {}

    async def search(self, request: TitleSearchRequest) -> TitleSearchResult:
        """
        Execute a complete title search.

        Args:
            request: Title search request

        Returns:
            Search results with documents from all counties
        """
        request_id = hashlib.md5(
            f"{request.parcel_number}{request.property_address}{datetime.utcnow()}".encode()
        ).hexdigest()[:16]

        logger.info(f"🔍 Starting title search: {request_id}")

        result = TitleSearchResult(
            request_id=request_id,
            status=SearchStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )

        # Determine which counties to search
        counties_to_search = request.counties
        if not counties_to_search:
            # Auto-detect counties (would need geocoding/FIPS lookup)
            logger.warning("No counties specified - cannot auto-detect yet")
            result.status = SearchStatus.FAILED
            result.errors.append({"error": "No counties specified for search"})
            return result

        # Create search tasks for each county
        tasks = [
            self._create_search_task(county, state, request)
            for county, state in counties_to_search
        ]

        # Execute searches in parallel (with concurrency limit)
        search_results = await self._execute_parallel_searches(tasks)

        # Aggregate results
        for task in search_results:
            county_key = f"{task.county}, {task.state}"

            result.counties_searched += 1

            if task.status == SearchStatus.COMPLETED:
                result.counties_succeeded += 1
                result.documents_by_county[county_key] = task.results
                result.all_documents.extend(task.results)
            else:
                result.counties_failed += 1
                result.errors.append({
                    "county": county_key,
                    "error": task.error or "Unknown error"
                })

        result.total_documents = len(result.all_documents)
        result.completed_at = datetime.utcnow()

        # Determine overall status
        if result.counties_succeeded == result.counties_searched:
            result.status = SearchStatus.COMPLETED
        elif result.counties_succeeded > 0:
            result.status = SearchStatus.PARTIAL
        else:
            result.status = SearchStatus.FAILED

        duration = (result.completed_at - result.started_at).total_seconds()
        logger.info(
            f"✅ Search completed: {request_id} | "
            f"{result.total_documents} docs from {result.counties_succeeded}/{result.counties_searched} counties | "
            f"{duration:.1f}s"
        )

        return result

    def _create_search_task(
        self,
        county: str,
        state: str,
        request: TitleSearchRequest
    ) -> SearchTask:
        """Create a search task for a single county."""
        # Build search criteria from request
        criteria = SearchCriteria(
            parcel_number=request.parcel_number,
            property_address=request.property_address,
            owner_name=request.current_owner,
            start_date=datetime.utcnow() - timedelta(days=365 * request.years_back),
            end_date=datetime.utcnow(),
            document_types=request.document_types,
            max_results=request.max_documents,
            include_images=request.retrieve_images
        )

        task_id = f"{state}_{county}_{hashlib.md5(str(criteria).encode()).hexdigest()[:8]}"

        return SearchTask(
            task_id=task_id,
            county=county,
            state=state,
            criteria=criteria
        )

    async def _execute_parallel_searches(self, tasks: List[SearchTask]) -> List[SearchTask]:
        """
        Execute multiple search tasks in parallel with concurrency limit.

        Args:
            tasks: List of search tasks

        Returns:
            Completed tasks with results
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_counties)

        async def execute_with_limit(task: SearchTask) -> SearchTask:
            async with semaphore:
                return await self._execute_single_search(task)

        # Execute all tasks concurrently (but limited by semaphore)
        results = await asyncio.gather(
            *[execute_with_limit(task) for task in tasks],
            return_exceptions=True
        )

        # Handle any exceptions
        completed_tasks = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tasks[i].status = SearchStatus.FAILED
                tasks[i].error = str(result)
                completed_tasks.append(tasks[i])
            else:
                completed_tasks.append(result)

        return completed_tasks

    async def _execute_single_search(self, task: SearchTask) -> SearchTask:
        """
        Execute a single county search.

        Args:
            task: Search task

        Returns:
            Updated task with results
        """
        task.status = SearchStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()

        logger.info(f"Searching {task.county}, {task.state}...")

        try:
            # Check cache first
            cache_key = self.cache._make_key(task.county, task.state, task.criteria)
            cached_results = self.cache.get(cache_key)

            if cached_results:
                logger.info(f"Using cached results for {task.county}, {task.state}")
                task.results = cached_results
                task.status = SearchStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                return task

            # Get connector for this county
            connector = await self.factory.create_connector(task.county, task.state)

            # Authenticate if needed
            if not connector._authenticated:
                await connector.authenticate()

            # Execute search
            results = await connector.search(task.criteria)

            # Cache results
            self.cache.set(cache_key, results)

            # Update task
            task.results = results
            task.status = SearchStatus.COMPLETED
            task.completed_at = datetime.utcnow()

            logger.info(
                f"✅ {task.county}, {task.state}: {len(results)} documents | "
                f"{(task.completed_at - task.started_at).total_seconds():.1f}s"
            )

            # Close connector
            await connector.close()

        except Exception as e:
            task.status = SearchStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            logger.error(f"❌ Search failed for {task.county}, {task.state}: {e}")

        return task

    async def close(self):
        """Close all active connectors."""
        for connector in self._connectors.values():
            try:
                await connector.close()
            except:
                pass
        self._connectors.clear()


# Convenience function for quick searches
async def search_title(
    parcel_number: Optional[str] = None,
    property_address: Optional[str] = None,
    counties: Optional[List[tuple[str, str]]] = None,
    credentials: Optional[Dict[str, Any]] = None
) -> TitleSearchResult:
    """
    Quick title search function.

    Args:
        parcel_number: Property parcel/tax number
        property_address: Property address
        counties: List of (county, state) tuples to search
        credentials: Authentication credentials for county systems

    Returns:
        Search results

    Example:
        >>> result = await search_title(
        ...     parcel_number="12-345-6789",
        ...     counties=[("Montgomery", "MD")],
        ...     credentials={"montgomery_md": {"email": "...", "password": "..."}}
        ... )
    """
    request = TitleSearchRequest(
        parcel_number=parcel_number,
        property_address=property_address,
        counties=counties or []
    )

    agent = SearchAgent(credentials=credentials)
    try:
        result = await agent.search(request)
        return result
    finally:
        await agent.close()
