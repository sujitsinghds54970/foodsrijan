
-- Update Super Admin Credentials in Production
UPDATE users 
SET username = 'sujiterp',
    hashed_password = '$2b$12$/6WtQ5yzZjcsO70MJKqz1eyGIcnb6DXSu95jFSR0ED7zjXtdLQUXG',
    email = 'sujit@vaidyavihar.com',
    full_name = 'Sujit Singh - Super Admin'
WHERE role = 'super_admin';
