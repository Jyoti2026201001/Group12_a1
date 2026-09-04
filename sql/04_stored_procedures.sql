CREATE OR REPLACE PROCEDURE sp_atomic_booking(
    p_guest_id UUID,
    p_property_id UUID,
    p_total_cost DECIMAL,
    p_check_in DATE,
    p_check_out DATE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_updated INT;
BEGIN
    -- Validate that check_out date is after check_in date
    IF p_check_out <= p_check_in THEN
        RAISE EXCEPTION 'Check-out date (%) must be after check-in date (%)', p_check_out, p_check_in;
    END IF;

    -- Atomic conditional update: prevents overdrawing balance
    UPDATE guests
    SET wallet_balance = wallet_balance - p_total_cost
    WHERE id = p_guest_id
      AND wallet_balance >= p_total_cost;

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    IF v_updated = 0 THEN
        RAISE EXCEPTION 'Insufficient funds for guest ID: %', p_guest_id;
    END IF;

    -- Insert booking record with provided dates
    INSERT INTO bookings (guest_id, property_id, total_cost, status, check_in, check_out)
    VALUES (p_guest_id, p_property_id, p_total_cost, 'CONFIRMED', p_check_in, p_check_out);

END;
$$;