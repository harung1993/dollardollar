# Utility Scripts

This directory contains various utility scripts for database management, testing, and maintenance.

## Database Management

### `init_db.py`
Initializes the database by creating all tables defined in the models.

```bash
python scripts/init_db.py
```

### `reset.py`
Resets the database by dropping all tables and recreating them. **Use with caution!**

```bash
python scripts/reset.py
```

### `add_column.py`
Database migration utility for adding columns to existing tables.

```bash
python scripts/add_column.py
```

### `fix_currency.py`
Utility to fix currency-related issues in the database, such as setting the base currency.

```bash
python scripts/fix_currency.py
```

## Demo & Testing

### `demo_reset.py`
Resets the database and populates it with demo data for testing purposes.

```bash
python scripts/demo_reset.py
```

### `test_app.py`
Basic application tests to verify functionality.

```bash
python scripts/test_app.py
```

## Currency Management

### `update_currencies.py`
Updates exchange rates for all currencies in the database from external API sources.

```bash
python scripts/update_currencies.py
```

## Notes

- All scripts should be run from the project root directory
- Make sure your virtual environment is activated before running scripts
- Some scripts require database connection to be configured in environment variables
