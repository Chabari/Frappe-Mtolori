import frappe
from frappe import _
import math
from frappe.utils import now, nowdate, nowtime, get_first_day, get_last_day

def virtual_warehouses():
    items = frappe.db.sql("""
        SELECT name, warehouse_name, phone_no, shop_id, linked_shop
        FROM `tabWarehouse`
        WHERE disabled = 0 AND is_virtual_store = 1 AND is_group=0
    """, as_dict=1)
    return items

def get_stock_availability(item_code, warehouse):
    actual_qty = (
        frappe.db.get_value(
            "Stock Ledger Entry",
            filters={
                "item_code": item_code,
                "warehouse": warehouse,
                "is_cancelled": 0,
            },
            fieldname="qty_after_transaction",
            order_by="posting_date desc, posting_time desc, creation desc",
        )
        or 0.0
    )
    return actual_qty

def get_percent(qty, per):
    return math.ceil(per * qty)