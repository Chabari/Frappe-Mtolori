from mtolori_api.utils import *
import logging

@frappe.whitelist(allow_guest=True)  
def price_group():
    items = frappe.db.sql("""
        SELECT name, price_list_name, price_list_id, buying, selling
        FROM `tabPrice List`
        WHERE enabled=1
    """, as_dict=1)
    frappe.enqueue('mtolori_api.pricing.save_price_group', queue='long', items=items)

    return "Success. Data queued for processing"
    
def save_price_group(items):
    logging.info(f"save_price_group called with items: {items}")
    try:
        for item in items:
            payload = {
                "name": item.price_list_name,
                "buying": True if item.buying == 1 else False,
                "selling": True if item.selling == 1 else False,
                "shop": 1,
                "erp_serial": item.price_list_id,
                "active": True
            }   
            res = get(f'/price-list/{item.price_list_id}/')
            if not res:
                res = post(f'/price-list/', payload)
            else:
                res = patch(f'/price-list/{item.price_list_id}/', payload)

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
     
@frappe.whitelist(allow_guest=True)  
def test_price(name):
    try:
        doc = frappe.get_doc("Price List", name)
        payload = {
            "name": doc.price_list_name,
            "buying": True if doc.buying == 1 else False,
            "selling": True if doc.selling == 1 else False,
            "shop": 1,
            "erp_serial": doc.price_list_id,
            "active": True
        }
        res = get(f'/price-list/{doc.price_list_id}/')
        if not res:
            res = post(f'/price-list/', payload)
        else:
            res = patch(f'/price-list/{doc.price_list_id}/', payload)
            
        # frappe.db.commit() 
        frappe.response.message = res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Not successful"
 
def before_save(doc, method):
    try:
        
        # payload = {
        #     "name": doc.price_list_name,
        #     "price_list": doc.price_list_id,
        #     "active": True,
        #     "erp_serial": doc.name,
        #     "shop": 1
        # }   
        # res = get(f'/price-group/{doc.name}/')
        # if not res:
        #     res = post(f'/price-group/', payload)
        # else:
        #     res = patch(f'/price-group/{doc.name}/', payload)
        frappe.db.commit() 
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Order not created"
        
def before_save_price(doc, method):
    # save_price(doc)
        
    frappe.db.commit() 
    
def save_price(items):
    try:
        for doc in items:
            price_list = frappe.get_doc("Price List", doc.price_list)
            payload = {
                "shop": 1,
                "product": doc.item_code,
                "price_list": price_list.price_list_id,
                "selling_price": doc.price_list_rate if doc.selling == 1 else 0.0,
                "buying_price": doc.price_list_rate if doc.buying == 1 else 0.0,
                "erp_serial": doc.name
            }   
            res = get(f'/pricing/{doc.name}/')
            if not res:
                res = post(f'/pricing/', payload)
            else:
                res = patch(f'/pricing/{doc.name}/', payload)
                
        frappe.db.commit() 
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    
@frappe.whitelist(allow_guest=True)  
def item_pricing():
    try:
        items = frappe.db.sql("""
            SELECT ip.name, ip.price_list_rate, ip.item_code, ip.price_list, ip.buying, ip.selling
            FROM `tabItem Price` ip
            INNER JOIN `tabItem` i ON ip.item_code = i.name
            WHERE i.disabled = 0 AND i.publish_item = 1 AND ip.disabled = 0
        """, as_dict=True)

        frappe.enqueue('mtolori_api.pricing.save_price', queue='long', items=items)
                    
        return "Success"
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Order not created"
    
 
@frappe.whitelist(allow_guest=True)  
def test_item_price(name):
    try:
        doc = frappe.get_doc("Item Price", name)
        price_list = frappe.get_doc("Price List", doc.price_list)
        payload = {
            "shop": 1,
            "product": doc.item_code,
            "price_list": price_list.price_list_id,
            "selling_price": doc.price_list_rate if doc.selling == 1 else 0.0,
            "buying_price": doc.price_list_rate if doc.buying == 1 else 0.0,
            "erp_serial": doc.name
        }   
        res = get(f'/pricing/{doc.name}/')
        if not res:
            res = post(f'/pricing/', payload)
        else:
            res = patch(f'/pricing/{doc.name}/', payload)
            
        # frappe.db.commit() 
        frappe.response.payload = payload
        frappe.response.message = res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Not successful"
    
def save_customers(customers):
    try:
        for cus in customers:
            if cus.mobile_contact_no:
                customer_group = frappe.get_doc("Customer Group", cus.customer_group)
                default_price_list = None
                if customer_group and customer_group.default_price_list:
                    default_price_list = customer_group.default_price_list
                    
                if cus.default_price_list:
                    default_price_list = cus.default_price_list
                    
                if not default_price_list:
                    continue
                
                price_list = frappe.get_doc("Price List", default_price_list)
                    
                payload = {
                    "phone_number": cus.mobile_contact_no,
                    "price_list__erp_serial": price_list.price_list_id,
                    "shop": 1
                }   
                res = post(f'/price-bias-lookup/', payload)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    
@frappe.whitelist(allow_guest=True)  
def sync_customers():
    customers = frappe.db.sql("""
            SELECT name, default_price_list, mobile_contact_no, customer_group
            FROM `tabCustomer`
            WHERE disabled=0
        """, as_dict=1)
    frappe.enqueue('mtolori_api.pricing.save_customers', queue='long', customers=customers)
    return "Success"
