-- Add verification columns to dim_users
ALTER TABLE dim_users 
ADD COLUMN is_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN verification_code VARCHAR(10);

-- Set existing admin users to verified
UPDATE dim_users 
SET is_verified = TRUE 
WHERE role_name = 'admin';
