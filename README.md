# Product Recommendation Engine

A separate Python module for generating supermarket product recommendations from the existing ERP MySQL database.

The existing ERP remains unchanged. This service reads from the shared ERP database tables and writes generated recommendations to the `product_pair` table.

The module now includes basket extraction, pair-count recommendation mining, and a scheduler for incremental daily updates plus weekly full rebuilds. API endpoints are still not implemented.

## Architecture

The module is organized around infrastructure concerns only:

- Configuration loading and validation from environment variables.
- MySQL connection pooling with safe reconnect and shutdown behavior.
- Generic database manager for query execution and transaction control.
- Generic base repository for future table-specific repositories.
- Centralized console and rotating file logging.
- Simple entry point that validates configuration, connects to MySQL, runs recommendation generation, and exits safely.

## Folder Structure

```text
recommendation_engine/
  config/
    __init__.py
    database.py
    settings.py
  database/
    __init__.py
    connection.py
    base_repository.py
  repositories/
    __init__.py
  services/
    __init__.py
  scheduler/
    __init__.py
    recommendation_scheduler.py
  models/
    __init__.py
  sql/
    .gitkeep
  utils/
    logger.py
  tests/
    .gitkeep
  .env.example
  requirements.txt
  README.md
  main.py
```

## Installation

Use Python 3.11 or newer.

```bash
cd recommendation_engine
python -m venv .venv
```

Activate the virtual environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Configure the database connection:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=your_erp_database
DB_USER=your_database_user
DB_PASSWORD=your_database_password
LOG_LEVEL=INFO
```

The database user should have read access to the existing ERP tables:

- `products`
- `products_logs`
- `sales_order`
- `sales`

Write access is required for the `product_pair` recommendation table.

## Running

From inside the `recommendation_engine` directory:

```bash
python main.py
```

Expected output:

```text
Recommendation generation completed: {...}
```

The command loads configuration, initializes logging, connects to MySQL through a connection pool, runs the recommendation scheduler, and disconnects safely.

For automation, run `main.py` using Windows Task Scheduler or cron.

## Current Scope

Implemented in this stage:

- Project architecture
- Dependency management
- Environment configuration
- Settings validation
- MySQL connection manager
- Generic database operations
- Generic base repository
- Logger
- Entry point
- Documentation
- Transaction builder
- Pair-count recommendation mining
- Recommendation repository
- Support/confidence/lift calculations
- Scheduler jobs

Still not implemented:

- API endpoints

## Transaction Extraction Layer

This stage adds schema-aware basket reconstruction from the ERP tables:

- `sales_order`
- `products_logs`
- `products`

The extraction layer joins `sales_order.sales` to `products_logs.referrer` to exclude instore sales, filters sale lines with `products_logs.type = 0`, and joins product metadata using `products.id = products_logs.product` with `products.on_app = 1`.

Implemented components:

- `models/transaction.py` defines `TransactionItem` and `TransactionBasket` data models.
- `repositories/transaction_repository.py` reads sale item rows from MySQL.
- `services/transaction_extraction_service.py` groups sale rows into baskets and prepares product ID transactions for recommendation processing.
- `services/pair_count_service.py` counts product pairs, calculates support/confidence/lift, and stores one-to-one recommendation rules.

Example usage inside application code:

```python
repository = TransactionRepository(database_manager)
service = TransactionExtractionService(repository)

baskets = service.extract_baskets(branch_id=1, months=3)
transactions = service.extract_product_id_transactions(branch_id=1, months=3)
```

The extraction layer prepares baskets; `services/pair_count_service.py` counts product pairs, calculates support/confidence/lift, and writes recommendations.

## Production Pair-Count Recommendation Engine

The production recommendation path uses `products_logs` as the line-item source, `sales_order` to restrict baskets to non-instore sales, and `products` to keep only app-enabled items.

Transaction extraction rules:

- Read `products_logs` line items.
- Keep only `type = 0` sold rows.
- Join `sales_order` on `sales_order.sales = products_logs.referrer` to exclude instore sales.
- Join `products` and keep only `products.on_app = 1`.
- Group rows by `referrer`; each unique referrer is one customer purchase basket.
- Duplicate product IDs inside the same referrer are reduced to one item.

Create the basket query with:

```sql
source sql/pair_count_baskets.sql
```

Create the recommendation output table with:

```sql
source sql/create_product_pair.sql
```

The `product_pair` table stores one-to-one recommendation rules with `support`, `confidence`, and `lift`. These metrics are calculated from co-occurrence counts in code and then written with `INSERT ... ON DUPLICATE KEY UPDATE`; the engine does not truncate previous results on every run.

A scheduler runs daily incremental updates for new sales and performs a weekly full rebuild to correct drift and refresh stale recommendations. The scheduler stores its state in `state/recommendation_scheduler.json`.

Configuration:

```env
RECOMMENDATION_BATCH_SIZE=5000
PAIR_COUNT_MIN_SUPPORT=0.001
PAIR_COUNT_MIN_CONFIDENCE=0.05
```

Legacy `FP_GROWTH_MIN_SUPPORT` and `FP_GROWTH_MIN_CONFIDENCE` values are still accepted for compatibility.

For product suggestions, results are ordered by `lift DESC`, then `confidence DESC`, then `support DESC`.

Example wiring:

```python
transaction_repository = TransactionRepository(database_manager)
transaction_service = TransactionExtractionService(transaction_repository)
recommendation_repository = RecommendationRepository(database_manager)
recommendation_service = PairCountRecommendationService(
    transaction_extraction_service=transaction_service,
    recommendation_repository=recommendation_repository,
    min_support=settings.pair_count_min_support,
    min_confidence=settings.pair_count_min_confidence,
    batch_size=settings.recommendation_batch_size,
)

summary = recommendation_service.run(months=3)
```

Lookup recommendations for a product through `RecommendationRepository.find_pairs_for_product(product_id, limit=3)`.

## Scheduling daily and weekly jobs

This project does not keep a background process running all the time. Use the operating system scheduler to start `python main.py` automatically.

### Windows Task Scheduler

Create two tasks:

- **Daily task**: run every day to process incremental updates.
- **Weekly task**: run once per week to perform a full rebuild.

Use the same command for both tasks:

```bash
python main.py
```

### cron (Linux/macOS)

Example daily run at 2:00 AM:

```cron
0 2 * * * /path/to/python /path/to/recommendation_engine/main.py
```

Example weekly full rebuild run on Sunday at 2:00 AM:

```cron
0 2 * * 0 /path/to/python /path/to/recommendation_engine/main.py
```

The scheduler decides whether to do an incremental update or a weekly rebuild based on `state/recommendation_scheduler.json`.
