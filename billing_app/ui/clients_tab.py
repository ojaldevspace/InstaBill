"""
clients_tab.py - Client management UI.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import database as db

C_HEADER = "#1a3a5c"
C_BG     = "#f4f7fb"
C_WHITE  = "#ffffff"
C_GREEN  = "#27ae60"
C_RED    = "#e74c3c"
C_BORDER = "#d0dae8"
CURRENCY = "$"


def fmt_currency(v):
    return f"{CURRENCY}{float(v):,.2f}"


class ClientsTab:
    def __init__(self, parent: ttk.Frame, app):
        self.app = app
        self.selected_id = None
        self._build(parent)
        self.load_clients()

    # ── Layout ───────────────────────────────────────────────────

    def _build(self, parent):
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        # Left – list
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        lbl = ttk.Label(left, text="All Clients",
                        font=("Segoe UI", 12, "bold"), foreground=C_HEADER)
        lbl.grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Search bar
        sf = ttk.Frame(left)
        sf.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        sf.columnconfigure(1, weight=1)
        ttk.Label(sf, text="🔍").grid(row=0, column=0, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_clients())
        ttk.Entry(sf, textvariable=self.search_var).grid(
            row=0, column=1, sticky="ew")

        # Treeview
        cols = ("business_name", "contact_person", "phone", "balance")
        self.tree = ttk.Treeview(left, columns=cols, show="headings",
                                 selectmode="browse")
        headers = [("business_name", "Business Name", 200),
                   ("contact_person", "Contact", 130),
                   ("phone", "Phone", 120),
                   ("balance", "Balance Due", 110)]
        for cid, text, w in headers:
            self.tree.heading(cid, text=text,
                              command=lambda c=cid: self._sort_tree(c))
            self.tree.column(cid, width=w, anchor="w")

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        vsb.grid(row=2, column=1, sticky="ns")
        left.rowconfigure(2, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.tag_configure("has_balance", foreground=C_RED)
        self.tree.tag_configure("all_paid", foreground=C_GREEN)

        # Action buttons below tree
        btn_f = ttk.Frame(left)
        btn_f.grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Button(btn_f, text="➕ Add New",
                   command=self.add_new).pack(side="left", padx=(0, 6))
        ttk.Button(btn_f, text="🗑 Delete", style="Red.TButton",
                   command=self.delete_client).pack(side="left")

        # Right – form
        right = ttk.LabelFrame(parent, text="Client Details", padding=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        right.columnconfigure(1, weight=1)

        fields = [
            ("Business Name *", "business_name"),
            ("Contact Person",  "contact_person"),
            ("Phone",           "phone"),
            ("Email",           "email"),
        ]
        self.vars = {}
        for row, (label, key) in enumerate(fields):
            ttk.Label(right, text=label).grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            v = tk.StringVar()
            self.vars[key] = v
            ttk.Entry(right, textvariable=v).grid(
                row=row, column=1, sticky="ew", pady=5)

        # Address textarea
        ttk.Label(right, text="Address").grid(
            row=len(fields), column=0, sticky="nw", pady=5, padx=(0, 10))
        self.addr_text = tk.Text(right, height=4, width=28,
                                 font=("Segoe UI", 10),
                                 bg=C_WHITE, relief="solid", bd=1)
        self.addr_text.grid(row=len(fields), column=1, sticky="ew", pady=5)

        # Form buttons
        form_btn = ttk.Frame(right)
        form_btn.grid(row=len(fields)+1, column=0, columnspan=2,
                      sticky="e", pady=(12, 0))
        ttk.Button(form_btn, text="✔ Save", style="Green.TButton",
                   command=self.save_client).pack(side="left", padx=(0, 6))
        ttk.Button(form_btn, text="✖ Clear",
                   command=self.clear_form).pack(side="left")

        # Info label
        self.info_lbl = ttk.Label(right, text="", foreground=C_RED,
                                  wraplength=250)
        self.info_lbl.grid(row=len(fields)+2, column=0, columnspan=2,
                           sticky="w", pady=(6, 0))

    # ── Data ─────────────────────────────────────────────────────

    def load_clients(self, *_):
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.search_var.get().lower()
        clients = db.get_all_clients()
        for c in clients:
            if query and query not in c["business_name"].lower() \
                    and query not in (c.get("contact_person") or "").lower() \
                    and query not in (c.get("phone") or "").lower():
                continue
            billed, paid = db.get_client_balance(c["id"])
            balance = billed - paid
            tag = "has_balance" if balance > 0.01 else "all_paid"
            self.tree.insert("", "end", iid=str(c["id"]),
                             values=(
                                 c["business_name"],
                                 c.get("contact_person") or "",
                                 c.get("phone") or "",
                                 fmt_currency(balance)
                             ), tags=(tag,))

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self.selected_id = int(sel[0])
        c = db.get_client(self.selected_id)
        if not c:
            return
        self.vars["business_name"].set(c.get("business_name", ""))
        self.vars["contact_person"].set(c.get("contact_person", "") or "")
        self.vars["phone"].set(c.get("phone", "") or "")
        self.vars["email"].set(c.get("email", "") or "")
        self.addr_text.delete("1.0", "end")
        self.addr_text.insert("1.0", c.get("address", "") or "")
        self.info_lbl.config(text="")

    def _sort_tree(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort(key=lambda x: x[0].lower())
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)

    # ── Actions ──────────────────────────────────────────────────

    def add_new(self):
        self.selected_id = None
        self.clear_form()
        self.tree.selection_remove(self.tree.selection())

    def save_client(self):
        name = self.vars["business_name"].get().strip()
        if not name:
            self.info_lbl.config(text="Business Name is required.")
            return
        contact = self.vars["contact_person"].get().strip()
        phone   = self.vars["phone"].get().strip()
        email   = self.vars["email"].get().strip()
        address = self.addr_text.get("1.0", "end").strip()

        try:
            if self.selected_id:
                db.update_client(self.selected_id, name, contact,
                                 phone, email, address)
                msg = f"Client '{name}' updated."
            else:
                db.add_client(name, contact, phone, email, address)
                msg = f"Client '{name}' added."
            self.info_lbl.config(text=msg, foreground=C_GREEN)
            self.load_clients()
            self.app.refresh_billing_clients()
            self.app.set_status(msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_client(self):
        if not self.selected_id:
            messagebox.showwarning("No selection", "Select a client to delete.")
            return
        c = db.get_client(self.selected_id)
        if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete client '{c['business_name']}' and all their bills?\n"
                "This cannot be undone."):
            return
        try:
            db.delete_client(self.selected_id)
            self.selected_id = None
            self.clear_form()
            self.load_clients()
            self.app.refresh_billing_clients()
            self.app.set_status("Client deleted.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear_form(self):
        for v in self.vars.values():
            v.set("")
        self.addr_text.delete("1.0", "end")
        self.info_lbl.config(text="")
        self.selected_id = None
