from erpnext.stock.doctype.batch.batch import get_batch_no, get_batch_qty, set_batch_nos
from mtolori_api.utils import *
from frappe.utils import flt
from frappe.utils import flt, cint, getdate, get_datetime, nowdate, nowtime, add_days, unique, month_diff
import traceback
import json

@frappe.whitelist(allow_guest=True)  
def create(**args):
    try:
        headers = frappe.local.request.headers
        
        api_key = headers.get("Api-Key")

        if not api_key:
            frappe.throw(("Missing API Key"), frappe.PermissionError)
        
        if api_key != "87454e2bac913cebefb9ac88826cf9":
            frappe.throw(("Failed. The API Key is invalid."), frappe.PermissionError)
            
        sales_invoice_doc = frappe.db.get_value('Sales Invoice', {'order_id': str(args.get('order_id'))}, ['name'], as_dict=1) 
        if not sales_invoice_doc:
            
            warehouse_name = frappe.db.get_value('Warehouse', {'shop_id': args.get('shop_id')}, ['name'], as_dict=1) 
            if warehouse_name:
            
                # profile_name = frappe.db.get_value('POS Profile', {'warehouse': warehouse_name.name}, ['name', 'income_account'], as_dict=1) 
                sales_invoice_doc = frappe.new_doc('Sales Invoice')
                company = get_main_company()
                customer = 'M-TOLORI WALK IN CUSTOMER'
                sales_invoice_doc.discount_amount = 0
                sales_invoice_doc.customer = customer
                sales_invoice_doc.due_date = frappe.utils.data.today()
                sales_invoice_doc.debit_to = company.default_receivable_account
                sales_invoice_doc.set_warehouse = warehouse_name.name
                sales_invoice_doc.order_type = "Mtolori"
                sales_invoice_doc.order_number = args.get('number')
                sales_invoice_doc.delivery_method = args.get('delivery_method')
                sales_invoice_doc.order_id = str(args.get('order_id'))
                default_income_account = "4118 - Mtolori Online Sales - MNA"
                # if profile_name:
                #     sales_invoice_doc.pos_profile = profile_name.name
                #     if profile_name.income_account:
                #         default_income_account = profile_name.income_account
                    
                
                total_amount = 0
                
                for itm in args.get('items'):
                    item = frappe.get_doc("Item", itm.get('erp_serial'))
                    if item: 
                        sales_invoice_doc.append('items',{
                            'item_code': item.item_code,
                            'item_name': item.item_name,
                            'description': item.description,
                            'qty': itm.get('quantity'),
                            'uom': item.stock_uom,
                            'rate': itm.get('price'),
                            'amount': itm.get('amount'),
                            'cost_center': warehouse_name.name,
                            'income_account': default_income_account
                        })
                        total_amount += float(itm.get('amount'))
                    
                if total_amount > 0:
                    sales_invoice_doc.is_pos = 1
                    sales_invoice_doc.update_stock = 1
                    sales_invoice_doc.paid_amount = total_amount
                    
                
                    payments = []
                    
                    payments.append(frappe._dict({
                        'mode_of_payment': "M-Tolori Online Till",
                        'amount': total_amount,
                    }))
                    sales_invoice_doc.set("payments", payments)
                    

                    sales_invoice_doc.flags.ignore_permissions = True
                    sales_invoice_doc.set_missing_values()
                    frappe.flags.ignore_account_permission = True
                    sales_invoice_doc.save(ignore_permissions = True)
                    
                    for item in sales_invoice_doc.items:
                        item.is_free_item = 0
                        add_taxes_from_tax_template(item, sales_invoice_doc)
                        
                        
                    if frappe.get_cached_value(
                        "POS Profile", sales_invoice_doc.pos_profile, "posa_tax_inclusive"
                    ):
                        if sales_invoice_doc.get("taxes"):
                            for tax in sales_invoice_doc.taxes:
                                tax.included_in_print_rate = 1
                                
                    sales_invoice_doc.save(ignore_permissions = True)
                                    
                    # sign_invoice(sales_invoice_doc)
                    
                    # sales_invoice_doc.submit()
                    # frappe.db.commit() 
                    

                    frappe.response.sales_invoice_doc = sales_invoice_doc
                    frappe.response.success = True
                    frappe.response.message = "Success. Order created"
            else:
                frappe.response.success = False
                frappe.response.message = "Failed. Shop does not exist"
        else:
            frappe.response.success = False
            frappe.response.message = "Failed. Order already created"
            
    except frappe.DoesNotExistError as e:
        log_error(e)
   
    except Exception as e:
        log_error(e)
        

def add_taxes_from_tax_template(item, parent_doc):
    accounts_settings = frappe.get_cached_doc("Accounts Settings")
    add_taxes_from_item_tax_template = (
        accounts_settings.add_taxes_from_item_tax_template
    )
    if item.get("item_tax_template") and add_taxes_from_item_tax_template:
        item_tax_template = item.get("item_tax_template")
        taxes_template_details = frappe.get_all(
            "Item Tax Template Detail",
            filters={"parent": item_tax_template},
            fields=["tax_type"],
        )

        for tax_detail in taxes_template_details:
            tax_type = tax_detail.get("tax_type")

            found = any(tax.account_head == tax_type for tax in parent_doc.taxes)
            if not found:
                tax_row = parent_doc.append("taxes", {})
                tax_row.update(
                    {
                        "description": str(tax_type).split(" - ")[0],
                        "charge_type": "On Net Total",
                        "account_head": tax_type,
                    }
                )

                if parent_doc.doctype == "Purchase Order":
                    tax_row.update({"category": "Total", "add_deduct_tax": "Add"})
                tax_row.db_insert()


        
def sign_invoice(invoice):
    theitems = []
    for itm in invoice.items:
        doctm = frappe.get_doc('Item', itm.item_code)
        item_group = frappe.get_doc('Item Group', doctm.item_group)
        
        if itm.qty < 1:
            myitm = " Agri 1.0 " +str(abs(itm.amount)) + " " + str(abs(itm.amount))
        else:
            myitm = " Agri "+str(itm.qty) +" " +str(abs(itm.rate)) + " " + str(abs(itm.amount))
        
        if item_group.hs_code:
            if itm.qty < 1:
                myitm = item_group.hs_code+ " Agri 1.0 " + str(abs(itm.amount)) + " " + str(abs(itm.amount))
            else:
                myitm = item_group.hs_code+ " Agri "+str(itm.qty) +" " + str(abs(itm.rate)) + " " + str(abs(itm.amount))
                
            
        theitems.append(myitm)
            
    tax_id = ""
    customer = frappe.get_doc('Customer', invoice.customer)
    if customer.tax_id:
        tax_id = customer.tax_id

    payload = {
        "invoice_date": str(invoice.posting_date),
        "invoice_number": invoice.name,
        "invoice_pin":"P051736886D",
        "customer_pin": tax_id,
        "customer_exid":"",    
        "grand_total": str(abs(invoice.grand_total)),
        "net_subtotal": str(abs(invoice.net_total)),
        "tax_total": str(abs(invoice.total_taxes_and_charges)),
        "net_discount_total": str(abs(invoice.base_discount_amount)),
        "sel_currency":"KSH",
        "rel_doc_number":"",
        "items_list": theitems
    }

    receip_url = 'http://192.168.1.20:8084/api/sign?invoice+1'

    if invoice.select_print_heading == "Invoice":
        receip_url = 'http://192.168.1.20:8084/api/sign?invoice+3'


    if invoice.is_return == 1:
        x_inv = frappe.get_doc("Sales Invoice", invoice.return_against)
        payload['rel_doc_number'] = x_inv.cu_invoice_number
        receip_url = 'http://192.168.1.20:8084/api/sign?invoice+2'
    
    try:
        headers = {
            "Authorization": "Bearer ZxZoaZMUQbUJDljA7kTExQ==",
            "Content-Type": "application/json",
        }
        x_data = "nooop"
        response = requests.post(receip_url, headers=headers, json=payload)
        
        if response.status_code == 401:
            frappe.response.status_code = response.status_code

        x_data = json.loads(response.text.replace("\\", ""), strict=False)
        if "cu_serial_number" in x_data:
            invoice.db_set({
                'cu_serial_number': x_data['cu_serial_number'],
                'cu_invoice_number': x_data['cu_invoice_number'],
                'verify_url': x_data['verify_url']
            })
            
            frappe.response.signature = {
                'cu_serial_number': x_data['cu_serial_number'],
                'cu_invoice_number': x_data['cu_invoice_number'],
                'verify_url': x_data['verify_url']
            }
            
        else:
            frappe.log_error(frappe.get_traceback(), str(response.text))
            
    except requests.exceptions.Timeout as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    except requests.exceptions.TooManyRedirects as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    except requests.exceptions.RequestException as e:
        frappe.log_error(frappe.get_traceback(), str(e))
    except requests.exceptions.ConnectionError as e:
        frappe.log_error('Connection error: Failed to establish a new connection', 'submitKra Connection Error')
        
        
def log_error(e):
    frappe.log_error(frappe.get_traceback(), str(e))
    frappe.response.error = str(e)
    frappe.response.success = False
    frappe.response.message = "Failed. Order not created"

    
def set_batch_nos_for_bundels(doc, warehouse_field, throw=False):
    """Automatically select `batch_no` for outgoing items in item table"""
    for d in doc.packed_items:
        qty = d.get("stock_qty") or d.get("transfer_qty") or d.get("qty") or 0
        has_batch_no = frappe.db.get_value("Item", d.item_code, "has_batch_no")
        warehouse = d.get(warehouse_field, None)
        if has_batch_no and warehouse and qty > 0:
            if not d.batch_no:
                d.batch_no = get_batch_no(
                    d.item_code, warehouse, qty, throw, d.serial_no
                )
            else:
                batch_qty = get_batch_qty(batch_no=d.batch_no, warehouse=warehouse)
                if flt(batch_qty, d.precision("qty")) < flt(qty, d.precision("qty")):
                    frappe.throw(
                        (
                            "Row #{0}: The batch {1} has only {2} qty. Please select another batch which has {3} qty available or split the row into multiple rows, to deliver/issue from multiple batches"
                        ).format(d.idx, d.batch_no, batch_qty, qty)
                    )
          
          
@frappe.whitelist(allow_guest=True)  
def test_invoice(**args):
    
    try:
        
        sales_invoice = frappe.new_doc("Sales Invoice")
        posting_date = nowdate()
        posting_time = nowtime()
            
        sales_invoice.discount_amount = 0
        sales_invoice.customer = "george mukundi"
        sales_invoice.due_date = posting_date
        sales_invoice.posting_date = posting_date
        sales_invoice.posting_time = posting_time
        sales_invoice.set_warehouse = "HQ Store - G"
        
        sales_invoice.debit_to = get_main_company().default_receivable_account
        
        order_items = []
        for itm in args.get('items'):
            item_doc = frappe.get_doc('Item', itm.get('erp_serial'))
            order_items.append(frappe._dict({
                'item_code': item_doc.item_code,
                'item_name': item_doc.item_name,
                'description': item_doc.description,
                'item_group': item_doc.item_group,
                'qty': itm.get('quantity'),
                'uom': item_doc.stock_uom,
                'warehouse': "HQ Store - G",
                'rate': 1,
                'amount': 1,
                'income_account': get_main_company().default_income_account
            }))
            
        sales_invoice.set("items", order_items)
            
        sales_invoice.is_pos = 1
        sales_invoice.paid_amount = 1
        payments = []
        
        payments.append(frappe._dict({
            'mode_of_payment': "Cash",
            'amount': 1,
            'type': "Cash",
            'default': 1
        }))
        sales_invoice.set("payments", payments)

        sales_invoice.flags.ignore_permissions = True
        frappe.flags.ignore_account_permission = True
        sales_invoice.save()
        sales_invoice.submit()
        
        frappe.db.commit() 
        
        frappe.response.message = "Success. Order created"
              
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
        frappe.response.message = "Failed. Orders not created"
    