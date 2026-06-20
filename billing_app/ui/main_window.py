"""
main_window.py - Root application window with tab navigation.
"""
import tkinter as tk
from tkinter import ttk

from ui.clients_tab import ClientsTab
from ui.inventory_tab import InventoryTab
from ui.billing_tab import BillingTab
from ui.ledger_tab import LedgerTab

# ── Colour palette ───────────────────────────────────────────────────
C_HEADER   = "#1a3a5c"
C_ACCENT   = "#2c5f8a"
C_WHITE    = "#ffffff"
C_BG       = "#f4f7fb"
C_GREEN    = "#27ae60"
C_RED      = "#e74c3c"
C_ORANGE   = "#e67e22"
C_TEXT     = "#2d3436"
C_BORDER   = "#d0dae8"


def apply_theme(root: tk.Tk):
    style = ttk.Style(root)
    style.theme_use("clam")

    # Generic
    style.configure(".", background=C_BG, foreground=C_TEXT,
                    font=("Segoe UI", 10))
    style.configure("TFrame", background=C_BG)
    style.configure("TLabel", background=C_BG, foreground=C_TEXT,
                    font=("Segoe UI", 10))
    style.configure("TEntry", fieldbackground=C_WHITE,
                    foreground=C_TEXT, font=("Segoe UI", 10))
    style.configure("TCombobox", fieldbackground=C_WHITE,
                    foreground=C_TEXT, font=("Segoe UI", 10))
    style.configure("TSpinbox", fieldbackground=C_WHITE,
                    foreground=C_TEXT, font=("Segoe UI", 10))

    # Buttons
    style.configure("TButton", background=C_ACCENT, foreground=C_WHITE,
                    font=("Segoe UI", 10, "bold"), padding=(10, 5),
                    relief="flat", borderwidth=0)
    style.map("TButton",
              background=[("active", C_HEADER), ("pressed", C_HEADER)],
              foreground=[("active", C_WHITE)])
    style.configure("Green.TButton", background=C_GREEN, foreground=C_WHITE,
                    font=("Segoe UI", 10, "bold"), padding=(10, 5))
    style.map("Green.TButton",
              background=[("active", "#219a52"), ("pressed", "#1e8449")])
    style.configure("Red.TButton", background=C_RED, foreground=C_WHITE,
                    font=("Segoe UI", 10, "bold"), padding=(10, 5))
    style.map("Red.TButton",
              background=[("active", "#c0392b"), ("pressed", "#a93226")])
    style.configure("Orange.TButton", background=C_ORANGE, foreground=C_WHITE,
                    font=("Segoe UI", 10, "bold"), padding=(10, 5))
    style.map("Orange.TButton",
              background=[("active", "#d35400"), ("pressed", "#ba4a00")])

    # Treeview
    style.configure("Treeview",
                    background=C_WHITE, foreground=C_TEXT,
                    fieldbackground=C_WHITE, rowheight=28,
                    font=("Segoe UI", 10))
    style.configure("Treeview.Heading",
                    background=C_HEADER, foreground=C_WHITE,
                    font=("Segoe UI", 10, "bold"), relief="flat")
    style.map("Treeview",
              background=[("selected", C_ACCENT)],
              foreground=[("selected", C_WHITE)])
    style.map("Treeview.Heading",
              background=[("active", C_ACCENT)])

    # Notebook tabs
    style.configure("TNotebook", background=C_HEADER, borderwidth=0)
    style.configure("TNotebook.Tab",
                    background=C_ACCENT, foreground=C_WHITE,
                    font=("Segoe UI", 11, "bold"),
                    padding=(20, 8), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", C_BG), ("active", C_HEADER)],
              foreground=[("selected", C_HEADER), ("active", C_WHITE)])

    # LabelFrame
    style.configure("TLabelframe", background=C_BG,
                    bordercolor=C_BORDER, relief="groove")
    style.configure("TLabelframe.Label", background=C_BG,
                    foreground=C_HEADER, font=("Segoe UI", 10, "bold"))

    # Scrollbar
    style.configure("TScrollbar", background=C_BG, troughcolor=C_BG,
                    arrowcolor=C_HEADER)

    # Separator
    style.configure("TSeparator", background=C_BORDER)

    # Summary card styles
    style.configure("Card.TFrame", background=C_WHITE,
                    relief="raised", borderwidth=1)
    style.configure("CardTitle.TLabel", background=C_WHITE,
                    foreground=C_TEXT, font=("Segoe UI", 9))
    style.configure("CardValue.TLabel", background=C_WHITE,
                    foreground=C_HEADER, font=("Segoe UI", 16, "bold"))
    style.configure("CardGreen.TLabel", background=C_WHITE,
                    foreground=C_GREEN, font=("Segoe UI", 16, "bold"))
    style.configure("CardRed.TLabel", background=C_WHITE,
                    foreground=C_RED, font=("Segoe UI", 16, "bold"))


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("InstaBill — Billing & Receipt Manager")
        self.root.geometry("1200x750")
        self.root.minsize(900, 600)
        self._center_window()

        apply_theme(root)

        self._build_header()
        self._build_notebook()
        self._build_statusbar()

    # ── Layout helpers ───────────────────────────────────────────

    def _center_window(self):
        self.root.update_idletasks()
        w = 1200
        h = 750
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_header(self):
        header = tk.Frame(self.root, bg=C_HEADER, height=60)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        logo_lbl = tk.Label(
            header, text="⚡  InstaBill",
            bg=C_HEADER, fg=C_WHITE,
            font=("Segoe UI", 20, "bold")
        )
        logo_lbl.pack(side="left", padx=20, pady=10)

        tagline = tk.Label(
            header, text="Professional Billing & Receipt Manager",
            bg=C_HEADER, fg="#8ab4d4",
            font=("Segoe UI", 10)
        )
        tagline.pack(side="left", padx=5, pady=10)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # Clients tab
        clients_frame = ttk.Frame(self.notebook)
        self.notebook.add(clients_frame, text="  👥  Clients  ")
        self.clients_tab = ClientsTab(clients_frame, self)

        # Inventory tab
        inventory_frame = ttk.Frame(self.notebook)
        self.notebook.add(inventory_frame, text="  📦  Inventory  ")
        self.inventory_tab = InventoryTab(inventory_frame, self)

        # Billing tab
        billing_frame = ttk.Frame(self.notebook)
        self.notebook.add(billing_frame, text="  🧾  Create Bill  ")
        self.billing_tab = BillingTab(billing_frame, self)

        # Ledger tab
        ledger_frame = ttk.Frame(self.notebook)
        self.notebook.add(ledger_frame, text="  📊  Ledger  ")
        self.ledger_tab = LedgerTab(ledger_frame, self)

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Ready")
        bar = tk.Frame(self.root, bg=C_HEADER, height=24)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        tk.Label(
            bar, textvariable=self.status_var,
            bg=C_HEADER, fg="#8ab4d4",
            font=("Segoe UI", 9), anchor="w"
        ).pack(side="left", padx=12, pady=3)

    # ── Public helpers ───────────────────────────────────────────

    def set_status(self, msg: str):
        self.status_var.set(msg)

    def switch_to_billing(self):
        self.notebook.select(2)

    def switch_to_ledger(self):
        self.notebook.select(3)

    def refresh_billing_clients(self):
        """Called after client changes so billing tab dropdown stays fresh."""
        self.billing_tab.refresh_clients()
        self.ledger_tab.refresh_clients()
