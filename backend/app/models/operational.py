from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


# ============================================================
# Authentication & User Management
# ============================================================


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    officer_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="OFFICER", index=True)
    department: Mapped[str | None] = mapped_column(String(200))
    designation: Mapped[str | None] = mapped_column(String(200))
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    login_count: Mapped[int] = mapped_column(Integer, default=0)


class UserSession(Base, TimestampMixin):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship()


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship()


class LoginAudit(Base):
    __tablename__ = "login_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(30), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship()


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(30), index=True)
    permission: Mapped[str] = mapped_column(String(100), index=True)
    resource: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("role", "permission", "resource"),)


# ============================================================
# Asset Workflow
# ============================================================


class AssetAssignment(Base, TimestampMixin):
    __tablename__ = "asset_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assignment_type: Mapped[str] = mapped_column(String(50), index=True)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    asset: Mapped["Asset"] = relationship("Asset")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    assigned_by_user: Mapped[User] = relationship(foreign_keys=[assigned_by])


class AssetReview(Base, TimestampMixin):
    __tablename__ = "asset_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    review_type: Mapped[str] = mapped_column(String(50))
    inspection_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    condition: Mapped[str | None] = mapped_column(String(30))
    observation: Mapped[str | None] = mapped_column(Text)
    components_inspected: Mapped[list[str] | None] = mapped_column(JSONB)
    recommendation: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")

    asset: Mapped["Asset"] = relationship("Asset")
    reviewer: Mapped[User] = relationship()


# ============================================================
# Inspection Workflow
# ============================================================


class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    asset_code: Mapped[str] = mapped_column(String(50), index=True)
    inspection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    scheduled_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    inspection_agency: Mapped[str | None] = mapped_column(String(200))
    inspection_type: Mapped[str] = mapped_column(String(50), index=True)
    assigned_officer: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[str] = mapped_column(String(30), default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED", index=True)

    # Condition fields
    deck_condition: Mapped[str | None] = mapped_column(String(30))
    superstructure_condition: Mapped[str | None] = mapped_column(String(30))
    substructure_condition: Mapped[str | None] = mapped_column(String(30))
    foundation_condition: Mapped[str | None] = mapped_column(String(30))
    scour_condition: Mapped[str | None] = mapped_column(String(30))
    bearing_condition: Mapped[str | None] = mapped_column(String(30))
    joint_condition: Mapped[str | None] = mapped_column(String(30))

    overall_condition: Mapped[str | None] = mapped_column(String(30))
    defect_count: Mapped[int] = mapped_column(Integer, default=0)
    max_defect_severity: Mapped[str | None] = mapped_column(String(30))

    observation: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")

    asset: Mapped["Asset"] = relationship("Asset")
    assigned_officer_user: Mapped[User] = relationship(foreign_keys=[assigned_officer])
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by])
    reviewed_by_user: Mapped[User] = relationship(foreign_keys=[reviewed_by])


class InspectionComponent(Base, TimestampMixin):
    __tablename__ = "inspection_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    component_name: Mapped[str] = mapped_column(String(100))
    component_type: Mapped[str] = mapped_column(String(50))
    condition: Mapped[str | None] = mapped_column(String(30))
    observation: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    inspection: Mapped[Inspection] = relationship()


class InspectionDefect(Base, TimestampMixin):
    __tablename__ = "inspection_defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("inspection_components.id"))
    defect_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30), index=True)
    measurement: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    location: Mapped[str | None] = mapped_column(Text)
    observation: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)

    inspection: Mapped[Inspection] = relationship()
    component: Mapped[InspectionComponent] = relationship()


class InspectionDocument(Base, TimestampMixin):
    __tablename__ = "inspection_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    checksum: Mapped[str] = mapped_column(String(128))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    inspection: Mapped[Inspection] = relationship()
    uploader: Mapped[User] = relationship()


class InspectionAssignment(Base, TimestampMixin):
    __tablename__ = "inspection_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assignment_type: Mapped[str] = mapped_column(String(50))
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    inspection: Mapped[Inspection] = relationship()
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    assigned_by_user: Mapped[User] = relationship(foreign_keys=[assigned_by])


# ============================================================
# Maintenance Workflow
# ============================================================


class Maintenance(Base, TimestampMixin):
    __tablename__ = "maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    asset_code: Mapped[str] = mapped_column(String(50), index=True)
    maintenance_type: Mapped[str] = mapped_column(String(50), index=True)
    component: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(30), default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(30), default="PROPOSED", index=True)

    problem: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    proposed_action: Mapped[str | None] = mapped_column(Text)

    assigned_department: Mapped[str | None] = mapped_column(String(200))
    contractor: Mapped[str | None] = mapped_column(String(200))
    estimated_cost: Mapped[float | None] = mapped_column(Integer)
    actual_cost: Mapped[float | None] = mapped_column(Integer)

    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    completion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress: Mapped[int] = mapped_column(Integer, default=0)

    related_inspection_id: Mapped[int | None] = mapped_column(ForeignKey("inspections.id"))
    related_plan_id: Mapped[int | None] = mapped_column(ForeignKey("asset_plans.id"))

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verification_status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")

    asset: Mapped["Asset"] = relationship("Asset")
    related_inspection: Mapped[Inspection] = relationship()
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by])
    reviewed_by_user: Mapped[User] = relationship(foreign_keys=[reviewed_by])


class MaintenanceDocument(Base, TimestampMixin):
    __tablename__ = "maintenance_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("maintenance.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    checksum: Mapped[str] = mapped_column(String(128))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    maintenance: Mapped[Maintenance] = relationship()
    uploader: Mapped[User] = relationship()


class MaintenanceProgress(Base, TimestampMixin):
    __tablename__ = "maintenance_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("maintenance.id", ondelete="CASCADE"), index=True)
    progress_percentage: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    maintenance: Mapped[Maintenance] = relationship()
    updater: Mapped[User] = relationship()


class MaintenanceComponent(Base, TimestampMixin):
    __tablename__ = "maintenance_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("maintenance.id", ondelete="CASCADE"), index=True)
    component_name: Mapped[str] = mapped_column(String(100))
    component_type: Mapped[str] = mapped_column(String(50))
    work_description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")

    maintenance: Mapped[Maintenance] = relationship()


# ============================================================
# Action Plans
# ============================================================


class AssetPlan(Base, TimestampMixin):
    __tablename__ = "asset_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    asset_code: Mapped[str] = mapped_column(String(50), index=True)
    plan_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(30), default="MEDIUM", index=True)

    problem_identified: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    proposed_action: Mapped[str | None] = mapped_column(Text)
    affected_components: Mapped[list[str] | None] = mapped_column(JSONB)

    proposed_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposed_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_cost: Mapped[float | None] = mapped_column(Integer)
    department: Mapped[str | None] = mapped_column(String(200))

    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    asset: Mapped["Asset"] = relationship("Asset")
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by])
    reviewed_by_user: Mapped[User] = relationship(foreign_keys=[reviewed_by])
    approved_by_user: Mapped[User] = relationship(foreign_keys=[approved_by])


class PlanStatusHistory(Base, TimestampMixin):
    __tablename__ = "plan_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("asset_plans.id", ondelete="CASCADE"), index=True)
    old_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[AssetPlan] = relationship()
    changed_by_user: Mapped[User] = relationship()


class PlanDocument(Base, TimestampMixin):
    __tablename__ = "plan_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("asset_plans.id", ondelete="CASCADE"), index=True)
    document_type: Mapped[str] = mapped_column(String(50))
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(Text)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    checksum: Mapped[str] = mapped_column(String(128))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    plan: Mapped[AssetPlan] = relationship()
    uploader: Mapped[User] = relationship()


# ============================================================
# Notifications
# ============================================================


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    notification_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(30), default="INFO", index=True)
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)

    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    inspection_id: Mapped[int | None] = mapped_column(ForeignKey("inspections.id"))
    maintenance_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance.id"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("asset_plans.id"))

    link: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()
    asset: Mapped["Asset"] = relationship("Asset")
    inspection: Mapped[Inspection] = relationship()
    maintenance: Mapped[Maintenance] = relationship()
    plan: Mapped[AssetPlan] = relationship()


# ============================================================
# Audit Log
# ============================================================


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship()

    __table_args__ = (
        Index("ix_audit_log_user_action", "user_id", "action"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )


# ============================================================
# AI Assistant Audit
# ============================================================


class AIAssistantAudit(Base):
    __tablename__ = "ai_assistant_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    asset_code: Mapped[str] = mapped_column(String(50), index=True)
    question: Mapped[str] = mapped_column(Text)
    assessment_id: Mapped[str | None] = mapped_column(String(100))
    evidence_ids: Mapped[list[int] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(100))
    response: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship()


# ============================================================
# Evidence Versioning
# ============================================================


class EvidenceRevision(Base, TimestampMixin):
    __tablename__ = "evidence_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    field_name: Mapped[str] = mapped_column(String(120), index=True)
    old_value: Mapped[Any] = mapped_column(JSONB)
    new_value: Mapped[Any] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(200))
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    review_status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    asset: Mapped["Asset"] = relationship("Asset")
    submitted_by_user: Mapped[User] = relationship(foreign_keys=[submitted_by])
    reviewed_by_user: Mapped[User] = relationship(foreign_keys=[reviewed_by])
