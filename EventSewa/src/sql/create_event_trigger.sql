-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION users.update_event_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at timestamp
DROP TRIGGER IF EXISTS update_event_updated_at ON users.event;
CREATE TRIGGER update_event_updated_at
    BEFORE UPDATE ON users.event
    FOR EACH ROW
    EXECUTE FUNCTION users.update_event_updated_at(); 