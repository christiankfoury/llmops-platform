CREATE TABLE operator_project_grants (
    id UUID PRIMARY KEY,
    issuer VARCHAR(512) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_operator_project_grants_identity_project UNIQUE (issuer, subject, project_id),
    CONSTRAINT ck_operator_project_grants_role CHECK (role IN ('viewer', 'operator'))
);
CREATE INDEX ix_operator_project_grants_project_id ON operator_project_grants(project_id);
