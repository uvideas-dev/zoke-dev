-- Migration to add ZoScore and Badge Level to users table
ALTER TABLE users ADD COLUMN zoscore INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN badge_level VARCHAR;
