"""
inventory_tab.py - Inventory item management UI.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import database as db

C_HEADER = "#1a3a5c"
C_BG     = "#f4f7fb"
C_WHITE  = "#ffffff"
C_GREEN  = "#27ae60"
C_RED    = "#e74c3c"
CURRENCY = "₹"

UNITS = ["pcs", "kg", "g", "litre", "ml", "hr", "day", "month",
         "set", "box", "pair", "sq.ft", "sq.m", "m", "ft", "other"]


def fmt_currency(v):
    return f"{CURRENCY}{float(v):,.2f}"


class InventoryTab:
    def __init__(self, parent: ttk.Frame, app):
        self.app = app
        self.selected_id = None
        self._build(parent)
        self.load_items()

    def _build(self, parent):
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        # ── Left – list ──────────────────────────────────────────
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Inventory Items",
                  font=("Segoe UI", 12, "bold"),
                  foreground=C_HEADER).grid(row=0, column=0, sticky="w",
                                            pady=(0, 6))

        cols = ("name", "description", "unit", "unit_price")
        self.tree = ttk.Treeview(left, columns=cols,
                                 show="headings", selectmode="browse")
        headers = [
            ("name", "Item Name", 200),
            ("description", "Description", 200),
            ("unit", "Unit", 70),
            ("unit_price", "Unit Price", 100),
        ]
        for cid, text, w in headers:
            self.tree.heading(cid, text=text,
                              command=lambda c=cid: self._sort(c))
            anchor = "e" if cid == "unit_price" else "w"
            self.tree.column(cid, width=w, anchor=anchor)

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btn_f = ttk.Frame(left)
        btn_f.grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Button(btn_f, text="➕ Add New",
                   command=self.add_new).pack(side="left", padx=(0, 6))
        ttk.Button(btn_f, text="🗑 Delete", style="Red.TButton",
                   command=self.delete_item).pack(side="left")

        # ── Right – form ─────────────────────────────────────────
        right = ttk.LabelFrame(parent, text="Item Details", padding=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.columnconfigure(1, weight=1)

        # Item name
        ttk.Label(right, text="Item Name *").grid(
            row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        self.name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.name_var).grid(
            row=0, column=1, sticky="ew", pady=6)

        # Description
        ttk.Label(right, text="Description").grid(
            row=1, column=0, sticky="w", pady=6, padx=(0, 10))
        self.desc_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.desc_var).grid(
            row=1, column=1, sticky="ew", pady=6)

        # Unit price
        ttk.Label(right, text="Unit Price *").grid(
            row=2, column=0, sticky="w", pady=6, padx=(0, 10))
        self.price_var = tk.StringVar(value="0.00")
        ttk.Entry(right, textvariable=self.price_var).grid(
            row=2, column=1, sticky="ew", pady=6)

        # Unit
        ttk.Label(right, text="Unit").grid(
            row=3, column=0, sticky="w", pady=6, padx=(0, 10))
        self.unit_var = tk.StringVar(value="pcs")
        unit_cb = ttk.Combobox(right, textvariable=self.unit_var,
                               values=UNITS, state="normal", width=10)
        unit_cb.grid(row=3, column=1, sticky="w", pady=6)

        # Buttons
        btn_row = ttk.Frame(right)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btn_row, text="✔ Save", style="Green.TButton",
                   command=self.save_item).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="✖ Clear",
                   command=self.clear_form).pack(side="left")

        self.info_lbl = ttk.Label(right, text="", foreground=C_RED,
                                  wraplength=250)
        self.info_lbl.grid(row=5, column=0, columnspan=2, sticky="w",
                           pady=(6, 0))

    # ── Data ─────────────────────────────────────────────────────

    def load_items(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for it in db.get_all_inventory():
            self.tree.insert("", "end", iid=str(it["id"]),
                             values=(
                                 it["name"],
                                 it.get("description") or "",
                                 it.get("unit") or "pcs",
                                 fmt_currency(it["unit_price"]),
                             ))

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        items = db.get_all_inventory()
        it = next((x for x in items if x["id"] == self.selected_id), None)
        if not it:
            return
        self.name_var.set(it["name"])
        self.desc_var.set(it.get("description") or "")
        self.price_var.set(f"{it['unit_price']:.2f}")
        self.unit_var.set(it.get("unit") or "pcs")
        self.info_lbl.config(text="")

    def _sort(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            items.sort(key=lambda x: float(x[0].replace(CURRENCY, "").replace(",", "")))
        except ValueError:
            items.sort(key=lambda x: x[0].lower())
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)

    # ── Actions ──────────────────────────────────────────────────

    def add_new(self):
        self.selected_id = None
        self.clear_form()
        self.tree.selection_remove(self.tree.selection())

    def save_item(self):
        name = self.name_var.get().strip()
        if not name:
            self.info_lbl.config(text="Item Name is required.")
            return
        try:
            price = float(self.price_var.get().strip() or "0")
        except ValueError:
            self.info_lbl.config(text="Unit Price must be a number.")
            return

        desc = self.desc_var.get().strip()
        unit = self.unit_var.get().strip() or "pcs"

        try:
            if self.selected_id:
                db.update_inventory_item(self.selected_id, name, desc, price, unit)
                msg = f"Item '{name}' updated."
            else:
                db.add_inventory_item(name, desc, price, unit)
                msg = f"Item '{name}' added."
            self.info_lbl.config(text=msg, foreground=C_GREEN)
            self.load_items()
            # Also refresh billing tab's inventory dropdown
            self.app.billing_tab.refresh_inventory()
            self.app.set_status(msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_item(self):
        if not self.selected_id:
            messagebox.showwarning("No selection", "Select an item to delete.")
            return
        items = db.get_all_inventory()
        it = next((x for x in items if x["id"] == self.selected_id), None)
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete item '{it['name']}'?"):
            return
        try:
            db.delete_inventory_item(self.selected_id)
            self.selected_id = None
            self.clear_form()
            self.load_items()
            self.app.billing_tab.refresh_inventory()
            self.app.set_status("Item deleted.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_form(self):
        self.name_var.set("")
        self.desc_var.set("")
        self.price_var.set("0.00")
        self.unit_var.set("pcs")
        self.info_lbl.config(text="")
        self.selected_id = None
