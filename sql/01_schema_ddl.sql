
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS guests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(150) NOT NULL,
    email           VARCHAR(255) UNIQUE,
    wallet_balance  DECIMAL(10,2) NOT NULL DEFAULT 0.00
                        CHECK (wallet_balance >= 0.00),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS wallet_audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id        UUID NOT NULL REFERENCES guests(id) ON DELETE RESTRICT,
    amount_changed  DECIMAL(10,2) NOT NULL,
    action_type     VARCHAR(10) NOT NULL CHECK (action_type IN ('DEBIT','CREDIT')),
    balance_after   DECIMAL(10,2) NOT NULL CHECK (balance_after >= 0.00),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(200) NOT NULL,
    base_price      DECIMAL(10,2) NOT NULL CHECK (base_price > 0),
    latitude        FLOAT NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude       FLOAT NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id        UUID NOT NULL REFERENCES guests(id) ON DELETE RESTRICT,
    property_id     UUID NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
    check_in        DATE NOT NULL,
    check_out       DATE NOT NULL CHECK (check_out > check_in),
    total_cost      DECIMAL(10,2) NOT NULL CHECK (total_cost >= 0.00),
    status          VARCHAR(20) NOT NULL
                        CHECK (status IN ('CONFIRMED','CHECKED_IN','COMPLETED')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
