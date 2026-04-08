-- ORINOX v2 Database Schema (AlloyDB / SQLite)

CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    segment TEXT DEFAULT 'mass_affluent',
    risk_profile TEXT DEFAULT 'moderate',
    channel_preference TEXT DEFAULT 'email',
    occupation TEXT,
    city TEXT,
    region TEXT DEFAULT 'west',
    date_of_birth TEXT,
    aum REAL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id),
    instrument_name TEXT NOT NULL,
    instrument_type TEXT NOT NULL,
    sector TEXT,
    quantity REAL DEFAULT 0,
    avg_cost REAL DEFAULT 0,
    current_value REAL DEFAULT 0,
    allocation_pct REAL DEFAULT 0,
    currency TEXT DEFAULT 'INR',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS households (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id),
    member_name TEXT NOT NULL,
    relationship TEXT,
    date_of_birth TEXT,
    occupation TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS market_events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT,
    severity TEXT DEFAULT 'medium',
    affected_sectors TEXT DEFAULT '[]',
    affected_instruments TEXT DEFAULT '[]',
    impact_analysis TEXT,
    source TEXT,
    event_date TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_segments (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES market_events(id),
    client_id TEXT NOT NULL REFERENCES clients(id),
    exposure_type TEXT,
    exposure_amount REAL DEFAULT 0,
    exposure_pct REAL DEFAULT 0,
    risk_level TEXT DEFAULT 'medium',
    segment_label TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS communications (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id),
    event_id TEXT,
    workflow_id TEXT,
    channel TEXT DEFAULT 'email',
    message_type TEXT DEFAULT 'advisory',
    subject TEXT,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    gmail_message_id TEXT,
    sent_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_events (
    id TEXT PRIMARY KEY,
    client_id TEXT REFERENCES clients(id),
    workflow_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    attendees TEXT DEFAULT '[]',
    calendar_event_id TEXT,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    channel TEXT,
    subject TEXT,
    summary TEXT,
    direction TEXT DEFAULT 'outbound',
    logged_by TEXT DEFAULT 'system',
    interaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    status TEXT DEFAULT 'pending',
    duration_ms INTEGER,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_clients_segment ON clients(segment);
CREATE INDEX IF NOT EXISTS idx_clients_risk ON clients(risk_profile);
CREATE INDEX IF NOT EXISTS idx_portfolios_client ON portfolios(client_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_sector ON portfolios(sector);
CREATE INDEX IF NOT EXISTS idx_portfolios_type ON portfolios(instrument_type);
CREATE INDEX IF NOT EXISTS idx_segments_event ON client_segments(event_id);
CREATE INDEX IF NOT EXISTS idx_comms_client ON communications(client_id);
CREATE INDEX IF NOT EXISTS idx_comms_workflow ON communications(workflow_id);
CREATE INDEX IF NOT EXISTS idx_comms_status ON communications(status);
CREATE INDEX IF NOT EXISTS idx_sched_client ON scheduled_events(client_id);
CREATE INDEX IF NOT EXISTS idx_sched_workflow ON scheduled_events(workflow_id);
CREATE INDEX IF NOT EXISTS idx_interactions_client ON interactions(client_id);
CREATE INDEX IF NOT EXISTS idx_wf_logs ON workflow_logs(workflow_id);