
from mtolori_api.helper import *
from frappe import _
from frappe.model.document import Document
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
            top_selling = get_top_selling_products_this_month(20, row.linked_shop)
            the_top_selling = [x.item_code for x in top_selling]
            for itm in xitems:
                balance = get_stock_availability(itm.name, row.linked_shop)
                if balance > 1:
                    per = 0.1
                    if itm.name in the_top_selling:
                        per = 0.2
                    qty = get_percent(balance, per)
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
                


@frappe.whitelist(allow_guest=True)  
def get_top_selling_products():
    top_selling = get_top_selling_products_this_month(10)
    return [x.item_code for x in top_selling]

def get_top_selling_products_this_month(limit, warehouse=None):
    # Get first and last day of the current month
    start_date = get_first_day(nowdate())
    end_date = get_last_day(nowdate())
    
    conditions = ""
    params = [start_date, end_date]

    if warehouse:
        conditions += " AND sii.warehouse = %s"
        params.append(warehouse)

    # Safe numeric limit formatting
    query = f"""
        SELECT
            sii.item_code,
            sii.item_name,
            SUM(sii.qty) AS total_qty,
            SUM(sii.amount) AS total_amount
        FROM
            `tabSales Invoice Item` sii
        INNER JOIN
            `tabSales Invoice` si ON sii.parent = si.name
        WHERE
            si.docstatus = 1
            AND si.posting_date BETWEEN %s AND %s
            {conditions}
        GROUP BY
            sii.item_code
        ORDER BY
            total_qty DESC
        LIMIT {int(limit)}
    """

    data = frappe.db.sql(query, params, as_dict=True)
    return data
