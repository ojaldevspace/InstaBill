"""
receipt_generator.py - Generate formatted receipts matching the InstaBill invoice style.

Invoice layout (mirrors the Frame Zone / InstaBill design):
  - Business name + address top-left
  - "BILL OF SUPPLY / ORIGINAL FOR RECIPIENT" badge top-right
  - Invoice No, Invoice Date, Due Date row
  - Bill To section with client name + mobile
  - Items table: No | Items | Qty | Rate | Total
  - Subtotal row, Total Amount, Received Amount
  - Total Amount in words
"""
import os
from datetime import datetime

# ── Business info — edit these to match your business ────────────────
BUSINESS_NAME    = "InstaBill"
BUSINESS_ADDRESS = "Your City, Your State"
BUSINESS_PHONE   = ""
BUSINESS_EMAIL   = ""
BUSINESS_GSTIN   = ""   # e.g. "GSTIN: 22AAAAA0000A1Z5"
CURRENCY_SYMBOL  = "₹"


# ── Helpers ───────────────────────────────────────────────────────────

def fmt_currency(amount: float) -> str:
    return f"{CURRENCY_SYMBOL} {amount:,.2f}"


def fmt_currency_plain(amount: float) -> str:
    """No space, for tight columns."""
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def fmt_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return date_str or ""


def _amount_in_words(amount: float) -> str:
    """Convert a rupee amount to words (handles up to crores)."""
    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
        "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "Sixteen", "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty",
        "Sixty", "Seventy", "Eighty", "Ninety",
    ]

    def _two_digits(n: int) -> str:
        if n < 20:
            return ones[n]
        return (tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")).strip()

    def _three_digits(n: int) -> str:
        if n >= 100:
            rest = _two_digits(n % 100)
            return ones[n // 100] + " Hundred" + (" " + rest if rest else "")
        return _two_digits(n)

    rupees = int(amount)
    paise  = round((amount - rupees) * 100)

    if rupees == 0 and paise == 0:
        return "Zero Rupees"

    parts = []
    if rupees >= 10_000_000:
        parts.append(_three_digits(rupees // 10_000_000) + " Crore")
        rupees %= 10_000_000
    if rupees >= 100_000:
        parts.append(_three_digits(rupees // 100_000) + " Lakh")
        rupees %= 100_000
    if rupees >= 1_000:
        parts.append(_three_digits(rupees // 1_000) + " Thousand")
        rupees %= 1_000
    if rupees > 0:
        parts.append(_three_digits(rupees))

    result = " ".join(parts).strip() + " Rupees"
    if paise:
        result += f" and {_two_digits(paise)} Paise"
    return result


# ── Plain-text receipt ────────────────────────────────────────────────

def generate_text_receipt(bill: dict, client: dict, items: list,
                           payments: list) -> str:
    """Return a formatted plain-text receipt string."""
    W    = 64
    LINE = "=" * W
    THIN = "-" * W

    paid_total = sum(p.get("amount", 0) for p in payments)
    total      = bill.get("total", 0)
    balance    = total - paid_total

    lines = []

    # Header
    lines.append(LINE)
    lines.append(BUSINESS_NAME.center(W))
    if BUSINESS_ADDRESS:
        lines.append(BUSINESS_ADDRESS.center(W))
    if BUSINESS_PHONE or BUSINESS_EMAIL:
        contact = "  |  ".join(filter(None, [BUSINESS_PHONE, BUSINESS_EMAIL]))
        lines.append(contact.center(W))
    if BUSINESS_GSTIN:
        lines.append(BUSINESS_GSTIN.center(W))
    lines.append(LINE)
    lines.append("BILL OF SUPPLY".center(W))
    lines.append("ORIGINAL FOR RECIPIENT".center(W))
    lines.append(LINE)

    # Invoice meta
    inv_no   = bill.get("bill_number", "")
    inv_date = fmt_date(bill.get("bill_date", ""))
    due_date = fmt_date(bill.get("due_date", ""))
    lines.append(f"  Invoice No.: {inv_no:<20}  Invoice Date: {inv_date}")
    if due_date:
        lines.append(f"  Due Date   : {due_date}")
    lines.append(THIN)

    # Bill To
    lines.append("  Bill To")
    lines.append(f"  {client.get('business_name', '')}")
    cp = client.get("contact_person", "")
    if cp:
        lines.append(f"  {cp}")
    ph = client.get("phone", "")
    if ph:
        lines.append(f"  Mobile {ph}")
    addr = client.get("address", "")
    if addr:
        for a in addr.split("\n"):
            lines.append(f"  {a}")
    lines.append(THIN)

    # Items table header
    lines.append(f"  {'No':<4} {'Items':<26} {'Qty':>8}  {'Rate':>8}  {'Total':>8}")
    lines.append(THIN)

    # Items rows
    for idx, item in enumerate(items, 1):
        name = str(item.get("item_name", ""))
        qty  = item.get("quantity", 1)
        rate = item.get("unit_price", 0)
        amt  = item.get("amount", 0)
        unit = ""  # unit is stored in description or item name context
        qty_str = f"{qty:g} PCS"
        lines.append(
            f"  {idx:<4} {name:<26} {qty_str:>8}  {rate:>8.0f}  {amt:>8.0f}"
        )
        desc = item.get("description", "")
        if desc:
            lines.append(f"       ({desc})")

    lines.append(THIN)

    # Subtotal
    subtotal   = bill.get("subtotal", 0)
    tax_pct    = bill.get("tax_percent", 0)
    tax_amt    = bill.get("tax_amount", 0)
    qty_total  = sum(item.get("quantity", 0) for item in items)

    lines.append(
        f"  {'SUBTOTAL':<30} {qty_total:>8g}  {'':>8}  {CURRENCY_SYMBOL}{subtotal:>7.0f}"
    )
    if tax_pct:
        lines.append(
            f"  {'Tax (' + str(tax_pct) + '%)':<38}  {CURRENCY_SYMBOL}{tax_amt:>7.0f}"
        )
    lines.append(THIN)

    # Totals
    lines.append(f"  {'Total Amount':<38}  {CURRENCY_SYMBOL} {total:,.2f}")
    lines.append(f"  {'Received Amount':<38}  {CURRENCY_SYMBOL} {paid_total:,.2f}")
    if balance > 0.01:
        lines.append(f"  {'Balance Due':<38}  {CURRENCY_SYMBOL} {balance:,.2f}")
    lines.append(THIN)

    # Amount in words
    lines.append(f"  Total Amount (in words)")
    lines.append(f"  {_amount_in_words(total)}")

    # Payment history
    if payments:
        lines.append(THIN)
        lines.append("  Payment History:")
        for p in payments:
            lines.append(
                f"    {fmt_date(p.get('payment_date','')):<14}"
                f"  {p.get('payment_method','').capitalize():<10}"
                f"  {CURRENCY_SYMBOL} {p.get('amount', 0):,.2f}"
            )

    # Notes
    notes = bill.get("notes", "")
    if notes:
        lines.append(THIN)
        lines.append("  Notes:")
        for n in notes.split("\n"):
            lines.append(f"    {n}")

    # Footer
    lines.append(LINE)
    lines.append("Thank you for your business!".center(W))
    lines.append(f"Generated by InstaBill on {datetime.now().strftime('%d/%m/%Y %H:%M')}".center(W))
    lines.append(LINE)

    return "\n".join(lines)


def save_text_receipt(content: str, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# ── PDF receipt ───────────────────────────────────────────────────────

def save_pdf_receipt(bill: dict, client: dict, items: list,
                     payments: list, filepath: str) -> bool:
    """
    Generate a PDF invoice matching the Frame Zone / InstaBill style.
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

    PAGE_W, PAGE_H = A4
    L_MARGIN = R_MARGIN = 15 * mm
    CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN

    # ── Colours (matches the invoice PDF style) ──────────────────
    NAVY       = colors.HexColor("#1a3a5c")
    GOLD       = colors.HexColor("#c8a84b")
    LIGHT_GREY = colors.HexColor("#f2f2f2")
    MID_GREY   = colors.HexColor("#cccccc")
    WHITE      = colors.white
    GREEN      = colors.HexColor("#27ae60")
    RED        = colors.HexColor("#e74c3c")
    ORANGE     = colors.HexColor("#e67e22")

    styles = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    biz_name_style = ps("biz", fontSize=22, fontName="Helvetica-Bold",
                        textColor=NAVY, spaceAfter=2)
    biz_addr_style = ps("addr", fontSize=9, textColor=colors.grey, spaceAfter=1)
    badge_style    = ps("badge", fontSize=9, fontName="Helvetica-Bold",
                        textColor=NAVY, alignment=TA_RIGHT)
    badge_sub_style = ps("bsub", fontSize=7, textColor=colors.grey,
                         alignment=TA_RIGHT)
    label_style    = ps("lbl", fontSize=9, textColor=colors.grey)
    value_style    = ps("val", fontSize=9, fontName="Helvetica-Bold",
                        textColor=NAVY)
    section_style  = ps("sec", fontSize=9, fontName="Helvetica-Bold",
                        textColor=NAVY, spaceAfter=2)
    normal_style   = ps("norm", fontSize=9, textColor=colors.HexColor("#333333"))
    total_label    = ps("tl", fontSize=10, fontName="Helvetica-Bold",
                        textColor=NAVY, alignment=TA_RIGHT)
    total_value    = ps("tv", fontSize=11, fontName="Helvetica-Bold",
                        textColor=NAVY, alignment=TA_RIGHT)
    words_style    = ps("words", fontSize=9, textColor=colors.grey,
                        spaceAfter=2)
    footer_style   = ps("foot", fontSize=8, textColor=colors.grey,
                        alignment=TA_CENTER)

    # ── Build story ──────────────────────────────────────────────
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=R_MARGIN, leftMargin=L_MARGIN,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    story = []

    paid_total = sum(p.get("amount", 0) for p in payments)
    total      = bill.get("total", 0)
    balance    = total - paid_total
    status     = bill.get("status", "pending").upper()

    # ── TOP ROW: Business info left | BILL OF SUPPLY badge right ─
    biz_lines = [Paragraph(BUSINESS_NAME, biz_name_style)]
    if BUSINESS_ADDRESS:
        biz_lines.append(Paragraph(BUSINESS_ADDRESS, biz_addr_style))
    if BUSINESS_PHONE:
        biz_lines.append(Paragraph(f"📞 {BUSINESS_PHONE}", biz_addr_style))
    if BUSINESS_EMAIL:
        biz_lines.append(Paragraph(f"✉ {BUSINESS_EMAIL}", biz_addr_style))
    if BUSINESS_GSTIN:
        biz_lines.append(Paragraph(BUSINESS_GSTIN, biz_addr_style))

    from reportlab.platypus import KeepInFrame
    biz_cell = biz_lines

    # Badge cell (right side)
    badge_cell = [
        Paragraph("BILL OF SUPPLY", badge_style),
        Paragraph("ORIGINAL FOR RECIPIENT", badge_sub_style),
    ]

    top_table = Table(
        [[biz_cell, badge_cell]],
        colWidths=[CONTENT_W * 0.65, CONTENT_W * 0.35],
    )
    top_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW",    (0, 0), (-1, 0),  1.5, GOLD),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 4 * mm))

    # ── INVOICE META ROW ─────────────────────────────────────────
    inv_no   = bill.get("bill_number", "")
    inv_date = fmt_date(bill.get("bill_date", ""))
    due_date = fmt_date(bill.get("due_date", ""))

    meta_data = [[
        Paragraph("Invoice No.", label_style),
        Paragraph("Invoice Date", label_style),
        Paragraph("Due Date", label_style),
        Paragraph("Status", label_style),
    ], [
        Paragraph(inv_no, value_style),
        Paragraph(inv_date, value_style),
        Paragraph(due_date or "—", value_style),
        Paragraph(status, ps("st", fontSize=9, fontName="Helvetica-Bold",
                              textColor=(GREEN if status == "PAID"
                                         else ORANGE if status == "PARTIAL"
                                         else RED))),
    ]]
    meta_table = Table(meta_data,
                       colWidths=[CONTENT_W * 0.2] * 4)
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  LIGHT_GREY),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",         (0, 0), (-1, -1), 0.4, MID_GREY),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4 * mm))

    # ── BILL TO ──────────────────────────────────────────────────
    bill_to_lines = [Paragraph("Bill To", section_style)]
    bill_to_lines.append(
        Paragraph(f"<b>{client.get('business_name', '')}</b>", normal_style))
    cp = client.get("contact_person", "")
    if cp:
        bill_to_lines.append(Paragraph(cp, normal_style))
    ph = client.get("phone", "")
    if ph:
        bill_to_lines.append(
            Paragraph(f"<b>Mobile</b> {ph}", normal_style))
    addr = client.get("address", "")
    if addr:
        for a in addr.split("\n"):
            bill_to_lines.append(Paragraph(a, normal_style))
    em = client.get("email", "")
    if em:
        bill_to_lines.append(Paragraph(em, normal_style))

    bt_table = Table([[bill_to_lines]], colWidths=[CONTENT_W])
    bt_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.4, MID_GREY),
    ]))
    story.append(bt_table)
    story.append(Spacer(1, 4 * mm))

    # ── ITEMS TABLE ──────────────────────────────────────────────
    col_w = [
        CONTENT_W * 0.06,   # No
        CONTENT_W * 0.38,   # Items
        CONTENT_W * 0.18,   # Qty
        CONTENT_W * 0.18,   # Rate
        CONTENT_W * 0.20,   # Total
    ]

    def th(text):
        return Paragraph(text, ps("th", fontSize=9, fontName="Helvetica-Bold",
                                   textColor=WHITE, alignment=TA_CENTER))

    def td_left(text):
        return Paragraph(str(text), ps("td", fontSize=9, textColor=colors.HexColor("#333")))

    def td_right(text):
        return Paragraph(str(text), ps("tdr", fontSize=9,
                                        textColor=colors.HexColor("#333"),
                                        alignment=TA_RIGHT))

    table_data = [[th("No"), th("Items"), th("Qty."), th("Rate"), th("Total")]]

    for idx, item in enumerate(items, 1):
        name = item.get("item_name", "")
        desc = item.get("description", "")
        display_name = name + (f"\n({desc})" if desc else "")
        qty  = item.get("quantity", 1)
        rate = item.get("unit_price", 0)
        amt  = item.get("amount", 0)
        qty_str = f"{qty:g} PCS"
        table_data.append([
            td_right(str(idx)),
            td_left(display_name),
            td_right(qty_str),
            td_right(f"{rate:,.0f}"),
            td_right(f"{amt:,.0f}"),
        ])

    # Subtotal row
    qty_total = sum(item.get("quantity", 0) for item in items)
    subtotal  = bill.get("subtotal", 0)
    table_data.append([
        Paragraph("", normal_style),
        Paragraph("<b>SUBTOTAL</b>", ps("sbt", fontSize=9,
                                         fontName="Helvetica-Bold",
                                         textColor=NAVY)),
        td_right(f"{qty_total:g}"),
        Paragraph("", normal_style),
        Paragraph(f"<b>{CURRENCY_SYMBOL} {subtotal:,.0f}</b>",
                  ps("sbv", fontSize=9, fontName="Helvetica-Bold",
                     textColor=NAVY, alignment=TA_RIGHT)),
    ])

    items_table = Table(table_data, colWidths=col_w, repeatRows=1)

    n_items = len(items)
    row_bgs = []
    for i in range(1, n_items + 1):
        bg = WHITE if i % 2 == 1 else LIGHT_GREY
        row_bgs.append(("BACKGROUND", (0, i), (-1, i), bg))

    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0),  (-1, 0),       NAVY),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),       WHITE),
        ("TOPPADDING",    (0, 0),  (-1, -1),      5),
        ("BOTTOMPADDING", (0, 0),  (-1, -1),      5),
        ("LEFTPADDING",   (0, 0),  (-1, -1),      6),
        ("RIGHTPADDING",  (0, 0),  (-1, -1),      6),
        ("GRID",          (0, 0),  (-1, -1),      0.4, MID_GREY),
        ("VALIGN",        (0, 0),  (-1, -1),      "MIDDLE"),
        # Subtotal row styling
        ("BACKGROUND",    (0, -1), (-1, -1),      LIGHT_GREY),
        ("LINEABOVE",     (0, -1), (-1, -1),      1,   NAVY),
    ] + row_bgs))

    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # ── TOTALS SECTION ───────────────────────────────────────────
    tax_pct = bill.get("tax_percent", 0)
    tax_amt = bill.get("tax_amount", 0)

    totals_rows = []
    if tax_pct:
        totals_rows.append([
            Paragraph(f"Tax ({tax_pct:.1f}%)", label_style),
            Paragraph(f"{CURRENCY_SYMBOL} {tax_amt:,.2f}",
                      ps("txa", fontSize=9, alignment=TA_RIGHT,
                         textColor=colors.HexColor("#333"))),
        ])

    totals_rows += [
        [
            Paragraph("<b>Total Amount</b>",
                      ps("ta", fontSize=11, fontName="Helvetica-Bold",
                         textColor=NAVY)),
            Paragraph(f"<b>{CURRENCY_SYMBOL} {total:,.2f}</b>",
                      ps("tav", fontSize=11, fontName="Helvetica-Bold",
                         textColor=NAVY, alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Received Amount",
                      ps("ra", fontSize=9, textColor=colors.grey)),
            Paragraph(f"{CURRENCY_SYMBOL} {paid_total:,.2f}",
                      ps("rav", fontSize=9, textColor=colors.grey,
                         alignment=TA_RIGHT)),
        ],
    ]
    if balance > 0.01:
        totals_rows.append([
            Paragraph("<b>Balance Due</b>",
                      ps("bd", fontSize=9, fontName="Helvetica-Bold",
                         textColor=RED)),
            Paragraph(f"<b>{CURRENCY_SYMBOL} {balance:,.2f}</b>",
                      ps("bdv", fontSize=9, fontName="Helvetica-Bold",
                         textColor=RED, alignment=TA_RIGHT)),
        ])

    totals_col_w = [CONTENT_W * 0.62, CONTENT_W * 0.38]
    tot_table = Table(totals_rows, colWidths=totals_col_w)

    # Find the "Total Amount" row index (after optional tax row)
    total_row_idx = 1 if tax_pct else 0

    tot_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0),  (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 4),
        ("ALIGN",         (1, 0),  (1, -1),  "RIGHT"),
        ("LINEABOVE",     (0, total_row_idx), (-1, total_row_idx), 1, NAVY),
        ("LINEBELOW",     (0, total_row_idx), (-1, total_row_idx), 0.5, MID_GREY),
    ]))
    story.append(tot_table)
    story.append(Spacer(1, 2 * mm))

    # ── AMOUNT IN WORDS ──────────────────────────────────────────
    story.append(HRFlowable(width="100%", color=MID_GREY, thickness=0.5))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Total Amount (in words)</b>", words_style))
    story.append(Paragraph(_amount_in_words(total), normal_style))

    # ── PAYMENT HISTORY (if any) ─────────────────────────────────
    if payments:
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", color=MID_GREY, thickness=0.5))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Payment History</b>", section_style))
        pay_hdr = [
            [Paragraph(h, ps(f"ph{i}", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE, alignment=TA_CENTER))
             for i, h in enumerate(["Date", "Method", "Amount", "Notes"])]
        ]
        pay_rows = []
        for p in payments:
            pay_rows.append([
                Paragraph(fmt_date(p.get("payment_date", "")), normal_style),
                Paragraph(p.get("payment_method", "").capitalize(), normal_style),
                Paragraph(f"{CURRENCY_SYMBOL} {p.get('amount', 0):,.2f}",
                          ps("pav", fontSize=9, alignment=TA_RIGHT)),
                Paragraph(p.get("notes", "") or "", normal_style),
            ])
        pay_table = Table(
            pay_hdr + pay_rows,
            colWidths=[CONTENT_W * 0.18, CONTENT_W * 0.18,
                       CONTENT_W * 0.18, CONTENT_W * 0.46]
        )
        pay_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
            ("GRID",          (0, 0), (-1, -1), 0.4, MID_GREY),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(pay_table)

    # ── NOTES ─────────────────────────────────────────────────────
    if bill.get("notes"):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"<b>Notes:</b> {bill.get('notes', '')}", normal_style))

    # ── FOOTER ────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.5))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Thank you for your business!", footer_style))
    story.append(Paragraph(
        f"Generated by InstaBill · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        footer_style
    ))

    doc.build(story)
    return True
