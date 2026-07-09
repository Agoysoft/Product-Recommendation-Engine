CREATE TABLE IF NOT EXISTS product_pair (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product BIGINT UNSIGNED NOT NULL,
    pair BIGINT UNSIGNED NOT NULL,
    support DECIMAL(18, 10) NOT NULL DEFAULT 0,
    confidence DECIMAL(18, 10) NOT NULL DEFAULT 0,
    lift DECIMAL(18, 10) NOT NULL DEFAULT 0,
    cooccurrence_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    antecedent_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    consequent_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    transaction_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_product_pair (product, pair),
    KEY idx_product_pair_product (product),
    KEY idx_product_pair_pair (pair),
    KEY idx_product_pair_rank (product, lift, confidence, support)
);
