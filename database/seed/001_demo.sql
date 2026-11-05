-- Fixed, synthetic data only. Password hashes arrive as psql variables, never plaintext.
INSERT INTO catalog.products (id, name, description, price, is_public)
SELECT n,
       CASE WHEN n=1 THEN 'O''Reilly Notebook' ELSE 'Demo Product ' || lpad(n::text, 2, '0') END,
       'Synthetic product for the isolated MiniShop lab',
       (n * 1250)::numeric(12,2), true
FROM generate_series(1,12) AS n;
INSERT INTO catalog.products (id, name, description, price, is_public)
VALUES (13, 'Hidden Test Product', 'Not publicly listed', 9999, false);

INSERT INTO auth.users (id, username, password_hash)
SELECT n,
       CASE WHEN n<=2 THEN 'user'||n ELSE 'synthetic'||lpad(n::text,3,'0') END,
       CASE WHEN n=1 THEN :'user1_hash' WHEN n=2 THEN :'user2_hash' ELSE '!disabled' END
FROM generate_series(1,100) AS n;
INSERT INTO private.customers (id, user_id, name, email, phone, address)
SELECT n, n, 'Synthetic Customer '||lpad(n::text,3,'0'),
       'customer'||lpad(n::text,3,'0')||'@example.invalid',
       'TEST-PHONE-'||lpad(n::text,4,'0'),
       'Synthetic Zone '||lpad(n::text,3,'0')
FROM generate_series(1,100) AS n;

INSERT INTO private.orders (id, customer_id, product_id, quantity, total_amount, order_date)
SELECT c.id*1000+v.n, c.id, ((c.id+v.n-2)%12)+1, v.n,
       p.price*v.n, timestamptz '2026-01-01 00:00:00+00' + (c.id*3+v.n)*interval '1 hour'
FROM private.customers AS c CROSS JOIN generate_series(1,3) AS v(n)
JOIN catalog.products AS p ON p.id=((c.id+v.n-2)%12)+1;
INSERT INTO private.payment_meta (id, order_id, method, reference)
SELECT id, id, CASE WHEN id%2=0 THEN 'TEST_WALLET' ELSE 'TEST_CARD' END,
       'TEST-NOT-A-PAYMENT-'||id FROM private.orders;

SELECT setval(pg_get_serial_sequence('catalog.products','id'),13);
SELECT setval(pg_get_serial_sequence('auth.users','id'),100);
SELECT setval(pg_get_serial_sequence('private.customers','id'),100);
