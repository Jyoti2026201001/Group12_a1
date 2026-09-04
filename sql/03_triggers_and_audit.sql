CREATE OR REPLACE FUNCTION fn_log_wallet_audit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO wallet_audit_logs (guest_id, amount_changed, action_type, balance_after)
    VALUES (
        NEW.id,
        ABS(NEW.wallet_balance - OLD.wallet_balance),
        CASE
            WHEN NEW.wallet_balance < OLD.wallet_balance THEN 'DEBIT'
            ELSE 'CREDIT'
        END,
        NEW.wallet_balance
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_wallet_balance_audit
AFTER UPDATE OF wallet_balance ON guests
FOR EACH ROW
EXECUTE PROCEDURE fn_log_wallet_audit();
