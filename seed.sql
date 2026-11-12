INSERT INTO products (id, seller_id, title, description, price, stock, is_active, created_at, updated_at)
SELECT
    gen_random_uuid(),
    (SELECT id FROM users ORDER BY created_at LIMIT 1),
    'Product ' || g || ' ' || substr(md5(g::text), 1, 8),
    'Seed description',
    round((random() * 1000)::numeric, 2),
    (random() * 100)::int,
    true,
    now() - (g || ' seconds')::interval,
    now()
FROM generate_series(1, 100000) AS g;
 
ANALYZE products;
 
-- ===== Замер (запускай в psql вручную, искать лучше 4+ символа) =====
-- 1) С индексом:
-- EXPLAIN (ANALYZE, BUFFERS)
-- SELECT * FROM products
-- WHERE is_active AND title ILIKE '%a1b2c3%'
-- ORDER BY created_at DESC LIMIT 20;
--
-- 2) Без индекса (потом верни обратно через alembic downgrade/upgrade):
-- DROP INDEX ix_products_title_trgm;
-- ...тот же EXPLAIN ANALYZE (ожидаем Seq Scan)...
--
-- Сравни Execution Time и тип сканирования, цифры запиши в README.