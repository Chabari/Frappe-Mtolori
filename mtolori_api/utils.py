import frappe
import requests
from erpnext import get_default_company
from datetime import datetime
import os
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

        
    # warehouses = frappe.get_all("Warehouse", filters={"is_virtual_store": 1}, fields=["name"])
    warehouses = frappe.get_all("Warehouse", filters={"name": "Mwea Shop Warehouse - MNA"}, fields=["name"])
        
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

def post2(endpoint, payload):
    response = requests.post(f'{mtolori_main_url()}{endpoint}', headers=get_headers(), json=payload)
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
        return buy_price[0].price_list_rate
    return 0

@frappe.whitelist(allow_guest=True)  
def sync_items():
    try:
        xitems = frappe.db.sql("""
            SELECT name
            FROM `tabItem`
        """, as_dict=1)
        items = [itm.name for itm in xitems]
        frappe.enqueue('mtolori_api.utils.save_itm', queue='long', items=items, timeout=60*60*4)
        frappe.response.items_count = len(items)
        return "Success"
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        

@frappe.whitelist(allow_guest=True)  
def sync_the_items(**args):
    try:
        start = cint(args.get('start')) if args.get('start') else 0
        page_length = cint(args.get('page_length')) if args.get('page_length') else 1000
        xitems = frappe.db.sql("""
            SELECT name
            FROM `tabItem`
            LIMIT %(page_length)s OFFSET %(start)s 
        """, {"page_length": page_length, "start": start}, as_dict=1)
        items = [itm.name for itm in xitems]
        frappe.enqueue('mtolori_api.utils.save_itm', queue='long', items=items, timeout=60*60*1)
        frappe.response.pagination = {
            "start": start,
            "page_length": page_length,
            "total_count": frappe.db.count("Item"),
        }
        return "Success"
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        
        
def before_save_item(doc, method):
    try:
        save_itm([doc.name])
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        
def save_itm(items):
    try:
        for itm in items:
            doc = frappe.get_doc('Item', itm)    
            inventory = []
            inventory.append({
                "shop_id": 1,
                "quantity": 5,
                "buying_price": get_buy_price(doc.item_code),
                
            })
            subcategory = 1
            if doc.sub_category:
                subcategory = frappe.get_value("Item Category", doc.sub_category, "id")
                
            payload = {
                "erp_serial": doc.item_code,
                "organization_id" : 1,
                "name": doc.item_name,
                "description": doc.the_extended_description if doc.the_extended_description else doc.description,
                "weight": doc.weight_grams,
                "sku": doc.item_code,
                "subcategory_id": subcategory,
                "is_active": True if doc.publish_item == 1 else False,
                "inventory": inventory
            }   
            
            res = get(f'/products/{doc.item_code}/')
            if not res:
                if doc.publish_item == 1:
                    res = post('/products/', payload)
            else:
                res = patch(f'/products/{doc.item_code}/', payload)
                
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
         
@frappe.whitelist(allow_guest=True)        
def save_ids(items):
    reses = []
    try:
        for itm in items:
            doc = frappe.get_doc('Item', itm)    
            inventory = []
            item_data = get_data(doc.item_code)
            for dt in item_data:
                shop = frappe.get_doc("Warehouse", dt.warehouse)
                inventory.append({
                    "shop_id": shop.shop_id,
                    "quantity": dt.actual_qty,
                    "buying_price": get_buy_price(doc.item_code)
                })
            subcategory = 1
            if doc.sub_category:
                subcategory = frappe.get_value("Item Category", doc.sub_category, "id")
                
            payload = {
                "erp_serial": doc.item_code,
                "organization_id" : 1,
                "name": doc.item_name,
                "description": doc.the_extended_description if doc.the_extended_description else doc.description,
                "weight": doc.weight_grams,
                "sku": doc.item_code,
                "subcategory_id": subcategory,
                "is_active": True,
                "inventory": inventory
            }
            res = get(f'/products/{doc.item_code}/')
            reses.append({
                "get": res
            })
            if not res:
                if doc.publish_item == 1:
                    res = post('/products/', payload)
                    reses.append({
                        "post": res
                    })
            else:
                res = patch(f'/products/{doc.item_code}/', payload)
                reses.append({
                    "patch": res
                })
            
        return reses
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        return str(e)
    
@frappe.whitelist(allow_guest=True) 
def sync_images():
    try:
        items = frappe.db.sql("""
            SELECT name, image, back_image
            FROM `tabItem`
            WHERE disabled = 0 AND publish_item = 1
        """, as_dict=1)
        
        frappe.enqueue('mtolori_api.utils.save_itm_image', queue='long', items=items, timeout=60*60*2)
        return "Success"
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        
def save_itm_image(items):
    try:
        for itm in items:
            if itm.image:
                file_url = itm.image
                file_path = frappe.get_site_path("public", file_url.lstrip('/'))
                if not os.path.exists(file_path):
                    continue  # Skip if the file does not exist

                file_name = os.path.basename(file_path)
                
                payload = {
                    "product__erp_serial": itm.name,
                    "side" : 'front',
                }  
                
                with open(file_path, "rb") as f:
                    files = {
                        'path': (file_name, f, 'image/png')
                    }

                    response = requests.post(f'{mtolori_main_url()}/product-images/', data=payload, files=files)
                if not response.ok:
                    print(f"Failed to upload image for {itm.name}: {response.text}")
                    frappe.log_error("Failed to log", f"Failed to upload front image for {itm.name}: {response.text}")
                    
            if itm.back_image:
                file_url = itm.back_image
                file_path = frappe.get_site_path("public", file_url.lstrip('/'))
                if not os.path.exists(file_path):
                    continue  # Skip if the file does not exist

                file_name = os.path.basename(file_path)
                
                payload = {
                    "product__erp_serial": itm.name,
                    "side" : 'back',
                }  
                
                with open(file_path, "rb") as f:
                    files = {
                        'path': (file_name, f, 'image/png')
                    }

                    response = requests.post(f'{mtolori_main_url()}/product-images/', data=payload, files=files)
                if not response.ok:
                    print(f"Failed to upload image for {itm.name}: {response.text}")
                    frappe.log_error("Failed to log", f"Failed to upload back image for {itm.name}: {response.text}")
                    
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        
@frappe.whitelist(allow_guest=True) 
def get_item(name):
    try:
        item = frappe.get_doc("Item", name)
        if item.image:
            file_url = item.image
            file_path = frappe.get_site_path("public", file_url.lstrip('/'))

            if not os.path.exists(file_path):
                frappe.throw(f"File not found at {file_path}")

            file_name = os.path.basename(file_path)
            
            payload = {
                "product__erp_serial": name,
                "side" : 'front',
            }  
            
            with open(file_path, "rb") as f:
                files = {
                    'path': (file_name, f, 'image/png')
                }

                response = requests.post(f'{mtolori_main_url()}/product-images/', data=payload, files=files)

            frappe.response.payload = response.json()
            frappe.response.file_path = file_path
            frappe.response.file_name = file_name
            return "success"
        return "yeeee"
    except Exception as e:
        print(str(e))
        frappe.log_error(frappe.get_traceback(), str(e))
        
    

@frappe.whitelist(allow_guest=True)  
def initiate_batch_item():
    frappe.enqueue('mtolori_api.utils.batch_item', queue='long', timeout=60*60*4)
    return "Success"

@frappe.whitelist(allow_guest=True)  
def batch_item():
    try:
        chunk_size = 7000
        start = 0
        while True:
            items = frappe.db.sql("""
                SELECT name
                FROM `tabItem`
                LIMIT {start}, {limit}
            """.format(start=start, limit=chunk_size), as_dict=True)
            if not items:
                break
            
            payload = []
            
            for x in items:
                doc = frappe.get_doc('Item', x.name)    
                inventory = []
                inventory.append({
                    "shop_id": 1,
                    "quantity": 5,
                    "buying_price": get_buy_price(doc.item_code),
                    
                })
                subcategory = 1
                if doc.sub_category:
                    subcategory = frappe.get_value("Item Category", doc.sub_category, "id")
                    
                pd = {
                    "erp_serial": doc.item_code,
                    "organization_id" : 1,
                    "name": doc.item_name,
                    "description": doc.the_extended_description if doc.the_extended_description else doc.description,
                    "weight": doc.weight_grams,
                    "sku": doc.item_code,
                    "subcategory_id": subcategory,
                    "is_active": True if doc.publish_item == 1 else False,
                    "inventory": inventory
                }   
                payload.append(pd)
            if payload:
                res = post('/products/', payload)
                        
            start += chunk_size

        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    
