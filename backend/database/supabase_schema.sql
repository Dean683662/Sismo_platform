-- SISMO Platform PostgreSQL schema for Supabase.
-- This script is intended for a new, empty public schema. It mirrors the
-- application's Alembic revisions through 20261017_0005.
-- Prefer `alembic upgrade head` for managed deployments; do not apply both
-- this file and the migrations to the same unversioned database.
--
-- The application uses its own API authentication/RBAC. Never expose the
-- database connection string, service-role key, or database password to the
-- browser/frontend.

CREATE TABLE IF NOT EXISTS platform_settings (
    key VARCHAR(120) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS roles (
    name VARCHAR(40) PRIMARY KEY,
    description VARCHAR(200) NOT NULL
);

INSERT INTO roles (name, description) VALUES
    ('administrator', 'Administración total de la plataforma'),
    ('analyst', 'Análisis de datos y experimentos'),
    ('alert_operator', 'Operación del centro de alertas'),
    ('auditor', 'Consulta de auditoría y trazabilidad'),
    ('read_only', 'Consulta sin cambios operativos')
ON CONFLICT (name) DO NOTHING;

-- Local password login is used by the current API. For Supabase Auth, replace
-- this model with a verified external identity mapping; never store plaintext.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(160) NOT NULL,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    token_version INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- Keep the role key compatible with the application's current RBAC model.
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id VARCHAR(40) NOT NULL REFERENCES roles(name) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(64),
    before_json JSON,
    after_json JSON,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_occurred_at ON audit_logs (occurred_at);

CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_key VARCHAR(40) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    organization VARCHAR(120) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    source_type VARCHAR(40) NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    last_sync_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    records_seen INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_duplicated INTEGER NOT NULL DEFAULT 0,
    records_skipped INTEGER NOT NULL DEFAULT 0,
    error_summary VARCHAR(500),
    CONSTRAINT ck_ingestion_runs_status CHECK (status IN ('running', 'succeeded', 'failed')),
    CONSTRAINT ck_ingestion_runs_counts CHECK (
        records_seen >= 0 AND records_inserted >= 0
        AND records_updated >= 0 AND records_duplicated >= 0 AND records_skipped >= 0
    )
);

CREATE INDEX IF NOT EXISTS ix_ingestion_runs_source_id ON ingestion_runs (source_id);
CREATE INDEX IF NOT EXISTS ix_ingestion_runs_started_at ON ingestion_runs (started_at);

CREATE TABLE IF NOT EXISTS seismic_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(100) NOT NULL,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE RESTRICT,
    occurred_at TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    magnitude DOUBLE PRECISION NOT NULL,
    magnitude_type VARCHAR(30),
    depth_km DOUBLE PRECISION NOT NULL,
    place VARCHAR(300) NOT NULL,
    source_url VARCHAR(500),
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_hash VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'reported',
    CONSTRAINT uq_seismic_event_source_external UNIQUE (source_id, external_id),
    CONSTRAINT ck_seismic_events_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_seismic_events_longitude CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT ck_seismic_events_magnitude CHECK (magnitude BETWEEN 0 AND 10),
    CONSTRAINT ck_seismic_events_depth CHECK (depth_km BETWEEN 0 AND 1000)
);

CREATE INDEX IF NOT EXISTS ix_seismic_events_source_id ON seismic_events (source_id);
CREATE INDEX IF NOT EXISTS ix_seismic_events_occurred_at ON seismic_events (occurred_at);
CREATE INDEX IF NOT EXISTS ix_seismic_events_magnitude ON seismic_events (magnitude);
CREATE INDEX IF NOT EXISTS ix_seismic_events_received_at ON seismic_events (received_at);

CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(160) NOT NULL,
    version INTEGER NOT NULL,
    query_spec JSON NOT NULL,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    row_count INTEGER NOT NULL,
    quality_report JSON NOT NULL,
    records_json JSON NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_datasets_name_version UNIQUE (name, version),
    CONSTRAINT ck_datasets_version CHECK (version > 0),
    CONSTRAINT ck_datasets_row_count CHECK (row_count >= 0)
);

CREATE INDEX IF NOT EXISTS ix_datasets_name ON datasets (name);

CREATE TABLE IF NOT EXISTS ml_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(160) NOT NULL,
    task_type VARCHAR(30) NOT NULL,
    algorithm VARCHAR(80) NOT NULL,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    feature_spec JSON NOT NULL,
    target_name VARCHAR(80) NOT NULL,
    params JSON NOT NULL,
    metrics JSON NOT NULL,
    validation_spec JSON NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'completed',
    limitations TEXT NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ml_experiments_dataset_id ON ml_experiments (dataset_id);

-- These two tables reserve the image's model publication / risk-estimate
-- concepts for a later API phase. The current application does not read/write
-- them; ML experiments are not automatically published as operational models.
CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID NOT NULL REFERENCES ml_experiments(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    limitations TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_model_registry_experiment_version UNIQUE (experiment_id, version),
    CONSTRAINT ck_model_registry_version CHECK (version > 0),
    CONSTRAINT ck_model_registry_status CHECK (status IN ('pending', 'approved', 'rejected', 'retired'))
);

CREATE TABLE IF NOT EXISTS risk_estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE RESTRICT,
    area_code VARCHAR(80) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    metric_name VARCHAR(80) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    lower_bound DOUBLE PRECISION,
    upper_bound DOUBLE PRECISION,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    disclaimer TEXT NOT NULL,
    CONSTRAINT ck_risk_estimates_window CHECK (window_start < window_end),
    CONSTRAINT ck_risk_estimates_bounds CHECK (
        (lower_bound IS NULL OR lower_bound <= value)
        AND (upper_bound IS NULL OR upper_bound >= value)
        AND (lower_bound IS NULL OR upper_bound IS NULL OR lower_bound <= upper_bound)
    )
);

CREATE INDEX IF NOT EXISTS ix_risk_estimates_model_window
    ON risk_estimates (model_id, window_start, window_end);

CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    min_magnitude DOUBLE PRECISION NOT NULL,
    min_depth_km DOUBLE PRECISION,
    region_bounds JSON,
    source_ids JSON NOT NULL DEFAULT '[]'::json,
    channel VARCHAR(30) NOT NULL DEFAULT 'in_app',
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    template VARCHAR(500) NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_alert_rules_min_magnitude CHECK (min_magnitude BETWEEN 0 AND 10),
    CONSTRAINT ck_alert_rules_min_depth CHECK (min_depth_km IS NULL OR min_depth_km BETWEEN 0 AND 1000),
    CONSTRAINT ck_alert_rules_channel CHECK (channel IN ('in_app', 'webhook'))
);

-- The application stores each alert event and its delivery state together in
-- alert_deliveries (rather than splitting the image's conceptual alerts table).
CREATE TABLE IF NOT EXISTS alert_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES alert_rules(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES seismic_events(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL,
    channel VARCHAR(30) NOT NULL,
    message VARCHAR(500) NOT NULL,
    deduplication_key VARCHAR(255) NOT NULL,
    is_test BOOLEAN NOT NULL DEFAULT FALSE,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    CONSTRAINT uq_alert_deliveries_deduplication_key UNIQUE (deduplication_key),
    CONSTRAINT ck_alert_deliveries_channel CHECK (channel IN ('in_app', 'webhook')),
    CONSTRAINT ck_alert_deliveries_status CHECK (
        status IN ('queued', 'pending_approval', 'delivered', 'rejected', 'failed')
    ),
    CONSTRAINT ck_alert_deliveries_attempt_count CHECK (attempt_count >= 0)
);

CREATE INDEX IF NOT EXISTS ix_alert_deliveries_rule_id ON alert_deliveries (rule_id);
CREATE INDEX IF NOT EXISTS ix_alert_deliveries_event_id ON alert_deliveries (event_id);
CREATE INDEX IF NOT EXISTS ix_alert_deliveries_status ON alert_deliveries (status);
CREATE INDEX IF NOT EXISTS ix_alert_deliveries_created_at ON alert_deliveries (created_at);

CREATE TABLE IF NOT EXISTS report_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type VARCHAR(30) NOT NULL,
    filters JSON NOT NULL,
    row_count INTEGER NOT NULL,
    records_json JSON NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_report_runs_type CHECK (report_type IN ('events', 'models', 'sources', 'alerts', 'quality')),
    CONSTRAINT ck_report_runs_row_count CHECK (row_count >= 0)
);

CREATE INDEX IF NOT EXISTS ix_report_runs_report_type ON report_runs (report_type);
CREATE INDEX IF NOT EXISTS ix_report_runs_created_at ON report_runs (created_at);

-- Reserve an asynchronous report-job table as shown in the planning diagram.
-- The current API generates synchronous immutable report_runs instead.
CREATE TABLE IF NOT EXISTS report_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by UUID REFERENCES users(id) ON DELETE SET NULL,
    report_type VARCHAR(30) NOT NULL,
    filters_json JSON NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'queued',
    file_ref VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT ck_report_jobs_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'expired')),
    CONSTRAINT ck_report_jobs_expiration CHECK (expires_at IS NULL OR expires_at >= created_at)
);

CREATE INDEX IF NOT EXISTS ix_report_jobs_status_created_at ON report_jobs (status, created_at);

-- Seed the configured official IGP catalog. The latest-event and historical
-- catalog downloads use separate API requests against this verified provider.
INSERT INTO data_sources (
    provider_key, name, organization, base_url, source_type, is_verified, status
) VALUES (
    'igp',
    'Último sismo reportado',
    'Instituto Geofísico del Perú',
    'https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos',
    'official_api',
    TRUE,
    'active'
)
ON CONFLICT (provider_key) DO NOTHING;

-- Initial platform administrator for first-time setup. The password is stored
-- as an Argon2id hash compatible with backend.core.security.verify_password.
-- Reapplying this seed does not overwrite an existing account's password.
INSERT INTO users (full_name, email, password_hash)
VALUES (
    'Administrador',
    'solanodavid587@gmail.com',
    '$argon2id$v=19$m=65536,t=3,p=4$PIP/FP3sVwJ5SHNmiGGXCQ$QJVYGPkNb+RDZwb9GsA0rlxBoUKOYiuenMYXWzj+s5A'
)
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT users.id, roles.name
FROM users
CROSS JOIN roles
WHERE users.email = 'solanodavid587@gmail.com'
  AND roles.name = 'administrator'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- The API connects through its trusted server-side PostgreSQL role. Supabase
-- Data API roles receive no policies and therefore cannot read these tables.
ALTER TABLE public.platform_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seismic_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_estimates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_jobs ENABLE ROW LEVEL SECURITY;
