-- Create organizers table
CREATE TABLE IF NOT EXISTS organizers (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES group1(id) ON DELETE CASCADE,
    organization_name VARCHAR(100) NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    owner_names TEXT NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    verification_status BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create organizer_requests table
CREATE TABLE IF NOT EXISTS organizer_requests (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES group1(id) ON DELETE CASCADE,
    organization_name VARCHAR(100) NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    owner_names TEXT NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(15) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create organizer_notification table
CREATE TABLE IF NOT EXISTS organizer_notification (
    id SERIAL PRIMARY KEY,
    organizer_id BIGINT REFERENCES group1(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create event table
CREATE TABLE IF NOT EXISTS event (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    organizer_id INTEGER REFERENCES organizers(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    location VARCHAR(255) NOT NULL,
    capacity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    event_code VARCHAR(6) UNIQUE,
    image BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create event_history table
CREATE TABLE IF NOT EXISTS event_history (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES event(id) ON DELETE CASCADE,
    admin_id INTEGER REFERENCES admins(id) ON DELETE CASCADE,
    occurrence_status VARCHAR(20) DEFAULT 'pending',
    payment_status VARCHAR(20) DEFAULT 'pending',
    marketing_fee DECIMAL(10,2),
    total_revenue DECIMAL(10,2),
    verification_date TIMESTAMP,
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
