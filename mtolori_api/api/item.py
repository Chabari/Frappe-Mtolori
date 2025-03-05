import frappe
from mtolori_api.utils import *

def after_insert(doc, method):
    company = get_main_company()
    # payload = {
    #     "erp_serial": doc.item_code,
    #     "name": doc.item_name,
    #     "description": doc.custom_item_description or doc.item_name,
    #     "weight": doc.custom_item_weight,
    #     "organization": company.custom_mtolori_organization_id,
    #     "subcategory": doc.custom_subcategory,
    #     "inventory": []
    # }   
    # res = post('/products/', payload)
    # if res and res.status_code == 201:
    #     if res['id']:
    #         doc.custom_item_id = res['id']
    #         doc.save(ignore_permissions = True)
      
@frappe.whitelist(allow_guest=True) 
def get_stock_levels():
    return get_data("WATER MELLON")