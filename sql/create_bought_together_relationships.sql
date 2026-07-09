CREATE TABLE IF NOT EXISTS bought_together_relationships (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product BIGINT UNSIGNED NOT NULL,
    pair BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_bought_together_product_pair (product, pair),
    KEY idx_bought_together_product (product),
    KEY idx_bought_together_pair (pair)
);
