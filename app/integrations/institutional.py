from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.config import settings


InstitutionalPersonType = Literal["ALUNO", "FUNCIONARIO"]


class InstitutionalProviderError(RuntimeError):
    """Base error raised by institutional provider adapters."""


class InstitutionalProviderUnavailableError(InstitutionalProviderError):
    """Raised when a configured institutional source cannot be reached."""


@dataclass(frozen=True, slots=True)
class InstitutionalCoordination:
    name: str
    acronym: str | None = None


@dataclass(frozen=True, slots=True)
class InstitutionalCourse:
    name: str
    code: str | None = None


@dataclass(frozen=True, slots=True)
class InstitutionalPerson:
    registration: str
    full_name: str
    person_type: InstitutionalPersonType
    active: bool
    email: str | None = None
    phone: str | None = None
    course: InstitutionalCourse | None = None
    coordination: InstitutionalCoordination | None = None


class InstitutionalPersonProvider(Protocol):
    """Boundary for the future RM/institutional data adapter."""

    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        """Return a person from the institutional source, when one exists."""


def normalize_registration(registration: str) -> str:
    return registration.strip().upper()


def normalize_institutional_person_type(person_type: str) -> str:
    normalized = person_type.strip().upper()
    aliases = {
        "ALUNO": "ALUNO",
        "ESTUDANTE": "ALUNO",
        "FUNCIONARIO": "FUNCIONARIO",
        "FUNCIONÁRIO": "FUNCIONARIO",
        "COLABORADOR": "FUNCIONARIO",
    }
    try:
        return aliases[normalized]
    except KeyError:
        raise ValueError("Unsupported institutional person type.") from None


class LocalInstitutionalPersonProvider:
    """In-memory provider used until the real institutional adapter exists."""

    def __init__(self, people: tuple[InstitutionalPerson, ...] = ()) -> None:
        self._people = {
            normalize_registration(person.registration): person for person in people
        }

    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        return self._people.get(normalize_registration(registration))


class UnconfiguredRMInstitutionalPersonProvider:
    """RM boundary that reports the missing real contract and connection.

    No transport, endpoint, schema, credentials, or RM field mapping is assumed.
    """

    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        del registration
        raise InstitutionalProviderUnavailableError(
            "The real RM provider has no configured contract or connection."
        )


_LOCAL_PEOPLE = (
    InstitutionalPerson(
        registration="20260001",
        full_name="Aluno Institucional de Teste",
        person_type="ALUNO",
        email="aluno.teste@cest.edu.br",
        phone="85999990001",
        active=True,
        course=InstitutionalCourse(name="Análise e Desenvolvimento de Sistemas", code="ADS"),
        coordination=InstitutionalCoordination(
            name="Coordenação de Tecnologia", acronym="CTI"
        ),
    ),
    InstitutionalPerson(
        registration="FUNC0001",
        full_name="Funcionário Institucional de Teste",
        person_type="FUNCIONARIO",
        email="funcionario.teste@cest.edu.br",
        phone="85999990002",
        active=True,
    ),
    InstitutionalPerson(
        registration="20260002",
        full_name="Aluno Institucional Inativo",
        person_type="ALUNO",
        email="aluno.inativo@cest.edu.br",
        active=False,
    ),
)

local_institutional_person_provider = LocalInstitutionalPersonProvider(_LOCAL_PEOPLE)
unconfigured_rm_institutional_person_provider = UnconfiguredRMInstitutionalPersonProvider()


def get_institutional_person_provider() -> InstitutionalPersonProvider:
    if settings.institutional_provider == "local":
        return local_institutional_person_provider
    return unconfigured_rm_institutional_person_provider
