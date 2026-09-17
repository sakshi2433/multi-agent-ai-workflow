-- PostgreSQL initialization script for the Multi-Agent AI Workflow system
-- Creates necessary extensions and initial data

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a dedicated role and database would typically be done separately,
-- but we ensure the necessary extensions are available.

-- Table indexes for performance (will be created by Alembic in production)
-- CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
-- CREATE INDEX IF NOT EXISTS idx_tool_calls_workflow_id ON tool_call_logs(workflow_id);
-- CREATE INDEX IF NOT EXISTS idx_audit_logs_workflow_id ON audit_logs(workflow_id);

-- Logging informational message
DO $$
BEGIN
    RAISE NOTICE 'Multi-Agent AI Workflow database initialized';
END
$$;