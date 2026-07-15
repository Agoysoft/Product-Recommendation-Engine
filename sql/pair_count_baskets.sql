-- Basket extraction query for pair-count recommendations
-- Builds one basket per sale from non-instore sales in sales_order
-- and keeps only products marked as on_app = 1.

SELECT
    pl.referrer AS sales_id,
    GROUP_CONCAT(DISTINCT pl.product ORDER BY pl.product) AS products,
    COUNT(DISTINCT pl.product) AS item_count
FROM products_logs pl
JOIN (
    SELECT DISTINCT sales
    FROM sales_order
    WHERE sales IS NOT NULL
) so
    ON so.sales = pl.referrer
JOIN products p
    ON p.id = pl.product
   AND p.on_app = 1
WHERE pl.type = 0
GROUP BY pl.referrer
HAVING COUNT(DISTINCT pl.product) > 1
ORDER BY pl.referrer;
