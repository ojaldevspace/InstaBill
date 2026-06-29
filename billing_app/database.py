"""
database.py - SQLite database setup and all query functions
"""
import sqlite3
import os
import sys
from datetime import datetime


def _get_db_path() -> str:
    """
    Return a persistent path for billing.db that survives across app restarts.

    - Windows (.exe or raw): %APPDATA%\\InstaBill\\billing.db
    - macOS:                 ~/Library/Application Support/InstaBill/billing.db
    - Linux:                 ~/.local/share/InstaBill/billing.db

    This avoids the PyInstaller temp-folder problem where __file__ points to
    a directory that is deleted when the .exe closes.
    """
    app_name = "InstaBill"

    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME",
                              os.path.join(os.path.expanduser("~"), ".local", "share"))

    data_dir = os.path.join(base, app_name)
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "billing.db")


DB_PATH = _get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create all tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            unit_price REAL NOT NULL DEFAULT 0.0,
            unit TEXT DEFAULT 'pcs',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            bill_number TEXT NOT NULL UNIQUE,
            bill_date TEXT NOT NULL,
            due_date TEXT,
            subtotal REAL DEFAULT 0.0,
            tax_percent REAL DEFAULT 0.0,
            tax_amount REAL DEFAULT 0.0,
            total REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            description TEXT,
            quantity REAL NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL DEFAULT 0.0,
            amount REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_method TEXT DEFAULT 'cash',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────── CLIENT QUERIES ───────────────────────────

def get_all_clients():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY business_name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_client(client_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_client(business_name, contact_person, phone, email, address):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO clients (business_name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
        (business_name, contact_person, phone, email, address)
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_client(client_id, business_name, contact_person, phone, email, address):
    conn = get_connection()
    conn.execute(
        "UPDATE clients SET business_name=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
        (business_name, contact_person, phone, email, address, client_id)
    )
    conn.commit()
    conn.close()


def delete_client(client_id):
    conn = get_connection()
    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
    conn.commit()
    conn.close()


def get_client_balance(client_id):
    """Return total billed and total paid for a client."""
    conn = get_connection()
    billed = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM bills WHERE client_id=?", (client_id,)
    ).fetchone()[0]
    paid = conn.execute(
        "SELECT COALESCE(SUM(p.amount),0) FROM payments p "
        "JOIN bills b ON p.bill_id=b.id WHERE b.client_id=?", (client_id,)
    ).fetchone()[0]
    conn.close()
    return billed, paid


# ─────────────────────────── INVENTORY QUERIES ───────────────────────────

def get_all_inventory():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM inventory_items ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_inventory_item(name, description, unit_price, unit):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO inventory_items (name, description, unit_price, unit) VALUES (?,?,?,?)",
        (name, description, unit_price, unit)
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_inventory_item(item_id, name, description, unit_price, unit):
    conn = get_connection()
    conn.execute(
        "UPDATE inventory_items SET name=?, description=?, unit_price=?, unit=? WHERE id=?",
        (name, description, unit_price, unit, item_id)
    )
    conn.commit()
    conn.close()


def delete_inventory_item(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# ─────────────────────────── BILL QUERIES ───────────────────────────

def generate_bill_number():
    """Generate bill number like BILL-202501-001."""
    now = datetime.now()
    prefix = f"BILL-{now.strftime('%Y%m')}-"
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM bills WHERE bill_number LIKE ?", (prefix + "%",)
    ).fetchone()
    count = row[0] + 1
    conn.close()
    return f"{prefix}{count:03d}"


def add_bill(client_id, bill_number, bill_date, due_date, subtotal,
             tax_percent, tax_amount, total, status, notes, items):
    """Insert bill and its items. Returns new bill id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO bills (client_id, bill_number, bill_date, due_date,
           subtotal, tax_percent, tax_amount, total, status, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (client_id, bill_number, bill_date, due_date,
         subtotal, tax_percent, tax_amount, total, status, notes)
    )
    bill_id = c.lastrowid
    for item in items:
        c.execute(
            """INSERT INTO bill_items (bill_id, item_name, description, quantity, unit_price, amount)
               VALUES (?,?,?,?,?,?)""",
            (bill_id, item["item_name"], item.get("description", ""),
             item["quantity"], item["unit_price"], item["amount"])
        )
    conn.commit()
    conn.close()
    return bill_id


def get_bill(bill_id):
    conn = get_connection()
    bill = conn.execute("SELECT * FROM bills WHERE id=?", (bill_id,)).fetchone()
    conn.close()
    return dict(bill) if bill else None


def get_bills_for_client(client_id, month=None, year=None):
    conn = get_connection()
    query = "SELECT * FROM bills WHERE client_id=?"
    params = [client_id]
    if month and year:
        query += " AND strftime('%m', bill_date)=? AND strftime('%Y', bill_date)=?"
        params += [f"{int(month):02d}", str(year)]
    query += " ORDER BY bill_date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bill_items(bill_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM bill_items WHERE bill_id=? ORDER BY id", (bill_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_bill(bill_id):
    conn = get_connection()
    conn.execute("DELETE FROM bills WHERE id=?", (bill_id,))
    conn.commit()
    conn.close()


def update_bill_status(bill_id, status):
    conn = get_connection()
    conn.execute("UPDATE bills SET status=? WHERE id=?", (status, bill_id))
    conn.commit()
    conn.close()


# ─────────────────────────── PAYMENT QUERIES ───────────────────────────

def add_payment(bill_id, amount, payment_date, payment_method, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO payments (bill_id, amount, payment_date, payment_method, notes)
           VALUES (?,?,?,?,?)""",
        (bill_id, amount, payment_date, payment_method, notes)
    )
    conn.commit()
    new_id = c.lastrowid

    # Recalculate bill status
    total_paid = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE bill_id=?", (bill_id,)
    ).fetchone()[0]
    bill_total = conn.execute(
        "SELECT total FROM bills WHERE id=?", (bill_id,)
    ).fetchone()[0]

    if total_paid >= bill_total:
        status = "paid"
    elif total_paid > 0:
        status = "partial"
    else:
        status = "pending"
    conn.execute("UPDATE bills SET status=? WHERE id=?", (status, bill_id))
    conn.commit()
    conn.close()
    return new_id


def get_payments_for_bill(bill_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM payments WHERE bill_id=? ORDER BY payment_date DESC", (bill_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_paid_amount(bill_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE bill_id=?", (bill_id,)
    ).fetchone()
    conn.close()
    return row[0]


def delete_payment(payment_id):
    conn = get_connection()
    # Get bill_id before deleting
    row = conn.execute("SELECT bill_id FROM payments WHERE id=?", (payment_id,)).fetchone()
    if row:
        bill_id = row[0]
        conn.execute("DELETE FROM payments WHERE id=?", (payment_id,))
        # Recalculate status
        total_paid = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE bill_id=?", (bill_id,)
        ).fetchone()[0]
        bill_total = conn.execute(
            "SELECT total FROM bills WHERE id=?", (bill_id,)
        ).fetchone()[0]
        if total_paid >= bill_total:
            status = "paid"
        elif total_paid > 0:
            status = "partial"
        else:
            status = "pending"
        conn.execute("UPDATE bills SET status=? WHERE id=?", (status, bill_id))
        conn.commit()
    conn.close()


# ─────────────────────────── LEDGER QUERIES ───────────────────────────

def get_ledger_summary(client_id, month=None, year=None):
    """Returns total_billed, total_paid, balance for given filters."""
    conn = get_connection()
    bill_query = "SELECT id, total FROM bills WHERE client_id=?"
    params = [client_id]
    if month and year:
        bill_query += " AND strftime('%m', bill_date)=? AND strftime('%Y', bill_date)=?"
        params += [f"{int(month):02d}", str(year)]

    bills = conn.execute(bill_query, params).fetchall()
    total_billed = sum(b["total"] for b in bills)
    bill_ids = [b["id"] for b in bills]

    total_paid = 0.0
    if bill_ids:
        placeholders = ",".join("?" * len(bill_ids))
        total_paid = conn.execute(
            f"SELECT COALESCE(SUM(amount),0) FROM payments WHERE bill_id IN ({placeholders})",
            bill_ids
        ).fetchone()[0]

    conn.close()
    return total_billed, total_paid, total_billed - total_paid
