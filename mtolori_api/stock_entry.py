
from mtolori_api.helper import *
from frappe import _
from frappe.model.document import Document
from frappe.utils import now, nowdate, nowtime
from erpnext.stock.utils import get_incoming_rate

@frappe.whitelist(allow_guest=True)  
def sync_stock():
    frappe.enqueue('mtolori_api.stock_entry.create_stock_entry', queue='long', timeout=60*60*4)
    return "Success"

def create_stock_entry():
    company = frappe.defaults.get_user_default(
                        "Company"
                    ) or frappe.defaults.get_global_default("company")
            
    warehouses = virtual_warehouses()
    for row in warehouses:
        if row.linked_shop:
            items = []
            xitems = frappe.db.sql("""
                SELECT name
                FROM `tabItem`
                WHERE publish_item = 1 AND disabled=0
            """, as_dict=1)
            for itm in xitems:
                balance = get_stock_availability(itm.name, row.linked_shop)
                if balance > 1:
                    qty = get_percent(balance)
                    if qty > 0:
                        args = {
                            "item_code": itm.name,
                            "warehouse": row.linked_shop,
                            "posting_date": nowdate(),
                            "posting_time": nowtime(),
                        }
                        valuation_rate = get_incoming_rate(args)
                        item = frappe._dict({
                                "item_code": itm.name,
                                "qty": qty,
                                "s_warehouse": row.linked_shop,
                                "t_warehouse": row.name,
                                "basic_rate": valuation_rate,
                                "valuation_rate": valuation_rate,
                            }
                        )
                        items.append(item)
            if items:
                stock_entry_doc = frappe.get_doc(
                    dict(
                        doctype="Stock Entry",
                        from_bom=0,
                        posting_date=nowdate(),
                        posting_time=nowtime(),
                        items=items,
                        stock_entry_type="Material Transfer",
                        purpose="Material Transfer",
                        from_warehouse=row.linked_shop,
                        to_warehouse=row.name,
                        company=company,
                        remarks="Material Transfer for Mtolori Virtual Store",
                    )
                )
                stock_entry_doc.insert(ignore_permissions=True)