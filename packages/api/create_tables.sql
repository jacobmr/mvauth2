-- Create community_users table
CREATE TABLE IF NOT EXISTS public.community_users (
    id SERIAL PRIMARY KEY,
    clerk_user_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    unit_number VARCHAR(20),
    phone_number VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create user_app_roles table
CREATE TABLE IF NOT EXISTS public.user_app_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.community_users(id) ON DELETE CASCADE,
    app_name VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, app_name)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_community_users_email ON public.community_users(email);
CREATE INDEX IF NOT EXISTS idx_community_users_clerk_id ON public.community_users(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_community_users_active ON public.community_users(is_active);
CREATE INDEX IF NOT EXISTS idx_user_app_roles_user_id ON public.user_app_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_app_roles_app ON public.user_app_roles(app_name);

-- Insert a test user (you - the admin)
INSERT INTO public.community_users (
    clerk_user_id, 
    email, 
    full_name, 
    role, 
    is_active
) VALUES (
    '', 
    'jacob@reider.us', 
    'Jacob Reider', 
    'SUPER_ADMIN', 
    true
) ON CONFLICT (email) DO NOTHING;

-- Enable Row Level Security (RLS) for better security
ALTER TABLE public.community_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_app_roles ENABLE ROW LEVEL SECURITY;

-- Create policies to allow service role access
DROP POLICY IF EXISTS "Service role can access all users" ON public.community_users;
CREATE POLICY "Service role can access all users" ON public.community_users
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role can access all app roles" ON public.user_app_roles;
CREATE POLICY "Service role can access all app roles" ON public.user_app_roles
    FOR ALL USING (auth.role() = 'service_role');