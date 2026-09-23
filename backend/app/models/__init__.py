from app.models.entities import (  # noqa: F401
    Alert,
    Asset,
    AssetComponent,
    AssetIdentifier,
    AssetModel,
    DataSource,
    EnvironmentObservation,
    IngestionRun,
    LegacyInspection,
    LegacyMaintenance,
    ModelRegistry,
    Prediction,
)

# New operational models for full workflow
# Note: LegacyInspection and LegacyMaintenance will be migrated to new models
from app.models.operational import (  # noqa: F401
    AIAssistantAudit,
    AssetAssignment,
    AssetPlan,
    AssetReview,
    AuditLog,
    EvidenceRevision,
    Inspection,
    InspectionAssignment,
    InspectionComponent,
    InspectionDefect,
    InspectionDocument,
    LoginAudit,
    Maintenance,
    MaintenanceComponent,
    MaintenanceDocument,
    MaintenanceProgress,
    Notification,
    PasswordResetToken,
    PlanDocument,
    PlanStatusHistory,
    RolePermission,
    User,
    UserSession,
)

