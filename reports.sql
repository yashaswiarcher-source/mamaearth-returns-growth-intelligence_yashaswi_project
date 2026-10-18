.bail on
.headers on
.mode column
.width 18 18 18 18

-- a) Output:
-- total_orders | total_revenue | avg_order_value
-- 180          | 99860.20      | 554.78
SELECT
    COUNT(*) AS total_orders,
    printf('%.2f', SUM(
        o.quantity * p.price *
        (1.0 - COALESCE(o.discount_pct, 0) / 100.0)
    )) AS total_revenue,
    printf('%.2f', AVG(
        o.quantity * p.price *
        (1.0 - COALESCE(o.discount_pct, 0) / 100.0)
    )) AS avg_order_value
FROM orders AS o
JOIN products AS p ON p.product_id = o.product_id;

-- b) Output:
-- count_all | count_rating | unrated_orders
-- 180       | 165          | 15
SELECT
    COUNT(*) AS count_all,
    COUNT(rating) AS count_rating,
    COUNT(*) - COUNT(rating) AS unrated_orders
FROM orders;

-- c1) Output:
-- customer_id | name
-- C045        | Vihaan
SELECT c.customer_id, c.name
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) = 0
ORDER BY c.customer_id;

-- c2) Independent NOT IN confirmation; output:
-- customer_id | name
-- C045        | Vihaan
SELECT c.customer_id, c.name
FROM customers AS c
WHERE c.customer_id NOT IN (SELECT DISTINCT customer_id FROM orders)
ORDER BY c.customer_id;

-- d) Output:
-- city      | total_orders | returned_orders | return_rate_pct
-- Jaipur    | 19           | 8               | 42.1
-- Lucknow   | 49           | 15              | 30.6
-- Bangalore | 33           | 8               | 24.2
SELECT
    c.city,
    COUNT(*) AS total_orders,
    SUM(o.returned) AS returned_orders,
    ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) AS return_rate_pct
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY c.city
HAVING ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) > 20
ORDER BY return_rate_pct DESC;

-- e1) Output:
-- customer_id | name    | total_spend
-- C043        | Reyansh | 12920.00
-- C026        | Isha    | 8371.60
-- C008        | Meera   | 4564.60
-- C011        | Arjun   | 4111.00
-- C042        | Sanya   | 3785.00
-- customer_id ASC makes equal-spend ranks deterministic and keeps LIMIT/OFFSET stable.
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.name,
        SUM(
            o.quantity * p.price *
            (1.0 - COALESCE(o.discount_pct, 0) / 100.0)
        ) AS total_spend
    FROM orders AS o
    JOIN products AS p ON p.product_id = o.product_id
    JOIN customers AS c ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name
)
SELECT customer_id, name, printf('%.2f', total_spend) AS total_spend
FROM customer_spend
ORDER BY customer_spend.total_spend DESC, customer_id ASC
LIMIT 5;

-- e2) The same ranking with the first two rows skipped; output:
-- customer_id | name  | total_spend
-- C008        | Meera | 4564.60
-- C011        | Arjun | 4111.00
-- C042        | Sanya | 3785.00
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.name,
        SUM(
            o.quantity * p.price *
            (1.0 - COALESCE(o.discount_pct, 0) / 100.0)
        ) AS total_spend
    FROM orders AS o
    JOIN products AS p ON p.product_id = o.product_id
    JOIN customers AS c ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.name
)
SELECT customer_id, name, printf('%.2f', total_spend) AS total_spend
FROM customer_spend
ORDER BY customer_spend.total_spend DESC, customer_id ASC
LIMIT 3 OFFSET 2;

-- f) Output:
-- category    | order_count | category_revenue
-- Haircare    | 54          | 44956.10
-- Skincare    | 60          | 27346.00
-- Babycare    | 30          | 16805.00
-- PersonalCare| 36          | 10753.10
SELECT
    p.category,
    COUNT(*) AS order_count,
    printf('%.2f', SUM(
        o.quantity * p.price *
        (1.0 - COALESCE(o.discount_pct, 0) / 100.0)
    )) AS category_revenue
FROM orders AS o
JOIN products AS p ON p.product_id = o.product_id
JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY p.category
ORDER BY SUM(
    o.quantity * p.price *
    (1.0 - COALESCE(o.discount_pct, 0) / 100.0)
) DESC;

-- g) Output:
-- name
-- Aarav
-- Aditi
-- Aditya
-- Aisha
-- Ananya
-- Anika
-- Aria
-- Arjun
-- Aryan
-- Ayaan
SELECT name
FROM customers
WHERE name LIKE 'A%'
ORDER BY name, customer_id;

-- h) Output:
-- acquisition_source
-- Ad
-- Organic
-- Referral
-- Social
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;

-- i) Run once after the reports above on a freshly loaded database.
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

-- Update all customers in one statement; no WHERE clause is intentional.
UPDATE customers
SET loyalty_tier = CASE
    WHEN city_tier = 1 THEN 'Gold'
    ELSE 'Silver'
END;

-- i) Output:
-- loyalty_tier | customer_count
-- Gold         | 28
-- Silver       | 17
SELECT loyalty_tier, COUNT(*) AS customer_count
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;
