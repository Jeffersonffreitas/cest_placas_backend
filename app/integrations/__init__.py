"""Boundaries and local adapters for external integrations."""

from app.integrations.institutional import (
    InstitutionalCoordination,
    InstitutionalCourse,
    InstitutionalPerson,
    InstitutionalPersonProvider,
    LocalInstitutionalPersonProvider,
)

__all__ = [
    "InstitutionalCoordination",
    "InstitutionalCourse",
    "InstitutionalPerson",
    "InstitutionalPersonProvider",
    "LocalInstitutionalPersonProvider",
]

