"""
models.py - Simple data model classes (thin wrappers for clarity).
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Client:
    id: int = 0
    business_name: str = ""
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Client":
        return cls(
            id=d.get("id", 0),
            business_name=d.get("business_name", ""),
            contact_person=d.get("contact_person", ""),
            phone=d.get("phone", ""),
            email=d.get("email", ""),
            address=d.get("address", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class InventoryItem:
    id: int = 0
    name: str = ""
    description: str = ""
    unit_price: float = 0.0
    unit: str = "pcs"
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "InventoryItem":
        return cls(
            id=d.get("id", 0),
            name=d.get("name", ""),
            description=d.get("description", ""),
            unit_price=d.get("unit_price", 0.0),
            unit=d.get("unit", "pcs"),
            created_at=d.get("created_at", ""),
        )


@dataclass
class BillItem:
    item_name: str = ""
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0


@dataclass
class Bill:
    id: int = 0
    client_id: int = 0
    bill_number: str = ""
    bill_date: str = ""
    due_date: str = ""
    subtotal: float = 0.0
    tax_percent: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    status: str = "pending"
    notes: str = ""
    created_at: str = ""
    items: List[BillItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Bill":
        return cls(
            id=d.get("id", 0),
            client_id=d.get("client_id", 0),
            bill_number=d.get("bill_number", ""),
            bill_date=d.get("bill_date", ""),
            due_date=d.get("due_date", ""),
            subtotal=d.get("subtotal", 0.0),
            tax_percent=d.get("tax_percent", 0.0),
            tax_amount=d.get("tax_amount", 0.0),
            total=d.get("total", 0.0),
            status=d.get("status", "pending"),
            notes=d.get("notes", ""),
            created_at=d.get("created_at", ""),
        )


@dataclass
class Payment:
    id: int = 0
    bill_id: int = 0
    amount: float = 0.0
    payment_date: str = ""
    payment_method: str = "cash"
    notes: str = ""
    created_at: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Payment":
        return cls(
            id=d.get("id", 0),
            bill_id=d.get("bill_id", 0),
            amount=d.get("amount", 0.0),
            payment_date=d.get("payment_date", ""),
            payment_method=d.get("payment_method", "cash"),
            notes=d.get("notes", ""),
            created_at=d.get("created_at", ""),
        )
