import datetime
import os
import sqlite3

from paths import DB_PATH

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK(role IN ('admin', 'staff')),
    full_name           TEXT    DEFAULT '',
    created_at          TEXT    DEFAULT (datetime('now', 'localtime')),
    is_active           INTEGER DEFAULT 1,
    has_completed_tour  INTEGER DEFAULT 0,
    last_login          TEXT    DEFAULT '',
    created_by          TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS inventory_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode          TEXT    UNIQUE NOT NULL,
    barcode_out      TEXT    UNIQUE DEFAULT '',
    item_name        TEXT    NOT NULL,
    brand            TEXT    DEFAULT '',
    category         TEXT    DEFAULT '',
    current_quantity INTEGER DEFAULT 0,
    minimum_stock    INTEGER DEFAULT 0,
    storage_location TEXT    DEFAULT '',
    shelf_life_days  INTEGER DEFAULT 0,
    expiration_date  TEXT    DEFAULT '',
    nutrition_data   TEXT    DEFAULT '{}',
    notes            TEXT    DEFAULT '',
    created_at       TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at       TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_type TEXT    NOT NULL CHECK(transaction_type IN ('SCAN_IN', 'SCAN_OUT')),
    barcode          TEXT    NOT NULL,
    item_name        TEXT    NOT NULL,
    category         TEXT    DEFAULT '',
    quantity         INTEGER NOT NULL,
    recipient        TEXT    DEFAULT '',
    username         TEXT    NOT NULL,
    timestamp        TEXT    DEFAULT (datetime('now', 'localtime')),
    notes            TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS activity_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL,
    action    TEXT NOT NULL,
    detail    TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS registered_clients (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id     TEXT    UNIQUE NOT NULL,
    hostname       TEXT    DEFAULT '',
    ip_address     TEXT    DEFAULT '',
    is_approved    INTEGER DEFAULT 0,
    registered_at  TEXT    DEFAULT (datetime('now', 'localtime')),
    last_seen      TEXT    DEFAULT '',
    approved_by    TEXT    DEFAULT '',
    notes          TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode          TEXT    UNIQUE NOT NULL,
    item_name        TEXT    NOT NULL,
    category         TEXT    DEFAULT '',
    quantity_needed  INTEGER NOT NULL DEFAULT 0,
    updated_at       TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pantry_clients (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id              TEXT    DEFAULT '',
    first_name              TEXT    NOT NULL,
    last_name               TEXT    NOT NULL,
    email                   TEXT    DEFAULT '',
    phone                   TEXT    DEFAULT '',
    semester                TEXT    DEFAULT '',
    enrollment_status       TEXT    NOT NULL DEFAULT 'full_time'
                            CHECK(enrollment_status IN ('full_time', 'part_time')),
    household_size          INTEGER DEFAULT 1,
    notes                   TEXT    DEFAULT '',
    waiver_signed           INTEGER DEFAULT 0,
    locker_waiver_signed    INTEGER DEFAULT 0,
    is_active               INTEGER DEFAULT 1,
    created_at              TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at              TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pantry_visits (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      INTEGER NOT NULL,
    visit_date     TEXT    DEFAULT (datetime('now', 'localtime')),
    pounds_received REAL   DEFAULT 0,
    notes          TEXT    DEFAULT '',
    recorded_by    TEXT    DEFAULT '',
    FOREIGN KEY (client_id) REFERENCES pantry_clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS archived_inventory (
    archive_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id      INTEGER NOT NULL,
    barcode          TEXT    NOT NULL,
    barcode_out      TEXT    DEFAULT '',
    item_name        TEXT    NOT NULL,
    brand            TEXT    DEFAULT '',
    category         TEXT    DEFAULT '',
    current_quantity INTEGER DEFAULT 0,
    minimum_stock    INTEGER DEFAULT 0,
    storage_location TEXT    DEFAULT '',
    shelf_life_days  INTEGER DEFAULT 0,
    expiration_date  TEXT    DEFAULT '',
    nutrition_data   TEXT    DEFAULT '{}',
    notes            TEXT    DEFAULT '',
    created_at       TEXT    DEFAULT '',
    updated_at       TEXT    DEFAULT '',
    archived_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    archived_by      TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS archived_pantry_clients (
    archive_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id        INTEGER NOT NULL,
    student_id         TEXT    DEFAULT '',
    first_name         TEXT    NOT NULL,
    last_name          TEXT    NOT NULL,
    email              TEXT    DEFAULT '',
    phone              TEXT    DEFAULT '',
    semester           TEXT    DEFAULT '',
    enrollment_status  TEXT    NOT NULL DEFAULT 'full_time'
                            CHECK(enrollment_status IN ('full_time', 'part_time')),
    household_size     INTEGER DEFAULT 1,
    notes              TEXT    DEFAULT '',
    waiver_signed      INTEGER DEFAULT 0,
    locker_waiver_signed INTEGER DEFAULT 0,
    is_active          INTEGER DEFAULT 1,
    created_at         TEXT    DEFAULT '',
    updated_at         TEXT    DEFAULT '',
    archived_at        TEXT    DEFAULT (datetime('now', 'localtime')),
    archived_by        TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS archived_users (
    archive_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id        INTEGER NOT NULL,
    username           TEXT    NOT NULL,
    password_hash      TEXT    NOT NULL,
    salt               TEXT    NOT NULL,
    role               TEXT    NOT NULL,
    full_name          TEXT    DEFAULT '',
    created_at         TEXT    DEFAULT '',
    is_active          INTEGER DEFAULT 1,
    has_completed_tour INTEGER DEFAULT 0,
    last_login         TEXT    DEFAULT '',
    created_by         TEXT    DEFAULT '',
    archived_at        TEXT    DEFAULT (datetime('now', 'localtime')),
    archived_by        TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS archived_transactions (
    archive_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    original_id      INTEGER NOT NULL,
    transaction_type TEXT    NOT NULL,
    barcode          TEXT    NOT NULL,
    item_name        TEXT    NOT NULL,
    category         TEXT    DEFAULT '',
    quantity         INTEGER NOT NULL,
    recipient        TEXT    DEFAULT '',
    username         TEXT    NOT NULL,
    timestamp        TEXT    DEFAULT '',
    notes            TEXT    DEFAULT '',
    archived_at      TEXT    DEFAULT (datetime('now', 'localtime')),
    archived_by      TEXT    DEFAULT ''
);
"""


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        conn = self._connect()
        conn.executescript(_SCHEMA)
        conn.commit()
        # Migrations for existing databases
        for sql in [
            "ALTER TABLE inventory_items ADD COLUMN barcode_out TEXT DEFAULT ''",
            "ALTER TABLE inventory_items ADD COLUMN brand TEXT DEFAULT ''",
            "ALTER TABLE inventory_items ADD COLUMN storage_location TEXT DEFAULT ''",
            "ALTER TABLE inventory_items ADD COLUMN shelf_life_days INTEGER DEFAULT 0",
            "ALTER TABLE inventory_items ADD COLUMN expiration_date TEXT DEFAULT ''",
            "ALTER TABLE inventory_items ADD COLUMN nutrition_data TEXT DEFAULT '{}'",
            "ALTER TABLE users ADD COLUMN has_completed_tour INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN last_login TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN created_by TEXT DEFAULT ''",
            """CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action   TEXT NOT NULL,
                detail   TEXT DEFAULT '',
                timestamp TEXT DEFAULT (datetime('now', 'localtime'))
            )""",
            """CREATE TABLE IF NOT EXISTS registered_clients (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id    TEXT UNIQUE NOT NULL,
                hostname      TEXT DEFAULT '',
                ip_address    TEXT DEFAULT '',
                is_approved   INTEGER DEFAULT 0,
                registered_at TEXT DEFAULT (datetime('now', 'localtime')),
                last_seen     TEXT DEFAULT '',
                approved_by   TEXT DEFAULT '',
                notes         TEXT DEFAULT ''
            )""",
            "ALTER TABLE pantry_clients ADD COLUMN waiver_signed INTEGER DEFAULT 0",
            "ALTER TABLE pantry_clients ADD COLUMN locker_waiver_signed INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                pass

        self._migrate_pantry_visits_cascade(conn)
        conn.close()

    def _migrate_pantry_visits_cascade(self, conn: sqlite3.Connection) -> None:
        """Rebuild pantry_visits so its FK to pantry_clients uses ON DELETE
        CASCADE. SQLite can't alter FK constraints in place; we detect the
        old definition and swap the table in a single transaction."""
        try:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='pantry_visits'"
            ).fetchone()
            if not row or not row[0]:
                return
            if "ON DELETE CASCADE" in row[0].upper():
                return

            conn.executescript("""
                BEGIN;
                CREATE TABLE pantry_visits_new (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id      INTEGER NOT NULL,
                    visit_date     TEXT    DEFAULT (datetime('now', 'localtime')),
                    pounds_received REAL   DEFAULT 0,
                    notes          TEXT    DEFAULT '',
                    recorded_by    TEXT    DEFAULT '',
                    FOREIGN KEY (client_id) REFERENCES pantry_clients(id) ON DELETE CASCADE
                );
                INSERT INTO pantry_visits_new
                    (id, client_id, visit_date, pounds_received, notes, recorded_by)
                SELECT id, client_id, visit_date, pounds_received, notes, recorded_by
                FROM pantry_visits;
                DROP TABLE pantry_visits;
                ALTER TABLE pantry_visits_new RENAME TO pantry_visits;
                COMMIT;
            """)
        except Exception:
            # If migration fails, roll back and leave the table alone;
            # cascade still works for any freshly-created database.
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------

    def create_user(self, username: str, password_hash: str, salt: str, role: str):
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                (username, password_hash, salt, role),
            )
            conn.commit()
            return True, "User created successfully."
        except sqlite3.IntegrityError:
            return False, "Username already exists."
        finally:
            conn.close()

    def get_user(self, username: str):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", (username,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_users(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT id, username, full_name, role, created_at, is_active, "
            "last_login, created_by FROM users ORDER BY username"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_last_login(self, username: str) -> None:
        conn = self._connect()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET last_login=? WHERE username=?", (ts, username))
        conn.commit()
        conn.close()

    def update_user_full_name(self, user_id: int, full_name: str) -> None:
        conn = self._connect()
        conn.execute("UPDATE users SET full_name=? WHERE id=?", (full_name, user_id))
        conn.commit()
        conn.close()

    def create_user_full(self, username: str, password_hash: str, salt: str,
                         role: str, full_name: str = "", created_by: str = ""):
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role, full_name, created_by) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, password_hash, salt, role, full_name, created_by),
            )
            conn.commit()
            return True, "User created successfully."
        except sqlite3.IntegrityError:
            return False, "Username already exists."
        finally:
            conn.close()

    def update_user_role(self, user_id: int, role: str) -> None:
        conn = self._connect()
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        conn.close()

    def update_user_password(self, user_id: int, password_hash: str, salt: str) -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (password_hash, salt, user_id),
        )
        conn.commit()
        conn.close()

    def set_user_active(self, user_id: int, active: bool) -> None:
        conn = self._connect()
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(active), user_id))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Inventory operations
    # ------------------------------------------------------------------

    def add_item(
        self,
        barcode: str,
        item_name: str,
        category: str,
        quantity: int,
        minimum_stock: int,
        notes: str,
        barcode_out: str = "",
        brand: str = "",
        storage_location: str = "",
        shelf_life_days: int = 0,
        expiration_date: str = "",
        nutrition_data: str = "{}",
    ):
        conn = self._connect()
        try:
            conn.execute(
                """INSERT INTO inventory_items
                       (barcode, barcode_out, item_name, brand, category,
                        current_quantity, minimum_stock, storage_location,
                        shelf_life_days, expiration_date, nutrition_data, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (barcode, barcode_out or None, item_name, brand, category,
                 quantity, minimum_stock, storage_location,
                 shelf_life_days, expiration_date, nutrition_data, notes),
            )
            conn.commit()
            return True, "Item added successfully."
        except sqlite3.IntegrityError as e:
            if "barcode_out" in str(e):
                return False, "That Scan-Out barcode is already used by another item."
            return False, "That Scan-In barcode is already used by another item."
        finally:
            conn.close()

    def get_item_by_barcode(self, barcode: str):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE barcode = ?", (barcode,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_item_by_any_barcode(self, barcode: str):
        """Check both barcode (Scan-In) and barcode_out (Scan-Out).

        Returns:
            (item_dict, 'SCAN_IN') | (item_dict, 'SCAN_OUT') | (None, None)
        """
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE barcode = ?", (barcode,)
        ).fetchone()
        if row:
            conn.close()
            return dict(row), "SCAN_IN"
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE barcode_out = ? AND barcode_out != ''",
            (barcode,),
        ).fetchone()
        conn.close()
        if row:
            return dict(row), "SCAN_OUT"
        return None, None

    def get_all_items(self, search: str = ""):
        conn = self._connect()
        if search:
            rows = conn.execute(
                """SELECT * FROM inventory_items
                   WHERE barcode LIKE ? OR item_name LIKE ? OR category LIKE ?
                   ORDER BY item_name""",
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM inventory_items ORDER BY item_name"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_item(
        self,
        item_id: int,
        item_name: str,
        category: str,
        minimum_stock: int,
        notes: str,
        barcode_out: str = "",
    ) -> None:
        conn = self._connect()
        conn.execute(
            """UPDATE inventory_items
               SET item_name = ?, category = ?, minimum_stock = ?, notes = ?,
                   barcode_out = ?,
                   updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (item_name, category, minimum_stock, notes, barcode_out or None, item_id),
        )
        conn.commit()
        conn.close()

    def set_stock(self, item_id: int, quantity: int) -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE inventory_items SET current_quantity = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (quantity, item_id),
        )
        conn.commit()
        conn.close()

    def adjust_stock(self, barcode: str, delta: int) -> None:
        conn = self._connect()
        conn.execute(
            """UPDATE inventory_items
               SET current_quantity = current_quantity + ?,
                   updated_at = datetime('now', 'localtime')
               WHERE barcode = ?""",
            (delta, barcode),
        )
        conn.commit()
        conn.close()

    def delete_item(self, item_id: int) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def get_low_stock_count(self) -> int:
        """Items where current_quantity <= minimum_stock (includes out-of-stock)."""
        conn = self._connect()
        count = conn.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE current_quantity <= minimum_stock"
        ).fetchone()[0]
        conn.close()
        return count

    def get_low_stock_items(self):
        """Items with 0 < current_quantity <= minimum_stock."""
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM inventory_items
               WHERE current_quantity > 0 AND current_quantity <= minimum_stock
               ORDER BY item_name"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_out_of_stock_items(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM inventory_items WHERE current_quantity = 0 ORDER BY item_name"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_expiring_items(self, days: int = 30):
        """Items expiring within the next N days (not already expired)."""
        conn = self._connect()
        today  = datetime.date.today().isoformat()
        cutoff = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT * FROM inventory_items
               WHERE expiration_date != '' AND expiration_date >= ? AND expiration_date <= ?
               ORDER BY expiration_date""",
            (today, cutoff),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_expired_items(self):
        """Items whose expiration_date is in the past."""
        conn = self._connect()
        today = datetime.date.today().isoformat()
        rows = conn.execute(
            """SELECT * FROM inventory_items
               WHERE expiration_date != '' AND expiration_date < ?
               ORDER BY expiration_date""",
            (today,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_item_extended(
        self, item_id: int, brand: str = "", storage_location: str = "",
        shelf_life_days: int = 0, expiration_date: str = "", nutrition_data: str = "{}",
    ) -> None:
        """Update AI-populated fields on an existing item."""
        conn = self._connect()
        conn.execute(
            """UPDATE inventory_items
               SET brand=?, storage_location=?, shelf_life_days=?,
                   expiration_date=?, nutrition_data=?,
                   updated_at=datetime('now','localtime')
               WHERE id=?""",
            (brand, storage_location, shelf_life_days, expiration_date, nutrition_data, item_id),
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Transaction operations
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        transaction_type: str,
        barcode: str,
        item_name: str,
        category: str,
        quantity: int,
        recipient: str,
        username: str,
        notes: str = "",
    ) -> None:
        conn = self._connect()
        conn.execute(
            """INSERT INTO transactions
                   (transaction_type, barcode, item_name, category,
                    quantity, recipient, username, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (transaction_type, barcode, item_name, category,
             quantity, recipient, username, notes),
        )
        conn.commit()
        conn.close()
        self._apply_shopping_list_delta(
            barcode, item_name, category,
            quantity if transaction_type == "SCAN_OUT" else -quantity,
        )

    # ------------------------------------------------------------------
    # Shopping list
    # ------------------------------------------------------------------

    def _apply_shopping_list_delta(self, barcode: str, item_name: str,
                                   category: str, delta: int) -> None:
        """Adjust the running shopping-list quantity for an item. Positive
        delta (SCAN_OUT) increases the amount needed; negative delta
        (SCAN_IN) reduces it. The row is removed once quantity hits 0."""
        conn = self._connect()
        row = conn.execute(
            "SELECT id, quantity_needed FROM shopping_list_items WHERE barcode=?",
            (barcode,)).fetchone()
        if row is None:
            new_qty = max(0, delta)
            if new_qty > 0:
                conn.execute(
                    "INSERT INTO shopping_list_items "
                    "(barcode, item_name, category, quantity_needed) "
                    "VALUES (?, ?, ?, ?)",
                    (barcode, item_name, category, new_qty))
        else:
            new_qty = max(0, row["quantity_needed"] + delta)
            if new_qty == 0:
                conn.execute(
                    "DELETE FROM shopping_list_items WHERE id=?", (row["id"],))
            else:
                conn.execute(
                    "UPDATE shopping_list_items SET quantity_needed=?, "
                    "item_name=?, category=?, "
                    "updated_at=datetime('now', 'localtime') WHERE id=?",
                    (new_qty, item_name, category, row["id"]))
        conn.commit()
        conn.close()

    def get_shopping_list(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM shopping_list_items ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def update_shopping_list_quantity(self, item_id: int, quantity: int) -> None:
        conn = self._connect()
        quantity = max(0, int(quantity))
        if quantity == 0:
            conn.execute("DELETE FROM shopping_list_items WHERE id=?", (item_id,))
        else:
            conn.execute(
                "UPDATE shopping_list_items SET quantity_needed=?, "
                "updated_at=datetime('now', 'localtime') WHERE id=?",
                (quantity, item_id))
        conn.commit()
        conn.close()

    def remove_shopping_list_item(self, item_id: int) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM shopping_list_items WHERE id=?", (item_id,))
        conn.commit()
        conn.close()

    def clear_shopping_list(self) -> None:
        conn = self._connect()
        conn.execute("DELETE FROM shopping_list_items")
        conn.commit()
        conn.close()

    def sync_shopping_list_from_stock(self) -> int:
        """Add or update low/out-of-stock items in the shopping list.

        Returns the number of items added/updated.
        """
        conn = self._connect()
        low = conn.execute(
            "SELECT * FROM inventory_items WHERE current_quantity > 0 "
            "AND current_quantity <= minimum_stock ORDER BY item_name"
        ).fetchall()
        out = conn.execute(
            "SELECT * FROM inventory_items WHERE current_quantity = 0 "
            "ORDER BY item_name"
        ).fetchall()

        added = 0
        for row in low + out:
            item = dict(row)
            current = int(item["current_quantity"] or 0)
            minimum = int(item["minimum_stock"] or 0)
            needed = max(minimum - current, 1)

            existing = conn.execute(
                "SELECT id, quantity_needed FROM shopping_list_items WHERE barcode=?",
                (item["barcode"],),
            ).fetchone()

            if existing is None:
                conn.execute(
                    "INSERT INTO shopping_list_items "
                    "(barcode, item_name, category, quantity_needed) "
                    "VALUES (?, ?, ?, ?)",
                    (item["barcode"], item["item_name"], item["category"], needed),
                )
                added += 1
            elif needed > int(existing["quantity_needed"]):
                conn.execute(
                    "UPDATE shopping_list_items SET quantity_needed=?, "
                    "item_name=?, category=?, "
                    "updated_at=datetime('now', 'localtime') WHERE id=?",
                    (needed, item["item_name"], item["category"], existing["id"]),
                )
                added += 1
        conn.commit()
        conn.close()
        return added

    # ------------------------------------------------------------------
    # Inventory archival
    # ------------------------------------------------------------------

    def archive_inventory_item(self, item_id: int, archived_by: str = "") -> bool:
        """Move an inventory item into archived_inventory and remove it.
        Both statements run in a single transaction; on failure the DB is
        rolled back so nothing is half-archived."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM inventory_items WHERE id=?", (item_id,)
            ).fetchone()
            if row is None:
                return False

            item = dict(row)
            conn.execute(
                """INSERT INTO archived_inventory
                    (original_id, barcode, barcode_out, item_name, brand, category,
                     current_quantity, minimum_stock, storage_location, shelf_life_days,
                     expiration_date, nutrition_data, notes, created_at, updated_at,
                     archived_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["id"], item["barcode"], item["barcode_out"], item["item_name"],
                    item["brand"], item["category"], item["current_quantity"],
                    item["minimum_stock"], item["storage_location"], item["shelf_life_days"],
                    item["expiration_date"], item["nutrition_data"], item["notes"],
                    item["created_at"], item["updated_at"], archived_by,
                ),
            )
            conn.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_archived_inventory(self, search: str = ""):
        conn = self._connect()
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT * FROM archived_inventory
                   WHERE item_name LIKE ? OR barcode LIKE ? OR brand LIKE ? OR category LIKE ?
                   ORDER BY archived_at DESC""",
                (like, like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM archived_inventory ORDER BY archived_at DESC"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def restore_archived_item(self, archive_id: int) -> bool:
        """Restore an archived inventory item back into active inventory,
        atomically. Rolls back on any error."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM archived_inventory WHERE archive_id=?", (archive_id,)
            ).fetchone()
            if row is None:
                return False

            item = dict(row)
            existing = conn.execute(
                "SELECT id FROM inventory_items WHERE barcode=?", (item["barcode"],)
            ).fetchone()

            if existing:
                conn.execute(
                    "DELETE FROM archived_inventory WHERE archive_id=?", (archive_id,)
                )
            else:
                conn.execute(
                    """INSERT INTO inventory_items
                        (barcode, barcode_out, item_name, brand, category,
                         current_quantity, minimum_stock, storage_location, shelf_life_days,
                         expiration_date, nutrition_data, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["barcode"], item["barcode_out"], item["item_name"],
                        item["brand"], item["category"], item["current_quantity"],
                        item["minimum_stock"], item["storage_location"], item["shelf_life_days"],
                        item["expiration_date"], item["nutrition_data"], item["notes"],
                        item["created_at"], item["updated_at"],
                    ),
                )
                conn.execute(
                    "DELETE FROM archived_inventory WHERE archive_id=?", (archive_id,)
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def permanently_delete_archived_item(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM archived_inventory WHERE archive_id=?", (archive_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Pantry client archival
    # ------------------------------------------------------------------

    def archive_pantry_client(self, client_id: int, archived_by: str = "") -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM pantry_clients WHERE id=?", (client_id,)
            ).fetchone()
            if row is None:
                return False

            client = dict(row)
            conn.execute(
                """INSERT INTO archived_pantry_clients
                    (original_id, student_id, first_name, last_name, email, phone,
                     semester, enrollment_status, household_size, notes, waiver_signed,
                     locker_waiver_signed, is_active, created_at, updated_at, archived_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    client["id"], client["student_id"], client["first_name"], client["last_name"],
                    client["email"], client["phone"], client["semester"], client["enrollment_status"],
                    client["household_size"], client["notes"], client["waiver_signed"],
                    client["locker_waiver_signed"], client["is_active"], client["created_at"],
                    client["updated_at"], archived_by,
                ),
            )
            conn.execute("DELETE FROM pantry_clients WHERE id=?", (client_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_archived_clients(self, search: str = ""):
        conn = self._connect()
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT * FROM archived_pantry_clients
                   WHERE first_name LIKE ? OR last_name LIKE ? OR student_id LIKE ?
                   ORDER BY archived_at DESC""",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM archived_pantry_clients ORDER BY archived_at DESC"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def restore_archived_client(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM archived_pantry_clients WHERE archive_id=?", (archive_id,)
            ).fetchone()
            if row is None:
                return False

            client = dict(row)
            existing = conn.execute(
                "SELECT id FROM pantry_clients WHERE student_id=?",
                (client["student_id"],),
            ).fetchone()

            if existing:
                conn.execute(
                    "DELETE FROM archived_pantry_clients WHERE archive_id=?", (archive_id,)
                )
            else:
                conn.execute(
                    """INSERT INTO pantry_clients
                        (student_id, first_name, last_name, email, phone, semester,
                         enrollment_status, household_size, notes, waiver_signed,
                         locker_waiver_signed, is_active, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        client["student_id"], client["first_name"], client["last_name"],
                        client["email"], client["phone"], client["semester"],
                        client["enrollment_status"], client["household_size"], client["notes"],
                        client["waiver_signed"], client["locker_waiver_signed"],
                        client["is_active"], client["created_at"], client["updated_at"],
                    ),
                )
                conn.execute(
                    "DELETE FROM archived_pantry_clients WHERE archive_id=?", (archive_id,)
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def permanently_delete_archived_client(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM archived_pantry_clients WHERE archive_id=?", (archive_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # User archival
    # ------------------------------------------------------------------

    def archive_user(self, user_id: int, archived_by: str = "") -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE id=?", (user_id,)
            ).fetchone()
            if row is None:
                return False

            user = dict(row)
            conn.execute(
                """INSERT INTO archived_users
                    (original_id, username, password_hash, salt, role, full_name,
                     created_at, is_active, has_completed_tour, last_login, created_by, archived_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user["id"], user["username"], user["password_hash"], user["salt"],
                    user["role"], user["full_name"], user["created_at"], user["is_active"],
                    user["has_completed_tour"], user["last_login"], user["created_by"], archived_by,
                ),
            )
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_archived_users(self, search: str = ""):
        conn = self._connect()
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT * FROM archived_users
                   WHERE username LIKE ? OR full_name LIKE ?
                   ORDER BY archived_at DESC""",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM archived_users ORDER BY archived_at DESC"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def restore_archived_user(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM archived_users WHERE archive_id=?", (archive_id,)
            ).fetchone()
            if row is None:
                return False

            user = dict(row)
            existing = conn.execute(
                "SELECT id FROM users WHERE username=?", (user["username"],)
            ).fetchone()

            if existing:
                conn.execute(
                    "DELETE FROM archived_users WHERE archive_id=?", (archive_id,)
                )
            else:
                conn.execute(
                    """INSERT INTO users
                        (username, password_hash, salt, role, full_name, created_at,
                         is_active, has_completed_tour, last_login, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user["username"], user["password_hash"], user["salt"],
                        user["role"], user["full_name"], user["created_at"],
                        user["is_active"], user["has_completed_tour"], user["last_login"],
                        user["created_by"],
                    ),
                )
                conn.execute(
                    "DELETE FROM archived_users WHERE archive_id=?", (archive_id,)
                )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def permanently_delete_archived_user(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM archived_users WHERE archive_id=?", (archive_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Transaction archival
    # ------------------------------------------------------------------

    def archive_transaction(self, transaction_id: int, archived_by: str = "") -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM transactions WHERE id=?", (transaction_id,)
            ).fetchone()
            if row is None:
                return False

            txn = dict(row)
            conn.execute(
                """INSERT INTO archived_transactions
                    (original_id, transaction_type, barcode, item_name, category,
                     quantity, recipient, username, timestamp, notes, archived_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    txn["id"], txn["transaction_type"], txn["barcode"], txn["item_name"],
                    txn["category"], txn["quantity"], txn["recipient"], txn["username"],
                    txn["timestamp"], txn["notes"], archived_by,
                ),
            )
            conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_archived_transactions(self, search: str = ""):
        conn = self._connect()
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT * FROM archived_transactions
                   WHERE item_name LIKE ? OR barcode LIKE ? OR username LIKE ?
                   ORDER BY archived_at DESC""",
                (like, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM archived_transactions ORDER BY archived_at DESC"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def restore_archived_transaction(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM archived_transactions WHERE archive_id=?", (archive_id,)
            ).fetchone()
            if row is None:
                return False

            txn = dict(row)
            conn.execute(
                """INSERT INTO transactions
                    (transaction_type, barcode, item_name, category, quantity,
                     recipient, username, timestamp, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    txn["transaction_type"], txn["barcode"], txn["item_name"],
                    txn["category"], txn["quantity"], txn["recipient"], txn["username"],
                    txn["timestamp"], txn["notes"],
                ),
            )
            conn.execute(
                "DELETE FROM archived_transactions WHERE archive_id=?", (archive_id,)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def permanently_delete_archived_transaction(self, archive_id: int) -> bool:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM archived_transactions WHERE archive_id=?", (archive_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Pantry clients (student profiles)
    # ------------------------------------------------------------------

    def create_pantry_client(self, first_name: str, last_name: str,
                              student_id: str = "", email: str = "",
                              phone: str = "", semester: str = "",
                              enrollment_status: str = "full_time",
                              household_size: int = 1, notes: str = "",
                              waiver_signed: int = 0,
                              locker_waiver_signed: int = 0) -> int:
        conn = self._connect()
        cur = conn.execute(
            """INSERT INTO pantry_clients
                   (student_id, first_name, last_name, email, phone,
                    semester, enrollment_status, household_size, notes,
                    waiver_signed, locker_waiver_signed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, first_name, last_name, email, phone,
             semester, enrollment_status, household_size, notes,
             waiver_signed, locker_waiver_signed),
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id

    def update_pantry_client(self, client_id: int, first_name: str,
                              last_name: str, student_id: str = "",
                              email: str = "", phone: str = "",
                              semester: str = "",
                              enrollment_status: str = "full_time",
                              household_size: int = 1, notes: str = "",
                              waiver_signed: int = 0,
                              locker_waiver_signed: int = 0) -> None:
        conn = self._connect()
        conn.execute(
            """UPDATE pantry_clients
               SET first_name=?, last_name=?, student_id=?, email=?, phone=?,
                   semester=?, enrollment_status=?, household_size=?, notes=?,
                   waiver_signed=?, locker_waiver_signed=?,
                   updated_at=datetime('now', 'localtime')
               WHERE id=?""",
            (first_name, last_name, student_id, email, phone, semester,
             enrollment_status, household_size, notes,
             waiver_signed, locker_waiver_signed, client_id),
        )
        conn.commit()
        conn.close()

    def set_pantry_client_active(self, client_id: int, active: bool) -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE pantry_clients SET is_active=?, "
            "updated_at=datetime('now', 'localtime') WHERE id=?",
            (1 if active else 0, client_id))
        conn.commit()
        conn.close()

    def get_all_pantry_clients(self, search: str = ""):
        conn = self._connect()
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT * FROM pantry_clients
                   WHERE first_name LIKE ? OR last_name LIKE ?
                      OR student_id LIKE ? OR email LIKE ?
                   ORDER BY last_name, first_name""",
                (like, like, like, like)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pantry_clients ORDER BY last_name, first_name"
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_pantry_client(self, client_id: int):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM pantry_clients WHERE id=?", (client_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Pantry visits
    # ------------------------------------------------------------------

    def record_pantry_visit(self, client_id: int, pounds_received: float,
                             recorded_by: str, notes: str = "") -> int:
        conn = self._connect()
        cur = conn.execute(
            """INSERT INTO pantry_visits
                   (client_id, pounds_received, recorded_by, notes)
               VALUES (?, ?, ?, ?)""",
            (client_id, pounds_received, recorded_by, notes),
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id

    def get_client_visits(self, client_id: int):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM pantry_visits WHERE client_id=? "
            "ORDER BY visit_date DESC", (client_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_visit_count_since(self, client_id: int, since_iso_date: str) -> int:
        """Count visits for a client on/after the given ISO date (YYYY-MM-DD)."""
        conn = self._connect()
        count = conn.execute(
            "SELECT COUNT(*) FROM pantry_visits "
            "WHERE client_id=? AND DATE(visit_date) >= ?",
            (client_id, since_iso_date)).fetchone()[0]
        conn.close()
        return count

    def get_client_visit_stats(self, client_id: int) -> dict:
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(*) AS total_visits, "
            "COALESCE(SUM(pounds_received),0) AS total_pounds, "
            "MAX(visit_date) AS last_visit "
            "FROM pantry_visits WHERE client_id=?", (client_id,)).fetchone()
        conn.close()
        return dict(row) if row else {"total_visits": 0, "total_pounds": 0, "last_visit": None}

    def get_recent_pantry_visits(self, limit: int = 20):
        conn = self._connect()
        rows = conn.execute(
            """SELECT v.*, c.first_name, c.last_name, c.enrollment_status
               FROM pantry_visits v
               JOIN pantry_clients c ON c.id = v.client_id
               ORDER BY v.visit_date DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Dashboard stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        conn = self._connect()
        total = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(current_quantity),0) FROM inventory_items"
        ).fetchone()
        low = conn.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE current_quantity > 0 AND current_quantity <= minimum_stock"
        ).fetchone()[0]
        out = conn.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE current_quantity = 0"
        ).fetchone()[0]
        today = datetime.date.today().isoformat()
        sin = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(quantity),0) FROM transactions "
            "WHERE transaction_type='SCAN_IN' AND DATE(timestamp)=?", (today,)
        ).fetchone()
        sout = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(quantity),0) FROM transactions "
            "WHERE transaction_type='SCAN_OUT' AND DATE(timestamp)=?", (today,)
        ).fetchone()
        users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_active=1"
        ).fetchone()[0]
        disabled_users = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_active=0"
        ).fetchone()[0]
        week_start = (datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())).isoformat()
        month_start = datetime.date.today().replace(day=1).isoformat()
        week_txns = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE DATE(timestamp)>=?", (week_start,)
        ).fetchone()[0]
        month_txns = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE DATE(timestamp)>=?", (month_start,)
        ).fetchone()[0]
        today_txns = (sin[0] or 0) + (sout[0] or 0)
        new_users_week = conn.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at)>=?", (week_start,)
        ).fetchone()[0]
        most_active_row = conn.execute(
            "SELECT username, COUNT(*) as cnt FROM transactions "
            "WHERE DATE(timestamp)=? GROUP BY username ORDER BY cnt DESC LIMIT 1", (today,)
        ).fetchone()
        most_scanned_row = conn.execute(
            "SELECT item_name, COUNT(*) as cnt FROM transactions "
            "WHERE DATE(timestamp)=? GROUP BY item_name ORDER BY cnt DESC LIMIT 1", (today,)
        ).fetchone()
        conn.close()
        return {
            "total_items": total[0] or 0,
            "total_units": total[1] or 0,
            "low_stock":   low,
            "out_of_stock": out,
            "today_in_count":  sin[0] or 0,
            "today_in_qty":    sin[1] or 0,
            "today_out_count": sout[0] or 0,
            "today_out_qty":   sout[1] or 0,
            "today_total":     today_txns,
            "active_users":    users,
            "disabled_users":  disabled_users,
            "new_users_week":  new_users_week,
            "week_txns":       week_txns,
            "month_txns":      month_txns,
            "most_active_user": most_active_row[0] if most_active_row else "—",
            "most_scanned_item": most_scanned_row[0] if most_scanned_row else "—",
        }

    def get_scan_trend(self, days: int = 7, username: str = None):
        """Return scan-in / scan-out totals per day for the last N days."""
        conn = self._connect()
        result = []
        today = datetime.date.today()
        for i in range(days - 1, -1, -1):
            d = (today - datetime.timedelta(days=i)).isoformat()
            label = d[5:]
            user_filter = " AND username=?" if username else ""
            params = [d, username] if username else [d]
            sin = conn.execute(
                f"SELECT COALESCE(SUM(quantity),0) FROM transactions "
                f"WHERE transaction_type='SCAN_IN' AND DATE(timestamp)=?{user_filter}",
                params,
            ).fetchone()[0]
            sout = conn.execute(
                f"SELECT COALESCE(SUM(quantity),0) FROM transactions "
                f"WHERE transaction_type='SCAN_OUT' AND DATE(timestamp)=?{user_filter}",
                params,
            ).fetchone()[0]
            result.append({"label": label, "in": int(sin), "out": int(sout)})
        conn.close()
        return result

    def get_inventory_by_category(self, limit: int = 8):
        conn = self._connect()
        rows = conn.execute(
            """SELECT category AS label, COUNT(*) AS value
               FROM inventory_items
               WHERE category != ''
               GROUP BY category
               ORDER BY value DESC
               LIMIT ?""", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_top_low_stock(self, limit: int = 8):
        conn = self._connect()
        rows = conn.execute(
            """SELECT item_name, current_quantity, minimum_stock,
                      (minimum_stock - current_quantity) AS gap
               FROM inventory_items
               WHERE current_quantity <= minimum_stock
               ORDER BY gap DESC
               LIMIT ?""", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_recent_transactions(self, limit: int = 12):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Tour & settings
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Activity log
    # ------------------------------------------------------------------

    def log_activity(self, username: str, action: str, detail: str = "") -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO activity_log(username, action, detail) VALUES(?,?,?)",
            (username, action, detail))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Registered clients
    # ------------------------------------------------------------------

    def upsert_client(self, machine_id: str, hostname: str, ip: str) -> bool:
        """Register client if new; update last_seen. Returns True if new."""
        conn = self._connect()
        existing = conn.execute(
            "SELECT id FROM registered_clients WHERE machine_id=?",
            (machine_id,)
        ).fetchone()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if existing:
            conn.execute(
                "UPDATE registered_clients SET last_seen=?, ip_address=? WHERE machine_id=?",
                (ts, ip, machine_id))
            conn.commit()
            conn.close()
            return False
        else:
            conn.execute(
                "INSERT INTO registered_clients (machine_id, hostname, ip_address, last_seen) "
                "VALUES (?,?,?,?)",
                (machine_id, hostname, ip, ts))
            conn.commit()
            conn.close()
            return True

    def get_all_clients(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM registered_clients ORDER BY registered_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def set_client_approved(self, machine_id: str, approved: bool,
                            approved_by: str = "") -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE registered_clients SET is_approved=?, approved_by=? "
            "WHERE machine_id=?",
            (int(approved), approved_by, machine_id))
        conn.commit()
        conn.close()

    def is_client_approved(self, machine_id: str) -> bool:
        conn = self._connect()
        row = conn.execute(
            "SELECT is_approved FROM registered_clients WHERE machine_id=?",
            (machine_id,)).fetchone()
        conn.close()
        return bool(row and row[0])

    def get_activity_log(self, limit: int = 200):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def clear_activity_log(self, older_than_days: int = None) -> int:
        """Delete activity log entries. If older_than_days is None, clears
        the entire log. Otherwise deletes only entries older than that many
        days. Returns the number of rows deleted."""
        conn = self._connect()
        if older_than_days is None:
            cur = conn.execute("DELETE FROM activity_log")
        else:
            cur = conn.execute(
                "DELETE FROM activity_log WHERE timestamp < "
                "datetime('now', 'localtime', ?)",
                (f"-{int(older_than_days)} days",))
        conn.commit()
        deleted = cur.rowcount
        conn.close()
        return deleted

    def set_tour_complete(self, user_id: int) -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE users SET has_completed_tour=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def get_app_setting(self, key: str, default: str = "") -> str:
        conn = self._connect()
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default

    def set_app_setting(self, key: str, value: str) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO app_settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value))
        conn.commit()
        conn.close()

    def get_transactions(
        self,
        search: str = "",
        trans_type: str = "",
        date_from: str = "",
        date_to: str = "",
        recipient: str = "",
    ):
        conn = self._connect()
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if search:
            query += " AND (barcode LIKE ? OR item_name LIKE ? OR category LIKE ?)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        if trans_type:
            query += " AND transaction_type = ?"
            params.append(trans_type)
        if date_from:
            query += " AND timestamp >= ?"
            params.append(date_from)
        if date_to:
            query += " AND timestamp <= ?"
            params.append(date_to + " 23:59:59")
        if recipient:
            query += " AND recipient LIKE ?"
            params.append(f"%{recipient}%")

        query += " ORDER BY timestamp DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
