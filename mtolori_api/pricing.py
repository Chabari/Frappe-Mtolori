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
        
        items = frappe.db.sql(f"""
            SELECT name, price_list_name, price_list_id, buying, selling
            FROM `tabPrice List`
            WHERE enabled=1 AND name='{doc.name}'
        """, as_dict=1)
        if items:
            frappe.enqueue('mtolori_api.pricing.save_price_group', queue='long', items=items)
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Order not created"
        
def before_save_price(doc, method):
    items = frappe.db.sql(f"""
            SELECT ip.name, ip.price_list_rate, ip.item_code, ip.price_list, ip.buying, ip.selling
            FROM `tabItem Price` ip
            INNER JOIN `tabItem` i ON ip.item_code = i.name
            WHERE i.disabled = 0 AND i.publish_item = 1 AND ip.disabled = 0 AND ip.name='{doc.name}'
        """, as_dict=True)

    frappe.enqueue('mtolori_api.pricing.save_price', queue='long', items=items)
        
    
def save_price(items):

    try:
        for doc in items:
            price_list = frappe.get_doc("Price List", doc.price_list)
            payload = {
                "shop": 1,
                "product__erp_serial": doc.item_code,
                "price_list__erp_serial": price_list.price_list_id,
                "selling_price": doc.price_list_rate if doc.selling == 1 else 0.0,
                "buying_price": doc.price_list_rate if doc.buying == 1 else 0.0,
                "erp_serial": doc.name
            }  
            res = None 
            try:
                res = get(f'/pricing/{doc.name}/')
                try:
                    if not res:
                        res = post(f'/pricing/', payload)
                    else:
                        res = patch(f'/pricing/{doc.name}/', payload)
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"POST failed for {doc.item_code}")
                    continue
            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"GET failed for {doc.item_code}")
                try:
                    res = post(f'/pricing/', payload)
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"POST failed for {doc.item_code}")
                    continue
                    
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

        frappe.enqueue('mtolori_api.pricing.save_price', queue='long', items=items, timeout=60*60*2)
                       
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
            "product__erp_serial": doc.item_code,
            "price_list__erp_serial": price_list.price_list_id,
            "selling_price": doc.price_list_rate if doc.selling == 1 else 0.0,
            "buying_price": doc.price_list_rate if doc.buying == 1 else 0.0,
            "erp_serial": doc.name
        }   
        res = get(f'/pricing/{doc.name}/')
        if not res:
            res = post2(f'/pricing/', payload)
        else:
            res = patch(f'/pricing/{doc.name}/', payload)
            
        # frappe.db.commit() 
        frappe.response.payload = payload
        frappe.response.message = res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Not successful"
    
    
@frappe.whitelist(allow_guest=True)  
def test_save_customer(name):
    try:
        cus = frappe.get_doc("Customer", name)
        if cus.mobile_contact_no:
            customer_group = frappe.get_doc("Customer Group", cus.customer_group)
            default_price_list = None
            if customer_group and customer_group.default_price_list:
                default_price_list = customer_group.default_price_list
                
            if cus.default_price_list:
                default_price_list = cus.default_price_list
                
            if default_price_list:
                price_list = frappe.get_doc("Price List", default_price_list)
                    
                payload = {
                    "phone_number": cus.mobile_contact_no,
                    "price_list__erp_serial": price_list.price_list_id,
                    "shop": 1
                }   
                res = post2(f'/price-bias-lookup/', payload)
                frappe.response.message = res
                frappe.response.payload = payload
            
        # frappe.db.commit() 
        frappe.response.data = "wuueh"
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Not successful"
    
def save_customers(customers):
    try:
        for c in customers:
            cus = frappe.get_doc("Customer", c.name)
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

 
def save_customer_group(groups):
    try:
        for c in groups:
            customer_group = frappe.get_doc("Customer Group", c.name)
            price_list_id = frappe.db.get_value("Price List", customer_group.default_price_list, "price_list_id")
            payload = {
                "name": customer_group.customer_group_name,
                "price_list__erp_serial": price_list_id if price_list_id else customer_group.default_price_list,
                "active": True,
                "shop": 1,
                "erp_serial" : customer_group.name
            }  
            res = post(f'/customer-group/', payload)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    
@frappe.whitelist(allow_guest=True)
def save_group(name):
    try:
        customer_group = frappe.get_doc("Customer Group", name)
        price_list_id = frappe.db.get_value("Price List", customer_group.default_price_list, "price_list_id")
        payload = {
            "name": customer_group.customer_group_name,
            "price_list__erp_serial": price_list_id if price_list_id else customer_group.default_price_list,
            "active": True,
            "shop": 1,
            "erp_serial" : customer_group.name
        }  
        res = post2(f'/customer-group/', payload)
        frappe.db.commit()
        price_list = frappe.db.get_value('Price List', {'name': customer_group.default_price_list}, ['price_list_id'])
        frappe.response.price_list_id = price_list_id
        frappe.response.price_list = price_list
        frappe.response.message = res
        frappe.response.payload = payload
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    
    
@frappe.whitelist(allow_guest=True)  
def sync_customer_group():
    groups = frappe.db.sql("""
            SELECT name
            FROM `tabCustomer Group`
            WHERE is_group=0
        """, as_dict=1)
    frappe.enqueue('mtolori_api.pricing.save_customer_group', queue='long', groups=groups)
    return "Success"
