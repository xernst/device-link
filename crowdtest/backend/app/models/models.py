"""SQLAlchemy models matching the data model from plan.md §7."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def gen_uuid():
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    hashed_password = Column(String(255))
    plan = Column(String(50), default="free")  # free, starter, pro, enterprise
    stripe_customer_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    industry = Column(String(100))
    target_audience_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="projects")
    materials = relationship("Material", back_populates="project")
    persona_packs = relationship("PersonaPack", back_populates="project")
    simulations = relationship("Simulation", back_populates="project")


class Material(Base):
    __tablename__ = "materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    type = Column(String(50), nullable=False)  # ad_copy, landing_page, email, social_post
    title = Column(String(255))
    content = Column(Text, nullable=False)
    platform = Column(String(50))
    variant_label = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="materials")


class PersonaPack(Base):
    __tablename__ = "persona_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    archetype_distribution = Column(JSON)  # {"skeptic": 0.2, "early_adopter": 0.3, ...}
    demographic_config = Column(JSON)
    custom_overrides = Column(JSON)
    generated_personas = Column(JSON)  # full persona list after LLM enrichment
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="persona_packs")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    persona_pack_id = Column(UUID(as_uuid=True), ForeignKey("persona_packs.id"))
    status = Column(String(20), default="queued")  # queued, running, complete, failed
    config = Column(JSON)  # {crowd_size, platform, reach_mode}
    material_ids = Column(JSON)  # list of material UUIDs
    results = Column(JSON)  # {scores, feed, recommendations}
    social_graph = Column(JSON)  # {nodes, edges}
    turn_log = Column(JSON)  # per-turn events
    duration_ms = Column(Integer)
    token_cost = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="simulations")
