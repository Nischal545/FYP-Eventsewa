import psycopg2

# Connect to the database
conn = psycopg2.connect(
    dbname="eventsewa",
    user="nischal",
    password="nischal",
    host="localhost",
    port="5432"
)
conn.autocommit = True
cursor = conn.cursor()

# Create django_migrations table
cursor.execute("""
CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL
);
""")

# Create django_session table
cursor.execute("""
CREATE TABLE IF NOT EXISTS django_session (
    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);
""")

# Create index on expire_date
cursor.execute("""
CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session (expire_date);
""")

# Insert a dummy migration record for sessions
cursor.execute("""
INSERT INTO django_migrations (app, name, applied)
VALUES ('sessions', '0001_initial', NOW())
ON CONFLICT DO NOTHING;
""")

print("Session tables created successfully!")

# Close the connection
cursor.close()
conn.close()
