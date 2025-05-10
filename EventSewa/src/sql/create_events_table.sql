-- Create events table in the users schema
CREATE TABLE IF NOT EXISTS users.events (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    organizer_id INTEGER NOT NULL REFERENCES users.organizers(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    location VARCHAR(255) NOT NULL,
    capacity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on organizer_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_events_organizer_id ON users.events(organizer_id);

-- Create index on date for faster date-based queries
CREATE INDEX IF NOT EXISTS idx_events_date ON users.events(date);

-- Create index on is_active for faster filtering of active/inactive events
CREATE INDEX IF NOT EXISTS idx_events_is_active ON users.events(is_active);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at timestamp
DROP TRIGGER IF EXISTS update_events_updated_at ON users.events;
CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON users.events
    FOR EACH ROW
    EXECUTE FUNCTION update_events_updated_at(); 