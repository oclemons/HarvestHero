"""Physical pantry layout and legacy stock migration tests."""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import Database


class ShelfLayout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "inventory.db")
        self.db = Database(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_empty_shelf_is_listed(self):
        section_id = self.db.create_pantry_section("Canned goods")
        shelf_id = self.db.create_pantry_shelf(section_id, "Shelf A")
        self.assertEqual(self.db.get_pantry_layout()[0]["shelves"][0]["id"], shelf_id)
        self.assertEqual(self.db.get_pantry_layout()[0]["shelves"][0]["units"], 0)

    def test_pre_layout_database_keeps_legacy_counts(self):
        old_path = str(Path(self.tmp.name) / "legacy.db")
        conn = sqlite3.connect(old_path)
        conn.execute("CREATE TABLE inventory_items (id INTEGER PRIMARY KEY, barcode TEXT UNIQUE, "
                     "item_name TEXT, current_quantity INTEGER, storage_location TEXT)")
        conn.execute("INSERT INTO inventory_items VALUES (1, 'LEGACY', 'Beans', 9, 'Section 2 Shelf A')")
        conn.commit()
        conn.close()
        upgraded = Database(old_path)
        self.assertEqual(upgraded.get_item_shelf_stock(1)[0]["quantity"], 9)
        self.assertEqual(upgraded.get_item_shelf_stock(1)[0]["section_name"], "Unassigned")
        self.assertEqual(upgraded.get_item_by_id(1)["current_quantity"], 9)

    def test_legacy_staff_is_not_promoted_to_admin(self):
        old_path = str(Path(self.tmp.name) / "legacy_roles.db")
        conn = sqlite3.connect(old_path)
        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
                salt TEXT, role TEXT CHECK(role IN ('admin', 'staff')),
                created_at TEXT, is_active INTEGER DEFAULT 1
            );
            INSERT INTO users VALUES (1, 'old_staff', 'hash', 'salt', 'staff', '', 1);
        """)
        conn.close()
        upgraded = Database(old_path)
        self.assertEqual(upgraded.get_user("old_staff")["role"], "student")

    def test_prechange_visit_migration_preserves_items_and_client(self):
        old_path = str(Path(self.tmp.name) / "visits.db")
        conn = sqlite3.connect(old_path)
        conn.executescript("""
            CREATE TABLE pantry_clients (
                id INTEGER PRIMARY KEY, student_id TEXT, first_name TEXT,
                last_name TEXT, enrollment_status TEXT, is_active INTEGER
            );
            CREATE TABLE pantry_visits (
                id INTEGER PRIMARY KEY, client_id INTEGER, visit_date TEXT,
                pounds_received REAL, items_json TEXT, notes TEXT, recorded_by TEXT,
                FOREIGN KEY(client_id) REFERENCES pantry_clients(id)
            );
            INSERT INTO pantry_clients VALUES (1, 'S123', 'Avery', 'Rivera', 'full_time', 1);
            INSERT INTO pantry_visits VALUES
                (1, 1, '2026-01-01', 1.25, '[{"name":"Rice"}]', '', 'admin');
        """)
        conn.close()
        upgraded = Database(old_path)
        client = upgraded.get_pantry_client(1)
        visit = upgraded.get_client_visits(1)[0]
        self.assertEqual(client["student_id"], "S123")
        self.assertIsNone(client["birth_date"])
        self.assertEqual(client["household_size"], 1)
        self.assertEqual(client["allergies"], "")
        self.assertEqual(client["religious_restrictions"], "")
        self.assertEqual(visit["items_json"], '[{"name":"Rice"}]')
        self.assertIsNone(visit["known_weight_milli_lb"])
        self.assertEqual(visit["weight_complete"], 0)

    def test_existing_review_carts_upgrade_to_immediate_mode_schema(self):
        old_path = str(Path(self.tmp.name) / "review_carts.db")
        conn = sqlite3.connect(old_path)
        conn.executescript("""
            CREATE TABLE pantry_carts (
                id TEXT PRIMARY KEY, owner_id INTEGER, direction TEXT, client_id INTEGER,
                status TEXT DEFAULT 'DRAFT', created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT '', completed_at TEXT
            );
            CREATE TABLE pantry_visits (
                id INTEGER PRIMARY KEY, client_id INTEGER, visit_date TEXT,
                pounds_received REAL, items_json TEXT, known_weight_milli_lb INTEGER,
                pending_weight_lines INTEGER DEFAULT 0, weight_complete INTEGER DEFAULT 0,
                cart_id TEXT, notes TEXT, recorded_by TEXT,
                FOREIGN KEY(client_id) REFERENCES pantry_clients(id) ON DELETE CASCADE
            );
            CREATE TABLE inventory_movements (
                id INTEGER PRIMARY KEY, cart_id TEXT, item_id INTEGER, item_name TEXT,
                shelf_id INTEGER, client_id INTEGER, visit_id INTEGER,
                direction TEXT, quantity_delta INTEGER, weight_milli_lb INTEGER,
                weight_override_reason TEXT, recorded_by TEXT, timestamp_utc TEXT
            );
            INSERT INTO pantry_carts (id, owner_id, direction, status)
            VALUES ('existing-cart', 1, 'OUT', 'DRAFT');
        """)
        conn.close()
        Database(old_path)
        conn = sqlite3.connect(old_path)
        try:
            self.assertIn("mode", {row[1] for row in conn.execute("PRAGMA table_info(pantry_carts)")})
            self.assertIn("fulfillment_type", {row[1] for row in conn.execute("PRAGMA table_info(pantry_carts)")})
            self.assertIn("is_void", {row[1] for row in conn.execute("PRAGMA table_info(pantry_visits)")})
            self.assertIn("verified_term", {row[1] for row in conn.execute("PRAGMA table_info(pantry_visits)")})
            self.assertIn("scan_request_id", {row[1] for row in conn.execute("PRAGMA table_info(inventory_movements)")})
            self.assertIn("reverses_movement_id", {row[1] for row in conn.execute("PRAGMA table_info(inventory_movements)")})
            self.assertEqual(conn.execute("SELECT mode, fulfillment_type FROM pantry_carts "
                                          "WHERE id='existing-cart'").fetchone(),
                             ("REVIEW", "in_person"))
        finally:
            conn.close()

    def test_legacy_weight_is_converted_to_fixed_precision(self):
        self.db.add_item("WEIGHT1", "Oats", "Dry goods", 0, 0, "")
        conn = sqlite3.connect(self.path)
        conn.execute("UPDATE inventory_items SET weight_per_unit = 1.234 WHERE barcode = 'WEIGHT1'")
        conn.execute("DELETE FROM app_settings WHERE key='unit_weight_migrated'")
        conn.commit()
        conn.close()
        self.db = Database(self.path)
        self.assertEqual(self.db.get_item_by_barcode("WEIGHT1")["unit_weight_milli_lb"], 1234)

    def test_existing_quantity_migrates_to_unassigned_once(self):
        self.db.add_item("LEGACY1", "Rice", "Dry goods", 7, 1, "")
        conn = sqlite3.connect(self.path)
        conn.execute("DELETE FROM app_settings WHERE key='shelf_stock_migrated'")
        conn.commit()
        conn.close()
        self.db = Database(self.path)
        item = self.db.get_item_by_barcode("LEGACY1")
        allocations = self.db.get_item_shelf_stock(item["id"])
        self.assertEqual(sum(row["quantity"] for row in allocations), 7)
        self.assertEqual(allocations[0]["shelf_name"], "Unassigned")
        self.db = Database(self.path)
        self.assertEqual(self.db.get_item_shelf_stock(item["id"]), allocations)

    def test_item_starts_on_selected_shelf_with_known_unit_weight(self):
        section_id = self.db.create_pantry_section("Canned goods")
        shelf_id = self.db.create_pantry_shelf(section_id, "Shelf A")
        item_id = self.db.create_item_on_shelf(
            "CORN", "Corn", "Canned", 12, 4, shelf_id, "admin", 625
        )
        item = self.db.get_item_by_id(item_id)
        self.assertEqual(item["current_quantity"], 12)
        self.assertEqual(item["unit_weight_milli_lb"], 625)
        self.assertEqual(self.db.get_item_shelf_stock(item_id)[0]["quantity"], 12)
        self.assertEqual(self.db.get_pantry_layout()[0]["shelves"][0]["units"], 12)

    def test_two_foods_share_a_shelf_and_renames_preserve_stock(self):
        section_id = self.db.create_pantry_section("Section 3")
        shelf_id = self.db.create_pantry_shelf(section_id, "Shelf 1")
        veg_id = self.db.create_item_on_shelf("VEGS", "Mixed vegetables", "Canned", 4, 0,
                                               shelf_id, "admin")
        potato_id = self.db.create_item_on_shelf("POTATO", "Potatoes", "Produce", 7, 0,
                                                  shelf_id, "admin")
        shelf = self.db.get_pantry_layout(include_items=True)[0]["shelves"][0]
        self.assertEqual(shelf["units"], 11)
        self.assertEqual({item["item_name"] for item in shelf["items"]},
                         {"Mixed vegetables", "Potatoes"})
        self.db.rename_pantry_section(section_id, "Section 3 East", "admin")
        self.db.update_pantry_shelf(shelf_id, "Shelf 1A", True, "admin")
        self.assertEqual(self.db.get_item_by_id(veg_id)["current_quantity"], 4)
        self.assertEqual(self.db.get_item_by_id(potato_id)["current_quantity"], 7)
        renamed = self.db.get_pantry_layout(include_items=True)[0]["shelves"][0]
        self.assertEqual(renamed["name"], "Shelf 1A")
        self.assertEqual(renamed["is_overflow"], 1)
        self.assertIn("Section 3 East / Shelf 1A", self.db.get_item_locations([veg_id])[veg_id])

    def test_same_shelf_label_is_unique_per_section_not_per_item(self):
        first = self.db.create_pantry_section("Section 3")
        shelf_id = self.db.create_pantry_shelf(first, "Shelf 1")
        with self.assertRaises(ValueError):
            self.db.create_pantry_shelf(first, "shelf 1")
        second = self.db.create_pantry_section("Section 4")
        self.db.create_pantry_shelf(second, "Shelf 1")
        other = self.db.create_pantry_shelf(first, "Shelf 2")
        with self.assertRaises(ValueError):
            self.db.update_pantry_shelf(other, "Shelf 1", False, "admin")
        self.assertEqual(self.db.get_item_shelf_stock(999), [])
        self.assertEqual(shelf_id, self.db.get_pantry_layout()[0]["shelves"][0]["id"])

    def test_split_shelves_and_transfer_preserve_total(self):
        section_id = self.db.create_pantry_section("Dry goods")
        first = self.db.create_pantry_shelf(section_id, "Shelf A")
        second = self.db.create_pantry_shelf(section_id, "Overflow", is_overflow=True)
        self.db.add_item("RICE", "Rice", "Dry goods", 0, 0, "")
        item = self.db.get_item_by_barcode("RICE")
        self.db.adjust_shelf_stock(item["id"], first, 10, "admin", "Opening count")
        self.db.transfer_shelf_stock(item["id"], first, second, 4, "admin")
        stock = {row["shelf_id"]: row["quantity"] for row in self.db.get_item_shelf_stock(item["id"])
                 if row["quantity"] > 0}
        self.assertEqual(stock, {first: 6, second: 4})
        self.assertEqual(self.db.get_item_by_id(item["id"])["current_quantity"], 10)

    def test_legacy_stock_writers_keep_shelf_balances_in_sync(self):
        self.db.add_item("LEGACY", "Beans", "Canned", 3, 1, "")
        item = self.db.get_item_by_barcode("LEGACY")
        self.db.set_stock(item["id"], 5)
        self.db.adjust_stock("LEGACY", -2)
        allocations = self.db.get_item_shelf_stock(item["id"])
        self.assertEqual(sum(row["quantity"] for row in allocations), 3)
        self.assertEqual(self.db.get_item_by_id(item["id"])["current_quantity"], 3)
        added, updated, errors = self.db.batch_upsert_inventory([
            {"barcode": "NEW", "item_name": "Peas", "current_quantity": 4},
            {"barcode": "LEGACY", "item_name": "Beans", "current_quantity": 6},
        ])
        self.assertEqual((added, updated, errors), (1, 1, []))
        for barcode in ("NEW", "LEGACY"):
            row = self.db.get_item_by_barcode(barcode)
            self.assertEqual(sum(s["quantity"] for s in self.db.get_item_shelf_stock(row["id"])),
                             row["current_quantity"])

    def test_failed_transfer_does_not_change_stock(self):
        section_id = self.db.create_pantry_section("Dry goods")
        first = self.db.create_pantry_shelf(section_id, "Shelf A")
        second = self.db.create_pantry_shelf(section_id, "Shelf B")
        self.db.add_item("RICE", "Rice", "Dry goods", 0, 0, "")
        item = self.db.get_item_by_barcode("RICE")
        self.db.adjust_shelf_stock(item["id"], first, 2, "admin", "Opening count")
        with self.assertRaises(ValueError):
            self.db.transfer_shelf_stock(item["id"], first, second, 3, "admin")
        self.assertEqual(self.db.get_item_shelf_stock(item["id"])[0]["quantity"], 2)
        self.assertEqual(self.db.get_item_by_id(item["id"])["current_quantity"], 2)


if __name__ == "__main__":
    unittest.main()
