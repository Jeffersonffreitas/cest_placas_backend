"""Boundaries and local adapters for external integrations."""

from app.integrations.institutional import (
    InstitutionalCoordination,
    InstitutionalCourse,
    InstitutionalPerson,
    InstitutionalPersonProvider,
    InstitutionalProviderError,
    InstitutionalProviderUnavailableError,
    LocalInstitutionalPersonProvider,
    UnconfiguredRMInstitutionalPersonProvider,
)

__all__ = [
    "InstitutionalCoordination",
    "InstitutionalCourse",
    "InstitutionalPerson",
    "InstitutionalPersonProvider",
    "InstitutionalProviderError",
    "InstitutionalProviderUnavailableError",
    "LocalInstitutionalPersonProvider",
    "UnconfiguredRMInstitutionalPersonProvider",
]

