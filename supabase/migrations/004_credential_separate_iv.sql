-- ============================================================
-- Separate IV/auth_tag for email and password encryption
-- ============================================================
-- Previously only one IV and auth_tag were stored, but email and
-- password are encrypted separately with different random IVs.
-- This adds dedicated columns for the password's IV and auth_tag.
--
-- NOTE: Existing credentials cannot be decrypted correctly for
-- passwords (they were stored with the email's IV/auth_tag).
-- Users must re-save their studio credentials after this migration.
-- ============================================================

ALTER TABLE studio_credentials ADD COLUMN password_iv text;
ALTER TABLE studio_credentials ADD COLUMN password_auth_tag text;

-- Backfill existing rows so NOT NULL can be applied.
-- These values are wrong for password decryption, but users must re-save anyway.
UPDATE studio_credentials SET password_iv = iv, password_auth_tag = auth_tag;

ALTER TABLE studio_credentials ALTER COLUMN password_iv SET NOT NULL;
ALTER TABLE studio_credentials ALTER COLUMN password_auth_tag SET NOT NULL;
