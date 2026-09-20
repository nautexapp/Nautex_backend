import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint

from app.db.base import Base


class School(Base):
    """Escuela cliente. Centraliza sus particularidades."""

    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    particularities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    registration_codes: Mapped[list["RegistrationCode"]] = relationship(back_populates="school")
    users: Mapped[list["User"]] = relationship(back_populates="school")


class Course(Base):
    """Curso que sigue el alumno. Contiene el índice de documentos en Azure Blob."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Índice de contenidos: { tests: [], apuntes: [], examenes: [], documentos: [] }
    documents: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    registration_codes: Mapped[list["RegistrationCode"]] = relationship(back_populates="course")
    users: Mapped[list["User"]] = relationship(back_populates="course")


class RegistrationCode(Base):
    """Código de alta que entrega la escuela a cada alumno."""

    __tablename__ = "registration_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=True, index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    school: Mapped["School | None"] = relationship(back_populates="registration_codes")
    course: Mapped["Course | None"] = relationship(back_populates="registration_codes")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    google_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False, server_default='{}')
    school_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True, index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    school: Mapped["School | None"] = relationship(back_populates="users")
    course: Mapped["Course | None"] = relationship(back_populates="users")

    @property
    def entra_id(self) -> str:
        return self.google_id



