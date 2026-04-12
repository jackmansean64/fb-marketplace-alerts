"""
Configuration models for Facebook Marketplace alerts.

Uses Pydantic for validation and YAML for the config file format.
Supports multiple searches, each with their own parameters.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class AlertFrequency(str, Enum):
    """How often the user wants to be alerted about new listings."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class VehicleFilters(BaseModel):
    """Category-specific filters for vehicle searches."""

    min_year: Optional[int] = Field(None, description="Minimum model year")
    max_year: Optional[int] = Field(None, description="Maximum model year")
    min_mileage: Optional[int] = Field(None, description="Minimum mileage in km")
    max_mileage: Optional[int] = Field(None, description="Maximum mileage in km")


class SearchConfig(BaseModel):
    """Configuration for a single marketplace search."""

    # Search query
    query: str = Field(..., description="Search query text (e.g. 'Prius V')")

    # Pricing
    min_price: Optional[int] = Field(None, ge=0, description="Minimum price in dollars")
    max_price: Optional[int] = Field(None, ge=0, description="Maximum price in dollars")

    # Listing age
    days_since_listed: Optional[int] = Field(
        None, ge=1, description="Only show listings from the last N days"
    )

    # Location
    location: str = Field(
        "victoria",
        description=(
            "Facebook Marketplace location slug used in the URL path "
            "(e.g. 'victoria', 'toronto', 'vancouver'). "
            "You can also use a numeric location ID."
        ),
    )
    allowed_locations: Optional[list[str]] = Field(
        None,
        description=(
            "Only keep listings from these locations (e.g. ['Victoria, BC']). "
            "Matched case-insensitively. If omitted, all locations are kept."
        ),
    )

    # Category-specific filters
    vehicle_filters: Optional[VehicleFilters] = Field(
        None, description="Additional filters when searching for vehicles"
    )

    # Results
    max_listings: int = Field(
        100, ge=1, description="Maximum number of listings to return"
    )

    def build_url(self) -> str:
        """Build the Facebook Marketplace search URL from config values."""
        base_url = f"https://www.facebook.com/marketplace/{self.location}/search?"

        params: dict[str, str | int] = {
            "query": self.query,
        }

        if self.min_price is not None:
            params["minPrice"] = self.min_price
        if self.max_price is not None:
            params["maxPrice"] = self.max_price
        if self.days_since_listed is not None:
            params["daysSinceListed"] = self.days_since_listed
        # Vehicle-specific filters
        if self.vehicle_filters:
            vf = self.vehicle_filters
            if vf.min_year is not None:
                params["minYear"] = vf.min_year
            if vf.max_year is not None:
                params["maxYear"] = vf.max_year
            if vf.min_mileage is not None:
                params["minMileage"] = vf.min_mileage
            if vf.max_mileage is not None:
                params["maxMileage"] = vf.max_mileage

        return base_url + "&".join(f"{k}={v}" for k, v in params.items())


class EmailConfig(BaseModel):
    """Email notification settings."""

    sender_email: str = Field(..., description="Gmail address to send from")
    receiver_email: str = Field(..., description="Email address to receive alerts")


class AppConfig(BaseModel):
    """Top-level application configuration."""

    email: EmailConfig
    alert_frequency: AlertFrequency = Field(
        AlertFrequency.DAILY,
        description=(
            "How often alerts should be sent. "
            "Not yet functional — reserved for future scheduling."
        ),
    )
    searches: list[SearchConfig] = Field(
        ..., min_length=1, description="One or more search configurations to run"
    )

    @field_validator("searches")
    @classmethod
    def _validate_searches_not_empty(cls, v: list[SearchConfig]) -> list[SearchConfig]:
        if not v:
            raise ValueError("At least one search must be configured")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load and validate the application config from a YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Copy config.example.yaml to config.yaml and edit it."
        )
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig(**raw)
