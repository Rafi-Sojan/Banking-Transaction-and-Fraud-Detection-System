-- Single-entry PostgreSQL initialization script.
-- Execute from psql with: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/setup.sql

\set ON_ERROR_STOP on
\ir schema/create_tables.sql
\ir schema/constraints.sql
\ir schema/indexes.sql
\ir triggers/transaction_triggers.sql
\ir triggers/fraud_triggers.sql
\ir procedures/transaction_procedures.sql
\ir procedures/fraud_procedures.sql
\ir views/transaction_reports.sql
\ir views/fraud_reports.sql
\ir seed/data.sql
