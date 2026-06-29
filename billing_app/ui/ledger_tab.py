"""
ledger_tab.py - Monthly ledger per client with payment tracking.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
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

STATUS_COLORS = {
    "paid":    C_GREEN,
    "partial": C_ORANGE,
    "pending": C_RED,
}

MONTHS = [
    "All", "January", "February", "March", "April",
    "May", "June", "July", "August", "September",
    "October", "November", "December"
]

PAYMENT_METHODS = ["Cash", "Bank Transfer", "Cheque", "Online", "Card", "Other"]


def fmt_currency(v):
    return f"{CURRENCY}{float(v):,.2f}"


def fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return d or ""


def parse_date(d):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return d


class LedgerTab:
    def __init__(self, parent: ttk.Frame, app):
        self.app = app
        self._selected_bill_id = None
        self._build(parent)
        self.refresh_clients()

    def _build(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        parent.rowconfigure(4, weight=0)

        # ── Filter row ───────────────────────────────────────────
        flt = ttk.LabelFrame(parent, text="Filter", padding=10)
        flt.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        ttk.Label(flt, text="Client:").pack(side="left", padx=(0, 6))
        self.client_var = tk.StringVar()
        self.client_cb = ttk.Combobox(flt, textvariable=self.client_var,
                                      state="readonly", width=28)
        self.client_cb.pack(side="left", padx=(0, 14))

        ttk.Label(flt, text="Month:").pack(side="left", padx=(0, 6))
        self.month_var = tk.StringVar(value="All")
        month_cb = ttk.Combobox(flt, textvariable=self.month_var,
                                 values=MONTHS, state="readonly", width=12)
        month_cb.pack(side="left", padx=(0, 14))

        ttk.Label(flt, text="Year:").pack(side="left", padx=(0, 6))
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        years = [str(y) for y in range(datetime.now().year, 2019, -1)]
        year_cb = ttk.Combobox(flt, textvariable=self.year_var,
                                values=years, state="normal", width=8)
        year_cb.pack(side="left", padx=(0, 14))

        ttk.Button(flt, text="🔍 Apply Filter",
                   command=self.apply_filter).pack(side="left", padx=(0, 8))
        ttk.Button(flt, text="↺ Reset",
                   command=self._reset_filter).pack(side="left")

        # ── Summary cards ────────────────────────────────────────
        cards_frame = ttk.Frame(parent)
        cards_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        cards_frame.columnconfigure((0, 1, 2), weight=1)

        self.card_billed_val = tk.StringVar(value=fmt_currency(0))
        self.card_paid_val   = tk.StringVar(value=fmt_currency(0))
        self.card_bal_val    = tk.StringVar(value=fmt_currency(0))

        card_defs = [
            ("Total Billed",  self.card_billed_val, "CardValue.TLabel",  0),
            ("Total Paid",    self.card_paid_val,   "CardGreen.TLabel",  1),
            ("Balance Due",   self.card_bal_val,    "CardRed.TLabel",    2),
        ]
        for title, var, style, col in card_defs:
            f = ttk.Frame(cards_frame, style="Card.TFrame", relief="groove")
            f.grid(row=0, column=col, sticky="ew",
                   padx=6 if col else 0, pady=2)
            f.columnconfigure(0, weight=1)
            ttk.Label(f, text=title, style="CardTitle.TLabel",
                      anchor="center").pack(pady=(8, 2), fill="x")
            ttk.Label(f, textvariable=var, style=style,
                      anchor="center").pack(pady=(0, 8), fill="x")

        # ── Bills treeview ───────────────────────────────────────
        tree_frame = ttk.LabelFrame(parent, text="Bills", padding=8)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("bill_number", "bill_date", "due_date",
                "total", "paid", "balance", "status")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                 show="headings", selectmode="browse")
        hdrs = [
            ("bill_number", "Bill #",      130, "w"),
            ("bill_date",   "Bill Date",   100, "center"),
            ("due_date",    "Due Date",    100, "center"),
            ("total",       "Total",       110, "e"),
            ("paid",        "Paid",        110, "e"),
            ("balance",     "Balance",     110, "e"),
            ("status",      "Status",       90, "center"),
        ]
        for cid, text, w, anc in hdrs:
            self.tree.heading(cid, text=text)
            self.tree.column(cid, width=w, anchor=anc, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("paid",    foreground=C_GREEN)
        self.tree.tag_configure("partial", foreground=C_ORANGE)
        self.tree.tag_configure("pending", foreground=C_RED)

        self.tree.bind("<<TreeviewSelect>>", self._on_bill_select)

        # Bills action buttons
        bill_btns = ttk.Frame(tree_frame)
        bill_btns.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Button(bill_btns, text="🖨 View Receipt",
                   command=self.view_receipt).pack(side="left", padx=(0, 8))
        ttk.Button(bill_btns, text="🗑 Delete Bill", style="Red.TButton",
                   command=self.delete_bill).pack(side="left")

        # ── Payment section ──────────────────────────────────────
        pay_frame = ttk.LabelFrame(parent, text="Payment History", padding=8)
        pay_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        pay_frame.columnconfigure(0, weight=1)

        pay_cols = ("payment_date", "amount", "method", "notes")
        self.pay_tree = ttk.Treeview(pay_frame, columns=pay_cols,
                                     show="headings", height=5,
                                     selectmode="browse")
        pay_hdrs = [
            ("payment_date", "Date",   110, "center"),
            ("amount",       "Amount", 110, "e"),
            ("method",       "Method", 110, "center"),
            ("notes",        "Notes",  300, "w"),
        ]
        for cid, text, w, anc in pay_hdrs:
            self.pay_tree.heading(cid, text=text)
            self.pay_tree.column(cid, width=w, anchor=anc)

        pvsb = ttk.Scrollbar(pay_frame, orient="vertical",
                              command=self.pay_tree.yview)
        self.pay_tree.configure(yscrollcommand=pvsb.set)
        self.pay_tree.grid(row=0, column=0, sticky="ew")
        pvsb.grid(row=0, column=1, sticky="ns")

        pay_btns = ttk.Frame(pay_frame)
        pay_btns.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Button(pay_btns, text="💵 Record Payment",
                   style="Green.TButton",
                   command=self.record_payment).pack(side="left", padx=(0, 8))
        ttk.Button(pay_btns, text="🗑 Delete Payment",
                   style="Red.TButton",
                   command=self.delete_payment).pack(side="left")

    # ── Refresh ──────────────────────────────────────────────────

    def refresh_clients(self):
        clients = db.get_all_clients()
        self._clients = clients
        names = [c["business_name"] for c in clients]
        self.client_cb["values"] = names
        if not self.client_var.get() and names:
            self.client_cb.current(0)
            self.apply_filter()

    def _reset_filter(self):
        self.month_var.set("All")
        self.year_var.set(str(datetime.now().year))
        self.apply_filter()

    # ── Filter & load ────────────────────────────────────────────

    def apply_filter(self):
        client_id = self._get_client_id()
        if not client_id:
            return
        month_name = self.month_var.get()
        month_num = MONTHS.index(month_name) if month_name != "All" else None
        year = self.year_var.get()

        # Summary
        total_b, total_p, balance = db.get_ledger_summary(
            client_id,
            month_num if month_num else None,
            year if month_num else None
        )
        self.card_billed_val.set(fmt_currency(total_b))
        self.card_paid_val.set(fmt_currency(total_p))
        self.card_bal_val.set(fmt_currency(balance))

        # Bills
        bills = db.get_bills_for_client(
            client_id,
            month_num if month_num else None,
            year if month_num else None
        )
        for item in self.tree.get_children():
            self.tree.delete(item)
        for b in bills:
            paid = db.get_paid_amount(b["id"])
            bal = b["total"] - paid
            status = b.get("status", "pending")
            self.tree.insert(
                "", "end", iid=str(b["id"]),
                values=(
                    b["bill_number"],
                    fmt_date(b["bill_date"]),
                    fmt_date(b.get("due_date", "")),
                    fmt_currency(b["total"]),
                    fmt_currency(paid),
                    fmt_currency(bal),
                    status.capitalize(),
                ),
                tags=(status,)
            )
        # Clear payment panel
        for item in self.pay_tree.get_children():
            self.pay_tree.delete(item)
        self._selected_bill_id = None

    def _get_client_id(self):
        name = self.client_var.get()
        for c in self._clients:
            if c["business_name"] == name:
                return c["id"]
        return None

    # ── Events ───────────────────────────────────────────────────

    def _on_bill_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_bill_id = int(sel[0])
        self._load_payments(self._selected_bill_id)

    def _load_payments(self, bill_id):
        for item in self.pay_tree.get_children():
            self.pay_tree.delete(item)
        payments = db.get_payments_for_bill(bill_id)
        for p in payments:
            self.pay_tree.insert("", "end", iid=str(p["id"]),
                                 values=(
                                     fmt_date(p["payment_date"]),
                                     fmt_currency(p["amount"]),
                                     p.get("payment_method", "").capitalize(),
                                     p.get("notes", "") or "",
                                 ))

    # ── Actions ──────────────────────────────────────────────────

    def record_payment(self):
        if not self._selected_bill_id:
            messagebox.showwarning("No Bill", "Select a bill first.")
            return
        bill = db.get_bill(self._selected_bill_id)
        paid_so_far = db.get_paid_amount(self._selected_bill_id)
        remaining = bill["total"] - paid_so_far
        _PaymentDialog(
            self.app.root, self._selected_bill_id,
            bill["bill_number"], remaining,
            callback=self._after_payment
        )

    def _after_payment(self):
        self.apply_filter()
        if self._selected_bill_id:
            self._load_payments(self._selected_bill_id)
        self.app.clients_tab.load_clients()
        self.app.set_status("Payment recorded.")

    def delete_payment(self):
        sel = self.pay_tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a payment to delete.")
            return
        pay_id = int(sel[0])
        if not messagebox.askyesno("Confirm", "Delete this payment record?"):
            return
        try:
            db.delete_payment(pay_id)
            self.apply_filter()
            if self._selected_bill_id:
                self._load_payments(self._selected_bill_id)
            self.app.clients_tab.load_clients()
            self.app.set_status("Payment deleted.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def view_receipt(self):
        if not self._selected_bill_id:
            messagebox.showwarning("No Bill", "Select a bill to view its receipt.")
            return
        bill = db.get_bill(self._selected_bill_id)
        client = db.get_client(bill["client_id"])
        items = db.get_bill_items(self._selected_bill_id)
        payments = db.get_payments_for_bill(self._selected_bill_id)
        ReceiptViewWindow(self.app.root, bill, client, items, payments)

    def delete_bill(self):
        if not self._selected_bill_id:
            messagebox.showwarning("No Bill", "Select a bill to delete.")
            return
        bill = db.get_bill(self._selected_bill_id)
        if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete bill {bill['bill_number']}?\n"
                "All related payments will also be deleted."):
            return
        try:
            db.delete_bill(self._selected_bill_id)
            self._selected_bill_id = None
            for item in self.pay_tree.get_children():
                self.pay_tree.delete(item)
            self.apply_filter()
            self.app.clients_tab.load_clients()
            self.app.set_status("Bill deleted.")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ─────────────────────────── Payment Dialog ───────────────────────────

class _PaymentDialog(tk.Toplevel):
    def __init__(self, parent, bill_id, bill_number, remaining, callback):
        super().__init__(parent)
        self.title(f"Record Payment — {bill_number}")
        self.resizable(False, False)
        self.grab_set()
        self.bill_id = bill_id
        self.callback = callback

        pad = {"padx": 20, "pady": 6}
        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # Amount
        ttk.Label(frm, text="Amount *").grid(row=0, column=0, sticky="w", **pad)
        self.amount_var = tk.StringVar(value=f"{remaining:.2f}")
        ttk.Entry(frm, textvariable=self.amount_var, width=18).grid(
            row=0, column=1, sticky="ew", **pad)

        remaining_lbl = ttk.Label(
            frm,
            text=f"(Balance due: {fmt_currency(remaining)})",
            foreground=C_RED, font=("Segoe UI", 9)
        )
        remaining_lbl.grid(row=0, column=2, sticky="w", padx=(0, 10))

        # Date
        ttk.Label(frm, text="Payment Date *").grid(row=1, column=0, sticky="w", **pad)
        self.date_var = tk.StringVar(
            value=datetime.now().strftime("%d/%m/%Y"))
        ttk.Entry(frm, textvariable=self.date_var, width=14).grid(
            row=1, column=1, sticky="w", **pad)

        # Method
        ttk.Label(frm, text="Method").grid(row=2, column=0, sticky="w", **pad)
        self.method_var = tk.StringVar(value="Cash")
        method_cb = ttk.Combobox(frm, textvariable=self.method_var,
                                  values=PAYMENT_METHODS,
                                  state="readonly", width=16)
        method_cb.grid(row=2, column=1, sticky="w", **pad)

        # Notes
        ttk.Label(frm, text="Notes").grid(row=3, column=0, sticky="w", **pad)
        self.notes_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.notes_var, width=30).grid(
            row=3, column=1, columnspan=2, sticky="ew", **pad)

        # Error label
        self.err_lbl = ttk.Label(frm, text="", foreground=C_RED)
        self.err_lbl.grid(row=4, column=0, columnspan=3, sticky="w",
                           padx=20, pady=(0, 4))

        # Buttons
        btn_f = ttk.Frame(frm)
        btn_f.grid(row=5, column=0, columnspan=3, sticky="e",
                   padx=20, pady=(6, 0))
        ttk.Button(btn_f, text="Save Payment", style="Green.TButton",
                   command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(btn_f, text="Cancel", command=self.destroy).pack(side="left")

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _save(self):
        try:
            amount = float(self.amount_var.get().strip())
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            self.err_lbl.config(text=f"Invalid amount: {e}")
            return

        date_raw = self.date_var.get().strip()
        try:
            date = parse_date(date_raw)
        except Exception:
            self.err_lbl.config(text="Invalid date format. Use DD/MM/YYYY.")
            return

        method = self.method_var.get().lower()
        notes = self.notes_var.get().strip()

        try:
            db.add_payment(self.bill_id, amount, date, method, notes)
            self.destroy()
            self.callback()
        except Exception as e:
            self.err_lbl.config(text=str(e))
