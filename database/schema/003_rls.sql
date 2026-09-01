-- Enable RLS on dim_users
ALTER TABLE dim_users ENABLE ROW LEVEL SECURITY;

-- Create policy to allow admins to see and modify all users
CREATE POLICY admin_all ON dim_users
FOR ALL
USING (current_setting('app.current_role', true) = 'admin');

-- Create policy to allow normal users to see and modify ONLY their own row
CREATE POLICY user_self ON dim_users
FOR ALL
USING (id = current_setting('app.current_user_id', true) OR current_setting('app.is_login', true) = 'true');

-- To ensure login queries work when not yet authenticated, we'll set a local var app.is_login = 'true'
