-- StaySpot :: 05_materialized_views.sql
-- Property summary: total bookings, total nights booked, gross revenue

DROP MATERIALIZED VIEW IF EXISTS property_summary;

CREATE MATERIALIZED VIEW property_summary AS
SELECT
    p.id AS property_id,
    p.title,
    COUNT(b.id) AS total_bookings,
    COALESCE(SUM(b.check_out - b.check_in), 0) AS total_nights_booked,
    COALESCE(SUM(b.total_cost), 0) AS gross_revenue
FROM properties p
LEFT JOIN bookings b
    ON b.property_id = p.id
GROUP BY p.id, p.title;

-- Required for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX idx_property_summary_property_id
ON property_summary (property_id);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_property_summary()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY property_summary;
END;
$$;