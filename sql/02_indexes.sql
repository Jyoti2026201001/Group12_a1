

-- Partial key || Prevents a guest from having more than one overlapping CHECKED_IN stay.
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_stay
    ON bookings (guest_id)
    WHERE status = 'CHECKED_IN';

-- Secondary indexes to keep FK lookups and analytics fast.
CREATE INDEX IF NOT EXISTS idx_bookings_property_id
    ON bookings (property_id);

CREATE INDEX IF NOT EXISTS idx_bookings_created_at
    ON bookings (created_at);
    
CREATE INDEX IF NOT EXISTS idx_bookings_status
    ON bookings (status);

CREATE INDEX IF NOT EXISTS idx_bookings_property_created
    ON bookings (property_id, created_at);

CREATE INDEX IF NOT EXISTS idx_wallet_audit_guest_id
    ON wallet_audit_logs (guest_id);

CREATE INDEX IF NOT EXISTS idx_wallet_audit_timestamp
    ON wallet_audit_logs (timestamp);
