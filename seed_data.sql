.bail on
PRAGMA foreign_keys = ON;
.mode csv

-- Delete in dependency order so this import can be safely rerun.
DELETE FROM orders;
DELETE FROM customers;
DELETE FROM products;

-- Import the original source files without their header rows.
.import --skip 1 data/customers.csv customers
.import --skip 1 data/products.csv products
.import --skip 1 data/orders.csv orders

-- SQLite .import stores blank cells as empty strings; convert them to SQL NULL
-- so COUNT(rating) and other NULL-aware reports behave correctly.
UPDATE orders
SET discount_pct = NULL
WHERE NULLIF(TRIM(CAST(discount_pct AS TEXT)), '') IS NULL;

UPDATE orders
SET rating = NULL
WHERE NULLIF(TRIM(CAST(rating AS TEXT)), '') IS NULL;
