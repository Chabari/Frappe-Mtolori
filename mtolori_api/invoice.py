from erpnext.stock.doctype.batch.batch import get_batch_no, get_batch_qty, set_batch_nos
from mtolori_api.utils import *
from frappe.utils import flt
from frappe.utils import flt, cint, getdate, get_datetime, nowdate, nowtime, add_days, unique, month_diff
import traceback

@frappe.whitelist(allow_guest=True)  
def create(**args):
    try:
        sales_invoice_doc = frappe.db.get_value('Sales Invoice', {'order_id': str(args.get('order_id'))}, ['name'], as_dict=1) 
        if not sales_invoice_doc:
            
            warehouse_name = frappe.db.get_value('Warehouse', {'shop_id': args.get('shop_id')}, ['name'], as_dict=1) 
            if warehouse_name:
            
                profile_name = frappe.db.get_value('POS Profile', {'warehouse': warehouse_name.name}, ['name'], as_dict=1) 
                sales_invoice_doc = frappe.new_doc('Sales Invoice')
                company = get_main_company()
                customer = '100342-M-TOLORI RETAIL ONLINE'
                sales_invoice_doc.discount_amount = 0
                sales_invoice_doc.customer = customer
                sales_invoice_doc.due_date = frappe.utils.data.today()
                sales_invoice_doc.debit_to = company.default_receivable_account
                sales_invoice_doc.set_warehouse = warehouse_name.name
                sales_invoice_doc.order_type = "Mtolori"
                sales_invoice_doc.order_number = args.get('number')
                sales_invoice_doc.delivery_method = args.get('delivery_method')
                sales_invoice_doc.order_id = str(args.get('order_id'))
                if profile_name:
                    sales_invoice_doc.pos_profile = profile_name.name
                total_amount = 0
                
                for itm in args.get('items'):
                    item = frappe.get_doc("Item", itm.get('erp_serial'))
                    default_income_account = None
                    for item_default in item.item_defaults:
                        if item_default.company == company.name:
                            if item_default.income_account:
                                default_income_account = item_default.income_account
                            else:
                                default_income_account = company.default_income_account
                                
                    sales_invoice_doc.append('items',{
                        'item_code': item.item_code,
                        'item_name': item.item_name,
                        'description': item.description,
                        'qty': itm.get('quantity'),
                        'uom': item.stock_uom,
                        'rate': itm.get('price'),
                        'amount': itm.get('amount'),
                        'income_account': default_income_account
                    })
                    total_amount += float(itm.get('amount'))
                    
                if total_amount > 0:
                    sales_invoice_doc.is_pos = 0
                    sales_invoice_doc.update_stock = 1
                    sales_invoice_doc.paid_amount = total_amount
                    
                    payments = []
                    
                    payments.append(frappe._dict({
                        'mode_of_payment': "Cash",
                        'amount': total_amount,
                        'type': "Cash",
                        'default': 1
                    }))
                    sales_invoice_doc.set("payments", payments)

                    sales_invoice_doc.flags.ignore_permissions = True
                    sales_invoice_doc.set_missing_values()
                    frappe.flags.ignore_account_permission = True
                    sales_invoice_doc.save(ignore_permissions = True)
                    
                    sales_invoice_doc.submit()
                    frappe.db.commit() 
                    
                    
                    # payment_entry = frappe.get_doc({
                    #     "doctype": "Payment Entry",
                    #     "payment_type": "Receive",
                    #     "party_type": "Customer",
                    #     "party": customer,
                    #     "paid_amount": total_amount,
                    #     "base_paid_amount": total_amount,
                    #     "target_exchange_rate": 1,
                    #     "received_amount": total_amount,
                    #     "base_received_amount": total_amount,
                    #     "paid_to": "Cash - G",
                    #     "paid_from": "Debtors - G",
                    #     "paid_to_account_currency": "KES",
                    #     "paid_from_account_currency": "KES",
                    #     "source_exchange_rate": 1,
                    #     "reference_no": sales_invoice_doc.name,
                    #     "reference_date": frappe.utils.nowdate(),
                    #     "references": [{
                    #         "reference_doctype": "Sales Invoice",
                    #         "reference_name": sales_invoice_doc.name,
                    #         "total_amount": total_amount,
                    #         "outstanding_amount": total_amount,
                    #         "allocated_amount": total_amount
                    #     }]
                    # })
                    
                    # payment_entry.flags.ignore_permissions = True
                    # # payment_entry.flags.ignore_mandatory = True
                    # payment_entry.flags.ignore_validate = True

                    # payment_entry.insert(ignore_permissions=True)
                    # payment_entry.submit()

                    frappe.response.message = "Success. Order created"
            else:
                frappe.response.message = "Failed. Shop does not exist"
        else:
            frappe.response.message = "Failed. Order already created"
            
    except frappe.DoesNotExistError as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.message = traceback.format_exc()
        frappe.response.error = str(e)
   
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), str(e))
        frappe.response.error = str(e)
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
    