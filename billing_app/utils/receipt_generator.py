"""
receipt_generator.py - Generate formatted text receipts and optional PDF.
"""
import os
from datetime import datetime

# Business info – edit these to customise the receipt header
BUSINESS_NAME = "Your Business Name"
BUSINESS_ADDRESS = "123 Main Street, City, State - 000000"
BUSINESS_PHONE = "+1 (555) 000-0000"
BUSINESS_EMAIL = "contact@yourbusiness.com"
BUSINESS_GSTIN = ""          # e.g. "GSTIN: 22AAAAA0000A1Z5"
CURRENCY_SYMBOL = "$"


def fmt_currency(amount: float) -> str:
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def fmt_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to DD/MM/YYYY, or return as-is."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return date_str or ""


def generate_text_receipt(bill: dict, client: dict, items: list,
                           payments: list) -> str:
    """Return a fully formatted plain-text receipt string."""
    LINE = "=" * 60
    THIN = "-" * 60

    paid_total = sum(p.get("amount", 0) for p in payments)
    balance = bill.get("total", 0) - paid_total
    status = bill.get("status", "pending").upper()

    lines = []

    # ── Header ──────────────────────────────────────────────────
    lines.append(LINE)
    lines.append(BUSINESS_NAME.center(60))
    lines.append(BUSINESS_ADDRESS.center(60))
    lines.append(f"Phone: {BUSINESS_PHONE}   Email: {BUSINESS_EMAIL}".center(60))
    if BUSINESS_GSTIN:
        lines.append(BUSINESS_GSTIN.center(60))
    lines.append(LINE)
    lines.append("INVOICE / RECEIPT".center(60))
    lines.append(LINE)

    # ── Bill meta ────────────────────────────────────────────────
    lines.append(f"Bill No : {bill.get('bill_number', '')}")
    lines.append(f"Date    : {fmt_date(bill.get('bill_date', ''))}")
    due = bill.get("due_date", "")
    if due:
        lines.append(f"Due Date: {fmt_date(due)}")
    lines.append(f"Status  : {status}")
    lines.append(THIN)

    # ── Client info ──────────────────────────────────────────────
    lines.append("BILL TO:")
    lines.append(f"  {client.get('business_name', '')}")
    cp = client.get("contact_person", "")
    if cp:
        lines.append(f"  Attn: {cp}")
    addr = client.get("address", "")
    if addr:
        for a_line in addr.split("\n"):
            lines.append(f"  {a_line}")
    ph = client.get("phone", "")
    if ph:
        lines.append(f"  Phone: {ph}")
    em = client.get("email", "")
    if em:
        lines.append(f"  Email: {em}")
    lines.append(THIN)

    # ── Items table ──────────────────────────────────────────────
    col_w = [28, 6, 12, 12]
    hdr = (
        f"{'Item':<{col_w[0]}}"
        f"{'Qty':>{col_w[1]}}"
        f"{'Unit Price':>{col_w[2]}}"
        f"{'Amount':>{col_w[3]}}"
    )
    lines.append(hdr)
    lines.append(THIN)
    for item in items:
        name = str(item.get("item_name", ""))
        desc = str(item.get("description", ""))
        qty = item.get("quantity", 1)
        up = item.get("unit_price", 0)
        amt = item.get("amount", 0)

        # Wrap long name
        if len(name) > col_w[0]:
            lines.append(
                f"{name[:col_w[0]]:<{col_w[0]}}"
                f"{qty:>{col_w[1]}}"
                f"{fmt_currency(up):>{col_w[2]}}"
                f"{fmt_currency(amt):>{col_w[3]}}"
            )
            remainder = name[col_w[0]:]
            while remainder:
                lines.append(f"  {remainder[:col_w[0]-2]}")
                remainder = remainder[col_w[0]-2:]
        else:
            lines.append(
                f"{name:<{col_w[0]}}"
                f"{qty:>{col_w[1]}}"
                f"{fmt_currency(up):>{col_w[2]}}"
                f"{fmt_currency(amt):>{col_w[3]}}"
            )
        if desc:
            lines.append(f"  ({desc})")

    lines.append(THIN)

    # ── Totals ───────────────────────────────────────────────────
    subtotal = bill.get("subtotal", 0)
    tax_pct = bill.get("tax_percent", 0)
    tax_amt = bill.get("tax_amount", 0)
    total = bill.get("total", 0)

    r_width = col_w[0] + col_w[1] + col_w[2]
    lines.append(f"{'Subtotal':<{r_width}}{fmt_currency(subtotal):>{col_w[3]}}")
    if tax_pct:
        lines.append(
            f"{f'Tax ({tax_pct:.1f}%)':<{r_width}}{fmt_currency(tax_amt):>{col_w[3]}}"
        )
    lines.append(THIN)
    lines.append(f"{'TOTAL':<{r_width}}{fmt_currency(total):>{col_w[3]}}")
    lines.append(THIN)

    # ── Payment info ─────────────────────────────────────────────
    lines.append(f"{'Amount Paid':<{r_width}}{fmt_currency(paid_total):>{col_w[3]}}")
    lines.append(f"{'Balance Due':<{r_width}}{fmt_currency(balance):>{col_w[3]}}")

    if payments:
        lines.append("")
        lines.append("Payment History:")
        for p in payments:
            lines.append(
                f"  {fmt_date(p.get('payment_date',''))}  "
                f"{p.get('payment_method','').capitalize():<10}  "
                f"{fmt_currency(p.get('amount',0))}"
            )

    # ── Notes ────────────────────────────────────────────────────
    notes = bill.get("notes", "")
    if notes:
        lines.append(THIN)
        lines.append("Notes:")
        for n in notes.split("\n"):
            lines.append(f"  {n}")

    # ── Footer ───────────────────────────────────────────────────
    lines.append(LINE)
    lines.append("Thank you for your business!".center(60))
    lines.append(f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}".center(60))
    lines.append(LINE)

    return "\n".join(lines)


def save_text_receipt(content: str, filepath: str) -> None:
    """Write the text receipt to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def save_pdf_receipt(bill: dict, client: dict, items: list,
                     payments: list, filepath: str) -> bool:
    """
    Generate a PDF receipt using reportlab.
    Returns True on success, False if reportlab is not installed.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    except ImportError:
        return False

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    PRIMARY = colors.HexColor("#1a3a5c")
    GREEN = colors.HexColor("#27ae60")
    RED = colors.HexColor("#e74c3c")

    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        textColor=PRIMARY, fontSize=18, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        textColor=colors.grey, fontSize=9, spaceAfter=2
    )
    normal = ParagraphStyle(
        "norm", parent=styles["Normal"], fontSize=10, spaceAfter=2
    )
    bold_style = ParagraphStyle(
        "bold", parent=styles["Normal"],
        fontSize=10, spaceAfter=2, fontName="Helvetica-Bold"
    )
    right_bold = ParagraphStyle(
        "rbold", parent=styles["Normal"],
        fontSize=11, alignment=TA_RIGHT, fontName="Helvetica-Bold"
    )

    story = []

    # Header
    story.append(Paragraph(BUSINESS_NAME, title_style))
    story.append(Paragraph(BUSINESS_ADDRESS, sub_style))
    story.append(Paragraph(
        f"Phone: {BUSINESS_PHONE}  |  Email: {BUSINESS_EMAIL}", sub_style
    ))
    if BUSINESS_GSTIN:
        story.append(Paragraph(BUSINESS_GSTIN, sub_style))
    story.append(HRFlowable(width="100%", color=PRIMARY, thickness=2))
    story.append(Spacer(1, 4 * mm))

    # Invoice title row
    paid_total = sum(p.get("amount", 0) for p in payments)
    balance = bill.get("total", 0) - paid_total
    status = bill.get("status", "pending").upper()
    status_color = GREEN if status == "PAID" else (
        colors.orange if status == "PARTIAL" else RED
    )

    header_data = [
        [
            Paragraph("<b>INVOICE / RECEIPT</b>", ParagraphStyle(
                "ih", parent=styles["Normal"], fontSize=14, textColor=PRIMARY,
                fontName="Helvetica-Bold"
            )),
            Paragraph(
                f'<font color="{status_color.hexval()}">[{status}]</font>',
                ParagraphStyle("sh", parent=styles["Normal"], fontSize=12,
                               alignment=TA_RIGHT, fontName="Helvetica-Bold")
            )
        ]
    ]
    ht = Table(header_data, colWidths=["70%", "30%"])
    ht.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(ht)
    story.append(Spacer(1, 4 * mm))

    # Bill meta + Client info side by side
    meta_lines = [
        f"<b>Bill No:</b> {bill.get('bill_number','')}",
        f"<b>Date:</b> {fmt_date(bill.get('bill_date',''))}",
    ]
    if bill.get("due_date"):
        meta_lines.append(f"<b>Due Date:</b> {fmt_date(bill.get('due_date',''))}")

    client_lines = [
        f"<b>Bill To:</b>",
        client.get("business_name", ""),
    ]
    cp = client.get("contact_person", "")
    if cp:
        client_lines.append(f"Attn: {cp}")
    addr = client.get("address", "")
    if addr:
        client_lines.extend(addr.split("\n"))
    ph = client.get("phone", "")
    if ph:
        client_lines.append(f"Phone: {ph}")

    meta_para = Paragraph("<br/>".join(meta_lines), normal)
    client_para = Paragraph("<br/>".join(client_lines), normal)
    info_table = Table([[meta_para, client_para]], colWidths=["40%", "60%"])
    info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    # Items table
    item_header = ["Item", "Description", "Qty", "Unit Price", "Amount"]
    table_data = [item_header]
    for item in items:
        table_data.append([
            item.get("item_name", ""),
            item.get("description", ""),
            f"{item.get('quantity', 1):g}",
            fmt_currency(item.get("unit_price", 0)),
            fmt_currency(item.get("amount", 0)),
        ])

    col_widths = ["25%", "30%", "10%", "17%", "18%"]
    page_w = A4[0] - 30 * mm
    abs_widths = [page_w * float(w.strip("%")) / 100 for w in col_widths]

    items_table = Table(table_data, colWidths=abs_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # Totals
    totals_data = []
    totals_data.append(["", "Subtotal:", fmt_currency(bill.get("subtotal", 0))])
    if bill.get("tax_percent"):
        totals_data.append(
            ["", f"Tax ({bill.get('tax_percent',0):.1f}%):", fmt_currency(bill.get("tax_amount", 0))]
        )
    totals_data.append(["", "TOTAL:", fmt_currency(bill.get("total", 0))])
    totals_data.append(["", "Amount Paid:", fmt_currency(paid_total)])
    totals_data.append(["", "Balance Due:", fmt_currency(balance)])

    totals_table = Table(totals_data, colWidths=[page_w * 0.55, page_w * 0.27, page_w * 0.18])
    total_row = 2 if not bill.get("tax_percent") else 3
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (1, total_row), (-1, total_row), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (1, total_row), (-1, total_row), 1, PRIMARY),
        ("LINEBELOW", (1, total_row), (-1, total_row), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(totals_table)

    # Payment history
    if payments:
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", color=colors.lightgrey))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Payment History</b>", bold_style))
        pay_data = [["Date", "Method", "Amount", "Notes"]]
        for p in payments:
            pay_data.append([
                fmt_date(p.get("payment_date", "")),
                p.get("payment_method", "").capitalize(),
                fmt_currency(p.get("amount", 0)),
                p.get("notes", ""),
            ])
        pay_table = Table(pay_data, colWidths=[page_w * 0.2, page_w * 0.2, page_w * 0.2, page_w * 0.4])
        pay_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf2")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(pay_table)

    # Notes
    if bill.get("notes"):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"<b>Notes:</b> {bill.get('notes','')}", normal))

    # Footer
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", color=PRIMARY, thickness=1))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Thank you for your business!",
        ParagraphStyle("foot", parent=styles["Normal"], alignment=TA_CENTER,
                       textColor=PRIMARY, fontSize=11, fontName="Helvetica-Bold")
    ))
    story.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("gen", parent=styles["Normal"], alignment=TA_CENTER,
                       textColor=colors.grey, fontSize=8)
    ))

    doc.build(story)
    return True
