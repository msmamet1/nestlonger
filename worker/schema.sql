-- NestLonger form storage (Cloudflare D1)
--
-- Applied with:
--   npx wrangler d1 execute nestlonger-leads --remote --file worker/schema.sql
--
-- Note on PII: these tables hold a ZIP code plus free-text notes about an elderly
-- person's home. Treat them as sensitive. The submitter's IP is stored only as a
-- salted hash (ip_hash), enough to rate-limit without retaining the address itself.

CREATE TABLE IF NOT EXISTS leads (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at  TEXT NOT NULL,
  source      TEXT,           -- entry point: homepage, grab-bars, adus, about, privacy, 404
  name        TEXT NOT NULL,
  email       TEXT NOT NULL,
  phone       TEXT,
  zip         TEXT NOT NULL,
  need        TEXT,           -- grab-bars | adu | home-safety | not-sure
  who         TEXT,           -- parent | both-parents | myself | other
  details     TEXT,
  ip_hash     TEXT,
  user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_created ON leads (created_at);
CREATE INDEX IF NOT EXISTS idx_leads_source  ON leads (source);

CREATE TABLE IF NOT EXISTS partners (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at        TEXT NOT NULL,
  business          TEXT NOT NULL,
  contact           TEXT NOT NULL,
  email             TEXT NOT NULL,
  phone             TEXT,
  trade             TEXT,
  coverage          TEXT,
  license           TEXT,
  aging_experience  TEXT,
  ip_hash           TEXT,
  user_agent        TEXT
);

CREATE INDEX IF NOT EXISTS idx_partners_created ON partners (created_at);

CREATE TABLE IF NOT EXISTS subscribers (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at  TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  source      TEXT,
  ip_hash     TEXT
);

-- Per-IP submission log, used only for rate limiting. Rows older than the window
-- are pruned by the Worker on write, so this stays small.
CREATE TABLE IF NOT EXISTS rate_limit (
  ip_hash     TEXT NOT NULL,
  created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_limit ON rate_limit (ip_hash, created_at);
