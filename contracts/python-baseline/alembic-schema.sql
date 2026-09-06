BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_create_llmops_schema

CREATE TABLE projects (
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_projects_slug ON projects (slug);

CREATE TABLE applications (
    project_id UUID NOT NULL,
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(120) NOT NULL,
    environment VARCHAR(40) NOT NULL,
    is_active BOOLEAN NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT uq_applications_project_slug UNIQUE (project_id, slug)
);

CREATE INDEX ix_applications_project_id ON applications (project_id);

CREATE INDEX ix_applications_slug ON applications (slug);

CREATE TABLE api_keys (
    application_id UUID NOT NULL,
    key_prefix VARCHAR(24) NOT NULL,
    key_hash VARCHAR(128) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE,
    UNIQUE (key_hash)
);

CREATE INDEX ix_api_keys_application_id ON api_keys (application_id);

CREATE INDEX ix_api_keys_key_prefix ON api_keys (key_prefix);

CREATE TABLE prompt_versions (
    project_id UUID NOT NULL,
    application_id UUID,
    name VARCHAR(160) NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE,
    CONSTRAINT uq_prompt_versions_scope_name_version UNIQUE (project_id, application_id, name, version)
);

CREATE INDEX ix_prompt_versions_application_id ON prompt_versions (application_id);

CREATE INDEX ix_prompt_versions_project_id ON prompt_versions (project_id);

CREATE TABLE model_routes (
    project_id UUID NOT NULL,
    application_id UUID,
    environment VARCHAR(40) NOT NULL,
    provider VARCHAR(80) NOT NULL,
    model_name VARCHAR(160) NOT NULL,
    priority INTEGER NOT NULL,
    is_default BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_model_routes_application_id ON model_routes (application_id);

CREATE INDEX ix_model_routes_project_id ON model_routes (project_id);

CREATE TABLE gateway_requests (
    request_id VARCHAR(80) NOT NULL,
    project_id UUID NOT NULL,
    application_id UUID NOT NULL,
    api_key_id UUID,
    prompt_version_id UUID,
    model_route_id UUID,
    provider VARCHAR(80),
    model_name VARCHAR(160),
    status VARCHAR(40) NOT NULL,
    latency_ms INTEGER,
    estimated_input_tokens INTEGER,
    estimated_output_tokens INTEGER,
    estimated_cost_usd NUMERIC(12, 6),
    error_category VARCHAR(80),
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(api_key_id) REFERENCES api_keys (id) ON DELETE SET NULL,
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE RESTRICT,
    FOREIGN KEY(model_route_id) REFERENCES model_routes (id) ON DELETE SET NULL,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE RESTRICT,
    FOREIGN KEY(prompt_version_id) REFERENCES prompt_versions (id) ON DELETE SET NULL
);

CREATE INDEX ix_gateway_requests_api_key_id ON gateway_requests (api_key_id);

CREATE INDEX ix_gateway_requests_application_id ON gateway_requests (application_id);

CREATE INDEX ix_gateway_requests_error_category ON gateway_requests (error_category);

CREATE INDEX ix_gateway_requests_model_route_id ON gateway_requests (model_route_id);

CREATE INDEX ix_gateway_requests_project_id ON gateway_requests (project_id);

CREATE INDEX ix_gateway_requests_prompt_version_id ON gateway_requests (prompt_version_id);

CREATE UNIQUE INDEX ix_gateway_requests_request_id ON gateway_requests (request_id);

CREATE TABLE audit_logs (
    project_id UUID,
    application_id UUID,
    actor_type VARCHAR(40) NOT NULL,
    actor_id VARCHAR(120),
    action VARCHAR(120) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id VARCHAR(120),
    metadata_json JSONB NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE SET NULL,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_application_id ON audit_logs (application_id);

CREATE INDEX ix_audit_logs_project_id ON audit_logs (project_id);

CREATE TABLE cost_records (
    gateway_request_id UUID NOT NULL,
    project_id UUID NOT NULL,
    application_id UUID NOT NULL,
    provider VARCHAR(80) NOT NULL,
    model_name VARCHAR(160) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    estimated_cost_usd NUMERIC(12, 6) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE RESTRICT,
    FOREIGN KEY(gateway_request_id) REFERENCES gateway_requests (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE RESTRICT,
    UNIQUE (gateway_request_id)
);

CREATE INDEX ix_cost_records_application_id ON cost_records (application_id);

CREATE INDEX ix_cost_records_project_id ON cost_records (project_id);

INSERT INTO alembic_version (version_num) VALUES ('0001_create_llmops_schema') RETURNING alembic_version.version_num;

-- Running upgrade 0001_create_llmops_schema -> 0002_external_telemetry

ALTER TABLE gateway_requests ADD COLUMN source_app VARCHAR(80);

ALTER TABLE gateway_requests ADD COLUMN operation_type VARCHAR(80);

ALTER TABLE gateway_requests ADD COLUMN external_event_id VARCHAR(80);

ALTER TABLE gateway_requests ADD COLUMN external_request_id VARCHAR(120);

ALTER TABLE gateway_requests ADD COLUMN external_metadata_json JSONB;

CREATE INDEX ix_gateway_requests_source_app ON gateway_requests (source_app);

CREATE INDEX ix_gateway_requests_operation_type ON gateway_requests (operation_type);

CREATE INDEX ix_gateway_requests_external_event_id ON gateway_requests (external_event_id);

CREATE INDEX ix_gateway_requests_external_request_id ON gateway_requests (external_request_id);

ALTER TABLE gateway_requests ADD CONSTRAINT uq_gateway_requests_application_external_event UNIQUE (application_id, external_event_id);

UPDATE alembic_version SET version_num='0002_external_telemetry' WHERE alembic_version.version_num = '0001_create_llmops_schema';

COMMIT;
