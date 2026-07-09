# Product Recommendation Engine

A separate Python module for generating supermarket product recommendations from the existing ERP MySQL database.

The existing ERP remains unchanged. This service reads from the shared ERP database tables and will later write generated recommendations to a dedicated `product_recommendations` table.

No recommendation algorithm, transaction builder, scheduler, API, or association rule logic is implemented in this stage.

## Architecture

The module is organized around infrastructure concerns only:

- Configuration loading and validation from environment variables.
- MySQL connection pooling with safe reconnect and shutdown behavior.
- Generic database manager for query execution and transaction control.
- Generic base repository for future table-specific repositories.
- Centralized console and rotating file logging.
- Simple entry point that validates configuration, connects to MySQL, runs a health check, and exits safely.

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
- `sales`

Write access can be added later for the future `product_recommendations` table.

## Running

From inside the `recommendation_engine` directory:

```bash
python main.py
```

Expected output:

```text
Recommendation Engine initialized successfully.
```

The command loads configuration, initializes logging, connects to MySQL through a connection pool, runs `SELECT 1 AS healthy`, and disconnects safely.

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

Not implemented in this stage:

- FP-Growth
- Transaction builder
- Recommendation repository
- Association rules
- Scheduler jobs
- API endpoints

## Transaction Extraction Layer

This stage adds schema-aware basket reconstruction from the ERP tables:

- `sales`
- `products_logs`
- `products`

The extraction layer joins sale headers to sale line records using `products_logs.referrer = sales.id`, filters sale lines with `products_logs.type = 0`, and joins product metadata using `products.id = products_logs.product`.

Implemented components:

- `models/transaction.py` defines `TransactionItem` and `TransactionBasket` data models.
- `repositories/transaction_repository.py` reads sale item rows from MySQL.
- `services/transaction_extraction_service.py` groups sale rows into baskets and prepares product ID transactions or a one-hot `pandas.DataFrame` for future FP-Growth processing.

Example usage inside application code:

```python
repository = TransactionRepository(database_manager)
service = TransactionExtractionService(repository)

baskets = service.extract_baskets(branch_id=1, months=3)
transactions = service.extract_product_id_transactions(branch_id=1, months=3)
one_hot = service.extract_one_hot_dataframe(branch_id=1, months=3)
```

The extraction layer does not mine frequent itemsets, generate association rules, or write recommendations. Those steps are intentionally left for later implementation.

## Production FP-Growth Recommendation Engine

The production recommendation path uses only the ApexCloud ERP inventory ledger table `products_logs`.

Transaction extraction rules:

- Read only `products_logs`.
- Use only `type = 0` sales rows.
- Do not read `sales` or invoice detail tables.
- Group rows by `referrer`; each unique referrer is one customer purchase basket.
- Duplicate product IDs inside the same referrer are reduced to one item.
- Invalid product IDs are ignored.

Create the recommendation output table with:

```sql
source sql/create_product_pair.sql
```

The `product_pair` table stores one-to-one association rules with `support`, `confidence`, and `lift`. Updates use `INSERT ... ON DUPLICATE KEY UPDATE`; the engine does not truncate previous results on every run.

Configuration:

```env
RECOMMENDATION_BATCH_SIZE=5000
FP_GROWTH_MIN_SUPPORT=0.001
FP_GROWTH_MIN_CONFIDENCE=0.05
```

Example wiring:

```python
transaction_repository = TransactionRepository(database_manager)
transaction_service = TransactionExtractionService(transaction_repository)
recommendation_repository = RecommendationRepository(database_manager)
fp_growth_service = FPGrowthService(
    transaction_extraction_service=transaction_service,
    recommendation_repository=recommendation_repository,
    min_support=settings.fp_growth_min_support,
    min_confidence=settings.fp_growth_min_confidence,
    batch_size=settings.recommendation_batch_size,
)

summary = fp_growth_service.run(months=3)
```

Lookup recommendations for a product through `RecommendationRepository.find_pairs_for_product(product_id)`.
