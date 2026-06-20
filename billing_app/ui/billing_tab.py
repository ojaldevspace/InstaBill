"""
billing_tab.py - Bill creation UI.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import database as db
from ui.receipt_view import ReceiptViewWindow

C_HEADER  = "#1a3a5c"
C_BG      = "#f4f7fb"
C_WHITE   = "#ffffff"
C_GREEN   = "#27ae60"
C_RED     = "#e74c3c"
C_ORANGE  = "#e67e22"
C_BORDER  = "#d0dae8"
CURRENCY  = "₹"


def fmt_currency(v):
    return f"{CURRENCY}{float(v):,.2f}"


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def display_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return d


def parse_date(d):
    """Accept DD/MM/YYYY or YYYY-MM-DD, return YYYY-MM-DD."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return d


class BillingTab:
    def __init__(self, parent: ttk.Frame, app):
        self.app = app
        self._bill_rows = []   # list of dicts representing line items
        self._editing_bill_id = None
        self._build(parent)
        self.refresh_clients()
        self.refresh_inventory()
        self._reset_bill_number()

    # ── Build ────────────────────────────────────────────────────

    def _build(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        canvas = tk.Canvas(parent, bg=C_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical",
                                  command=canvas.yview)
        self._scroll_frame = ttk.Frame(canvas)
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        scrollbar.grid(row=0, column=1, sticky="ns")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        # Bind mousewheel
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        outer = self._scroll_frame
        outer.columnconfigure(0, weight=1)

        # ── Section 1: Bill header ────────────────────────────────
        hdr = ttk.LabelFrame(outer, text="Bill Information", padding=12)
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        hdr.columnconfigure(1, weight=1)
        hdr.columnconfigure(3, weight=1)

        # Row 0: Client / Bill Number
        ttk.Label(hdr, text="Client *").grid(row=0, column=0, sticky="w",
                                              padx=(0, 8), pady=5)
        self.client_var = tk.StringVar()
        self.client_cb = ttk.Combobox(hdr, textvariable=self.client_var,
                                      state="readonly", width=32)
        self.client_cb.grid(row=0, column=1, sticky="ew", pady=5)

        ttk.Label(hdr, text="Bill Number").grid(row=0, column=2, sticky="w",
                                                padx=(16, 8), pady=5)
        self.bill_num_var = tk.StringVar()
        bill_num_entry = ttk.Entry(hdr, textvariable=self.bill_num_var,
                                   state="readonly", width=20)
        bill_num_entry.grid(row=0, column=3, sticky="w", pady=5)

        # Row 1: Bill Date / Due Date
        ttk.Label(hdr, text="Bill Date *").grid(row=1, column=0, sticky="w",
                                                 padx=(0, 8), pady=5)
        self.bill_date_var = tk.StringVar(
            value=datetime.now().strftime("%d/%m/%Y"))
        ttk.Entry(hdr, textvariable=self.bill_date_var, width=14).grid(
            row=1, column=1, sticky="w", pady=5)

        ttk.Label(hdr, text="Due Date").grid(row=1, column=2, sticky="w",
                                              padx=(16, 8), pady=5)
        due = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        self.due_date_var = tk.StringVar(value=due)
        ttk.Entry(hdr, textvariable=self.due_date_var, width=14).grid(
            row=1, column=3, sticky="w", pady=5)

        # Row 2: Notes
        ttk.Label(hdr, text="Notes").grid(row=2, column=0, sticky="nw",
                                           padx=(0, 8), pady=5)
        self.notes_var = tk.StringVar()
        ttk.Entry(hdr, textvariable=self.notes_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", pady=5)

        # ── Section 2: Add item row ───────────────────────────────
        item_sec = ttk.LabelFrame(outer, text="Add Line Item", padding=12)
        item_sec.grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        for i in range(7):
            item_sec.columnconfigure(i, weight=(1 if i in (0, 1) else 0))

        ttk.Label(item_sec, text="Item / Service").grid(
            row=0, column=0, sticky="w", padx=(0, 6))
        self.item_name_var = tk.StringVar()
        self.item_cb = ttk.Combobox(item_sec, textvariable=self.item_name_var,
                                    width=26)
        self.item_cb.grid(row=0, column=0, sticky="ew", pady=4)
        self.item_cb.bind("<<ComboboxSelected>>", self._on_item_select)

        ttk.Label(item_sec, text="Description").grid(
            row=0, column=1, sticky="w", padx=(10, 6))
        self.item_desc_var = tk.StringVar()
        ttk.Entry(item_sec, textvariable=self.item_desc_var, width=22).grid(
            row=0, column=1, sticky="ew", pady=4)

        ttk.Label(item_sec, text="Qty").grid(row=0, column=2, sticky="w",
                                              padx=(10, 4))
        self.qty_var = tk.StringVar(value="1")
        qty_e = ttk.Entry(item_sec, textvariable=self.qty_var, width=7)
        qty_e.grid(row=0, column=3, sticky="w", pady=4)
        qty_e.bind("<KeyRelease>", self._recalc_row)

        ttk.Label(item_sec, text="Unit Price").grid(row=0, column=4,
                                                    sticky="w", padx=(10, 4))
        self.item_price_var = tk.StringVar(value="0.00")
        price_e = ttk.Entry(item_sec, textvariable=self.item_price_var, width=10)
        price_e.grid(row=0, column=5, sticky="w", pady=4)
        price_e.bind("<KeyRelease>", self._recalc_row)

        self.row_amt_var = tk.StringVar(value=fmt_currency(0))
        ttk.Label(item_sec, textvariable=self.row_amt_var,
                  font=("Segoe UI", 10, "bold"),
                  foreground=C_HEADER, width=12).grid(
            row=0, column=6, sticky="e", padx=(10, 0))

        ttk.Button(item_sec, text="➕ Add Item",
                   style="Green.TButton",
                   command=self._add_row).grid(
            row=1, column=6, sticky="e", pady=(6, 0))

        # ── Section 3: Items table ────────────────────────────────
        tbl_sec = ttk.LabelFrame(outer, text="Bill Items", padding=8)
        tbl_sec.grid(row=2, column=0, sticky="ew", padx=14, pady=6)
        tbl_sec.columnconfigure(0, weight=1)

        cols = ("item_name", "description", "quantity", "unit_price", "amount")
        self.items_tree = ttk.Treeview(tbl_sec, columns=cols,
                                       show="headings", height=8,
                                       selectmode="browse")
        item_headers = [
            ("item_name",   "Item Name",   200, "w"),
            ("description", "Description", 200, "w"),
            ("quantity",    "Qty",          70, "e"),
            ("unit_price",  "Unit Price",  100, "e"),
            ("amount",      "Amount",      110, "e"),
        ]
        for cid, text, w, anc in item_headers:
            self.items_tree.heading(cid, text=text)
            self.items_tree.column(cid, width=w, anchor=anc)

        vsb = ttk.Scrollbar(tbl_sec, orient="vertical",
                             command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=vsb.set)
        self.items_tree.grid(row=0, column=0, sticky="ew")
        vsb.grid(row=0, column=1, sticky="ns")

        ttk.Button(tbl_sec, text="🗑 Remove Selected",
                   style="Red.TButton",
                   command=self._remove_row).grid(
            row=1, column=0, sticky="w", pady=(6, 0))

        # ── Section 4: Totals ─────────────────────────────────────
        tot_sec = ttk.LabelFrame(outer, text="Totals", padding=12)
        tot_sec.grid(row=3, column=0, sticky="e", padx=14, pady=6)

        self.subtotal_var = tk.StringVar(value=fmt_currency(0))
        self.tax_pct_var  = tk.StringVar(value="0")
        self.tax_amt_var  = tk.StringVar(value=fmt_currency(0))
        self.total_var    = tk.StringVar(value=fmt_currency(0))

        rows_def = [
            ("Subtotal:", self.subtotal_var, False),
            ("Tax %:",    self.tax_pct_var,  True),
            ("Tax Amount:", self.tax_amt_var, False),
            ("TOTAL:",    self.total_var,    False),
        ]
        for r, (label, var, editable) in enumerate(rows_def):
            ttk.Label(tot_sec, text=label,
                      font=("Segoe UI", 10,
                            "bold" if label == "TOTAL:" else "normal")).grid(
                row=r, column=0, sticky="e", padx=(0, 10), pady=4)
            if editable:
                e = ttk.Entry(tot_sec, textvariable=var, width=10)
                e.grid(row=r, column=1, sticky="w", pady=4)
                e.bind("<KeyRelease>", lambda _: self._recalc_totals())
            else:
                font = ("Segoe UI", 12, "bold") if label == "TOTAL:" else ("Segoe UI", 10)
                fg = C_HEADER if label == "TOTAL:" else "#555"
                ttk.Label(tot_sec, textvariable=var, font=font,
                          foreground=fg, width=14, anchor="e").grid(
                    row=r, column=1, sticky="e", pady=4)

        # ── Section 5: Action buttons ─────────────────────────────
        act = ttk.Frame(outer)
        act.grid(row=4, column=0, sticky="ew", padx=14, pady=(6, 14))

        ttk.Button(act, text="💾 Save Bill", style="Green.TButton",
                   command=self.save_bill).pack(side="left", padx=(0, 8))
        ttk.Button(act, text="🖨 Generate Receipt", style="Orange.TButton",
                   command=self.generate_receipt_prompt).pack(
            side="left", padx=(0, 8))
        ttk.Button(act, text="✖ Clear Bill",
                   command=self.clear_bill).pack(side="left")

        self.status_lbl = ttk.Label(act, text="", foreground=C_GREEN)
        self.status_lbl.pack(side="left", padx=(16, 0))

    # ── Refresh helpers ──────────────────────────────────────────

    def refresh_clients(self):
        clients = db.get_all_clients()
        self._clients = clients
        names = [c["business_name"] for c in clients]
        self.client_cb["values"] = names
        if not self.client_var.get() and names:
            pass  # Don't auto-select

    def refresh_inventory(self):
        items = db.get_all_inventory()
        self._inventory = {it["name"]: it for it in items}
        names = list(self._inventory.keys())
        self.item_cb["values"] = names

    def _reset_bill_number(self):
        self.bill_num_var.set(db.generate_bill_number())

    # ── Item row helpers ─────────────────────────────────────────

    def _on_item_select(self, _event=None):
        name = self.item_name_var.get()
        if name in self._inventory:
            it = self._inventory[name]
            self.item_price_var.set(f"{it['unit_price']:.2f}")
            self.item_desc_var.set(it.get("description") or "")
        self._recalc_row()

    def _recalc_row(self, _event=None):
        try:
            qty = float(self.qty_var.get() or "0")
            price = float(self.item_price_var.get() or "0")
            amt = qty * price
        except ValueError:
            amt = 0.0
        self.row_amt_var.set(fmt_currency(amt))

    def _add_row(self):
        name = self.item_name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Enter an item name.")
            return
        try:
            qty = float(self.qty_var.get() or "1")
            price = float(self.item_price_var.get() or "0")
        except ValueError:
            messagebox.showwarning("Invalid", "Quantity and price must be numbers.")
            return
        if qty <= 0:
            messagebox.showwarning("Invalid", "Quantity must be greater than 0.")
            return

        amt = round(qty * price, 2)
        desc = self.item_desc_var.get().strip()
        row = {
            "item_name": name,
            "description": desc,
            "quantity": qty,
            "unit_price": price,
            "amount": amt,
        }
        self._bill_rows.append(row)
        self.items_tree.insert("", "end",
                               values=(name, desc, qty,
                                       fmt_currency(price),
                                       fmt_currency(amt)))
        # Clear entry row
        self.item_name_var.set("")
        self.item_desc_var.set("")
        self.qty_var.set("1")
        self.item_price_var.set("0.00")
        self.row_amt_var.set(fmt_currency(0))
        self._recalc_totals()

    def _remove_row(self):
        sel = self.items_tree.selection()
        if not sel:
            return
        idx = self.items_tree.index(sel[0])
        self.items_tree.delete(sel[0])
        if 0 <= idx < len(self._bill_rows):
            self._bill_rows.pop(idx)
        self._recalc_totals()

    def _recalc_totals(self, _event=None):
        subtotal = sum(r["amount"] for r in self._bill_rows)
        try:
            tax_pct = float(self.tax_pct_var.get() or "0")
        except ValueError:
            tax_pct = 0.0
        tax_amt = round(subtotal * tax_pct / 100, 2)
        total = round(subtotal + tax_amt, 2)
        self.subtotal_var.set(fmt_currency(subtotal))
        self.tax_amt_var.set(fmt_currency(tax_amt))
        self.total_var.set(fmt_currency(total))

    # ── Validation ───────────────────────────────────────────────

    def _get_selected_client_id(self):
        name = self.client_var.get()
        for c in self._clients:
            if c["business_name"] == name:
                return c["id"]
        return None

    # ── Actions ──────────────────────────────────────────────────

    def save_bill(self):
        client_id = self._get_selected_client_id()
        if not client_id:
            messagebox.showwarning("Missing", "Please select a client.")
            return
        if not self._bill_rows:
            messagebox.showwarning("Missing", "Add at least one item.")
            return

        bill_num = self.bill_num_var.get().strip()
        bill_date_raw = self.bill_date_var.get().strip()
        due_date_raw = self.due_date_var.get().strip()

        try:
            bill_date = parse_date(bill_date_raw)
        except Exception:
            messagebox.showwarning("Invalid", "Invalid bill date format.")
            return
        due_date = parse_date(due_date_raw) if due_date_raw else ""

        subtotal = sum(r["amount"] for r in self._bill_rows)
        try:
            tax_pct = float(self.tax_pct_var.get() or "0")
        except ValueError:
            tax_pct = 0.0
        tax_amt = round(subtotal * tax_pct / 100, 2)
        total = round(subtotal + tax_amt, 2)
        notes = self.notes_var.get().strip()

        try:
            bill_id = db.add_bill(
                client_id, bill_num, bill_date, due_date,
                subtotal, tax_pct, tax_amt, total, "pending", notes,
                self._bill_rows
            )
            msg = f"Bill {bill_num} saved successfully."
            self.status_lbl.config(text=msg, foreground=C_GREEN)
            self.app.set_status(msg)
            self.app.ledger_tab.refresh_clients()
            # Ask if they want to generate receipt now
            if messagebox.askyesno("Success",
                                   f"{msg}\n\nGenerate receipt now?"):
                self._open_receipt(bill_id)
            self.clear_bill()
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def generate_receipt_prompt(self):
        """Prompt user for a saved bill to view receipt, or use last saved."""
        client_id = self._get_selected_client_id()
        if not client_id:
            messagebox.showwarning("Missing", "Select a client first.")
            return
        bills = db.get_bills_for_client(client_id)
        if not bills:
            messagebox.showinfo("No Bills", "No bills found for this client.")
            return
        # Show picker dialog
        _ReceiptPickerDialog(self.app.root, bills, client_id,
                             callback=self._open_receipt)

    def _open_receipt(self, bill_id: int):
        bill = db.get_bill(bill_id)
        if not bill:
            return
        client = db.get_client(bill["client_id"])
        items = db.get_bill_items(bill_id)
        payments = db.get_payments_for_bill(bill_id)
        ReceiptViewWindow(self.app.root, bill, client, items, payments)

    def clear_bill(self):
        self.client_var.set("")
        self._reset_bill_number()
        self.bill_date_var.set(datetime.now().strftime("%d/%m/%Y"))
        due = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        self.due_date_var.set(due)
        self.notes_var.set("")
        self._bill_rows.clear()
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        self.item_name_var.set("")
        self.item_desc_var.set("")
        self.qty_var.set("1")
        self.item_price_var.set("0.00")
        self.tax_pct_var.set("0")
        self._recalc_totals()
        self.status_lbl.config(text="")
        self._editing_bill_id = None


class _ReceiptPickerDialog(tk.Toplevel):
    """Simple dialog to pick a bill for receipt preview."""
    def __init__(self, parent, bills, client_id, callback):
        super().__init__(parent)
        self.title("Select Bill for Receipt")
        self.resizable(False, False)
        self.grab_set()
        self.callback = callback

        ttk.Label(self, text="Select bill:",
                  font=("Segoe UI", 11)).pack(padx=20, pady=(16, 6))

        self.var = tk.StringVar()
        options = {f"{b['bill_number']} — {b['bill_date']} — ₹{b['total']:.2f}": b["id"]
                   for b in bills}
        self._map = options
        cb = ttk.Combobox(self, textvariable=self.var,
                          values=list(options.keys()),
                          state="readonly", width=44)
        cb.pack(padx=20, pady=4)
        if options:
            cb.current(0)

        bf = ttk.Frame(self)
        bf.pack(padx=20, pady=14)
        ttk.Button(bf, text="View Receipt", style="Green.TButton",
                   command=self._ok).pack(side="left", padx=(0, 8))
        ttk.Button(bf, text="Cancel", command=self.destroy).pack(side="left")

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _ok(self):
        sel = self.var.get()
        if sel in self._map:
            self.destroy()
            self.callback(self._map[sel])
