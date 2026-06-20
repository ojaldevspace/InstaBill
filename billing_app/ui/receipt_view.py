"""
receipt_view.py - Receipt preview window with export options.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from utils.receipt_generator import (
    generate_text_receipt, save_text_receipt, save_pdf_receipt
)

C_HEADER = "#1a3a5c"
C_BG     = "#f4f7fb"
C_WHITE  = "#ffffff"
C_GREEN  = "#27ae60"
C_RED    = "#e74c3c"


class ReceiptViewWindow(tk.Toplevel):
    """A Toplevel window showing a formatted text receipt with export buttons."""

    def __init__(self, parent, bill: dict, client: dict,
                 items: list, payments: list):
        super().__init__(parent)
        self.title(f"Receipt — {bill.get('bill_number', '')}")
        self.geometry("680x700")
        self.minsize(500, 400)

        self.bill     = bill
        self.client   = client
        self.items    = items
        self.payments = payments

        self._text_content = generate_text_receipt(bill, client, items, payments)
        self._build()

        # Center
        self.update_idletasks()
        pw = parent.winfo_x()
        py = parent.winfo_y()
        pw_w = parent.winfo_width()
        pw_h = parent.winfo_height()
        x = pw + (pw_w - self.winfo_width()) // 2
        y = py + (pw_h - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.grab_set()

    def _build(self):
        # ── Toolbar ──────────────────────────────────────────────
        toolbar = tk.Frame(self, bg=C_HEADER, height=48)
        toolbar.pack(side="top", fill="x")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text=f"🧾  {self.bill.get('bill_number', '')}",
                 bg=C_HEADER, fg="white",
                 font=("Segoe UI", 12, "bold")).pack(
            side="left", padx=14, pady=10)

        ttk.Button(toolbar, text="📄 Export .txt",
                   style="Green.TButton",
                   command=self._export_txt).pack(
            side="right", padx=8, pady=8)
        ttk.Button(toolbar, text="📕 Export PDF",
                   command=self._export_pdf).pack(
            side="right", padx=(0, 4), pady=8)

        # ── Text area ─────────────────────────────────────────────
        text_frame = ttk.Frame(self)
        text_frame.pack(fill="both", expand=True, padx=12, pady=12)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.text_widget = tk.Text(
            text_frame,
            font=("Courier New", 10),
            bg=C_WHITE,
            fg="#2d3436",
            wrap="none",
            state="normal",
            relief="flat",
            padx=12,
            pady=10,
        )
        vsb = ttk.Scrollbar(text_frame, orient="vertical",
                             command=self.text_widget.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal",
                             command=self.text_widget.xview)
        self.text_widget.configure(
            yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.text_widget.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.text_widget.insert("1.0", self._text_content)
        self.text_widget.config(state="disabled")

        # Syntax highlighting for key lines
        self._highlight()

        # ── Close button ─────────────────────────────────────────
        ttk.Button(self, text="✖ Close",
                   command=self.destroy).pack(pady=(0, 10))

    def _highlight(self):
        """Apply colour tags to the receipt text for visual appeal."""
        self.text_widget.config(state="normal")

        self.text_widget.tag_configure(
            "header", foreground=C_HEADER,
            font=("Courier New", 11, "bold"))
        self.text_widget.tag_configure(
            "section", foreground=C_HEADER,
            font=("Courier New", 10, "bold"))
        self.text_widget.tag_configure(
            "total_row", foreground=C_HEADER,
            font=("Courier New", 11, "bold"))
        self.text_widget.tag_configure(
            "paid_row", foreground=C_GREEN,
            font=("Courier New", 10))
        self.text_widget.tag_configure(
            "balance_row", foreground=C_RED,
            font=("Courier New", 10))

        lines = self._text_content.split("\n")
        for i, line in enumerate(lines):
            line_start = f"{i+1}.0"
            line_end   = f"{i+1}.end"
            if "=" * 30 in line or line.strip().startswith("==="):
                self.text_widget.tag_add("header", line_start, line_end)
            elif line.strip() in ("INVOICE / RECEIPT",):
                self.text_widget.tag_add("section", line_start, line_end)
            elif line.startswith("TOTAL"):
                self.text_widget.tag_add("total_row", line_start, line_end)
            elif line.startswith("Amount Paid"):
                self.text_widget.tag_add("paid_row", line_start, line_end)
            elif line.startswith("Balance Due"):
                self.text_widget.tag_add("balance_row", line_start, line_end)

        self.text_widget.config(state="disabled")

    # ── Export helpers ───────────────────────────────────────────

    def _export_txt(self):
        default_name = f"{self.bill.get('bill_number', 'receipt')}.txt"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Receipt as Text"
        )
        if not filepath:
            return
        try:
            save_text_receipt(self._text_content, filepath)
            messagebox.showinfo("Saved",
                                f"Receipt saved to:\n{filepath}",
                                parent=self)
            # Try to open the file
            try:
                os.startfile(filepath)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

    def _export_pdf(self):
        default_name = f"{self.bill.get('bill_number', 'receipt')}.pdf"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save Receipt as PDF"
        )
        if not filepath:
            return
        try:
            success = save_pdf_receipt(
                self.bill, self.client, self.items, self.payments, filepath)
            if success:
                messagebox.showinfo("Saved",
                                    f"PDF receipt saved to:\n{filepath}",
                                    parent=self)
                try:
                    os.startfile(filepath)
                except Exception:
                    pass
            else:
                messagebox.showwarning(
                    "PDF Not Available",
                    "PDF export requires the 'reportlab' library.\n\n"
                    "Install it with:\n  pip install reportlab\n\n"
                    "Use 'Export .txt' in the meantime.",
                    parent=self
                )
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
