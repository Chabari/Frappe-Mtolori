from mtolori_api.utils import *
import logging

@frappe.whitelist(allow_guest=True)  
def price_group():
    items = frappe.db.sql("""
        SELECT name, price_list_name, price_list_id
        FROM `tabPrice List`
        WHERE enabled=1
    """, as_dict=1)
    frappe.enqueue('mtolori_api.pricing.save_price_group', queue='short', items=items)


    return "Success. Data queued for processing"
    
def save_price_group(items):
    logging.info(f"save_price_group called with items: {items}")

    try:
        for item in items:
            payload = {
                "name": item.price_list_name,
                "price_list": item.price_list_id,
                "active": True,
                "erp_serial": item.name,
                "shop": 1
            }   
            res = get(f'/price-group/{item.name}/')
            if not res:
                res = post(f'/price-group/', payload)
            else:
                res = patch(f'/price-group/{item.name}/', payload)

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
     
    
@frappe.whitelist(allow_guest=True)  
def test_price(name):
    try:
        doc = frappe.get_doc("Price List", name)
        payload = {
            "name": doc.price_list_name,
            "price_list": doc.price_list_id,
            "active": True,
            "erp_serial": doc.name,
            "shop": 1
        }   
        res = get(f'/price-group/{doc.name}/')
        if not res:
            res = post(f'/price-group/', payload)
        else:
            res = patch(f'/price-group/{doc.name}/', payload)
            
        frappe.db.commit() 
        frappe.response.message = res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Order not created"
 
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
            SELECT name, item_code, price_list, price_list_rate, buying, selling
            FROM `tabItem Price`
            WHERE disabled=0
        """, as_dict=1)
        
        frappe.enqueue(save_price, queue='short', items=items)
                    
        return "Success"
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Order not created"
    
def save_customers(customers):
    try:
        for cus in customers:
            if cus.mobile_contact_no and cus.default_price_list:
                payload = {
                    "phone_number": cus.mobile_contact_no,
                    "group": cus.default_price_list,
                    "shop": 1
                }   
                res = post(f'/price-bias-lookup/', payload)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    
@frappe.whitelist(allow_guest=True)  
def sync_customers():
    customers = frappe.db.sql("""
            SELECT name, default_price_list, mobile_contact_no
            FROM `tabCustomer`
            WHERE disabled=0
        """, as_dict=1)
    frappe.enqueue(save_customers, queue='short', customers=customers)
    return "Success"
            