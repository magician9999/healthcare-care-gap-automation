-- Healthcare Care Gap Database Initialization Script
-- This script sets up the initial database structure and configurations

-- Create the main database (if running this separately)
-- CREATE DATABASE healthcare_care_gap;

-- Connect to the database
\c healthcare_care_gap;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance (these will be created by Alembic migrations)
-- but having them here as reference

-- Set timezone
SET timezone = 'UTC';

-- Create a function to automatically update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE healthcare_care_gap TO postgres;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Healthcare Care Gap database initialized successfully at %', NOW();
END
$$;