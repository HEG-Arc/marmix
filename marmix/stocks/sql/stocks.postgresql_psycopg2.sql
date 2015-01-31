--
-- Update the price of the stock after a new quote is inserted.
--
CREATE OR REPLACE FUNCTION update_stock_quote() RETURNS TRIGGER AS $update_quote$
    BEGIN
        --
        -- Update the price of the stock after a new quote is inserted.
        --
        UPDATE stocks_stock SET price=NEW.price WHERE id=NEW.stock_id;
        RETURN NULL; -- result is ignored since this is an AFTER trigger
    END;
$update_quote$ LANGUAGE plpgsql;

CREATE TRIGGER update_quote
AFTER INSERT ON stocks_quote
    FOR EACH ROW EXECUTE PROCEDURE update_stock_quote();