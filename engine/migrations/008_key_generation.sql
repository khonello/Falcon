-- Phase 5 (auth): per-PC key generation so a client key can be rotated without reissuing the
-- client_id. derived_key = HMAC(master_secret, "<client_id>:<key_generation>").
ALTER TABLE pcs ADD COLUMN IF NOT EXISTS key_generation INTEGER NOT NULL DEFAULT 1;
