-- Dedicated least-privilege account used by the application.
-- Demo credentials only: replace them with secrets outside local development.
CREATE ROLE analytics_user LOGIN PASSWORD 'analytics_pass';
GRANT CONNECT ON DATABASE sales_analytics TO analytics_user;
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
ALTER DEFAULT PRIVILEGES FOR ROLE analytics_admin IN SCHEMA public
    GRANT SELECT ON TABLES TO analytics_user;

-- Defense in depth: make transactions read-only by default for this role.
ALTER ROLE analytics_user SET default_transaction_read_only = on;
