-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION users.update_events_updated_at()
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
    EXECUTE FUNCTION users.update_events_updated_at(); 