-- Stoken Advisory — Supabase Tables
-- Execute este SQL no SQL Editor do Supabase

CREATE TABLE IF NOT EXISTS interviews (
    id          BIGSERIAL PRIMARY KEY,
    interviewer TEXT    NOT NULL DEFAULT '',
    interviewee TEXT    NOT NULL DEFAULT '',
    role        TEXT    DEFAULT '',
    department  TEXT    DEFAULT '',
    level       TEXT    DEFAULT '',
    pillar      TEXT    DEFAULT '',
    date        TEXT    DEFAULT '',
    transcript  TEXT    DEFAULT '',
    ia_ready    BOOLEAN DEFAULT FALSE,
    created_at  TEXT    NOT NULL,
    analysis    TEXT
);

CREATE TABLE IF NOT EXISTS analysis_results (
    key          TEXT PRIMARY KEY,
    content      TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_status (
    id              INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    running         BOOLEAN DEFAULT FALSE,
    last_run        TEXT,
    steps_completed TEXT    DEFAULT '[]',
    errors          TEXT    DEFAULT '[]'
);

-- Seed pipeline status
INSERT INTO pipeline_status (id, running, steps_completed, errors)
VALUES (1, FALSE, '[]', '[]')
ON CONFLICT (id) DO NOTHING;

-- Disable RLS for backend service access
ALTER TABLE interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_status ENABLE ROW LEVEL SECURITY;

-- Allow full access with service key
CREATE POLICY "Allow all for service" ON interviews FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service" ON analysis_results FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all for service" ON pipeline_status FOR ALL USING (true) WITH CHECK (true);
