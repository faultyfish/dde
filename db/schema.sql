-- =============================================================
-- DevOps Job Board — Neon Postgres Schema
-- Run via: python db/migrate.py
-- =============================================================

CREATE TABLE IF NOT EXISTS jobs (
    id              SERIAL PRIMARY KEY,
    external_id     TEXT NOT NULL,          -- source-specific unique ID
    source          TEXT NOT NULL,          -- 'indeed' | 'linkedin'
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT,
    remote_type     TEXT,                   -- 'Remote' | 'Hybrid' | 'On-site'
    job_type        TEXT,                   -- 'Full-time' | 'Contract' | 'Part-time'
    salary_raw      TEXT,                   -- raw string as scraped
    salary_min      INTEGER,                -- parsed EUR min
    salary_max      INTEGER,                -- parsed EUR max
    description     TEXT,
    url             TEXT NOT NULL,
    category        TEXT,                   -- 'DevOps' | 'Cloud' | 'SRE' | 'MLOps'
    level           TEXT,                   -- 'Junior' | 'Mid' | 'Senior' | 'Lead'
    stack           TEXT[],                 -- ['Kubernetes','Terraform','AWS']
    visa_sponsor    BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    first_seen_at   TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ DEFAULT NOW(),
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),

    -- Deduplication: one row per job per source
    CONSTRAINT uq_source_external UNIQUE (source, external_id)
);

-- Index for common filter queries
CREATE INDEX IF NOT EXISTS idx_jobs_category    ON jobs(category);
CREATE INDEX IF NOT EXISTS idx_jobs_level       ON jobs(level);
CREATE INDEX IF NOT EXISTS idx_jobs_remote      ON jobs(remote_type);
CREATE INDEX IF NOT EXISTS idx_jobs_active      ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at  ON jobs(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_stack       ON jobs USING GIN(stack);

-- Scrape run log
CREATE TABLE IF NOT EXISTS scrape_runs (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    jobs_found      INTEGER DEFAULT 0,
    jobs_new        INTEGER DEFAULT 0,
    jobs_updated    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'running',   -- 'running' | 'success' | 'failed'
    error_message   TEXT
);
