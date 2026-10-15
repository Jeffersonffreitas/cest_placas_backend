"""Compatibility name for student-facing code.

Students are persisted as ``Person`` rows with ``person_type='ALUNO'``. The
alias keeps imports used by older callers working without registering a
``tblalunos`` table in SQLAlchemy metadata.
"""

from app.models.person import Person


Student = Person

__all__ = ["Student"]

