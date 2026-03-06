-- Run this in PostgreSQL as postgres user:
-- sudo -u postgres psql

\c kaziconnect5

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE kaziconnect5 TO kazi_admin;

-- Grant all on schema
GRANT ALL ON SCHEMA public TO kazi_admin;

-- Grant all on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kazi_admin;

-- Grant all on all sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kazi_admin;

-- Grant default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO kazi_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO kazi_admin;

-- Make kazi_admin owner of the database
ALTER DATABASE kaziconnect5 OWNER TO kazi_admin;
