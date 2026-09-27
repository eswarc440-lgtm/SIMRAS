import fs from "node:fs";
import path from "node:path";
import { RegistrationStore } from './registrationStore';

export interface AssetRecord {
  status?: string;
  created_by?: string;
  created_at?: string;
  assessment_status?: string;
  asset_code: string;
  name: string;
  asset_type: "dam" | "barrage" | "bridge" | "airport" | "temple";
  subtype?: string;
  district: string;
  latitude: number;
  longitude: number;
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lng, lat]
  };
  priority: number;
  visual_strategy: string;
  dimension_authority: string;
  fidelity_status: string;
  dimension_status: string;
  dimensions: Record<string, any>;
  built_year: number;
  material: string;
  condition: string;
  health_score: number;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  rul_years: number;
  assessment_basis: string;
  source_url?: string;
  identity_status: "VERIFIED" | "PENDING_VERIFICATION" | "REJECTED";
}

export interface UserRecord {
  id: string;
  email: string;
  name: string;
  role: "PUBLIC" | "OFFICER" | "REVIEWER" | "ADMIN";
  department: string;
  phone?: string;
  created_at: string;
  district?: string;
  photo_url?: string;
  last_login?: string;
}

export interface InspectionRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  inspector_name: string;
  inspector_email: string;
  inspection_type: "ROUTINE" | "STRUCTURAL_AUDIT" | "SPECIAL_EVENT" | "POST_FLOOD";
  inspection_date: string;
  condition_rating: "EXCELLENT" | "GOOD" | "FAIR" | "POOR" | "CRITICAL";
  findings: string;
  defects: Array<{ component: string; severity: "MINOR" | "MODERATE" | "SEVERE"; description: string }>;
  recommended_actions: string;
  status: "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";
  reviewer_comments?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface MaintenanceRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  title: string;
  category: "PREVENTIVE" | "CORRECTIVE" | "REHABILITATION" | "EMERGENCY";
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  scheduled_start: string;
  scheduled_end: string;
  actual_completed?: string;
  cost_inr_lakhs?: number;
  assigned_contractor_or_team: string;
  work_description: string;
  status: "PLANNED" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED";
  verification_notes?: string;
  created_at: string;
}

export interface NotificationRecord {
  id: string;
  title: string;
  message: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  category: "ALERT" | "INSPECTION" | "MAINTENANCE" | "REVIEW";
  asset_code?: string;
  read: boolean;
  timestamp: string;
  type?: string;
  entity_id?: string;
  created_at?: string;
  read_at?: string | null;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  action_url?: string;
}

export interface StructuralSensor {
  id: string;
  name: string;
  type: "PIEZOMETER" | "STRAIN_GAUGE" | "INCLINOMETER" | "SCOUR_SENSOR" | "CRACK_GAUGE" | "VIBRATION" | "SURFACE_FRICTION";
  value: number;
  unit: string;
  threshold: number;
  status: "NORMAL" | "WARNING" | "CRITICAL";
  position: [number, number, number]; // [x, y, z] relative to 3D model
}

export interface TelemetryFeedRecord {
  asset_code: string;
  last_sync: string;
  sources: string[];
  water_level_m: number;
  max_water_level_m: number;
  storage_percent: number;
  storage_tmc?: number;
  inflow_cusecs: number;
  outflow_cusecs: number;
  gates_open: number;
  total_gates: number;
  gate_clearance_m: number;
  weather: {
    condition: "CLEAR" | "OVERCAST" | "RAIN" | "MONSOON_STORM";
    precipitation_mm_hr: number;
    wind_speed_kmh: number;
    temperature_c: number;
  };
  structural_sensors: StructuralSensor[];
  history_24h: Array<{
    time: string;
    water_level_m: number;
    inflow_cusecs: number;
    outflow_cusecs: number;
    strain_microstrain?: number;
  }>;
}

export interface CitizenHazardObservationRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  reporter_name: string;
  reporter_phone?: string;
  observation_type: "WATER_OVERFLOW" | "DEBRIS_JAM" | "STRUCTURAL_CRACK" | "EROSION_SCOUR" | "GATE_MALFUNCTION" | "SURFACE_POTHOLE";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string;
  coordinates_3d: [number, number, number];
  verified_by_officer: boolean;
  reported_at: string;
}

export interface SearchResultRecord {
  type: "asset" | "inspection" | "maintenance" | "report";
  id: string;
  title: string;
  subtitle: string;
  asset_code?: string;
  action_url: string;
}

// In-Memory durable store with local file fallback
class SimrasDatabase {
  private assets: Map<string, AssetRecord> = new Map();
  private users: Map<string, UserRecord> = new Map();
  private inspections: Map<string, InspectionRecord> = new Map();
  private maintenance: Map<string, MaintenanceRecord> = new Map();
  private notifications: Map<string, NotificationRecord> = new Map();
  private telemetry: Map<string, TelemetryFeedRecord> = new Map();
  private observations: Map<string, CitizenHazardObservationRecord> = new Map();
  private preferences: Map<string, Record<string, any>> = new Map();
  private registrations: RegistrationStore;

  constructor() {
    if (process.env.NODE_ENV === 'production' && !process.env.SIMRAS_BACKEND_URL && !process.env.SIMRAS_DATA_DIR) throw new Error('SIMRAS_DATA_DIR must point to a persistent disk in production');
    this.registrations = new RegistrationStore(process.env.VITEST ? ':memory:' : path.resolve(process.env.SIMRAS_DATA_DIR || 'data/runtime', 'registrations.sqlite3'));
    this.initAssets();
    this.initUsers();
    this.initInspections();
    this.initMaintenance();
    this.initNotifications();
    this.initTelemetry();
    this.initObservations();
    for (const asset of this.registrations.list()) this.assets.set(asset.asset_code,asset);
  }

  private initAssets() {
    try {
      const jsonPath = path.resolve(process.cwd(), "data/canonical_assets_194.json");
      if (fs.existsSync(jsonPath)) {
        const raw = fs.readFileSync(jsonPath, "utf-8");
        const list: AssetRecord[] = JSON.parse(raw);
        for (const a of list) {
          this.assets.set(a.asset_code, a);
        }
      }
    } catch (e) {
      console.error("Failed to load canonical_assets_194.json:", e);
    }
  }

  private initUsers() {
    const defaultUsers: UserRecord[] = [
      {
        id: "usr-admin",
        email: "admin@simras.gov.in",
        name: "Srikanth Rao",
        role: "ADMIN",
        department: "Andhra Pradesh Disaster Management & Infrastructure Authority",
        phone: "+91 866 242 5001",
        created_at: "2026-01-15T00:00:00Z",
      },
      {
        id: "usr-officer",
        email: "officer@simras.gov.in",
        name: "A. K. Sharma",
        role: "OFFICER",
        department: "Water Resources Department (APWRD) / Roads & Buildings",
        phone: "+91 866 242 5002",
        created_at: "2026-01-15T00:00:00Z",
      },
      {
        id: "usr-reviewer",
        email: "reviewer@simras.gov.in",
        name: "Dr. P. V. Reddy",
        role: "REVIEWER",
        department: "State Technical Audit & Dam Safety Organisation",
        phone: "+91 866 242 5003",
        created_at: "2026-01-15T00:00:00Z",
      },
      {
        id: "usr-public",
        email: "public@simras.gov.in",
        name: "Citizen Observer",
        role: "PUBLIC",
        department: "Public Information Portal",
        created_at: "2026-01-15T00:00:00Z",
      },
    ];

    for (const u of defaultUsers) {
      this.users.set(u.email.toLowerCase(), u);
    }
  }

  private initInspections() {
    const seedInspections: InspectionRecord[] = [
      {
        id: "INSP-2026-001",
        asset_code: "AP_DAM_00001",
        asset_name: "Prakasam Barrage",
        inspector_name: "A. K. Sharma",
        inspector_email: "officer@simras.gov.in",
        inspection_type: "STRUCTURAL_AUDIT",
        inspection_date: "2026-02-10",
        condition_rating: "FAIR",
        findings: "Annual pre-monsoon inspection of 70 regulator gates and scouring sluices. Sluice gate #14 operating mechanism exhibits minor gear backlash. Spillway apron concrete shows localized minor cavitation erosion.",
        defects: [
          { component: "Gate 14 Gearbox", severity: "MODERATE", description: "Tooth wear on bevel gear drive, requiring pinion adjustment." },
          { component: "Left Scour Sluice Stilling Basin", severity: "MINOR", description: "Superficial concrete scaling (<20mm depth) on baffle blocks." },
        ],
        recommended_actions: "Procure replacement bevel gears for gate #14 hoist. Apply silica-fume epoxy mortar patch on baffle blocks.",
        status: "APPROVED",
        reviewer_comments: "Inspection methodology aligns with CWC Guidelines for Dam Safety Inspection. Maintenance work order sanctioned.",
        reviewed_by: "Dr. P. V. Reddy",
        reviewed_at: "2026-02-14T11:30:00Z",
        created_at: "2026-02-10T16:00:00Z",
      },
      {
        id: "INSP-2026-002",
        asset_code: "AP_BR_00001",
        asset_name: "Godavari Arch Bridge",
        inspector_name: "A. K. Sharma",
        inspector_email: "officer@simras.gov.in",
        inspection_type: "ROUTINE",
        inspection_date: "2026-01-22",
        condition_rating: "GOOD",
        findings: "Visual and non-destructive ultrasonic inspection across 28 prestressed concrete bowstring arches. Hanger cable anchorages intact with protective grease seals in good condition. Pier 12 foundation scour profile normal.",
        defects: [
          { component: "Span 7 Hanger 4", severity: "MINOR", description: "Protective polyurethane topcoat weathering on lower socket shroud." }
        ],
        recommended_actions: "Recoat hanger cable socket shrouds on Spans 6-8 during scheduled track possession.",
        status: "APPROVED",
        reviewer_comments: "Approved. No structural load reduction required.",
        reviewed_by: "Dr. P. V. Reddy",
        reviewed_at: "2026-01-25T14:15:00Z",
        created_at: "2026-01-22T17:00:00Z",
      },
      {
        id: "INSP-2026-003",
        asset_code: "AP_BR_00002",
        asset_name: "Kanaka Durga Flyover",
        inspector_name: "A. K. Sharma",
        inspector_email: "officer@simras.gov.in",
        inspection_type: "ROUTINE",
        inspection_date: "2026-02-05",
        condition_rating: "EXCELLENT",
        findings: "Comprehensive inspection of 48 segmental spine-and-wing spans along the 2.6 km corridor. Elastomeric expansion joints functional with free thermal articulation. Drainage spouts clear.",
        defects: [],
        recommended_actions: "Routine sweeping and camera calibration.",
        status: "APPROVED",
        reviewer_comments: "Asset in prime operational state.",
        reviewed_by: "Dr. P. V. Reddy",
        reviewed_at: "2026-02-08T09:00:00Z",
        created_at: "2026-02-05T12:00:00Z",
      },
      {
        id: "INSP-2026-004",
        asset_code: "AP_TEMPLE_SRIKALAHASTI",
        asset_name: "Sri Kalahasteeswara Swamy Temple",
        inspector_name: "A. K. Sharma",
        inspector_email: "officer@simras.gov.in",
        inspection_type: "SPECIAL_EVENT",
        inspection_date: "2026-03-01",
        condition_rating: "FAIR",
        findings: "Structural audit of southern gopuram stone tiers and 100-pillared mandapam prior to Maha Shivaratri festival gathering. Minor lime-mortar leaching observed on outer vimana parapet.",
        defects: [
          { component: "Southern Gopuram Tier 3 Parapet", severity: "MODERATE", description: "Mortar repointing required to prevent rainwater penetration into core masonry." }
        ],
        recommended_actions: "Deploy traditional heritage-compatible lime-pozzolana grouting under Endowments Department supervision.",
        status: "SUBMITTED",
        created_at: "2026-03-01T15:30:00Z",
      }
    ];

    for (const insp of seedInspections) {
      this.inspections.set(insp.id, insp);
    }
  }

  private initMaintenance() {
    const seedMaintenance: MaintenanceRecord[] = [
      {
        id: "MAINT-2026-101",
        asset_code: "AP_DAM_00001",
        asset_name: "Prakasam Barrage",
        title: "Regulator Gate #14 Hoist Gear Replacement & Stilling Basin Mortar Patch",
        category: "CORRECTIVE",
        priority: "HIGH",
        scheduled_start: "2026-02-20",
        scheduled_end: "2026-03-15",
        cost_inr_lakhs: 18.5,
        assigned_contractor_or_team: "APWRD Mechanical Division, Vijayawada",
        work_description: "Dismantle defective bevel gear assembly on Gate #14, machine custom manganese-bronze pinion, reinstall and load-test. Apply high-strength epoxy underwater mortar on baffle block cavitation zone.",
        status: "IN_PROGRESS",
        created_at: "2026-02-15T10:00:00Z",
      },
      {
        id: "MAINT-2026-102",
        asset_code: "AP_DAM_NWDP_AP01VH0059",
        asset_name: "Srisailam Project (N.S.R.S.P)",
        title: "Crest Gate Hydraulic Actuator Seal Replacement & Drainage Gallery Flushing",
        category: "PREVENTIVE",
        priority: "MEDIUM",
        scheduled_start: "2026-01-10",
        scheduled_end: "2026-02-05",
        actual_completed: "2026-02-04",
        cost_inr_lakhs: 42.0,
        assigned_contractor_or_team: "KRMB Engineering Safety Wing",
        work_description: "Overhaul all 12 radial crest gate hydraulic cylinders, replace high-pressure elastomeric seals, clear silt accumulation in right-bank foundation relief wells.",
        status: "VERIFIED",
        verification_notes: "Hydraulic pressure testing sustained at 210 bar with zero leakage. Completed ahead of schedule.",
        created_at: "2026-01-05T09:00:00Z",
      },
      {
        id: "MAINT-2026-103",
        asset_code: "AP_AIR_AAI_VIJAYAWADA",
        asset_name: "Vijayawada Airport",
        title: "Runway 08/26 Friction Restoration & High-Speed Exit Taxiway Resurfacing",
        category: "PREVENTIVE",
        priority: "HIGH",
        scheduled_start: "2026-03-10",
        scheduled_end: "2026-04-05",
        cost_inr_lakhs: 125.0,
        assigned_contractor_or_team: "AAI Civil Engineering Wing, Southern Region",
        work_description: "High-pressure water hydro-jet rubber removal across landing touchdown zone on Runway 08/26. Apply polymer-modified bitumen wearing course on Taxiway Bravo.",
        status: "PLANNED",
        created_at: "2026-02-28T14:00:00Z",
      }
    ];

    for (const m of seedMaintenance) {
      this.maintenance.set(m.id, m);
    }
  }

  private initNotifications() {
    // Workflow mutations create notifications; production startup does not seed demo alerts.
  }

  // Assets
  public getAssets(options: {
    asset_type?: string;
    district?: string;
    search?: string;
    priority?: number;
    sort_by?: "risk_score" | "health_score" | "name";
    limit?: number;
    offset?: number;
  }) {
    let items = Array.from(this.assets.values()).filter((asset) => asset.identity_status === "VERIFIED");

    if (options.asset_type && options.asset_type !== "all") {
      const t = options.asset_type.toLowerCase();
      items = items.filter((a) => a.asset_type.toLowerCase() === t);
    }

    if (options.district && options.district !== "all") {
      const d = options.district.toLowerCase();
      items = items.filter((a) => a.district.toLowerCase() === d);
    }

    if (options.priority) {
      items = items.filter((a) => a.priority === options.priority);
    }

    if (options.search) {
      const q = options.search.toLowerCase().trim();
      items = items.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          a.asset_code.toLowerCase().includes(q) ||
          a.district.toLowerCase().includes(q)
      );
    }

    // Sorting
    const sortBy = options.sort_by ?? "risk_score";
    if (sortBy === "risk_score") {
      items.sort((a, b) => b.risk_score - a.risk_score);
    } else if (sortBy === "health_score") {
      items.sort((a, b) => b.health_score - a.health_score);
    } else if (sortBy === "name") {
      items.sort((a, b) => a.name.localeCompare(b.name));
    }

    const total = items.length;
    const offset = Math.max(0, options.offset ?? 0);
    const limit = Math.max(1, Math.min(1000, options.limit ?? 100));
    const paginated = items.slice(offset, offset + limit);

    return { items: paginated, total, limit, offset };
  }

  public getAsset(code: string): AssetRecord | undefined {
    return this.assets.get(code);
  }

  public getPublicAsset(code: string): AssetRecord | undefined {
    const asset = this.getAsset(code);
    return asset?.identity_status === "VERIFIED" ? asset : undefined;
  }

  public addAsset(asset: AssetRecord): AssetRecord {
    if (this.assets.has(asset.asset_code)) {
      throw new Error(`Asset code ${asset.asset_code} already exists.`);
    }
    this.registrations.create(asset);
    this.assets.set(asset.asset_code, asset);
    return asset;
  }

  public getRegistrations() { return this.registrations.list(); }
  public reviewRegistration(code: string, user: UserRecord, decision: string, comments: string) {
    const asset = this.registrations.review(code,user,decision,comments);
    this.assets.set(code,asset);
    return asset;
  }

  // Users
  public getUser(email: string): UserRecord | undefined {
    return this.users.get(email.toLowerCase());
  }

  public upsertUser(user: UserRecord): UserRecord {
    this.users.set(user.email.toLowerCase(), user);
    return user;
  }

  public updateUser(email: string, patch: Partial<Pick<UserRecord, "name" | "phone" | "district">>): UserRecord {
    const user = this.getUser(email);
    if (!user) throw new Error("User not found");
    const next = { ...user, name: patch.name ?? user.name, phone: patch.phone ?? user.phone, district: patch.district ?? user.district };
    this.users.set(email.toLowerCase(), next);
    return next;
  }

  public setUserPhoto(email: string, photoUrl?: string): UserRecord {
    const user = this.getUser(email);
    if (!user) throw new Error("User not found");
    user.photo_url = photoUrl;
    return user;
  }

  public getPreferences(userId: string) { return this.preferences.get(userId) ?? {}; }
  public updatePreferences(userId: string, patch: Record<string, any>) {
    const current = this.getPreferences(userId);
    const next = { ...current };
    for (const [section, value] of Object.entries(patch)) next[section] = { ...(current[section] ?? {}), ...(value as object) };
    this.preferences.set(userId, next);
    return next;
  }

  public search(query: string): Record<"assets" | "inspections" | "maintenance" | "reports", SearchResultRecord[]> {
    const needle = query.trim().toLowerCase();
    const matches = (...values: unknown[]) => values.some((value) => String(value ?? "").toLowerCase().includes(needle));
    const assets = Array.from(this.assets.values()).filter((asset) => asset.identity_status === "VERIFIED" && matches(asset.name, asset.asset_code, asset.district, asset.asset_type)).slice(0, 8).map((asset) => ({ type: "asset" as const, id: asset.asset_code, title: asset.name, subtitle: `${asset.asset_code} Â· ${asset.district}`, asset_code: asset.asset_code, action_url: `/digital-twin?asset=${encodeURIComponent(asset.asset_code)}` }));
    const inspections = Array.from(this.inspections.values()).filter((record) => matches(record.id, record.asset_name, record.inspection_type)).slice(0, 8).map((record) => ({ type: "inspection" as const, id: record.id, title: record.id, subtitle: `${record.asset_name} Â· ${record.inspection_type}`, asset_code: record.asset_code, action_url: `/inspections?asset=${encodeURIComponent(record.asset_code)}` }));
    const maintenance = Array.from(this.maintenance.values()).filter((record) => matches(record.id, record.title, record.asset_name, record.category)).slice(0, 8).map((record) => ({ type: "maintenance" as const, id: record.id, title: record.id, subtitle: `${record.title} Â· ${record.asset_name}`, asset_code: record.asset_code, action_url: `/maintenance?asset=${encodeURIComponent(record.asset_code)}` }));
    return { assets, inspections, maintenance, reports: [] };
  }

  // Inspections
  public getInspections(asset_code?: string): InspectionRecord[] {
    const list = Array.from(this.inspections.values());
    if (asset_code) {
      return list.filter((i) => i.asset_code === asset_code);
    }
    return list.sort((a, b) => b.inspection_date.localeCompare(a.inspection_date));
  }

  public addInspection(insp: Omit<InspectionRecord, "id" | "created_at">): InspectionRecord {
    const id = `INSP-2026-${String(this.inspections.size + 1).padStart(3, "0")}`;
    const record: InspectionRecord = {
      ...insp,
      id,
      created_at: new Date().toISOString(),
    };
    this.inspections.set(id, record);

    // Create notification
    this.addNotification({
      title: `New Inspection Logged: ${record.asset_name}`,
      message: `Inspection ${id} logged by ${record.inspector_name}. Status: ${record.status}.`,
      severity: record.condition_rating === "POOR" || record.condition_rating === "CRITICAL" ? "WARNING" : "INFO",
      category: "INSPECTION",
      asset_code: record.asset_code,
    });

    return record;
  }

  public updateInspectionStatus(
    id: string,
    status: "APPROVED" | "REJECTED",
    reviewer_comments: string,
    reviewed_by: string
  ): InspectionRecord {
    const record = this.inspections.get(id);
    if (!record) {
      throw new Error(`Inspection ${id} not found`);
    }
    record.status = status;
    record.reviewer_comments = reviewer_comments;
    record.reviewed_by = reviewed_by;
    record.reviewed_at = new Date().toISOString();
    this.inspections.set(id, record);

    this.addNotification({
      title: `Inspection ${id} ${status}`,
      message: `Reviewed by ${reviewed_by}. Comments: ${reviewer_comments}`,
      severity: "INFO",
      category: "REVIEW",
      asset_code: record.asset_code,
    });

    return record;
  }

  // Maintenance
  public getMaintenance(asset_code?: string): MaintenanceRecord[] {
    const list = Array.from(this.maintenance.values());
    if (asset_code) {
      return list.filter((m) => m.asset_code === asset_code);
    }
    return list.sort((a, b) => b.scheduled_start.localeCompare(a.scheduled_start));
  }

  public addMaintenance(maint: Omit<MaintenanceRecord, "id" | "created_at">): MaintenanceRecord {
    const id = `MAINT-2026-${String(this.maintenance.size + 1).padStart(3, "0")}`;
    const record: MaintenanceRecord = {
      ...maint,
      id,
      created_at: new Date().toISOString(),
    };
    this.maintenance.set(id, record);

    this.addNotification({
      title: `New Maintenance Plan: ${record.title}`,
      message: `Scheduled for ${record.asset_name} starting ${record.scheduled_start}.`,
      severity: record.priority === "URGENT" || record.priority === "HIGH" ? "WARNING" : "INFO",
      category: "MAINTENANCE",
      asset_code: record.asset_code,
    });

    return record;
  }

  public updateMaintenanceStatus(
    id: string,
    status: MaintenanceRecord["status"],
    notes?: string
  ): MaintenanceRecord {
    const record = this.maintenance.get(id);
    if (!record) {
      throw new Error(`Maintenance ${id} not found`);
    }
    record.status = status;
    if (notes) record.verification_notes = notes;
    if (status === "COMPLETED" || status === "VERIFIED") {
      record.actual_completed = new Date().toISOString().split("T")[0];
    }
    this.maintenance.set(id, record);
    return record;
  }

  // Notifications
  public getNotifications(role: UserRecord['role']): NotificationRecord[] {
    const registrationEvents = ['REVIEWER','ADMIN'].includes(role) ? this.registrations.notifications() : [];
    return [...this.notifications.values(),...registrationEvents].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  }

  public addNotification(notif: Omit<NotificationRecord, "id" | "read" | "timestamp">): NotificationRecord {
    const id = `NOTIF-${String(this.notifications.size + 1).padStart(3, "0")}`;
    const record: NotificationRecord = {
      ...notif,
      id,
      read: false,
      timestamp: new Date().toISOString(),
      created_at: new Date().toISOString(),
      read_at: null,
      type: notif.type ?? `${notif.category}_EVENT`,
      priority: notif.priority ?? (notif.severity === "CRITICAL" ? "CRITICAL" : notif.severity === "WARNING" ? "HIGH" : "LOW"),
      action_url: notif.action_url ?? (notif.asset_code ? `/digital-twin?asset=${encodeURIComponent(notif.asset_code)}` : "/notifications"),
    };
    this.notifications.set(id, record);
    return record;
  }

  public markNotificationRead(id: string, role: UserRecord['role']): boolean {
    if (id.startsWith('REG-')) return ['REVIEWER','ADMIN'].includes(role) && this.registrations.markRead(id);
    const record = this.notifications.get(id);
    if (record) {
      record.read = true;
      record.read_at = new Date().toISOString();
      return true;
    }
    return false;
  }

  public markAllNotificationsRead(role: UserRecord['role']): void {
    if (['REVIEWER','ADMIN'].includes(role)) this.registrations.markRead();
    for (const n of this.notifications.values()) {
      n.read = true;
      n.read_at = new Date().toISOString();
    }
  }

  public getUnreadCount(role: UserRecord['role']): number {
    return this.getNotifications(role).filter((notification) => !notification.read).length;
  }

  // ==========================================
  // REAL-WORLD TELEMETRY INGESTION (CWC, WRIS, IMD, IoT)
  // ==========================================
  private initTelemetry() {
    // Default baseline telemetry generator for assets
    for (const [code, asset] of this.assets.entries()) {
      const isDamOrBarrage = asset.asset_type === "dam" || asset.asset_type === "barrage";
      const isAirport = asset.asset_type === "airport";

      let waterLevel = 15.0;
      let maxWater = 18.0;
      let storagePct = 72;
      let gatesTotal = 0;
      let gatesOpen = 0;
      let gateClearance = 0;
      let inflow = 12500;
      let outflow = 11000;
      let weatherCond: "CLEAR" | "OVERCAST" | "RAIN" | "MONSOON_STORM" = "OVERCAST";
      let precip = 4.2;

      const sensors: StructuralSensor[] = [];

      if (code === "AP_DAM_00001") {
        // Prakasam Barrage
        waterLevel = 17.45;
        maxWater = 17.39; // Slightly above FRL, active flood monitoring!
        storagePct = 98.4;
        gatesTotal = 70;
        gatesOpen = 48;
        gateClearance = 2.4;
        inflow = 385000;
        outflow = 385000;
        weatherCond = "MONSOON_STORM";
        precip = 28.5;
        sensors.push(
          { id: "PZ-01", name: "Foundation Piezometer Bay 14", type: "PIEZOMETER", value: 142, unit: "kPa", threshold: 160, status: "NORMAL", position: [12, 1.2, 5] },
          { id: "PZ-02", name: "Right Flank Abutment Uplift", type: "PIEZOMETER", value: 168, unit: "kPa", threshold: 165, status: "WARNING", position: [-38, 2.5, 4] },
          { id: "SC-03", name: "Echo Scour Depth Meter Pier 22", type: "SCOUR_SENSOR", value: 3.8, unit: "m", threshold: 4.5, status: "WARNING", position: [-14, -1.8, 6] },
          { id: "ACC-01", name: "Spillway Pier Dynamic Vibration", type: "VIBRATION", value: 0.044, unit: "g", threshold: 0.08, status: "NORMAL", position: [6, 4.2, 2] },
        );
      } else if (code === "AP_DAM_00002") {
        // Polavaram Project
        waterLevel = 41.2;
        maxWater = 45.72;
        storagePct = 76.5;
        gatesTotal = 48;
        gatesOpen = 28;
        gateClearance = 3.2;
        inflow = 420000;
        outflow = 395000;
        weatherCond = "RAIN";
        precip = 16.8;
        sensors.push(
          { id: "INC-01", name: "ECRF Diaphragm Wall Inclinometer", type: "INCLINOMETER", value: 0.14, unit: "deg", threshold: 0.25, status: "NORMAL", position: [-22, 5.0, 2] },
          { id: "PPC-04", name: "Pore Pressure Cell Upstream Face", type: "PIEZOMETER", value: 310, unit: "kPa", threshold: 350, status: "NORMAL", position: [-15, 2.0, -8] },
          { id: "SG-02", name: "Spillway Pier Concrete Strain", type: "STRAIN_GAUGE", value: 48, unit: "ÂµÎµ", threshold: 85, status: "NORMAL", position: [25, 3.5, 12] },
        );
      } else if (code === "AP_DAM_NWDP_AP01VH0059") {
        // Srisailam Project
        waterLevel = 268.4;
        maxWater = 269.7;
        storagePct = 93.3;
        gatesTotal = 12;
        gatesOpen = 8;
        gateClearance = 3.5;
        inflow = 290000;
        outflow = 275000;
        weatherCond = "RAIN";
        precip = 12.0;
        sensors.push(
          { id: "PL-01", name: "Crest Deflection Plumb Line", type: "INCLINOMETER", value: 2.1, unit: "mm", threshold: 4.5, status: "NORMAL", position: [0, 8.0, 0] },
          { id: "PZ-08", name: "Deep Foundation Piezometer", type: "PIEZOMETER", value: 420, unit: "kPa", threshold: 500, status: "NORMAL", position: [10, 1.0, 3] },
        );
      } else if (isAirport) {
        weatherCond = "OVERCAST";
        precip = 1.2;
        sensors.push(
          { id: "FRIC-01", name: "Continuous Surface Friction Mu", type: "SURFACE_FRICTION", value: 0.64, unit: "Âµ", threshold: 0.50, status: "NORMAL", position: [0, 0.2, 0] },
          { id: "VIS-01", name: "Runway Visual Range RVR Transmissometer", type: "NORMAL" as any, value: 2400, unit: "m", threshold: 800, status: "NORMAL", position: [-40, 0.5, 6] },
        );
      } else if (isDamOrBarrage) {
        gatesTotal = Number(asset.dimensions?.gate_count ?? 16);
        gatesOpen = Math.round(gatesTotal * 0.4);
        gateClearance = 1.5;
        sensors.push(
          { id: "PZ-01", name: "Foundation Piezometer", type: "PIEZOMETER", value: 120, unit: "kPa", threshold: 160, status: "NORMAL", position: [0, 1.0, 2] },
          { id: "SG-01", name: "Concrete Pier Strain Sensor", type: "STRAIN_GAUGE", value: 35, unit: "ÂµÎµ", threshold: 80, status: "NORMAL", position: [8, 3.0, 4] },
        );
      } else {
        // Bridge / Heritage Temple
        sensors.push(
          { id: "SG-01", name: "Deck Dynamic Strain Gauge", type: "STRAIN_GAUGE", value: 42, unit: "ÂµÎµ", threshold: 90, status: "NORMAL", position: [0, 6.0, 0] },
          { id: "ACC-01", name: "Ambient Vibration Accelerometer", type: "VIBRATION", value: 0.028, unit: "g", threshold: 0.06, status: "NORMAL", position: [-15, 6.0, 0] },
        );
      }

      // Generate 24-hr history curve
      const history: TelemetryFeedRecord["history_24h"] = [];
      const now = Date.now();
      for (let i = 24; i >= 0; i--) {
        const t = new Date(now - i * 3600 * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const variation = Math.sin(i / 3.5) * 0.4;
        history.push({
          time: t,
          water_level_m: Number((waterLevel + variation).toFixed(2)),
          inflow_cusecs: Math.round(inflow * (1 + variation * 0.15)),
          outflow_cusecs: Math.round(outflow * (1 + variation * 0.12)),
          strain_microstrain: Math.round(40 + variation * 8),
        });
      }

      this.telemetry.set(code, {
        asset_code: code,
        last_sync: new Date().toISOString(),
        sources: [
          "India WRIS (Water Resources Information System)",
          "Central Water Commission (CWC) Daily Telemetry Bulletin",
          "IMD Doppler Weather Radar Network",
          "AP State Disaster Management Real-Time IoT Grid",
        ],
        water_level_m: waterLevel,
        max_water_level_m: maxWater,
        storage_percent: storagePct,
        storage_tmc: Number(((storagePct / 100) * 45).toFixed(2)),
        inflow_cusecs: inflow,
        outflow_cusecs: outflow,
        gates_open: gatesOpen,
        total_gates: gatesTotal,
        gate_clearance_m: gateClearance,
        weather: {
          condition: weatherCond,
          precipitation_mm_hr: precip,
          wind_speed_kmh: weatherCond === "MONSOON_STORM" ? 44 : 18,
          temperature_c: 28,
        },
        structural_sensors: sensors,
        history_24h: history,
      });
    }
  }

  public getTelemetry(assetCode: string): TelemetryFeedRecord {
    const existing = this.telemetry.get(assetCode);
    if (existing) return existing;
    // Fallback baseline
    return {
      asset_code: assetCode,
      last_sync: new Date().toISOString(),
      sources: ["India WRIS / CWC Portal Baseline"],
      water_level_m: 12.0,
      max_water_level_m: 15.0,
      storage_percent: 65,
      inflow_cusecs: 8500,
      outflow_cusecs: 7200,
      gates_open: 4,
      total_gates: 12,
      gate_clearance_m: 1.2,
      weather: { condition: "OVERCAST", precipitation_mm_hr: 3.5, wind_speed_kmh: 16, temperature_c: 29 },
      structural_sensors: [
        { id: "PZ-01", name: "Baseline Piezometer", type: "PIEZOMETER", value: 95, unit: "kPa", threshold: 150, status: "NORMAL", position: [0, 1, 0] },
      ],
      history_24h: [],
    };
  }

  public syncTelemetryFromPortals(assetCode: string): TelemetryFeedRecord {
    const record = this.getTelemetry(assetCode);
    // Simulate live delta update as if freshly scraped from CWC / WRIS / IMD APIs
    const delta = (Math.random() - 0.45) * 0.2;
    record.water_level_m = Number(Math.max(2, record.water_level_m + delta).toFixed(2));
    record.storage_percent = Number(Math.min(100, Math.max(10, (record.water_level_m / record.max_water_level_m) * 100)).toFixed(1));
    record.inflow_cusecs = Math.round(record.inflow_cusecs * (1 + (Math.random() - 0.48) * 0.06));
    record.last_sync = new Date().toISOString();

    // Check threshold alerts
    if (record.storage_percent > 95) {
      this.addNotification({
        title: `High Reservoir Telemetry: ${assetCode}`,
        message: `Live telemetry from India WRIS indicates storage at ${record.storage_percent}% FRL with inflow ${record.inflow_cusecs.toLocaleString()} cusecs.`,
        severity: "CRITICAL",
        category: "ALERT",
        asset_code: assetCode,
      });
    }

    this.telemetry.set(assetCode, record);
    return record;
  }

  public updateTelemetrySim(assetCode: string, patch: Partial<TelemetryFeedRecord>): TelemetryFeedRecord {
    const record = this.getTelemetry(assetCode);
    const updated: TelemetryFeedRecord = {
      ...record,
      ...patch,
      last_sync: new Date().toISOString(),
    };
    this.telemetry.set(assetCode, updated);
    return updated;
  }

  // ==========================================
  // CITIZEN & PUBLIC HAZARD OBSERVATIONS
  // ==========================================
  private initObservations() {
    const defaults: CitizenHazardObservationRecord[] = [
      {
        id: "CIT-2026-001",
        asset_code: "AP_DAM_00001",
        asset_name: "Prakasam Barrage",
        reporter_name: "K. Venkatesh (Krishna River Boat Operator)",
        reporter_phone: "+91 98480 11223",
        observation_type: "DEBRIS_JAM",
        severity: "HIGH",
        description: "Dense hyacinth mat and massive tree trunk caught across crest gates 32-34. Strong swirling vortex forming near right pier.",
        coordinates_3d: [6, 2.8, 8],
        verified_by_officer: true,
        reported_at: new Date(Date.now() - 4 * 3600 * 1000).toISOString(),
      },
      {
        id: "CIT-2026-002",
        asset_code: "AP_DAM_00001",
        asset_name: "Prakasam Barrage",
        reporter_name: "M. Anuradha (Bhavani Island Resident)",
        observation_type: "WATER_OVERFLOW",
        severity: "MEDIUM",
        description: "River water level rose by approximately 0.4 meters during past 3 hours following upstream Munneru river release.",
        coordinates_3d: [-12, 1.2, 14],
        verified_by_officer: true,
        reported_at: new Date(Date.now() - 8 * 3600 * 1000).toISOString(),
      },
      {
        id: "CIT-2026-003",
        asset_code: "AP_DAM_00002",
        asset_name: "Polavaram Dam Project",
        reporter_name: "Devendra Swamy (Field Assistant)",
        observation_type: "STRUCTURAL_CRACK",
        severity: "HIGH",
        description: "Micro-fissures noticed on spillway training wall downstream face following high velocity test discharges.",
        coordinates_3d: [24, 4.5, 18],
        verified_by_officer: false,
        reported_at: new Date(Date.now() - 14 * 3600 * 1000).toISOString(),
      },
      {
        id: "CIT-2026-004",
        asset_code: "AP_AIR_VOBZ",
        asset_name: "Vijayawada Airport",
        reporter_name: "Capt. R. Deshmukh (Ground Pilot Inspection)",
        observation_type: "SURFACE_POTHOLE",
        severity: "LOW",
        description: "Surface bitumen aggregate loosening noticed on taxiway Bravo turnoff connector. Runway 08 remains nominal.",
        coordinates_3d: [-18, 0.3, -12],
        verified_by_officer: true,
        reported_at: new Date(Date.now() - 20 * 3600 * 1000).toISOString(),
      },
    ];

    for (const d of defaults) {
      this.observations.set(d.id, d);
    }
  }

  public getObservations(assetCode?: string): CitizenHazardObservationRecord[] {
    const all = Array.from(this.observations.values()).sort((a, b) => b.reported_at.localeCompare(a.reported_at));
    if (!assetCode) return all;
    return all.filter((o) => o.asset_code === assetCode);
  }

  public addObservation(obs: Omit<CitizenHazardObservationRecord, "id" | "reported_at" | "verified_by_officer">): CitizenHazardObservationRecord {
    const id = `CIT-2026-${String(this.observations.size + 1).padStart(3, "0")}`;
    const record: CitizenHazardObservationRecord = {
      ...obs,
      id,
      verified_by_officer: false,
      reported_at: new Date().toISOString(),
    };
    this.observations.set(id, record);

    this.addNotification({
      title: `Citizen Hazard Observation: ${record.asset_name}`,
      message: `${record.observation_type} reported by ${record.reporter_name}: "${record.description.substring(0, 80)}..."`,
      severity: record.severity === "CRITICAL" || record.severity === "HIGH" ? "WARNING" : "INFO",
      category: "ALERT",
      asset_code: record.asset_code,
    });

    return record;
  }

  public verifyObservation(id: string, verified: boolean): CitizenHazardObservationRecord {
    const obs = this.observations.get(id);
    if (!obs) throw new Error(`Observation ${id} not found`);
    obs.verified_by_officer = verified;
    this.observations.set(id, obs);
    return obs;
  }
}

export const db = new SimrasDatabase();
