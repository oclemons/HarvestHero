import calendar
import datetime
import json
import os
import re
import sqlite3
from uuid import uuid4

from paths import DB_PATH

INVENTORY_COLUMNS = ("barcode", "item", "category", "quantity", "minimum", "location")


def _utc_date() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


def _add_calendar_months(day: datetime.date, months: int) -> datetime.date:
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    month += 1
    return datetime.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS roles (
    name        TEXT    PRIMARY KEY,       -- 'admin', 'student', ...
    description TEXT    DEFAULT '',
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
);

INSERT OR IGNORE INTO roles(name, description) VALUES
    ('admin',   'Full inventory + user administration'),
    ('student', 'Scan-in only; read-only inventory access');

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    -- role is FK to roles.name so new roles can be added without a
    -- schema migration (INSERT INTO roles). No CHECK constraint here
    -- deliberately; the FK enforces validity.
    role          TEXT    NOT NULL REFERENCES roles(name),
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

CREATE TABLE IF NOT EXISTS user_inventory_views (
    user_id INTEGER PRIMARY KEY,
    columns_json TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    theme TEXT NOT NULL DEFAULT 'fall' CHECK(theme IN ('fall', 'spring')),
    updated_at TEXT DEFAULT (datetime('now'))
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
    overstock_threshold INTEGER DEFAULT 0,
    storage_location TEXT    DEFAULT '',
    shelf_life_days  INTEGER DEFAULT 0,
    expiration_date  TEXT    DEFAULT '',
    nutrition_data   TEXT    DEFAULT '{}',
    weight_per_unit  REAL    DEFAULT 0.0,
    unit_weight_milli_lb INTEGER CHECK(unit_weight_milli_lb >= 0),
    notes            TEXT    DEFAULT '',
    current_pounds   REAL    DEFAULT 0.0,
    donated_pounds   REAL    DEFAULT 0.0,
    discarded_pounds REAL    DEFAULT 0.0,
    calculated_remaining REAL DEFAULT 0.0,
    created_at       TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at       TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS pantry_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    system INTEGER NOT NULL DEFAULT 0 CHECK(system IN (0, 1))
);

CREATE TABLE IF NOT EXISTS pantry_shelves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL REFERENCES pantry_sections(id),
    name TEXT NOT NULL COLLATE NOCASE,
    is_overflow INTEGER NOT NULL DEFAULT 0 CHECK(is_overflow IN (0, 1)),
    UNIQUE(section_id, name)
);

CREATE TABLE IF NOT EXISTS item_shelf_stock (
    item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    shelf_id INTEGER NOT NULL REFERENCES pantry_shelves(id),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    PRIMARY KEY(item_id, shelf_id)
);

CREATE INDEX IF NOT EXISTS idx_shelf_stock_shelf ON item_shelf_stock(shelf_id);

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
    birth_date              TEXT,
    expected_graduation_semester TEXT DEFAULT '',
    household_size          INTEGER DEFAULT 1,
    allergies               TEXT    DEFAULT '',
    religious_restrictions  TEXT    DEFAULT '',
    notes                   TEXT    DEFAULT '',
    waiver_signed           INTEGER DEFAULT 0,
    locker_waiver_signed    INTEGER DEFAULT 0,
    is_active               INTEGER DEFAULT 1,
    deactivated_at          TEXT,
    created_at              TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at              TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_pantry_client_student_id ON pantry_clients(student_id);

CREATE TABLE IF NOT EXISTS client_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES pantry_clients(id),
    term TEXT NOT NULL,
    verified_at TEXT NOT NULL DEFAULT (datetime('now')),
    verified_until TEXT NOT NULL,
    verified_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('verified', 'revoked'))
);

CREATE INDEX IF NOT EXISTS idx_client_verifications_client ON client_verifications(client_id, id);

CREATE TABLE IF NOT EXISTS pantry_visits (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      INTEGER NOT NULL,
    visit_date     TEXT    DEFAULT (datetime('now', 'localtime')),
    pounds_received REAL   DEFAULT 0,
    items_json     TEXT    DEFAULT '[]',
    known_weight_milli_lb INTEGER,
    pending_weight_lines INTEGER NOT NULL DEFAULT 0,
    weight_complete INTEGER NOT NULL DEFAULT 0,
    is_void INTEGER NOT NULL DEFAULT 0,
    verified_term TEXT,
    fulfillment_type TEXT NOT NULL DEFAULT 'unknown'
        CHECK(fulfillment_type IN ('unknown', 'in_person', 'locker')),
    cart_id TEXT UNIQUE REFERENCES pantry_carts(id),
    notes          TEXT    DEFAULT '',
    recorded_by    TEXT    DEFAULT '',
    FOREIGN KEY (client_id) REFERENCES pantry_clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retired_service_months (
    month_utc TEXT PRIMARY KEY,
    visits INTEGER NOT NULL DEFAULT 0,
    known_weight_milli_lb INTEGER NOT NULL DEFAULT 0,
    pending_visits INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pantry_carts (
    id TEXT PRIMARY KEY,
    owner_id INTEGER NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('IN', 'OUT')),
    client_id INTEGER REFERENCES pantry_clients(id),
    mode TEXT NOT NULL DEFAULT 'REVIEW' CHECK(mode IN ('REVIEW', 'IMMEDIATE')),
    fulfillment_type TEXT NOT NULL DEFAULT 'in_person'
        CHECK(fulfillment_type IN ('in_person', 'locker')),
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'COMPLETED', 'CANCELLED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_active_pantry_cart
    ON pantry_carts(owner_id, direction) WHERE status = 'DRAFT';

CREATE TABLE IF NOT EXISTS pantry_cart_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id TEXT NOT NULL REFERENCES pantry_carts(id),
    item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    shelf_id INTEGER NOT NULL REFERENCES pantry_shelves(id),
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 1000000),
    weight_override_milli_lb INTEGER CHECK(weight_override_milli_lb > 0),
    override_reason TEXT DEFAULT '',
    UNIQUE(cart_id, item_id, shelf_id)
);

CREATE TABLE IF NOT EXISTS inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id TEXT REFERENCES pantry_carts(id),
    item_id INTEGER REFERENCES inventory_items(id),
    item_name TEXT NOT NULL,
    shelf_id INTEGER NOT NULL REFERENCES pantry_shelves(id),
    client_id INTEGER REFERENCES pantry_clients(id),
    visit_id INTEGER REFERENCES pantry_visits(id),
    direction TEXT NOT NULL CHECK(direction IN ('IN', 'OUT', 'OPENING', 'ADJUST', 'TRANSFER')),
    quantity_delta INTEGER NOT NULL,
    weight_milli_lb INTEGER,
    weight_override_reason TEXT DEFAULT '',
    scan_request_id TEXT,
    reverses_movement_id INTEGER REFERENCES inventory_movements(id),
    movement_reason TEXT DEFAULT '',
    recorded_by TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_inventory_movements_time ON inventory_movements(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_cart ON inventory_movements(cart_id);

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

CREATE TABLE IF NOT EXISTS weight_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id             INTEGER NOT NULL,
    month_year          TEXT    NOT NULL,
    current_pounds      REAL    DEFAULT 0.0,
    donated_pounds      REAL    DEFAULT 0.0,
    discarded_pounds    REAL    DEFAULT 0.0,
    calculated_remaining REAL   DEFAULT 0.0,
    recorded_date       TEXT    DEFAULT (datetime('now', 'localtime')),
    recorded_by         TEXT    DEFAULT '',
    notes               TEXT    DEFAULT '',
    FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
    UNIQUE(item_id, month_year)
);

CREATE TABLE IF NOT EXISTS monthly_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    month_year      TEXT    NOT NULL UNIQUE,
    report_type     TEXT    DEFAULT 'weights',
    generated_date  TEXT    DEFAULT (datetime('now', 'localtime')),
    generated_by    TEXT    DEFAULT '',
    report_data     TEXT    DEFAULT '{}',
    export_format   TEXT    DEFAULT 'csv'
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
        was_new = not os.path.exists(self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if was_new:
            # Lock the DB file down to owner-only as soon as sqlite creates
            # it, so password hashes and archived data aren't world-readable
            # on shared systems. Best-effort — no-op on filesystems without
            # POSIX permissions (e.g. FAT32 removable media).
            try:
                os.chmod(self.db_path, 0o600)
            except OSError:
                pass
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
            "ALTER TABLE inventory_items ADD COLUMN overstock_threshold INTEGER DEFAULT 0",
            "ALTER TABLE inventory_items ADD COLUMN weight_per_unit REAL DEFAULT 0.0",
            "ALTER TABLE inventory_items ADD COLUMN unit_weight_milli_lb INTEGER CHECK(unit_weight_milli_lb >= 0)",
            "ALTER TABLE pantry_visits ADD COLUMN items_json TEXT DEFAULT '[]'",
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
        self._migrate_visit_columns(conn)
        self._migrate_immediate_cart_columns(conn)
        self._migrate_users_role_to_fk(conn)
        self._migrate_client_columns(conn)
        self._migrate_item_unit_weights(conn)
        self._migrate_shelf_stock(conn)
        self._migrate_session_weight(conn)
        self._migrate_donation_records(conn)
        conn.close()

    def _migrate_visit_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(pantry_visits)")}
        additions = {
            "known_weight_milli_lb": "INTEGER",
            "pending_weight_lines": "INTEGER NOT NULL DEFAULT 0",
            "weight_complete": "INTEGER NOT NULL DEFAULT 0",
            "is_void": "INTEGER NOT NULL DEFAULT 0",
            "verified_term": "TEXT",
            "fulfillment_type": "TEXT NOT NULL DEFAULT 'unknown' CHECK(fulfillment_type IN ('unknown', 'in_person', 'locker'))",
            "cart_id": "TEXT REFERENCES pantry_carts(id)",
        }
        try:
            for name, column_type in additions.items():
                if name not in columns:
                    conn.execute(f"ALTER TABLE pantry_visits ADD COLUMN {name} {column_type}")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_pantry_visit_cart ON pantry_visits(cart_id) "
                "WHERE cart_id IS NOT NULL"
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_immediate_cart_columns(self, conn: sqlite3.Connection) -> None:
        carts = {row["name"] for row in conn.execute("PRAGMA table_info(pantry_carts)")}
        movements = {row["name"] for row in conn.execute("PRAGMA table_info(inventory_movements)")}
        additions = {
            "scan_request_id": "TEXT",
            "reverses_movement_id": "INTEGER REFERENCES inventory_movements(id)",
            "movement_reason": "TEXT DEFAULT ''",
        }
        try:
            if "mode" not in carts:
                conn.execute(
                    "ALTER TABLE pantry_carts ADD COLUMN mode TEXT NOT NULL DEFAULT 'REVIEW' "
                    "CHECK(mode IN ('REVIEW', 'IMMEDIATE'))"
                )
            if "fulfillment_type" not in carts:
                conn.execute(
                    "ALTER TABLE pantry_carts ADD COLUMN fulfillment_type TEXT NOT NULL "
                    "DEFAULT 'in_person' CHECK(fulfillment_type IN ('in_person', 'locker'))"
                )
            for name, column_type in additions.items():
                if name not in movements:
                    conn.execute(f"ALTER TABLE inventory_movements ADD COLUMN {name} {column_type}")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_movement_scan_request "
                "ON inventory_movements(scan_request_id) WHERE scan_request_id IS NOT NULL"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_movement_reversal "
                "ON inventory_movements(reverses_movement_id) WHERE reverses_movement_id IS NOT NULL"
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_client_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(pantry_clients)")}
        additions = {
            "birth_date": "TEXT",
            "expected_graduation_semester": "TEXT DEFAULT ''",
            "household_size": "INTEGER DEFAULT 1",
            "allergies": "TEXT DEFAULT ''",
            "religious_restrictions": "TEXT DEFAULT ''",
            "deactivated_at": "TEXT",
        }
        if all(name in columns for name in additions):
            return
        try:
            conn.execute("BEGIN IMMEDIATE")
            for name, column_type in additions.items():
                if name not in columns:
                    conn.execute(f"ALTER TABLE pantry_clients ADD COLUMN {name} {column_type}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_item_unit_weights(self, conn: sqlite3.Connection) -> None:
        if conn.execute(
            "SELECT 1 FROM app_settings WHERE key = 'unit_weight_migrated'"
        ).fetchone():
            return
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE inventory_items SET unit_weight_milli_lb = CAST(ROUND(weight_per_unit * 1000) AS INTEGER) "
                "WHERE unit_weight_milli_lb IS NULL AND weight_per_unit >= 0.0005"
            )
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES ('unit_weight_migrated', '1')"
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_shelf_stock(self, conn: sqlite3.Connection) -> None:
        if conn.execute(
            "SELECT 1 FROM app_settings WHERE key = 'shelf_stock_migrated'"
        ).fetchone():
            return
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT OR IGNORE INTO pantry_sections (name, system) VALUES ('Unassigned', 1)")
            section_id = conn.execute(
                "SELECT id FROM pantry_sections WHERE name = 'Unassigned'"
            ).fetchone()[0]
            conn.execute(
                "INSERT OR IGNORE INTO pantry_shelves (section_id, name) VALUES (?, 'Unassigned')",
                (section_id,),
            )
            shelf_id = conn.execute(
                "SELECT id FROM pantry_shelves WHERE section_id = ? AND name = 'Unassigned'",
                (section_id,),
            ).fetchone()[0]
            migrated = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'shelf_stock_migrated'"
            ).fetchone()
            if not migrated:
                for item in conn.execute(
                    "SELECT i.id, i.item_name, i.unit_weight_milli_lb, i.current_quantity, "
                    "COALESCE(SUM(s.quantity), 0) AS allocated "
                    "FROM inventory_items i LEFT JOIN item_shelf_stock s ON s.item_id = i.id "
                    "GROUP BY i.id"
                ).fetchall():
                    remainder = item["current_quantity"] - item["allocated"]
                    if remainder < 0:
                        raise ValueError("Existing shelf stock exceeds catalog quantity")
                    if remainder:
                        conn.execute(
                            "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?) "
                            "ON CONFLICT(item_id, shelf_id) DO UPDATE SET quantity = quantity + excluded.quantity",
                            (item["id"], shelf_id, remainder),
                        )
                        conn.execute(
                            "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
                            "quantity_delta, weight_milli_lb, recorded_by) "
                            "VALUES (?, ?, ?, 'OPENING', ?, ?, 'migration')",
                            (item["id"], item["item_name"], shelf_id, remainder,
                             remainder * item["unit_weight_milli_lb"]
                             if item["unit_weight_milli_lb"] is not None else None),
                        )
                conn.execute(
                    "INSERT INTO app_settings (key, value) VALUES ('shelf_stock_migrated', '1')"
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_session_weight(self, conn: sqlite3.Connection) -> None:
        carts_cols = {row["name"] for row in conn.execute("PRAGMA table_info(pantry_carts)")}
        try:
            if "session_weight_milli_lb" not in carts_cols:
                conn.execute(
                    "ALTER TABLE pantry_carts ADD COLUMN "
                    "session_weight_milli_lb INTEGER CHECK(session_weight_milli_lb >= 0)"
                )
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_donation_records(self, conn: sqlite3.Connection) -> None:
        tables = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "donation_records" in tables:
            return
        try:
            conn.execute("""
                CREATE TABLE donation_records (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    weight_milli_lb  INTEGER NOT NULL CHECK(weight_milli_lb > 0),
                    donation_date    TEXT    NOT NULL,
                    source           TEXT    DEFAULT '',
                    notes            TEXT    DEFAULT '',
                    cart_id          TEXT    DEFAULT NULL,
                    recorded_by      TEXT    NOT NULL,
                    created_at       TEXT    DEFAULT (datetime('now', 'localtime')),
                    updated_at       TEXT    DEFAULT (datetime('now', 'localtime'))
                )
            """)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _migrate_users_role_to_fk(self, conn: sqlite3.Connection) -> None:
        """Replace ``users.role`` CHECK('admin','staff') with a FK to
        ``roles.name``. Adding a new role now = INSERT into roles;
        no more schema migration.

        Idempotent: detects the old CHECK constraint in
        ``sqlite_master`` and only runs when found. If migration
        fails partway through, the transaction is rolled back and
        the original ``users`` table is left in place.
        """
        try:
            row = conn.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='users'"
            ).fetchone()
            if not row or not row[0]:
                return
            existing_sql = row[0].upper()
            if "CHECK" not in existing_sql or "STAFF" not in existing_sql:
                # Already migrated (or table was created fresh from
                # the new _SCHEMA above).
                return

            conn.executescript("""
                BEGIN;

                CREATE TABLE users_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    username      TEXT    UNIQUE NOT NULL,
                    password_hash TEXT    NOT NULL,
                    salt          TEXT    NOT NULL,
                    role          TEXT    NOT NULL REFERENCES roles(name),
                    full_name           TEXT    DEFAULT '',
                    created_at          TEXT    DEFAULT (datetime('now', 'localtime')),
                    is_active           INTEGER DEFAULT 1,
                    has_completed_tour  INTEGER DEFAULT 0,
                    last_login          TEXT    DEFAULT '',
                    created_by          TEXT    DEFAULT ''
                );

                -- Green-field data is expected, but be defensive: any
                -- legacy 'staff' user becomes 'student' rather than
                -- silently gaining administrator access.
                INSERT INTO users_new
                    (id, username, password_hash, salt, role,
                     full_name, created_at, is_active,
                     has_completed_tour, last_login, created_by)
                SELECT id, username, password_hash, salt,
                       CASE role WHEN 'staff' THEN 'student' ELSE role END,
                       COALESCE(full_name, ''),
                       created_at,
                       is_active,
                       COALESCE(has_completed_tour, 0),
                       COALESCE(last_login, ''),
                       COALESCE(created_by, '')
                FROM users;

                DROP TABLE users;
                ALTER TABLE users_new RENAME TO users;

                COMMIT;
            """)
        except Exception:  # pragma: no cover - safety net
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise

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
                    items_json     TEXT    DEFAULT '[]',
                    notes          TEXT    DEFAULT '',
                    recorded_by    TEXT    DEFAULT '',
                    FOREIGN KEY (client_id) REFERENCES pantry_clients(id) ON DELETE CASCADE
                );
                INSERT INTO pantry_visits_new
                    (id, client_id, visit_date, pounds_received, items_json, notes, recorded_by)
                SELECT id, client_id, visit_date, pounds_received,
                       COALESCE(items_json, '[]'), notes, recorded_by
                FROM pantry_visits;
                DROP TABLE pantry_visits;
                ALTER TABLE pantry_visits_new RENAME TO pantry_visits;
                COMMIT;
            """)
        except Exception:
            # If migration fails, roll back and keep the old table;
            # never silently continue with an incomplete schema.
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------

    def create_user(self, username: str, password_hash: str, salt: str, role: str):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE LIMIT 1", (username,)
            ).fetchone():
                conn.rollback()
                return False, "Username already exists."
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                (username, password_hash, salt, role),
            )
            conn.commit()
            return True, "User created successfully."
        except sqlite3.IntegrityError:
            conn.rollback()
            return False, "Username already exists."
        finally:
            conn.close()

    def get_user(self, username: str):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE AND is_active = 1 LIMIT 2",
            (username,),
        ).fetchall()
        conn.close()
        return dict(rows[0]) if len(rows) == 1 else None

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
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE LIMIT 1", (username,)
            ).fetchone():
                conn.rollback()
                return False, "Username already exists."
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role, full_name, created_by) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (username, password_hash, salt, role, full_name, created_by),
            )
            conn.commit()
            return True, "User created successfully."
        except sqlite3.IntegrityError:
            conn.rollback()
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

    def get_user_by_id(self, user_id: int):
        conn = self._connect()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def reset_student_password(self, actor_id: int, user_id: int,
                               password_hash: str, salt: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            actor = conn.execute(
                "SELECT username, role, is_active FROM users WHERE id = ?", (actor_id,)
            ).fetchone()
            target = conn.execute(
                "SELECT role FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not actor or actor["role"] != "admin" or not actor["is_active"] or not target:
                raise ValueError("Only an active administrator may reset a Student account.")
            if target["role"] != "student":
                raise ValueError("Only Student account passwords can be reset here.")
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (password_hash, salt, user_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) "
                "VALUES (?, 'STUDENT_PASSWORD_RESET', ?)",
                (actor["username"], f"user={user_id}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_user_active(self, user_id: int, active: bool) -> None:
        conn = self._connect()
        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(active), user_id))
        conn.commit()
        conn.close()

    def manage_user_active(self, actor_id: int, target_id: int, active: bool) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            actor = conn.execute(
                "SELECT username, role, is_active FROM users WHERE id = ?", (actor_id,)
            ).fetchone()
            target = conn.execute(
                "SELECT role FROM users WHERE id = ?", (target_id,)
            ).fetchone()
            if not actor or not actor["is_active"] or actor["role"] != "admin" or not target:
                raise ValueError("Only an active administrator may change team access.")
            if not active and actor_id == target_id:
                raise ValueError("You cannot deactivate your own account.")
            if not active and target["role"] == "admin":
                count = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
                ).fetchone()[0]
                if count <= 1:
                    raise ValueError("At least one active administrator is required.")
            conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(active), target_id))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'USER_STATUS', ?)",
                (actor["username"], f"user={target_id} active={int(active)}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def import_catalog_rows(self, rows: list[dict], username: str) -> int:
        if not rows or len(rows) > 150:
            raise ValueError("Select 1–150 valid product rows.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for row in rows:
                name = (row.get("item_name") or "").strip()
                code_in = (row.get("barcode") or "").strip()
                code_out = (row.get("barcode_out") or "").strip()
                section = (row.get("section_name") or "").strip()
                shelf = (row.get("shelf_name") or "").strip()
                category = (row.get("category") or "").strip()
                if (row.get("problem") or not name or len(name) > 200 or
                        not re.fullmatch(r"[A-Za-z0-9-]{1,64}", code_in) or
                        not re.fullmatch(r"[A-Za-z0-9-]{1,64}", code_out) or code_in == code_out or
                        not re.fullmatch(r"Section [1-9][0-9]{0,2}", section) or
                        not re.fullmatch(r"Shelf [1-9][0-9]{0,2}", shelf) or len(category) > 120):
                    raise ValueError("An import row is invalid. Preview and select valid rows again.")
                if conn.execute(
                    "SELECT 1 FROM inventory_items WHERE barcode IN (?, ?) "
                    "OR barcode_out IN (?, ?) LIMIT 1",
                    (code_in, code_out, code_in, code_out),
                ).fetchone():
                    raise ValueError("A barcode already exists in the pantry. Nothing was imported.")
                conn.execute("INSERT OR IGNORE INTO pantry_sections (name) VALUES (?)", (section,))
                section_id = conn.execute(
                    "SELECT id FROM pantry_sections WHERE name = ? COLLATE NOCASE", (section,)
                ).fetchone()[0]
                conn.execute(
                    "INSERT OR IGNORE INTO pantry_shelves (section_id, name) VALUES (?, ?)",
                    (section_id, shelf),
                )
                shelf_id = conn.execute(
                    "SELECT id FROM pantry_shelves WHERE section_id = ? AND name = ? COLLATE NOCASE",
                    (section_id, shelf),
                ).fetchone()[0]
                created = conn.execute(
                    "INSERT INTO inventory_items (barcode, barcode_out, item_name, category, "
                    "current_quantity, minimum_stock, storage_location) VALUES (?, ?, ?, ?, 0, 0, ?)",
                    (code_in, code_out, name, category, f"{section}, {shelf}"),
                )
                conn.execute(
                    "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, 0)",
                    (created.lastrowid, shelf_id),
                )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CATALOG_IMPORT', ?)",
                (username, f"items={len(rows)}"),
            )
            conn.commit()
            return len(rows)
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError("The catalog conflicts with existing items. Nothing was imported.") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_item_on_shelf(self, barcode: str, item_name: str, category: str,
                             quantity: int, minimum_stock: int, shelf_id: int,
                             username: str, unit_weight_milli_lb: int | None = None,
                             barcode_out: str = "", brand: str = "", notes: str = "") -> int:
        barcode = barcode.strip()
        barcode_out = barcode_out.strip()
        if not barcode or not barcode_out:
            label_id = uuid4().hex[:16].upper()
            barcode = barcode or f"HHI-{label_id}"
            barcode_out = barcode_out or f"HHO-{label_id}"
        item_name = item_name.strip()
        if not item_name or len(item_name) > 200:
            raise ValueError("Item name is required.")
        if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", barcode) or not re.fullmatch(r"[A-Za-z0-9-]{1,64}", barcode_out):
            raise ValueError("Pantry barcodes must be 1–64 letters, numbers or hyphens.")
        if (not isinstance(quantity, int) or not 0 <= quantity <= 1_000_000 or
                not isinstance(minimum_stock, int) or not 0 <= minimum_stock <= 1_000_000):
            raise ValueError("Quantities must be non-negative whole numbers up to one million.")
        if len(category) > 120 or len(brand) > 120 or len(notes) > 2000:
            raise ValueError("Item details exceed the allowed length.")
        if unit_weight_milli_lb is not None and (
                not isinstance(unit_weight_milli_lb, int) or not 0 < unit_weight_milli_lb <= 10_000_000):
            raise ValueError("Unit weight must be positive or left unknown.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            shelf = conn.execute(
                "SELECT shelf.name AS shelf_name, section.name AS section_name "
                "FROM pantry_shelves shelf JOIN pantry_sections section ON section.id = shelf.section_id "
                "WHERE shelf.id = ? AND section.system = 0", (shelf_id,),
            ).fetchone()
            if not shelf:
                raise ValueError("Choose a pantry shelf first.")
            if conn.execute(
                "SELECT 1 FROM inventory_items WHERE barcode IN (?, ?) "
                "OR barcode_out IN (?, ?) LIMIT 1",
                (barcode, barcode_out or barcode, barcode, barcode_out or barcode),
            ).fetchone():
                raise ValueError("A barcode is already assigned to another item.")
            if barcode_out and barcode_out == barcode:
                raise ValueError("Scan-in and scan-out barcodes must differ.")
            cursor = conn.execute(
                "INSERT INTO inventory_items (barcode, barcode_out, item_name, brand, category, "
                "current_quantity, minimum_stock, storage_location, weight_per_unit, "
                "unit_weight_milli_lb, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (barcode, barcode_out or None, item_name, brand, category, quantity,
                 minimum_stock, f"{shelf['section_name']}, {shelf['shelf_name']}",
                 (unit_weight_milli_lb or 0) / 1000, unit_weight_milli_lb, notes),
            )
            conn.execute(
                "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?)",
                (cursor.lastrowid, shelf_id, quantity),
            )
            if quantity:
                conn.execute(
                    "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
                    "quantity_delta, weight_milli_lb, recorded_by) "
                    "VALUES (?, ?, ?, 'OPENING', ?, ?, ?)",
                    (cursor.lastrowid, item_name, shelf_id, quantity,
                     quantity * unit_weight_milli_lb if unit_weight_milli_lb is not None else None,
                     username),
                )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'ITEM_OPENING', ?)",
                (username, f"item={cursor.lastrowid} shelf={shelf_id} units={quantity}"),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError("An item with this barcode already exists.") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_item_profile(self, item_id: int, item_name: str, category: str,
                            minimum_stock: int, notes: str, barcode_out: str,
                            brand: str, unit_weight_milli_lb: int | None,
                            username: str) -> None:
        if (not item_name.strip() or len(item_name) > 200 or
                not isinstance(minimum_stock, int) or not 0 <= minimum_stock <= 1_000_000):
            raise ValueError("Item name and a valid minimum are required.")
        if len(category) > 120 or len(brand) > 120 or len(notes) > 2000 or len(barcode_out) > 128:
            raise ValueError("Item details exceed the allowed length.")
        if unit_weight_milli_lb is not None and (
                not isinstance(unit_weight_milli_lb, int) or not 0 < unit_weight_milli_lb <= 10_000_000):
            raise ValueError("Unit weight must be positive or left unknown.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT id, barcode, barcode_out FROM inventory_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not item:
                raise ValueError("Item not found.")
            if item["barcode_out"] and barcode_out and barcode_out != item["barcode_out"]:
                raise ValueError("An existing scan-out label cannot be changed after printing.")
            barcode_out = item["barcode_out"] or barcode_out.strip() or f"HHO-{uuid4().hex[:16].upper()}"
            if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", barcode_out):
                raise ValueError("Pantry scan-out barcode must be letters, numbers or hyphens.")
            if barcode_out == item["barcode"]:
                raise ValueError("Scan-in and scan-out barcodes must differ.")
            if barcode_out and conn.execute(
                "SELECT 1 FROM inventory_items WHERE id != ? "
                "AND (barcode = ? OR barcode_out = ?)", (item_id, barcode_out, barcode_out)
            ).fetchone():
                raise ValueError("That scan-out barcode already belongs to another item.")
            conn.execute(
                "UPDATE inventory_items SET item_name = ?, category = ?, minimum_stock = ?, "
                "notes = ?, barcode_out = ?, brand = ?, unit_weight_milli_lb = ?, weight_per_unit = ?, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?",
                (item_name.strip(), category, minimum_stock, notes, barcode_out or None,
                 brand, unit_weight_milli_lb, (unit_weight_milli_lb or 0) / 1000, item_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'ITEM_EDIT', ?)",
                (username, f"item={item_id}"),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError("Barcode is already assigned.") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_pantry_section(self, name: str) -> int:
        name = name.strip()
        if not name or len(name) > 80 or name.casefold() == "unassigned":
            raise ValueError("Enter a unique section name (up to 80 characters).")
        conn = self._connect()
        try:
            cursor = conn.execute("INSERT INTO pantry_sections (name) VALUES (?)", (name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError("This section already exists.") from exc
        finally:
            conn.close()

    def create_pantry_shelf(self, section_id: int, name: str, is_overflow: bool = False) -> int:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("Enter a shelf name (up to 80 characters).")
        conn = self._connect()
        try:
            section = conn.execute(
                "SELECT system FROM pantry_sections WHERE id = ?", (section_id,)
            ).fetchone()
            if not section or section["system"]:
                raise ValueError("Select a valid section.")
            cursor = conn.execute(
                "INSERT INTO pantry_shelves (section_id, name, is_overflow) VALUES (?, ?, ?)",
                (section_id, name, int(is_overflow)),
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ValueError("This shelf already exists in the section.") from exc
        finally:
            conn.close()

    def rename_pantry_section(self, section_id: int, name: str, username: str) -> None:
        name = name.strip()
        if not name or len(name) > 80 or name.casefold() == "unassigned":
            raise ValueError("Enter a section name (up to 80 characters).")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT name, system FROM pantry_sections WHERE id = ?", (section_id,)
            ).fetchone()
            if not previous or previous["system"]:
                raise ValueError("The system section cannot be renamed.")
            conn.execute("UPDATE pantry_sections SET name = ? WHERE id = ?", (name, section_id))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'SECTION_RENAME', ?)",
                (username, f"section={section_id} from={previous['name']} to={name}"),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError("This section name is already in use.") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_pantry_shelf(self, shelf_id: int, name: str, is_overflow: bool,
                            username: str) -> None:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("Enter a shelf name (up to 80 characters).")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT shelf.name, shelf.is_overflow, section.system FROM pantry_shelves shelf "
                "JOIN pantry_sections section ON section.id = shelf.section_id "
                "WHERE shelf.id = ?", (shelf_id,),
            ).fetchone()
            if not previous or previous["system"]:
                raise ValueError("The system shelf cannot be changed.")
            conn.execute(
                "UPDATE pantry_shelves SET name = ?, is_overflow = ? WHERE id = ?",
                (name, int(is_overflow), shelf_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'SHELF_EDIT', ?)",
                (username, f"shelf={shelf_id} from={previous['name']} to={name} "
                 f"overflow={previous['is_overflow']}->{int(is_overflow)}"),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError("This shelf name is already used in the section.") from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _purge_shelf_references(self, conn, shelf_id: int) -> int:
        """Remove all FK references to a shelf and return units of stock removed."""
        removed_stock = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS total FROM item_shelf_stock "
            "WHERE shelf_id = ?", (shelf_id,),
        ).fetchone()["total"]
        conn.execute("DELETE FROM inventory_movements WHERE shelf_id = ?", (shelf_id,))
        conn.execute("DELETE FROM pantry_cart_lines WHERE shelf_id = ?", (shelf_id,))
        conn.execute("DELETE FROM item_shelf_stock WHERE shelf_id = ?", (shelf_id,))
        return removed_stock

    def delete_pantry_shelf(self, shelf_id: int, username: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            shelf = conn.execute(
                "SELECT shelf.id, shelf.name, shelf.section_id, section.system "
                "FROM pantry_shelves shelf "
                "JOIN pantry_sections section ON section.id = shelf.section_id "
                "WHERE shelf.id = ?", (shelf_id,),
            ).fetchone()
            if not shelf:
                raise ValueError("Shelf not found.")
            if shelf["system"]:
                raise ValueError("The system shelf cannot be deleted.")
            removed_stock = self._purge_shelf_references(conn, shelf_id)
            conn.execute("DELETE FROM pantry_shelves WHERE id = ?", (shelf_id,))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'SHELF_DELETE', ?)",
                (username, f"shelf={shelf_id} name={shelf['name']} "
                 f"section={shelf['section_id']} removed_stock={removed_stock}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_pantry_section(self, section_id: int, username: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            section = conn.execute(
                "SELECT id, name, system FROM pantry_sections WHERE id = ?",
                (section_id,),
            ).fetchone()
            if not section:
                raise ValueError("Section not found.")
            if section["system"]:
                raise ValueError("The system section cannot be deleted.")
            shelf_ids = [row["id"] for row in conn.execute(
                "SELECT id FROM pantry_shelves WHERE section_id = ?",
                (section_id,),
            ).fetchall()]
            removed_stock = 0
            for sid in shelf_ids:
                removed_stock += self._purge_shelf_references(conn, sid)
            conn.execute("DELETE FROM pantry_shelves WHERE section_id = ?", (section_id,))
            conn.execute("DELETE FROM pantry_sections WHERE id = ?", (section_id,))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'SECTION_DELETE', ?)",
                (username, f"section={section_id} name={section['name']} "
                 f"shelves={len(shelf_ids)} removed_stock={removed_stock}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_pantry_layout(self, include_items: bool = False):
        conn = self._connect()
        sections = conn.execute(
            "SELECT id, name, system FROM pantry_sections "
            "ORDER BY system, "
            "CAST(CASE WHEN name GLOB '*[0-9]*' "
            "THEN SUBSTR(name, LENGTH(RTRIM(name, '0123456789')) + 1) "
            "ELSE '999999' END AS INTEGER), "
            "name COLLATE NOCASE"
        ).fetchall()
        shelves = conn.execute(
            "SELECT s.id, s.section_id, s.name, s.is_overflow, "
            "COALESCE(SUM(stock.quantity), 0) AS units "
            "FROM pantry_shelves s LEFT JOIN item_shelf_stock stock ON stock.shelf_id = s.id "
            "GROUP BY s.id ORDER BY s.is_overflow, "
            "CAST(CASE WHEN s.name GLOB '*[0-9]*' "
            "THEN SUBSTR(s.name, LENGTH(RTRIM(s.name, '0123456789')) + 1) "
            "ELSE '999999' END AS INTEGER), "
            "s.name COLLATE NOCASE"
        ).fetchall()
        contents = {}
        if include_items:
            rows = conn.execute(
                "SELECT stock.shelf_id, stock.item_id, stock.quantity, item.item_name "
                "FROM item_shelf_stock stock JOIN inventory_items item ON item.id = stock.item_id "
                "ORDER BY item.item_name COLLATE NOCASE, item.id"
            ).fetchall()
            for row in rows:
                contents.setdefault(row["shelf_id"], []).append(dict(row))
        conn.close()
        return [dict(section, shelves=[dict(shelf, items=contents.get(shelf["id"], []))
                                      for shelf in shelves if shelf["section_id"] == section["id"]])
                for section in sections]

    def get_item_locations(self, item_ids: list[int]) -> dict[int, str]:
        if not item_ids:
            return {}
        conn = self._connect()
        placeholders = ", ".join("?" for _ in item_ids)
        rows = conn.execute(
            "SELECT stock.item_id, stock.quantity, section.name AS section_name, "
            "shelf.name AS shelf_name FROM item_shelf_stock stock "
            "JOIN pantry_shelves shelf ON shelf.id = stock.shelf_id "
            "JOIN pantry_sections section ON section.id = shelf.section_id "
            f"WHERE stock.item_id IN ({placeholders}) "
            "ORDER BY section.system, section.name, shelf.name", item_ids,
        ).fetchall()
        conn.close()
        locations = {}
        for row in rows:
            label = f"{row['section_name']} / {row['shelf_name']}"
            locations.setdefault(row["item_id"], []).append((row["quantity"], label))
        return {item_id: ", ".join(label for qty, label in entries if qty > 0) or
                entries[0][1] for item_id, entries in locations.items()}

    def get_item_shelf_stock(self, item_id: int):
        conn = self._connect()
        rows = conn.execute(
            "SELECT stock.shelf_id, stock.quantity, shelf.name AS shelf_name, "
            "section.name AS section_name, shelf.is_overflow "
            "FROM item_shelf_stock stock JOIN pantry_shelves shelf ON shelf.id = stock.shelf_id "
            "JOIN pantry_sections section ON section.id = shelf.section_id "
            "WHERE stock.item_id = ? ORDER BY section.system, section.name, shelf.name",
            (item_id,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def adjust_shelf_stock(self, item_id: int, shelf_id: int, delta: int,
                           username: str, reason: str, expected_quantity: int | None = None) -> int:
        if not isinstance(delta, int) or not delta or not reason.strip():
            raise ValueError("An adjustment and reason are required.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT item_name, unit_weight_milli_lb, current_quantity "
                "FROM inventory_items WHERE id = ?", (item_id,)
            ).fetchone()
            shelf = conn.execute("SELECT id FROM pantry_shelves WHERE id = ?", (shelf_id,)).fetchone()
            if not item or not shelf:
                raise ValueError("Item or shelf not found.")
            allocated = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM item_shelf_stock WHERE item_id = ?",
                (item_id,),
            ).fetchone()[0]
            if allocated != item["current_quantity"]:
                raise ValueError("Item has unmapped stock. Reconcile its location first.")
            row = conn.execute(
                "SELECT quantity FROM item_shelf_stock WHERE item_id = ? AND shelf_id = ?",
                (item_id, shelf_id),
            ).fetchone()
            previous = row[0] if row else 0
            if expected_quantity is not None and previous != expected_quantity:
                raise ValueError("This shelf changed since you opened the page. Refresh and retry.")
            quantity = previous + delta
            if quantity < 0:
                raise ValueError("The shelf does not have enough stock.")
            if quantity > 1_000_000 or item["current_quantity"] + delta > 1_000_000:
                raise ValueError("The stock count exceeds the allowed range.")
            conn.execute(
                "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(item_id, shelf_id) DO UPDATE SET quantity = excluded.quantity",
                (item_id, shelf_id, quantity),
            )
            conn.execute(
                "UPDATE inventory_items SET current_quantity = current_quantity + ?, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?", (delta, item_id)
            )
            conn.execute(
                "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
                "quantity_delta, weight_milli_lb, recorded_by) VALUES (?, ?, ?, 'ADJUST', ?, ?, ?)",
                (item_id, item["item_name"], shelf_id, delta,
                 delta * item["unit_weight_milli_lb"]
                 if item["unit_weight_milli_lb"] is not None else None, username),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'STOCK_ADJUST', ?)",
                (username, f"item={item_id} shelf={shelf_id} delta={delta} reason={reason.strip()[:200]}"),
            )
            conn.commit()
            return quantity
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def transfer_shelf_stock(self, item_id: int, source_id: int, destination_id: int,
                             quantity: int, username: str) -> None:
        if not isinstance(quantity, int) or quantity <= 0 or source_id == destination_id:
            raise ValueError("Select two different shelves and a positive quantity.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT item_name, unit_weight_milli_lb, current_quantity FROM inventory_items WHERE id = ?",
                (item_id,),
            ).fetchone()
            source = conn.execute(
                "SELECT quantity FROM item_shelf_stock WHERE item_id = ? AND shelf_id = ?",
                (item_id, source_id),
            ).fetchone()
            target = conn.execute("SELECT id FROM pantry_shelves WHERE id = ?", (destination_id,)).fetchone()
            allocated = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM item_shelf_stock WHERE item_id = ?",
                (item_id,),
            ).fetchone()[0]
            if not item or not target or allocated != item["current_quantity"]:
                raise ValueError("Item or shelf stock needs reconciliation.")
            if not source or source["quantity"] < quantity:
                raise ValueError("The source shelf does not have enough stock.")
            conn.execute(
                "UPDATE item_shelf_stock SET quantity = quantity - ? WHERE item_id = ? AND shelf_id = ?",
                (quantity, item_id, source_id),
            )
            conn.execute(
                "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(item_id, shelf_id) DO UPDATE SET quantity = quantity + excluded.quantity",
                (item_id, destination_id, quantity),
            )
            weight = item["unit_weight_milli_lb"]
            moved_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            conn.executemany(
                "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
                "quantity_delta, weight_milli_lb, recorded_by, timestamp_utc) "
                "VALUES (?, ?, ?, 'TRANSFER', ?, ?, ?, ?)",
                [(item_id, item["item_name"], source_id, -quantity,
                  -quantity * weight if weight is not None else None, username, moved_at),
                 (item_id, item["item_name"], destination_id, quantity,
                  quantity * weight if weight is not None else None, username, moved_at)],
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'STOCK_TRANSFER', ?)",
                (username, f"item={item_id} from={source_id} to={destination_id} units={quantity}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
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
            cursor = conn.execute(
                """INSERT INTO inventory_items
                       (barcode, barcode_out, item_name, brand, category,
                        current_quantity, minimum_stock, storage_location,
                        shelf_life_days, expiration_date, nutrition_data, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (barcode, barcode_out or None, item_name, brand, category,
                 quantity, minimum_stock, storage_location,
                 shelf_life_days, expiration_date, nutrition_data, notes),
            )
            shelf = conn.execute(
                "SELECT shelf.id FROM pantry_shelves shelf JOIN pantry_sections section "
                "ON section.id = shelf.section_id WHERE section.system = 1"
            ).fetchone()
            conn.execute(
                "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?)",
                (cursor.lastrowid, shelf[0], quantity),
            )
            if quantity:
                conn.execute(
                    "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
                    "quantity_delta, recorded_by) VALUES (?, ?, ?, 'OPENING', ?, 'legacy')",
                    (cursor.lastrowid, item_name, shelf[0], quantity),
                )
            conn.commit()
            return True, "Item added successfully."
        except sqlite3.IntegrityError as e:
            if "barcode_out" in str(e):
                return False, "That Scan-Out barcode is already used by another item."
            return False, "That Scan-In barcode is already used by another item."
        finally:
            conn.close()

    def batch_upsert_inventory(self, rows: list[dict]) -> tuple[int, int, list[str]]:
        """Apply a batch of inventory rows atomically.

        Each row dict may contain: barcode, barcode_out, item_name,
        category, quantity, minimum_stock, notes, brand, storage_location,
        shelf_life_days, expiration_date, nutrition_data. `barcode` and
        `item_name` are required; other fields fall back to sensible
        defaults. Rows with an existing `barcode` are updated in place
        (preserving shelf_life_days and nutrition_data when the CSV
        doesn't carry them). Rows without one are inserted.

        Returns (added, updated, per_row_errors). If the whole batch
        raises, the transaction is rolled back and the caller sees the
        exception — nothing is persisted.
        """
        added = updated = 0
        errors: list[str] = []
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for i, row in enumerate(rows, start=1):
                try:
                    barcode = (row.get("barcode") or "").strip()
                    name    = (row.get("item_name") or "").strip()
                    if not barcode or not name:
                        errors.append(f"Row {i}: barcode and item_name are required")
                        continue

                    b_out    = (row.get("barcode_out") or "").strip() or None
                    category = row.get("category", "")
                    qty      = int(row.get("current_quantity", 0) or 0)
                    mstk     = int(row.get("minimum_stock", 0) or 0)
                    if not 0 <= qty <= 1_000_000 or not 0 <= mstk <= 1_000_000:
                        errors.append(f"Row {i}: quantities must be between zero and one million")
                        continue
                    notes    = row.get("notes", "") or ""
                    brand    = row.get("brand", "") or ""
                    loc      = row.get("storage_location", "") or ""
                    exp      = row.get("expiration_date", "") or ""
                    shelf    = int(row.get("shelf_life_days", 0) or 0)
                    nutr     = row.get("nutrition_data", "{}") or "{}"

                    existing = conn.execute(
                        "SELECT id, shelf_life_days, nutrition_data, current_quantity "
                        "FROM inventory_items WHERE barcode = ?",
                        (barcode,),
                    ).fetchone()

                    if existing:
                        eid = existing["id"]
                        # Preserve AI-populated fields the CSV omits.
                        keep_shelf = shelf if "shelf_life_days" in row else existing["shelf_life_days"]
                        keep_nutr  = nutr  if "nutrition_data"  in row else (existing["nutrition_data"] or "{}")
                        conn.execute(
                            """UPDATE inventory_items
                               SET item_name=?, category=?, minimum_stock=?, notes=?,
                                   barcode_out=?, brand=?, storage_location=?,
                                   shelf_life_days=?, expiration_date=?, nutrition_data=?,
                                   updated_at=datetime('now','localtime')
                               WHERE id=?""",
                            (name, category, mstk, notes, b_out, brand, loc,
                             keep_shelf, exp, keep_nutr, eid),
                        )
                        if qty > 0:
                            self._apply_legacy_stock_delta(
                                conn, eid, existing["current_quantity"], qty - existing["current_quantity"]
                            )
                            conn.execute(
                                "UPDATE inventory_items SET current_quantity=?, "
                                "updated_at=datetime('now','localtime') WHERE id=?",
                                (qty, eid),
                            )
                        updated += 1
                    else:
                        cursor = conn.execute(
                            """INSERT INTO inventory_items
                                (barcode, barcode_out, item_name, brand, category,
                                 current_quantity, minimum_stock, storage_location,
                                 shelf_life_days, expiration_date, nutrition_data, notes)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (barcode, b_out, name, brand, category,
                             qty, mstk, loc, shelf, exp, nutr, notes),
                        )
                        unassigned = conn.execute(
                            "SELECT shelf.id FROM pantry_shelves shelf JOIN pantry_sections section "
                            "ON section.id = shelf.section_id WHERE section.system = 1"
                        ).fetchone()[0]
                        conn.execute(
                            "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?)",
                            (cursor.lastrowid, unassigned, qty),
                        )
                        if qty:
                            conn.execute(
                                "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
                                "quantity_delta, recorded_by) VALUES (?, ?, ?, 'OPENING', ?, 'legacy')",
                                (cursor.lastrowid, name, unassigned, qty),
                            )
                        added += 1
                except sqlite3.IntegrityError as ex:
                    errors.append(f"Row {i}: {ex}")
                    # Continue with next row; the row itself failed but
                    # the transaction stays open.
            conn.commit()
            return added, updated, errors
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_item_by_barcode(self, barcode: str):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE barcode = ?", (barcode,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_item_by_id(self, item_id: int):
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM inventory_items WHERE id = ?", (item_id,)
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

    def get_user_theme(self, user_id: int) -> str:
        conn = self._connect()
        row = conn.execute(
            "SELECT preferences.theme FROM user_preferences preferences "
            "JOIN users account ON account.id = preferences.user_id "
            "WHERE preferences.user_id = ? AND account.is_active = 1",
            (user_id,),
        ).fetchone()
        conn.close()
        return row["theme"] if row and row["theme"] in {"fall", "spring"} else "fall"

    def save_user_theme(self, user_id: int, theme: str) -> None:
        if theme not in {"fall", "spring"}:
            raise ValueError("Choose the Fall or Spring theme.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            account = conn.execute(
                "SELECT is_active FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not account or not account["is_active"]:
                raise ValueError("Only an active account can save a theme.")
            conn.execute(
                "INSERT INTO user_preferences (user_id, theme) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET theme = excluded.theme, "
                "updated_at = datetime('now')", (user_id, theme),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_inventory_columns(self, user_id: int) -> list[str]:
        conn = self._connect()
        row = conn.execute(
            "SELECT view.columns_json FROM user_inventory_views view "
            "JOIN users account ON account.id = view.user_id "
            "WHERE view.user_id = ? AND account.role = 'admin' AND account.is_active = 1",
            (user_id,),
        ).fetchone()
        conn.close()
        if row:
            try:
                columns = json.loads(row["columns_json"])
                if (isinstance(columns, list) and "item" in columns and
                        len(columns) == len(set(columns)) and
                        all(column in INVENTORY_COLUMNS for column in columns)):
                    return columns
            except (ValueError, TypeError):
                pass
        return list(INVENTORY_COLUMNS)

    def save_inventory_columns(self, user_id: int, columns: list[str]) -> None:
        if (not columns or "item" not in columns or len(columns) != len(set(columns)) or
                any(column not in INVENTORY_COLUMNS for column in columns)):
            raise ValueError("Choose valid, unique inventory columns and keep Item visible.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            account = conn.execute("SELECT role, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
            if not account or not account["is_active"] or account["role"] != "admin":
                raise ValueError("Only an active Admin can customize inventory columns.")
            conn.execute(
                "INSERT INTO user_inventory_views (user_id, columns_json) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET columns_json = excluded.columns_json, "
                "updated_at = datetime('now')", (user_id, json.dumps(columns)),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_all_items(self, search: str = "", limit: int | None = None,
                      sort: str = "item", direction: str = "asc"):
        """Return active inventory rows.

        `limit` is opt-in: callers that render a table can pass a cap so
        a runaway DB doesn't try to inflate the entire inventory into
        RAM. Exports and admin scripts pass None to get everything.
        """
        order_fields = {
            "barcode": "barcode COLLATE NOCASE", "item": "item_name COLLATE NOCASE",
            "category": "category COLLATE NOCASE", "quantity": "current_quantity",
            "minimum": "minimum_stock",
        }
        order = order_fields.get(sort, order_fields["item"])
        sort_direction = "DESC" if direction == "desc" and sort in order_fields else "ASC"
        conn = self._connect()
        params: list = []
        query = "SELECT * FROM inventory_items"
        if search:
            query += (" WHERE barcode LIKE ? OR barcode_out LIKE ? OR item_name LIKE ? "
                      "OR category LIKE ? OR brand LIKE ?")
            params.extend([f"%{search}%"] * 5)
        query += f" ORDER BY {order} {sort_direction}, item_name COLLATE NOCASE, id"
        if isinstance(limit, int) and limit > 0:
            query += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(query, params).fetchall()
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

    def _apply_legacy_stock_delta(self, conn: sqlite3.Connection, item_id: int,
                                  current: int, delta: int) -> None:
        allocations = conn.execute(
            "SELECT stock.shelf_id, stock.quantity, section.system FROM item_shelf_stock stock "
            "JOIN pantry_shelves shelf ON shelf.id = stock.shelf_id "
            "JOIN pantry_sections section ON section.id = shelf.section_id "
            "WHERE stock.item_id = ?", (item_id,),
        ).fetchall()
        if sum(row["quantity"] for row in allocations) != current:
            raise ValueError("Stock locations need reconciliation before changing quantities.")
        if not delta:
            return
        unassigned = next((row for row in allocations if row["system"]), None)
        if delta > 0:
            shelf_id = unassigned["shelf_id"] if unassigned else conn.execute(
                "SELECT shelf.id FROM pantry_shelves shelf JOIN pantry_sections section "
                "ON section.id = shelf.section_id WHERE section.system = 1"
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?) "
                "ON CONFLICT(item_id, shelf_id) DO UPDATE SET quantity = quantity + excluded.quantity",
                (item_id, shelf_id, delta),
            )
        else:
            candidates = [row for row in allocations if row["quantity"] >= -delta]
            source = unassigned if unassigned and unassigned["quantity"] >= -delta else (
                candidates[0] if len(candidates) == 1 else None
            )
            if not source:
                raise ValueError("Choose a shelf to reduce; stock is split across shelves.")
            shelf_id = source["shelf_id"]
            conn.execute(
                "UPDATE item_shelf_stock SET quantity = quantity + ? "
                "WHERE item_id = ? AND shelf_id = ?", (delta, item_id, source["shelf_id"]),
            )
        item = conn.execute(
            "SELECT item_name, unit_weight_milli_lb FROM inventory_items WHERE id = ?", (item_id,)
        ).fetchone()
        conn.execute(
            "INSERT INTO inventory_movements (item_id, item_name, shelf_id, direction, "
            "quantity_delta, weight_milli_lb, recorded_by) VALUES (?, ?, ?, 'ADJUST', ?, ?, 'legacy')",
            (item_id, item["item_name"], shelf_id, delta,
             delta * item["unit_weight_milli_lb"]
             if item["unit_weight_milli_lb"] is not None else None),
        )

    def set_stock(self, item_id: int, quantity: int) -> None:
        if not isinstance(quantity, int) or not 0 <= quantity <= 1_000_000:
            raise ValueError("Quantity must be between zero and one million.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT current_quantity FROM inventory_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not item:
                raise ValueError("Item not found.")
            self._apply_legacy_stock_delta(conn, item_id, item["current_quantity"],
                                           quantity - item["current_quantity"])
            conn.execute(
                "UPDATE inventory_items SET current_quantity = ?, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?", (quantity, item_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES ('legacy', 'STOCK_LEGACY', ?)",
                (f"item={item_id} new_quantity={quantity}",),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def adjust_stock(self, barcode: str, delta: int) -> None:
        if not isinstance(delta, int):
            raise ValueError("Quantity change must be a whole number.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT id, current_quantity FROM inventory_items WHERE barcode = ?", (barcode,)
            ).fetchone()
            if not item or not 0 <= item["current_quantity"] + delta <= 1_000_000:
                raise ValueError("Item missing or stock count outside the allowed range.")
            self._apply_legacy_stock_delta(conn, item["id"], item["current_quantity"], delta)
            conn.execute(
                "UPDATE inventory_items SET current_quantity = current_quantity + ?, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?", (delta, item["id"]),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES ('legacy', 'STOCK_LEGACY', ?)",
                (f"item={item['id']} delta={delta}",),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_empty_item(self, item_id: int, confirm_barcode: str, username: str) -> str:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT barcode, item_name, current_quantity FROM inventory_items WHERE id = ?",
                (item_id,),
            ).fetchone()
            if not item:
                raise ValueError("Item not found.")
            if item["barcode"] != confirm_barcode:
                raise ValueError("Enter the item barcode to confirm deletion.")
            conn.execute("DELETE FROM inventory_movements WHERE item_id = ?", (item_id,))
            conn.execute("DELETE FROM pantry_cart_lines WHERE item_id = ?", (item_id,))
            conn.execute("DELETE FROM item_shelf_stock WHERE item_id = ?", (item_id,))
            conn.execute("DELETE FROM transactions WHERE barcode = ?", (item["barcode"],))
            conn.execute("DELETE FROM archived_transactions WHERE barcode = ?", (item["barcode"],))
            conn.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'ITEM_DELETE', ?)",
                (username, f"item={item_id} barcode={item['barcode']} "
                 f"name={item['item_name']} had_stock={item['current_quantity']}"),
            )
            conn.commit()
            return item["item_name"]
        except Exception:
            conn.rollback()
            raise
        finally:
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
        """Items with current_quantity < minimum_stock (including out of stock items with minimum set)."""
        conn = self._connect()
        rows = conn.execute(
            """SELECT * FROM inventory_items
               WHERE minimum_stock > 0 AND current_quantity < minimum_stock
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

    def get_active_cart(self, owner_id: int, direction: str = "IN"):
        conn = self._connect()
        cart = conn.execute(
            "SELECT * FROM pantry_carts WHERE owner_id = ? AND direction = ? AND status = 'DRAFT'",
            (owner_id, direction),
        ).fetchone()
        if not cart:
            conn.close()
            return None
        immediate = direction == "OUT" and cart["mode"] == "IMMEDIATE"
        if immediate:
            lines = conn.execute(
                "SELECT movement.id, movement.item_id, movement.shelf_id, "
                "ABS(movement.quantity_delta) AS quantity, movement.weight_milli_lb, "
                "movement.weight_override_reason AS override_reason, movement.item_name, "
                "item.barcode_out AS barcode, shelf.name AS shelf_name, "
                "section.name AS section_name FROM inventory_movements movement "
                "JOIN inventory_items item ON item.id = movement.item_id "
                "JOIN pantry_shelves shelf ON shelf.id = movement.shelf_id "
                "JOIN pantry_sections section ON section.id = shelf.section_id "
                "WHERE movement.cart_id = ? AND movement.direction = 'OUT' "
                "AND NOT EXISTS (SELECT 1 FROM inventory_movements undo "
                "WHERE undo.reverses_movement_id = movement.id) ORDER BY movement.id",
                (cart["id"],),
            ).fetchall()
        else:
            lines = conn.execute(
                "SELECT line.id, line.item_id, line.shelf_id, line.quantity, "
                "item.item_name, item.barcode, shelf.name AS shelf_name, "
                "section.name AS section_name FROM pantry_cart_lines line "
                "JOIN inventory_items item ON item.id = line.item_id "
                "JOIN pantry_shelves shelf ON shelf.id = line.shelf_id "
                "JOIN pantry_sections section ON section.id = shelf.section_id "
                "WHERE line.cart_id = ? ORDER BY line.id", (cart["id"],),
            ).fetchall()
        conn.close()
        result = dict(cart)
        result["lines"] = [dict(row) for row in lines]
        return result

    def add_scan_to_cart(self, owner_id: int, barcode: str, shelf_id: int) -> str:
        barcode = barcode.strip()
        if not barcode or len(barcode) > 128:
            raise ValueError("Scan an item barcode.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            item = conn.execute(
                "SELECT id FROM inventory_items WHERE barcode = ?", (barcode,)
            ).fetchone()
            if not item:
                if conn.execute(
                    "SELECT 1 FROM inventory_items WHERE barcode_out = ?", (barcode,)
                ).fetchone():
                    raise ValueError("This barcode is for scan-out. Use the scan-in barcode.")
                raise ValueError("Item not found. Ask an administrator to add it first.")
            shelf = conn.execute(
                "SELECT shelf.id FROM pantry_shelves shelf JOIN pantry_sections section "
                "ON section.id = shelf.section_id WHERE shelf.id = ? AND section.system = 0",
                (shelf_id,),
            ).fetchone()
            if not shelf:
                raise ValueError("Select an existing pantry shelf.")
            cart = conn.execute(
                "SELECT id FROM pantry_carts WHERE owner_id = ? AND direction = 'IN' "
                "AND status = 'DRAFT'", (owner_id,),
            ).fetchone()
            cart_id = cart["id"] if cart else uuid4().hex
            if not cart:
                conn.execute(
                    "INSERT INTO pantry_carts (id, owner_id, direction) VALUES (?, ?, 'IN')",
                    (cart_id, owner_id),
                )
            existing = conn.execute(
                "SELECT quantity FROM pantry_cart_lines WHERE cart_id = ? AND item_id = ? AND shelf_id = ?",
                (cart_id, item["id"], shelf_id),
            ).fetchone()
            if existing and existing["quantity"] >= 1_000_000:
                raise ValueError("Cart line has reached its quantity limit.")
            conn.execute(
                "INSERT INTO pantry_cart_lines (cart_id, item_id, shelf_id, quantity) "
                "VALUES (?, ?, ?, 1) ON CONFLICT(cart_id, item_id, shelf_id) "
                "DO UPDATE SET quantity = quantity + 1, weight_override_milli_lb = NULL, override_reason = ''",
                (cart_id, item["id"], shelf_id),
            )
            conn.execute(
                "UPDATE pantry_carts SET updated_at = datetime('now') WHERE id = ?", (cart_id,)
            )
            conn.commit()
            return cart_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_cart_line(self, owner_id: int, line_id: int, direction: str = "IN") -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT line.cart_id FROM pantry_cart_lines line "
                "JOIN pantry_carts cart ON cart.id = line.cart_id "
                "WHERE line.id = ? AND cart.owner_id = ? AND cart.direction = ? "
                "AND cart.status = 'DRAFT'",
                (line_id, owner_id, direction),
            ).fetchone()
            if not row:
                raise ValueError("Cart item is no longer available.")
            conn.execute("DELETE FROM pantry_cart_lines WHERE id = ?", (line_id,))
            conn.execute(
                "UPDATE pantry_carts SET updated_at = datetime('now') WHERE id = ?", (row["cart_id"],)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_cart_line_weight(self, owner_id: int, line_id: int, measured_milli_lb: int,
                             reason: str, username: str, direction: str = "IN") -> None:
        if (not isinstance(measured_milli_lb, int) or not 0 < measured_milli_lb <= 10_000_000
                or not reason.strip()):
            raise ValueError("Measured pounds and an override reason are required.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            line = conn.execute(
                "SELECT line.item_id FROM pantry_cart_lines line "
                "JOIN pantry_carts cart ON cart.id = line.cart_id "
                "WHERE line.id = ? AND cart.owner_id = ? AND cart.direction = ? "
                "AND cart.status = 'DRAFT'",
                (line_id, owner_id, direction),
            ).fetchone()
            if not line:
                raise ValueError("Cart item is no longer available.")
            conn.execute(
                "UPDATE pantry_cart_lines SET weight_override_milli_lb = ?, override_reason = ? "
                "WHERE id = ?", (measured_milli_lb, reason.strip()[:200], line_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'WEIGHT_OVERRIDE', ?)",
                (username, f"item={line['item_id']} line={line_id}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cancel_scan_cart(self, owner_id: int, cart_id: str, direction: str = "IN") -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cart = conn.execute(
                "SELECT mode FROM pantry_carts WHERE id = ? AND owner_id = ? AND direction = ? "
                "AND status = 'DRAFT'", (cart_id, owner_id, direction),
            ).fetchone()
            if cart and direction == "OUT" and cart["mode"] == "IMMEDIATE" and conn.execute(
                "SELECT 1 FROM inventory_movements movement WHERE movement.cart_id = ? "
                "AND movement.direction = 'OUT' AND NOT EXISTS "
                "(SELECT 1 FROM inventory_movements undo WHERE undo.reverses_movement_id = movement.id) "
                "LIMIT 1", (cart_id,),
            ).fetchone():
                raise ValueError("Food was already scanned out. Finish the visit or undo each scan.")
            changed = conn.execute(
                "UPDATE pantry_carts SET status = 'CANCELLED', updated_at = datetime('now') "
                "WHERE id = ? AND owner_id = ? AND direction = ? AND status = 'DRAFT'",
                (cart_id, owner_id, direction),
            ).rowcount
            if not changed:
                raise ValueError("Cart is no longer active.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_cart_receipt(self, owner_id: int, cart_id: str):
        conn = self._connect()
        cart = conn.execute(
            "SELECT * FROM pantry_carts WHERE id = ? AND owner_id = ? "
            "AND status = 'COMPLETED'", (cart_id, owner_id),
        ).fetchone()
        if not cart:
            conn.close()
            return None
        lines = conn.execute(
            "SELECT movement.id, movement.item_name, movement.quantity_delta "
            "FROM inventory_movements movement WHERE movement.cart_id = ? "
            "AND (movement.direction = 'IN' OR (movement.direction = 'OUT' "
            "AND NOT EXISTS (SELECT 1 FROM inventory_movements undo "
            "WHERE undo.reverses_movement_id = movement.id))) ORDER BY movement.id",
            (cart_id,),
        ).fetchall()
        visit = conn.execute(
            "SELECT id, verified_term, fulfillment_type FROM pantry_visits WHERE cart_id = ?",
            (cart_id,),
        ).fetchone()
        conn.close()
        result = dict(cart)
        result["lines"] = [dict(line) for line in lines]
        result["visit_id"] = visit["id"] if visit else None
        result["verified_term"] = visit["verified_term"] if visit else None
        result["known_weight_milli_lb"] = cart["session_weight_milli_lb"] or 0
        result["weight_entered"] = cart["session_weight_milli_lb"] is not None
        return result

    def complete_scan_in_cart(self, owner_id: int, cart_id: str, username: str,
                             session_weight_milli_lb: int | None = None):
        if session_weight_milli_lb is not None and (
                not isinstance(session_weight_milli_lb, int) or
                not 0 < session_weight_milli_lb <= 10_000_000):
            raise ValueError("Enter a valid total donation weight.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cart = conn.execute(
                "SELECT status FROM pantry_carts WHERE id = ? AND owner_id = ? AND direction = 'IN'",
                (cart_id, owner_id),
            ).fetchone()
            if not cart:
                raise ValueError("Cart not found.")
            if cart["status"] == "COMPLETED":
                conn.rollback()
                return self.get_cart_receipt(owner_id, cart_id)
            if cart["status"] != "DRAFT":
                raise ValueError("Cart is no longer active.")
            lines = conn.execute(
                "SELECT line.*, item.barcode, item.item_name, item.category, "
                "item.current_quantity FROM pantry_cart_lines line "
                "JOIN inventory_items item ON item.id = line.item_id WHERE line.cart_id = ?",
                (cart_id,),
            ).fetchall()
            if not lines:
                raise ValueError("Add an item before completing intake.")
            for line in lines:
                shelf = conn.execute(
                    "SELECT section.system FROM pantry_shelves shelf JOIN pantry_sections section "
                    "ON section.id = shelf.section_id WHERE shelf.id = ?", (line["shelf_id"],),
                ).fetchone()
                if not shelf or shelf["system"]:
                    raise ValueError("A cart shelf is no longer available.")
                allocated = conn.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM item_shelf_stock WHERE item_id = ?",
                    (line["item_id"],),
                ).fetchone()[0]
                current = conn.execute(
                    "SELECT current_quantity FROM inventory_items WHERE id = ?", (line["item_id"],)
                ).fetchone()[0]
                if allocated != current:
                    raise ValueError("Stock needs administrator reconciliation before intake.")
                if current + line["quantity"] > 1_000_000:
                    raise ValueError("The stock count would exceed the allowed range.")
                conn.execute(
                    "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, ?) "
                    "ON CONFLICT(item_id, shelf_id) DO UPDATE SET quantity = quantity + excluded.quantity",
                    (line["item_id"], line["shelf_id"], line["quantity"]),
                )
                conn.execute(
                    "UPDATE inventory_items SET current_quantity = current_quantity + ?, "
                    "updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (line["quantity"], line["item_id"]),
                )
                conn.execute(
                    "INSERT INTO inventory_movements (cart_id, item_id, item_name, shelf_id, "
                    "direction, quantity_delta, recorded_by) "
                    "VALUES (?, ?, ?, ?, 'IN', ?, ?)",
                    (cart_id, line["item_id"], line["item_name"], line["shelf_id"],
                     line["quantity"], username),
                )
                conn.execute(
                    "INSERT INTO transactions (transaction_type, barcode, item_name, category, "
                    "quantity, recipient, username) VALUES ('SCAN_IN', ?, ?, ?, ?, '', ?)",
                    (line["barcode"], line["item_name"], line["category"], line["quantity"], username),
                )
                needed = conn.execute(
                    "SELECT id, quantity_needed FROM shopping_list_items WHERE barcode = ?",
                    (line["barcode"],),
                ).fetchone()
                if needed:
                    remainder = max(0, needed["quantity_needed"] - line["quantity"])
                    if remainder:
                        conn.execute(
                            "UPDATE shopping_list_items SET quantity_needed = ? WHERE id = ?",
                            (remainder, needed["id"]),
                        )
                    else:
                        conn.execute("DELETE FROM shopping_list_items WHERE id = ?", (needed["id"],))
            conn.execute(
                "UPDATE pantry_carts SET status = 'COMPLETED', completed_at = datetime('now'), "
                "updated_at = datetime('now'), session_weight_milli_lb = ? WHERE id = ?",
                (session_weight_milli_lb, cart_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CART_IN', ?)",
                (username, f"cart={cart_id} lines={len(lines)}"),
            )
            conn.commit()
            return self.get_cart_receipt(owner_id, cart_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _eligible_client_on_connection(self, conn: sqlite3.Connection, client_id: int):
        client = conn.execute(
            "SELECT c.id, c.is_active, c.student_id, c.birth_date, c.enrollment_status, "
            "c.expected_graduation_semester, v.term, v.status, v.verified_until "
            "FROM pantry_clients c LEFT JOIN client_verifications v ON v.id = "
            "(SELECT id FROM client_verifications WHERE client_id = c.id ORDER BY id DESC LIMIT 1) "
            "WHERE c.id = ?", (client_id,),
        ).fetchone()
        if (not client or not client["is_active"] or not client["student_id"] or
                not client["birth_date"] or not client["expected_graduation_semester"] or
                client["status"] != "verified" or
                client["verified_until"] < _utc_date().isoformat()):
            raise ValueError("Verify this client's current-semester enrollment before checkout.")
        return client

    def _check_visit_capacity_on_connection(self, conn: sqlite3.Connection,
                                            client_id: int, cart_id: str | None = None):
        client = self._eligible_client_on_connection(conn, client_id)
        existing = conn.execute(
            "SELECT verified_term FROM pantry_visits WHERE cart_id = ?", (cart_id,)
        ).fetchone() if cart_id else None
        if existing:
            if existing["verified_term"] != client["term"]:
                raise ValueError("Reverify the current semester before adding food to this visit.")
            return client
        limit = 3 if client["enrollment_status"] == "full_time" else 2
        used = conn.execute(
            "SELECT COUNT(*) FROM pantry_visits WHERE client_id = ? AND verified_term = ? "
            "AND is_void = 0", (client_id, client["term"]),
        ).fetchone()[0]
        if used >= limit:
            raise ValueError(f"This client has reached the {limit}-visit limit for {client['term']}.")
        return client

    def get_client_visit_allowance(self, client_id: int) -> dict:
        conn = self._connect()
        record = conn.execute(
            "SELECT enrollment_status FROM pantry_clients WHERE id = ?", (client_id,)
        ).fetchone()
        if not record:
            conn.close()
            raise ValueError("Client not found.")
        limit = 3 if record["enrollment_status"] == "full_time" else 2
        try:
            client = self._eligible_client_on_connection(conn, client_id)
            term = client["term"]
            used = conn.execute(
                "SELECT COUNT(*) FROM pantry_visits WHERE client_id = ? AND verified_term = ? "
                "AND is_void = 0", (client_id, term),
            ).fetchone()[0]
            return {"term": term, "used": used, "limit": limit,
                    "remaining": max(0, limit - used), "verified": True}
        except ValueError:
            return {"term": None, "used": 0, "limit": limit, "remaining": 0, "verified": False}
        finally:
            conn.close()

    def start_scan_out_cart(self, owner_id: int, client_id: int,
                            mode: str = "REVIEW", fulfillment_type: str = "in_person") -> str:
        if mode not in ("REVIEW", "IMMEDIATE") or fulfillment_type not in ("in_person", "locker"):
            raise ValueError("Choose a valid distribution mode and fulfillment type.")
        if fulfillment_type == "locker" and mode != "IMMEDIATE":
            raise ValueError("Locker orders require immediate mode so returned food can be undone and audited.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            owner = conn.execute(
                "SELECT role, is_active FROM users WHERE id = ?", (owner_id,)
            ).fetchone()
            if not owner or owner["role"] != "admin" or not owner["is_active"]:
                raise ValueError("Only an active administrator may distribute food.")
            existing = conn.execute(
                "SELECT id, client_id, mode, fulfillment_type FROM pantry_carts "
                "WHERE owner_id = ? AND direction = 'OUT' AND status = 'DRAFT'", (owner_id,),
            ).fetchone()
            if existing and (existing["client_id"] != client_id or existing["mode"] != mode or
                             existing["fulfillment_type"] != fulfillment_type):
                raise ValueError("Finish or cancel the current visitor's cart first.")
            self._check_visit_capacity_on_connection(
                conn, client_id, existing["id"] if existing else None
            )
            if existing:
                conn.commit()
                return existing["id"]
            cart_id = uuid4().hex
            conn.execute(
                "INSERT INTO pantry_carts (id, owner_id, direction, client_id, mode, fulfillment_type) "
                "VALUES (?, ?, 'OUT', ?, ?, ?)",
                (cart_id, owner_id, client_id, mode, fulfillment_type),
            )
            conn.commit()
            return cart_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_scan_out_to_cart(self, owner_id: int, barcode: str, shelf_id: int | None = None) -> str:
        barcode = barcode.strip()
        if not barcode or len(barcode) > 128:
            raise ValueError("Scan an item barcode.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            owner = conn.execute(
                "SELECT role, is_active FROM users WHERE id = ?", (owner_id,)
            ).fetchone()
            if not owner or owner["role"] != "admin" or not owner["is_active"]:
                raise ValueError("Only an active administrator may distribute food.")
            cart = conn.execute(
                "SELECT id, client_id, mode FROM pantry_carts WHERE owner_id = ? AND direction = 'OUT' "
                "AND status = 'DRAFT'", (owner_id,),
            ).fetchone()
            if not cart:
                raise ValueError("Choose an eligible client before scanning out.")
            if cart["mode"] != "REVIEW":
                raise ValueError("This visitor is in immediate scan-out mode.")
            self._check_visit_capacity_on_connection(conn, cart["client_id"], cart["id"])
            matches = conn.execute(
                "SELECT id FROM inventory_items WHERE barcode_out = ? OR "
                "(barcode = ? AND (barcode_out IS NULL OR barcode_out = ''))",
                (barcode, barcode),
            ).fetchall()
            if len(matches) != 1:
                raise ValueError("Scan-out barcode not found or ambiguous. Ask an Admin to check it.")
            item = matches[0]
            available_shelves = conn.execute(
                "SELECT stock.shelf_id FROM item_shelf_stock stock "
                "JOIN pantry_shelves shelf ON shelf.id = stock.shelf_id "
                "JOIN pantry_sections section ON section.id = shelf.section_id "
                "LEFT JOIN pantry_cart_lines line ON line.cart_id = ? AND line.item_id = stock.item_id "
                "AND line.shelf_id = stock.shelf_id "
                "WHERE stock.item_id = ? AND section.system = 0 "
                "AND stock.quantity > COALESCE(line.quantity, 0)",
                (cart["id"], item["id"]),
            ).fetchall()
            if shelf_id is None:
                if len(available_shelves) != 1:
                    if not available_shelves:
                        raise ValueError("This item has no stocked physical shelf.")
                    raise ValueError("This item is stocked on more than one shelf. Choose the shelf it came from.")
                shelf_id = available_shelves[0]["shelf_id"]
            elif not any(row["shelf_id"] == shelf_id for row in available_shelves):
                raise ValueError("The selected shelf does not have enough stock.")
            conn.execute(
                "INSERT INTO pantry_cart_lines (cart_id, item_id, shelf_id, quantity) "
                "VALUES (?, ?, ?, 1) ON CONFLICT(cart_id, item_id, shelf_id) "
                "DO UPDATE SET quantity = quantity + 1, weight_override_milli_lb = NULL, override_reason = ''",
                (cart["id"], item["id"], shelf_id),
            )
            conn.execute(
                "UPDATE pantry_carts SET updated_at = datetime('now') WHERE id = ?", (cart["id"],)
            )
            conn.commit()
            return cart["id"]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_immediate_scan_out(self, owner_id: int, barcode: str, shelf_id: int | None,
                                  username: str, scan_request_id: str) -> int:
        barcode = barcode.strip()
        if not barcode or len(barcode) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", scan_request_id):
            raise ValueError("Scan a valid out-barcode from the open visit page.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            actor = conn.execute("SELECT role, is_active FROM users WHERE id = ?", (owner_id,)).fetchone()
            cart = conn.execute(
                "SELECT id, client_id, fulfillment_type FROM pantry_carts "
                "WHERE owner_id = ? AND direction = 'OUT' "
                "AND mode = 'IMMEDIATE' AND status = 'DRAFT'", (owner_id,),
            ).fetchone()
            if not actor or actor["role"] != "admin" or not actor["is_active"] or not cart:
                raise ValueError("Choose an open Admin visitor session before scanning out.")
            previous = conn.execute(
                "SELECT id, cart_id FROM inventory_movements WHERE scan_request_id = ?",
                (scan_request_id,),
            ).fetchone()
            if previous:
                if previous["cart_id"] != cart["id"]:
                    raise ValueError("This scan request belongs to another visit.")
                conn.rollback()
                return previous["id"]
            client = self._check_visit_capacity_on_connection(conn, cart["client_id"], cart["id"])
            matches = conn.execute(
                "SELECT id, barcode, item_name, category, current_quantity "
                "FROM inventory_items WHERE barcode_out = ? OR "
                "(barcode = ? AND (barcode_out IS NULL OR barcode_out = ''))",
                (barcode, barcode),
            ).fetchall()
            if len(matches) != 1:
                raise ValueError("Scan-out barcode not found or ambiguous. Check the item label.")
            item = matches[0]
            available_shelves = conn.execute(
                "SELECT stock.shelf_id FROM item_shelf_stock stock "
                "JOIN pantry_shelves shelf ON shelf.id = stock.shelf_id "
                "JOIN pantry_sections section ON section.id = shelf.section_id "
                "WHERE stock.item_id = ? AND stock.quantity > 0 AND section.system = 0",
                (item["id"],),
            ).fetchall()
            allocated = conn.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM item_shelf_stock WHERE item_id = ?",
                (item["id"],),
            ).fetchone()[0]
            if allocated != item["current_quantity"]:
                raise ValueError("Stock locations need Admin reconciliation before distribution.")
            if item["current_quantity"] < 1 or not available_shelves:
                raise ValueError("This item has no stock on a physical shelf.")
            if shelf_id is None:
                if len(available_shelves) != 1:
                    raise ValueError("This item is stocked on more than one shelf. Choose the shelf it came from.")
                shelf_id = available_shelves[0]["shelf_id"]
            elif not any(row["shelf_id"] == shelf_id for row in available_shelves):
                raise ValueError("The selected shelf has no available stock for this item.")
            visit = conn.execute(
                "SELECT id, items_json FROM pantry_visits WHERE cart_id = ?", (cart["id"],)
            ).fetchone()
            if visit is None:
                visit_id = conn.execute(
                    "INSERT INTO pantry_visits (client_id, pounds_received, items_json, recorded_by, "
                    "known_weight_milli_lb, pending_weight_lines, weight_complete, cart_id, "
                    "verified_term, fulfillment_type) "
                    "VALUES (?, NULL, '[]', ?, 0, 0, 0, ?, ?, ?)",
                    (cart["client_id"], username, cart["id"], client["term"],
                     cart["fulfillment_type"]),
                ).lastrowid
                items = []
            else:
                visit_id = visit["id"]
                items = json.loads(visit["items_json"] or "[]")
            conn.execute(
                "UPDATE item_shelf_stock SET quantity = quantity - 1 "
                "WHERE item_id = ? AND shelf_id = ?", (item["id"], shelf_id),
            )
            conn.execute(
                "UPDATE inventory_items SET current_quantity = current_quantity - 1, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?", (item["id"],),
            )
            movement_id = conn.execute(
                "INSERT INTO inventory_movements (cart_id, item_id, item_name, shelf_id, "
                "client_id, visit_id, direction, quantity_delta, "
                "scan_request_id, recorded_by) "
                "VALUES (?, ?, ?, ?, ?, ?, 'OUT', -1, ?, ?)",
                (cart["id"], item["id"], item["item_name"], shelf_id,
                 cart["client_id"], visit_id, scan_request_id, username),
            ).lastrowid
            items.append({"movement_id": movement_id, "item_id": item["id"],
                          "item_name": item["item_name"], "shelf_id": shelf_id,
                          "quantity": 1, "undone": False})
            conn.execute(
                "UPDATE pantry_visits SET items_json = ? WHERE id = ?",
                (json.dumps(items), visit_id),
            )
            conn.execute(
                "INSERT INTO transactions (transaction_type, barcode, item_name, category, "
                "quantity, recipient, username) VALUES ('SCAN_OUT', ?, ?, ?, 1, '', ?)",
                (barcode, item["item_name"], item["category"], username),
            )
            conn.execute(
                "INSERT INTO shopping_list_items (barcode, item_name, category, quantity_needed) "
                "VALUES (?, ?, ?, 1) ON CONFLICT(barcode) DO UPDATE SET "
                "quantity_needed = quantity_needed + 1",
                (item["barcode"], item["item_name"], item["category"]),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) "
                "VALUES (?, 'SCAN_OUT_IMMEDIATE', ?)",
                (username, f"cart={cart['id']} visit={visit_id} movement={movement_id}"),
            )
            conn.commit()
            return movement_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def undo_immediate_scan(self, owner_id: int, movement_id: int,
                            reason: str, username: str) -> str:
        reason = reason.strip()
        if not reason or len(reason) > 200:
            raise ValueError("Enter a reason for correcting this scan.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            actor = conn.execute("SELECT role, is_active FROM users WHERE id = ?", (owner_id,)).fetchone()
            movement = conn.execute(
                "SELECT movement.id, movement.cart_id, movement.item_id, movement.item_name, "
                "movement.shelf_id, movement.client_id, movement.visit_id, movement.weight_milli_lb "
                "FROM inventory_movements movement JOIN pantry_carts cart ON cart.id = movement.cart_id "
                "WHERE movement.id = ? AND movement.direction = 'OUT' "
                "AND cart.owner_id = ? AND cart.mode = 'IMMEDIATE'",
                (movement_id, owner_id),
            ).fetchone()
            if not actor or actor["role"] != "admin" or not actor["is_active"] or not movement:
                raise ValueError("This scan cannot be corrected from your visit.")
            if conn.execute(
                "SELECT 1 FROM inventory_movements WHERE reverses_movement_id = ?", (movement_id,)
            ).fetchone():
                raise ValueError("This scan was already corrected.")
            current = conn.execute(
                "SELECT current_quantity, barcode, category FROM inventory_items WHERE id = ?",
                (movement["item_id"],),
            ).fetchone()
            if not current or current["current_quantity"] >= 1_000_000:
                raise ValueError("Item stock cannot safely be restored.")
            conn.execute(
                "INSERT INTO item_shelf_stock (item_id, shelf_id, quantity) VALUES (?, ?, 1) "
                "ON CONFLICT(item_id, shelf_id) DO UPDATE SET quantity = quantity + 1",
                (movement["item_id"], movement["shelf_id"]),
            )
            conn.execute(
                "UPDATE inventory_items SET current_quantity = current_quantity + 1, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?", (movement["item_id"],),
            )
            conn.execute(
                "INSERT INTO inventory_movements (cart_id, item_id, item_name, shelf_id, "
                "client_id, visit_id, direction, quantity_delta, weight_milli_lb, "
                "reverses_movement_id, movement_reason, recorded_by) "
                "VALUES (?, ?, ?, ?, ?, ?, 'ADJUST', 1, ?, ?, ?, ?)",
                (movement["cart_id"], movement["item_id"], movement["item_name"],
                 movement["shelf_id"], movement["client_id"], movement["visit_id"],
                 abs(movement["weight_milli_lb"]) if movement["weight_milli_lb"] is not None else None,
                 movement_id, reason, username),
            )
            visit = conn.execute(
                "SELECT items_json FROM pantry_visits WHERE id = ?", (movement["visit_id"],)
            ).fetchone()
            items = json.loads(visit["items_json"] or "[]")
            for entry in items:
                if entry.get("movement_id") == movement_id:
                    entry["undone"] = True
                    break
            conn.execute("UPDATE pantry_visits SET items_json = ? WHERE id = ?",
                         (json.dumps(items), movement["visit_id"]),)
            self._refresh_visit_weight_on_connection(conn, movement["visit_id"])
            needed = conn.execute(
                "SELECT id, quantity_needed FROM shopping_list_items WHERE barcode = ?",
                (current["barcode"],),
            ).fetchone()
            if needed:
                if needed["quantity_needed"] <= 1:
                    conn.execute("DELETE FROM shopping_list_items WHERE id = ?", (needed["id"],))
                else:
                    conn.execute("UPDATE shopping_list_items SET quantity_needed = quantity_needed - 1 "
                                 "WHERE id = ?", (needed["id"],))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'SCAN_OUT_UNDO', ?)",
                (username, f"movement={movement_id} visit={movement['visit_id']}"),
            )
            conn.commit()
            return movement["cart_id"]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _refresh_visit_weight_on_connection(self, conn: sqlite3.Connection,
                                            visit_id: int) -> None:
        active = conn.execute(
            "SELECT COUNT(*) AS units "
            "FROM inventory_movements movement WHERE movement.visit_id = ? "
            "AND movement.direction = 'OUT' AND NOT EXISTS "
            "(SELECT 1 FROM inventory_movements undo WHERE undo.reverses_movement_id = movement.id)",
            (visit_id,),
        ).fetchone()
        is_void = not active["units"]
        conn.execute(
            "UPDATE pantry_visits SET is_void = ? WHERE id = ?",
            (int(is_void), visit_id),
        )

    def get_client_weight_summary(self, client_id: int) -> dict:
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(*) AS total_visits, "
            "COALESCE(SUM(COALESCE(known_weight_milli_lb, "
            "CAST(ROUND(COALESCE(pounds_received, 0) * 1000) AS INTEGER))), 0) "
            "AS known_weight_milli_lb, "
            "COALESCE(SUM(CASE WHEN weight_complete = 0 THEN 1 ELSE 0 END), 0) "
            "AS pending_visits FROM pantry_visits WHERE client_id = ? AND is_void = 0", (client_id,),
        ).fetchone()
        conn.close()
        return dict(row)

    def get_monthly_weight_report(self, month: str) -> dict:
        if len(month) != 7 or month[4] != "-" or not (month[:4] + month[5:]).isdigit():
            raise ValueError("Enter a month in YYYY-MM format.")
        try:
            first = datetime.date.fromisoformat(f"{month}-01")
        except ValueError as exc:
            raise ValueError("Enter a valid reporting month.") from exc
        following = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        start = f"{month}-01"
        end = following.isoformat()
        conn = self._connect()
        intake_carts = conn.execute(
            "SELECT COALESCE(SUM(session_weight_milli_lb), 0) AS total, "
            "COALESCE(SUM(CASE WHEN session_weight_milli_lb IS NULL THEN 1 ELSE 0 END), 0) AS pending "
            "FROM pantry_carts WHERE direction = 'IN' AND status = 'COMPLETED' "
            "AND completed_at >= ? AND completed_at < ?",
            (start, end),
        ).fetchone()
        standalone = conn.execute(
            "SELECT COALESCE(SUM(weight_milli_lb), 0) AS total "
            "FROM donation_records WHERE donation_date >= ? AND donation_date < ?",
            (start, end),
        ).fetchone()
        donated_total = intake_carts["total"] + standalone["total"]
        distributed = conn.execute(
            "SELECT COALESCE(SUM(session_weight_milli_lb), 0) AS total, "
            "COALESCE(SUM(CASE WHEN session_weight_milli_lb IS NULL THEN 1 ELSE 0 END), 0) AS pending "
            "FROM pantry_carts WHERE direction = 'OUT' AND status = 'COMPLETED' "
            "AND completed_at >= ? AND completed_at < ?",
            (start, end),
        ).fetchone()
        earliest_cart = conn.execute(
            "SELECT MIN(completed_at) FROM pantry_carts WHERE status = 'COMPLETED'"
        ).fetchone()[0]
        earliest_donation = conn.execute(
            "SELECT MIN(donation_date) FROM donation_records"
        ).fetchone()[0]
        earliest = min(filter(None, [earliest_cart, earliest_donation]), default=None)
        conn.close()
        return {
            "month": month, "timezone": "UTC", "first_movement": earliest,
            "donated_milli_lb": donated_total,
            "donated_intake_milli_lb": intake_carts["total"],
            "donated_standalone_milli_lb": standalone["total"],
            "distributed_milli_lb": distributed["total"],
            "pending_sessions": intake_carts["pending"] + distributed["pending"],
            "history_available": earliest is not None and earliest[:7] <= month,
        }

    # ------------------------------------------------------------------
    # Donation records (standalone weight entries)
    # ------------------------------------------------------------------

    def record_donation_weight(self, weight_milli_lb: int, donation_date: str,
                               source: str, notes: str, username: str,
                               cart_id: str | None = None) -> int:
        if not isinstance(weight_milli_lb, int) or not 0 < weight_milli_lb <= 10_000_000:
            raise ValueError("Enter a valid donation weight.")
        if not donation_date or len(donation_date) != 10:
            raise ValueError("Enter a valid date in YYYY-MM-DD format.")
        try:
            datetime.date.fromisoformat(donation_date)
        except ValueError as exc:
            raise ValueError("Enter a valid donation date.") from exc
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO donation_records (weight_milli_lb, donation_date, source, "
                "notes, cart_id, recorded_by) VALUES (?, ?, ?, ?, ?, ?)",
                (weight_milli_lb, donation_date, (source or "").strip()[:200],
                 (notes or "").strip()[:500], cart_id, username),
            )
            record_id = cur.lastrowid
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'DONATION_RECORD', ?)",
                (username, f"id={record_id} lb={weight_milli_lb / 1000:.3f} date={donation_date}"),
            )
            conn.commit()
            return record_id
        finally:
            conn.close()

    def update_donation_record(self, record_id: int, weight_milli_lb: int,
                               donation_date: str, source: str, notes: str,
                               username: str) -> None:
        if not isinstance(weight_milli_lb, int) or not 0 < weight_milli_lb <= 10_000_000:
            raise ValueError("Enter a valid donation weight.")
        if not donation_date or len(donation_date) != 10:
            raise ValueError("Enter a valid date in YYYY-MM-DD format.")
        try:
            datetime.date.fromisoformat(donation_date)
        except ValueError as exc:
            raise ValueError("Enter a valid donation date.") from exc
        conn = self._connect()
        try:
            old = conn.execute("SELECT * FROM donation_records WHERE id = ?",
                               (record_id,)).fetchone()
            if not old:
                raise ValueError("Donation record not found.")
            changes = []
            if old["weight_milli_lb"] != weight_milli_lb:
                changes.append(f"weight:{old['weight_milli_lb']}->{weight_milli_lb}")
            if old["donation_date"] != donation_date:
                changes.append(f"date:{old['donation_date']}->{donation_date}")
            if old["source"] != (source or "").strip():
                changes.append(f"source changed")
            if old["notes"] != (notes or "").strip():
                changes.append(f"notes changed")
            conn.execute(
                "UPDATE donation_records SET weight_milli_lb = ?, donation_date = ?, "
                "source = ?, notes = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (weight_milli_lb, donation_date, (source or "").strip()[:200],
                 (notes or "").strip()[:500], record_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'DONATION_EDIT', ?)",
                (username, f"id={record_id} changes=[{', '.join(changes)}]"),
            )
            conn.commit()
        finally:
            conn.close()

    def get_donation_records(self, limit: int = 200) -> list[dict]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM donation_records ORDER BY donation_date DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_donation_record(self, record_id: int) -> dict | None:
        conn = self._connect()
        row = conn.execute("SELECT * FROM donation_records WHERE id = ?",
                           (record_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_donation_record(self, record_id: int, username: str) -> None:
        conn = self._connect()
        try:
            old = conn.execute("SELECT * FROM donation_records WHERE id = ?",
                               (record_id,)).fetchone()
            if not old:
                raise ValueError("Donation record not found.")
            conn.execute("DELETE FROM donation_records WHERE id = ?", (record_id,))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'DONATION_DELETE', ?)",
                (username, f"id={record_id} lb={old['weight_milli_lb'] / 1000:.3f} date={old['donation_date']}"),
            )
            conn.commit()
        finally:
            conn.close()

    def update_session_weight(self, cart_id: str, weight_milli_lb: int,
                              reason: str, username: str) -> None:
        if not isinstance(weight_milli_lb, int) or not 0 < weight_milli_lb <= 10_000_000:
            raise ValueError("Enter a valid weight.")
        reason = (reason or "").strip()
        if not reason or len(reason) > 200:
            raise ValueError("Enter a correction reason (up to 200 characters).")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cart = conn.execute(
                "SELECT id, session_weight_milli_lb, direction FROM pantry_carts "
                "WHERE id = ? AND status = 'COMPLETED'", (cart_id,),
            ).fetchone()
            if not cart:
                raise ValueError("Completed session not found.")
            old_weight = cart["session_weight_milli_lb"]
            conn.execute(
                "UPDATE pantry_carts SET session_weight_milli_lb = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (weight_milli_lb, cart_id),
            )
            if cart["direction"] == "OUT":
                visit = conn.execute(
                    "SELECT id FROM pantry_visits WHERE cart_id = ?", (cart_id,)
                ).fetchone()
                if visit:
                    conn.execute(
                        "UPDATE pantry_visits SET known_weight_milli_lb = ?, "
                        "pending_weight_lines = 0, weight_complete = 1, "
                        "pounds_received = ? WHERE id = ?",
                        (weight_milli_lb, weight_milli_lb / 1000, visit["id"]),
                    )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'WEIGHT_CORRECTION', ?)",
                (username, f"cart={cart_id} old={old_weight} new={weight_milli_lb} reason={reason}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def resolve_movement_weight(self, movement_id: int, measured_milli_lb: int,
                                reason: str, username: str) -> None:
        reason = reason.strip()
        if (not isinstance(measured_milli_lb, int) or not 0 < measured_milli_lb <= 10_000_000 or
                not reason or len(reason) > 200):
            raise ValueError("Enter positive measured pounds and a reason (up to 200 characters).")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            movement = conn.execute(
                "SELECT item_id, shelf_id, visit_id, direction, quantity_delta, weight_milli_lb "
                "FROM inventory_movements WHERE id = ?", (movement_id,),
            ).fetchone()
            if (not movement or movement["weight_milli_lb"] is not None or
                    movement["direction"] == "TRANSFER" or conn.execute(
                        "SELECT 1 FROM inventory_movements WHERE id = ? AND reverses_movement_id IS NOT NULL "
                        "UNION SELECT 1 FROM inventory_movements WHERE reverses_movement_id = ? LIMIT 1",
                        (movement_id, movement_id),
                    ).fetchone()):
                raise ValueError("This movement has already been weighed or cannot be reconciled.")
            signed_weight = (-measured_milli_lb if movement["quantity_delta"] < 0
                             else measured_milli_lb)
            conn.execute(
                "UPDATE inventory_movements SET weight_milli_lb = ?, weight_override_reason = ? "
                "WHERE id = ? AND weight_milli_lb IS NULL",
                (signed_weight, reason, movement_id),
            )
            if movement["visit_id"]:
                amounts = conn.execute(
                    "SELECT COALESCE(SUM(ABS(weight_milli_lb)), 0) AS known, "
                    "COALESCE(SUM(CASE WHEN weight_milli_lb IS NULL THEN 1 ELSE 0 END), 0) AS pending "
                    "FROM inventory_movements WHERE visit_id = ?", (movement["visit_id"],),
                ).fetchone()
                visit = conn.execute(
                    "SELECT items_json FROM pantry_visits WHERE id = ?", (movement["visit_id"],)
                ).fetchone()
                items = json.loads(visit["items_json"] or "[]")
                for entry in items:
                    if (entry.get("movement_id") == movement_id or
                            ("movement_id" not in entry and entry.get("item_id") == movement["item_id"]
                             and entry.get("shelf_id") == movement["shelf_id"])):
                        entry["weight_milli_lb"] = measured_milli_lb
                        break
                conn.execute(
                    "UPDATE pantry_visits SET known_weight_milli_lb = ?, pending_weight_lines = ?, "
                    "weight_complete = ?, pounds_received = ?, items_json = ? WHERE id = ?",
                    (amounts["known"], amounts["pending"], int(not amounts["pending"]),
                     amounts["known"] / 1000 if not amounts["pending"] else None,
                     json.dumps(items), movement["visit_id"]),
                )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'WEIGHT_RESOLVE', ?)",
                (username, f"movement={movement_id} pounds_milli={measured_milli_lb}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def complete_scan_out_cart(self, owner_id: int, cart_id: str, username: str,
                              session_weight_milli_lb: int | None = None):
        if session_weight_milli_lb is not None and (
                not isinstance(session_weight_milli_lb, int) or
                not 0 < session_weight_milli_lb <= 10_000_000):
            raise ValueError("Enter a valid total weight for this visit.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            owner = conn.execute(
                "SELECT role, is_active FROM users WHERE id = ?", (owner_id,)
            ).fetchone()
            if not owner or owner["role"] != "admin" or not owner["is_active"]:
                raise ValueError("Only an active administrator may distribute food.")
            cart = conn.execute(
                "SELECT status, client_id, mode, fulfillment_type FROM pantry_carts "
                "WHERE id = ? AND owner_id = ? AND direction = 'OUT'", (cart_id, owner_id),
            ).fetchone()
            if not cart:
                raise ValueError("Cart not found.")
            if cart["status"] == "COMPLETED":
                conn.rollback()
                return self.get_cart_receipt(owner_id, cart_id)
            if cart["status"] != "DRAFT":
                raise ValueError("Cart is no longer active.")
            if cart["mode"] == "IMMEDIATE":
                active = conn.execute(
                    "SELECT 1 FROM inventory_movements movement WHERE movement.cart_id = ? "
                    "AND movement.direction = 'OUT' AND NOT EXISTS "
                    "(SELECT 1 FROM inventory_movements undo WHERE undo.reverses_movement_id = movement.id) "
                    "LIMIT 1", (cart_id,),
                ).fetchone()
                if not active:
                    raise ValueError("Scan an item before finishing this visit.")
                visit = conn.execute(
                    "SELECT id FROM pantry_visits WHERE cart_id = ?", (cart_id,)
                ).fetchone()
                if visit and session_weight_milli_lb is not None:
                    conn.execute(
                        "UPDATE pantry_visits SET known_weight_milli_lb = ?, "
                        "pending_weight_lines = 0, weight_complete = 1, "
                        "pounds_received = ? WHERE id = ?",
                        (session_weight_milli_lb, session_weight_milli_lb / 1000,
                         visit["id"]),
                    )
                conn.execute(
                    "UPDATE pantry_carts SET status = 'COMPLETED', completed_at = datetime('now'), "
                    "updated_at = datetime('now'), session_weight_milli_lb = ? WHERE id = ?",
                    (session_weight_milli_lb, cart_id),
                )
                conn.execute(
                    "INSERT INTO activity_log (username, action, detail) VALUES (?, 'VISIT_FINISH', ?)",
                    (username, f"cart={cart_id}"),
                )
                conn.commit()
                return self.get_cart_receipt(owner_id, cart_id)
            client = self._check_visit_capacity_on_connection(conn, cart["client_id"], cart_id)
            lines = conn.execute(
                "SELECT line.*, item.barcode, item.item_name, item.category, "
                "item.current_quantity "
                "FROM pantry_cart_lines line JOIN inventory_items item ON item.id = line.item_id "
                "WHERE line.cart_id = ? ORDER BY line.id", (cart_id,),
            ).fetchall()
            if not lines:
                raise ValueError("Add an item before completing distribution.")
            items = json.dumps([
                {"item_id": line["item_id"], "item_name": line["item_name"],
                 "shelf_id": line["shelf_id"], "quantity": line["quantity"]}
                for line in lines
            ])
            weight_complete = session_weight_milli_lb is not None
            visit = conn.execute(
                "INSERT INTO pantry_visits (client_id, pounds_received, items_json, recorded_by, "
                "known_weight_milli_lb, pending_weight_lines, weight_complete, cart_id, "
                "verified_term, fulfillment_type) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
                (cart["client_id"],
                 session_weight_milli_lb / 1000 if weight_complete else None,
                 items, username, session_weight_milli_lb if weight_complete else 0,
                 int(weight_complete), cart_id, client["term"],
                 cart["fulfillment_type"]),
            )
            visit_id = visit.lastrowid
            for line in lines:
                shelf = conn.execute(
                    "SELECT stock.quantity, section.system FROM item_shelf_stock stock "
                    "JOIN pantry_shelves shelf ON shelf.id = stock.shelf_id "
                    "JOIN pantry_sections section ON section.id = shelf.section_id "
                    "WHERE stock.item_id = ? AND stock.shelf_id = ?",
                    (line["item_id"], line["shelf_id"]),
                ).fetchone()
                allocated = conn.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM item_shelf_stock WHERE item_id = ?",
                    (line["item_id"],),
                ).fetchone()[0]
                if allocated != line["current_quantity"]:
                    raise ValueError("Stock needs administrator reconciliation before checkout.")
                if (not shelf or shelf["system"] or shelf["quantity"] < line["quantity"] or
                        line["current_quantity"] < line["quantity"]):
                    raise ValueError("A cart item is no longer in stock on its selected shelf.")
                conn.execute(
                    "UPDATE item_shelf_stock SET quantity = quantity - ? WHERE item_id = ? AND shelf_id = ?",
                    (line["quantity"], line["item_id"], line["shelf_id"]),
                )
                conn.execute(
                    "UPDATE inventory_items SET current_quantity = current_quantity - ?, "
                    "updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (line["quantity"], line["item_id"]),
                )
                conn.execute(
                    "INSERT INTO inventory_movements (cart_id, item_id, item_name, shelf_id, "
                    "client_id, visit_id, direction, quantity_delta, recorded_by) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'OUT', ?, ?)",
                    (cart_id, line["item_id"], line["item_name"], line["shelf_id"],
                     cart["client_id"], visit_id, -line["quantity"], username),
                )
                conn.execute(
                    "INSERT INTO transactions (transaction_type, barcode, item_name, category, "
                    "quantity, recipient, username) VALUES ('SCAN_OUT', ?, ?, ?, ?, '', ?)",
                    (line["barcode"], line["item_name"], line["category"],
                     line["quantity"], username),
                )
                conn.execute(
                    "INSERT INTO shopping_list_items (barcode, item_name, category, quantity_needed) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(barcode) DO UPDATE SET "
                    "quantity_needed = quantity_needed + excluded.quantity_needed",
                    (line["barcode"], line["item_name"], line["category"], line["quantity"]),
                )
            conn.execute(
                "UPDATE pantry_carts SET status = 'COMPLETED', completed_at = datetime('now'), "
                "updated_at = datetime('now'), session_weight_milli_lb = ? WHERE id = ?",
                (session_weight_milli_lb, cart_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CART_OUT', ?)",
                (username, f"cart={cart_id} visit={visit_id}"),
            )
            conn.commit()
            return self.get_cart_receipt(owner_id, cart_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

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
        
        # After transaction, check if item is now below minimum stock
        # and add to shopping list if needed
        if transaction_type == "SCAN_OUT":
            self._check_and_add_low_stock_item(barcode, item_name, category)

    # ------------------------------------------------------------------
    # Shopping list
    # ------------------------------------------------------------------

    def _check_and_add_low_stock_item(self, barcode: str, item_name: str, category: str) -> None:
        """Check if item is below minimum stock and add to shopping list if needed."""
        try:
            conn = self._connect()
            # Get current quantity and minimum stock
            item = conn.execute(
                "SELECT current_quantity, minimum_stock FROM inventory_items WHERE barcode=?",
                (barcode,)
            ).fetchone()
            conn.close()
            
            if item and item["minimum_stock"] > 0 and item["current_quantity"] < item["minimum_stock"]:
                # Item is below minimum, add to shopping list
                qty_needed = item["minimum_stock"] - item["current_quantity"]
                self._apply_shopping_list_delta(barcode, item_name, category, qty_needed)
        except Exception:
            pass  # Silently fail if check doesn't work

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

    # Columns of archived_users that are safe to hand back to the UI.
    # password_hash and salt stay in the DB (restore_archived_user needs
    # them) but must NEVER leave server memory — they'd otherwise show up
    # in list responses, screenshots, error tracebacks, etc.
    _ARCHIVED_USER_SAFE_COLS = (
        "archive_id, original_id, username, role, full_name, created_at, "
        "is_active, has_completed_tour, last_login, created_by, "
        "archived_at, archived_by"
    )

    def get_archived_users(self, search: str = ""):
        conn = self._connect()
        cols = self._ARCHIVED_USER_SAFE_COLS
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                f"""SELECT {cols} FROM archived_users
                    WHERE username LIKE ? OR full_name LIKE ?
                    ORDER BY archived_at DESC""",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {cols} FROM archived_users ORDER BY archived_at DESC"
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

    def _validate_client_service_fields(self, household_size: int, allergies: str,
                                        religious_restrictions: str) -> tuple[int, str, str]:
        allergies = allergies.strip()
        religious_restrictions = religious_restrictions.strip()
        if (not isinstance(household_size, int) or not 1 <= household_size <= 99 or
                len(allergies) > 1000 or len(religious_restrictions) > 1000):
            raise ValueError("Household size must be 1–99; dietary notes must be under 1,000 characters.")
        return household_size, allergies, religious_restrictions

    def register_pantry_client(self, student_id: str, first_name: str, last_name: str,
                               birth_date: str, graduation_semester: str,
                               enrollment_status: str, username: str,
                               household_size: int = 1, allergies: str = "",
                               religious_restrictions: str = "") -> int:
        student_id = student_id.strip().upper()
        first_name, last_name = first_name.strip(), last_name.strip()
        graduation_semester = graduation_semester.strip()
        household_size, allergies, religious_restrictions = self._validate_client_service_fields(
            household_size, allergies, religious_restrictions
        )
        if (not student_id or len(student_id) > 64 or not first_name or not last_name or
                len(first_name) > 80 or len(last_name) > 80 or not graduation_semester or
                len(graduation_semester) > 40 or enrollment_status not in ("full_time", "part_time")):
            raise ValueError("Complete the student ID, name, graduation term and enrollment type.")
        try:
            born = datetime.date.fromisoformat(birth_date)
        except ValueError as exc:
            raise ValueError("Enter a valid birth date.") from exc
        if born > _utc_date():
            raise ValueError("Birth date cannot be in the future.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM pantry_clients WHERE UPPER(TRIM(student_id)) = ? LIMIT 1",
                (student_id,),
            ).fetchone():
                raise ValueError("A client with this student ID already exists.")
            cursor = conn.execute(
                "INSERT INTO pantry_clients (student_id, first_name, last_name, birth_date, "
                "expected_graduation_semester, enrollment_status, household_size, allergies, "
                "religious_restrictions) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (student_id, first_name, last_name, birth_date, graduation_semester,
                 enrollment_status, household_size, allergies, religious_restrictions),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CLIENT_CREATE', ?)",
                (username, f"client={cursor.lastrowid}"),
            )
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_registered_client(self, client_id: int, student_id: str, first_name: str,
                                 last_name: str, birth_date: str, graduation_semester: str,
                                 enrollment_status: str, username: str,
                                 household_size: int = 1, allergies: str = "",
                                 religious_restrictions: str = "") -> None:
        student_id = student_id.strip().upper()
        first_name, last_name = first_name.strip(), last_name.strip()
        graduation_semester = graduation_semester.strip()
        household_size, allergies, religious_restrictions = self._validate_client_service_fields(
            household_size, allergies, religious_restrictions
        )
        if (not student_id or len(student_id) > 64 or not first_name or not last_name or
                len(first_name) > 80 or len(last_name) > 80 or not graduation_semester or
                len(graduation_semester) > 40 or enrollment_status not in ("full_time", "part_time")):
            raise ValueError("Complete the student ID, name, graduation term and enrollment type.")
        try:
            born = datetime.date.fromisoformat(birth_date)
        except ValueError as exc:
            raise ValueError("Enter a valid birth date.") from exc
        if born > _utc_date():
            raise ValueError("Birth date cannot be in the future.")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            original = conn.execute(
                "SELECT student_id, birth_date, enrollment_status FROM pantry_clients WHERE id = ?",
                (client_id,)
            ).fetchone()
            if not original:
                raise ValueError("Client not found.")
            if conn.execute(
                "SELECT 1 FROM pantry_clients WHERE id != ? AND UPPER(TRIM(student_id)) = ? LIMIT 1",
                (client_id, student_id),
            ).fetchone():
                raise ValueError("A client with this student ID already exists.")
            conn.execute(
                "UPDATE pantry_clients SET student_id = ?, first_name = ?, last_name = ?, "
                "birth_date = ?, expected_graduation_semester = ?, enrollment_status = ?, "
                "household_size = ?, allergies = ?, religious_restrictions = ?, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?",
                (student_id, first_name, last_name, birth_date, graduation_semester,
                 enrollment_status, household_size, allergies, religious_restrictions, client_id),
            )
            if (original["student_id"] != student_id or original["birth_date"] != birth_date or
                    original["enrollment_status"] != enrollment_status):
                previous = conn.execute(
                    "SELECT term FROM client_verifications WHERE client_id = ? ORDER BY id DESC LIMIT 1",
                    (client_id,),
                ).fetchone()
                if previous:
                    conn.execute(
                        "INSERT INTO client_verifications (client_id, term, verified_until, verified_by, status) "
                        "VALUES (?, ?, ?, ?, 'revoked')",
                        (client_id, previous["term"], _utc_date().isoformat(), username),
                    )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CLIENT_EDIT', ?)",
                (username, f"client={client_id}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_client_export_rows(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT client.student_id, client.first_name, client.last_name, client.birth_date, "
            "client.expected_graduation_semester, client.enrollment_status, client.household_size, "
            "client.allergies, client.religious_restrictions, client.is_active, "
            "client.created_at, verification.term AS verified_term, "
            "verification.verified_until, verification.status AS verification_status "
            "FROM pantry_clients client LEFT JOIN client_verifications verification "
            "ON verification.id = (SELECT id FROM client_verifications WHERE client_id = client.id "
            "ORDER BY id DESC LIMIT 1) ORDER BY client.id"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_visit_export_rows(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT visit.id AS visit_id, visit.client_id, client.student_id, "
            "client.first_name, client.last_name, visit.visit_date, visit.items_json, "
            "visit.known_weight_milli_lb, visit.pounds_received, "
            "visit.pending_weight_lines, visit.weight_complete, visit.is_void, "
            "visit.verified_term, visit.fulfillment_type, visit.recorded_by "
            "FROM pantry_visits visit JOIN pantry_clients client ON client.id = visit.client_id "
            "ORDER BY visit.id"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_monthly_service_summary(self, month: str) -> dict:
        try:
            datetime.date.fromisoformat(f"{month}-01")
        except ValueError as exc:
            raise ValueError("Enter a valid month in YYYY-MM format.") from exc
        if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
            raise ValueError("Enter a valid month in YYYY-MM format.")
        conn = self._connect()
        active = conn.execute(
            "SELECT COUNT(*) AS visits, "
            "COALESCE(SUM(COALESCE(known_weight_milli_lb, "
            "CAST(ROUND(COALESCE(pounds_received, 0) * 1000) AS INTEGER))), 0) AS known, "
            "COALESCE(SUM(CASE WHEN weight_complete = 0 THEN 1 ELSE 0 END), 0) AS pending "
            "FROM pantry_visits WHERE SUBSTR(visit_date, 1, 7) = ? AND is_void = 0",
            (month,),
        ).fetchone()
        retired = conn.execute(
            "SELECT visits, known_weight_milli_lb, pending_visits "
            "FROM retired_service_months WHERE month_utc = ?", (month,),
        ).fetchone()
        conn.close()
        return {"month_utc": month, "visits": active["visits"] + (retired["visits"] if retired else 0),
                "known_weight_milli_lb": active["known"] + (retired["known_weight_milli_lb"] if retired else 0),
                "pending_visits": active["pending"] + (retired["pending_visits"] if retired else 0)}

    def get_report_months(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT month FROM (SELECT SUBSTR(timestamp_utc, 1, 7) AS month "
            "FROM inventory_movements WHERE direction IN ('OPENING', 'IN', 'OUT', 'ADJUST') "
            "UNION SELECT month_utc AS month FROM retired_service_months "
            "UNION SELECT SUBSTR(visit_date, 1, 7) AS month FROM pantry_visits "
            "WHERE is_void = 0) ORDER BY month"
        ).fetchall()
        conn.close()
        return [row["month"] for row in rows]

    def _retention_due_on_connection(self, conn: sqlite3.Connection, client_id: int):
        client = conn.execute(
            "SELECT id, student_id, first_name, last_name, is_active, deactivated_at "
            "FROM pantry_clients WHERE id = ?", (client_id,),
        ).fetchone()
        if not client:
            return None
        last_visit = conn.execute(
            "SELECT MAX(DATE(visit_date)) FROM pantry_visits WHERE client_id = ? AND is_void = 0",
            (client_id,),
        ).fetchone()[0]
        anchor = last_visit or client["deactivated_at"]
        if not anchor:
            return None
        try:
            due = _add_calendar_months(datetime.date.fromisoformat(anchor[:10]), 6)
        except ValueError:
            return None
        return dict(client, last_visit=last_visit, due_date=due.isoformat())

    def get_retention_candidates(self, today: datetime.date | None = None,
                                 days_ahead: int = 0) -> list[dict]:
        today = today or _utc_date()
        conn = self._connect()
        ids = [row["id"] for row in conn.execute("SELECT id FROM pantry_clients ORDER BY id")]
        candidates = []
        for client_id in ids:
            candidate = self._retention_due_on_connection(conn, client_id)
            if candidate and datetime.date.fromisoformat(candidate["due_date"]) <= (
                    today + datetime.timedelta(days=days_ahead)):
                candidate["due"] = candidate["due_date"] <= today.isoformat()
                candidate["student_id_last4"] = (candidate.pop("student_id") or "")[-4:]
                candidates.append(candidate)
        conn.close()
        return sorted(candidates, key=lambda candidate: candidate["due_date"])

    def remove_client_identity(self, client_id: int, confirmed_student_id: str,
                               username: str, today: datetime.date | None = None) -> None:
        today = today or _utc_date()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            actor = conn.execute(
                "SELECT role, is_active FROM users WHERE username = ? COLLATE NOCASE",
                (username,),
            ).fetchone()
            if not actor or actor["role"] != "admin" or not actor["is_active"]:
                raise ValueError("Only an active Admin can confirm retention removal.")
            candidate = self._retention_due_on_connection(conn, client_id)
            if not candidate:
                raise ValueError("This client has no retention deadline yet.")
            if datetime.date.fromisoformat(candidate["due_date"]) > today:
                raise ValueError("The six-month deadline has not arrived.")
            if not confirmed_student_id.strip() or candidate["student_id"] != confirmed_student_id.strip().upper():
                raise ValueError("Confirm the student's exact ID before removing their record.")
            if conn.execute(
                "SELECT 1 FROM pantry_carts WHERE client_id = ? AND status = 'DRAFT' LIMIT 1",
                (client_id,),
            ).fetchone():
                raise ValueError("Finish or cancel this client's open distribution before retention removal.")
            totals = conn.execute(
                "SELECT SUBSTR(visit_date, 1, 7) AS month_utc, COUNT(*) AS visits, "
                "COALESCE(SUM(COALESCE(known_weight_milli_lb, "
                "CAST(ROUND(COALESCE(pounds_received, 0) * 1000) AS INTEGER))), 0) AS known, "
                "COALESCE(SUM(CASE WHEN weight_complete = 0 THEN 1 ELSE 0 END), 0) AS pending "
                "FROM pantry_visits WHERE client_id = ? AND is_void = 0 "
                "GROUP BY SUBSTR(visit_date, 1, 7)", (client_id,),
            ).fetchall()
            for row in totals:
                if not row["month_utc"] or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", row["month_utc"]):
                    raise ValueError("Visit month is invalid; review this record before removing it.")
                conn.execute(
                    "INSERT INTO retired_service_months "
                    "(month_utc, visits, known_weight_milli_lb, pending_visits) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(month_utc) DO UPDATE SET visits = visits + excluded.visits, "
                    "known_weight_milli_lb = known_weight_milli_lb + excluded.known_weight_milli_lb, "
                    "pending_visits = pending_visits + excluded.pending_visits",
                    (row["month_utc"], row["visits"], row["known"], row["pending"]),
                )
            conn.execute(
                "UPDATE inventory_movements SET client_id = NULL, visit_id = NULL "
                "WHERE client_id = ? OR visit_id IN "
                "(SELECT id FROM pantry_visits WHERE client_id = ?)", (client_id, client_id),
            )
            conn.execute("UPDATE pantry_carts SET client_id = NULL WHERE client_id = ?", (client_id,))
            conn.execute("DELETE FROM pantry_visits WHERE client_id = ?", (client_id,))
            conn.execute("DELETE FROM client_verifications WHERE client_id = ?", (client_id,))
            conn.execute("DELETE FROM pantry_clients WHERE id = ?", (client_id,))
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CLIENT_RETENTION_REMOVE', ?)",
                (username, f"visit_count={sum(row['visits'] for row in totals)}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list_private_clients(self):
        conn = self._connect()
        rows = conn.execute(
            "SELECT id, first_name, last_name, student_id, is_active "
            "FROM pantry_clients ORDER BY last_name, first_name"
        ).fetchall()
        conn.close()
        return [dict(id=row["id"], first_name=row["first_name"], last_name=row["last_name"],
                     student_id_last4=(row["student_id"] or "")[-4:], is_active=row["is_active"])
                for row in rows]

    def get_client_eligibility(self, client_id: int):
        conn = self._connect()
        row = conn.execute(
            "SELECT verification.term, verification.verified_at, verification.verified_until, "
            "verification.verified_by, verification.status "
            "FROM client_verifications verification WHERE verification.client_id = ? "
            "ORDER BY verification.id DESC LIMIT 1", (client_id,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def verify_client_term(self, client_id: int, term: str, verified_until: str,
                           username: str) -> None:
        term = " ".join(term.split()).title()
        if not term or len(term) > 40:
            raise ValueError("Enter the verified academic term.")
        try:
            expiry = datetime.date.fromisoformat(verified_until)
        except ValueError as exc:
            raise ValueError("Enter a valid semester end date.") from exc
        if expiry < _utc_date() or expiry > _utc_date() + datetime.timedelta(days=185):
            raise ValueError("Verification must expire during the current semester (within 185 days).")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            client = conn.execute(
                "SELECT id, is_active, birth_date, student_id, expected_graduation_semester "
                "FROM pantry_clients WHERE id = ?",
                (client_id,),
            ).fetchone()
            if not client or not client["is_active"] or not client["birth_date"] or not client["student_id"] or not client["expected_graduation_semester"]:
                raise ValueError("Complete an active client's intake record before verifying enrollment.")
            conn.execute(
                "INSERT INTO client_verifications (client_id, term, verified_until, verified_by, status) "
                "VALUES (?, ?, ?, ?, 'verified')",
                (client_id, term, verified_until, username),
            )
            conn.execute(
                "UPDATE pantry_clients SET semester = ?, updated_at = datetime('now', 'localtime') "
                "WHERE id = ?", (term, client_id),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CLIENT_VERIFY', ?)",
                (username, f"client={client_id} term={term} valid_until={verified_until}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_client_record_active(self, client_id: int, active: bool, username: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            client = conn.execute(
                "SELECT id, is_active, deactivated_at FROM pantry_clients WHERE id = ?", (client_id,)
            ).fetchone()
            if not client:
                raise ValueError("Client not found.")
            deactivated_at = None if active else client["deactivated_at"] or _utc_date().isoformat()
            conn.execute(
                "UPDATE pantry_clients SET is_active = ?, deactivated_at = ?, "
                "updated_at = datetime('now', 'localtime') WHERE id = ?",
                (int(active), deactivated_at, client_id),
            )
            if not active and client["is_active"]:
                previous = conn.execute(
                    "SELECT term, status FROM client_verifications WHERE client_id = ? "
                    "ORDER BY id DESC LIMIT 1", (client_id,),
                ).fetchone()
                if previous and previous["status"] == "verified":
                    conn.execute(
                        "INSERT INTO client_verifications "
                        "(client_id, term, verified_until, verified_by, status) "
                        "VALUES (?, ?, ?, ?, 'revoked')",
                        (client_id, previous["term"], _utc_date().isoformat(), username),
                    )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CLIENT_STATUS', ?)",
                (username, f"client={client_id} active={int(active)}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def revoke_client_term(self, client_id: int, username: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT term, status FROM client_verifications WHERE client_id = ? ORDER BY id DESC LIMIT 1",
                (client_id,),
            ).fetchone()
            if not previous or previous["status"] != "verified":
                raise ValueError("This client has no active term verification to revoke.")
            conn.execute(
                "INSERT INTO client_verifications (client_id, term, verified_until, verified_by, status) "
                "VALUES (?, ?, ?, ?, 'revoked')",
                (client_id, previous["term"], _utc_date().isoformat(), username),
            )
            conn.execute(
                "INSERT INTO activity_log (username, action, detail) VALUES (?, 'CLIENT_REVOKE', ?)",
                (username, f"client={client_id}"),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def is_client_eligible(self, client_id: int) -> bool:
        conn = self._connect()
        row = conn.execute(
            "SELECT client.is_active, client.student_id, client.birth_date, "
            "client.expected_graduation_semester, verification.status, verification.verified_until "
            "FROM pantry_clients client LEFT JOIN client_verifications verification "
            "ON verification.id = (SELECT id FROM client_verifications "
            "WHERE client_id = client.id ORDER BY id DESC LIMIT 1) "
            "WHERE client.id = ?", (client_id,),
        ).fetchone()
        conn.close()
        return bool(row and row["is_active"] and row["student_id"] and row["birth_date"]
                    and row["expected_graduation_semester"] and row["status"] == "verified" and row["verified_until"] >= _utc_date().isoformat())

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
                             recorded_by: str, notes: str = "", items_json: str = "[]") -> int:
        conn = self._connect()
        cur = conn.execute(
            """INSERT INTO pantry_visits
                   (client_id, pounds_received, recorded_by, notes, items_json)
               VALUES (?, ?, ?, ?, ?)""",
            (client_id, pounds_received, recorded_by, notes, items_json),
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

    def get_recent_movements(self, limit: int = 12):
        conn = self._connect()
        rows = conn.execute(
            "SELECT movement.item_name, movement.recorded_by AS username, "
            "movement.timestamp_utc AS timestamp, ABS(movement.quantity_delta) AS quantity, "
            "CASE WHEN movement.reverses_movement_id IS NOT NULL THEN 'UNDO' "
            "WHEN movement.direction = 'OUT' AND EXISTS "
            "(SELECT 1 FROM inventory_movements reversal "
            "WHERE reversal.reverses_movement_id = movement.id) THEN 'VOIDED_OUT' "
            "ELSE movement.direction END AS transaction_type "
            "FROM inventory_movements movement ORDER BY movement.id DESC LIMIT ?", (limit,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_recent_transactions(self, limit: int = 12):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY timestamp DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_recent_transactions_by_user(self, username: str, limit: int = 5):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM transactions WHERE username = ? AND transaction_type = 'SCAN_IN' "
            "ORDER BY timestamp DESC, id DESC LIMIT ?", (username, limit)
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
        limit: int | None = None,
    ):
        """Return transactions matching the filters, newest first.

        `limit` is opt-in. UI views should pass a bound so a multi-year
        transaction log doesn't blow up the window; CSV exports and
        Ava's context builder pass their own explicit caps.
        """
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
        if isinstance(limit, int) and limit > 0:
            query += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def clear_all_transactions(self) -> None:
        """Delete all transaction history from the database.
        
        WARNING: This action cannot be undone!
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM transactions")
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Weight Tracking Methods
    # ------------------------------------------------------------------

    def get_current_month_year(self) -> str:
        """Get current month/year string (e.g., 'August 2024')."""
        from datetime import datetime
        return datetime.now().strftime("%B %Y")

    def update_item_weights(self, item_id: int, current_pounds: float, 
                           donated_pounds: float, discarded_pounds: float,
                           notes: str = "", username: str = ""):
        """Update weight fields for an item and calculate remaining."""
        conn = self._connect()
        try:
            # Calculate remaining
            calculated_remaining = current_pounds + donated_pounds - discarded_pounds
            
            # Update inventory_items
            conn.execute("""
                UPDATE inventory_items 
                SET current_pounds = ?, donated_pounds = ?, discarded_pounds = ?,
                    calculated_remaining = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            """, (current_pounds, donated_pounds, discarded_pounds, 
                  calculated_remaining, item_id))
            
            conn.commit()
            return True, "Weights updated successfully"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def archive_monthly_weights(self, month_year: str, username: str = ""):
        """Archive all current weights to weight_history for a specific month."""
        conn = self._connect()
        try:
            # Get all items with weights
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, current_pounds, donated_pounds, discarded_pounds,
                       calculated_remaining FROM inventory_items
                WHERE current_pounds > 0 OR donated_pounds > 0 OR discarded_pounds > 0
            """)
            items = cursor.fetchall()
            
            # Archive each item's weights
            for item_id, curr, donated, discarded, remaining in items:
                conn.execute("""
                    INSERT OR REPLACE INTO weight_history
                    (item_id, month_year, current_pounds, donated_pounds, 
                     discarded_pounds, calculated_remaining, recorded_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (item_id, month_year, curr, donated, discarded, remaining, username))
            
            conn.commit()
            return True, f"Archived weights for {month_year}"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def get_monthly_weights(self, month_year: str = None) -> list:
        """Get all weights for a specific month (or current month if not specified)."""
        if month_year is None:
            month_year = self.get_current_month_year()
        
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT wh.id, wh.item_id, i.item_name, i.category, i.storage_location,
                       wh.current_pounds, wh.donated_pounds, wh.discarded_pounds,
                       wh.calculated_remaining, wh.recorded_date, wh.recorded_by
                FROM weight_history wh
                JOIN inventory_items i ON wh.item_id = i.id
                WHERE wh.month_year = ?
                ORDER BY i.item_name
            """, (month_year,))
            
            rows = cursor.fetchall()
            return [dict(zip([d[0] for d in cursor.description], row)) for row in rows]
        except Exception:
            return []
        finally:
            conn.close()

    def get_all_months(self) -> list:
        """Get all months with weight history data."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT month_year FROM weight_history
                ORDER BY month_year DESC
            """)
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    def get_weight_summary(self, month_year: str = None) -> dict:
        """Get summary statistics for weights in a month."""
        if month_year is None:
            month_year = self.get_current_month_year()
        
        conn = self._connect()
        try:
            cursor = conn.cursor()
            current_month = self.get_current_month_year()
            
            # For current month, get from inventory_items
            if month_year == current_month:
                cursor.execute("""
                    SELECT 
                        SUM(current_pounds) as total_current,
                        SUM(donated_pounds) as total_donated,
                        SUM(discarded_pounds) as total_discarded,
                        SUM(calculated_remaining) as total_remaining,
                        COUNT(*) as item_count
                    FROM inventory_items
                    WHERE current_pounds > 0 OR donated_pounds > 0 OR discarded_pounds > 0
                """)
            else:
                # For past months, get from weight_history
                cursor.execute("""
                    SELECT 
                        SUM(current_pounds) as total_current,
                        SUM(donated_pounds) as total_donated,
                        SUM(discarded_pounds) as total_discarded,
                        SUM(calculated_remaining) as total_remaining,
                        COUNT(*) as item_count
                    FROM weight_history
                    WHERE month_year = ?
                """, (month_year,))
            
            row = cursor.fetchone()
            if row and row[4]:  # Check if item_count > 0
                return {
                    "total_current": float(row[0] or 0.0),
                    "total_donated": float(row[1] or 0.0),
                    "total_discarded": float(row[2] or 0.0),
                    "total_remaining": float(row[3] or 0.0),
                    "item_count": int(row[4] or 0)
                }
            return {
                "total_current": 0.0,
                "total_donated": 0.0,
                "total_discarded": 0.0,
                "total_remaining": 0.0,
                "item_count": 0
            }
        except Exception as e:
            print(f"Error getting weight summary: {e}")
            return {
                "total_current": 0.0,
                "total_donated": 0.0,
                "total_discarded": 0.0,
                "total_remaining": 0.0,
                "item_count": 0
            }
        finally:
            conn.close()
