#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATABASE="$PROJECT_ROOT/data/mamaearth.db"
TEMP_DATABASE="$(mktemp "$PROJECT_ROOT/data/.mamaearth.db.XXXXXX")"

cleanup() {
    rm -f "$TEMP_DATABASE"
}
trap cleanup EXIT

cd "$PROJECT_ROOT"

sqlite3 "$TEMP_DATABASE" < sql/schema.sql
sqlite3 "$TEMP_DATABASE" < sql/seed_data.sql
sqlite3 "$TEMP_DATABASE" < sql/reports.sql

assert_query() {
    local description="$1"
    local expected="$2"
    local query="$3"
    local actual

    actual="$(sqlite3 -batch -list -noheader "$TEMP_DATABASE" "$query")"
    if [[ "$actual" != "$expected" ]]; then
        printf 'Validation failed for %s: expected <%s>, got <%s>\n' \
            "$description" "$expected" "$actual" >&2
        exit 1
    fi
}

assert_query \
    "seed row counts" \
    "45|16|180" \
    "SELECT (SELECT COUNT(*) FROM customers) || '|' || (SELECT COUNT(*) FROM products) || '|' || (SELECT COUNT(*) FROM orders);"

assert_query \
    "missing ratings and discounts" \
    "15|12" \
    "SELECT SUM(rating IS NULL) || '|' || SUM(discount_pct IS NULL) FROM orders;"

assert_query \
    "discounted revenue" \
    "99860.20" \
    "SELECT printf('%.2f', SUM(o.quantity * p.price * (1.0 - COALESCE(o.discount_pct, 0) / 100.0))) FROM orders AS o JOIN products AS p USING (product_id);"

assert_query \
    "top five customer spenders" \
    "C043:Reyansh:12920.00|C026:Isha:8371.60|C008:Meera:4564.60|C011:Arjun:4111.00|C042:Sanya:3785.00" \
    "SELECT group_concat(customer_id || ':' || name || ':' || printf('%.2f', total_spend), '|') FROM (SELECT c.customer_id, c.name, SUM(o.quantity * p.price * (1.0 - COALESCE(o.discount_pct, 0) / 100.0)) AS total_spend FROM orders AS o JOIN products AS p USING (product_id) JOIN customers AS c USING (customer_id) GROUP BY c.customer_id, c.name ORDER BY total_spend DESC, c.customer_id ASC LIMIT 5);"

assert_query \
    "unrated order count" \
    "15" \
    "SELECT COUNT(*) - COUNT(rating) FROM orders;"

assert_query \
    "loyalty tier counts" \
    "Gold:28|Silver:17" \
    "SELECT group_concat(loyalty_tier || ':' || customer_count, '|') FROM (SELECT loyalty_tier, COUNT(*) AS customer_count FROM customers GROUP BY loyalty_tier ORDER BY loyalty_tier);"

assert_query \
    "foreign key check" \
    "" \
    "PRAGMA foreign_key_check;"

assert_query \
    "database integrity check" \
    "ok" \
    "PRAGMA integrity_check;"

mv -f "$TEMP_DATABASE" "$DATABASE"
trap - EXIT
printf '\nSQLite database rebuilt and verified: %s\n' "$DATABASE"
