-- Add event_code and image columns to events table
ALTER TABLE users.events
ADD COLUMN IF NOT EXISTS event_code VARCHAR(6) UNIQUE,
ADD COLUMN IF NOT EXISTS image BYTEA;

-- Create index on event_code for faster lookups
CREATE INDEX IF NOT EXISTS idx_events_event_code ON users.events(event_code); 