"""
County Registry System for Nationwide Coverage

Manages 3,600+ county land record systems across all 50 states.
Provides factory pattern for creating appropriate connectors based on
county/state, with automatic fallback and failover strategies.

Architecture designed for:
- Scale: 3,600+ counties
- Diversity: Multiple access methods (API, scraper, FTP, etc.)
- Reliability: Failover and caching
- Extensibility: Easy to add new counties
"""

from typing import Dict, Optional, Type, List, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json
from pathlib import Path

from .county_connector import (
    CountyConnectorBase,
    MockCountyConnector,
    AccessMethod
)

logger = logging.getLogger(__name__)


class ConnectorPriority(Enum):
    """Priority level for connector selection."""
    PRIMARY = 1      # Official API, highest reliability
    SECONDARY = 2    # Web scraper, reliable but may break
    TERTIARY = 3     # Alternative source, less reliable
    FALLBACK = 4     # Mock/cached data only


@dataclass
class CountyConfig:
    """Configuration for a single county's land records access."""

    # Identification
    county: str
    state: str
    fips_code: str  # 5-digit FIPS code (state + county)

    # Access methods (in priority order)
    connectors: List[Dict[str, Any]]  # List of connector configs with priority

    # Metadata
    population: Optional[int] = None
    has_online_access: bool = False
    requires_subscription: bool = False
    cost_per_search: Optional[float] = None
    cost_per_document: Optional[float] = None

    # Rate limiting
    requests_per_minute: int = 10
    requests_per_day: Optional[int] = None

    # Contact info
    website_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Notes
    notes: Optional[str] = None
    last_updated: Optional[str] = None

    def __post_init__(self):
        """Sort connectors by priority."""
        self.connectors.sort(key=lambda x: x.get('priority', 99))


class CountyRegistry:
    """
    Registry of all county land record systems in the United States.

    Maintains configuration for 3,600+ counties across 50 states,
    including access methods, credentials, rate limits, and pricing.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize registry.

        Args:
            config_path: Path to county configuration JSON file
        """
        self._counties: Dict[str, CountyConfig] = {}
        self._connector_classes: Dict[str, Type[CountyConnectorBase]] = {}
        self._register_builtin_connectors()

        if config_path and config_path.exists():
            self.load_config(config_path)
        else:
            self._load_default_configs()

    def _register_builtin_connectors(self):
        """Register built-in connector classes."""
        from .montgomery_county_md import MontgomeryCountyMDConnector

        self.register_connector_class("mock", MockCountyConnector)
        self.register_connector_class("montgomery_md", MontgomeryCountyMDConnector)

    def register_connector_class(
        self,
        connector_name: str,
        connector_class: Type[CountyConnectorBase]
    ):
        """
        Register a connector class for use by the factory.

        Args:
            connector_name: Unique name for this connector
            connector_class: The connector class
        """
        self._connector_classes[connector_name] = connector_class
        logger.info(f"Registered connector: {connector_name}")

    def add_county(self, config: CountyConfig):
        """
        Add a county to the registry.

        Args:
            config: County configuration
        """
        key = f"{config.state}_{config.county}".lower().replace(" ", "_")
        self._counties[key] = config
        logger.debug(f"Added county: {config.county}, {config.state}")

    def get_county(self, county: str, state: str) -> Optional[CountyConfig]:
        """
        Get configuration for a specific county.

        Args:
            county: County name (e.g., "Montgomery")
            state: State code (e.g., "MD")

        Returns:
            County configuration or None if not found
        """
        key = f"{state}_{county}".lower().replace(" ", "_")
        return self._counties.get(key)

    def get_connector_class(self, connector_name: str) -> Optional[Type[CountyConnectorBase]]:
        """Get a registered connector class by name."""
        return self._connector_classes.get(connector_name)

    def list_counties(
        self,
        state: Optional[str] = None,
        has_online_access: Optional[bool] = None
    ) -> List[CountyConfig]:
        """
        List counties with optional filtering.

        Args:
            state: Filter by state code
            has_online_access: Filter by online access availability

        Returns:
            List of matching county configurations
        """
        results = list(self._counties.values())

        if state:
            results = [c for c in results if c.state == state.upper()]

        if has_online_access is not None:
            results = [c for c in results if c.has_online_access == has_online_access]

        return sorted(results, key=lambda c: (c.state, c.county))

    def load_config(self, config_path: Path):
        """
        Load county configurations from JSON file.

        Args:
            config_path: Path to JSON configuration file
        """
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)

            for county_data in data.get('counties', []):
                config = CountyConfig(**county_data)
                self.add_county(config)

            logger.info(f"Loaded {len(self._counties)} counties from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise

    def save_config(self, config_path: Path):
        """
        Save county configurations to JSON file.

        Args:
            config_path: Path to save JSON configuration
        """
        try:
            data = {
                "version": "1.0",
                "counties": [
                    {
                        "county": c.county,
                        "state": c.state,
                        "fips_code": c.fips_code,
                        "connectors": c.connectors,
                        "population": c.population,
                        "has_online_access": c.has_online_access,
                        "requires_subscription": c.requires_subscription,
                        "cost_per_search": c.cost_per_search,
                        "cost_per_document": c.cost_per_document,
                        "requests_per_minute": c.requests_per_minute,
                        "requests_per_day": c.requests_per_day,
                        "website_url": c.website_url,
                        "contact_email": c.contact_email,
                        "contact_phone": c.contact_phone,
                        "notes": c.notes,
                        "last_updated": c.last_updated
                    }
                    for c in self._counties.values()
                ]
            }

            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._counties)} counties to {config_path}")

        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            raise

    def _load_default_configs(self):
        """Load default county configurations."""
        # Montgomery County, MD
        self.add_county(CountyConfig(
            county="Montgomery",
            state="MD",
            fips_code="24031",
            connectors=[
                {
                    "connector_type": "montgomery_md",
                    "priority": ConnectorPriority.PRIMARY.value,
                    "access_method": AccessMethod.WEB_SCRAPER.value,
                    "requires_auth": True,
                    "base_url": "https://landrec.msa.maryland.gov"
                },
                {
                    "connector_type": "mock",
                    "priority": ConnectorPriority.FALLBACK.value,
                    "access_method": AccessMethod.MOCK.value
                }
            ],
            population=1062061,
            has_online_access=True,
            requires_subscription=True,
            cost_per_search=0.0,  # Free with registration
            cost_per_document=0.0,
            requests_per_minute=10,
            website_url="https://landrec.msa.maryland.gov",
            notes="Free access with email registration. Web scraping required.",
            last_updated="2026-01-08"
        ))

        # Template for adding more counties
        # Example: Los Angeles County, CA (largest county by population)
        self.add_county(CountyConfig(
            county="Los Angeles",
            state="CA",
            fips_code="06037",
            connectors=[
                {
                    "connector_type": "mock",  # TODO: Implement LA County connector
                    "priority": ConnectorPriority.FALLBACK.value,
                    "access_method": AccessMethod.MOCK.value
                }
            ],
            population=10014009,
            has_online_access=True,
            requires_subscription=False,
            cost_per_search=0.0,
            cost_per_document=0.0,
            website_url="https://lavote.gov/",
            notes="Has public API - connector not yet implemented",
            last_updated="2026-01-08"
        ))

        # Cook County, IL (Chicago)
        self.add_county(CountyConfig(
            county="Cook",
            state="IL",
            fips_code="17031",
            connectors=[
                {
                    "connector_type": "mock",  # TODO: Implement Cook County connector
                    "priority": ConnectorPriority.FALLBACK.value,
                    "access_method": AccessMethod.MOCK.value
                }
            ],
            population=5275541,
            has_online_access=True,
            requires_subscription=False,
            website_url="https://www.cookcountyassessor.com/",
            notes="Public data portal available - connector not yet implemented",
            last_updated="2026-01-08"
        ))

        logger.info(f"Loaded {len(self._counties)} default county configurations")

    def get_coverage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about county coverage.

        Returns:
            Dictionary with coverage statistics
        """
        total = len(self._counties)
        with_online = sum(1 for c in self._counties.values() if c.has_online_access)
        with_api = sum(
            1 for c in self._counties.values()
            if any(
                conn.get('access_method') == AccessMethod.REST_API.value
                for conn in c.connectors
            )
        )
        with_scraper = sum(
            1 for c in self._counties.values()
            if any(
                conn.get('access_method') == AccessMethod.WEB_SCRAPER.value
                for conn in c.connectors
            )
        )

        states = set(c.state for c in self._counties.values())

        return {
            "total_counties": total,
            "counties_with_online_access": with_online,
            "counties_with_api": with_api,
            "counties_with_scraper": with_scraper,
            "mock_only": total - with_online,
            "states_covered": len(states),
            "coverage_percentage": round((total / 3143) * 100, 2)  # 3,143 US counties
        }


class CountyConnectorFactory:
    """
    Factory for creating county connector instances.

    Handles instantiation of the correct connector type based on
    county configuration, with automatic failover.
    """

    def __init__(self, registry: CountyRegistry, credentials: Optional[Dict[str, Any]] = None):
        """
        Initialize factory.

        Args:
            registry: County registry instance
            credentials: Dictionary of credentials by county/connector
                        Format: {
                            "montgomery_md": {"email": "...", "password": "..."},
                            "global": {"api_key": "..."}
                        }
        """
        self.registry = registry
        self.credentials = credentials or {}

    async def create_connector(
        self,
        county: str,
        state: str,
        priority: Optional[ConnectorPriority] = None
    ) -> CountyConnectorBase:
        """
        Create a connector instance for the specified county.

        Args:
            county: County name
            state: State code
            priority: Maximum priority level to use (uses highest available if None)

        Returns:
            Instantiated connector

        Raises:
            ValueError: If county not found or no suitable connector available
        """
        config = self.registry.get_county(county, state)
        if not config:
            raise ValueError(f"County not found: {county}, {state}")

        # Filter connectors by priority if specified
        connectors = config.connectors
        if priority:
            connectors = [c for c in connectors if c.get('priority', 99) <= priority.value]

        if not connectors:
            raise ValueError(f"No suitable connector found for {county}, {state}")

        # Try connectors in priority order
        for connector_config in connectors:
            try:
                connector = await self._instantiate_connector(connector_config, config)
                logger.info(f"Created connector for {county}, {state}: {connector_config['connector_type']}")
                return connector
            except Exception as e:
                logger.warning(f"Failed to create connector {connector_config['connector_type']}: {e}")
                continue

        # If all failed, fall back to mock
        logger.warning(f"All connectors failed for {county}, {state} - using mock")
        return MockCountyConnector(county=county, state=state)

    async def _instantiate_connector(
        self,
        connector_config: Dict[str, Any],
        county_config: CountyConfig
    ) -> CountyConnectorBase:
        """
        Instantiate a specific connector.

        Args:
            connector_config: Configuration for this connector
            county_config: County configuration

        Returns:
            Instantiated connector

        Raises:
            Exception: If instantiation fails
        """
        connector_type = connector_config['connector_type']
        connector_class = self.registry.get_connector_class(connector_type)

        if not connector_class:
            raise ValueError(f"Unknown connector type: {connector_type}")

        # Get credentials for this connector
        creds = self.credentials.get(connector_type, {})
        if not creds:
            creds = self.credentials.get('global', {})

        # Instantiate connector
        # Different connectors may have different constructor signatures
        if connector_type == "mock":
            connector = connector_class(county=county_config.county, state=county_config.state)
        elif connector_type == "montgomery_md":
            email = creds.get('email')
            password = creds.get('password')
            if not email or not password:
                raise ValueError("Montgomery County MD connector requires email and password")
            connector = connector_class(email=email, password=password)
        else:
            # Generic instantiation
            connector = connector_class(**creds)

        return connector


# Global registry instance
_global_registry: Optional[CountyRegistry] = None


def get_global_registry() -> CountyRegistry:
    """Get or create the global county registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CountyRegistry()
    return _global_registry
