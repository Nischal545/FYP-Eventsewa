-- First create the django_migrations table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create django_session table in public schema
CREATE TABLE IF NOT EXISTS public.django_session (
    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create index on expire_date
CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON public.django_session (expire_date);

-- Grant permissions to nischal user
GRANT ALL PRIVILEGES ON TABLE public.django_session TO nischal;
GRANT ALL PRIVILEGES ON TABLE public.django_migrations TO nischal;

-- Insert a dummy migration record for sessions
INSERT INTO public.django_migrations (app, name, applied)
VALUES ('sessions', '0001_initial', NOW())
ON CONFLICT DO NOTHING;
