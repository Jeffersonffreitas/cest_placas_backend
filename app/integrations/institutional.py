from dataclasses import dataclass
from typing import Literal, Protocol


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
    person_type: Literal["ALUNO", "FUNCIONARIO"]
    email: str | None
    active: bool
    course: InstitutionalCourse | None = None
    coordination: InstitutionalCoordination | None = None


class InstitutionalPersonProvider(Protocol):
    """Boundary for the future RM/institutional data adapter."""

    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        """Return a person from the institutional source, when one exists."""


def normalize_registration(registration: str) -> str:
    return registration.strip().upper()


class LocalInstitutionalPersonProvider:
    """In-memory provider used until the real institutional adapter exists."""

    def __init__(self, people: tuple[InstitutionalPerson, ...] = ()) -> None:
        self._people = {
            normalize_registration(person.registration): person for person in people
        }

    def find_by_registration(self, registration: str) -> InstitutionalPerson | None:
        return self._people.get(normalize_registration(registration))


_LOCAL_PEOPLE = (
    InstitutionalPerson(
        registration="20260001",
        full_name="Aluno Institucional de Teste",
        person_type="ALUNO",
        email="aluno.teste@cest.edu.br",
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


def get_institutional_person_provider() -> InstitutionalPersonProvider:
    return local_institutional_person_provider
