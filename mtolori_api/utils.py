import frappe
import requests
from erpnext import get_default_company
from datetime import datetime

from requests.auth import HTTPBasicAuth

from frappe.utils import cint, flt
import qrcode


@frappe.whitelist(allow_guest=True)  
def get_data(
	item_code=None, start=0, sort_by="actual_qty", sort_order="desc"
):
    """Return data to render the item dashboard"""
    filters = []
    if item_code:
        filters.append(["item_code", "=", item_code])
        
    warehouses = frappe.get_all("Warehouse", filters={"is_virtual_store": 1}, fields=["name"])
        
    filters.append(["warehouse", "in", [w.name for w in warehouses]])

    items = frappe.db.get_all(
        "Bin",
        fields=[
            "item_code",
            "warehouse",
            "projected_qty",
            "reserved_qty",
            "reserved_qty_for_production",
            "reserved_qty_for_sub_contract",
            "actual_qty",
            "valuation_rate",
        ],
        or_filters={
            "projected_qty": ["!=", 0],
            "reserved_qty": ["!=", 0],
            "reserved_qty_for_production": ["!=", 0],
            "reserved_qty_for_sub_contract": ["!=", 0],
            "actual_qty": ["!=", 0],
        },
        filters=filters,
        order_by=sort_by + " " + sort_order,
        limit_start=start,
        limit_page_length=21,
    )

    precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

    for item in items:
        item.update(
            {
                "item_name": frappe.get_cached_value("Item", item.item_code, "item_name"),
                "disable_quick_entry": frappe.get_cached_value("Item", item.item_code, "has_batch_no")
                or frappe.get_cached_value("Item", item.item_code, "has_serial_no"),
                "projected_qty": flt(item.projected_qty, precision),
                "reserved_qty": flt(item.reserved_qty, precision),
                "reserved_qty_for_production": flt(item.reserved_qty_for_production, precision),
                "reserved_qty_for_sub_contract": flt(item.reserved_qty_for_sub_contract, precision),
                "actual_qty": flt(item.actual_qty, precision),
            }
        )
    return items

def get_main_company():
    return frappe.get_doc("Company", get_default_company())

def mtolori_main_url():
    return get_main_company().mtolori_host_url

def mtolori_api_key():
    return get_main_company().mtolori_api_key

def get_headers():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {mtolori_api_key()}"
    }
    return headers

def get(endpoint):
    response = requests.get(f'{mtolori_main_url()}{endpoint}', headers=get_headers())
    if not response.ok:
        return False
    return response.json()

def post(endpoint, payload):
    response = requests.post(f'{mtolori_main_url()}{endpoint}', headers=get_headers(), json=payload)
    if not response.ok:
        return False
    return response.json()

def patch(endpoint, payload):
    response = requests.patch(f'{mtolori_main_url()}{endpoint}', headers=get_headers(), json=payload)
    if not response.ok:
        return False
    return response.json()

def get_buy_price(code):
    buy_price = frappe.db.get_all(
        "Item Price",
        filters={
            "item_code": code,
            'price_list': "Standard Buying"
        },            
        fields=["price_list_rate"],
        limit=1,
    )
    if buy_price:
        return buy_price.price_list_rate
    return 0
  
@frappe.whitelist(allow_guest=True)  
def sync_items():
    try:
        items = frappe.db.sql("""
            SELECT name
            FROM `tabItem`
            WHERE disabled = 0
        """, as_dict=1)
        company = get_main_company()
        for itm in items:
            doc = frappe.get_doc('Item', itm)    
            inventory = []
            item_data = get_data(doc.item_code)
            for dt in item_data:
                shop = frappe.get_doc("Warehouse", dt.warehouse)
                inventory.append({
                    "shop": shop.shop_id,
                    "quantity": dt.actual_qty,
                    "buying_price": get_buy_price(doc.item_code)
                })
                
            payload = {
                "erp_serial": doc.item_code,
                "name": doc.item_name,
                "description": doc.extended_description or doc.item_name,
                "weight": doc.weight_grams,
                "sku": doc.item_code,
                "subcategory": doc.sub_category,
                "inventory": inventory
            }   
            
            res = get(f'/products/{doc.item_code}/')
            if not res:
                res = post('/products/', payload)
            else:
                res = patch(f'/products/{doc.item_code}/', payload)
                
                # if res and res.status_code == 201:
                #     if res['id']:
                #         doc.item_id = res['id']
                #         doc.save(ignore_permissions = True)
                    
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))