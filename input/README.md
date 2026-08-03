# Harvest Hero — Input Folder

Place CSV files here to bulk-import inventory items into the application.

## How to Import

1. Create a CSV file with the columns below (use `inventory_template.csv` as a starting point)
2. Save it anywhere — the app opens a file picker defaulting to this folder
3. Go to **Settings → Data Import → Import Inventory CSV**
4. Select your file — the app will add new items and update existing ones

## CSV Column Reference

| Column | Required | Description | Example |
|---|---|---|---|
| `barcode` | **Yes** | Unique barcode / SKU | `012345678901` |
| `item_name` | **Yes** | Product name | `Canned Tomatoes` |
| `brand` | No | Brand name | `Hunt's` |
| `category` | No | Category label | `Canned Goods` |
| `current_quantity` | No | Units on hand (default 0) | `24` |
| `minimum_stock` | No | Low-stock threshold | `6` |
| `storage_location` | No | Shelf / bin / room | `Shelf A-3` |
| `expiration_date` | No | ISO date YYYY-MM-DD | `2025-12-31` |
| `notes` | No | Free-text notes | `Donated by Acme` |

## Rules

- The `barcode` column is the unique key — existing items with the same barcode will be **updated**, not duplicated
- Rows missing `barcode` or `item_name` are skipped
- The file must be UTF-8 encoded (standard for Excel "Save As CSV UTF-8")
- Column order does not matter; extra columns are ignored
