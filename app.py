import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import json
import string
import smtplib
import inspect
from email.message import EmailMessage
from urllib.parse import quote
from datetime import datetime, date
from io import BytesIO
from zoneinfo import ZoneInfo
from supabase import create_client, Client
from streamlit_geolocation import streamlit_geolocation


st.set_page_config(page_title="RBM ERP SaaS", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

# ---------- RBM ERP GLOBAL DROPDOWN PATCH ----------
# Requirement: every dropdown must show an "All" option.
# This wrapper adds "All" automatically in every Streamlit selectbox without changing your old code.
# It also preserves the old default selection by shifting the index by +1.
_RBM_ORIGINAL_SELECTBOX = st.selectbox

def _rbm_options_with_all(options):
    try:
        opts = list(options)
    except TypeError:
        opts = [options]
    # Do not duplicate All if already available.
    if "All" not in opts:
        opts = ["All"] + opts
    return opts

def rbm_selectbox_with_all(label, options, index=0, *args, **kwargs):
    opts = _rbm_options_with_all(options)
    # Preserve old selected default. If old index=0, new index=1 so old first item remains selected.
    if opts and opts[0] == "All":
        try:
            old_opts = list(options)
            if "All" not in old_opts:
                index = min(max(int(index) + 1, 0), len(opts) - 1)
            else:
                index = min(max(int(index), 0), len(opts) - 1)
        except Exception:
            index = 0
    return _RBM_ORIGINAL_SELECTBOX(label, opts, index=index, *args, **kwargs)

st.selectbox = rbm_selectbox_with_all

INDIA_TZ = ZoneInfo("Asia/Kolkata")
MAX_FILE_SIZE_MB = 2

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLES = {
    "clients": "clients", "users": "users", "employees": "employees", "attendance": "attendance",
    "attendance_visits": "attendance_visits", "inout": "inout_register", "visitors": "visitors", "tasks": "tasks",
    "appointments": "appointments", "ledger_groups": "ledger_groups", "ledgers": "ledgers",
    "stock_groups": "stock_groups", "stock_ledgers": "stock_ledgers", "stock_raw": "stock_raw_material",
    "stock_fg": "stock_finished_goods", "stock_wip": "stock_wip", "stock_vouchers": "stock_vouchers",
    "sales": "sales", "purchase": "purchase", "expenses": "expenses", "service_vouchers": "service_vouchers",
    "fixed_assets": "fixed_assets", "accounting_entries": "accounting_entries", "accounting_entry_lines": "accounting_entry_lines",
    "import_logs": "import_logs",
    "company_profiles": "company_profiles",
    "financial_years": "financial_years",
    "cost_centers": "cost_centers",
    "document_series": "document_series",
    "gst_settings": "gst_settings",
    "calculation_books": "calculation_books",
    "quotation_requirements": "quotation_requirements",
    "quotation_business_users": "quotation_business_users",
    "quotation_access": "quotation_access",
    "quotations": "quotations",
    "quotation_negotiations": "quotation_negotiations",
    "audit_logs": "audit_logs",
    "bom_headers": "bom_headers",
    "bom_lines": "bom_lines",
    "production_orders": "production_orders",
    "production_entries": "production_entries",
    "consumption_entries": "consumption_entries",
    "fg_entries": "fg_entries",
    "production_costing": "production_costing",
    "mrp": "mrp",
    "project_accounting": "project_accounting",
    "amc_subscriptions": "amc_subscriptions",
    "support_tickets": "support_tickets",
    "license_manager": "license_manager",
    "role_permissions": "role_permissions",
    "user_permissions": "user_permissions",
}

DISPLAY_COLUMNS = {
    "clients": ["id","client_code","client_name","allow_master_group","allow_task","allow_attendance","allow_inout","allow_visitor","allow_appointment","allow_stock_raw","allow_stock_fg","allow_stock_wip","allow_sales","allow_purchase","allow_expense","allow_service_voucher","allow_fixed_assets","allow_accounting","allow_excel_upload","allow_google_sheet_import","allow_quotation","allow_manufacturing","allow_project_accounting","allow_subscription","allow_support","allow_license_manager","status","created_at"],
    "users": ["id","client_code","username","password","role","full_name","email","mobile","status"],
    "employees": ["id","client_code","employee_id","employee_name","mobile","email","department","designation","branch_division","status"],
    "attendance": ["id","client_code","attendance_date","financial_year","employee_name","attendance_type","office_location","status","in_time","out_time","working_hours","in_latitude","in_longitude","out_latitude","out_longitude","remarks","created_by"],
    "attendance_visits": ["id","client_code","visit_date","financial_year","employee_name","visit_place","in_time","out_time","in_latitude","in_longitude","out_latitude","out_longitude","remarks","created_by"],
    "inout": ["id","client_code","entry_date","financial_year","person_name","purpose","in_time","out_time","remarks","created_by"],
    "visitors": ["id","client_code","visit_date","financial_year","visitor_name","mobile","company","meeting_with","purpose","in_time","out_time","remarks","created_by"],
    "tasks": ["id","client_code","task_date","financial_year","branch_division","task","assigned_to","priority","due_date","status","remarks","task_photo_name","created_by"],
    "appointments": ["id","client_code","appointment_date","appointment_time","customer_name","mobile","email","company","purpose","meeting_with","fees","status","remarks","created_by"],
    "ledger_groups": ["id","client_code","group_name","group_type","status","created_by"],
    "ledgers": ["id","client_code","ledger_name","ledger_group","address","contact_no","email","tan_no","gst_no","pan_no","opening_balance","balance_type","status","created_by"],
    "stock_groups": ["id","client_code","stock_group_name","stock_type","status","created_by"],
    "stock_ledgers": ["id","client_code","item_name","item_code","stock_group","unit","hsn_code","opening_qty","opening_rate","opening_value","gst_rate","status","created_by"],
    "stock_raw": ["id","client_code","entry_date","item_name","item_code","unit","opening_qty","inward_qty","outward_qty","closing_qty","rate","value","remarks","created_by"],
    "stock_fg": ["id","client_code","entry_date","item_name","item_code","unit","opening_qty","production_qty","sales_qty","closing_qty","rate","value","remarks","created_by"],
    "stock_wip": ["id","client_code","entry_date","process_name","item_name","item_code","unit","opening_qty","input_qty","output_qty","closing_qty","remarks","created_by"],
    "stock_vouchers": ["id","client_code","voucher_no","voucher_date","voucher_type","item_name","stock_group","qty","rate","value","remarks","created_by"],
    "sales": ["id","client_code","invoice_no","invoice_date","customer_name","gstin","item_name","hsn_sac","qty","rate","taxable_value","discount","freight","other_exp","tds","cgst","sgst","igst","total_value","remarks","created_by"],
    "purchase": ["id","client_code","invoice_no","invoice_date","supplier_name","gstin","item_name","hsn_sac","qty","rate","taxable_value","discount","freight","other_exp","tds","cgst","sgst","igst","total_value","remarks","created_by"],
    "expenses": ["id","client_code","expense_date","vendor_name","expense_head","invoice_no","gstin","taxable_value","discount","freight","other_exp","tds","cgst","sgst","igst","total_value","payment_mode","remarks","created_by"],
    "service_vouchers": ["id","client_code","voucher_no","voucher_date","customer_name","mobile","email","service_name","sac_code","taxable_value","cgst","sgst","igst","total_value","payment_status","remarks","created_by"],
    "fixed_assets": ["id","client_code","asset_code","asset_name","purchase_date","supplier_name","invoice_no","asset_category","location","cost","depreciation_rate","status","remarks","created_by"],
    "accounting_entries": ["id","client_code","entry_date","voucher_type","voucher_no","debit_account","credit_account","amount","cgst","sgst","igst","total_amount","narration","created_by"],
    "accounting_entry_lines": ["id","client_code","entry_id","dr_cr","ledger_name","amount","remarks"],
    "import_logs": ["id","client_code","import_type","module_name","total_rows","success_rows","failed_rows","remarks","created_by"],
    "company_profiles": ["id","client_code","company_name","legal_name","gst_no","pan_no","tan_no","address","state","email","mobile","financial_year_start","books_start_date","status","created_by"],
    "financial_years": ["id","client_code","fy_name","start_date","end_date","status","lock_status","created_by"],
    "cost_centers": ["id","client_code","cost_center_name","department","location","status","created_by"],
    "document_series": ["id","client_code","module_name","prefix","next_no","suffix","status","created_by"],
    "gst_settings": ["id","client_code","gst_no","legal_name","state","registration_type","default_tax_type","status","created_by"],
    "calculation_books": ["id","client_code","book_name","sheet_name","grid_json","remarks","created_by","created_at"],
    "quotation_requirements": ["id","client_code","requirement_no","requirement_date","requirement_title","requirement_details","item_name","qty","unit","expected_date","status","remarks","created_by","created_at"],
    "quotation_business_users": ["id","client_code","business_name","contact_person","mobile","email","username","password","status","created_by","created_at"],
    "quotation_access": ["id","client_code","requirement_id","requirement_no","business_username","business_name","status","created_by","created_at"],
    "quotations": ["id","client_code","requirement_id","requirement_no","business_username","business_name","quotation_no","quotation_date","amount","gst_amount","total_amount","valid_till","quotation_file_name","quotation_status","negotiation_status","negotiation_deadline","negotiation_message","remarks","created_by","created_at"],
    "quotation_negotiations": ["id","client_code","quotation_id","requirement_id","requirement_no","business_username","business_name","vendor_email","original_amount","requested_amount","negotiation_message","deadline","status","client_requested_by","client_requested_at","vendor_response","revised_amount","revised_gst_amount","revised_total_amount","revised_file_name","submitted_by","submitted_at","created_at"],
    "audit_logs": ["id","client_code","action_date","module_name","action_type","record_id","details","created_by","created_at"],
    "bom_headers": ["id","client_code","bom_no","bom_date","fg_item","fg_qty","labour_cost","power_cost","packing_cost","other_cost","material_cost","total_cost","cost_per_unit","status","remarks","created_by","created_at"],
    "bom_lines": ["id","client_code","bom_header_id","bom_no","rm_item","rm_qty","rm_rate","rm_amount","unit","remarks","created_by","created_at"],
    "production_orders": ["id","client_code","order_no","order_date","bom_no","fg_item","planned_qty","due_date","status","remarks","created_by","created_at"],
    "production_entries": ["id","client_code","entry_no","entry_date","order_no","fg_item","produced_qty","warehouse","status","remarks","created_by","created_at"],
    "consumption_entries": ["id","client_code","entry_no","entry_date","order_no","rm_item","consumed_qty","rate","amount","warehouse","remarks","created_by","created_at"],
    "fg_entries": ["id","client_code","entry_no","entry_date","fg_item","qty","rate","amount","warehouse","remarks","created_by","created_at"],
    "production_costing": ["id","client_code","costing_no","costing_date","order_no","fg_item","material_cost","labour_cost","overhead_cost","total_cost","qty","cost_per_unit","remarks","created_by","created_at"],
    "mrp": ["id","client_code","plan_no","plan_date","fg_item","required_qty","bom_no","rm_item","rm_required_qty","available_qty","shortage_qty","remarks","created_by","created_at"],
    "project_accounting": ["id","client_code","project_name","project_code","customer_name","income","expense","profit","status","remarks","created_by","created_at"],
    "amc_subscriptions": ["id","client_code","plan_name","client_name","start_date","expiry_date","no_of_users","storage_limit_mb","amount","renewal_status","remarks","created_by","created_at"],
    "support_tickets": ["id","client_code","ticket_no","ticket_date","raised_by","subject","priority","status","assigned_to","remarks","created_by","created_at"],
    "license_manager": ["id","client_code","license_key","client_name","machine_id","start_date","expiry_date","status","remarks","created_by","created_at"],
    "role_permissions": ["id","client_code","role_name","module_name","can_view","can_add","can_edit","can_delete","can_reverse","can_approve","can_print","can_export","created_by","created_at"],
    "user_permissions": ["id","client_code","username","module_name","can_view","can_add","can_edit","can_delete","can_reverse","can_approve","can_print","can_export","created_by","created_at"],
}

DEFAULT_LEDGER_GROUPS = ["Sundry Debtors", "Sundry Creditors", "Sales Accounts", "Purchase Accounts", "Direct Expenses", "Indirect Expenses", "Bank Accounts", "Cash-in-Hand", "Duties & Taxes", "Fixed Assets", "Loans & Advances", "Capital Account"]
DEFAULT_STOCK_GROUPS = ["Raw Material", "Finished Goods", "Work in Progress", "Packing Material", "Consumables", "Stores & Spares", "Trading Goods"]

# ---------- RBM ERP ONLINE FULL GROUP/MODULE CONFIG ----------
# Source tags for colored ticks:
# 🔴 Developer Only | 🔵 SAP Style | 🟢 QuickBooks Style | 🟠 Tally Style | 🟣 RBM Native
DEVELOPER_ROLES = ["Developer"]
SUPERADMIN_ROLES = ["Developer", "Super Admin"]
CLIENT_SUPERADMIN_ROLES = ["Client Super Admin"]
ADMIN_ROLES = ["Developer", "Super Admin", "Client Super Admin", "Admin"]

DEVELOPER_ONLY_MODULES = {
    "Client Master", "Client License Dashboard", "License Status Screen",
    "Client Group Permission", "Client Module Permission", "Data Purge Control",
    "Data Locking Period", "License Manager", "Offline Sync Engine",
    "System Settings", "Settings Center", "Error Log Viewer", "Data Health Check",
    "Backup Restore System", "Restore Backup", "Optional Online Sync Center",
}

MODULE_TAGS = {
    # Tally style
    "Ledger Group Master": "Tally", "Ledger Master": "Tally", "Stock Group Master": "Tally",
    "Stock Ledger Master": "Tally", "Accounting Entries": "Tally", "Accounting Entry Lines": "Tally",
    "Trial Balance": "Tally", "Profit Loss": "Tally", "Balance Sheet": "Tally",
    "Sundry Receivable": "Tally", "Sundry Payable": "Tally", "Stock Report": "Tally",
    "Gst Report": "Tally", "Tds Report": "Tally", "Calculation Book": "Tally",
    "Auto Invoice Numbering": "Tally", "Document Series": "Tally",

    # QuickBooks style
    "CRM Leads": "QuickBooks", "CRM Followups": "QuickBooks", "CRM Customers": "QuickBooks",
    "CRM Opportunities": "QuickBooks", "Customer Portal Access": "QuickBooks",
    "Bank Reconciliation": "QuickBooks", "Budget vs Actual": "QuickBooks",
    "Cash Flow Statement": "QuickBooks", "Customer Outstanding Ageing": "QuickBooks",
    "Supplier Outstanding Ageing": "QuickBooks", "Payment Receipt Voucher": "QuickBooks",
    "Bank Payment Voucher": "QuickBooks", "Reminder System": "QuickBooks",
    "Email Utility": "QuickBooks", "Email Integration": "QuickBooks", "WhatsApp Integration": "QuickBooks",

    # SAP style
    "MRP": "SAP", "Material Requirement Planning": "SAP", "Production Planning": "SAP",
    "Production Schedule": "SAP", "Production Orders": "SAP", "Production Entries": "SAP",
    "Consumption Entries": "SAP", "FG Entries": "SAP", "Production Costing": "SAP",
    "Manufacturing BOM": "SAP", "BOM Header": "SAP", "BOM Lines": "SAP",
    "Quality Management": "SAP", "Preventive Maintenance": "SAP",
    "Warehouse Bin Rack Management": "SAP", "Batch Management": "SAP",
    "Serial Number Tracking": "SAP", "Capacity Planning": "SAP",
    "Demand Forecasting": "SAP", "Profitability Analysis": "SAP",
    "Profitability Analysis - Customer Product Branch": "SAP",
    "Consolidated Financial Statements": "SAP",
    "Inter Company Transactions": "SAP", "Workflow Engine": "SAP",
    "Approval Matrix": "SAP", "Business Process Flow": "SAP",

    # Developer only
    **{m: "Developer" for m in DEVELOPER_ONLY_MODULES},
}

TAG_PREFIX = {
    "Developer": "🔴",
    "SAP": "🔵",
    "QuickBooks": "🟢",
    "Tally": "🟠",
    "RBM": "🟣",
}

ONLINE_MODULE_GROUPS = {
    "Dashboard": ["Dashboard"],

    "Admin": [
        "Client Master", "User Management", "Role Permission Control", "Role Based Security",
        "Client License Dashboard", "User Password Change", "License Status Screen", "Data Purge Control",
        "Data Locking Period", "Mandatory Field Settings", "Client Group Permission",
        "User Group Permission", "Client Module Permission",
    ],

    "Master": [
        "Company Profile", "Financial Year Master", "Cost Center Master", "Document Series",
        "GST Settings", "Ledger Group Master", "Ledger Master", "Stock Group Master",
        "Stock Ledger Master", "Auto Invoice Numbering",
    ],

    "CRM": [
        "CRM Leads", "CRM Followups", "CRM Customers", "CRM Opportunities", "Customer Portal Access",
    ],

    "HR": [
        "Employee Master", "Attendance Management", "Attendance Visits", "IN / OUT Register",
        "Visitor Register", "Task Delegation", "Appointments", "Payroll Salary Structure",
        "Payroll Processing", "Payroll Payslip",
    ],

    "Inventory": [
        "Inventory Item Master", "Barcode Master", "Barcode Print Log", "Warehouse Stock",
        "Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher",
        "Stock Report", "Stock Ageing / Slow Moving Stock",
    ],

    "Manufacturing": [
        "BOM Header", "BOM Lines", "Production Orders", "Production Entries",
        "Consumption Entries", "FG Entries", "Production Costing", "MRP",
        "Manufacturing BOM", "Production Planning", "Production Schedule",
        "Capacity Planning", "Demand Forecasting", "Quality Management",
        "Preventive Maintenance", "Batch Management", "Serial Number Tracking",
        "Warehouse Bin Rack Management",
    ],

    "Accounts": [
        "Accounting Entries", "Accounting Entry Lines", "Fixed Assets", "Asset Management",
        "Asset Maintenance", "Payment Receipt Voucher", "Bank Payment Voucher",
        "Bank Reconciliation", "Year Closing / Opening Balance Transfer",
        "Budget vs Actual", "Cash Flow Statement",
    ],

    "Sales": [
        "Sales GST Invoice", "Sales Order", "Delivery Note", "Credit Note",
        "Customer Outstanding Ageing", "Sales Cycle", "Recurring Invoices",
    ],

    "Purchase": [
        "Purchase GST Invoice", "Purchase Order", "Receipt Note", "Debit Note",
        "Supplier Outstanding Ageing", "Purchase Cycle", "GST Reconciliation",
    ],

    "Expense": [
        "Expense GST", "Service Voucher", "Expense Approval", "Recurring Expenses",
        "TDS Report", "Gst Report",
    ],

    "Projects": [
        "Project Accounting", "Project Income Heads", "Project Expense Heads",
        "Project Profitability", "Internal Orders", "Budget Control",
    ],

    "Quotation": [
        "Quotation", "Quotation Negotiations", "Quotation Requirements",
        "Quotation Business Users", "Quotation Access",
    ],

    "Enterprise": [
        "Workflow Engine", "Approval Matrix", "Business Process Flow", "Document Management",
        "OCR Invoice Scanner", "Global Smart Search", "AI Audit & Exception Dashboard",
        "Consolidated Financial Statements", "Inter Company Transactions",
        "Multi Company / Branch", "Multi Currency", "Customer Portal", "Vendor Portal",
        "Profitability Analysis - Customer Product Branch",
    ],

    "Support": [
        "Support Desk", "Support Tickets", "Customer Complaints", "Service Requests",
        "Client Support Register", "AMC / Subscription",
    ],

    "Audit": [
        "Audit Log", "Numbering Series Audit", "Digital Audit", "Duplicate Payment Detection",
        "Duplicate Invoice Detection", "Suspicious Entry Report", "Backdated Voucher Report",
        "Weekend Entry Report", "User Wise Modification Report",
    ],

    "Tools": [
        "OneDrive Backup", "Optional Online Sync Center", "Data Import", "Data Export",
        "Email Utility", "PDF Print Utility", "System Settings", "AI Chat Assistant",
        "WhatsApp Integration", "Email Integration", "OneDrive Backup Advanced",
        "Mobile App Sync", "Notification Center", "Backup Restore System",
        "Excel Import Wizard", "Export All Data", "Reminder System", "Settings Center",
        "Restore Backup", "Error Log Viewer", "Data Health Check",
    ],

    "Reports": [
        "Trial Balance", "Ledger Statement", "Profit Loss", "Balance Sheet", "Sundry Receivable",
        "Sundry Payable", "Stock Report", "Gst Report", "Tds Report",
        "Calculation Book", "Import Logs", "Dashboard Analytics", "Chairman MIS",
        "User Activity Dashboard", "Pending Work Dashboard", "GST Return Summary",
        "Customer Outstanding Ageing", "Supplier Outstanding Ageing",
        "Stock Ageing / Slow Moving Stock", "Budget vs Actual", "Cash Flow Statement",
        "GST Reconciliation", "Profitability Analysis - Customer Product Branch",
    ],
}

GROUP_ACCESS_KEYS = {
    "Admin": ["__client_admin_group__"],
    "Master": ["allow_master_group"],
    "CRM": ["allow_support", "allow_quotation", "allow_sales"],
    "HR": ["allow_attendance", "allow_inout", "allow_visitor", "allow_task", "allow_appointment"],
    "Inventory": ["allow_stock_raw", "allow_stock_fg", "allow_stock_wip"],
    "Manufacturing": ["allow_manufacturing"],
    "Accounts": ["allow_accounting", "allow_fixed_assets"],
    "Sales": ["allow_sales"],
    "Purchase": ["allow_purchase"],
    "Expense": ["allow_expense", "allow_service_voucher"],
    "Projects": ["allow_project_accounting"],
    "Quotation": ["allow_quotation"],
    "Enterprise": ["allow_support"],
    "Support": ["allow_support", "allow_subscription", "allow_license_manager"],
    "Audit": ["allow_support"],
    "Tools": ["allow_excel_upload", "allow_google_sheet_import", "allow_support"],
    "Reports": ["allow_master_group", "allow_sales", "allow_purchase", "allow_expense", "allow_accounting", "allow_stock_raw", "allow_stock_fg", "allow_stock_wip"],
}

def is_developer():
    return st.session_state.get("role") == "Developer"

def is_developer_or_super_admin():
    return st.session_state.get("role") in SUPERADMIN_ROLES

def is_client_super_admin():
    return st.session_state.get("role") == "Client Super Admin"

def module_tag(module_name):
    return MODULE_TAGS.get(str(module_name), "RBM")

def module_prefix(module_name):
    tag = module_tag(module_name)
    double = "✓✓" if tag in ["SAP", "QuickBooks", "Developer"] else "✓"
    return f"{TAG_PREFIX.get(tag, '🟣')}{double}"

def module_label(module_name):
    return f"{module_prefix(module_name)} {module_name}"

def strip_module_label(label):
    s = str(label)
    # remove colored icon/check prefix like "🔵✓✓ "
    for icon in TAG_PREFIX.values():
        s = s.replace(icon, "", 1).strip()
    while s.startswith("✓"):
        s = s[1:].strip()
    return s



def all_online_module_names():
    names = []
    try:
        for _g, _mods in ONLINE_MODULE_GROUPS.items():
            names.extend(list(_mods))
    except Exception:
        pass
    return list(dict.fromkeys([x for x in names if str(x).strip()]))

def modules_for_selected_group(module_title=None):
    try:
        if module_title == "Client Module Permission":
            g = st.session_state.get(f"gen_{module_title}_group_name", "Admin")
            return list(ONLINE_MODULE_GROUPS.get(g, [])) or all_online_module_names()
        return all_online_module_names()
    except Exception:
        return ["Dashboard", "User Management", "Company Profile"]

def role_can_see_module(module_name):
    role = st.session_state.get("role", "")
    client_code = str(st.session_state.get("client_code", "")).upper().strip()

    # Client Master and all red developer modules must be hidden from client-side roles.
    # Client Super Admin can create Admin/User from User Management, but cannot open Client Master.

    # RBM internal Super Admin must see Client Master / License / Developer-control modules.
    # Client Super Admin / Admin / User must NOT see other developer-control modules.
    if module_name in DEVELOPER_ONLY_MODULES:
        return role == "Developer" or (role == "Super Admin" and client_code == "RBM")

    if role in ["Developer", "Super Admin"]:
        return True
    return True

def group_enabled_for_client(group_name):
    if group_name in ["Dashboard"]:
        return True
    if is_developer_or_super_admin():
        return True

    # Client Super Admin / Admin must see Admin group to create users and assign user permissions.
    # Developer-only red modules are still hidden by role_can_see_module().
    if group_name == "Admin":
        return st.session_state.get("role") in ["Client Super Admin", "Admin"]

    keys = GROUP_ACCESS_KEYS.get(group_name, [])
    if not keys:
        return False
    return any(bool(st.session_state.get(k, False)) for k in keys if k != "__client_admin_group__")


COMMON_CONTROL_COLUMNS = ["parking_status", "approval_status", "cost_center", "approved_by", "approval_remarks"]
CONTROL_TABLE_KEYS = [
    "attendance", "attendance_visits", "inout", "visitors", "tasks", "appointments",
    "stock_raw", "stock_fg", "stock_wip", "stock_vouchers", "sales", "purchase",
    "expenses", "service_vouchers", "fixed_assets", "accounting_entries",
    "bom_headers", "production_orders", "production_entries", "consumption_entries", "fg_entries",
    "production_costing", "mrp", "project_accounting", "amc_subscriptions", "support_tickets", "license_manager"
]
for _k in CONTROL_TABLE_KEYS:
    if _k in DISPLAY_COLUMNS:
        for _c in COMMON_CONTROL_COLUMNS:
            if _c not in DISPLAY_COLUMNS[_k]:
                DISPLAY_COLUMNS[_k].append(_c)

REVERSIBLE_TABLE_KEYS = [
    "attendance", "attendance_visits", "inout", "visitors", "tasks", "appointments",
    "stock_raw", "stock_fg", "stock_wip", "stock_vouchers", "sales", "purchase",
    "expenses", "service_vouchers", "fixed_assets", "accounting_entries",
    "bom_headers", "production_orders", "production_entries", "consumption_entries", "fg_entries",
    "production_costing", "mrp", "project_accounting", "amc_subscriptions", "support_tickets", "license_manager"
]
REVERSAL_COLUMNS = ["reversal_status", "reversed_from_id", "reversal_reason", "reversed_by", "reversed_at"]
for _k in REVERSIBLE_TABLE_KEYS:
    if _k in DISPLAY_COLUMNS:
        for _c in REVERSAL_COLUMNS:
            if _c not in DISPLAY_COLUMNS[_k]:
                DISPLAY_COLUMNS[_k].append(_c)

st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}
[data-testid="stAppViewContainer"] {padding-top:0rem!important;}
[data-testid="stHeader"] {height:0rem!important;}
.block-container {padding-top:0.15rem!important;padding-bottom:1rem!important;padding-left:0.75rem!important;padding-right:0.75rem!important;max-width:100%!important;}
.rbm-header {background:linear-gradient(135deg,#082f49,#075985,#0284c7);padding:18px 24px;border-radius:18px;margin-top:0!important;margin-bottom:14px;box-shadow:0 10px 24px rgba(2,132,199,.22);display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.rbm-title {color:white;font-size:34px;font-weight:900;margin:0;line-height:1;}
.rbm-divider {color:#bae6fd;font-size:30px;font-weight:300;}
.rbm-subtitle {color:white;font-size:15px;font-weight:600;}
.rbm-client {background:rgba(8,47,73,.9);color:#7dd3fc;font-size:14px;font-weight:800;padding:8px 12px;border-radius:10px;}
.metric-card {background:linear-gradient(180deg,#fff,#f8fafc);padding:20px;border-radius:18px;box-shadow:0 7px 18px rgba(15,23,42,.08);border:1px solid #e2e8f0;text-align:center;}
.metric-number {font-size:32px;font-weight:900;color:#0f172a;}
.metric-label {color:#475569;font-size:14px;font-weight:600;}
.erp-box {padding:10px 12px;border-radius:12px;background:linear-gradient(135deg,#eff6ff,#e0f2fe);border:1px solid #bfdbfe;margin-bottom:8px;font-size:13px;}
.erp-name {font-size:20px;font-weight:900;color:#0f172a;margin-bottom:4px;}
.erp-small {font-size:12px;color:#334155;line-height:1.35;}
.section-title {padding:13px 16px;border-radius:14px;color:white;font-size:26px;font-weight:900;margin-bottom:16px;background:linear-gradient(135deg,#1e3a8a,#2563eb,#06b6d4);box-shadow:0 8px 20px rgba(37,99,235,.18);}
.section-master {background:linear-gradient(135deg,#4c1d95,#7c3aed,#c084fc)!important;}
.section-admin {background:linear-gradient(135deg,#0f766e,#14b8a6,#5eead4)!important;}
.section-hr {background:linear-gradient(135deg,#166534,#16a34a,#86efac)!important;}
.section-inv {background:linear-gradient(135deg,#9a3412,#f97316,#fdba74)!important;}
.section-acc {background:linear-gradient(135deg,#581c87,#9333ea,#e879f9)!important;}
.section-rep {background:linear-gradient(135deg,#7f1d1d,#dc2626,#fb7185)!important;}
.stButton button, .stDownloadButton button {border-radius:12px;font-weight:800;border:0;background:linear-gradient(135deg,#0f172a,#2563eb);color:white;}
.stButton button:hover, .stDownloadButton button:hover {border:0;color:white;filter:brightness(1.07);}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#f8fafc,#e0f2fe); min-width:300px!important; max-width:300px!important;}
[data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapseButton"] {display:none!important;}
section[data-testid="stSidebar"] button[kind="header"] {display:none!important;}
.rbm-show-menu {position:fixed;top:86px;left:12px;z-index:999999;background:linear-gradient(135deg,#0f172a,#2563eb);color:white;padding:8px 12px;border-radius:12px;font-weight:900;box-shadow:0 10px 24px rgba(15,23,42,.25);}
.rbm-menu-note {font-size:12px;color:#64748b;margin-bottom:8px;}
.ctrl-card {background:linear-gradient(135deg,#fff7ed,#ffedd5);border:1px solid #fed7aa;border-radius:14px;padding:12px;margin:10px 0;}

/* Final top-space fix */
[data-testid="stToolbar"] {display:none !important;}
[data-testid="stDecoration"] {display:none !important;}
[data-testid="stStatusWidget"] {display:none !important;}
section.main > div {padding-top:0rem !important;}
div[data-testid="stVerticalBlock"] {gap:0.55rem !important;}

</style>
""", unsafe_allow_html=True)

# ---------- BASIC HELPERS ----------
def india_now(): return datetime.now(INDIA_TZ)
def safe_df(data): return pd.DataFrame(data or [])
def get_client_code(): return st.session_state.get("client_code", "RBM")
def is_super_admin(): return st.session_state.get("role") in ["Developer", "Super Admin"]
def is_platform_admin(): return st.session_state.get("role") in ["Developer", "Super Admin"]
def is_client_super_admin_role(): return st.session_state.get("role") == "Client Super Admin"
def can_manage_client_users(): return st.session_state.get("role") in ["Developer", "Super Admin", "Client Super Admin", "Admin"]
def current_user(): return st.session_state.get("username", "system")

def get_cost_center_options():
    try:
        q = supabase.table("cost_centers").select("cost_center_name,status")
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        df = safe_df(q.execute().data)
        if not df.empty and "cost_center_name" in df.columns:
            vals = df[df.get("status", "Active").astype(str).ne("Inactive")]["cost_center_name"].dropna().astype(str).tolist()
            vals = sorted([v for v in vals if v.strip()])
            return ["None"] + vals if vals else ["None"]
    except Exception:
        pass
    return ["None"]

def entry_controls(prefix="ctrl"):
    st.markdown("<div class='ctrl-card'><b>🧾 Parking / Approval / ERP Control</b></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    parking_status = c1.selectbox("Parking / Posting", ["Draft", "Parked", "Posted"], key=f"{prefix}_parking")
    approval_status = c2.selectbox("Approval", ["Pending", "Approved", "Rejected", "Not Required"], key=f"{prefix}_approval")
    cost_center = c3.selectbox("Cost Center", get_cost_center_options(), key=f"{prefix}_cost_center")
    c4, c5 = st.columns(2)
    approved_by = c4.text_input("Approved By", key=f"{prefix}_approved_by")
    approval_remarks = c5.text_input("Approval / Parking Remarks", key=f"{prefix}_approval_remarks")
    return {
        "parking_status": parking_status,
        "approval_status": approval_status,
        "cost_center": cost_center,
        "approved_by": approved_by,
        "approval_remarks": approval_remarks,
    }

def money(x):
    try: return f"{float(x):,.2f}"
    except Exception: return "0.00"

def financial_year(value):
    try:
        d = pd.to_datetime(value)
        return f"{d.year}-{str(d.year+1)[-2:]}" if d.month >= 4 else f"{d.year-1}-{str(d.year)[-2:]}"
    except Exception: return ""

def indian_date(value):
    try:
        if value in ["", None]: return ""
        return pd.to_datetime(value).strftime("%d-%m-%Y")
    except Exception: return value

def indian_time(value):
    try:
        if value in ["", None]: return ""
        return str(value)[:5]
    except Exception: return value

def format_df_for_display(df):
    if df.empty: return df
    df = df.copy()
    for col in ["attendance_date","visit_date","entry_date","task_date","due_date","created_at","appointment_date","invoice_date","expense_date","voucher_date","purchase_date"]:
        if col in df.columns: df[col] = df[col].apply(indian_date)
    for col in ["in_time","out_time","appointment_time"]:
        if col in df.columns: df[col] = df[col].apply(indian_time)
    if "financial_year" not in df.columns:
        for c in ["attendance_date","visit_date","entry_date","task_date","invoice_date","expense_date","voucher_date"]:
            if c in df.columns:
                df["financial_year"] = df[c].apply(financial_year)
                break
    return df

def load_table(key, limit_rows=500):
    query = supabase.table(TABLES[key]).select("*")
    if key != "clients" and not is_super_admin():
        query = query.eq("client_code", get_client_code())
    response = query.order("id", desc=True).limit(limit_rows).execute()
    df = format_df_for_display(safe_df(response.data))
    if key in DISPLAY_COLUMNS:
        for col in DISPLAY_COLUMNS[key]:
            if col not in df.columns: df[col] = ""
        df = df[DISPLAY_COLUMNS[key]]
    return df

def raw_table(key, limit_rows=500):
    query = supabase.table(TABLES[key]).select("*")
    if key != "clients" and not is_super_admin():
        query = query.eq("client_code", get_client_code())
    return safe_df(query.order("id", desc=True).limit(limit_rows).execute().data)

def write_audit_log(module_name, action_type, record_id="", details=""):
    """Write audit trail. This never stops the main transaction if audit logging fails."""
    try:
        if "audit_logs" not in TABLES:
            return
        supabase.table(TABLES["audit_logs"]).insert({
            "client_code": get_client_code(),
            "action_date": india_now().date().isoformat(),
            "module_name": str(module_name),
            "action_type": str(action_type),
            "record_id": str(record_id or ""),
            "details": str(details or ""),
            "created_by": current_user()
        }).execute()
    except Exception:
        pass



def log_audit(module_name, action_type, record_id="", details=""):
    """Backward-compatible alias used by enterprise modules."""
    return write_audit_log(module_name, action_type, record_id, details)


def insert_row(key, row):
    if key != "clients" and "client_code" not in row:
        row["client_code"] = get_client_code()
    response = supabase.table(TABLES[key]).insert(row).execute()
    try:
        new_id = ""
        if response.data and isinstance(response.data, list) and len(response.data) > 0:
            new_id = response.data[0].get("id", "")
        if key != "audit_logs":
            write_audit_log(key, "CREATE", new_id, f"Created record in {key}")
    except Exception:
        pass
    return response

# ---------- SAFE UPDATE HELPERS ----------
READ_ONLY_UPDATE_COLUMNS = {
    "id", "financial_year", "created_at"
}

DATE_COLUMNS = {
    "attendance_date", "visit_date", "entry_date", "task_date", "due_date",
    "appointment_date", "invoice_date", "expense_date", "voucher_date",
    "purchase_date", "action_date", "start_date", "end_date",
    "books_start_date", "financial_year_start"
}

TIME_COLUMNS = {"in_time", "out_time", "appointment_time"}

NUMERIC_COLUMNS = {
    "working_hours", "fees", "opening_balance", "opening_qty", "opening_rate",
    "opening_value", "gst_rate", "inward_qty", "outward_qty", "closing_qty",
    "production_qty", "sales_qty", "input_qty", "output_qty", "qty", "rate",
    "value", "taxable_value", "discount", "freight", "other_exp", "tds",
    "cgst", "sgst", "igst", "total_value", "gross_value", "net_value",
    "cost", "depreciation_rate", "amount", "total_amount", "next_no",
    "total_rows", "success_rows", "failed_rows"
}

BOOLEAN_COLUMNS = {c for c in DISPLAY_COLUMNS.get("clients", []) if c.startswith("allow_")}

def clean_for_update(col, value):
    """Convert UI text values safely before sending update to Supabase."""
    if value is None:
        return None

    txt = str(value).strip()

    if txt.lower() in ["", "none", "nan", "nat", "null"]:
        return None

    if col in DATE_COLUMNS:
        try:
            return pd.to_datetime(txt, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            return txt

    if col in TIME_COLUMNS:
        try:
            return str(txt)[:8]
        except Exception:
            return txt

    if col in NUMERIC_COLUMNS:
        try:
            return float(txt.replace(",", ""))
        except Exception:
            return 0

    if col in BOOLEAN_COLUMNS:
        return txt.lower() in ["true", "1", "yes", "y", "on"]

    return txt

def update_row(key, row_id, row):
    clean = {}

    for col, val in row.items():
        if col in READ_ONLY_UPDATE_COLUMNS:
            continue
        clean[col] = clean_for_update(col, val)

    response = supabase.table(TABLES[key]).update(clean).eq("id", int(row_id)).execute()
    if key != "audit_logs":
        changed_cols = ", ".join(clean.keys())
        write_audit_log(key, "UPDATE", row_id, f"Updated columns: {changed_cols}")
    return response


def delete_row(key, row_id):
    try:
        old_df = safe_df(supabase.table(TABLES[key]).select("*").eq("id", int(row_id)).limit(1).execute().data)
        old_details = ""
        if not old_df.empty:
            old_details = str(old_df.iloc[0].to_dict())[:1000]
    except Exception:
        old_details = ""
    response = supabase.table(TABLES[key]).delete().eq("id", int(row_id)).execute()
    if key != "audit_logs":
        write_audit_log(key, "DELETE", row_id, f"Deleted record. Snapshot: {old_details}")
    return response


def reverse_record(key, row_id, reversal_reason=""):
    """Create a reverse/cancel entry and mark original as Reversed.
    Original entry is kept for audit trail. Reversal row has negative numeric values where applicable.
    """
    try:
        row_id = int(row_id)
        table_name = TABLES[key]

        original_df = safe_df(
            supabase.table(table_name)
            .select("*")
            .eq("id", row_id)
            .limit(1)
            .execute()
            .data
        )

        if original_df.empty:
            return False, "Original record not found."

        original = original_df.iloc[0].to_dict()

        if str(original.get("reversal_status", "Active")).lower() in ["reversed", "reverse"]:
            return False, "This entry is already reversed."

        skip_cols = {"id", "created_at", "updated_at"}
        reverse_row = {}

        for col, val in original.items():
            if col in skip_cols:
                continue

            if col in ["reversal_status", "reversed_from_id", "reversal_reason", "reversed_by", "reversed_at"]:
                continue

            if col in NUMERIC_COLUMNS:
                try:
                    reverse_row[col] = -1 * float(val or 0)
                except Exception:
                    reverse_row[col] = 0
            else:
                reverse_row[col] = val

        reverse_row["reversal_status"] = "Reverse"
        reverse_row["reversed_from_id"] = row_id
        reverse_row["reversal_reason"] = str(reversal_reason or "Reversed by user")
        reverse_row["reversed_by"] = current_user()
        reverse_row["reversed_at"] = india_now().isoformat()

        if "remarks" in reverse_row:
            reverse_row["remarks"] = f"REVERSAL of ID {row_id}. {reversal_reason or ''}".strip()

        if "created_by" in reverse_row:
            reverse_row["created_by"] = current_user()

        supabase.table(table_name).insert(reverse_row).execute()

        supabase.table(table_name).update({
            "reversal_status": "Reversed",
            "reversal_reason": str(reversal_reason or "Reversed by user"),
            "reversed_by": current_user(),
            "reversed_at": india_now().isoformat()
        }).eq("id", row_id).execute()

        write_audit_log(key, "REVERSE", row_id, str(reversal_reason or "Reversed by user"))

        # If accounting entry has line table, reverse lines also.
        if key == "accounting_entries":
            lines = safe_df(
                supabase.table("accounting_entry_lines")
                .select("*")
                .eq("entry_id", row_id)
                .execute()
                .data
            )
            if not lines.empty:
                for _, line in lines.iterrows():
                    l = line.to_dict()
                    new_line = {}
                    for c, v in l.items():
                        if c in ["id", "created_at"]:
                            continue
                        if c == "entry_id":
                            # Generic reversal line cannot know new inserted header id from Supabase API response here.
                            # Keep reference to original entry id for traceability.
                            new_line[c] = row_id
                        elif c == "dr_cr":
                            new_line[c] = "Cr" if str(v).lower() == "dr" else "Dr"
                        elif c == "amount":
                            try:
                                new_line[c] = float(v or 0)
                            except Exception:
                                new_line[c] = 0
                        else:
                            new_line[c] = v
                    if "remarks" in new_line:
                        new_line["remarks"] = f"Reversal line of entry {row_id}"
                    supabase.table("accounting_entry_lines").insert(new_line).execute()

        return True, "Entry reversed successfully. Original is marked as Reversed and separate reverse entry is created."

    except Exception as e:
        return False, f"Reverse failed: {e}"

def get_count(key):
    query = supabase.table(TABLES[key]).select("id", count="exact")
    if key != "clients" and not is_super_admin(): query = query.eq("client_code", get_client_code())
    return query.execute().count or 0

def filter_dataframe(df, keyword):
    if keyword.strip() == "": return df
    keyword = keyword.lower()
    return df[df.astype(str).apply(lambda row: row.str.lower().str.contains(keyword, na=False).any(), axis=1)]

def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer: df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def show_header(title, cls=""): st.markdown(f'<div class="section-title {cls}">{title}</div>', unsafe_allow_html=True)

def show_metric_card(label, value):
    st.markdown(f'<div class="metric-card"><div class="metric-number">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

def show_table_with_edit_delete(key, df, title):
    st.subheader(title)

    msg_key = f"last_action_msg_{key}"
    if msg_key in st.session_state:
        st.success(st.session_state.pop(msg_key))

    search = st.text_input(f"Search {title}", key=f"search_{key}")
    filtered = filter_dataframe(df, search)

    st.dataframe(filtered, use_container_width=True)

    if has_key_permission(key, "export") or is_super_admin():
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Download Excel",
                to_excel_bytes(filtered),
                f"{key}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"xlsx_{key}"
            )
        with c2:
            st.download_button(
                "Download CSV",
                filtered.to_csv(index=False).encode("utf-8"),
                f"{key}.csv",
                "text/csv",
                use_container_width=True,
                key=f"csv_{key}"
            )

    can_manage = (
        is_super_admin()
        or (
            st.session_state.get("role") == "Admin"
            and (
                has_key_permission(key, "edit")
                or has_key_permission(key, "delete")
                or has_key_permission(key, "reverse")
            )
        )
    )

    if can_manage and not filtered.empty and "id" in filtered.columns:
        st.divider()
        st.subheader("Edit / Delete")

        # IMPORTANT FIX:
        # Use filtered data for selection and keep keys dependent on selected_id.
        # Earlier, text_input keys were same for every ID, so Streamlit kept old values.
        id_list = filtered["id"].dropna().tolist()
        if not id_list:
            st.info("No ID available for edit/delete.")
            return

        selected_id = st.selectbox(
            "Select ID",
            id_list,
            key=f"select_id_{key}_{len(id_list)}"
        )

        selected_id_str = str(selected_id).strip()
        selected_match = filtered[filtered["id"].astype(str).str.strip() == selected_id_str]

        if selected_match.empty:
            st.warning("Selected record not found after filter. Please clear search or refresh.")
            return

        selected_row = selected_match.iloc[0]

        with st.expander(f"Edit Selected Record - ID {selected_id}", expanded=False):
            edited = {}
            for col in filtered.columns:
                value_text = "" if pd.isna(selected_row[col]) else str(selected_row[col])

                # Key includes selected_id so fields refresh when ID changes.
                field_key = f"edit_{key}_{selected_id}_{col}"

                if col in ["id", "financial_year"]:
                    st.text_input(col, value_text, disabled=True, key=field_key)
                else:
                    edited[col] = st.text_input(col, value_text, key=field_key)

            if has_key_permission(key, "edit") or is_super_admin():
                if st.button("Update Record", use_container_width=True, key=f"update_{key}_{selected_id}"):
                    update_row(key, selected_id, edited)
                    st.session_state[f"last_action_msg_{key}"] = f"Record ID {selected_id} updated successfully. Details closed."
                    st.rerun()
            else:
                st.info("You do not have edit permission for this module.")

        if key in REVERSIBLE_TABLE_KEYS:
            with st.expander(f"Reverse / Cancel Posted Entry - ID {selected_id}", expanded=False):
                st.warning("This will create a separate reversal entry and mark the original as Reversed. It will not delete original data.")
                reversal_reason = st.text_input("Reversal Reason", key=f"reverse_reason_{key}_{selected_id}")

                if has_key_permission(key, "reverse") or is_super_admin():
                    if st.button("Reverse Selected Entry", use_container_width=True, key=f"reverse_{key}_{selected_id}"):
                        ok, msg = reverse_record(key, selected_id, reversal_reason)
                        if ok:
                            st.session_state[f"last_action_msg_{key}"] = msg
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.info("You do not have reverse permission for this module.")

        with st.expander(f"Delete Selected Record - ID {selected_id}", expanded=False):
            st.warning("This will permanently delete selected record. Prefer Reverse for posted/saved business entries.")
            if has_key_permission(key, "delete") or is_super_admin():
                if st.button("Delete Record", use_container_width=True, key=f"delete_{key}_{selected_id}"):
                    delete_row(key, selected_id)
                    st.session_state[f"last_action_msg_{key}"] = f"Record ID {selected_id} deleted successfully. Details closed."
                    st.rerun()
            else:
                st.info("You do not have delete permission for this module.")


# ---------- MASTER DATA HELPERS ----------
def get_ledger_names(group_name=None, include_all=False):
    query = supabase.table("ledgers").select("ledger_name,ledger_group,status")
    if not is_super_admin(): query = query.eq("client_code", get_client_code())
    if group_name: query = query.eq("ledger_group", group_name)
    df = safe_df(query.execute().data)
    if not df.empty and "status" in df.columns: df = df[df["status"].astype(str).str.lower() == "active"]
    names = df["ledger_name"].dropna().astype(str).sort_values().unique().tolist() if not df.empty and "ledger_name" in df.columns else []
    if include_all: names = ["All"] + names
    return names if names else ["No Ledger Found"]

def get_ledger_details(ledger_name):
    """Fetch ledger address/contact/GST/PAN/email details for invoice print preview."""
    try:
        if not ledger_name or str(ledger_name).strip() in ["", "No Ledger Found"]:
            return {}
        query = supabase.table("ledgers").select("*").eq("ledger_name", str(ledger_name).strip())
        if not is_super_admin():
            query = query.eq("client_code", get_client_code())
        df = safe_df(query.limit(1).execute().data)
        if df.empty:
            return {}
        row = df.iloc[0].to_dict()
        return {
            "ledger_name": row.get("ledger_name", ledger_name),
            "address": row.get("address", ""),
            "contact_no": row.get("contact_no", ""),
            "mobile": row.get("contact_no", ""),
            "email": row.get("email", ""),
            "gst_no": row.get("gst_no", ""),
            "pan_no": row.get("pan_no", ""),
            "tan_no": row.get("tan_no", ""),
        }
    except Exception:
        return {}

def get_stock_items(group_name=None):
    query = supabase.table("stock_ledgers").select("item_name,stock_group,status")
    if not is_super_admin(): query = query.eq("client_code", get_client_code())
    if group_name: query = query.eq("stock_group", group_name)
    df = safe_df(query.execute().data)
    if not df.empty and "status" in df.columns: df = df[df["status"].astype(str).str.lower() == "active"]
    names = df["item_name"].dropna().astype(str).sort_values().unique().tolist() if not df.empty and "item_name" in df.columns else []
    return names if names else ["No Item Found"]


def get_stock_item_names(group_name=None):
    """Compatibility wrapper for Enterprise Purchase/Sales Cycle modules."""
    return get_stock_items(group_name)


def get_stock_item_names():
    """Backward compatible alias used by Enterprise Purchase/Sales Cycle modules."""
    return get_stock_items()


def get_groups(table_key, col, defaults):
    df = raw_table(table_key, 1000)
    names = df[col].dropna().astype(str).unique().tolist() if not df.empty and col in df.columns else []
    return sorted(list(set(defaults + names)))



def quick_ledger_creator(default_group="Sundry Creditors", key_prefix="quick_ledger"):
    """Small direct ledger creation box shown inside voucher screens."""
    with st.expander("➕ Add New Ledger Here"):
        groups = get_groups("ledger_groups", "group_name", DEFAULT_LEDGER_GROUPS)
        c1, c2, c3 = st.columns(3)
        ledger_name = c1.text_input("Ledger Name", key=f"{key_prefix}_name")
        ledger_group = c2.selectbox("Ledger Group", groups, index=groups.index(default_group) if default_group in groups else 0, key=f"{key_prefix}_group")
        contact_no = c3.text_input("Contact No", key=f"{key_prefix}_contact")
        address = st.text_area("Address", key=f"{key_prefix}_address")
        c4, c5, c6, c7 = st.columns(4)
        gst_no = c4.text_input("GST No", key=f"{key_prefix}_gst")
        pan_no = c5.text_input("PAN No", key=f"{key_prefix}_pan")
        tan_no = c6.text_input("TAN No", key=f"{key_prefix}_tan")
        opening_balance = c7.number_input("Opening Balance", value=0.0, key=f"{key_prefix}_ob")
        balance_type = st.selectbox("Balance Type", ["Dr", "Cr"], key=f"{key_prefix}_baltype")
        if st.button("Save New Ledger", use_container_width=True, key=f"{key_prefix}_save"):
            if str(ledger_name).strip() == "":
                st.error("Ledger Name required")
            else:
                insert_row("ledgers", {
                    "ledger_name": ledger_name.strip(),
                    "ledger_group": ledger_group,
                    "address": address,
                    "contact_no": contact_no,
                    "tan_no": tan_no,
                    "gst_no": gst_no,
                    "pan_no": pan_no,
                    "opening_balance": opening_balance,
                    "balance_type": balance_type,
                    "status": "Active",
                    "created_by": current_user()
                })
                st.success("Ledger created. Please refresh/reopen this module to see it in dropdown.")


def quick_stock_item_creator(default_group="Finished Goods", key_prefix="quick_item"):
    """Small direct stock item creation box shown inside invoice screens."""
    with st.expander("➕ Add New Stock Item Here"):
        groups = get_groups("stock_groups", "stock_group_name", DEFAULT_STOCK_GROUPS)
        c1, c2, c3 = st.columns(3)
        item_name = c1.text_input("Item Name", key=f"{key_prefix}_name")
        item_code = c2.text_input("Item Code", key=f"{key_prefix}_code")
        stock_group = c3.selectbox("Stock Group", groups, index=groups.index(default_group) if default_group in groups else 0, key=f"{key_prefix}_group")
        c4, c5, c6, c7 = st.columns(4)
        unit = c4.text_input("Unit", value="Nos", key=f"{key_prefix}_unit")
        hsn_code = c5.text_input("HSN/SAC", key=f"{key_prefix}_hsn")
        gst_rate = c6.number_input("GST %", value=18.0, key=f"{key_prefix}_gst")
        opening_qty = c7.number_input("Opening Qty", value=0.0, key=f"{key_prefix}_oqty")
        opening_rate = c6.number_input("Opening Rate", value=0.0, key=f"{key_prefix}_orate")
        opening_value = round(opening_qty * opening_rate, 2)
        st.info(f"Opening Value: {money(opening_value)}")
        if st.button("Save New Stock Item", use_container_width=True, key=f"{key_prefix}_save"):
            if str(item_name).strip() == "":
                st.error("Item Name required")
            else:
                insert_row("stock_ledgers", {
                    "item_name": item_name.strip(),
                    "item_code": item_code,
                    "stock_group": stock_group,
                    "unit": unit,
                    "hsn_code": hsn_code,
                    "opening_qty": opening_qty,
                    "opening_rate": opening_rate,
                    "opening_value": opening_value,
                    "gst_rate": gst_rate,
                    "status": "Active",
                    "created_by": current_user()
                })
                st.success("Stock item created. Please refresh/reopen this module to see it in dropdown.")



def safe_get_ledger_details(ledger_name):
    """Never crash invoice preview if ledger detail lookup has any issue."""
    try:
        return get_ledger_details(ledger_name)
    except Exception:
        return {
            "address": "",
            "contact_no": "",
            "mobile": "",
            "email": "",
            "gst_no": "",
            "pan_no": "",
            "tan_no": "",
        }

def gst_calc(taxable, gst_rate=18, gst_type="CGST+SGST"):
    try: taxable = float(taxable); gst_rate = float(gst_rate)
    except Exception: taxable = 0; gst_rate = 0
    if gst_type == "IGST":
        igst = taxable * gst_rate / 100; cgst = 0; sgst = 0
    else:
        cgst = taxable * gst_rate / 200; sgst = cgst; igst = 0
    return round(cgst,2), round(sgst,2), round(igst,2), round(taxable+cgst+sgst+igst,2)

def invoice_html(title, invoice_no, party, rows, total, summary=None, party_info=None):
    """Professional invoice preview with item-wise CGST/SGST/IGST and voucher-level adjustments."""
    summary = summary or {}
    party_info = party_info or safe_get_ledger_details(party)

    def safe_text(value):
        value = "" if value is None else str(value)
        return value if value.lower() not in ["none", "nan"] else ""

    def info_line(label, value):
        value = safe_text(value)
        return f"<div><b>{label}:</b> {value}</div>" if value.strip() else ""

    party_details_html = f"""
        <div class='party-box'>
            <div class='box-title'>Billed To / Party Details</div>
            <div><b>Name:</b> {safe_text(party)}</div>
            {info_line('Address', party_info.get('address'))}
            {info_line('Contact / Mobile', party_info.get('contact_no') or party_info.get('mobile'))}
            {info_line('Email', party_info.get('email'))}
            {info_line('GSTIN', party_info.get('gst_no'))}
            {info_line('PAN', party_info.get('pan_no'))}
            {info_line('TAN', party_info.get('tan_no'))}
        </div>
    """

    def nz(value):
        try:
            return abs(float(value or 0)) > 0.000001
        except Exception:
            return False

    item_body = "".join([
        f"""
        <tr>
            <td>{r.get('item','')}</td>
            <td>{r.get('hsn','')}</td>
            <td align='right'>{r.get('qty',0)}</td>
            <td align='right'>{money(r.get('rate',0))}</td>
            <td align='right'>{money(r.get('taxable',0))}</td>
            <td align='right'>{money(r.get('cgst',0))}</td>
            <td align='right'>{money(r.get('sgst',0))}</td>
            <td align='right'>{money(r.get('igst',0))}</td>
            <td align='right'>{money(r.get('total',0))}</td>
        </tr>
        """ for r in rows
    ])

    charges_rows = ""
    if nz(summary.get('discount')):
        charges_rows += f"<tr><td colspan='8' align='right'><b>Less: Discount</b></td><td align='right'>-{money(summary.get('discount',0))}</td></tr>"
    if nz(summary.get('freight')):
        charges_rows += f"<tr><td colspan='4'><b>Freight</b></td><td align='right'>{money(summary.get('freight',0))}</td><td align='right'>{money(summary.get('freight_cgst',0))}</td><td align='right'>{money(summary.get('freight_sgst',0))}</td><td align='right'>{money(summary.get('freight_igst',0))}</td><td align='right'>{money(summary.get('freight_total',0))}</td></tr>"
    if nz(summary.get('other_exp')):
        charges_rows += f"<tr><td colspan='4'><b>Other Charges</b></td><td align='right'>{money(summary.get('other_exp',0))}</td><td align='right'>{money(summary.get('other_cgst',0))}</td><td align='right'>{money(summary.get('other_sgst',0))}</td><td align='right'>{money(summary.get('other_igst',0))}</td><td align='right'>{money(summary.get('other_total',0))}</td></tr>"
    if nz(summary.get('tds')):
        charges_rows += f"<tr><td colspan='8' align='right'><b>Less: TDS</b></td><td align='right'>-{money(summary.get('tds',0))}</td></tr>"

    basic_taxable = summary.get('basic_taxable_total', sum(float(r.get('taxable',0) or 0) for r in rows))
    taxable_total = summary.get('taxable_total', sum(float(r.get('taxable',0) or 0) for r in rows))
    cgst_total = summary.get('cgst_total', sum(float(r.get('cgst',0) or 0) for r in rows) + float(summary.get('freight_cgst',0) or 0) + float(summary.get('other_cgst',0) or 0))
    sgst_total = summary.get('sgst_total', sum(float(r.get('sgst',0) or 0) for r in rows) + float(summary.get('freight_sgst',0) or 0) + float(summary.get('other_sgst',0) or 0))
    igst_total = summary.get('igst_total', sum(float(r.get('igst',0) or 0) for r in rows) + float(summary.get('freight_igst',0) or 0) + float(summary.get('other_igst',0) or 0))
    total_gst = summary.get('total_gst', cgst_total + sgst_total + igst_total)
    gross_total = summary.get('gross_total', total + float(summary.get('tds',0) or 0))

    return f"""
    <html>
    <head>
        <meta charset='utf-8'>
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 14px; color: #111827; }}
            .top {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom:3px solid #0f3b66; padding-bottom:12px; margin-bottom:18px; }}
            .brand {{ font-size:30px; font-weight:800; color:#0f3b66; }}
            .title {{ background:linear-gradient(90deg,#0f3b66,#2563eb); color:white; padding:10px 14px; border-radius:10px; font-size:22px; font-weight:800; margin:16px 0; }}
            .info {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px; font-size:13px; }}
            .invoice-meta, .party-box {{ border:1px solid #cbd5e1; border-radius:10px; padding:10px; background:#f8fafc; }}
            .box-title {{ font-weight:800; color:#0f3b66; margin-bottom:6px; font-size:14px; }}
            table {{ border-collapse:collapse; width:100%; margin-top:10px; }}
            th {{ background:#0f3b66; color:white; padding:8px; border:1px solid #0f3b66; font-size:12px; }}
            td {{ padding:7px; border:1px solid #d1d5db; font-size:12px; }}
            .summary {{ margin-top:12px; width:100%; margin-left:0; }}
            .summary td {{ font-size:13px; }}
            .grand td {{ background:#e0f2fe; font-size:15px; }}
            .footer {{ margin-top:20px; display:flex; justify-content:space-between; }}
            .sign {{ border-top:1px solid #111827; padding-top:8px; min-width:180px; text-align:center; }}
            .no-print {{ margin-bottom:15px; }}
            .print-btn {{ background:#0f3b66; color:white; border:none; padding:10px 18px; border-radius:8px; font-weight:bold; cursor:pointer; }}
            @media print {{ .no-print {{ display:none; }} body {{ padding:0; }} }}
        </style>
    </head>
    <body>
        <div class='no-print'><button class='print-btn' onclick='window.print()'>🖨 Print Invoice</button></div>
        <div class='top'>
            <div><div class='brand'>RBM AI</div><div>Robotic Business Management</div></div>
            <div style='text-align:right'><b>Date:</b> {india_now().strftime('%d-%m-%Y')}<br><b>Generated By:</b> RBM ERP SaaS</div>
        </div>
        <div class='title'>{title}</div>
        <div class='info'>
            <div class='invoice-meta'>
                <div class='box-title'>Invoice Details</div>
                <div><b>Invoice/Voucher No:</b> {invoice_no}</div>
                <div><b>Date:</b> {india_now().strftime('%d-%m-%Y')}</div>
                <div><b>Generated By:</b> RBM ERP SaaS</div>
            </div>
            {party_details_html}
        </div>
        <table>
            <tr><th>Item/Service</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>Taxable</th><th>CGST</th><th>SGST</th><th>IGST</th><th>Total</th></tr>
            {item_body}
            {charges_rows}
            <tr class='grand'><td colspan='8' align='right'><b>Net Payable / Receivable</b></td><td align='right'><b>{money(total)}</b></td></tr>
        </table>
        <table class='summary'>
            <tr><td><b>Basic Taxable</b></td><td align='right'>{money(basic_taxable)}</td></tr>
            <tr><td><b>Discount</b></td><td align='right'>{money(summary.get('discount',0))}</td></tr>
            <tr><td><b>Taxable After Discount</b></td><td align='right'>{money(taxable_total)}</td></tr>
            <tr><td><b>Freight</b></td><td align='right'>{money(summary.get('freight',0))}</td></tr>
            <tr><td><b>Other Charges</b></td><td align='right'>{money(summary.get('other_exp',0))}</td></tr>
            <tr><td><b>CGST</b></td><td align='right'>{money(cgst_total)}</td></tr>
            <tr><td><b>SGST</b></td><td align='right'>{money(sgst_total)}</td></tr>
            <tr><td><b>IGST</b></td><td align='right'>{money(igst_total)}</td></tr>
            <tr><td><b>Total GST</b></td><td align='right'>{money(total_gst)}</td></tr>
            <tr><td><b>Gross Total</b></td><td align='right'>{money(gross_total)}</td></tr>
            {f"<tr><td><b>Less TDS</b></td><td align='right'>{money(summary.get('tds',0))}</td></tr>" if nz(summary.get('tds')) else ""}
            <tr class='grand'><td><b>Final Net Amount</b></td><td align='right'><b>{money(total)}</b></td></tr>
        </table>
        <div class='footer'>
            <div><b>Note:</b> This is a computer-generated invoice/voucher.</div>
            <div class='sign'>Authorised Signatory</div>
        </div>
    </body>
    </html>"""

def show_invoice_preview_and_download(html, file_name, button_label='Print / Download Invoice'):
    st.markdown('### Invoice Print Preview')
    with st.expander('👁️ Show / Hide Print Preview', expanded=True):
        components.html(html, height=520, scrolling=True)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            f'⬇ Download HTML Invoice',
            data=html.encode('utf-8'),
            file_name=file_name,
            mime='text/html',
            use_container_width=True
        )
    with c2:
        st.info('Preview ke andar 🖨 Print Invoice button par click karke print/PDF save kar sakte ho.')



def get_saved_invoice_preview_html(key, title, party_col):
    """Return HTML for selected saved Sales/Purchase invoice. Does not render separately."""
    df = load_table(key, 5000)

    if df.empty:
        st.info("No saved invoice found for preview.")
        return None, None

    if "invoice_no" not in df.columns:
        st.info("Invoice number column not found in saved data.")
        return None, None

    preview_df = df.copy()
    preview_df["invoice_no"] = preview_df["invoice_no"].astype(str)
    preview_df = preview_df[preview_df["invoice_no"].str.strip() != ""]

    if preview_df.empty:
        st.info("No saved invoice number found for preview.")
        return None, None

    if "invoice_date" in preview_df.columns:
        preview_df["invoice_label"] = preview_df["invoice_no"].astype(str) + " | " + preview_df["invoice_date"].astype(str)
    else:
        preview_df["invoice_label"] = preview_df["invoice_no"].astype(str)

    if party_col in preview_df.columns:
        preview_df["invoice_label"] = preview_df["invoice_label"] + " | " + preview_df[party_col].astype(str)

    labels = preview_df["invoice_label"].drop_duplicates().tolist()
    selected_label = st.selectbox("Select Saved Invoice No. / Party to Preview", labels, key=f"saved_preview_{key}")
    selected_invoice_no = str(selected_label).split(" | ")[0]

    inv_df = preview_df[preview_df["invoice_no"].astype(str) == selected_invoice_no].copy()
    if inv_df.empty:
        st.warning("Selected invoice data not found.")
        return None, None

    first = inv_df.iloc[0]
    party = str(first.get(party_col, ""))

    rows = []
    for _, r in inv_df.iterrows():
        rows.append({
            "item": r.get("item_name", ""),
            "hsn": r.get("hsn_sac", ""),
            "qty": r.get("qty", 0),
            "rate": r.get("rate", 0),
            "taxable": r.get("taxable_value", 0),
            "cgst": r.get("cgst", 0),
            "sgst": r.get("sgst", 0),
            "igst": r.get("igst", 0),
            "total": r.get("total_value", 0),
        })

    def first_num(col):
        try:
            return float(first.get(col, 0) or 0)
        except Exception:
            return 0.0

    discount = first_num("discount")
    freight = first_num("freight")
    other_exp = first_num("other_exp")
    tds = first_num("tds")
    taxable_after_discount = sum(float(x.get("taxable", 0) or 0) for x in rows)
    basic_taxable_total = taxable_after_discount + discount

    row_cgst = sum(float(x.get("cgst", 0) or 0) for x in rows)
    row_sgst = sum(float(x.get("sgst", 0) or 0) for x in rows)
    row_igst = sum(float(x.get("igst", 0) or 0) for x in rows)

    # Old saved rows may not have separate freight/other GST fields, so we show freight/other as taxable charges and keep GST totals from saved values.
    cgst_total = first_num("cgst_total") or row_cgst
    sgst_total = first_num("sgst_total") or row_sgst
    igst_total = first_num("igst_total") or row_igst
    total_gst = cgst_total + sgst_total + igst_total

    net_value = first_num("net_value")
    if net_value == 0:
        net_value = sum(float(x.get("total", 0) or 0) for x in rows) + freight + other_exp - tds

    gross_value = first_num("gross_value")
    if gross_value == 0:
        gross_value = net_value + tds

    summary = {
        "basic_taxable_total": basic_taxable_total,
        "discount": discount,
        "taxable_total": taxable_after_discount,
        "freight": freight,
        "other_exp": other_exp,
        "tds": tds,
        "cgst_total": cgst_total,
        "sgst_total": sgst_total,
        "igst_total": igst_total,
        "total_gst": total_gst,
        "gross_total": gross_value,
    }

    html = invoice_html(title, selected_invoice_no, party, rows, net_value, summary, safe_get_ledger_details(party))
    return html, f"saved_{title.replace(' ', '_')}_{selected_invoice_no}.html"

# ---------- LOGIN / SIDEBAR ----------
def rbm_header():
    name = st.session_state.get("client_name", get_client_code())
    html = f"""<div class="rbm-header">
        <div class="rbm-title">RBM AI</div>
        <div class="rbm-divider">|</div>
        <div><div class="rbm-subtitle">Robotic Business Management</div><div style="font-size:11px;color:#e0f2fe;font-weight:700;margin-top:2px;letter-spacing:.5px;">स्वदेशी • Made in India</div></div>
        <div class="rbm-client">RBM ERP SaaS | {name}</div>
    </div>"""
    st.markdown(html, unsafe_allow_html=True)

def init_users():
    df = safe_df(supabase.table("users").select("*").execute().data)
    if df.empty:
        supabase.table("users").insert({
            "client_code": "RBM",
            "username": "developer",
            "password": "rbm123",
            "role": "Developer",
            "full_name": "RBM Developer",
            "status": "Active"
        }).execute()
        supabase.table("users").insert({
            "client_code": "RBM",
            "username": "admin",
            "password": "rbm123",
            "role": "Super Admin",
            "full_name": "RBM Super Admin",
            "status": "Active"
        }).execute()
        df = safe_df(supabase.table("users").select("*").execute().data)
    return df


def load_client_permissions(client_code):
    data = safe_df(supabase.table("clients").select("*").eq("client_code", client_code).limit(1).execute().data)
    permissions = ["allow_master_group","allow_task","allow_attendance","allow_inout","allow_visitor","allow_appointment","allow_stock_raw","allow_stock_fg","allow_stock_wip","allow_sales","allow_purchase","allow_expense","allow_service_voucher","allow_fixed_assets","allow_accounting","allow_excel_upload","allow_google_sheet_import","allow_quotation","allow_manufacturing","allow_project_accounting","allow_subscription","allow_support","allow_license_manager"]
    # Strict client security:
    # If a feature is not explicitly enabled for the client, it is treated as disabled.
    # RBM/Super Admin account can still see everything through is_super_admin().
    default_enabled = str(client_code).upper() == "RBM" and data.empty
    for p in permissions:
        st.session_state[p] = default_enabled
    name = client_code
    if not data.empty:
        row = data.iloc[0]; name = str(row.get("client_name", client_code))
        for p in permissions:
            # If column is missing/null, do NOT auto-enable for clients.
            st.session_state[p] = bool(row[p]) if p in row.index and pd.notna(row[p]) else False
    return name

def login_page():
    rbm_header(); show_header("Secure Login", "section-admin")
    users = init_users()
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            match = users[(users["username"].astype(str) == username) & (users["password"].astype(str) == password)]
            if match.empty: st.error("Wrong username or password")
            else:
                row = match.iloc[0]
                if str(row.get("status", "Active")) == "Inactive": st.error("This user is inactive."); return
                client_code = str(row.get("client_code", "RBM"))
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = str(row.get("role", "User"))
                st.session_state["full_name"] = str(row.get("full_name", username))
                st.session_state["client_code"] = client_code
                st.session_state["client_name"] = load_client_permissions(client_code)
                st.rerun()
        st.info("Welcome")

def sidebar_toggle_top():
    if "sidebar_open" not in st.session_state:
        st.session_state["sidebar_open"] = True

    if not st.session_state["sidebar_open"]:
        st.sidebar.markdown("""
        <div class='erp-box'>
          <div class='erp-name'>RBM AI</div>
          <div class='erp-small'><b>Menu Hidden</b></div>
        </div>
        """, unsafe_allow_html=True)

        if st.sidebar.button("☰ Show Menu", use_container_width=True, key="show_sidebar_menu_sidebar"):
            st.session_state["sidebar_open"] = True
            st.rerun()

        if st.button("☰ Show Menu", key="show_sidebar_menu_main"):
            st.session_state["sidebar_open"] = True
            st.rerun()

        st.caption("Menu is hidden. Click ☰ Show Menu to bring it back.")
        return False

    return True

def compact_sidebar():
    role = st.session_state.get("role", "")
    st.sidebar.markdown(f"""
    <div class='erp-box'>
      <div class='erp-name'>RBM AI</div>
      <div class='erp-small'><b>Name:</b> {st.session_state.get('client_name','RBM')}</div>
      <div class='erp-small'><b>Code:</b> {get_client_code()} | <b>Role:</b> {role}</div>
      <div class='erp-small'><b>User:</b> {st.session_state.get('full_name','')}</div>
      <div class='erp-small'><b>Date:</b> {india_now().strftime('%d-%m-%Y')} | IST</div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.sidebar.columns(2)
    if c1.button("◀ Hide", use_container_width=True, key="hide_sidebar_menu"):
        st.session_state["sidebar_open"] = False
        st.rerun()
    if c2.button("Logout", use_container_width=True, key="logout_sidebar"):
        st.session_state.clear()
        st.rerun()
    st.sidebar.markdown("<div class='rbm-menu-note'>Use ◀ Hide to hide menu. Use ☰ Show Menu to bring it back.</div>", unsafe_allow_html=True)

# ---------- MODULES ----------
def dashboard():
    show_header("Dashboard", "section-admin")
    st.info(f"Today: {india_now().strftime('%d-%m-%Y')} | India Time Zone: Asia/Kolkata | FY: {financial_year(india_now().date())}")
    metrics = [("Employees", get_count("employees")), ("Attendance", get_count("attendance")), ("Visits", get_count("attendance_visits")), ("Tasks", get_count("tasks")), ("Sales", get_count("sales")), ("Purchase", get_count("purchase")), ("Expenses", get_count("expenses")), ("Appointments", get_count("appointments")), ("Assets", get_count("fixed_assets"))]
    cols = st.columns(5)
    for i,(l,v) in enumerate(metrics[:5]):
        with cols[i]: show_metric_card(l,v)
    cols2 = st.columns(4)
    for i,(l,v) in enumerate(metrics[5:]):
        with cols2[i]: show_metric_card(l,v)

def client_master():
    show_header("Client Master", "section-admin")
    current_role = st.session_state.get("role", "")
    if current_role not in ["Developer", "Super Admin"]:
        st.warning("Client Master is Developer / RBM Super Admin only. Client Super Admin can create Admin/User from User Management.")
        return

    st.info("Same as Offline Desktop ERP: Group name + all module names are shown. Tick group to tick all modules; untick any module manually.")

    clients_df_existing = load_table("clients", 2000)

    # Client Super Admin can view/update only own company access panel, not create or see other clients.
    if current_role == "Client Super Admin":
        own_code = str(get_client_code()).upper().strip()
        if not clients_df_existing.empty and "client_code" in clients_df_existing.columns:
            clients_df_existing = clients_df_existing[clients_df_existing["client_code"].astype(str).str.upper().str.strip() == own_code]
        existing_codes = [own_code]
    else:
        existing_codes = clients_df_existing["client_code"].dropna().astype(str).tolist() if (not clients_df_existing.empty and "client_code" in clients_df_existing.columns) else []

    c1, c2, c3 = st.columns(3)
    existing_codes = sorted(list(dict.fromkeys([str(x).strip().upper() for x in existing_codes if str(x).strip()])))
    if current_role == "Client Super Admin":
        selected_existing = c1.selectbox("Company Code", existing_codes or [str(get_client_code()).upper()], key="cm_existing_code_client")
    else:
        selected_existing = c1.selectbox("Select Existing Company Code / New", ["New Client"] + existing_codes, key="cm_existing_code")

    default_code = "" if selected_existing == "New Client" else selected_existing
    default_name = ""
    default_status = "Active"
    if selected_existing != "New Client" and not clients_df_existing.empty:
        row_df = clients_df_existing[clients_df_existing["client_code"].astype(str).str.upper() == selected_existing]
        if not row_df.empty:
            default_name = str(row_df.iloc[0].get("client_name", row_df.iloc[0].get("name", "")) or "")
            default_status = str(row_df.iloc[0].get("status", "Active") or "Active")

    if selected_existing == "New Client":
        company_code = c1.text_input("New Company Code", value="", placeholder="Example: BWR01 / SJM01", key="cm_new_company_code").upper().strip()
    else:
        company_code = c1.text_input("Company Code", value=default_code, key=f"cm_existing_company_code_{selected_existing}", disabled=True).upper().strip()
    client_name = c2.text_input("Client Name", value=default_name, placeholder="Example: Siyaram Silk Mills Limited", key=f"cm_client_name_{selected_existing}")
    status = c3.selectbox("Status", ["Active", "Inactive"], index=0 if default_status != "Inactive" else 1, key=f"cm_status_{selected_existing}")

    st.markdown("### Client Group + Module Permission")
    st.caption("Offline Desktop ERP style: every group is shown with its modules. First tick group name; all modules tick automatically. Then untick any module manually if required.")

    selected_groups = {}
    selected_modules = {}

    group_to_old_flag = {
        "Master": "allow_master_group",
        "HR": "allow_attendance",
        "Inventory": "allow_stock_raw",
        "Manufacturing": "allow_manufacturing",
        "Accounts": "allow_accounting",
        "Sales": "allow_sales",
        "Purchase": "allow_purchase",
        "Expense": "allow_expense",
        "Projects": "allow_project_accounting",
        "Quotation": "allow_quotation",
        "Support": "allow_support",
        "Tools": "allow_excel_upload",
        "Reports": "allow_master_group",
    }

    color_map = {"Developer":"🔴", "SAP":"🔵", "QuickBooks":"🟢", "Tally":"🟠", "RBM":"🟣"}

    # Load existing detailed permissions if table exists, so edit screen remembers old ticks.
    existing_perm = {}
    if selected_existing != "New Client":
        try:
            pdf = safe_df(supabase.table("client_module_permissions").select("module_name,is_enabled").eq("client_code", selected_existing).execute().data)
            if not pdf.empty and "module_name" in pdf.columns:
                existing_perm = {str(r["module_name"]): bool(r.get("is_enabled", False)) for _, r in pdf.iterrows()}
        except Exception:
            existing_perm = {}

    for group_name, modules in ONLINE_MODULE_GROUPS.items():
        if group_name == "Dashboard":
            continue
        st.markdown(f"---\n#### {group_name}")
        # Existing old flag fallback
        default_group_value = False
        if selected_existing != "New Client" and not clients_df_existing.empty:
            old_flag = group_to_old_flag.get(group_name)
            if old_flag and old_flag in clients_df_existing.columns:
                row_df = clients_df_existing[clients_df_existing["client_code"].astype(str) == selected_existing]
                if not row_df.empty:
                    default_group_value = bool(row_df.iloc[0].get(old_flag, False))
        # RBM RULE: Developer-only modules (red) must stay unticked by default.
        # All other color modules must be ticked by default, same as offline desktop ERP.
        non_developer_modules = [m for m in modules if module_tag(m) != "Developer"]
        developer_modules = [m for m in modules if module_tag(m) == "Developer"]
        if selected_existing == "New Client" or not existing_perm:
            default_group_value = bool(non_developer_modules)
        elif any(existing_perm.values()):
            default_group_value = all(existing_perm.get(m, False) for m in non_developer_modules)

        group_key = f"cm_group_{group_name}_{selected_existing}"
        prev_group_key = f"cm_group_prev_{group_name}_{selected_existing}"

        tick_group = st.checkbox(
            f"Tick Full Group: {group_name}",
            value=default_group_value,
            key=group_key,
        )

        # IMPORTANT FIX: if full group tick is changed, immediately tick/untick all child modules.
        # Red Developer-only modules always remain unticked for client permission.
        previous_tick = st.session_state.get(prev_group_key, None)
        if previous_tick is None:
            st.session_state[prev_group_key] = tick_group
        elif bool(previous_tick) != bool(tick_group):
            for child_module in modules:
                child_key = f"cm_mod_{selected_existing}_{group_name}_{child_module}"
                st.session_state[child_key] = False if module_tag(child_module) == "Developer" else bool(tick_group)
            st.session_state[prev_group_key] = tick_group

        selected_groups[group_name] = tick_group
        cols = st.columns(4)
        for i, module in enumerate(modules):
            tag = module_tag(module)
            prefix = color_map.get(tag, "🟣")
            mod_key = f"cm_mod_{selected_existing}_{group_name}_{module}"
            if tag == "Developer":
                # Red modules are Developer-only, so never auto-tick them for a client.
                default_module = False
            else:
                # Non-red modules are active/ticked by default. Existing permissions are respected while editing.
                default_module = existing_perm.get(module, True if selected_existing == "New Client" or not existing_perm else tick_group)
            with cols[i % 4]:
                selected_modules[module] = st.checkbox(f"{prefix} {module}", value=default_module, key=mod_key)

    st.markdown("---")
    submitted = st.button("Save Client with Offline Style Group + Module Permissions", use_container_width=True, type="primary")
    if submitted:
        if not company_code or not client_name:
            st.error("Company Code and Client Name required")
        else:
            created_by = current_user()
            row = {"client_code": company_code, "client_name": client_name, "name": client_name, "status": status, "created_by": created_by}
            for old_col in [
                "allow_master_group","allow_attendance","allow_inout","allow_visitor","allow_task","allow_appointment",
                "allow_stock_raw","allow_stock_fg","allow_stock_wip","allow_sales","allow_purchase","allow_expense",
                "allow_service_voucher","allow_fixed_assets","allow_accounting","allow_excel_upload","allow_google_sheet_import",
                "allow_quotation","allow_manufacturing","allow_project_accounting","allow_subscription","allow_support","allow_license_manager"
            ]:
                row[old_col] = False
            for g, old_col in group_to_old_flag.items():
                if selected_groups.get(g):
                    row[old_col] = True
            if selected_groups.get("HR"):
                row.update({"allow_attendance": True, "allow_inout": True, "allow_visitor": True, "allow_task": True, "allow_appointment": True})
            if selected_groups.get("Inventory"):
                row.update({"allow_stock_raw": True, "allow_stock_fg": True, "allow_stock_wip": True})
            if selected_groups.get("Expense"):
                row.update({"allow_expense": True, "allow_service_voucher": True})
            if selected_groups.get("Accounts"):
                row.update({"allow_accounting": True, "allow_fixed_assets": True})
            if selected_groups.get("Support"):
                row.update({"allow_support": True, "allow_subscription": True})
            if selected_groups.get("Tools"):
                row.update({"allow_excel_upload": True, "allow_google_sheet_import": True})

            # Supabase clients table may be old/new schema.
            # Save only safe columns so client creation never crashes because of an extra column.
            safe_client_columns = [
                "client_code", "client_name", "status",
                "allow_master_group", "allow_attendance", "allow_inout", "allow_visitor", "allow_task", "allow_appointment",
                "allow_stock_raw", "allow_stock_fg", "allow_stock_wip", "allow_sales", "allow_purchase", "allow_expense",
                "allow_service_voucher", "allow_fixed_assets", "allow_accounting", "allow_excel_upload", "allow_google_sheet_import",
                "allow_quotation", "allow_manufacturing", "allow_project_accounting", "allow_subscription", "allow_support", "allow_license_manager"
            ]
            client_row = {k: v for k, v in row.items() if k in safe_client_columns}

            try:
                exists = safe_df(supabase.table("clients").select("id,client_code").eq("client_code", company_code).limit(1).execute().data)
                if not exists.empty:
                    supabase.table("clients").update(client_row).eq("client_code", company_code).execute()
                else:
                    supabase.table("clients").insert(client_row).execute()
            except Exception as e:
                # Last fallback for very old clients table: save only the minimum columns.
                try:
                    minimal_client_row = {"client_code": company_code, "client_name": client_name, "status": status}
                    exists = safe_df(supabase.table("clients").select("id,client_code").eq("client_code", company_code).limit(1).execute().data)
                    if not exists.empty:
                        supabase.table("clients").update(minimal_client_row).eq("client_code", company_code).execute()
                    else:
                        supabase.table("clients").insert(minimal_client_row).execute()
                except Exception as e2:
                    st.error("Client save failed. Please check Supabase clients table columns: client_code, client_name, status.")
                    st.exception(e2)
                    return

            try:
                supabase.table("client_module_permissions").delete().eq("client_code", company_code).execute()
                perm_rows = []
                for group_name, modules in ONLINE_MODULE_GROUPS.items():
                    if group_name == "Dashboard":
                        continue
                    for module in modules:
                        perm_rows.append({
                            "client_code": company_code,
                            "group_name": group_name,
                            "module_name": module,
                            "is_enabled": bool(selected_modules.get(module, False)),
                            "source_tag": module_tag(module),
                            "created_by": created_by,
                        })
                if perm_rows:
                    supabase.table("client_module_permissions").insert(perm_rows).execute()
            except Exception:
                st.warning("Client saved. Detailed module permission table is not created yet in Supabase. Old group flags are saved. Create client_module_permissions table using included SQL for module-wise permissions.")

            st.success("Client saved with Offline Desktop style group/module permissions.")
            st.rerun()

    client_list_df = load_table("clients", 500)
    if st.session_state.get("role") == "Client Super Admin" and not client_list_df.empty and "client_code" in client_list_df.columns:
        client_list_df = client_list_df[client_list_df["client_code"].astype(str).str.upper().str.strip() == str(get_client_code()).upper().strip()]
    show_table_with_edit_delete("clients", client_list_df, "Client List")

def user_management():
    show_header("User Management", "section-admin")

    if st.session_state.get("role") not in ["Developer", "Super Admin", "Client Super Admin", "Admin"]:
        st.warning("Only Developer, Super Admin, Client Super Admin or Admin can access User Management.")
        return

    if is_super_admin():
        clients_df = load_table("clients", 2000)
        client_codes = clients_df["client_code"].dropna().astype(str).str.upper().tolist() if (not clients_df.empty and "client_code" in clients_df.columns) else []
        client_codes = sorted(list(dict.fromkeys([c for c in client_codes if c])))
        if "RBM" not in client_codes:
            client_codes = ["RBM"] + client_codes
        else:
            client_codes = ["RBM"] + [c for c in client_codes if c != "RBM"]
        selected_client_code = st.selectbox("Client Code", client_codes, key="um_client_code")
        users_df = load_table("users", 2000)
    else:
        selected_client_code = get_client_code()
        st.info(f"You are creating users only for your business: {selected_client_code}")
        users_df = load_table("users", 2000)

    with st.form("user_form"):
        c1, c2 = st.columns(2)

        c1.text_input("Client Code", value=selected_client_code, disabled=True)
        password = c2.text_input("Password", type="password")

        username = c1.text_input("Username")
        full_name = c2.text_input("Full Name")

        email = c1.text_input("Email ID")
        mobile = c2.text_input("Mobile No.")

        current_role = st.session_state.get("role", "")
        if current_role == "Developer":
            role_options = ["Developer", "Super Admin", "Client Super Admin", "Admin", "User", "Quotation User", "Accounts User", "HR User", "Inventory User"]
        elif current_role == "Super Admin":
            role_options = ["Client Super Admin", "Admin", "User", "Quotation User", "Accounts User", "HR User", "Inventory User"]
        elif current_role == "Client Super Admin":
            # Client Super Admin can create Admin and normal users only inside own company.
            # Developer and platform Super Admin roles are hidden from client users.
            role_options = ["Admin", "User", "Quotation User", "Accounts User", "HR User", "Inventory User"]
        else:
            # Admin can create limited users only.
            role_options = ["User", "Quotation User", "Accounts User", "HR User", "Inventory User"]

        role = c1.selectbox("Role", role_options)

        status = c2.selectbox("Status", ["Active", "Inactive"])

        if st.form_submit_button("Create User", use_container_width=True):
            username_clean = username.strip()
            password_clean = password.strip()

            if username_clean == "" or password_clean == "":
                st.error("Username and password are required.")
            else:
                all_users = safe_df(supabase.table("users").select("*").execute().data)
                if not all_users.empty:
                    duplicate = all_users[
                        (all_users["username"].astype(str) == username_clean) &
                        (all_users["client_code"].astype(str) == selected_client_code)
                    ]
                else:
                    duplicate = pd.DataFrame()

                if not duplicate.empty:
                    st.error("This username already exists for this client.")
                else:
                    insert_row("users", {
                        "client_code": selected_client_code,
                        "username": username_clean,
                        "password": password_clean,
                        "role": role,
                        "full_name": full_name.strip(),
                        "email": email.strip(),
                        "mobile": mobile.strip(),
                        "status": status
                    })
                    st.success("User created successfully.")
                    st.rerun()

    st.subheader("User List")
    if not is_super_admin() and "client_code" in users_df.columns:
        users_df = users_df[users_df["client_code"].astype(str) == selected_client_code]

    show_table_with_edit_delete("users", users_df, "User List")


def employee_master():
    show_header("Employee Master", "section-admin")
    df = load_table("employees", 500)
    next_id = "EMP001" if df.empty else f"EMP{len(df)+1:03d}"
    with st.form("employee_form"):
        c1,c2 = st.columns(2)
        employee_id = c1.text_input("Employee ID", value=next_id)
        employee_name = c2.text_input("Employee Name")
        mobile = c1.text_input("Mobile"); email = c2.text_input("Email")
        department = c1.text_input("Department"); designation = c2.text_input("Designation")
        branch_division = c1.text_input("Branch / Division"); status = c2.selectbox("Status", ["Active","Inactive"])
        if st.form_submit_button("Save Employee", use_container_width=True):
            if not employee_name: st.error("Employee Name required")
            else: insert_row("employees", locals() | {"created_by": current_user()}); st.success("Employee saved"); st.rerun()
    show_table_with_edit_delete("employees", df, "Employee List")

# Master Group
def ledger_group_master():
    show_header("Ledger Group Master", "section-master")
    with st.form("ledger_group_form"):
        c1,c2 = st.columns(2)
        group_name = c1.selectbox("Ledger Group", get_groups("ledger_groups", "group_name", DEFAULT_LEDGER_GROUPS))
        custom = c1.text_input("Or New Group Name")
        group_type = c2.selectbox("Group Type", ["Asset","Liability","Income","Expense","Bank/Cash","Duties & Taxes","Other"])
        status = c2.selectbox("Status", ["Active","Inactive"])
        if st.form_submit_button("Save Ledger Group", use_container_width=True):
            insert_row("ledger_groups", {"group_name": custom.strip() or group_name, "group_type": group_type, "status": status, "created_by": current_user()}); st.success("Ledger group saved"); st.rerun()
    show_table_with_edit_delete("ledger_groups", load_table("ledger_groups", 500), "Ledger Group List")

def ledger_master():
    show_header("Ledger Master", "section-master")
    groups = get_groups("ledger_groups", "group_name", DEFAULT_LEDGER_GROUPS)
    with st.form("ledger_form"):
        c1,c2 = st.columns(2)
        ledger_name = c1.text_input("Ledger Name")
        ledger_group = c2.selectbox("Ledger Group", groups)
        address = c1.text_area("Address")
        contact_no = c2.text_input("Contact No")
        email = c1.text_input("Email")
        tan_no = c2.text_input("TAN No")
        gst_no = c1.text_input("GST No")
        pan_no = c2.text_input("PAN No")
        opening_balance = c1.number_input("Opening Balance", value=0.0)
        balance_type = c2.selectbox("Balance Type", ["Dr", "Cr"])
        status = c1.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Ledger", use_container_width=True):
            if not ledger_name:
                st.error("Ledger Name required")
            else:
                insert_row("ledgers", {"ledger_name":ledger_name,"ledger_group":ledger_group,"address":address,"contact_no":contact_no,"email":email,"tan_no":tan_no,"gst_no":gst_no,"pan_no":pan_no,"opening_balance":opening_balance,"balance_type":balance_type,"status":status,"created_by":current_user()})
                st.success("Ledger saved")
                st.rerun()
    show_table_with_edit_delete("ledgers", load_table("ledgers", 500), "Ledger List")

def stock_group_master():
    show_header("Stock Group Master", "section-master")
    with st.form("stock_group_form"):
        c1,c2 = st.columns(2)
        stock_group_name = c1.selectbox("Stock Group", get_groups("stock_groups", "stock_group_name", DEFAULT_STOCK_GROUPS))
        custom = c1.text_input("Or New Stock Group")
        stock_type = c2.selectbox("Stock Type", ["Raw Material","Finished Goods","WIP","Packing","Consumables","Trading","Other"])
        status = c2.selectbox("Status", ["Active","Inactive"])
        if st.form_submit_button("Save Stock Group", use_container_width=True):
            insert_row("stock_groups", {"stock_group_name": custom.strip() or stock_group_name,"stock_type":stock_type,"status":status,"created_by":current_user()}); st.success("Stock group saved"); st.rerun()
    show_table_with_edit_delete("stock_groups", load_table("stock_groups",500), "Stock Group List")

def stock_ledger_master():
    show_header("Stock Ledger / Item Master", "section-master")
    groups = get_groups("stock_groups", "stock_group_name", DEFAULT_STOCK_GROUPS)
    with st.form("stock_ledger_form"):
        c1,c2 = st.columns(2)
        item_name = c1.text_input("Item Name")
        item_code = c2.text_input("Item Code")
        stock_group = c1.selectbox("Stock Group", groups)
        unit = c2.selectbox("Unit", ["PCS","KG","MTR","LTR","NOS","BOX","BAG","SET","OTHER"])
        hsn_code = c1.text_input("HSN Code")
        gst_rate = c2.number_input("GST Rate %", value=18.0)
        opening_qty = c1.number_input("Opening Qty", value=0.0)
        opening_rate = c2.number_input("Opening Rate", value=0.0)
        opening_value = opening_qty * opening_rate
        st.info(f"Opening Value: {money(opening_value)}")
        status = c1.selectbox("Status", ["Active","Inactive"])
        if st.form_submit_button("Save Stock Ledger", use_container_width=True):
            if not item_name: st.error("Item Name required")
            else: insert_row("stock_ledgers", {"item_name":item_name,"item_code":item_code,"stock_group":stock_group,"unit":unit,"hsn_code":hsn_code,"gst_rate":gst_rate,"opening_qty":opening_qty,"opening_rate":opening_rate,"opening_value":opening_value,"status":status,"created_by":current_user()}); st.success("Stock ledger saved"); st.rerun()
    show_table_with_edit_delete("stock_ledgers", load_table("stock_ledgers",500), "Stock Ledger List")

# HR / Admin modules
def attendance():
    show_header("Attendance Management with GPS", "section-hr")
    emp = load_table("employees", 1000); emp_list = emp["employee_name"].dropna().astype(str).tolist() if not emp.empty else ["No Employee Found"]
    loc = streamlit_geolocation(); lat = str((loc or {}).get("latitude", "") or ""); lon = str((loc or {}).get("longitude", "") or "")
    if lat and lon: st.success(f"GPS: {lat}, {lon}")
    attendance_type = st.radio("Attendance Type", ["Office","Visit"], horizontal=True)
    with st.form("att_form"):
        c1,c2 = st.columns(2); d = c1.date_input("Date", value=india_now().date(), format="DD-MM-YYYY"); empname = c2.selectbox("Employee", emp_list)
        if attendance_type == "Office":
            status = c1.selectbox("Status", ["Present","Absent","Half Day","Leave"]); office_location = c2.text_input("Office Location", "Office")
            in_time = c1.time_input("In Time", value=india_now().time()); out_time = c2.time_input("Out Time", value=india_now().time()); remarks = c1.text_input("Remarks")
            controls = entry_controls("attendance_office_ctrl")
            if st.form_submit_button("Save Office Attendance", use_container_width=True):
                row = {"attendance_date":str(d),"financial_year":financial_year(d),"employee_name":empname,"attendance_type":"Office","office_location":office_location,"status":status,"in_time":str(in_time),"out_time":str(out_time),"working_hours":calculate_hours(in_time,out_time),"in_latitude":lat,"in_longitude":lon,"remarks":remarks,"created_by":current_user()}
                row.update(controls)
                insert_row("attendance", row); st.success("Saved"); st.rerun()
        else:
            place = c1.text_input("Visit Place"); in_time = c2.time_input("Visit In", value=india_now().time()); out_time = c1.time_input("Visit Out", value=india_now().time()); remarks = c2.text_input("Remarks")
            controls = entry_controls("attendance_visit_ctrl")
            if st.form_submit_button("Save Visit", use_container_width=True):
                row = {"visit_date":str(d),"financial_year":financial_year(d),"employee_name":empname,"visit_place":place,"in_time":str(in_time),"out_time":str(out_time),"in_latitude":lat,"in_longitude":lon,"remarks":remarks,"created_by":current_user()}
                row.update(controls)
                insert_row("attendance_visits", row); st.success("Saved"); st.rerun()
    show_table_with_edit_delete("attendance", load_table("attendance",500), "Office Attendance")
    show_table_with_edit_delete("attendance_visits", load_table("attendance_visits",500), "Visit Attendance")

def simple_module_form(key, title, fields, cls):
    show_header(title, cls)
    with st.form(f"{key}_form"):
        vals={}; cols=st.columns(2)
        for i,(name,label,typ) in enumerate(fields):
            c=cols[i%2]
            if typ=="date": vals[name]=str(c.date_input(label, value=india_now().date(), format="DD-MM-YYYY"))
            elif typ=="time": vals[name]=str(c.time_input(label, value=india_now().time()))
            elif typ=="number": vals[name]=c.number_input(label, value=0.0)
            elif isinstance(typ, list): vals[name]=c.selectbox(label, typ)
            else: vals[name]=c.text_input(label)
        controls = entry_controls(f"{key}_ctrl")
        if st.form_submit_button(f"Save {title}", use_container_width=True):
            vals.update(controls)
            vals["created_by"]=current_user(); insert_row(key, vals); st.success("Saved"); st.rerun()
    show_table_with_edit_delete(key, load_table(key,500), f"{title} Register")

def inout_register(): simple_module_form("inout", "IN / OUT Register", [("entry_date","Date","date"),("person_name","Person Name","text"),("purpose","Purpose","text"),("in_time","In Time","time"),("out_time","Out Time","time"),("remarks","Remarks","text")], "section-hr")
def visitor_register(): simple_module_form("visitors", "Visitor Register", [("visit_date","Date","date"),("visitor_name","Visitor Name","text"),("mobile","Mobile","text"),("company","Company","text"),("meeting_with","Meeting With","text"),("purpose","Purpose","text"),("in_time","In Time","time"),("out_time","Out Time","time"),("remarks","Remarks","text")], "section-hr")
def appointment_module(): simple_module_form("appointments", "Client / Customer Appointment", [("appointment_date","Date","date"),("appointment_time","Time","time"),("customer_name","Customer Name","text"),("mobile","Mobile","text"),("email","Email","text"),("company","Company","text"),("purpose","Purpose","text"),("meeting_with","Meeting With","text"),("fees","Fees","number"),("status","Status",["Scheduled","Completed","Cancelled"]),("remarks","Remarks","text")], "section-admin")

def task_delegation():
    show_header("Task Delegation", "section-hr")
    emp = load_table("employees", 1000); emp_list = ["All"] + (emp["employee_name"].dropna().astype(str).tolist() if not emp.empty else [])
    branches = ["All"] + (sorted(emp["branch_division"].dropna().astype(str).unique().tolist()) if not emp.empty and "branch_division" in emp.columns else [])
    with st.form("task_form", clear_on_submit=True):
        c1,c2=st.columns(2); task_date=str(c1.date_input("Task Date", value=india_now().date(), format="DD-MM-YYYY")); branch_division=c1.selectbox("Branch / Division", branches); task=c2.text_area("Task")
        assigned_to=c2.selectbox("Assigned To", emp_list); priority=c1.selectbox("Priority", ["Low","Medium","High","Urgent"]); due_date=str(c2.date_input("Due Date", value=india_now().date(), format="DD-MM-YYYY")); status=c1.selectbox("Status", ["Pending","In Progress","Completed"]); remarks=c2.text_input("Remarks")
        controls = entry_controls("task_ctrl")
        photo = st.file_uploader("Upload Task Photo - Max 2 MB", type=["png","jpg","jpeg"]); photo_name=""; photo_data=""; ok=True
        if photo:
            if photo.size > MAX_FILE_SIZE_MB*1024*1024: st.error("Photo size 2 MB se zyada nahi honi chahiye."); ok=False
            else: photo_name=photo.name; photo_data=base64.b64encode(photo.read()).decode("utf-8")
        if st.form_submit_button("Save Task", use_container_width=True):
            if not task or not ok: st.error("Task required / photo size check")
            else:
                row = {"task_date":task_date,"financial_year":financial_year(task_date),"branch_division":branch_division,"task":task,"assigned_to":assigned_to,"priority":priority,"due_date":due_date,"status":status,"remarks":remarks,"task_photo_name":photo_name,"task_photo_data":photo_data,"created_by":current_user()}
                row.update(controls)
                insert_row("tasks", row); st.success("Task saved"); st.rerun()
    show_table_with_edit_delete("tasks", load_table("tasks",500), "Task Records")

# Inventory modules
def stock_raw(): simple_module_form("stock_raw", "Raw Material Stock", [("entry_date","Date","date"),("item_name","Item Name",get_stock_items("Raw Material")),("item_code","Item Code","text"),("unit","Unit","text"),("opening_qty","Opening Qty","number"),("inward_qty","Inward Qty","number"),("outward_qty","Outward Qty","number"),("closing_qty","Closing Qty","number"),("rate","Rate","number"),("value","Value","number"),("remarks","Remarks","text")], "section-inv")
def stock_fg(): simple_module_form("stock_fg", "Finished Goods Stock", [("entry_date","Date","date"),("item_name","Item Name",get_stock_items("Finished Goods")),("item_code","Item Code","text"),("unit","Unit","text"),("opening_qty","Opening Qty","number"),("production_qty","Production Qty","number"),("sales_qty","Sales Qty","number"),("closing_qty","Closing Qty","number"),("rate","Rate","number"),("value","Value","number"),("remarks","Remarks","text")], "section-inv")
def stock_wip(): simple_module_form("stock_wip", "WIP Stock", [("entry_date","Date","date"),("process_name","Process Name","text"),("item_name","Item Name",get_stock_items()),("item_code","Item Code","text"),("unit","Unit","text"),("opening_qty","Opening Qty","number"),("input_qty","Input Qty","number"),("output_qty","Output Qty","number"),("closing_qty","Closing Qty","number"),("remarks","Remarks","text")], "section-inv")
def stock_voucher(): simple_module_form("stock_vouchers", "Stock Voucher", [("voucher_no","Voucher No","text"),("voucher_date","Date","date"),("voucher_type","Voucher Type",["Receipt","Issue","Transfer","Adjustment"]),("item_name","Item Name",get_stock_items()),("stock_group","Stock Group",get_groups("stock_groups","stock_group_name",DEFAULT_STOCK_GROUPS)),("qty","Qty","number"),("rate","Rate","number"),("value","Value","number"),("remarks","Remarks","text")], "section-inv")

# GST / voucher modules
def sales_invoice(): voucher_invoice("sales", "Sales GST Invoice", "customer_name", get_ledger_names("Sundry Debtors"), "section-acc")
def purchase_invoice(): voucher_invoice("purchase", "Purchase GST Invoice", "supplier_name", get_ledger_names("Sundry Creditors"), "section-acc")

def voucher_invoice(key, title, party_col, party_list, cls):
    show_header(title, cls)
    default_group = "Sundry Debtors" if key == "sales" else "Sundry Creditors"
    quick_ledger_creator(default_group=default_group, key_prefix=f"{key}_party_ledger")
    quick_stock_item_creator(default_group="Finished Goods" if key == "sales" else "Raw Material", key_prefix=f"{key}_stock_item")

    party_list = get_ledger_names(default_group)
    stock_items = get_stock_items()

    item_count_key = f"{key}_invoice_item_count"
    if item_count_key not in st.session_state:
        st.session_state[item_count_key] = 1

    a_add, a_remove, a_clear = st.columns(3)
    with a_add:
        if st.button("➕ Add Multiple Item", use_container_width=True, key=f"{key}_add_item_btn"):
            st.session_state[item_count_key] += 1
            st.rerun()
    with a_remove:
        if st.button("➖ Remove Last Item", use_container_width=True, key=f"{key}_remove_item_btn"):
            if st.session_state[item_count_key] > 1:
                st.session_state[item_count_key] -= 1
                st.rerun()
    with a_clear:
        if st.button("🔄 Reset Items", use_container_width=True, key=f"{key}_reset_item_btn"):
            st.session_state[item_count_key] = 1
            st.rerun()

    no_items = int(st.session_state[item_count_key])

    with st.form(f"{key}_form"):
        c1, c2, c3 = st.columns(3)
        inv_no = c1.text_input("Invoice / Voucher No")
        inv_date = str(c2.date_input("Date", value=india_now().date(), format="DD-MM-YYYY"))
        party = c3.selectbox("Customer Ledger" if key == "sales" else "Vendor Ledger", party_list)
        gstin = c1.text_input("GSTIN")
        gst_type = c2.selectbox("GST Type", ["CGST+SGST", "IGST"])
        c3.info(f"Items: {no_items}")

        raw_rows = []
        basic_taxable_total = 0.0
        for i in range(no_items):
            st.markdown(f"### Item {i + 1}")
            a, b, c, d, e = st.columns(5)
            item = a.selectbox("Item", stock_items, key=f"{key}_item_{i}")
            hsn = b.text_input("HSN/SAC", key=f"{key}_hsn_{i}")
            qty = c.number_input("Qty", min_value=0.0, value=1.0, step=1.0, key=f"{key}_qty_{i}")
            rate = d.number_input("Rate", min_value=0.0, value=0.0, step=1.0, key=f"{key}_rate_{i}")
            gst_rate = e.number_input("GST %", min_value=0.0, value=18.0, step=1.0, key=f"{key}_gst_{i}")
            taxable = round(qty * rate, 2)
            basic_taxable_total += taxable
            raw_rows.append({"item": item, "hsn": hsn, "qty": qty, "rate": rate, "gst_rate": gst_rate, "taxable_before_discount": taxable})
            st.caption(f"Item Taxable: {money(taxable)}")

        st.markdown("### Auto Calculation / Adjustments")
        d1, d2, f1, f2 = st.columns(4)
        discount_type = d1.selectbox("Discount Type", ["Amount", "%"], key=f"{key}_discount_type")
        discount_input = d2.number_input("Discount (-)", min_value=0.0, value=0.0, step=1.0, key=f"{key}_discount_input")
        freight = f1.number_input("Freight (+)", min_value=0.0, value=0.0, step=1.0, key=f"{key}_freight")
        freight_gst_rate = f2.number_input("Freight GST %", min_value=0.0, value=18.0, step=1.0, key=f"{key}_freight_gst")

        o1, o2, t1, t2 = st.columns(4)
        other_exp = o1.number_input("Other Charges (+)", min_value=0.0, value=0.0, step=1.0, key=f"{key}_other_exp")
        other_gst_rate = o2.number_input("Other Charges GST %", min_value=0.0, value=18.0, step=1.0, key=f"{key}_other_gst")
        tds_type = t1.selectbox("TDS Type", ["Amount", "%"], key=f"{key}_tds_type")
        tds_input = t2.number_input("TDS (-)", min_value=0.0, value=0.0, step=1.0, key=f"{key}_tds_input")

        discount = round((basic_taxable_total * discount_input / 100), 2) if discount_type == "%" else round(discount_input, 2)
        if discount > basic_taxable_total:
            discount = basic_taxable_total

        rows = []
        taxable_total = 0.0
        gst_total = 0.0
        gross_total = 0.0
        for r in raw_rows:
            share = (r["taxable_before_discount"] / basic_taxable_total) if basic_taxable_total else 0
            line_discount = round(discount * share, 2)
            taxable_after_discount = round(max(r["taxable_before_discount"] - line_discount, 0), 2)
            cgst, sgst, igst, line_total = gst_calc(taxable_after_discount, r["gst_rate"], gst_type)
            line_gst = round(cgst + sgst + igst, 2)
            taxable_total += taxable_after_discount
            gst_total += line_gst
            gross_total += line_total
            rows.append({
                "item": r["item"], "hsn": r["hsn"], "qty": r["qty"], "rate": r["rate"],
                "gst_rate": r["gst_rate"], "taxable": taxable_after_discount,
                "line_discount": line_discount, "cgst": cgst, "sgst": sgst, "igst": igst,
                "gst": line_gst, "total": line_total
            })

        freight_cgst, freight_sgst, freight_igst, freight_total = gst_calc(freight, freight_gst_rate, gst_type)
        other_cgst, other_sgst, other_igst, other_total = gst_calc(other_exp, other_gst_rate, gst_type)
        charges_taxable = round(freight + other_exp, 2)
        charges_gst = round(freight_cgst + freight_sgst + freight_igst + other_cgst + other_sgst + other_igst, 2)
        gross_before_tds = round(gross_total + freight_total + other_total, 2)
        tds_base = round(taxable_total + charges_taxable, 2)
        tds = round((tds_base * tds_input / 100), 2) if tds_type == "%" else round(tds_input, 2)
        grand = round(gross_before_tds - tds, 2)
        total_gst_with_charges = round(gst_total + charges_gst, 2)
        invoice_summary = {
            "basic_taxable_total": basic_taxable_total,
            "discount": discount,
            "taxable_total": taxable_total,
            "freight": freight,
            "freight_cgst": freight_cgst,
            "freight_sgst": freight_sgst,
            "freight_igst": freight_igst,
            "freight_total": freight_total,
            "other_exp": other_exp,
            "other_cgst": other_cgst,
            "other_sgst": other_sgst,
            "other_igst": other_igst,
            "other_total": other_total,
            "charges_taxable": charges_taxable,
            "charges_gst": charges_gst,
            "cgst_total": round(sum(float(x.get("cgst", 0) or 0) for x in rows) + freight_cgst + other_cgst, 2),
            "sgst_total": round(sum(float(x.get("sgst", 0) or 0) for x in rows) + freight_sgst + other_sgst, 2),
            "igst_total": round(sum(float(x.get("igst", 0) or 0) for x in rows) + freight_igst + other_igst, 2),
            "total_gst": total_gst_with_charges,
            "gross_total": gross_before_tds,
            "tds": tds,
        }
        remarks = st.text_input("Remarks")
        controls = entry_controls(f"{key}_voucher_ctrl")

        st.markdown("### Calculation Summary")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Basic Taxable", money(basic_taxable_total))
        s2.metric("Discount", money(discount))
        s3.metric("Taxable After Discount", money(taxable_total))
        s4.metric("Item GST", money(gst_total))
        s5, s6, s7, s8 = st.columns(4)
        s5.metric("Freight + Other", money(charges_taxable))
        s6.metric("GST on Charges", money(charges_gst))
        s7.metric("TDS", money(tds))
        s8.metric("Net Payable/Receivable", money(grand))
        st.info(
            f"Basic: {money(basic_taxable_total)} | Discount: {money(discount)} | "
            f"Taxable: {money(taxable_total + charges_taxable)} | GST: {money(total_gst_with_charges)} | "
            f"Gross: {money(gross_before_tds)} | Less TDS: {money(tds)} | Net: {money(grand)}"
        )

        if st.form_submit_button(f"Save {title}", use_container_width=True):
            if not rows:
                st.error("At least one item is required.")
            else:
                for r in rows:
                    row = {
                        "invoice_no": inv_no,
                        "invoice_date": inv_date,
                        party_col: party,
                        "gstin": gstin,
                        "item_name": r["item"],
                        "hsn_sac": r["hsn"],
                        "qty": r["qty"],
                        "rate": r["rate"],
                        "taxable_value": r["taxable"],
                        "discount": discount,
                        "freight": freight,
                        "other_exp": other_exp,
                        "tds": tds,
                        "cgst": r["cgst"],
                        "sgst": r["sgst"],
                        "igst": r["igst"],
                        "total_value": r["total"],
                        "gross_value": gross_before_tds,
                        "net_value": grand,
                        "remarks": remarks,
                        "created_by": current_user()
                    }
                    row.update(controls)
                    insert_row(key, row)

                if freight > 0 or other_exp > 0 or tds > 0:
                    st.info("Note: Freight, other charges and TDS are saved in the voucher rows. Net invoice value is saved in net_value.")
                st.session_state[item_count_key] = 1
                st.success("Voucher saved with automatic calculation.")
                st.rerun()

    st.divider()
    st.markdown("### Invoice Preview")
    st.caption("Select Current Invoice Preview to see the data currently filled above, or Saved Invoice Preview to print/download an already saved invoice.")
    preview_mode = st.radio(
        "Preview Source",
        ["Current Invoice Preview", "Saved Invoice Preview"],
        horizontal=True,
        key=f"{key}_single_preview_mode"
    )

    if preview_mode == "Saved Invoice Preview":
        html, file_name = get_saved_invoice_preview_html(key, title, party_col)
        if html:
            show_invoice_preview_and_download(html, file_name)
    else:
        current_party = party if 'party' in locals() else ''
        html = invoice_html(
            title,
            inv_no if 'inv_no' in locals() else '',
            current_party,
            rows if 'rows' in locals() else [],
            grand if 'grand' in locals() else 0,
            invoice_summary if 'invoice_summary' in locals() else {},
            safe_get_ledger_details(current_party)
        )
        show_invoice_preview_and_download(html, f"{title.replace(' ', '_')}.html")

    st.caption("Edit option: Use the Edit / Delete section below the register to modify saved Sales/Purchase entries.")
    show_table_with_edit_delete(key, load_table(key, 500), f"{title} Register")

def expense_gst():
    show_header("Expense GST Voucher", "section-acc")
    quick_ledger_creator(default_group="Sundry Creditors", key_prefix="expense_vendor_ledger")
    quick_ledger_creator(default_group="Indirect Expenses", key_prefix="expense_head_ledger")
    ledgers = get_ledger_names()

    exp_count_key = "expense_line_count"
    if exp_count_key not in st.session_state:
        st.session_state[exp_count_key] = 1

    e_add, e_remove, e_reset = st.columns(3)
    with e_add:
        if st.button("➕ Add Expense Line", use_container_width=True, key="expense_add_line_btn"):
            st.session_state[exp_count_key] += 1
            st.rerun()
    with e_remove:
        if st.button("➖ Remove Last Line", use_container_width=True, key="expense_remove_line_btn"):
            if st.session_state[exp_count_key] > 1:
                st.session_state[exp_count_key] -= 1
                st.rerun()
    with e_reset:
        if st.button("🔄 Reset Lines", use_container_width=True, key="expense_reset_line_btn"):
            st.session_state[exp_count_key] = 1
            st.rerun()

    with st.form("expense_form"):
        c1, c2, c3 = st.columns(3)
        expense_date = str(c1.date_input("Expense Date", value=india_now().date(), format="DD-MM-YYYY"))
        vendor_name = c2.selectbox("Vendor Ledger", ledgers)
        invoice_no = c3.text_input("Invoice No")
        gstin = c1.text_input("GSTIN")
        gst_type = c2.selectbox("GST Type", ["CGST+SGST", "IGST"])
        payment_mode = c3.selectbox("Payment Mode", ["Cash", "Bank", "UPI", "Credit"])

        raw_lines = []
        basic_taxable_total = 0.0
        for i in range(int(st.session_state[exp_count_key])):
            st.markdown(f"### Expense Line {i + 1}")
            a, b, c = st.columns([2, 1, 1])
            expense_head = a.selectbox("Expense Ledger", ledgers, key=f"expense_head_{i}")
            taxable_value = b.number_input("Taxable Value", min_value=0.0, value=0.0, step=1.0, key=f"expense_taxable_{i}")
            gst_rate = c.number_input("GST %", min_value=0.0, value=18.0, step=1.0, key=f"expense_gst_{i}")
            basic_taxable_total += taxable_value
            raw_lines.append({"expense_head": expense_head, "taxable_before_discount": taxable_value, "gst_rate": gst_rate})

        st.markdown("### Auto Calculation / Adjustments")
        d1, d2, f1, f2 = st.columns(4)
        discount_type = d1.selectbox("Discount Type", ["Amount", "%"], key="expense_discount_type")
        discount_input = d2.number_input("Discount (-)", min_value=0.0, value=0.0, step=1.0, key="expense_discount_input")
        freight = f1.number_input("Freight (+)", min_value=0.0, value=0.0, step=1.0, key="expense_freight")
        freight_gst_rate = f2.number_input("Freight GST %", min_value=0.0, value=18.0, step=1.0, key="expense_freight_gst")

        o1, o2, t1, t2 = st.columns(4)
        other_exp = o1.number_input("Other Charges (+)", min_value=0.0, value=0.0, step=1.0, key="expense_other_exp")
        other_gst_rate = o2.number_input("Other Charges GST %", min_value=0.0, value=18.0, step=1.0, key="expense_other_gst")
        tds_type = t1.selectbox("TDS Type", ["Amount", "%"], key="expense_tds_type")
        tds_input = t2.number_input("TDS (-)", min_value=0.0, value=0.0, step=1.0, key="expense_tds_input")

        discount = round((basic_taxable_total * discount_input / 100), 2) if discount_type == "%" else round(discount_input, 2)
        if discount > basic_taxable_total:
            discount = basic_taxable_total

        line_rows = []
        taxable_total = 0.0
        gst_total = 0.0
        gross_total = 0.0
        for r in raw_lines:
            share = (r["taxable_before_discount"] / basic_taxable_total) if basic_taxable_total else 0
            line_discount = round(discount * share, 2)
            taxable_after_discount = round(max(r["taxable_before_discount"] - line_discount, 0), 2)
            cgst, sgst, igst, gross_value = gst_calc(taxable_after_discount, r["gst_rate"], gst_type)
            taxable_total += taxable_after_discount
            gst_total += (cgst + sgst + igst)
            gross_total += gross_value
            line_rows.append({
                "expense_head": r["expense_head"],
                "taxable_value": taxable_after_discount,
                "line_discount": line_discount,
                "gst_rate": r["gst_rate"],
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
                "gross_value": gross_value
            })

        freight_cgst, freight_sgst, freight_igst, freight_total = gst_calc(freight, freight_gst_rate, gst_type)
        other_cgst, other_sgst, other_igst, other_total = gst_calc(other_exp, other_gst_rate, gst_type)
        charges_taxable = round(freight + other_exp, 2)
        charges_gst = round(freight_cgst + freight_sgst + freight_igst + other_cgst + other_sgst + other_igst, 2)
        gross_before_tds = round(gross_total + freight_total + other_total, 2)
        tds_base = round(taxable_total + charges_taxable, 2)
        tds = round((tds_base * tds_input / 100), 2) if tds_type == "%" else round(tds_input, 2)
        total_value = round(gross_before_tds - tds, 2)
        total_gst_with_charges = round(gst_total + charges_gst, 2)
        remarks = st.text_input("Remarks")
        controls = entry_controls("expense_ctrl")

        st.markdown("### Calculation Summary")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Basic Taxable", money(basic_taxable_total))
        s2.metric("Discount", money(discount))
        s3.metric("Taxable After Discount", money(taxable_total))
        s4.metric("Expense GST", money(gst_total))
        s5, s6, s7, s8 = st.columns(4)
        s5.metric("Freight + Other", money(charges_taxable))
        s6.metric("GST on Charges", money(charges_gst))
        s7.metric("TDS", money(tds))
        s8.metric("Net Payable", money(total_value))
        st.info(
            f"Basic: {money(basic_taxable_total)} | Discount: {money(discount)} | "
            f"Taxable: {money(taxable_total + charges_taxable)} | GST: {money(total_gst_with_charges)} | "
            f"Gross: {money(gross_before_tds)} | Less TDS: {money(tds)} | Net Payable: {money(total_value)}"
        )

        if st.form_submit_button("Save Expense GST", use_container_width=True):
            if not line_rows:
                st.error("At least one expense line is required.")
            else:
                for r in line_rows:
                    row = {
                        "expense_date": expense_date,
                        "vendor_name": vendor_name,
                        "expense_head": r["expense_head"],
                        "invoice_no": invoice_no,
                        "gstin": gstin,
                        "taxable_value": r["taxable_value"],
                        "discount": discount,
                        "freight": freight,
                        "other_exp": other_exp,
                        "tds": tds,
                        "cgst": r["cgst"],
                        "sgst": r["sgst"],
                        "igst": r["igst"],
                        "gross_value": gross_before_tds,
                        "net_value": total_value,
                        "total_value": r["gross_value"],
                        "payment_mode": payment_mode,
                        "remarks": remarks,
                        "created_by": current_user()
                    }
                    row.update(controls)
                    insert_row("expenses", row)
                st.session_state[exp_count_key] = 1
                st.success("Expense voucher saved with automatic calculation.")
                st.rerun()
    st.caption("Edit option: Use the Edit / Delete section below the register to modify saved Expense entries.")
    show_table_with_edit_delete("expenses", load_table("expenses", 500), "Expense Register")

def service_voucher():
    show_header("Service Voucher", "section-acc")
    customers=get_ledger_names("Sundry Debtors")
    with st.form("service_form"):
        c1,c2,c3=st.columns(3)
        voucher_no=c1.text_input("Voucher No"); voucher_date=str(c2.date_input("Date", value=india_now().date(), format="DD-MM-YYYY")); customer_name=c3.selectbox("Customer", customers)
        mobile=c1.text_input("Mobile"); email=c2.text_input("Email"); service_name=c3.text_input("Service Name")
        sac_code=c1.text_input("SAC Code"); taxable_value=c2.number_input("Taxable Value", value=0.0); gst_rate=c3.number_input("GST %", value=18.0)
        gst_type=c1.selectbox("GST Type", ["CGST+SGST","IGST"]); payment_status=c2.selectbox("Payment Status", ["Pending","Received","Partly Received"])
        cgst,sgst,igst,total_value=gst_calc(taxable_value,gst_rate,gst_type); remarks=st.text_input("Remarks")
        controls = entry_controls("service_ctrl")
        st.info(f"Total: {money(total_value)}")
        if st.form_submit_button("Save Service Voucher", use_container_width=True):
            row = {"voucher_no":voucher_no,"voucher_date":voucher_date,"customer_name":customer_name,"mobile":mobile,"email":email,"service_name":service_name,"sac_code":sac_code,"taxable_value":taxable_value,"cgst":cgst,"sgst":sgst,"igst":igst,"total_value":total_value,"payment_status":payment_status,"remarks":remarks,"created_by":current_user()}
            row.update(controls)
            insert_row("service_vouchers", row); st.success("Saved"); st.rerun()
    html=invoice_html("Service Voucher", voucher_no if 'voucher_no' in locals() else '', customer_name if 'customer_name' in locals() else '', [{"item":service_name if 'service_name' in locals() else '',"hsn":sac_code if 'sac_code' in locals() else '',"qty":1,"rate":taxable_value if 'taxable_value' in locals() else 0,"taxable":taxable_value if 'taxable_value' in locals() else 0,"gst":(cgst+sgst+igst) if 'cgst' in locals() else 0,"total":total_value if 'total_value' in locals() else 0}], total_value if 'total_value' in locals() else 0)
    show_invoice_preview_and_download(html, "service_voucher.html")
    show_table_with_edit_delete("service_vouchers", load_table("service_vouchers",500), "Service Register")

def fixed_assets(): simple_module_form("fixed_assets", "Fixed Assets", [("asset_code","Asset Code","text"),("asset_name","Asset Name","text"),("purchase_date","Purchase Date","date"),("supplier_name","Supplier",get_ledger_names("Sundry Creditors")),("invoice_no","Invoice No","text"),("asset_category","Category","text"),("location","Location","text"),("cost","Cost","number"),("depreciation_rate","Depreciation %","number"),("status","Status",["Active","Sold","Scrapped"]),("remarks","Remarks","text")], "section-acc")

def accounting_entries():
    show_header("Accounting Entries - Multiple Dr / Cr", "section-acc")
    quick_ledger_creator(default_group="Indirect Expenses", key_prefix="accounting_new_ledger")
    ledgers=get_ledger_names()
    with st.form("acc_form"):
        c1,c2,c3=st.columns(3)
        entry_date=str(c1.date_input("Entry Date", value=india_now().date(), format="DD-MM-YYYY")); voucher_type=c2.selectbox("Voucher Type", ["Journal","Payment","Receipt","Contra","GST Adjustment"]); voucher_no=c3.text_input("Voucher No")
        gst_rate=c1.number_input("GST % (optional)", value=0.0); gst_type=c2.selectbox("GST Type", ["None","CGST+SGST","IGST"])
        debit_count=c1.number_input("Debit Lines", min_value=1, max_value=10, value=1, step=1); credit_count=c2.number_input("Credit Lines", min_value=1, max_value=10, value=1, step=1)
        debit_lines=[]; credit_lines=[]
        st.markdown("### Debit Lines")
        for i in range(int(debit_count)):
            a,b,c=st.columns([2,1,2]); debit_lines.append({"ledger":a.selectbox("Dr Ledger", ledgers, key=f"dr_{i}"),"amount":b.number_input("Dr Amount", value=0.0, key=f"dra_{i}"),"remarks":c.text_input("Remarks", key=f"drr_{i}")})
        st.markdown("### Credit Lines")
        for i in range(int(credit_count)):
            a,b,c=st.columns([2,1,2]); credit_lines.append({"ledger":a.selectbox("Cr Ledger", ledgers, key=f"cr_{i}"),"amount":b.number_input("Cr Amount", value=0.0, key=f"cra_{i}"),"remarks":c.text_input("Remarks", key=f"crr_{i}")})
        total_dr=sum(x["amount"] for x in debit_lines); total_cr=sum(x["amount"] for x in credit_lines)
        cgst=sgst=igst=0
        if gst_type != "None": cgst,sgst,igst,_=gst_calc(total_dr,gst_rate,gst_type)
        narration=st.text_area("Narration")
        controls = entry_controls("accounting_ctrl")
        st.info(f"Total Dr: {money(total_dr)} | Total Cr: {money(total_cr)} | GST: {money(cgst+sgst+igst)}")
        if st.form_submit_button("Save Accounting Entry", use_container_width=True):
            if round(total_dr,2) != round(total_cr,2): st.error("Total Debit and Credit must be equal")
            else:
                header={"entry_date":entry_date,"voucher_type":voucher_type,"voucher_no":voucher_no,"debit_account":"Multiple","credit_account":"Multiple","amount":total_dr,"cgst":cgst,"sgst":sgst,"igst":igst,"total_amount":total_dr+cgst+sgst+igst,"narration":narration,"created_by":current_user()}
                header.update(controls)
                if "client_code" not in header: header["client_code"]=get_client_code()
                res=supabase.table("accounting_entries").insert(header).execute(); entry_id=(res.data or [{}])[0].get("id")
                for x in debit_lines: insert_row("accounting_entry_lines", {"entry_id":entry_id,"dr_cr":"Dr","ledger_name":x["ledger"],"amount":x["amount"],"remarks":x["remarks"]})
                for x in credit_lines: insert_row("accounting_entry_lines", {"entry_id":entry_id,"dr_cr":"Cr","ledger_name":x["ledger"],"amount":x["amount"],"remarks":x["remarks"]})
                st.success("Accounting entry saved"); st.rerun()
    show_table_with_edit_delete("accounting_entries", load_table("accounting_entries",500), "Accounting Entry Register")
    show_table_with_edit_delete("accounting_entry_lines", load_table("accounting_entry_lines",500), "Accounting Entry Lines")

# Reports and import
def import_center():
    show_header("Excel / Google Sheet Import", "section-rep")
    module = st.selectbox("Module", ["employees","ledgers","stock_ledgers","sales","purchase","expenses","appointments"])
    uploaded = st.file_uploader("Upload Excel / CSV", type=["xlsx","csv"])
    if uploaded and st.button("Import Data", use_container_width=True):
        df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        success=0
        for _,r in df.iterrows():
            row = {k: (None if pd.isna(v) else v) for k,v in r.to_dict().items()}
            try: insert_row(module,row); success += 1
            except Exception: pass
        insert_row("import_logs", {"import_type":"Excel/CSV","module_name":module,"total_rows":len(df),"success_rows":success,"failed_rows":len(df)-success,"remarks":"Uploaded file import","created_by":current_user()})
        st.success(f"Imported {success} rows")
    st.subheader("Google Sheet Import")
    st.info("Paste public CSV export link of Google Sheet. Format: File > Share public OR Publish to web as CSV.")
    url = st.text_input("Google Sheet CSV URL")
    if st.button("Import from Google Sheet", use_container_width=True) and url:
        try:
            df = pd.read_csv(url); success=0
            for _,r in df.iterrows(): insert_row(module, {k:(None if pd.isna(v) else v) for k,v in r.to_dict().items()}); success+=1
            insert_row("import_logs", {"import_type":"Google Sheet","module_name":module,"total_rows":len(df),"success_rows":success,"failed_rows":0,"remarks":url,"created_by":current_user()})
            st.success(f"Imported {success} rows from Google Sheet")
        except Exception as e: st.error(str(e))
    show_table_with_edit_delete("import_logs", load_table("import_logs",500), "Import Logs")


# ---------- FINANCIAL / STOCK REPORT HELPERS ----------
def num_value(value):
    try:
        if value in [None, ""]:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


# ---------- OFFLINE DESKTOP REPORT FORMAT PORTED TO ONLINE ----------
RBM_TB_HEADS_ONLINE = [
    ('Capital Account','Capital Account','Cr'),('Drawings','Capital Account','Dr'),
    ('Sales Account','Sales Accounts','Cr'),('Sales Return','Sales Accounts','Dr'),
    ('Purchase Account','Purchase Accounts','Dr'),('Purchase Return','Purchase Accounts','Cr'),
    ('Opening Stock','Direct Expenses','Dr'),('Closing Stock','Direct Incomes','Cr'),
    ('Cash-in-Hand','Current Assets','Dr'),('Bank Account','Bank Accounts','Dr'),
    ('Sundry Debtors','Sundry Debtors','Dr'),('Sundry Creditors','Sundry Creditors','Cr'),
    ('Furniture & Fixtures','Fixed Assets','Dr'),('Computer Equipment','Fixed Assets','Dr'),('Vehicle','Fixed Assets','Dr'),
    ('Direct Wages','Direct Expenses','Dr'),('Carriage Inward','Direct Expenses','Dr'),('Freight & Loading','Direct Expenses','Dr'),
    ('Salaries','Indirect Expenses','Dr'),('Rent','Indirect Expenses','Dr'),('Electricity Expenses','Indirect Expenses','Dr'),
    ('Telephone Expenses','Indirect Expenses','Dr'),('Printing & Stationery','Indirect Expenses','Dr'),('Advertisement Expenses','Indirect Expenses','Dr'),
    ('Travelling Expenses','Indirect Expenses','Dr'),('Audit Fees','Indirect Expenses','Dr'),('Legal & Professional Charges','Indirect Expenses','Dr'),
    ('Depreciation','Indirect Expenses','Dr'),('Bank Loan','Loans (Liability)','Cr'),('Interest on Loan','Indirect Expenses','Dr'),
    ('Commission Received','Indirect Incomes','Cr'),('Interest Received','Indirect Incomes','Cr'),
    ('GST Receivable','Current Assets','Dr'),('GST Payable','Current Liabilities','Cr'),('TDS Payable','Current Liabilities','Cr'),
    ('Outstanding Expenses','Current Liabilities','Cr'),('Advance & Deposits','Current Assets','Dr')
]

RBM_PL_STANDARD_ONLINE = [
    ('To Opening Stock','Opening Stock','By Sales','Sales Account'),('To Purchases','Purchase Account','By Closing Stock','Closing Stock'),
    ('To Direct Expenses','Direct Expenses','By Other Operating Income','Direct Incomes'),('To Gross Profit c/d','Gross Profit','', ''),
    ('Total','', 'Total',''),('Gross Profit Brought Down','','',''),
    ('To Salaries','Salaries','By Gross Profit b/d','Gross Profit'),('To Rent','Rent','By Commission Received','Commission Received'),
    ('To Electricity','Electricity Expenses','By Interest Received','Interest Received'),('To Office Expenses','Office Expenses','', ''),
    ('To Depreciation','Depreciation','', ''),('To Interest Paid','Interest on Loan','', ''),('To Net Profit transferred to Capital A/c','Net Profit','', ''),('Total','','Total','')
]
RBM_PL_OVERHEADS_ONLINE = [
    ('Manufacturing Overheads','Direct Wages','Operating Revenue','Sales Account'),('Power / Fuel / Factory Expenses','Electricity Expenses','Closing Stock','Closing Stock'),
    ('Administrative Overheads','Salaries','Other Income','Commission Received'),('Rent / Office / Legal','Rent','Interest Income','Interest Received'),
    ('Selling Overheads','Advertisement Expenses','',''),('Travelling / Marketing','Travelling Expenses','',''),('Financial Overheads','Interest on Loan','',''),('Net Profit / Loss','Net Profit','','')
]
RBM_BS_STANDARD_ONLINE = [
    ('Capital Account','Capital Account','Fixed Assets','Fixed Assets'),('Add: Net Profit','Net Profit','Less: Depreciation','Depreciation'),
    ('Less: Drawings','Drawings','Net Fixed Assets','Net Fixed Assets'),('Secured Loans','Secured Loans','Investments','Investments'),
    ('Unsecured Loans','Unsecured Loans','Closing Stock','Closing Stock'),('Sundry Creditors','Sundry Creditors','Sundry Debtors','Sundry Debtors'),
    ('Outstanding Expenses','Outstanding Expenses','Cash in Hand','Cash-in-Hand'),('Bills Payable','Bills Payable','Cash at Bank','Bank Accounts'),
    ('Duties & Taxes Payable','Duties & Taxes','Loans & Advances','Loans & Advances (Asset)'),('', '', 'Prepaid Expenses','Prepaid Expenses'),('Total','','Total','')
]
RBM_BS_OVERHEADS_ONLINE = [
    ('Capital & Reserves','Capital Account','Fixed Assets','Fixed Assets'),('Loans','Secured Loans','Inventory','Stock-in-Hand'),
    ('Current Liabilities','Current Liabilities','Receivables','Sundry Debtors'),('Statutory Liabilities','Duties & Taxes','Cash & Bank','Bank Accounts'),
    ('Creditors','Sundry Creditors','Loans & Advances','Loans & Advances (Asset)'),('Total','','Total','')
]

def rbm_amounts_from_online_tables():
    amounts={h:{'dr':0.0,'cr':0.0,'group':g} for h,g,_ in RBM_TB_HEADS_ONLINE}
    def add(name, group, dr=0.0, cr=0.0):
        name=str(name or '').strip()
        if not name: return
        amounts.setdefault(name, {'dr':0.0,'cr':0.0,'group':str(group or 'Other')})
        amounts[name]['dr'] += num_value(dr)
        amounts[name]['cr'] += num_value(cr)
        if not amounts[name].get('group') or amounts[name].get('group') == 'Other':
            amounts[name]['group'] = str(group or 'Other')
    try:
        ledgers=load_table('ledgers',50000)
        if not ledgers.empty:
            for _,r in ledgers.iterrows():
                nm=r.get('ledger_name',''); grp=r.get('ledger_group','Other'); bal=num_value(r.get('opening_balance',0)); bt=str(r.get('balance_type','Dr')).lower()
                add(nm, grp, cr=abs(bal) if 'cr' in bt else 0, dr=abs(bal) if 'cr' not in bt else 0)
    except Exception: pass
    try:
        entries=load_table('accounting_entries',50000)
        if not entries.empty:
            for _,e in entries.iterrows():
                amt=num_value(e.get('amount',0) or e.get('total_amount',0))
                add(e.get('debit_account',''), 'Other', dr=amt)
                add(e.get('credit_account',''), 'Other', cr=amt)
    except Exception: pass
    try:
        lines=load_table('accounting_entry_lines',50000)
        if not lines.empty:
            for _,l in lines.iterrows():
                amt=num_value(l.get('amount',0)); dc=str(l.get('dr_cr','')).lower()
                if dc.startswith('cr'): add(l.get('ledger_name',''), 'Other', cr=amt)
                else: add(l.get('ledger_name',''), 'Other', dr=amt)
    except Exception: pass
    for k, nm, grp, side in [('sales','Sales Account','Sales Accounts','cr'),('purchase','Purchase Account','Purchase Accounts','dr'),('expenses','Office Expenses','Indirect Expenses','dr')]:
        try:
            df=load_table(k,50000)
            if not df.empty:
                total=0.0
                for col in ['total_value','total_amount','amount','taxable_value']:
                    if col in df.columns: total=df[col].apply(num_value).sum(); break
                add(nm, grp, cr=total if side=='cr' else 0, dr=total if side=='dr' else 0)
        except Exception: pass
    try:
        stock_total=0.0
        for k in ['stock_fg','stock_raw','stock_wip','stock_ledgers']:
            df=load_table(k,50000)
            if not df.empty:
                for col in ['value','opening_value','closing_value']:
                    if col in df.columns:
                        stock_total += df[col].apply(num_value).sum(); break
        if stock_total: add('Closing Stock','Direct Incomes',cr=stock_total)
    except Exception: pass
    return amounts

def rbm_sum_by_names_online(amounts,*names):
    return sum(num_value(amounts.get(n,{}).get('dr',0))+num_value(amounts.get(n,{}).get('cr',0)) for n in names)

def rbm_sum_by_group_online(amounts,*groups):
    gs={str(g).lower() for g in groups}; total=0.0
    for rec in amounts.values():
        if str(rec.get('group','')).lower() in gs:
            total += num_value(rec.get('dr',0))+num_value(rec.get('cr',0))
    return total

def rbm_value_for_head_online(amounts, head):
    h=str(head or '')
    if not h: return 0.0
    if h == 'Gross Profit': return max(0.0, rbm_sum_by_group_online(amounts,'Sales Accounts','Direct Incomes') - rbm_sum_by_group_online(amounts,'Purchase Accounts','Direct Expenses'))
    if h == 'Net Profit':
        gp=max(0.0, rbm_sum_by_group_online(amounts,'Sales Accounts','Direct Incomes') - rbm_sum_by_group_online(amounts,'Purchase Accounts','Direct Expenses'))
        return max(0.0, gp + rbm_sum_by_group_online(amounts,'Indirect Incomes') - rbm_sum_by_group_online(amounts,'Indirect Expenses'))
    if h == 'Direct Expenses': return rbm_sum_by_group_online(amounts,'Direct Expenses')
    if h == 'Direct Incomes': return rbm_sum_by_group_online(amounts,'Direct Incomes')
    if h == 'Fixed Assets': return rbm_sum_by_group_online(amounts,'Fixed Assets')
    if h == 'Net Fixed Assets': return max(0.0, rbm_sum_by_group_online(amounts,'Fixed Assets') - rbm_value_for_head_online(amounts,'Depreciation'))
    if h == 'Secured Loans': return rbm_sum_by_group_online(amounts,'Secured Loans','Loans (Liability)')
    if h == 'Unsecured Loans': return rbm_sum_by_group_online(amounts,'Unsecured Loans')
    if h == 'Sundry Creditors': return rbm_sum_by_group_online(amounts,'Sundry Creditors')
    if h == 'Sundry Debtors': return rbm_sum_by_group_online(amounts,'Sundry Debtors')
    if h == 'Bank Accounts': return rbm_sum_by_group_online(amounts,'Bank Accounts','Current Assets')
    if h == 'Duties & Taxes': return rbm_sum_by_group_online(amounts,'Duties & Taxes','Current Liabilities')
    if h == 'Investments': return rbm_sum_by_group_online(amounts,'Investments')
    return rbm_sum_by_names_online(amounts,h)

def build_trial_balance_offline_style_df():
    amounts=rbm_amounts_from_online_tables(); rows=[]; heads={h for h,_,_ in RBM_TB_HEADS_ONLINE}
    for head,grp,typ in RBM_TB_HEADS_ONLINE:
        rec=amounts.get(head, {'dr':0.0,'cr':0.0,'group':grp})
        rows.append({'Group':grp,'Particulars':head,'Dr Amount':round(num_value(rec.get('dr',0)),2),'Cr Amount':round(num_value(rec.get('cr',0)),2),'Report Type':'Tally Group-Wise Trial Balance'})
    for name,rec in amounts.items():
        if name not in heads and (num_value(rec.get('dr',0)) or num_value(rec.get('cr',0))):
            rows.append({'Group':rec.get('group','Other'),'Particulars':name,'Dr Amount':round(num_value(rec.get('dr',0)),2),'Cr Amount':round(num_value(rec.get('cr',0)),2),'Report Type':'Actual Ledger'})
    rows.append({'Group':'TOTAL','Particulars':'TOTAL','Dr Amount':round(sum(r['Dr Amount'] for r in rows),2),'Cr Amount':round(sum(r['Cr Amount'] for r in rows),2),'Report Type':'Trial Balance Total'})
    return pd.DataFrame(rows)

def build_profit_loss_offline_style_df(fmt='Standard'):
    amounts=rbm_amounts_from_online_tables(); template=RBM_PL_OVERHEADS_ONLINE if fmt=='Overheads' else RBM_PL_STANDARD_ONLINE
    return pd.DataFrame([{'Debit Particulars':dp,'Debit Amount (₹)':round(rbm_value_for_head_online(amounts,dh),2),'Credit Particulars':cp,'Credit Amount (₹)':round(rbm_value_for_head_online(amounts,ch),2),'Format':fmt} for dp,dh,cp,ch in template])

def build_balance_sheet_offline_style_df(fmt='Standard'):
    amounts=rbm_amounts_from_online_tables(); template=RBM_BS_OVERHEADS_ONLINE if fmt=='Overheads' else RBM_BS_STANDARD_ONLINE
    return pd.DataFrame([{'Liabilities':lp,'Amount (₹)':round(rbm_value_for_head_online(amounts,lh),2),'Assets':ap,'Asset Amount (₹)':round(rbm_value_for_head_online(amounts,ah),2),'Format':fmt} for lp,lh,ap,ah in template])


def build_trial_balance_df():
    ledgers = load_table("ledgers", 50000)
    lines = load_table("accounting_entry_lines", 50000)

    if ledgers.empty:
        return pd.DataFrame(columns=["ledger_group", "ledger_name", "opening_dr", "opening_cr", "debit", "credit", "closing_dr", "closing_cr", "email", "contact_no"])

    for col in ["ledger_group", "ledger_name", "opening_balance", "balance_type", "email", "contact_no"]:
        if col not in ledgers.columns:
            ledgers[col] = ""

    if lines.empty:
        lines = pd.DataFrame(columns=["ledger_name", "dr_cr", "amount"])

    for col in ["ledger_name", "dr_cr", "amount"]:
        if col not in lines.columns:
            lines[col] = ""

    rows = []
    for _, row in ledgers.iterrows():
        ledger_name = str(row.get("ledger_name", ""))
        ledger_lines = lines[lines["ledger_name"].astype(str) == ledger_name].copy()
        dr_amount = ledger_lines[ledger_lines["dr_cr"].astype(str).str.lower().str.startswith("dr")]["amount"].apply(num_value).sum() if not ledger_lines.empty else 0.0
        cr_amount = ledger_lines[ledger_lines["dr_cr"].astype(str).str.lower().str.startswith("cr")]["amount"].apply(num_value).sum() if not ledger_lines.empty else 0.0

        opening = num_value(row.get("opening_balance", 0))
        balance_type = str(row.get("balance_type", "Dr"))
        opening_dr = opening if balance_type == "Dr" else 0.0
        opening_cr = opening if balance_type == "Cr" else 0.0

        closing_signed = opening_dr + dr_amount - opening_cr - cr_amount
        closing_dr = closing_signed if closing_signed >= 0 else 0.0
        closing_cr = abs(closing_signed) if closing_signed < 0 else 0.0

        rows.append({
            "ledger_group": row.get("ledger_group", ""),
            "ledger_name": ledger_name,
            "opening_dr": round(opening_dr, 2),
            "opening_cr": round(opening_cr, 2),
            "debit": round(dr_amount, 2),
            "credit": round(cr_amount, 2),
            "closing_dr": round(closing_dr, 2),
            "closing_cr": round(closing_cr, 2),
            "email": row.get("email", ""),
            "contact_no": row.get("contact_no", ""),
        })

    return pd.DataFrame(rows)


def build_profit_loss_df(tb):
    if tb.empty:
        return pd.DataFrame(columns=["particulars", "amount"])

    sales_groups = ["Sales Accounts", "Service Income", "Income", "Indirect Income"]
    purchase_groups = ["Purchase Accounts"]
    expense_groups = ["Direct Expenses", "Indirect Expenses", "Expense Account", "Expenses"]

    sales = tb[tb["ledger_group"].astype(str).isin(sales_groups)]["closing_cr"].sum() - tb[tb["ledger_group"].astype(str).isin(sales_groups)]["closing_dr"].sum()
    purchases = tb[tb["ledger_group"].astype(str).isin(purchase_groups)]["closing_dr"].sum() - tb[tb["ledger_group"].astype(str).isin(purchase_groups)]["closing_cr"].sum()
    expenses = tb[tb["ledger_group"].astype(str).isin(expense_groups)]["closing_dr"].sum() - tb[tb["ledger_group"].astype(str).isin(expense_groups)]["closing_cr"].sum()
    gross_profit = sales - purchases
    net_profit = gross_profit - expenses

    return pd.DataFrame([
        {"particulars": "Sales / Service Income", "amount": round(sales, 2)},
        {"particulars": "Less: Purchase", "amount": round(purchases, 2)},
        {"particulars": "Gross Profit / Loss", "amount": round(gross_profit, 2)},
        {"particulars": "Less: Expenses", "amount": round(expenses, 2)},
        {"particulars": "Net Profit / Loss", "amount": round(net_profit, 2)},
    ])


def build_balance_sheet_df(tb):
    if tb.empty:
        return pd.DataFrame(columns=["side", "group", "amount"])

    asset_groups = ["Fixed Assets", "Bank Accounts", "Cash-in-Hand", "Loans & Advances", "Sundry Debtors", "Duties & Taxes"]
    liability_groups = ["Capital Account", "Sundry Creditors", "Loans", "Secured Loans", "Unsecured Loans"]

    rows = []
    for group in sorted(tb["ledger_group"].dropna().astype(str).unique().tolist()):
        group_df = tb[tb["ledger_group"].astype(str) == group]
        debit_bal = group_df["closing_dr"].sum()
        credit_bal = group_df["closing_cr"].sum()
        net = debit_bal - credit_bal

        if group in asset_groups or net >= 0:
            rows.append({"side": "Assets", "group": group, "amount": round(abs(net), 2)})
        elif group in liability_groups or net < 0:
            rows.append({"side": "Liabilities", "group": group, "amount": round(abs(net), 2)})

    return pd.DataFrame(rows)


def build_stock_summary_df():
    stock = load_table("stock_ledgers", 50000)
    purchase_df = load_table("purchase", 50000)
    raw_df = load_table("stock_raw", 50000)
    fg_df = load_table("stock_fg", 50000)
    wip_df = load_table("stock_wip", 50000)
    vouchers = load_table("stock_vouchers", 50000)

    if stock.empty:
        return pd.DataFrame(columns=["Stock Group", "Item Name", "Item Code", "Unit", "Opening Balance", "Purchase", "Consumed", "Closing Balance"])

    rows = []
    for _, item in stock.iterrows():
        item_name = str(item.get("item_name", ""))
        stock_group = str(item.get("stock_group", ""))
        opening = num_value(item.get("opening_qty", 0))

        purchase_qty = 0.0
        if not purchase_df.empty and "item_name" in purchase_df.columns and "qty" in purchase_df.columns:
            purchase_qty += purchase_df[purchase_df["item_name"].astype(str) == item_name]["qty"].apply(num_value).sum()
        if not raw_df.empty and "item_name" in raw_df.columns and "inward_qty" in raw_df.columns:
            purchase_qty += raw_df[raw_df["item_name"].astype(str) == item_name]["inward_qty"].apply(num_value).sum()
        if not fg_df.empty and "item_name" in fg_df.columns and "production_qty" in fg_df.columns:
            purchase_qty += fg_df[fg_df["item_name"].astype(str) == item_name]["production_qty"].apply(num_value).sum()
        if not wip_df.empty and "item_name" in wip_df.columns and "input_qty" in wip_df.columns:
            purchase_qty += wip_df[wip_df["item_name"].astype(str) == item_name]["input_qty"].apply(num_value).sum()
        if not vouchers.empty and "item_name" in vouchers.columns and "voucher_type" in vouchers.columns and "qty" in vouchers.columns:
            receipt_mask = vouchers["voucher_type"].astype(str).str.lower().isin(["receipt", "inward", "purchase", "production"])
            purchase_qty += vouchers[(vouchers["item_name"].astype(str) == item_name) & receipt_mask]["qty"].apply(num_value).sum()

        consumed = 0.0
        if not raw_df.empty and "item_name" in raw_df.columns and "outward_qty" in raw_df.columns:
            consumed += raw_df[raw_df["item_name"].astype(str) == item_name]["outward_qty"].apply(num_value).sum()
        if not fg_df.empty and "item_name" in fg_df.columns and "sales_qty" in fg_df.columns:
            consumed += fg_df[fg_df["item_name"].astype(str) == item_name]["sales_qty"].apply(num_value).sum()
        if not wip_df.empty and "item_name" in wip_df.columns and "output_qty" in wip_df.columns:
            consumed += wip_df[wip_df["item_name"].astype(str) == item_name]["output_qty"].apply(num_value).sum()
        if not vouchers.empty and "item_name" in vouchers.columns and "voucher_type" in vouchers.columns and "qty" in vouchers.columns:
            issue_mask = vouchers["voucher_type"].astype(str).str.lower().isin(["issue", "outward", "sales", "consumed", "consumption"])
            consumed += vouchers[(vouchers["item_name"].astype(str) == item_name) & issue_mask]["qty"].apply(num_value).sum()

        closing = opening + purchase_qty - consumed
        rows.append({
            "Stock Group": stock_group,
            "Item Name": item_name,
            "Item Code": item.get("item_code", ""),
            "Unit": item.get("unit", ""),
            "Opening Balance": round(opening, 2),
            "Purchase": round(purchase_qty, 2),
            "Consumed": round(consumed, 2),
            "Closing Balance": round(closing, 2),
        })

    return pd.DataFrame(rows)



# ---------- ERP SETUP / CONTROL MODULES ----------
def company_profile():
    simple_module_form("company_profiles", "Company Profile / Statutory Details", [
        ("company_name","Company Name","text"), ("legal_name","Legal Name","text"),
        ("gst_no","GST No","text"), ("pan_no","PAN No","text"), ("tan_no","TAN No","text"),
        ("address","Address","text"), ("state","State","text"), ("email","Email","text"),
        ("mobile","Mobile","text"), ("financial_year_start","Financial Year Start","date"),
        ("books_start_date","Books Start Date","date"), ("status","Status",["Active","Inactive"])
    ], "section-master")

def financial_year_master():
    simple_module_form("financial_years", "Financial Year Master / Period Lock", [
        ("fy_name","Financial Year Name","text"), ("start_date","Start Date","date"),
        ("end_date","End Date","date"), ("status","Status",["Open","Closed"]),
        ("lock_status","Lock Status",["Unlocked","Locked"])
    ], "section-master")

def cost_center_master():
    simple_module_form("cost_centers", "Cost Center / Department Master", [
        ("cost_center_name","Cost Center Name","text"), ("department","Department","text"),
        ("location","Location","text"), ("status","Status",["Active","Inactive"])
    ], "section-master")

def document_series_master():
    simple_module_form("document_series", "Document Numbering Series", [
        ("module_name","Module Name",["Sales","Purchase","Expense","Service","Stock","Accounting","Appointment"]),
        ("prefix","Prefix","text"), ("next_no","Next No","number"), ("suffix","Suffix","text"),
        ("status","Status",["Active","Inactive"])
    ], "section-master")

def gst_settings_master():
    simple_module_form("gst_settings", "GST Settings / Tax Registration", [
        ("gst_no","GST No","text"), ("legal_name","Legal Name","text"), ("state","State","text"),
        ("registration_type","Registration Type",["Regular","Composition","Unregistered","SEZ","Export"]),
        ("default_tax_type","Default Tax Type",["CGST+SGST","IGST","None"]),
        ("status","Status",["Active","Inactive"])
    ], "section-master")

def audit_log_report():
    show_header("Audit Log / System Control", "section-rep")
    st.info("This register is reserved for tracking important user actions, approvals, edits and deletions.")
    show_table_with_edit_delete("audit_logs", load_table("audit_logs", 5000), "Audit Log")

# ---------- CALCULATION BOOK ----------
def _blank_calc_df(rows=20, cols=8):
    letters = list(string.ascii_uppercase[:int(cols)])
    return pd.DataFrame([[0.0 for _ in letters] for _ in range(int(rows))], columns=letters)

def _safe_apply_formula(df, target_col, formula):
    data = df.copy()
    for c in data.columns:
        data[c] = pd.to_numeric(data[c], errors="coerce").fillna(0)
    allowed = {c: data[c] for c in data.columns}
    try:
        data[target_col] = pd.eval(formula, local_dict=allowed, engine="python")
        return data, ""
    except Exception as e:
        return df, str(e)

def calculation_book():
    show_header("Calculation Book - Excel Like Working Sheet", "section-rep")
    st.caption("Use this as an internal working sheet. You can type values, apply simple column formulas like A+B, A*B, A+B-C, save the book and download Excel.")

    old_books = raw_table("calculation_books", 1000)
    book_options = ["New Calculation Book"]
    if not old_books.empty and "book_name" in old_books.columns:
        book_options += old_books["book_name"].dropna().astype(str).unique().tolist()

    c0, c1, c2, c3 = st.columns([2, 2, 1, 1])
    selected_book = c0.selectbox("Open Existing Book", book_options)
    book_name = c1.text_input("Book Name", value="Working Calculation" if selected_book == "New Calculation Book" else selected_book)
    sheet_name = c2.text_input("Sheet", value="Sheet1")
    rows = c3.number_input("Rows", min_value=5, max_value=200, value=20, step=5)
    cols = st.slider("Columns", min_value=3, max_value=20, value=8)

    initial_df = _blank_calc_df(rows, cols)
    if selected_book != "New Calculation Book" and not old_books.empty:
        row = old_books[old_books["book_name"].astype(str) == selected_book].iloc[0]
        try:
            loaded = pd.DataFrame(json.loads(row.get("grid_json", "[]")))
            if not loaded.empty:
                initial_df = loaded
        except Exception:
            pass

    edited_df = st.data_editor(initial_df, use_container_width=True, num_rows="dynamic", key="calc_grid_editor")

    st.subheader("Formula Bar")
    f1, f2, f3 = st.columns([1, 3, 1])
    target_col = f1.selectbox("Target Column", edited_df.columns.tolist())
    formula = f2.text_input("Formula", placeholder="Example: A+B-C or A*B")
    if f3.button("Apply Formula", use_container_width=True):
        new_df, err = _safe_apply_formula(edited_df, target_col, formula)
        if err:
            st.error(f"Formula error: {err}")
        else:
            st.session_state["calc_result_df"] = new_df
            st.success("Formula applied. See result below.")

    final_df = st.session_state.get("calc_result_df", edited_df)
    if "calc_result_df" in st.session_state:
        st.dataframe(final_df, use_container_width=True)

    st.subheader("Column Totals")
    numeric_df = final_df.copy()
    for c in numeric_df.columns:
        numeric_df[c] = pd.to_numeric(numeric_df[c], errors="coerce").fillna(0)
    total_df = pd.DataFrame({"Column": numeric_df.columns, "Total": [numeric_df[c].sum() for c in numeric_df.columns]})
    st.dataframe(total_df, use_container_width=True)

    c4, c5 = st.columns(2)
    if c4.button("Save Calculation Book", use_container_width=True):
        insert_row("calculation_books", {
            "book_name": book_name,
            "sheet_name": sheet_name,
            "grid_json": final_df.to_json(orient="records"),
            "remarks": "Saved from Calculation Book",
            "created_by": current_user()
        })
        st.success("Calculation book saved.")
        st.rerun()
    with c5:
        st.download_button("Download Calculation Excel", to_excel_bytes(final_df), f"{book_name}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.divider()
    show_table_with_edit_delete("calculation_books", load_table("calculation_books", 100), "Saved Calculation Books")


def _quote_role():
    return st.session_state.get("role") in ["Quotation User", "Vendor", "Supplier", "Business User"]


def _quotation_file_download(row):
    try:
        data = str(row.get("quotation_file_data", "") or "")
        name = str(row.get("quotation_file_name", "quotation_file")) or "quotation_file"
        if data.strip():
            st.download_button(
                "Download Uploaded Quotation",
                data=base64.b64decode(data),
                file_name=name,
                mime="application/octet-stream",
                use_container_width=True,
                key=f"download_quote_file_{row.get('id','')}"
            )
    except Exception:
        st.warning("File preview/download not available for this quotation.")




def _get_business_user_details(business_username):
    """Return business/vendor details from quotation_business_users."""
    try:
        q = supabase.table(TABLES["quotation_business_users"]).select("*").eq("username", str(business_username))
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        df = safe_df(q.limit(1).execute().data)
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    except Exception:
        return {}

def _get_requirement_details(requirement_id):
    try:
        q = supabase.table(TABLES["quotation_requirements"]).select("*").eq("id", int(requirement_id))
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        df = safe_df(q.limit(1).execute().data)
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    except Exception:
        return {}

def _safe_secret(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

def send_negotiation_email(to_email, subject, body):
    """Send email if SMTP secrets are configured. If not configured, return mailto link."""
    to_email = str(to_email or "").strip()
    if not to_email:
        return False, "Vendor email ID is not available. Please add vendor Email ID in Business Users / User Management.", ""

    smtp_host = _safe_secret("SMTP_HOST", "")
    smtp_port = int(_safe_secret("SMTP_PORT", 587) or 587)
    smtp_user = _safe_secret("SMTP_USER", "")
    smtp_password = _safe_secret("SMTP_PASSWORD", "")
    smtp_from = _safe_secret("SMTP_FROM", smtp_user)

    mailto = f"mailto:{quote(to_email)}?subject={quote(subject)}&body={quote(body)}"

    if not smtp_host or not smtp_user or not smtp_password or not smtp_from:
        return False, "SMTP not configured. Use the mail link below to send email from your email app.", mailto

    try:
        msg = EmailMessage()
        msg["From"] = smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return True, "Email sent successfully.", ""
    except Exception as e:
        return False, f"Email sending failed: {e}. Use the mail link below.", mailto

def _request_negotiation_for_quotation(qrow, deadline, message, requested_amount=None):
    """Create negotiation request, update quotation status, and send/email-draft to vendor."""
    try:
        qid = int(qrow.get("id"))
        business_username = str(qrow.get("business_username", ""))
        business_name = str(qrow.get("business_name", ""))
        vendor = _get_business_user_details(business_username)
        vendor_email = str(vendor.get("email", "") or "")
        req_id = qrow.get("requirement_id", None)
        req = _get_requirement_details(req_id) if req_id not in ["", None] else {}

        subject = f"Negotiation Requested for Quotation {qrow.get('quotation_no','')}"
        body = f"""Dear {business_name or business_username},

We have reviewed your quotation and would like to negotiate.

Requirement No: {qrow.get('requirement_no','')}
Requirement Title: {req.get('requirement_title','')}
Quotation No: {qrow.get('quotation_no','')}
Original Amount: {qrow.get('total_amount', qrow.get('amount',''))}

Negotiation Deadline: {deadline}

Message from Client:
{message}

Please login to RBM ERP Quotation Portal and submit your revised quotation before the deadline.

ERP URL:
{_safe_secret('ERP_PUBLIC_URL', 'https://rbm-office-saas.streamlit.app/')}

Regards,
{st.session_state.get('full_name', 'RBM ERP Admin')}
RBM ERP SaaS
"""

        neg_row = {
            "quotation_id": qid,
            "requirement_id": qrow.get("requirement_id"),
            "requirement_no": str(qrow.get("requirement_no", "")),
            "business_username": business_username,
            "business_name": business_name,
            "vendor_email": vendor_email,
            "original_amount": float(qrow.get("total_amount", qrow.get("amount", 0)) or 0),
            "requested_amount": float(requested_amount or 0),
            "negotiation_message": str(message or ""),
            "deadline": str(deadline),
            "status": "Negotiation Requested",
            "client_requested_by": current_user(),
            "client_requested_at": india_now().isoformat(),
        }
        insert_row("quotation_negotiations", neg_row)

        try:
            supabase.table(TABLES["quotations"]).update({
                "quotation_status": "Negotiation Requested",
                "negotiation_status": "Negotiation Requested",
                "negotiation_deadline": str(deadline),
                "negotiation_message": str(message or "")
            }).eq("id", qid).execute()
        except Exception:
            pass

        sent, msg, mailto = send_negotiation_email(vendor_email, subject, body)
        write_audit_log("Quotation Negotiation", "REQUEST", qid, f"Negotiation requested. Email status: {msg}")
        return sent, msg, mailto, body
    except Exception as e:
        return False, f"Negotiation request failed: {e}", "", ""


def quotation_module():
    show_header("Quotation Portal", "section-acc")

    role = st.session_state.get("role", "")
    username = current_user()

    if role in ["Admin", "Super Admin"]:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Our Requirements",
            "Business Users",
            "Requirement Access",
            "Received Quotations",
            "Negotiation Center",
        ])

        with tab1:
            st.subheader("Create Requirement / RFQ")
            with st.form("quotation_requirement_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                requirement_no = c1.text_input("Requirement No", value=f"REQ-{india_now().strftime('%Y%m%d%H%M')}")
                requirement_date = c2.date_input("Requirement Date", value=india_now().date(), format="DD-MM-YYYY")
                expected_date = c3.date_input("Expected Quote Date", value=india_now().date(), format="DD-MM-YYYY")
                requirement_title = st.text_input("Requirement Title")
                item_name = c1.text_input("Item / Service Name")
                qty = c2.number_input("Qty", min_value=0.0, value=1.0, step=1.0)
                unit = c3.text_input("Unit", value="Nos")
                requirement_details = st.text_area("Requirement Details / Technical Specification")
                status = c1.selectbox("Status", ["Open", "Closed", "Cancelled"])
                remarks = st.text_input("Remarks")
                if st.form_submit_button("Save Requirement", use_container_width=True):
                    if not requirement_no.strip() or not requirement_title.strip():
                        st.error("Requirement No and Title are required.")
                    else:
                        insert_row("quotation_requirements", {
                            "requirement_no": requirement_no.strip(),
                            "requirement_date": str(requirement_date),
                            "requirement_title": requirement_title.strip(),
                            "requirement_details": requirement_details,
                            "item_name": item_name,
                            "qty": qty,
                            "unit": unit,
                            "expected_date": str(expected_date),
                            "status": status,
                            "remarks": remarks,
                            "created_by": username,
                        })
                        st.success("Requirement saved.")
                        st.rerun()
            show_table_with_edit_delete("quotation_requirements", load_table("quotation_requirements", 1000), "Requirement List")

        with tab2:
            st.subheader("Create Business Login for Quotation Portal")
            with st.form("quotation_business_user_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                business_name = c1.text_input("Business Name")
                contact_person = c2.text_input("Contact Person")
                mobile = c1.text_input("Mobile")
                email = c2.text_input("Email")
                business_username = c1.text_input("Username")
                business_password = c2.text_input("Password", type="password")
                status = c1.selectbox("Status", ["Active", "Inactive"])
                if st.form_submit_button("Create Business User", use_container_width=True):
                    if not business_name.strip() or not business_username.strip() or not business_password.strip():
                        st.error("Business name, username and password are required.")
                    else:
                        insert_row("quotation_business_users", {
                            "business_name": business_name.strip(),
                            "contact_person": contact_person,
                            "mobile": mobile,
                            "email": email,
                            "username": business_username.strip(),
                            "password": business_password,
                            "status": status,
                            "created_by": username,
                        })
                        # Also create normal app login with restricted quotation role.
                        insert_row("users", {
                            "client_code": get_client_code(),
                            "username": business_username.strip(),
                            "password": business_password,
                            "role": "Quotation User",
                            "full_name": business_name.strip(),
                            "email": email.strip(),
                            "mobile": mobile.strip(),
                            "status": status,
                        })
                        st.success("Business quotation login created.")
                        st.rerun()
            show_table_with_edit_delete("quotation_business_users", load_table("quotation_business_users", 1000), "Business User List")

        with tab3:
            st.subheader("Assign Which Requirement a Business Can See")
            req_df = load_table("quotation_requirements", 5000)
            bus_df = load_table("quotation_business_users", 5000)
            if req_df.empty or bus_df.empty:
                st.info("Create at least one requirement and one business user first.")
            else:
                req_df = req_df[req_df["status"].astype(str).isin(["Open", "Active", ""])] if "status" in req_df.columns else req_df
                req_options = {
                    f"{r.get('requirement_no','')} | {r.get('requirement_title','')}": int(r.get("id"))
                    for _, r in req_df.iterrows()
                }
                bus_options = {
                    f"{r.get('business_name','')} | {r.get('username','')}": str(r.get("username"))
                    for _, r in bus_df.iterrows()
                }
                with st.form("quotation_access_form", clear_on_submit=True):
                    selected_req = st.selectbox("Requirement", list(req_options.keys()))
                    selected_businesses = st.multiselect("Business Users allowed to see this requirement", list(bus_options.keys()))
                    if st.form_submit_button("Save Access", use_container_width=True):
                        req_id = req_options[selected_req]
                        req_row = req_df[req_df["id"] == req_id].iloc[0]
                        for b in selected_businesses:
                            bun = bus_options[b]
                            b_row = bus_df[bus_df["username"].astype(str) == bun].iloc[0]
                            insert_row("quotation_access", {
                                "requirement_id": req_id,
                                "requirement_no": str(req_row.get("requirement_no", "")),
                                "business_username": bun,
                                "business_name": str(b_row.get("business_name", "")),
                                "status": "Active",
                                "created_by": username,
                            })
                        st.success("Access saved.")
                        st.rerun()
            show_table_with_edit_delete("quotation_access", load_table("quotation_access", 1000), "Requirement Access List")

        with tab4:
            st.subheader("All Quotations Received")
            qdf = load_table("quotations", 5000)
            st.dataframe(qdf, use_container_width=True)
            if not qdf.empty:
                selected = st.selectbox("Select quotation ID to download file", qdf["id"].tolist(), key="quote_admin_download_id")
                raw = safe_df(supabase.table("quotations").select("*").eq("id", int(selected)).limit(1).execute().data)
                if not raw.empty:
                    _quotation_file_download(raw.iloc[0])
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("Download Quotation Register Excel", to_excel_bytes(qdf), "quotation_register.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="quote_reg_xlsx")
            with c2:
                st.download_button("Download Quotation Register CSV", qdf.to_csv(index=False).encode("utf-8"), "quotation_register.csv", "text/csv", use_container_width=True, key="quote_reg_csv")

        with tab5:
            st.subheader("Negotiation Center")
            st.info("Select a received quotation, set negotiation deadline, write message, and inform vendor by email/mail draft.")
            qdf = load_table("quotations", 5000)
            if qdf.empty:
                st.info("No quotation received yet.")
            else:
                qdf_show = qdf.copy()
                st.dataframe(qdf_show, use_container_width=True)
                quote_ids = qdf_show["id"].dropna().astype(int).tolist() if "id" in qdf_show.columns else []
                if quote_ids:
                    selected_qid = st.selectbox("Select Quotation ID for Negotiation", quote_ids, key="neg_select_quote")
                    raw = safe_df(supabase.table(TABLES["quotations"]).select("*").eq("id", int(selected_qid)).limit(1).execute().data)
                    if not raw.empty:
                        qrow = raw.iloc[0].to_dict()
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Quotation No", str(qrow.get("quotation_no", "")))
                        c2.metric("Vendor", str(qrow.get("business_name", "")))
                        c3.metric("Total Amount", money(qrow.get("total_amount", qrow.get("amount", 0))))
                        deadline_date = st.date_input("Negotiation Deadline Date", value=india_now().date(), format="DD-MM-YYYY", key="neg_deadline_date")
                        deadline_time = st.time_input("Negotiation Deadline Time", value=india_now().time().replace(second=0, microsecond=0), key="neg_deadline_time")
                        requested_amount = st.number_input("Expected / Target Amount (optional)", min_value=0.0, value=0.0, step=100.0, key="neg_target_amount")
                        message = st.text_area("Message to Vendor", value="Please review your quotation and submit your best revised offer within the given time frame.", key="neg_message")
                        if st.button("Request Negotiation & Inform Vendor", use_container_width=True, key="request_negotiation_btn"):
                            deadline = f"{deadline_date} {deadline_time}"
                            sent, msg, mailto, body = _request_negotiation_for_quotation(qrow, deadline, message, requested_amount)
                            if sent:
                                st.success(msg)
                            else:
                                st.warning(msg)
                                if mailto:
                                    st.markdown(f"[Open Email Draft to Vendor]({mailto})")
                                    st.text_area("Email Draft Body", value=body, height=240)
                            st.rerun()

            st.divider()
            st.subheader("Negotiation History")
            ndf = load_table("quotation_negotiations", 5000)
            st.dataframe(ndf, use_container_width=True)

            if not ndf.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("Download Negotiation Excel", to_excel_bytes(ndf), "quotation_negotiations.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="neg_xlsx")
                with c2:
                    st.download_button("Download Negotiation CSV", ndf.to_csv(index=False).encode("utf-8"), "quotation_negotiations.csv", "text/csv", use_container_width=True, key="neg_csv")

                st.divider()
                st.subheader("Edit / Delete / Re-Send Negotiation")
                neg_ids = ndf["id"].dropna().astype(int).tolist() if "id" in ndf.columns else []
                if neg_ids:
                    selected_neg_id = st.selectbox("Select Negotiation ID", neg_ids, key="admin_neg_edit_id")
                    neg_match = ndf[ndf["id"].astype(str) == str(selected_neg_id)]
                    if not neg_match.empty:
                        neg_row = neg_match.iloc[0].to_dict()

                        with st.expander(f"Edit Negotiation - ID {selected_neg_id}", expanded=False):
                            c1, c2, c3 = st.columns(3)
                            vendor_email_edit = c1.text_input("Vendor Email", value=str(neg_row.get("vendor_email", "") or ""), key=f"neg_email_{selected_neg_id}")
                            deadline_edit = c2.text_input("Deadline", value=str(neg_row.get("deadline", "") or ""), key=f"neg_deadline_{selected_neg_id}")
                            statuses = ["Negotiation Requested", "Open", "Pending", "Revised Submitted", "Accepted", "Rejected", "Closed", "Converted To PO"]
                            current_status = str(neg_row.get("status", "Negotiation Requested") or "Negotiation Requested")
                            status_index = statuses.index(current_status) if current_status in statuses else 0
                            status_edit = c3.selectbox("Status", statuses, index=status_index, key=f"neg_status_{selected_neg_id}")

                            c4, c5, c6 = st.columns(3)
                            requested_amount_edit = c4.number_input("Target / Requested Amount", value=float(neg_row.get("requested_amount", 0) or 0), step=100.0, key=f"neg_req_amt_{selected_neg_id}")
                            revised_total_edit = c5.number_input("Revised Total Amount", value=float(neg_row.get("revised_total_amount", 0) or 0), step=100.0, key=f"neg_rev_total_{selected_neg_id}")
                            vendor_response_edit = c6.text_input("Vendor Response", value=str(neg_row.get("vendor_response", "") or ""), key=f"neg_vendor_resp_{selected_neg_id}")
                            message_edit = st.text_area("Negotiation Message", value=str(neg_row.get("negotiation_message", "") or ""), key=f"neg_msg_{selected_neg_id}")

                            b1, b2, b3, b4 = st.columns(4)

                            with b1:
                                if st.button("Update Negotiation", use_container_width=True, key=f"neg_update_{selected_neg_id}"):
                                    update_row("quotation_negotiations", selected_neg_id, {
                                        "vendor_email": vendor_email_edit,
                                        "deadline": deadline_edit,
                                        "status": status_edit,
                                        "requested_amount": requested_amount_edit,
                                        "revised_total_amount": revised_total_edit,
                                        "vendor_response": vendor_response_edit,
                                        "negotiation_message": message_edit,
                                    })
                                    try:
                                        qid = int(neg_row.get("quotation_id", 0) or 0)
                                        if qid:
                                            supabase.table(TABLES["quotations"]).update({
                                                "negotiation_status": status_edit,
                                                "negotiation_deadline": deadline_edit,
                                                "negotiation_message": message_edit,
                                                "quotation_status": status_edit,
                                            }).eq("id", qid).execute()
                                    except Exception:
                                        pass
                                    st.success("Negotiation updated.")
                                    st.rerun()

                            with b2:
                                if st.button("Delete Negotiation", use_container_width=True, key=f"neg_delete_{selected_neg_id}"):
                                    delete_row("quotation_negotiations", selected_neg_id)
                                    st.success("Negotiation deleted.")
                                    st.rerun()

                            with b3:
                                if st.button("Re-Send Email", use_container_width=True, key=f"neg_resend_{selected_neg_id}"):
                                    qid = int(neg_row.get("quotation_id", 0) or 0)
                                    qraw = safe_df(supabase.table(TABLES["quotations"]).select("*").eq("id", qid).limit(1).execute().data) if qid else pd.DataFrame()
                                    if qraw.empty:
                                        st.error("Linked quotation not found.")
                                    else:
                                        qrow = qraw.iloc[0].to_dict()
                                        qrow["business_name"] = neg_row.get("business_name", qrow.get("business_name", ""))
                                        qrow["business_username"] = neg_row.get("business_username", qrow.get("business_username", ""))
                                        sent, msg, mailto, body = _request_negotiation_for_quotation(qrow, deadline_edit, message_edit, requested_amount_edit)
                                        if sent:
                                            st.success("Negotiation email re-sent successfully.")
                                        else:
                                            st.warning(msg)
                                            if mailto:
                                                st.markdown(f"[Open Email Draft to Vendor]({mailto})")
                                                st.text_area("Email Draft Body", value=body, height=220, key=f"neg_resend_body_{selected_neg_id}")

                            with b4:
                                if st.button("Convert To PO", use_container_width=True, key=f"neg_po_{selected_neg_id}"):
                                    update_row("quotation_negotiations", selected_neg_id, {"status": "Converted To PO"})
                                    try:
                                        qid = int(neg_row.get("quotation_id", 0) or 0)
                                        if qid:
                                            supabase.table(TABLES["quotations"]).update({
                                                "quotation_status": "Converted To PO",
                                                "negotiation_status": "Converted To PO",
                                            }).eq("id", qid).execute()
                                    except Exception:
                                        pass
                                    st.success("Marked as Converted To PO.")
                                    st.rerun()


    elif _quote_role():
        st.info("You can see only requirements assigned to your business username and only your own quotations.")
        access_df = load_table("quotation_access", 5000)
        access_df = access_df[access_df["business_username"].astype(str) == username] if not access_df.empty and "business_username" in access_df.columns else pd.DataFrame()
        allowed_ids = access_df["requirement_id"].dropna().astype(int).tolist() if not access_df.empty and "requirement_id" in access_df.columns else []

        tab1, tab2, tab3 = st.tabs(["Assigned Requirements", "My Submitted Quotations", "Negotiation Requests"])
        with tab1:
            req_df = load_table("quotation_requirements", 5000)
            if allowed_ids and not req_df.empty:
                req_df = req_df[req_df["id"].astype(int).isin(allowed_ids)]
            else:
                req_df = pd.DataFrame()
            st.dataframe(req_df, use_container_width=True)
            if req_df.empty:
                st.info("No requirement assigned to you.")
            else:
                with st.form("submit_quote_form", clear_on_submit=True):
                    req_labels = {
                        f"{r.get('requirement_no','')} | {r.get('requirement_title','')}": int(r.get("id"))
                        for _, r in req_df.iterrows()
                    }
                    selected_req = st.selectbox("Select Requirement", list(req_labels.keys()))
                    req_id = req_labels[selected_req]
                    req_row = req_df[req_df["id"] == req_id].iloc[0]
                    c1, c2, c3 = st.columns(3)
                    quotation_no = c1.text_input("Quotation No")
                    quotation_date = c2.date_input("Quotation Date", value=india_now().date(), format="DD-MM-YYYY")
                    valid_till = c3.date_input("Valid Till", value=india_now().date(), format="DD-MM-YYYY")
                    amount = c1.number_input("Amount", min_value=0.0, value=0.0, step=100.0)
                    gst_amount = c2.number_input("GST Amount", min_value=0.0, value=0.0, step=100.0)
                    total_amount = c3.number_input("Total Amount", min_value=0.0, value=float(amount + gst_amount), step=100.0)
                    quotation_file = st.file_uploader("Upload Quotation PDF / Image / Excel", type=["pdf", "png", "jpg", "jpeg", "xlsx", "xls", "csv"])
                    remarks = st.text_area("Quotation Remarks")
                    if st.form_submit_button("Submit Quotation", use_container_width=True):
                        if not quotation_no.strip():
                            st.error("Quotation No is required.")
                        else:
                            fname, fdata = "", ""
                            if quotation_file is not None:
                                if quotation_file.size > 10 * 1024 * 1024:
                                    st.error("Quotation file should be max 10 MB.")
                                    return
                                fname = quotation_file.name
                                fdata = base64.b64encode(quotation_file.read()).decode("utf-8")
                            insert_row("quotations", {
                                "requirement_id": req_id,
                                "requirement_no": str(req_row.get("requirement_no", "")),
                                "business_username": username,
                                "business_name": st.session_state.get("full_name", username),
                                "quotation_no": quotation_no.strip(),
                                "quotation_date": str(quotation_date),
                                "amount": amount,
                                "gst_amount": gst_amount,
                                "total_amount": total_amount,
                                "valid_till": str(valid_till),
                                "quotation_file_name": fname,
                                "quotation_file_data": fdata,
                                "quotation_status": "Submitted",
                                "remarks": remarks,
                                "created_by": username,
                            })
                            st.success("Quotation submitted.")
                            st.rerun()
        with tab2:
            qdf = load_table("quotations", 5000)
            qdf = qdf[qdf["business_username"].astype(str) == username] if not qdf.empty and "business_username" in qdf.columns else pd.DataFrame()
            st.dataframe(qdf, use_container_width=True)
            if not qdf.empty:
                selected = st.selectbox("Select quotation ID to download file", qdf["id"].tolist(), key="quote_user_download_id")
                raw = safe_df(supabase.table("quotations").select("*").eq("id", int(selected)).limit(1).execute().data)
                if not raw.empty:
                    _quotation_file_download(raw.iloc[0])

        with tab3:
            st.subheader("Negotiation Requests")
            ndf = load_table("quotation_negotiations", 5000)
            ndf = ndf[ndf["business_username"].astype(str) == username] if not ndf.empty and "business_username" in ndf.columns else pd.DataFrame()
            if ndf.empty:
                st.info("No negotiation request received.")
            else:
                st.dataframe(ndf, use_container_width=True)
                open_ndf = ndf[ndf["status"].astype(str).isin(["Negotiation Requested", "Open", "Pending"])] if "status" in ndf.columns else ndf
                if open_ndf.empty:
                    st.info("No open negotiation pending.")
                else:
                    neg_ids = open_ndf["id"].dropna().astype(int).tolist()
                    selected_neg = st.selectbox("Select Negotiation ID to Respond", neg_ids, key="vendor_neg_id")
                    neg_raw = safe_df(supabase.table(TABLES["quotation_negotiations"]).select("*").eq("id", int(selected_neg)).limit(1).execute().data)
                    if not neg_raw.empty:
                        neg = neg_raw.iloc[0].to_dict()
                        st.info(f"Deadline: {neg.get('deadline','')} | Message: {neg.get('negotiation_message','')}")
                        with st.form("vendor_negotiation_response_form", clear_on_submit=True):
                            c1, c2, c3 = st.columns(3)
                            revised_amount = c1.number_input("Revised Amount", min_value=0.0, value=float(neg.get("original_amount", 0) or 0), step=100.0)
                            revised_gst = c2.number_input("Revised GST Amount", min_value=0.0, value=0.0, step=100.0)
                            revised_total = c3.number_input("Revised Total Amount", min_value=0.0, value=float(revised_amount + revised_gst), step=100.0)
                            response = st.text_area("Vendor Response / Negotiation Remarks")
                            revised_file = st.file_uploader("Upload Revised Quotation", type=["pdf", "png", "jpg", "jpeg", "xlsx", "xls", "csv"], key="revised_quote_file")
                            submit_neg = st.form_submit_button("Submit Revised Quotation", use_container_width=True)
                            if submit_neg:
                                fname, fdata = "", ""
                                if revised_file is not None:
                                    if revised_file.size > 10 * 1024 * 1024:
                                        st.error("Revised quotation file should be max 10 MB.")
                                        return
                                    fname = revised_file.name
                                    fdata = base64.b64encode(revised_file.read()).decode("utf-8")

                                supabase.table(TABLES["quotation_negotiations"]).update({
                                    "status": "Revised Submitted",
                                    "vendor_response": response,
                                    "revised_amount": revised_amount,
                                    "revised_gst_amount": revised_gst,
                                    "revised_total_amount": revised_total,
                                    "revised_file_name": fname,
                                    "revised_file_data": fdata,
                                    "submitted_by": username,
                                    "submitted_at": india_now().isoformat(),
                                }).eq("id", int(selected_neg)).execute()

                                try:
                                    qid = int(neg.get("quotation_id"))
                                    supabase.table(TABLES["quotations"]).update({
                                        "quotation_status": "Revised Submitted",
                                        "negotiation_status": "Revised Submitted",
                                        "amount": revised_amount,
                                        "gst_amount": revised_gst,
                                        "total_amount": revised_total,
                                        "remarks": response,
                                    }).eq("id", qid).execute()
                                except Exception:
                                    pass

                                write_audit_log("Quotation Negotiation", "REVISED_SUBMITTED", selected_neg, f"Vendor submitted revised quotation {revised_total}")
                                st.success("Revised quotation submitted.")
                                st.rerun()
    else:
        st.warning("You do not have access to Quotation Portal.")

def reports():
    show_header("Registers / Reports", "section-rep")

    tab1, tab2, tab3, tab4 = st.tabs([
        "General Registers",
        "Ledger / Party Reports",
        "Financial Statements",
        "Stock Summary",
    ])

    with tab1:
        opts=["employees","ledgers","stock_ledgers","company_profiles","financial_years","cost_centers","document_series","gst_settings","calculation_books","sales","purchase","expenses","service_vouchers","stock_vouchers","fixed_assets","accounting_entries","accounting_entry_lines","appointments","attendance","attendance_visits","inout","visitors","tasks","audit_logs","quotation_requirements","quotation_business_users","quotation_access","quotations"]
        if is_super_admin(): opts=["clients","users"]+opts
        report = st.selectbox("Select Register", opts, key="general_register_select")
        rows = st.number_input("Rows to load", 100, 50000, 1000, 100, key="general_rows")
        df=load_table(report, int(rows))
        search=st.text_input("Search Report", key="general_search")
        filtered=filter_dataframe(df, search)
        st.dataframe(filtered, use_container_width=True)
        c1,c2=st.columns(2)
        with c1: st.download_button("Download Excel", to_excel_bytes(filtered), f"{report}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="general_xlsx")
        with c2: st.download_button("Download CSV", filtered.to_csv(index=False).encode("utf-8"), f"{report}.csv", "text/csv", use_container_width=True, key="general_csv")

    with tab2:
        st.subheader("Ledger Group / Party Reports")
        ledger_df = load_table("ledgers", 50000)
        tb = build_trial_balance_df()
        if ledger_df.empty:
            st.info("No ledger found.")
        else:
            preferred = ["All", "Sundry Debtors", "Sundry Creditors", "Bank Accounts", "Cash-in-Hand", "Duties & Taxes", "Sales Accounts", "Purchase Accounts", "Direct Expenses", "Indirect Expenses", "Fixed Assets", "Capital Account"]
            actual = ledger_df["ledger_group"].dropna().astype(str).unique().tolist() if "ledger_group" in ledger_df.columns else []
            group_list=[]
            for g in preferred + sorted(actual):
                if g not in group_list: group_list.append(g)
            selected_group = st.selectbox("First Select Ledger Group", group_list, key="ledger_group_report")
            if selected_group == "All": show_df = ledger_df.copy()
            else: show_df = ledger_df[ledger_df["ledger_group"].astype(str) == selected_group].copy()
            ledger_names = ["All"] + sorted(show_df["ledger_name"].dropna().astype(str).unique().tolist()) if not show_df.empty else ["All"]
            selected_ledger = st.selectbox("Then Select Ledger Name", ledger_names, key="ledger_name_report")
            if selected_ledger != "All": show_df = show_df[show_df["ledger_name"].astype(str) == selected_ledger]
            cols = [c for c in ["ledger_group","ledger_name","address","contact_no","email","tan_no","gst_no","pan_no","opening_balance","balance_type","status"] if c in show_df.columns]
            show_df = show_df[cols] if cols else show_df
            st.info(f"Records Found: {len(show_df)}")
            st.dataframe(show_df, use_container_width=True)
            c1,c2=st.columns(2)
            safe_group=selected_group.replace(" ","_").replace("/","_"); safe_ledger=selected_ledger.replace(" ","_").replace("/","_")
            with c1: st.download_button("Download Ledger Excel", to_excel_bytes(show_df), f"ledger_{safe_group}_{safe_ledger}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="ledger_xlsx")
            with c2: st.download_button("Download Ledger CSV", show_df.to_csv(index=False).encode("utf-8"), f"ledger_{safe_group}_{safe_ledger}.csv", "text/csv", use_container_width=True, key="ledger_csv")

            st.divider()
            c3,c4=st.columns(2)
            receivable = tb[tb["ledger_group"].astype(str) == "Sundry Debtors"].copy() if not tb.empty else pd.DataFrame()
            payable = tb[tb["ledger_group"].astype(str) == "Sundry Creditors"].copy() if not tb.empty else pd.DataFrame()
            with c3:
                st.subheader("Sundry Receivable Report")
                if not receivable.empty:
                    receivable = receivable[["ledger_name","contact_no","email","closing_dr","closing_cr"]]
                    st.dataframe(receivable, use_container_width=True)
                    st.download_button("Download Receivable Excel", to_excel_bytes(receivable), "sundry_receivable.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="recv_xlsx")
                else: st.info("No Sundry Debtors found.")
            with c4:
                st.subheader("Sundry Payable Report")
                if not payable.empty:
                    payable = payable[["ledger_name","contact_no","email","closing_dr","closing_cr"]]
                    st.dataframe(payable, use_container_width=True)
                    st.download_button("Download Payable Excel", to_excel_bytes(payable), "sundry_payable.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="pay_xlsx")
                else: st.info("No Sundry Creditors found.")

    with tab3:
        st.subheader("Financial Statements")
        tb = build_trial_balance_df()
        if tb.empty:
            st.info("No ledger data found for financial reports.")
        else:
            report_type = st.selectbox("Select Financial Report", ["Trial Balance", "Profit & Loss", "Balance Sheet"], key="financial_report_type")
            fmt = "Standard"
            if report_type in ["Profit & Loss", "Balance Sheet"]:
                fmt = st.selectbox("P&L / B.S. Format", ["Standard", "Overheads"], key="financial_report_format_offline")
            if report_type == "Trial Balance":
                show_df = build_trial_balance_offline_style_df()
            elif report_type == "Profit & Loss":
                show_df = build_profit_loss_offline_style_df(fmt)
            else:
                show_df = build_balance_sheet_offline_style_df(fmt)
            st.success("Offline desktop ERP format applied in online report.")
            st.dataframe(show_df, use_container_width=True)
            st.download_button(f"Download {report_type} Excel", to_excel_bytes(show_df), f"{report_type.replace(' ','_').lower()}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="financial_xlsx")
            st.download_button(f"Download {report_type} CSV", show_df.to_csv(index=False).encode("utf-8"), f"{report_type.replace(' ','_').lower()}.csv", "text/csv", use_container_width=True, key="financial_csv")

    with tab4:
        st.subheader("Stock Report: Opening Balance / Purchase / Consumed / Closing Balance")
        stock_summary = build_stock_summary_df()
        if stock_summary.empty:
            st.info("No stock item found.")
        else:
            stock_groups = ["All"] + sorted(stock_summary["Stock Group"].dropna().astype(str).unique().tolist())
            selected_stock_group = st.selectbox("Select Stock Group", stock_groups, key="stock_summary_group")
            show_stock = stock_summary.copy() if selected_stock_group == "All" else stock_summary[stock_summary["Stock Group"].astype(str) == selected_stock_group].copy()
            stock_items = ["All"] + sorted(show_stock["Item Name"].dropna().astype(str).unique().tolist()) if not show_stock.empty else ["All"]
            selected_item = st.selectbox("Select Stock Item", stock_items, key="stock_summary_item")
            if selected_item != "All": show_stock = show_stock[show_stock["Item Name"].astype(str) == selected_item]
            st.dataframe(show_stock, use_container_width=True)
            safe_group = selected_stock_group.replace(" ", "_").replace("/", "_")
            safe_item = selected_item.replace(" ", "_").replace("/", "_")
            c1,c2=st.columns(2)
            with c1: st.download_button("Download Stock Summary Excel", to_excel_bytes(show_stock), f"stock_summary_{safe_group}_{safe_item}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="stock_summary_xlsx")
            with c2: st.download_button("Download Stock Summary CSV", show_stock.to_csv(index=False).encode("utf-8"), f"stock_summary_{safe_group}_{safe_item}.csv", "text/csv", use_container_width=True, key="stock_summary_csv")

def placeholder_denied(): st.warning("This module is not enabled for this client.")


def erp_control_center():
    show_header("ERP Control Center", "section-master")
    st.info("Use this screen to review parked / pending approval entries across key ERP modules.")
    keys = ["sales","purchase","expenses","service_vouchers","stock_vouchers","fixed_assets","accounting_entries","appointments","tasks"]
    selected = st.selectbox("Select Module", keys)
    df = load_table(selected, 5000)
    if df.empty:
        st.info("No records found.")
        return
    filters = ["All"]
    if "parking_status" in df.columns: filters += ["Draft", "Parked", "Posted"]
    parking = st.selectbox("Parking / Posting Filter", filters)
    if parking != "All" and "parking_status" in df.columns:
        df = df[df["parking_status"].astype(str) == parking]
    approval = st.selectbox("Approval Filter", ["All", "Pending", "Approved", "Rejected", "Not Required"])
    if approval != "All" and "approval_status" in df.columns:
        df = df[df["approval_status"].astype(str) == approval]
    st.dataframe(df, use_container_width=True)
    st.download_button("Download Control Report Excel", to_excel_bytes(df), f"erp_control_{selected}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)



# ---------- ENTERPRISE EXTENSION MODULES: WORKFLOW / ANALYTICS / AUDIT / SYNC ----------
def _table_df(table_name, limit_rows=5000):
    try:
        q = supabase.table(table_name).select("*")
        if not is_super_admin() and "client_code" not in ["clients"]:
            q = q.eq("client_code", get_client_code())
        return safe_df(q.order("id", desc=True).limit(limit_rows).execute().data)
    except Exception as e:
        st.warning(f"Table not ready: {table_name}. Please run SQL. Details: {e}")
        return pd.DataFrame()


def _insert_table(table_name, row):
    if "client_code" not in row:
        row["client_code"] = get_client_code()
    row.setdefault("created_by", st.session_state.get("username", ""))
    try:
        supabase.table(table_name).insert(row).execute()
        log_audit(table_name, "CREATE", "", "Created from Enterprise module")
        return True
    except Exception as e:
        st.error(f"Save failed in {table_name}: {e}")
        return False


def enterprise_card(title, value, note=""):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f172a,#1d4ed8);color:white;border-radius:14px;padding:14px 16px;margin:6px 0;box-shadow:0 6px 14px rgba(15,23,42,.18);">
      <div style="font-size:13px;opacity:.85;">{title}</div>
      <div style="font-size:26px;font-weight:900;line-height:1.1;">{value}</div>
      <div style="font-size:12px;opacity:.85;">{note}</div>
    </div>
    """, unsafe_allow_html=True)


def workflow_engine():
    show_header("Workflow Engine - Maker / Checker / Approver", "section-master")
    st.info("Define approval routing for ERP modules. Draft → Submitted → Checked → Approved → Posted / Rejected / Reversed.")
    with st.form("workflow_rule_form"):
        c1,c2,c3 = st.columns(3)
        module_name = c1.selectbox("Module", ["Sales", "Purchase", "Expense", "Service", "Stock Adjustment", "Payment", "Receipt", "Journal", "Attendance", "Task"])
        maker_role = c2.text_input("Maker Role", value="User")
        checker_role = c3.text_input("Checker Role", value="Manager")
        approver_role = c1.text_input("Approver Role", value="Admin")
        min_amount = c2.number_input("Minimum Amount", min_value=0.0, value=0.0, step=1000.0)
        max_amount = c3.number_input("Maximum Amount", min_value=0.0, value=999999999.0, step=1000.0)
        status = c1.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Workflow Rule", use_container_width=True):
            ok = _insert_table("workflow_rules", {"module_name":module_name,"maker_role":maker_role,"checker_role":checker_role,"approver_role":approver_role,"min_amount":min_amount,"max_amount":max_amount,"status":status})
            if ok: st.success("Workflow rule saved."); st.rerun()
    df=_table_df("workflow_rules")
    show_table_with_edit_delete("workflow_rules", df, "Workflow Rules") if not df.empty else st.info("No workflow rules found.")


def notification_center():
    show_header("Notification Center", "section-master")
    c1,c2,c3,c4 = st.columns(4)
    pending_approval = _table_df("approval_requests", 5000)
    quotations = _table_df("quotations", 5000)
    tasks_df = load_table("tasks", 5000)
    stock_df = _table_df("stock_ledgers", 5000)
    with c1: enterprise_card("Pending Approval", len(pending_approval[pending_approval.get("status", pd.Series(dtype=str)).astype(str).eq("Pending")]) if not pending_approval.empty and "status" in pending_approval else 0)
    with c2: enterprise_card("Quotations", len(quotations))
    with c3: enterprise_card("Overdue Tasks", len(tasks_df[tasks_df.get("status", pd.Series(dtype=str)).astype(str)!="Completed"]) if not tasks_df.empty and "status" in tasks_df else 0)
    with c4: enterprise_card("Low Stock Alerts", 0, "Set reorder level in stock master")
    st.subheader("Notification Inbox")
    notif = _table_df("notifications")
    if notif.empty:
        st.info("No notifications found.")
    else:
        st.dataframe(notif, use_container_width=True)


def dashboard_analytics():
    show_header("Dashboard Analytics", "section-master")
    sales_df = load_table("sales", 10000)
    purchase_df = load_table("purchase", 10000)
    exp_df = load_table("expenses", 10000)
    c1,c2,c3,c4 = st.columns(4)
    sales_total = float(pd.to_numeric(sales_df.get("total_value", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not sales_df.empty else 0
    pur_total = float(pd.to_numeric(purchase_df.get("total_value", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not purchase_df.empty else 0
    exp_total = float(pd.to_numeric(exp_df.get("total_value", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not exp_df.empty else 0
    with c1: enterprise_card("Sales", f"₹ {sales_total:,.2f}")
    with c2: enterprise_card("Purchase", f"₹ {pur_total:,.2f}")
    with c3: enterprise_card("Expense", f"₹ {exp_total:,.2f}")
    with c4: enterprise_card("Gross Margin", f"₹ {sales_total-pur_total-exp_total:,.2f}")
    tab1,tab2,tab3 = st.tabs(["Top Customers", "Top Vendors", "Monthly Trend"])
    with tab1:
        if not sales_df.empty and "customer_name" in sales_df:
            st.dataframe(sales_df.groupby("customer_name", dropna=False)["total_value"].sum().reset_index().sort_values("total_value", ascending=False).head(20), use_container_width=True)
    with tab2:
        if not purchase_df.empty and "supplier_name" in purchase_df:
            st.dataframe(purchase_df.groupby("supplier_name", dropna=False)["total_value"].sum().reset_index().sort_values("total_value", ascending=False).head(20), use_container_width=True)
    with tab3:
        st.info("Monthly sales/purchase/expense trend can be expanded with date-wise charts after clean invoice date data is available.")


def budget_vs_actual():
    show_header("Budget vs Actual", "section-master")
    with st.form("budget_form"):
        c1,c2,c3,c4=st.columns(4)
        budget_year=c1.text_input("Financial Year", value=financial_year(india_now().date()))
        cost_center=c2.text_input("Cost Center / Department")
        ledger_group=c3.selectbox("Ledger Group", DEFAULT_LEDGER_GROUPS)
        budget_amount=c4.number_input("Budget Amount", min_value=0.0, value=0.0, step=1000.0)
        remarks=st.text_input("Remarks")
        if st.form_submit_button("Save Budget", use_container_width=True):
            if _insert_table("budgets", {"budget_year":budget_year,"cost_center":cost_center,"ledger_group":ledger_group,"budget_amount":budget_amount,"remarks":remarks}):
                st.success("Budget saved."); st.rerun()
    budgets=_table_df("budgets")
    if budgets.empty:
        st.info("No budget found.")
    else:
        st.dataframe(budgets, use_container_width=True)
        st.download_button("Download Budget Excel", to_excel_bytes(budgets), "budget_vs_actual.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def bank_reconciliation():
    show_header("Bank Reconciliation", "section-master")
    st.info("Upload bank statement and mark matching entries. This is a practical starter BRS module.")
    uploaded = st.file_uploader("Upload Bank Statement CSV/XLSX", type=["csv","xlsx"], key="bank_stmt_upload")
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            st.dataframe(df, use_container_width=True)
            st.download_button("Download Uploaded Statement Excel", to_excel_bytes(df), "bank_statement_review.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        except Exception as e:
            st.error(e)
    with st.form("brs_manual_form"):
        c1,c2,c3=st.columns(3)
        bank_name=c1.text_input("Bank Name")
        stmt_date=c2.date_input("Statement Date", value=india_now().date(), format="DD-MM-YYYY")
        bank_balance=c3.number_input("Bank Statement Balance", value=0.0, step=1000.0)
        books_balance=c1.number_input("Books Balance", value=0.0, step=1000.0)
        remarks=c2.text_input("Remarks")
        if st.form_submit_button("Save BRS Snapshot", use_container_width=True):
            if _insert_table("bank_reconciliations", {"bank_name":bank_name,"statement_date":str(stmt_date),"bank_balance":bank_balance,"books_balance":books_balance,"difference":bank_balance-books_balance,"remarks":remarks}):
                st.success("BRS snapshot saved."); st.rerun()
    df=_table_df("bank_reconciliations")
    if not df.empty: st.dataframe(df, use_container_width=True)


def document_management():
    show_header("Document Management System", "section-master")
    with st.form("dms_form"):
        c1,c2,c3=st.columns(3)
        module_name=c1.selectbox("Module", ["Sales","Purchase","Expense","Service","Stock","Quotation","Fixed Asset","Other"])
        record_ref=c2.text_input("Record / Voucher Ref")
        doc_title=c3.text_input("Document Title")
        upload=st.file_uploader("Attach PDF/Image/Excel", type=["pdf","png","jpg","jpeg","xlsx","xls","csv"], key="dms_upload")
        remarks=st.text_input("Remarks")
        if st.form_submit_button("Save Document", use_container_width=True):
            fn=""; data=""
            if upload is not None:
                fn=upload.name; data=base64.b64encode(upload.read()).decode("utf-8")
            if _insert_table("documents", {"module_name":module_name,"record_ref":record_ref,"document_title":doc_title,"file_name":fn,"file_data":data,"remarks":remarks}):
                st.success("Document saved."); st.rerun()
    df=_table_df("documents")
    if not df.empty: st.dataframe(df.drop(columns=[c for c in ["file_data"] if c in df.columns]), use_container_width=True)


def purchase_cycle():
    show_header("Purchase Cycle: Indent → RFQ → PO → GRN → Invoice", "section-accounts")
    tab1,tab2,tab3=st.tabs(["Purchase Indent", "Purchase Order", "GRN"])
    with tab1:
        with st.form("indent_form"):
            c1,c2,c3=st.columns(3)
            indent_no=c1.text_input("Indent No")
            indent_date=c2.date_input("Indent Date", value=india_now().date(), format="DD-MM-YYYY")
            item=c3.text_input("Item / Requirement")
            qty=c1.number_input("Qty", min_value=0.0, value=1.0)
            purpose=c2.text_input("Purpose")
            status=c3.selectbox("Status", ["Draft","Submitted","Approved","Closed"])
            if st.form_submit_button("Save Indent", use_container_width=True):
                _insert_table("purchase_indents", {"indent_no":indent_no,"indent_date":str(indent_date),"item_name":item,"qty":qty,"purpose":purpose,"status":status}); st.rerun()
        df=_table_df("purchase_indents")
        if not df.empty: st.dataframe(df, use_container_width=True)
    with tab2:
        with st.form("po_form"):
            c1,c2,c3=st.columns(3)
            po_no=c1.text_input("PO No")
            po_date=c2.date_input("PO Date", value=india_now().date(), format="DD-MM-YYYY")
            vendor=c3.selectbox("Vendor", get_ledger_names("Sundry Creditors"))
            item=c1.selectbox("Item", get_stock_item_names())
            qty=c2.number_input("Qty", min_value=0.0, value=1.0)
            rate=c3.number_input("Rate", min_value=0.0, value=0.0)
            if st.form_submit_button("Save PO", use_container_width=True):
                _insert_table("purchase_orders", {"po_no":po_no,"po_date":str(po_date),"vendor_name":vendor,"item_name":item,"qty":qty,"rate":rate,"amount":qty*rate,"status":"Open"}); st.rerun()
        df=_table_df("purchase_orders")
        if not df.empty: st.dataframe(df, use_container_width=True)
    with tab3:
        with st.form("grn_form"):
            c1,c2,c3=st.columns(3)
            grn_no=c1.text_input("GRN No")
            grn_date=c2.date_input("GRN Date", value=india_now().date(), format="DD-MM-YYYY")
            po_no=c3.text_input("PO No")
            item=c1.selectbox("Received Item", get_stock_item_names(), key="grn_item")
            qty=c2.number_input("Received Qty", min_value=0.0, value=1.0)
            remarks=c3.text_input("Remarks")
            if st.form_submit_button("Save GRN", use_container_width=True):
                _insert_table("goods_receipt_notes", {"grn_no":grn_no,"grn_date":str(grn_date),"po_no":po_no,"item_name":item,"received_qty":qty,"remarks":remarks,"status":"Received"}); st.rerun()
        df=_table_df("goods_receipt_notes")
        if not df.empty: st.dataframe(df, use_container_width=True)


def sales_cycle():
    show_header("Sales Cycle: Quotation → Sales Order → Delivery Challan → Invoice", "section-accounts")
    tab1,tab2=st.tabs(["Sales Order", "Delivery Challan"])
    with tab1:
        with st.form("so_form"):
            c1,c2,c3=st.columns(3)
            so_no=c1.text_input("SO No")
            so_date=c2.date_input("SO Date", value=india_now().date(), format="DD-MM-YYYY")
            customer=c3.selectbox("Customer", get_ledger_names("Sundry Debtors"))
            item=c1.selectbox("Item", get_stock_item_names(), key="so_item")
            qty=c2.number_input("Qty", min_value=0.0, value=1.0)
            rate=c3.number_input("Rate", min_value=0.0, value=0.0)
            if st.form_submit_button("Save Sales Order", use_container_width=True):
                _insert_table("sales_orders", {"so_no":so_no,"so_date":str(so_date),"customer_name":customer,"item_name":item,"qty":qty,"rate":rate,"amount":qty*rate,"status":"Open"}); st.rerun()
        df=_table_df("sales_orders")
        if not df.empty: st.dataframe(df, use_container_width=True)
    with tab2:
        with st.form("dc_form"):
            c1,c2,c3=st.columns(3)
            dc_no=c1.text_input("Delivery Challan No")
            dc_date=c2.date_input("DC Date", value=india_now().date(), format="DD-MM-YYYY")
            so_no=c3.text_input("SO No")
            customer=c1.selectbox("Customer", get_ledger_names("Sundry Debtors"), key="dc_cust")
            item=c2.selectbox("Item", get_stock_item_names(), key="dc_item")
            qty=c3.number_input("Delivered Qty", min_value=0.0, value=1.0)
            if st.form_submit_button("Save Delivery Challan", use_container_width=True):
                _insert_table("delivery_challans", {"dc_no":dc_no,"dc_date":str(dc_date),"so_no":so_no,"customer_name":customer,"item_name":item,"qty":qty,"status":"Delivered"}); st.rerun()
        df=_table_df("delivery_challans")
        if not df.empty: st.dataframe(df, use_container_width=True)


def asset_management_advanced():
    show_header("Advanced Asset Management", "section-inventory")
    with st.form("asset_adv_form"):
        c1,c2,c3,c4=st.columns(4)
        asset_code=c1.text_input("Asset Code / Tag")
        asset_name=c2.text_input("Asset Name")
        location=c3.text_input("Location")
        status=c4.selectbox("Status", ["Active","Transferred","Under Repair","Scrapped","Sold"])
        purchase_date=c1.date_input("Purchase Date", value=india_now().date(), format="DD-MM-YYYY")
        cost=c2.number_input("Cost", min_value=0.0, value=0.0)
        dep_rate=c3.number_input("Dep %", min_value=0.0, value=0.0)
        amc_due=c4.date_input("AMC / Maintenance Due", value=india_now().date(), format="DD-MM-YYYY")
        if st.form_submit_button("Save Asset Control", use_container_width=True):
            _insert_table("asset_controls", {"asset_code":asset_code,"asset_name":asset_name,"location":location,"asset_status":status,"purchase_date":str(purchase_date),"cost":cost,"depreciation_rate":dep_rate,"maintenance_due_date":str(amc_due)}); st.rerun()
    df=_table_df("asset_controls")
    if not df.empty: st.dataframe(df, use_container_width=True)


def pwa_mobile_app():
    show_header("Mobile PWA Setup", "section-tools")
    st.success("RBM ERP can be installed on Android/iPhone as a browser app shortcut with custom icon.")

    st.markdown("""
    ### How to host custom PWA icon files

    In your GitHub repository, create this folder structure:

    ```text
    .streamlit/config.toml
    static/manifest.json
    static/rbm-logo-192.png
    static/rbm-logo-512.png
    ```

    In `.streamlit/config.toml` keep:

    ```toml
    [server]
    enableStaticServing = true
    ```

    Then your icon files will be available from:

    ```text
    /app/static/rbm-logo-192.png
    /app/static/rbm-logo-512.png
    /app/static/manifest.json
    ```

    Android Chrome: open ERP URL → 3 dots → Add to Home screen.  
    iPhone Safari: open ERP URL → Share → Add to Home Screen.
    """)

    manifest = {
        "name": "RBM Swadeshi ERP AI Enterprise",
        "short_name": "RBM ERP",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#075985",
        "description": "RBM Swadeshi ERP AI Enterprise",
        "icons": [
            {"src": "/app/static/rbm-logo-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/app/static/rbm-logo-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    st.download_button("Download manifest.json", json.dumps(manifest, indent=2).encode("utf-8"), "manifest.json", "application/json", use_container_width=True)
    st.info("Logo PNG files are included in the final package ZIP. Upload/copy them to the GitHub static folder.")


def digital_audit_module():
    show_header("RBM Digital Audit Module", "section-reports")
    st.info("Exception analytics for duplicate invoices, duplicate payments, GST mismatch and stock mismatch.")
    sales_df=load_table("sales",10000); purchase_df=load_table("purchase",10000); exp_df=load_table("expenses",10000)
    tab1,tab2,tab3=st.tabs(["Duplicate Invoices", "High Value Expenses", "GST Exceptions"])
    with tab1:
        if not purchase_df.empty and "invoice_no" in purchase_df:
            dup=purchase_df[purchase_df.duplicated(["invoice_no","supplier_name"], keep=False)] if "supplier_name" in purchase_df else purchase_df[purchase_df.duplicated(["invoice_no"], keep=False)]
            st.dataframe(dup, use_container_width=True)
        else: st.info("No purchase data.")
    with tab2:
        if not exp_df.empty and "total_value" in exp_df:
            val=pd.to_numeric(exp_df["total_value"], errors="coerce").fillna(0)
            st.dataframe(exp_df[val > val.quantile(.90)] if len(val)>0 else exp_df, use_container_width=True)
    with tab3:
        frames=[]
        for name,df in [("Sales",sales_df),("Purchase",purchase_df),("Expense",exp_df)]:
            if not df.empty:
                tmp=df.copy(); tmp["source"]=name
                frames.append(tmp)
        if frames: st.dataframe(pd.concat(frames, ignore_index=True).head(500), use_container_width=True)


def ai_assistant():
    show_header("Calculator", "section-tools")
    st.info("Simple ERP calculator. AI API integration can be added later as a separate premium module.")

    c1, c2, c3, c4 = st.columns(4)
    qty = c1.number_input("Qty", value=1.0, step=1.0, key="calc_qty")
    rate = c2.number_input("Rate", value=0.0, step=1.0, key="calc_rate")
    gst_percent = c3.number_input("GST %", value=18.0, step=1.0, key="calc_gst")
    discount = c4.number_input("Discount", value=0.0, step=1.0, key="calc_discount")

    c5, c6, c7 = st.columns(3)
    freight = c5.number_input("Freight", value=0.0, step=1.0, key="calc_freight")
    other_charges = c6.number_input("Other Charges", value=0.0, step=1.0, key="calc_other")
    tds = c7.number_input("Less TDS", value=0.0, step=1.0, key="calc_tds")

    taxable = qty * rate
    taxable_after_discount = max(taxable - discount, 0)
    gst_value = taxable_after_discount * gst_percent / 100
    gross = taxable_after_discount + gst_value + freight + other_charges
    net = gross - tds

    c8, c9, c10, c11 = st.columns(4)
    with c8: show_metric_card("Taxable", money(taxable))
    with c9: show_metric_card("GST", money(gst_value))
    with c10: show_metric_card("Gross", money(gross))
    with c11: show_metric_card("Net", money(net))

    st.subheader("Calculation Summary")
    st.dataframe(pd.DataFrame([{
        "Qty": qty,
        "Rate": rate,
        "Taxable": taxable,
        "Discount": discount,
        "Taxable After Discount": taxable_after_discount,
        "GST %": gst_percent,
        "GST Value": gst_value,
        "Freight": freight,
        "Other Charges": other_charges,
        "TDS": tds,
        "Net Amount": net,
    }]), use_container_width=True)


def multi_company_branch():
    show_header("Multi Company / Multi Branch Control", "section-master")
    tab1,tab2=st.tabs(["Company / Business Unit", "Branch / Location"])
    with tab1:
        with st.form("business_unit_form"):
            c1,c2,c3=st.columns(3)
            name=c1.text_input("Company / Unit Name")
            gst=c2.text_input("GST No")
            status=c3.selectbox("Status", ["Active","Inactive"])
            address=st.text_area("Address")
            if st.form_submit_button("Save Business Unit", use_container_width=True):
                _insert_table("business_units", {"unit_name":name,"gst_no":gst,"address":address,"status":status}); st.rerun()
        df=_table_df("business_units")
        if not df.empty: st.dataframe(df, use_container_width=True)
    with tab2:
        with st.form("branch_form"):
            c1,c2,c3=st.columns(3)
            branch=c1.text_input("Branch / Location")
            city=c2.text_input("City")
            status=c3.selectbox("Status", ["Active","Inactive"], key="branch_status")
            if st.form_submit_button("Save Branch", use_container_width=True):
                _insert_table("branches", {"branch_name":branch,"city":city,"status":status}); st.rerun()
        df=_table_df("branches")
        if not df.empty: st.dataframe(df, use_container_width=True)



def email_sms_settings():
    show_header("Email / SMS Settings", "section-tools")
    st.info("Email auto-send ke liye Streamlit Cloud Secrets me SMTP details add karni hongi. Password app me store mat karo.")
    st.markdown("""
    **Streamlit Cloud → App → Settings → Secrets** me ye add karo:

    ```toml
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = "587"
    SMTP_USER = "your_email@gmail.com"
    SMTP_PASSWORD = "your_gmail_app_password"
    SMTP_FROM = "your_email@gmail.com"
    ERP_PUBLIC_URL = "https://rbm-office-saas.streamlit.app/"
    ```

    Gmail ke liye normal password nahi chalega. Gmail **App Password** banana padega.
    """)

    c1, c2 = st.columns(2)
    with c1:
        st.write("Current SMTP Status")
        st.write("SMTP_HOST:", "✅ Set" if _safe_secret("SMTP_HOST", "") else "❌ Missing")
        st.write("SMTP_USER:", "✅ Set" if _safe_secret("SMTP_USER", "") else "❌ Missing")
        st.write("SMTP_PASSWORD:", "✅ Set" if _safe_secret("SMTP_PASSWORD", "") else "❌ Missing")
        st.write("SMTP_FROM:", "✅ Set" if _safe_secret("SMTP_FROM", "") else "❌ Missing")
    with c2:
        st.write("Test Email")
        test_to = st.text_input("Send test email to")
        if st.button("Send Test Email", use_container_width=True):
            subject = "RBM ERP Test Email"
            body = "This is a test email from RBM ERP SaaS."
            sent, msg, mailto = send_negotiation_email(test_to, subject, body)
            if sent:
                st.success(msg)
            else:
                st.warning(msg)
                if mailto:
                    st.markdown(f"[Open Email Draft]({mailto})")

    st.divider()
    st.subheader("SMS / WhatsApp")
    st.info("Direct SMS/WhatsApp auto-send ke liye Twilio / WhatsApp Business API / SMS provider API add karna padega. Abhi mobile number store hoga; email draft support hai.")


def offline_sync_engine():
    show_header("Online / Offline Sync Engine", "section-tools")
    st.info("Future-ready sync control for SQLite desktop + Supabase online ERP.")
    with st.form("sync_log_form"):
        c1,c2,c3=st.columns(3)
        device_id=c1.text_input("Device ID", value="DESKTOP-001")
        sync_direction=c2.selectbox("Sync Direction", ["Upload Offline to Online", "Download Online to Offline", "Two-way Sync"])
        status=c3.selectbox("Status", ["Planned", "Running", "Completed", "Failed"])
        remarks=st.text_input("Remarks")
        if st.form_submit_button("Save Sync Log", use_container_width=True):
            _insert_table("sync_logs", {"device_id":device_id,"sync_direction":sync_direction,"sync_status":status,"remarks":remarks}); st.rerun()
    df=_table_df("sync_logs")
    if not df.empty: st.dataframe(df, use_container_width=True)



# ---------- MANUFACTURING / BOM / SUPPORT EXTENSIONS ----------
def _bom_no_list():
    try:
        df = load_table("bom_headers", 2000)
        vals = df["bom_no"].dropna().astype(str).unique().tolist() if not df.empty and "bom_no" in df.columns else []
        return vals or ["No BOM Found"]
    except Exception:
        return ["No BOM Found"]


def bill_of_material_module():
    show_header("Bill of Material (BOM)", "section-inv")
    st.info("Create Finished Goods recipe with raw material consumption and cost per unit.")
    if "bom_line_count" not in st.session_state:
        st.session_state["bom_line_count"] = 1
    cadd, crem, creset = st.columns(3)
    if cadd.button("➕ Add Raw Material Line", use_container_width=True, key="bom_add_line"):
        st.session_state["bom_line_count"] += 1; st.rerun()
    if crem.button("➖ Remove Last Line", use_container_width=True, key="bom_remove_line"):
        if st.session_state["bom_line_count"] > 1:
            st.session_state["bom_line_count"] -= 1; st.rerun()
    if creset.button("🔄 Reset BOM Lines", use_container_width=True, key="bom_reset_line"):
        st.session_state["bom_line_count"] = 1; st.rerun()
    stock_items = get_stock_items()
    with st.form("bom_form"):
        c1, c2, c3 = st.columns(3)
        bom_no = c1.text_input("BOM No")
        bom_date = c2.date_input("BOM Date", value=india_now().date(), format="DD-MM-YYYY")
        fg_item = c3.selectbox("Finished Goods Item", stock_items, key="bom_fg_item")
        fg_qty = c1.number_input("FG Qty", min_value=0.0, value=1.0, step=1.0)
        status = c2.selectbox("Status", ["Draft", "Active", "Inactive"])
        remarks = c3.text_input("Remarks")
        st.subheader("Raw Material Consumption")
        line_rows, material_cost = [], 0.0
        for i in range(st.session_state["bom_line_count"]):
            st.markdown(f"**Raw Material {i + 1}**")
            a, b, c, d, e = st.columns(5)
            rm_item = a.selectbox("RM Item", stock_items, key=f"bom_rm_item_{i}")
            unit = b.text_input("Unit", key=f"bom_unit_{i}")
            rm_qty = c.number_input("Qty", min_value=0.0, value=0.0, step=1.0, key=f"bom_qty_{i}")
            rm_rate = d.number_input("Rate", min_value=0.0, value=0.0, step=1.0, key=f"bom_rate_{i}")
            rm_amount = rm_qty * rm_rate
            e.metric("Amount", f"{rm_amount:,.2f}")
            line_rows.append({"rm_item": rm_item, "unit": unit, "rm_qty": rm_qty, "rm_rate": rm_rate, "rm_amount": rm_amount})
            material_cost += rm_amount
        st.subheader("Production Cost")
        c4, c5, c6, c7 = st.columns(4)
        labour_cost = c4.number_input("Labour Cost", min_value=0.0, value=0.0, step=100.0)
        power_cost = c5.number_input("Power Cost", min_value=0.0, value=0.0, step=100.0)
        packing_cost = c6.number_input("Packing Cost", min_value=0.0, value=0.0, step=100.0)
        other_cost = c7.number_input("Other Cost", min_value=0.0, value=0.0, step=100.0)
        total_cost = material_cost + labour_cost + power_cost + packing_cost + other_cost
        cost_per_unit = total_cost / fg_qty if fg_qty else 0
        st.info(f"Material Cost: {material_cost:,.2f} | Total Cost: {total_cost:,.2f} | Cost Per Unit: {cost_per_unit:,.2f}")
        if st.form_submit_button("Save BOM", use_container_width=True):
            if not bom_no.strip():
                st.error("BOM No is required.")
            elif fg_item == "No Item Found":
                st.error("Please create Stock Ledger / Item first.")
            else:
                res = insert_row("bom_headers", {"bom_no": bom_no.strip(), "bom_date": str(bom_date), "fg_item": fg_item, "fg_qty": fg_qty, "labour_cost": labour_cost, "power_cost": power_cost, "packing_cost": packing_cost, "other_cost": other_cost, "material_cost": material_cost, "total_cost": total_cost, "cost_per_unit": cost_per_unit, "status": status, "remarks": remarks, "created_by": current_user()})
                header_id = ""
                try:
                    header_id = res.data[0].get("id", "") if res.data else ""
                except Exception:
                    header_id = ""
                for line in line_rows:
                    if line["rm_item"] != "No Item Found" and float(line["rm_qty"] or 0) > 0:
                        insert_row("bom_lines", {"bom_header_id": header_id, "bom_no": bom_no.strip(), "rm_item": line["rm_item"], "unit": line["unit"], "rm_qty": line["rm_qty"], "rm_rate": line["rm_rate"], "rm_amount": line["rm_amount"], "created_by": current_user()})
                st.success("BOM saved successfully."); st.rerun()
    tab1, tab2 = st.tabs(["BOM Register", "BOM Raw Material Lines"])
    with tab1: show_table_with_edit_delete("bom_headers", load_table("bom_headers", 1000), "BOM Register")
    with tab2: show_table_with_edit_delete("bom_lines", load_table("bom_lines", 2000), "BOM Lines")


def production_order_module():
    simple_module_form("production_orders", "Production Order", [("order_no", "Order No", "text"), ("order_date", "Order Date", "date"), ("bom_no", "BOM No", _bom_no_list()), ("fg_item", "FG Item", get_stock_items()), ("planned_qty", "Planned Qty", "number"), ("due_date", "Due Date", "date"), ("status", "Status", ["Draft", "Released", "In Process", "Completed", "Cancelled"]), ("remarks", "Remarks", "text")], "section-inv")

def production_entry_module():
    simple_module_form("production_entries", "Production Entry", [("entry_no", "Entry No", "text"), ("entry_date", "Entry Date", "date"), ("order_no", "Production Order No", "text"), ("fg_item", "Finished Goods", get_stock_items()), ("produced_qty", "Produced Qty", "number"), ("warehouse", "Warehouse", "text"), ("status", "Status", ["Draft", "Posted", "Cancelled"]), ("remarks", "Remarks", "text")], "section-inv")

def consumption_entry_module():
    simple_module_form("consumption_entries", "Consumption Entry", [("entry_no", "Entry No", "text"), ("entry_date", "Entry Date", "date"), ("order_no", "Production Order No", "text"), ("rm_item", "Raw Material", get_stock_items()), ("consumed_qty", "Consumed Qty", "number"), ("rate", "Rate", "number"), ("amount", "Amount", "number"), ("warehouse", "Warehouse", "text"), ("remarks", "Remarks", "text")], "section-inv")

def finished_goods_entry_module():
    simple_module_form("fg_entries", "Finished Goods Entry", [("entry_no", "Entry No", "text"), ("entry_date", "Entry Date", "date"), ("fg_item", "Finished Goods", get_stock_items()), ("qty", "Qty", "number"), ("rate", "Rate", "number"), ("amount", "Amount", "number"), ("warehouse", "Warehouse", "text"), ("remarks", "Remarks", "text")], "section-inv")

def production_costing_module():
    show_header("Production Costing", "section-inv")
    with st.form("production_costing_form"):
        c1, c2, c3 = st.columns(3)
        costing_no = c1.text_input("Costing No"); costing_date = c2.date_input("Costing Date", value=india_now().date(), format="DD-MM-YYYY"); order_no = c3.text_input("Production Order No")
        fg_item = c1.selectbox("FG Item", get_stock_items()); material_cost = c2.number_input("Material Cost", min_value=0.0, value=0.0, step=100.0); labour_cost = c3.number_input("Labour Cost", min_value=0.0, value=0.0, step=100.0)
        overhead_cost = c1.number_input("Overhead Cost", min_value=0.0, value=0.0, step=100.0); qty = c2.number_input("Qty", min_value=0.0, value=1.0, step=1.0); total_cost = material_cost + labour_cost + overhead_cost; cost_per_unit = total_cost / qty if qty else 0; remarks = c3.text_input("Remarks")
        st.info(f"Total Cost: {total_cost:,.2f} | Cost Per Unit: {cost_per_unit:,.2f}")
        if st.form_submit_button("Save Production Costing", use_container_width=True):
            insert_row("production_costing", {"costing_no":costing_no,"costing_date":str(costing_date),"order_no":order_no,"fg_item":fg_item,"material_cost":material_cost,"labour_cost":labour_cost,"overhead_cost":overhead_cost,"total_cost":total_cost,"qty":qty,"cost_per_unit":cost_per_unit,"remarks":remarks,"created_by":current_user()}); st.rerun()
    show_table_with_edit_delete("production_costing", load_table("production_costing", 1000), "Production Costing Register")

def mrp_module():
    simple_module_form("mrp", "Material Requirement Planning (MRP)", [("plan_no", "Plan No", "text"), ("plan_date", "Plan Date", "date"), ("fg_item", "FG Item", get_stock_items()), ("required_qty", "Required FG Qty", "number"), ("bom_no", "BOM No", _bom_no_list()), ("rm_item", "Raw Material", get_stock_items()), ("rm_required_qty", "RM Required Qty", "number"), ("available_qty", "Available Qty", "number"), ("shortage_qty", "Shortage Qty", "number"), ("remarks", "Remarks", "text")], "section-inv")

def project_accounting_module():
    show_header("Project Accounting", "section-accounts")
    with st.form("project_accounting_form"):
        c1,c2,c3=st.columns(3); project_name=c1.text_input("Project Name"); project_code=c2.text_input("Project Code"); customer_name=c3.selectbox("Customer", get_ledger_names("Sundry Debtors")); income=c1.number_input("Project Income", min_value=0.0, value=0.0, step=1000.0); expense=c2.number_input("Project Expense", min_value=0.0, value=0.0, step=1000.0); profit=income-expense; status=c3.selectbox("Status", ["Open", "In Progress", "Completed", "Closed"]); remarks=st.text_input("Remarks")
        st.info(f"Project Profit: {profit:,.2f}")
        if st.form_submit_button("Save Project Accounting", use_container_width=True):
            insert_row("project_accounting", {"project_name":project_name,"project_code":project_code,"customer_name":customer_name,"income":income,"expense":expense,"profit":profit,"status":status,"remarks":remarks,"created_by":current_user()}); st.rerun()
    show_table_with_edit_delete("project_accounting", load_table("project_accounting", 1000), "Project Accounting Register")

def amc_subscription_module():
    simple_module_form("amc_subscriptions", "AMC / Subscription Management", [("plan_name", "Plan Name", ["Trial", "Basic", "Standard", "Professional", "Enterprise"]), ("client_name", "Client Name", "text"), ("start_date", "Start Date", "date"), ("expiry_date", "Expiry Date", "date"), ("no_of_users", "No of Users", "number"), ("storage_limit_mb", "Storage Limit MB", "number"), ("amount", "Amount", "number"), ("renewal_status", "Renewal Status", ["Active", "Due Soon", "Expired", "Renewed"]), ("remarks", "Remarks", "text")], "section-admin")

def support_ticket_module():
    simple_module_form("support_tickets", "Ticket / Support Desk", [("ticket_no", "Ticket No", "text"), ("ticket_date", "Ticket Date", "date"), ("raised_by", "Raised By", "text"), ("subject", "Subject", "text"), ("priority", "Priority", ["Low", "Medium", "High", "Urgent"]), ("status", "Status", ["Open", "In Progress", "Resolved", "Closed"]), ("assigned_to", "Assigned To", "text"), ("remarks", "Remarks", "text")], "section-admin")

def license_manager_module():
    simple_module_form("license_manager", "License Manager", [("license_key", "License Key", "text"), ("client_name", "Client Name", "text"), ("machine_id", "Machine ID", "text"), ("start_date", "Start Date", "date"), ("expiry_date", "Expiry Date", "date"), ("status", "Status", ["Active", "Expired", "Blocked", "Trial"]), ("remarks", "Remarks", "text")], "section-admin")


# ---------- ROLE-WISE PERMISSION CONTROL / CLIENT AUTHORIZATION ----------
ERP_MODULES = [
    "Dashboard",
    "Client Master", "User Management", "Role Permission Control", "Employee Master",
    "Company Profile", "Financial Year Master", "Cost Center Master", "Document Series", "GST Settings",
    "Ledger Group Master", "Ledger Master", "Stock Group Master", "Stock Ledger Master",
    "Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation", "Appointments",
    "Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher",
    "Bill of Material", "Production Order", "Production Entry", "Consumption Entry", "Finished Goods Entry", "Production Costing", "Material Requirement Planning",
    "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Fixed Assets", "Accounting Entries",
    "Project Accounting", "Quotation", "Support Desk",
    "Registers / Reports", "Import Center", "Audit Log", "Calculation Book",
]

SUPER_ADMIN_ONLY_MODULES = {
    "Client Master", "License Manager", "AMC / Subscription", "Workflow Engine", "Notification Center",
    "Dashboard Analytics", "Budget vs Actual", "Bank Reconciliation", "Document Management", "Purchase Cycle", "Sales Cycle",
    "Advanced Asset Management", "Digital Audit", "Calculator", "Multi Company / Branch", "Offline Sync Engine",
    "ERP Control Center", "PWA Mobile App"
}

TABLE_KEY_TO_MODULE = {
    "clients": "Client Master", "users": "User Management", "role_permissions": "Role Permission Control",
    "employees": "Employee Master", "company_profiles": "Company Profile", "financial_years": "Financial Year Master",
    "cost_centers": "Cost Center Master", "document_series": "Document Series", "gst_settings": "GST Settings",
    "ledger_groups": "Ledger Group Master", "ledgers": "Ledger Master", "stock_groups": "Stock Group Master", "stock_ledgers": "Stock Ledger Master",
    "attendance": "Attendance Management", "attendance_visits": "Attendance Management", "inout": "IN / OUT Register", "visitors": "Visitor Register",
    "tasks": "Task Delegation", "appointments": "Appointments", "stock_raw": "Raw Material Stock", "stock_fg": "Finished Goods Stock",
    "stock_wip": "WIP Stock", "stock_vouchers": "Stock Voucher", "bom_headers": "Bill of Material", "bom_lines": "Bill of Material",
    "production_orders": "Production Order", "production_entries": "Production Entry", "consumption_entries": "Consumption Entry", "fg_entries": "Finished Goods Entry",
    "production_costing": "Production Costing", "mrp": "Material Requirement Planning", "sales": "Sales GST Invoice", "purchase": "Purchase GST Invoice",
    "expenses": "Expense GST", "service_vouchers": "Service Voucher", "fixed_assets": "Fixed Assets", "accounting_entries": "Accounting Entries",
    "accounting_entry_lines": "Accounting Entries", "project_accounting": "Project Accounting", "quotation_requirements": "Quotation", "quotation_business_users": "Quotation",
    "quotation_access": "Quotation", "quotations": "Quotation", "support_tickets": "Support Desk", "audit_logs": "Audit Log", "import_logs": "Import Center",
    "calculation_books": "Calculation Book"
}


# ---------- CLIENT FEATURE SECURITY ----------
MODULE_FEATURE_FLAGS = {
    "Dashboard": None,

    # Admin/internal
    "Client Master": "__client_super_admin__",
    "User Management": "__client_admin_normal__",
    "Role Permission Control": "__client_admin_normal__",
    "Employee Master": "allow_master_group",

    # Masters
    "Company Profile": "allow_master_group",
    "Financial Year Master": "allow_master_group",
    "Cost Center Master": "allow_master_group",
    "Document Series": "allow_master_group",
    "GST Settings": "allow_master_group",
    "Ledger Group Master": "allow_master_group",
    "Ledger Master": "allow_master_group",
    "Stock Group Master": "allow_master_group",
    "Stock Ledger Master": "allow_master_group",

    # HR
    "Attendance Management": "allow_attendance",
    "IN / OUT Register": "allow_inout",
    "Visitor Register": "allow_visitor",
    "Task Delegation": "allow_task",
    "Appointments": "allow_appointment",

    # Inventory
    "Raw Material Stock": "allow_stock_raw",
    "Finished Goods Stock": "allow_stock_fg",
    "WIP Stock": "allow_stock_wip",
    "Stock Voucher": "__stock_any__",

    # Manufacturing
    "Bill of Material": "allow_manufacturing",
    "Production Order": "allow_manufacturing",
    "Production Entry": "allow_manufacturing",
    "Consumption Entry": "allow_manufacturing",
    "Finished Goods Entry": "allow_manufacturing",
    "Production Costing": "allow_manufacturing",
    "Material Requirement Planning": "allow_manufacturing",

    # Accounts
    "Sales GST Invoice": "allow_sales",
    "Purchase GST Invoice": "allow_purchase",
    "Expense GST": "allow_expense",
    "Service Voucher": "allow_service_voucher",
    "Fixed Assets": "allow_fixed_assets",
    "Accounting Entries": "allow_accounting",

    # Optional modules
    "Project Accounting": "allow_project_accounting",
    "Quotation": "allow_quotation",
    "Support Desk": "allow_support",
    "AMC / Subscription": "allow_subscription",
    "License Manager": "allow_license_manager",

    # Reports/Tools
    "Registers / Reports": "__report_any__",
    "Import Center": "__import_any__",
    "Audit Log": "__client_admin_normal__",
    "Calculation Book": "__client_admin_normal__",

    # Super Admin only
    "Workflow Engine": "__super_admin__",
    "Notification Center": "__super_admin__",
    "Dashboard Analytics": "__super_admin__",
    "Budget vs Actual": "__super_admin__",
    "Bank Reconciliation": "__super_admin__",
    "Document Management": "__super_admin__",
    "Purchase Cycle": "__super_admin__",
    "Sales Cycle": "__super_admin__",
    "Advanced Asset Management": "__super_admin__",
    "Digital Audit": "__super_admin__",
    "Multi Company / Branch": "__super_admin__",
    "Offline Sync Engine": "__super_admin__",
    "ERP Control Center": "__super_admin__",
    "PWA Mobile App": "__super_admin__",
    "Calculator": "__super_admin__",
}

def _normal_feature_enabled_from_session():
    return any([
        st.session_state.get("allow_master_group", False),
        st.session_state.get("allow_attendance", False),
        st.session_state.get("allow_inout", False),
        st.session_state.get("allow_visitor", False),
        st.session_state.get("allow_task", False),
        st.session_state.get("allow_appointment", False),
        st.session_state.get("allow_stock_raw", False),
        st.session_state.get("allow_stock_fg", False),
        st.session_state.get("allow_stock_wip", False),
        st.session_state.get("allow_sales", False),
        st.session_state.get("allow_purchase", False),
        st.session_state.get("allow_expense", False),
        st.session_state.get("allow_service_voucher", False),
        st.session_state.get("allow_fixed_assets", False),
        st.session_state.get("allow_accounting", False),
        st.session_state.get("allow_manufacturing", False),
        st.session_state.get("allow_project_accounting", False),
        st.session_state.get("allow_support", False),
        st.session_state.get("allow_subscription", False),
    ])

def _core_feature_enabled_from_session():
    """Core ERP features only. Optional enterprise flags do not count.
    This prevents old/default TRUE optional columns from showing Manufacturing/Projects/etc.
    If a client is given only Quotation, only Quotation will show.
    """
    return any([
        st.session_state.get("allow_master_group", False),
        st.session_state.get("allow_attendance", False),
        st.session_state.get("allow_inout", False),
        st.session_state.get("allow_visitor", False),
        st.session_state.get("allow_task", False),
        st.session_state.get("allow_appointment", False),
        st.session_state.get("allow_stock_raw", False),
        st.session_state.get("allow_stock_fg", False),
        st.session_state.get("allow_stock_wip", False),
        st.session_state.get("allow_sales", False),
        st.session_state.get("allow_purchase", False),
        st.session_state.get("allow_expense", False),
        st.session_state.get("allow_service_voucher", False),
        st.session_state.get("allow_fixed_assets", False),
        st.session_state.get("allow_accounting", False),
        st.session_state.get("allow_excel_upload", False),
        st.session_state.get("allow_google_sheet_import", False),
    ])


def _quotation_only_from_session():
    return bool(st.session_state.get("allow_quotation", False)) and not _core_feature_enabled_from_session()


def module_enabled_for_current_client(module_name):
    """Client-wise feature gate. If client is assigned only Quotation, nothing else appears."""
    if is_super_admin():
        return True
    if _quote_role():
        return module_name == "Quotation"
    # Highest priority security rule:
    # If client is assigned only Quotation, no Dashboard/Admin/Projects/Manufacturing/Reports/Tools must appear.
    if _quotation_only_from_session():
        return module_name == "Quotation"

    flag = MODULE_FEATURE_FLAGS.get(module_name)

    if flag is None:
        return _normal_feature_enabled_from_session() or st.session_state.get("allow_quotation", False)

    if flag == "__super_admin__":
        return False

    if flag == "__client_super_admin__":
        return st.session_state.get("role") == "Client Super Admin" and _normal_feature_enabled_from_session()

    if flag == "__client_admin_normal__":
        return st.session_state.get("role") in ["Client Super Admin", "Admin"] and _normal_feature_enabled_from_session()

    if flag == "__stock_any__":
        return any([st.session_state.get("allow_stock_raw", False), st.session_state.get("allow_stock_fg", False), st.session_state.get("allow_stock_wip", False)])

    if flag == "__report_any__":
        return _normal_feature_enabled_from_session() or st.session_state.get("allow_quotation", False)

    if flag == "__import_any__":
        return st.session_state.get("allow_excel_upload", False) or st.session_state.get("allow_google_sheet_import", False)

    return bool(st.session_state.get(flag, False))

def _client_feature_row(client_code):
    try:
        df = safe_df(supabase.table("clients").select("*").eq("client_code", client_code).limit(1).execute().data)
        if df.empty:
            return {}
        return df.iloc[0].to_dict()
    except Exception:
        return {}

def _row_bool(row, flag):
    try:
        return bool(row.get(flag, False)) if pd.notna(row.get(flag, None)) else False
    except Exception:
        return False

def _normal_feature_enabled_from_row(row):
    return any([
        _row_bool(row, "allow_master_group"),
        _row_bool(row, "allow_attendance"),
        _row_bool(row, "allow_inout"),
        _row_bool(row, "allow_visitor"),
        _row_bool(row, "allow_task"),
        _row_bool(row, "allow_appointment"),
        _row_bool(row, "allow_stock_raw"),
        _row_bool(row, "allow_stock_fg"),
        _row_bool(row, "allow_stock_wip"),
        _row_bool(row, "allow_sales"),
        _row_bool(row, "allow_purchase"),
        _row_bool(row, "allow_expense"),
        _row_bool(row, "allow_service_voucher"),
        _row_bool(row, "allow_fixed_assets"),
        _row_bool(row, "allow_accounting"),
        _row_bool(row, "allow_manufacturing"),
        _row_bool(row, "allow_project_accounting"),
        _row_bool(row, "allow_support"),
        _row_bool(row, "allow_subscription"),
    ])

def _core_feature_enabled_from_row(row):
    return any([
        _row_bool(row, "allow_master_group"),
        _row_bool(row, "allow_attendance"),
        _row_bool(row, "allow_inout"),
        _row_bool(row, "allow_visitor"),
        _row_bool(row, "allow_task"),
        _row_bool(row, "allow_appointment"),
        _row_bool(row, "allow_stock_raw"),
        _row_bool(row, "allow_stock_fg"),
        _row_bool(row, "allow_stock_wip"),
        _row_bool(row, "allow_sales"),
        _row_bool(row, "allow_purchase"),
        _row_bool(row, "allow_expense"),
        _row_bool(row, "allow_service_voucher"),
        _row_bool(row, "allow_fixed_assets"),
        _row_bool(row, "allow_accounting"),
        _row_bool(row, "allow_excel_upload"),
        _row_bool(row, "allow_google_sheet_import"),
    ])


def _quotation_only_from_row(row):
    return _row_bool(row, "allow_quotation") and not _core_feature_enabled_from_row(row)


def module_enabled_for_client_code(module_name, client_code):
    """Used by Role Permission Control. Shows only modules enabled for selected client."""
    if str(client_code).upper() == "RBM" and is_super_admin():
        return True

    row = _client_feature_row(client_code)
    if _quotation_only_from_row(row):
        return module_name == "Quotation"

    flag = MODULE_FEATURE_FLAGS.get(module_name)

    if flag is None:
        return _normal_feature_enabled_from_row(row) or _row_bool(row, "allow_quotation")

    if flag == "__super_admin__":
        return False

    if flag == "__client_super_admin__":
        return _normal_feature_enabled_from_row(row)

    if flag == "__client_admin_normal__":
        return _normal_feature_enabled_from_row(row)

    if flag == "__stock_any__":
        return any([_row_bool(row, "allow_stock_raw"), _row_bool(row, "allow_stock_fg"), _row_bool(row, "allow_stock_wip")])

    if flag == "__report_any__":
        return _normal_feature_enabled_from_row(row) or _row_bool(row, "allow_quotation")

    if flag == "__import_any__":
        return _row_bool(row, "allow_excel_upload") or _row_bool(row, "allow_google_sheet_import")

    return _row_bool(row, flag)


PERMISSION_ACTIONS = ["view", "add", "edit", "delete", "reverse", "approve", "print", "export"]

def default_permission(module_name, action):
    role = st.session_state.get("role", "")
    if role in ["Developer", "Super Admin"]:
        return True
    if module_name in SUPER_ADMIN_ONLY_MODULES or module_name in DEVELOPER_ONLY_MODULES:
        return False
    # Client Super Admin gets full authority for every module enabled for his own client/company.
    if role == "Client Super Admin":
        return True
    if role == "Admin":
        return True
    if role == "Accounts User":
        return module_name in GROUP_MODULES.get("Accounts", []) and action in ["view", "add", "edit", "print", "export"]
    if role == "HR User":
        return module_name in GROUP_MODULES.get("HR", []) and action in ["view", "add", "edit", "print", "export"]
    if role == "Inventory User":
        return module_name in GROUP_MODULES.get("Inventory", []) and action in ["view", "add", "edit", "print", "export"]
    if role == "Quotation User":
        return module_name in GROUP_MODULES.get("Quotation", []) and action in ["view", "add", "print", "export"]
    if role == "User":
        return action in ["view", "print", "export"]
    return action == "view"

def has_permission(module_name, action="view"):
    try:
        if is_super_admin():
            return True
        if module_name in SUPER_ADMIN_ONLY_MODULES or module_name in DEVELOPER_ONLY_MODULES:
            return False
        # Client Super Admin must always get full access to all modules enabled for his company.
        if st.session_state.get("role") == "Client Super Admin":
            return module_enabled_for_current_client(module_name)
        action = str(action).lower().strip()
        if action not in PERMISSION_ACTIONS:
            return False
        role_name = str(st.session_state.get("role", "User"))
        username = str(st.session_state.get("username", ""))
        client_code = get_client_code()
        col = f"can_{action}"

        # First priority: Role Based Security means USERNAME wise security.
        # If a permission row exists for the logged-in username, it overrides role permission.
        try:
            udata = supabase.table("user_permissions").select("*").eq("client_code", client_code).eq("username", username).eq("module_name", module_name).limit(1).execute().data
            udf = safe_df(udata)
            if not udf.empty and col in udf.columns:
                return bool(udf.iloc[0].get(col, default_permission(module_name, action)))
        except Exception:
            pass

        data = supabase.table("role_permissions").select("*").eq("client_code", client_code).eq("role_name", role_name).eq("module_name", module_name).limit(1).execute().data
        dfp = safe_df(data)
        if dfp.empty:
            return default_permission(module_name, action)
        return bool(dfp.iloc[0].get(col, default_permission(module_name, action))) if col in dfp.columns else default_permission(module_name, action)
    except Exception:
        return default_permission(module_name, action)

def has_key_permission(key, action="view"):
    return has_permission(TABLE_KEY_TO_MODULE.get(key, key), action)

def filter_modules_by_permission(modules):
    if is_super_admin():
        return modules or ["No module available"]
    allowed = []
    for m in modules:
        if m == "No module available":
            continue
        if m in SUPER_ADMIN_ONLY_MODULES or m in DEVELOPER_ONLY_MODULES:
            continue
        if module_enabled_for_current_client(m) and has_permission(m, "view"):
            allowed.append(m)
    return allowed or ["No module available"]


def role_based_security_control():
    """Role Based Security screen: same as Role Permission Control, but Select Role dropdown shows USERNAMES."""
    show_header("Role Based Security", "section-admin")
    if st.session_state.get("role") not in ["Developer", "Super Admin", "Client Super Admin", "Admin"]:
        st.warning("Only Developer, Super Admin, Client Super Admin or Admin can access Role Based Security.")
        return

    st.info("Role Based Security = username/login wise permission. Screen same as Role Permission Control, but Select Role dropdown shows username created in User Management.")

    # Select client exactly like Role Permission Control
    if is_super_admin():
        clients_df = load_table("clients", 1000)
        client_codes = clients_df["client_code"].dropna().astype(str).tolist() if not clients_df.empty and "client_code" in clients_df.columns else ["RBM"]
        if "RBM" not in client_codes:
            client_codes = ["RBM"] + client_codes
        selected_client = st.selectbox("Select Client", client_codes, key="rbs_client")
    else:
        selected_client = get_client_code()
        st.selectbox("Select Client", [selected_client], key="rbs_client_fixed", disabled=True)

    # Select Role label remains same, but options are USERNAME only
    users_df = load_table("users", 5000)
    users_df = safe_df(users_df)
    if not users_df.empty and "client_code" in users_df.columns:
        users_df = users_df[users_df["client_code"].astype(str) == str(selected_client)]
    if not is_super_admin() and not users_df.empty and "role" in users_df.columns:
        users_df = users_df[~users_df["role"].astype(str).isin(["Developer", "Super Admin"])]
    if users_df.empty or "username" not in users_df.columns:
        st.warning("No username found for this client. First create username in User Management.")
        return

    usernames = users_df["username"].dropna().astype(str).unique().tolist()
    if not usernames:
        st.warning("No username found for this client. First create username in User Management.")
        return
    selected_username = st.selectbox("Select Role", usernames, key="rbs_username_select")

    user_role = ""
    if "role" in users_df.columns:
        rr = users_df[users_df["username"].astype(str) == str(selected_username)]
        if not rr.empty:
            user_role = str(rr.iloc[0].get("role", ""))
    if user_role:
        st.caption(f"Selected Username: {selected_username} | Actual Role: {user_role}")

    try:
        existing = safe_df(
            supabase.table("user_permissions")
            .select("*")
            .eq("client_code", selected_client)
            .eq("username", selected_username)
            .execute().data
        )
    except Exception:
        st.error("Supabase table user_permissions missing. Run supabase_required_patch.sql once in Supabase SQL Editor.")
        existing = pd.DataFrame()

    perm_rows = []
    with st.form("role_based_security_username_form"):
        st.markdown("### Module Permissions")
        header = st.columns([2.5,1,1,1,1,1,1,1,1])
        header[0].markdown("**Module**")
        for i, act in enumerate(PERMISSION_ACTIONS, start=1):
            header[i].markdown(f"**{act.title()}**")

        for module in ERP_MODULES:
            if module == "No module available":
                continue
            if not module_enabled_for_client_code(module, selected_client):
                continue
            if (not is_super_admin()) and module in SUPER_ADMIN_ONLY_MODULES:
                continue
            current = existing[existing["module_name"].astype(str) == str(module)] if not existing.empty and "module_name" in existing.columns else pd.DataFrame()
            cols = st.columns([2.5,1,1,1,1,1,1,1,1])
            cols[0].write(module)
            row = {"module_name": module}
            for i, act in enumerate(PERMISSION_ACTIONS, start=1):
                colname = f"can_{act}"
                default_val = bool(current.iloc[0].get(colname, default_permission(module, act))) if (not current.empty and colname in current.columns) else default_permission(module, act)
                row[colname] = cols[i].checkbox("", value=default_val, key=f"rbs_{selected_client}_{selected_username}_{module}_{act}")
            perm_rows.append(row)

        save_btn = st.form_submit_button("Save Role Based Security", use_container_width=True)

    if save_btn:
        try:
            supabase.table("user_permissions").delete().eq("client_code", selected_client).eq("username", selected_username).execute()
            rows = []
            for r in perm_rows:
                rec = {"client_code": selected_client, "username": selected_username, "created_by": current_user()}
                rec.update(r)
                rows.append(rec)
            if rows:
                supabase.table("user_permissions").insert(rows).execute()
            write_audit_log("Role Based Security", "UPDATE", "", f"Saved username wise permission for {selected_client} / {selected_username}")
            st.success("Role Based Security saved successfully for selected username.")
            st.rerun()
        except Exception as e:
            st.error(f"Unable to save Role Based Security. Run updated SQL patch if needed. Error: {e}")

    st.divider()
    try:
        show_table_with_edit_delete("user_permissions", load_table("user_permissions", 2000), "Saved Role Based Security")
    except Exception:
        st.info("Saved Role Based Security list will show after user_permissions table is created.")

def role_permission_control():
    show_header("Role-wise Permission Control", "section-admin")
    if st.session_state.get("role") not in ["Developer", "Super Admin", "Client Super Admin", "Admin"]:
        st.warning("Only Developer, Super Admin, Client Super Admin or Admin can access Role Permission Control.")
        return
    if is_super_admin():
        clients_df = load_table("clients", 1000)
        client_codes = clients_df["client_code"].dropna().astype(str).tolist() if not clients_df.empty else ["RBM"]
        if "RBM" not in client_codes:
            client_codes = ["RBM"] + client_codes
        selected_client = st.selectbox("Select Client", client_codes, key="perm_client")
    else:
        selected_client = get_client_code()
        st.info(f"Permission setting for your own business only: {selected_client}")
    current_role = st.session_state.get("role", "")
    if current_role in ["Developer", "Super Admin"]:
        assignable_roles = ["Client Super Admin", "Admin", "User", "Quotation User", "Accounts User", "HR User", "Inventory User", "Manager", "Approver", "Viewer"]
    elif current_role == "Client Super Admin":
        assignable_roles = ["Admin", "User", "Quotation User", "Accounts User", "HR User", "Inventory User", "Manager", "Approver", "Viewer"]
    else:
        assignable_roles = ["User", "Quotation User", "Accounts User", "HR User", "Inventory User", "Viewer"]
    role_name = st.selectbox("Select Role", assignable_roles, key="perm_role")
    existing = safe_df(supabase.table("role_permissions").select("*").eq("client_code", selected_client).eq("role_name", role_name).execute().data)
    perm_rows = []
    with st.form("role_permission_form"):
        st.markdown("### Module Permissions")
        header = st.columns([2.5,1,1,1,1,1,1,1,1])
        header[0].markdown("**Module**")
        for i, act in enumerate(PERMISSION_ACTIONS, start=1):
            header[i].markdown(f"**{act.title()}**")
        for module in ERP_MODULES:
            # Show only modules enabled for the selected client.
            # Example: if the client has only Quotation enabled, only Quotation appears here.
            if not module_enabled_for_client_code(module, selected_client):
                continue
            # Do not let client admins assign RBM internal/super-admin-only modules.
            if (not is_super_admin()) and module in SUPER_ADMIN_ONLY_MODULES and module != "Client Master":
                continue
            current = existing[existing["module_name"].astype(str) == module] if not existing.empty and "module_name" in existing.columns else pd.DataFrame()
            cols = st.columns([2.5,1,1,1,1,1,1,1,1])
            cols[0].write(module)
            row = {"module_name": module}
            for i, act in enumerate(PERMISSION_ACTIONS, start=1):
                colname = f"can_{act}"
                default_val = bool(current.iloc[0].get(colname, default_permission(module, act))) if not current.empty and colname in current.columns else default_permission(module, act)
                row[colname] = cols[i].checkbox("", value=default_val, key=f"perm_{selected_client}_{role_name}_{module}_{act}")
            perm_rows.append(row)
        if st.form_submit_button("Save Role Permissions", use_container_width=True):
            supabase.table("role_permissions").delete().eq("client_code", selected_client).eq("role_name", role_name).execute()
            rows = []
            for r in perm_rows:
                rec = {"client_code": selected_client, "role_name": role_name, "created_by": current_user()}
                rec.update(r)
                rows.append(rec)
            if rows:
                supabase.table("role_permissions").insert(rows).execute()
            write_audit_log("Role Permission Control", "UPDATE", "", f"Saved role permissions for {selected_client} / {role_name}")
            st.success("Role permissions saved successfully.")
            st.rerun()
    st.divider()
    show_table_with_edit_delete("role_permissions", load_table("role_permissions", 2000), "Saved Role Permissions")

# ---------- MAIN MENU ----------
def get_menu_modules(group):
    """Online menu based on latest offline desktop group/module structure."""
    modules = list(ONLINE_MODULE_GROUPS.get(group, []))

    # Client cannot see developer-only modules.
    modules = [m for m in modules if role_can_see_module(m)]

    # For normal client login, show group only when its client feature is enabled.
    # Developer/Super Admin see all modules.
    if not is_developer_or_super_admin() and group != "Dashboard":
        if not group_enabled_for_client(group):
            modules = []

    # Role permission table support, if available.
    modules = filter_modules_by_permission(modules)
    return modules or ["Dashboard"]


def build_group_list():
    """Latest offline desktop groups for online RBM ERP."""
    groups = []
    for g in ONLINE_MODULE_GROUPS.keys():
        if g == "Dashboard":
            groups.append(g)
            continue
        if group_enabled_for_client(g):
            visible_modules = [m for m in ONLINE_MODULE_GROUPS[g] if role_can_see_module(m)]
            if visible_modules:
                groups.append(g)

    # Quotation-only user fallback.
    if _quote_role() or ((not is_developer_or_super_admin()) and _quotation_only_from_session()):
        return ["Quotation"]

    return groups or ["Dashboard"]


def render_custom_menu():
    st.markdown("""
    <div class='erp-box'>
      <div class='erp-name'>RBM AI</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='erp-box'>
      <div class='erp-small'><b>Name:</b> {st.session_state.get('client_name','RBM')}</div>
      <div class='erp-small'><b>Code:</b> {get_client_code()}</div>
      <div class='erp-small'><b>Role:</b> {st.session_state.get('role','')}</div>
      <div class='erp-small'><b>User:</b> {st.session_state.get('full_name','')}</div>
      <div class='erp-small'><b>Date:</b> {india_now().strftime('%d-%m-%Y')} | IST</div>
    </div>
    """, unsafe_allow_html=True)

    groups = build_group_list()

    # Keep previously selected group if it is still allowed for this client.
    if st.session_state.get("active_group") in groups:
        default_group_index = groups.index(st.session_state.get("active_group"))
    else:
        default_group_index = 0

    group = st.selectbox("Group", groups, index=default_group_index, key="menu_group")
    modules = get_menu_modules(group)

    # Keep previously selected module if it belongs to the selected group.
    previous_choice = st.session_state.get("active_choice", st.session_state.get("menu_module"))
    if previous_choice in modules:
        default_module_index = modules.index(previous_choice)
    else:
        default_module_index = 0

    display_modules = [module_label(m) for m in modules]
    default_display_index = default_module_index if default_module_index < len(display_modules) else 0

    display_choice = st.radio("Module", display_modules, index=default_display_index, key="menu_module")
    choice = strip_module_label(display_choice)

    # Save active page before hiding, so the same page stays open after hide.
    st.session_state["active_group"] = group
    st.session_state["active_choice"] = choice

    c1, c2 = st.columns(2)
    if c1.button("◀ Hide", use_container_width=True, key="custom_hide_menu"):
        st.session_state["active_group"] = group
        st.session_state["active_choice"] = choice
        st.session_state["sidebar_open"] = False
        st.rerun()
    if c2.button("Logout", use_container_width=True, key="custom_logout"):
        st.session_state.clear()
        st.rerun()

    return group, choice



def _generic_options(label):
    base = {
        "status": ["Active", "Inactive", "Pending", "Completed", "Closed", "Cancelled"],
        "priority": ["High", "Medium", "Low"],
        "parking_status": ["Parked", "Posted"],
        "approval_status": ["Pending", "Approved", "Rejected"],
        "reminder_type": ["Payment Follow-up", "Receivable Follow-up", "Payable Follow-up", "GST Due Date", "TDS Due Date", "Salary Reminder", "License Expiry", "Task Reminder", "Meeting Reminder"],
        "repeat_type": ["One Time", "Daily", "Weekly", "Monthly", "Quarterly", "Yearly"],
        "check_type": ["Blank Records", "Duplicate Records", "Invalid Date", "Invalid Amount", "Missing Company Code", "Missing GST No", "Opening Balance Mismatch", "Stock Negative", "Voucher Number Gap", "All Checks"],
        "backup_type": ["Full Backup", "Data Backup", "Report Backup", "Client Backup", "Before Update Backup", "Restore Backup"],
        "export_type": ["CSV", "Excel", "PDF", "Full Data ZIP", "Module Wise Export"],
        "import_type": ["CSV", "Excel", "Opening Balance", "Stock Import", "Ledger Import", "Employee Import"],
        "voucher_type": ["Contra", "Payment", "Receipt", "Journal", "Sales", "Purchase", "Credit Note", "Debit Note", "Purchase Order", "Sales Order", "Receipt Note", "Delivery Note", "Stock Journal", "Physical Stock", "Material In", "Material Out"],
        "payment_mode": ["Cash", "Bank", "Cheque", "NEFT", "RTGS", "IMPS", "UPI", "Card", "Online"],
        "shift": ["General", "Morning", "Evening", "Night", "Rotational"],
        "module_name": list(ONLINE_MODULE_GROUPS.keys()) if 'ONLINE_MODULE_GROUPS' in globals() else ["Master","Sales","Purchase","Inventory","Accounts"],
    }
    return base.get(label.lower())

_GENERIC_MODULE_FIELDS = {
    "User Password Change": [("company_code","Company Code","company"),("username","Username","user"),("old_password","Old Password","password"),("new_password","New Password","password"),("confirm_password","Confirm Password","password"),("remarks","Remarks","text")],
    "Data Purge Control": [("company_code","Company Code","company"),("request_date","Request Date","date"),("module_name","Module Name","module_name"),("from_date","From Date","date"),("to_date","To Date","date"),("records_to_purge","Records To Purge","number"),("purge_status","Purge Status","status"),("requested_by","Requested By","text"),("approved_by","Approved By","text"),("remarks","Remarks","text")],
    "Data Locking Period": [("company_code","Company Code","company"),("module_name","Module Name","module_name"),("lock_from_date","Lock From Date","date"),("lock_to_date","Lock To Date","date"),("lock_status","Lock Status","status"),("reason","Reason","text")],
    "Mandatory Field Settings": [("company_code","Company Code","company"),("module_name","Module Name","module_name"),("field_name","Field Name","text"),("is_mandatory","Is Mandatory","bool"),("status","Status","status"),("remarks","Remarks","text")],
    "Client Group Permission": [("company_code","Company Code","company"),("group_name","Group Name","group"),("allowed","Allowed","bool"),("status","Status","status"),("remarks","Remarks","text")],
    "Client Module Permission": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name"),("allowed","Allowed","bool"),("status","Status","status"),("remarks","Remarks","text")],
    "CRM Leads": [("company_code","Company Code","company"),("lead_date","Lead Date","date"),("lead_name","Lead Name","text"),("company_name","Company Name","text"),("mobile","Mobile","text"),("email","Email","text"),("source","Source","text"),("status","Status","status"),("next_followup_date","Next Follow-up Date","date"),("remarks","Remarks","text")],
    "CRM Followups": [("company_code","Company Code","company"),("followup_date","Follow-up Date","date"),("lead_name","Lead / Customer Name","text"),("followup_type","Follow-up Type","text"),("next_date","Next Date","date"),("assigned_to","Assigned To","user"),("status","Status","status"),("remarks","Remarks","text")],
    "CRM Customers": [("company_code","Company Code","company"),("customer_code","Customer Code","text"),("customer_name","Customer Name","text"),("mobile","Mobile","text"),("email","Email","text"),("gst_no","GST No","text"),("city","City","text"),("status","Status","status"),("remarks","Remarks","text")],
    "CRM Opportunities": [("company_code","Company Code","company"),("opportunity_no","Opportunity No","text"),("customer_name","Customer Name","text"),("opportunity_value","Opportunity Value","number"),("stage","Stage","text"),("expected_closing_date","Expected Closing Date","date"),("assigned_to","Assigned To","user"),("status","Status","status"),("remarks","Remarks","text")],
    "Customer Portal Access": [("company_code","Company Code","company"),("customer_name","Customer Name","text"),("username","Username","text"),("password","Password","password"),("mobile","Mobile","text"),("email","Email","text"),("access_status","Access Status","status"),("remarks","Remarks","text")],
    "Payroll Salary Structure": [("company_code","Company Code","company"),("employee_name","Employee Name","employee"),("basic_salary","Basic Salary","number"),("hra","HRA","number"),("allowance","Allowance","number"),("pf","PF","number"),("esi","ESI","number"),("gross_salary","Gross Salary","number"),("net_salary","Net Salary","number"),("status","Status","status")],
    "Payroll Processing": [("company_code","Company Code","company"),("salary_month","Salary Month","text"),("employee_name","Employee Name","employee"),("working_days","Working Days","number"),("paid_days","Paid Days","number"),("gross_salary","Gross Salary","number"),("deduction","Deduction","number"),("net_salary","Net Salary","number"),("payment_mode","Payment Mode","payment_mode"),("status","Status","status")],
    "Payroll Payslip": [("company_code","Company Code","company"),("payslip_no","Payslip No","text"),("salary_month","Salary Month","text"),("employee_name","Employee Name","employee"),("gross_salary","Gross Salary","number"),("deduction","Deduction","number"),("net_salary","Net Salary","number"),("payment_date","Payment Date","date"),("status","Status","status")],
    "Barcode Master": [("company_code","Company Code","company"),("barcode_no","Barcode No","text"),("item_name","Item Name","stock_item"),("item_code","Item Code","text"),("batch_no","Batch No","text"),("mfg_date","MFG Date","date"),("expiry_date","Expiry Date","date"),("mrp","MRP","number"),("selling_rate","Selling Rate","number"),("qty","Qty","number"),("status","Status","status")],
    "Barcode Print Log": [("company_code","Company Code","company"),("print_date","Print Date","date"),("barcode_no","Barcode No","text"),("item_name","Item Name","stock_item"),("item_code","Item Code","text"),("qty_printed","Qty Printed","number"),("printed_by","Printed By","user"),("remarks","Remarks","text")],
    "Warehouse Stock": [("company_code","Company Code","company"),("warehouse_code","Warehouse Code","text"),("warehouse_name","Warehouse Name","text"),("item_name","Item Name","stock_item"),("item_code","Item Code","text"),("opening_qty","Opening Qty","number"),("inward_qty","Inward Qty","number"),("outward_qty","Outward Qty","number"),("closing_qty","Closing Qty","number"),("rate","Rate","number"),("value","Value","number")],
    "Production Planning": [("company_code","Company Code","company"),("plan_no","Plan No","text"),("plan_date","Plan Date","date"),("finished_item","Finished Item","stock_item"),("planned_qty","Planned Qty","number"),("bom_no","BOM No","bom"),("start_date","Start Date","date"),("end_date","End Date","date"),("machine_name","Machine Name","text"),("supervisor","Supervisor","employee"),("plan_status","Plan Status","status")],
    "Production Schedule": [("company_code","Company Code","company"),("schedule_no","Schedule No","text"),("schedule_date","Schedule Date","date"),("plan_no","Plan No","plan"),("shift","Shift","shift"),("machine_name","Machine Name","text"),("operator_name","Operator Name","employee"),("qty_scheduled","Qty Scheduled","number"),("status","Status","status")],
    "Capacity Planning": [("company_code","Company Code","company"),("machine_name","Machine Name","text"),("shift","Shift","shift"),("available_hours","Available Hours","number"),("planned_hours","Planned Hours","number"),("free_capacity","Free Capacity","number"),("plan_date","Plan Date","date"),("remarks","Remarks","text")],
    "Payment Receipt Voucher": [("company_code","Company Code","company"),("receipt_no","Receipt No","text"),("receipt_date","Receipt Date","date"),("customer_code","Customer Code","text"),("customer_name","Customer Name","text"),("ledger_name","Ledger Name","text"),("amount_received","Amount Received","number"),("tds_percent","TDS %","number"),("tds_deducted","TDS Deducted","number"),("net_amount","Net Amount","number"),("payment_mode","Payment Mode","payment_mode"),("remarks","Remarks","text")],
    "Bank Payment Voucher": [("company_code","Company Code","company"),("payment_no","Payment No","text"),("payment_date","Payment Date","date"),("vendor_code","Vendor Code","text"),("supplier_name","Supplier Name","text"),("ledger_name","Ledger Name","text"),("amount_paid","Amount Paid","number"),("tds_percent","TDS %","number"),("tds_deducted","TDS Deducted","number"),("net_amount","Net Amount","number"),("payment_mode","Payment Mode","payment_mode"),("remarks","Remarks","text")],
    "Purchase Order": [("company_code","Company Code","company"),("po_no","PO No","text"),("po_date","PO Date","date"),("vendor_code","Vendor Code","text"),("supplier_name","Supplier Name","text"),("item_name","Item Name","stock_item"),("qty","Qty","number"),("rate","Rate","number"),("value","Value","number"),("status","Status","status"),("remarks","Remarks","text")],
    "Receipt Note": [("company_code","Company Code","company"),("grn_no","GRN / Receipt No","text"),("grn_date","GRN Date","date"),("po_no","PO No","text"),("vendor_code","Vendor Code","text"),("supplier_name","Supplier Name","text"),("item_name","Item Name","stock_item"),("received_qty","Received Qty","number"),("status","Status","status"),("remarks","Remarks","text")],
    "Debit Note": [("company_code","Company Code","company"),("debit_note_no","Debit Note No","text"),("debit_note_date","Debit Note Date","date"),("vendor_code","Vendor Code","text"),("supplier_name","Supplier Name","text"),("reason","Reason","text"),("taxable_value","Taxable Value","number"),("cgst","CGST","number"),("sgst","SGST","number"),("igst","IGST","number"),("total_value","Total Value","number"),("remarks","Remarks","text")],
}


_SPECIAL_STORAGE_KEY = "online_generic_records"

def _company_codes():
    codes = []
    try:
        df = load_table("clients", 500)
        if not df.empty:
            for col in ["client_code", "company_code"]:
                if col in df.columns:
                    codes += [str(x) for x in df[col].dropna().unique().tolist() if str(x).strip()]
    except Exception:
        pass
    cur = get_client_code() if 'get_client_code' in globals() else st.session_state.get('client_code','RBM')
    codes = list(dict.fromkeys([cur] + codes + ["RBM", "SJM01", "CST01"]))
    return codes

def _collect_generic_values(module_name=None, column_name=None):
    vals = []
    try:
        for r in st.session_state.get(_SPECIAL_STORAGE_KEY, []):
            if module_name is None or r.get("module_name") == module_name:
                if column_name and r.get(column_name):
                    vals.append(str(r.get(column_name)))
    except Exception:
        pass
    try:
        q = supabase.table("generic_erp_records").select("module_name,data_json").limit(1000).execute().data or []
        for rec in q:
            data = rec.get("data_json") if isinstance(rec.get("data_json"), dict) else {}
            if data and (module_name is None or rec.get("module_name") == module_name or data.get("module_name") == module_name):
                if column_name and data.get(column_name):
                    vals.append(str(data.get(column_name)))
    except Exception:
        pass
    return list(dict.fromkeys([v for v in vals if str(v).strip() and str(v) != "All"]))

def _online_stock_items():
    vals = []
    try:
        vals += get_stock_items() or []
    except Exception:
        pass
    # Barcode Master and Inventory Item Master entries must become available in every Item dropdown.
    for mod in ["Barcode Master", "Inventory Item Master", "Stock Ledger / Item Master", "Raw Material Stock", "Finished Goods Stock"]:
        vals += _collect_generic_values(mod, "item_name")
        vals += _collect_generic_values(mod, "finished_item")
        vals += _collect_generic_values(mod, "raw_material")
    return list(dict.fromkeys([str(v) for v in vals if str(v).strip() and str(v) != "All"])) or ["Item 1"]

def _item_code_for_name(item_name):
    if not item_name or str(item_name) in ["All", "Add New..."]:
        return ""
    # First check online generic records including Barcode Master.
    try:
        for r in st.session_state.get(_SPECIAL_STORAGE_KEY, []):
            if str(r.get("item_name", "")) == str(item_name) and r.get("item_code"):
                return str(r.get("item_code"))
    except Exception:
        pass
    try:
        q = supabase.table("generic_erp_records").select("data_json").limit(1000).execute().data or []
        for rec in q:
            data = rec.get("data_json") if isinstance(rec.get("data_json"), dict) else {}
            if str(data.get("item_name", "")) == str(item_name) and data.get("item_code"):
                return str(data.get("item_code"))
    except Exception:
        pass
    # Then check existing stock master tables if columns exist.
    for tbl in ["stock_items", "items", "stock_ledgers"]:
        try:
            df = load_table(tbl, 1000)
            if not df.empty and "item_name" in df.columns and "item_code" in df.columns:
                m = df[df["item_name"].astype(str) == str(item_name)]
                if not m.empty:
                    return str(m.iloc[0].get("item_code", ""))
        except Exception:
            pass
    return ""

def _generic_lookup(kind):
    try:
        if kind == "company": return _company_codes()
        if kind == "user":
            df = load_table("users", 500); return [str(x) for x in df.get("username", pd.Series(dtype=str)).dropna().unique().tolist()] or [current_user()]
        if kind == "employee":
            df = load_table("employees", 500); return [str(x) for x in df.get("employee_name", pd.Series(dtype=str)).dropna().unique().tolist()] or ["Sample Employee"]
        if kind == "stock_item":
            return _online_stock_items()
        if kind == "bom":
            vals = _collect_generic_values("BOM Header", "bom_no") + _collect_generic_values("BOM Lines", "bom_no")
            try:
                df = load_table("bom_headers", 500); vals += [str(x) for x in df.get("bom_no", pd.Series(dtype=str)).dropna().unique().tolist()]
            except Exception: pass
            return list(dict.fromkeys(vals)) or ["BOM001"]
        if kind == "plan":
            vals = _collect_generic_values("Production Planning", "plan_no") + _collect_generic_values("Production Orders", "production_order_no")
            return vals or ["PLAN001"]
        if kind == "group": return list(ONLINE_MODULE_GROUPS.keys()) if 'ONLINE_MODULE_GROUPS' in globals() else ["Admin","Master","CRM","HR"]
        if kind == "module_name": return all_online_module_names() if 'ONLINE_MODULE_GROUPS' in globals() else ["Dashboard","User Management","Company Profile"]
    except Exception:
        pass
    return []

def _generic_save(module_title, row):
    row = dict(row)
    row["module_name"] = module_title
    row["created_by"] = current_user() if 'current_user' in globals() else st.session_state.get('username','')
    row["created_at"] = india_now().isoformat() if 'india_now' in globals() else datetime.now().isoformat()
    st.session_state.setdefault(_SPECIAL_STORAGE_KEY, []).append(row)
    # Optional Supabase persistence if generic_erp_records table exists. No crash if not created.
    try:
        supabase.table("generic_erp_records").insert({
            "client_code": row.get("company_code") or row.get("client_code") or get_client_code(),
            "module_name": module_title,
            "data_json": row,
            "created_by": row.get("created_by"),
        }).execute()
    except Exception:
        pass

def _generic_records_df(module_title):
    rows = [r for r in st.session_state.get(_SPECIAL_STORAGE_KEY, []) if r.get("module_name") == module_title]
    try:
        q = supabase.table("generic_erp_records").select("*").eq("module_name", module_title).limit(500).execute().data or []
        for rec in q:
            data = rec.get("data_json") if isinstance(rec.get("data_json"), dict) else {}
            if data: rows.append(data)
    except Exception:
        pass
    return pd.DataFrame(rows)

def _render_generic_input(col, label, field, typ, module_title):
    opts = _generic_options(typ) if isinstance(typ, str) else None
    if typ == "date": return str(col.date_input(label, value=india_now().date(), format="DD-MM-YYYY"))
    if typ == "time": return str(col.time_input(label, value=india_now().time()))
    if typ == "number": return col.number_input(label, value=0.0, key=f"gen_{module_title}_{field}")
    if typ == "bool": return col.checkbox(label, value=True, key=f"gen_{module_title}_{field}")
    if typ == "password": return col.text_input(label, type="password", key=f"gen_{module_title}_{field}")
    if typ in ["company","user","employee","stock_item","bom","plan","group","module_name"]:
        values = modules_for_selected_group(module_title) if typ == "module_name" else _generic_lookup(typ)
        if not values:
            values = ["All", "Add New..."]
        else:
            values = ["All"] + list(dict.fromkeys([str(v) for v in values if str(v).strip() and str(v) != "All"])) + ["Add New..."]
        return col.selectbox(label, values, key=f"gen_{module_title}_{field}")
    if opts: return col.selectbox(label, ["All"] + opts + ["Add New..."], key=f"gen_{module_title}_{field}")
    return col.text_input(label, key=f"gen_{module_title}_{field}")

def online_generic_module(module_title):
    """Integrated online working module screen for modules copied from offline desktop ERP.
    It gives real data-entry, import/export, records list, help and safe optional persistence.
    """
    tag = module_tag(module_title)
    cls = {"SAP":"section-master", "QuickBooks":"section-hr", "Tally":"section-rep", "Developer":"section-admin", "RBM":"section-admin"}.get(tag, "section-admin")
    show_header(f"{module_prefix(module_title)} {module_title}", cls)
    st.info(f"{module_title} is now integrated with data entry, save, list, CSV export, import/help screen and permission menu.")

    fields = _GENERIC_MODULE_FIELDS.get(module_title, [("company_code","Company Code","company"),("entry_date","Entry Date","date"),("document_no","Document No","text"),("party_name","Party / Employee / Item Name","text"),("amount","Amount","number"),("status","Status","status"),("remarks","Remarks","text")])

    with st.expander("Module Information / Help", expanded=False):
        st.write(f"**{module_title}** is used to capture and control related ERP records online. Saved records can be exported and later connected with reports, approvals and audit trails.")
        st.write("Dropdowns use already available master data wherever possible. Remarks remain free text. Company code is selected from client master list.")

    with st.form(f"form_{module_title}"):
        cols = st.columns(3)
        row = {}
        for i, (field, label, typ) in enumerate(fields):
            # Auto-fill Item Code wherever Item Name is selected, same working style as offline ERP.
            if field == "item_code" and row.get("item_name"):
                auto_code = _item_code_for_name(row.get("item_name"))
                row[field] = cols[i % 3].text_input(label, value=auto_code, key=f"gen_{module_title}_{field}_auto")
            else:
                row[field] = _render_generic_input(cols[i % 3], label, field, typ, module_title)
        c1, c2, c3 = st.columns(3)
        submitted = c1.form_submit_button(f"Save {module_title}", use_container_width=True)
        calc = c2.form_submit_button("Calculate", use_container_width=True)
        clear = c3.form_submit_button("Clear", use_container_width=True)
    if submitted or calc:
        # automatic calculations for common qty/rate/tax/payroll/capacity fields
        for qty_name in ["qty","opening_qty","inward_qty","outward_qty","planned_qty","qty_scheduled","produced_qty"]:
            if qty_name in row and "rate" in row and "value" in row:
                row["value"] = float(row.get(qty_name) or 0) * float(row.get("rate") or 0)
        if {"basic_salary","hra","allowance","pf","esi"}.issubset(row):
            row["gross_salary"] = float(row.get("basic_salary") or 0)+float(row.get("hra") or 0)+float(row.get("allowance") or 0)
            row["net_salary"] = row["gross_salary"]-float(row.get("pf") or 0)-float(row.get("esi") or 0)
        if {"gross_salary","deduction","net_salary"}.issubset(row):
            row["net_salary"] = float(row.get("gross_salary") or 0)-float(row.get("deduction") or 0)
        if {"available_hours","planned_hours","free_capacity"}.issubset(row):
            row["free_capacity"] = float(row.get("available_hours") or 0)-float(row.get("planned_hours") or 0)
        _generic_save(module_title, row)
        st.success(f"{module_title} record saved.")
        st.rerun()

    if module_title in ["Data Import"]:
        up = st.file_uploader("Upload CSV/Excel file", type=["csv","xlsx","xls"])
        if up is not None:
            try:
                df = pd.read_csv(up) if up.name.lower().endswith('.csv') else pd.read_excel(up)
                st.success(f"File loaded: {len(df)} rows")
                st.dataframe(df.head(50), use_container_width=True)
            except Exception as e:
                st.error(f"Import failed: {e}")

    df = _generic_records_df(module_title)
    st.subheader(f"Saved Records - {module_title}")
    if df.empty:
        sample = {label: f"Sample {label}" for _, label, typ in fields[:6]}
        st.dataframe(pd.DataFrame([sample]), use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)
        st.download_button("Export CSV", df.to_csv(index=False).encode(), file_name=f"{module_title.replace(' ','_')}.csv", mime="text/csv", use_container_width=True)


    # Print Preview / PDF style preview for payslip, voucher, bill, note, order and other printable modules.
    printable_words = ["Payslip", "Voucher", "Invoice", "Bill", "Receipt", "Payment", "Debit Note", "Credit Note", "Order", "Delivery Note", "Receipt Note"]
    if any(w.lower() in module_title.lower() for w in printable_words):
        st.markdown("### Print Preview / PDF")
        preview_row = None
        if not df.empty:
            preview_row = df.iloc[-1].to_dict()
        else:
            preview_row = row if 'row' in locals() else {}
        with st.expander("Open Print Preview", expanded=False):
            st.markdown(f"""
            <div style='border:1px solid #999;padding:18px;border-radius:8px;background:white;color:#111'>
                <h2 style='text-align:center;margin:0'>RBM ERP</h2>
                <h3 style='text-align:center;margin-top:4px'>{module_title}</h3>
                <hr>
            """, unsafe_allow_html=True)
            if preview_row:
                pv = pd.DataFrame([{str(k).replace('_',' ').title(): v for k, v in preview_row.items() if k not in ['module_name','created_at']}]).T.reset_index()
                pv.columns = ["Particulars", "Details"]
                st.table(pv)
            st.markdown("<hr><p style='text-align:center'>This is computer generated print preview from RBM ERP Online.</p></div>", unsafe_allow_html=True)

def _page(function_name, title):
    fn = globals().get(function_name)
    # IMPORTANT FIX:
    # online_generic_module needs one argument (module title).
    # Any other page function that requires an argument is also wrapped safely.
    if function_name == "online_generic_module":
        return lambda title=title: online_generic_module(title)
    if callable(fn):
        try:
            sig = inspect.signature(fn)
            required = [p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
            if required:
                return lambda title=title, fn=fn: fn(title)
            return fn
        except Exception:
            return lambda title=title: online_generic_module(title)
    return lambda title=title: online_generic_module(title)




def build_ledger_statement_df(selected_ledger, from_dt=None, to_dt=None):
    """Ledger statement: opening + Dr/Cr transactions + running/net balance."""
    ledger = str(selected_ledger or "All").strip()
    ledgers = load_table("ledgers", 50000)
    entries = load_table("accounting_entries", 50000)
    lines = load_table("accounting_entry_lines", 50000)

    def _date_ok(v):
        if from_dt is None and to_dt is None:
            return True
        try:
            d = pd.to_datetime(v, dayfirst=True, errors="coerce").date()
            if pd.isna(pd.to_datetime(v, dayfirst=True, errors="coerce")):
                return True
            if from_dt is not None and d < from_dt:
                return False
            if to_dt is not None and d > to_dt:
                return False
            return True
        except Exception:
            return True

    rows = []
    opening_dr = opening_cr = 0.0
    if not ledgers.empty and "ledger_name" in ledgers.columns:
        ldf = ledgers.copy()
        if ledger != "All":
            ldf = ldf[ldf["ledger_name"].astype(str) == ledger]
        for _, r in ldf.iterrows():
            op = num_value(r.get("opening_balance", 0))
            bt = str(r.get("balance_type", "Dr")).strip().lower()
            if bt.startswith("cr"):
                opening_cr += abs(op)
            else:
                opening_dr += abs(op)

    opening_net = opening_dr - opening_cr
    rows.append({
        "Date": "Opening",
        "Voucher Type": "Opening Balance",
        "Voucher No": "",
        "Ledger Name": ledger,
        "Particulars": "Opening Balance",
        "Dr Amount": round(opening_dr, 2),
        "Cr Amount": round(opening_cr, 2),
        "Net Balance": round(abs(opening_net), 2),
        "Balance Type": "Dr" if opening_net >= 0 else "Cr",
        "Narration / Remarks": ""
    })

    entry_lookup = {}
    if not entries.empty and "id" in entries.columns:
        for _, e in entries.iterrows():
            entry_lookup[str(e.get("id"))] = e

    txns = []
    if not lines.empty and "ledger_name" in lines.columns:
        lns = lines.copy()
        if ledger != "All":
            lns = lns[lns["ledger_name"].astype(str) == ledger]
        for _, l in lns.iterrows():
            e = entry_lookup.get(str(l.get("entry_id")), {})
            dt = e.get("entry_date", l.get("entry_date", "")) if hasattr(e, 'get') else l.get("entry_date", "")
            if not _date_ok(dt):
                continue
            dc = str(l.get("dr_cr", "Dr")).lower()
            amt = num_value(l.get("amount", 0))
            txns.append({
                "Date": dt,
                "Voucher Type": e.get("voucher_type", l.get("voucher_type", "")) if hasattr(e, 'get') else l.get("voucher_type", ""),
                "Voucher No": e.get("voucher_no", l.get("voucher_no", "")) if hasattr(e, 'get') else l.get("voucher_no", ""),
                "Ledger Name": l.get("ledger_name", ""),
                "Particulars": "Dr Entry" if dc.startswith("dr") else "Cr Entry",
                "Dr Amount": amt if dc.startswith("dr") else 0.0,
                "Cr Amount": amt if dc.startswith("cr") else 0.0,
                "Narration / Remarks": l.get("remarks", e.get("narration", "") if hasattr(e, 'get') else "")
            })

    # Fallback for old/simple accounting_entries rows without line table
    if not entries.empty:
        for _, e in entries.iterrows():
            dt = e.get("entry_date", "")
            if not _date_ok(dt):
                continue
            amt = num_value(e.get("amount", e.get("total_amount", 0)))
            debit_acc = str(e.get("debit_account", ""))
            credit_acc = str(e.get("credit_account", ""))
            if debit_acc and debit_acc != "Multiple" and (ledger == "All" or debit_acc == ledger):
                txns.append({"Date": dt, "Voucher Type": e.get("voucher_type", ""), "Voucher No": e.get("voucher_no", ""), "Ledger Name": debit_acc, "Particulars": "Debit", "Dr Amount": amt, "Cr Amount": 0.0, "Narration / Remarks": e.get("narration", "")})
            if credit_acc and credit_acc != "Multiple" and (ledger == "All" or credit_acc == ledger):
                txns.append({"Date": dt, "Voucher Type": e.get("voucher_type", ""), "Voucher No": e.get("voucher_no", ""), "Ledger Name": credit_acc, "Particulars": "Credit", "Dr Amount": 0.0, "Cr Amount": amt, "Narration / Remarks": e.get("narration", "")})

    # Sales/Purchase/Expense party impact rows where available
    extra_sources = [
        ("sales", "Sales Invoice", ["invoice_date", "date"], ["invoice_no", "voucher_no"], ["customer_name", "party_name", "ledger_name"], "Dr", ["total_value", "total_amount", "gross_value", "amount"]),
        ("purchase", "Purchase Invoice", ["invoice_date", "date"], ["invoice_no", "voucher_no", "bill_no"], ["vendor_name", "supplier_name", "party_name", "ledger_name"], "Cr", ["total_value", "total_amount", "gross_value", "amount"]),
        ("expenses", "Expense Voucher", ["expense_date", "voucher_date", "date"], ["voucher_no", "invoice_no"], ["vendor_name", "supplier_name", "party_name", "expense_head"], "Cr", ["total_value", "total_amount", "amount", "net_value"]),
        ("service_vouchers", "Service Voucher", ["voucher_date", "date"], ["voucher_no"], ["customer_name", "party_name", "ledger_name"], "Dr", ["total_value", "total_amount", "amount"]),
    ]
    for table, vtype, date_cols, doc_cols, party_cols, side, amt_cols in extra_sources:
        try:
            df = load_table(table, 50000)
            if df.empty:
                continue
            for _, r in df.iterrows():
                party = next((str(r.get(c, "")) for c in party_cols if c in df.columns and str(r.get(c, "")).strip()), "")
                if ledger != "All" and party != ledger:
                    continue
                dt = next((r.get(c, "") for c in date_cols if c in df.columns), "")
                if not _date_ok(dt):
                    continue
                doc = next((r.get(c, "") for c in doc_cols if c in df.columns), "")
                amt = next((num_value(r.get(c, 0)) for c in amt_cols if c in df.columns), 0.0)
                txns.append({"Date": dt, "Voucher Type": vtype, "Voucher No": doc, "Ledger Name": party, "Particulars": vtype, "Dr Amount": amt if side == "Dr" else 0.0, "Cr Amount": amt if side == "Cr" else 0.0, "Narration / Remarks": r.get("remarks", "")})
        except Exception:
            pass

    # Sort transactions by date where possible
    def _sort_key(r):
        d = pd.to_datetime(r.get("Date", ""), dayfirst=True, errors="coerce")
        return d if not pd.isna(d) else pd.Timestamp.max
    txns = sorted(txns, key=_sort_key)

    running = opening_net
    for r in txns:
        running += num_value(r.get("Dr Amount", 0)) - num_value(r.get("Cr Amount", 0))
        r["Dr Amount"] = round(num_value(r.get("Dr Amount", 0)), 2)
        r["Cr Amount"] = round(num_value(r.get("Cr Amount", 0)), 2)
        r["Net Balance"] = round(abs(running), 2)
        r["Balance Type"] = "Dr" if running >= 0 else "Cr"
        rows.append(r)

    total_dr = sum(num_value(r.get("Dr Amount", 0)) for r in rows)
    total_cr = sum(num_value(r.get("Cr Amount", 0)) for r in rows)
    net = total_dr - total_cr
    rows.append({
        "Date": "Total",
        "Voucher Type": "",
        "Voucher No": "",
        "Ledger Name": ledger,
        "Particulars": "Net Closing Balance",
        "Dr Amount": round(total_dr, 2),
        "Cr Amount": round(total_cr, 2),
        "Net Balance": round(abs(net), 2),
        "Balance Type": "Dr" if net >= 0 else "Cr",
        "Narration / Remarks": ""
    })
    return pd.DataFrame(rows)

def report_module_screen(report_title):
    """Tally-style individual report page so Trial Balance, P&L, B/S, receivable, payable and stock do not show same clients table."""
    show_header(f"{module_prefix(report_title)} {report_title}", "section-rep")
    c1, c2, c3 = st.columns(3)
    from_dt = c1.date_input("From Date", value=india_now().date().replace(day=1), format="DD-MM-YYYY", key=f"rep_from_{report_title}")
    to_dt = c2.date_input("To Date", value=india_now().date(), format="DD-MM-YYYY", key=f"rep_to_{report_title}")
    search = c3.text_input("Search / Ledger / Party / Item", key=f"rep_search_{report_title}")
    fmt = "Standard"
    if report_title in ["Profit Loss", "Balance Sheet"]:
        fmt = st.selectbox("P&L / B.S. Format", ["Standard", "Overheads"], key=f"rep_fmt_{report_title}")
    tb = build_trial_balance_df()
    if report_title == "Ledger Statement":
        ledger_options = ["All"]
        try:
            ldf = load_table("ledgers", 50000)
            if not ldf.empty and "ledger_name" in ldf.columns:
                ledger_options += sorted([x for x in ldf["ledger_name"].dropna().astype(str).unique().tolist() if x.strip()])
        except Exception:
            pass
        selected_ledger = st.selectbox("Select Ledger Name", ledger_options, key="ledger_statement_ledger")
        df = build_ledger_statement_df(selected_ledger, from_dt, to_dt)
        total_dr = round(df["Dr Amount"].apply(num_value).sum(), 2) if not df.empty and "Dr Amount" in df.columns else 0.0
        total_cr = round(df["Cr Amount"].apply(num_value).sum(), 2) if not df.empty and "Cr Amount" in df.columns else 0.0
        net = round(total_dr - total_cr, 2)
        st.info(f"Ledger: {selected_ledger} | Total Dr: ₹ {total_dr:,.2f} | Total Cr: ₹ {total_cr:,.2f} | Net Balance: ₹ {abs(net):,.2f} {'Dr' if net >= 0 else 'Cr'}")
    elif report_title == "Trial Balance":
        df = tb[[c for c in ["ledger_group","ledger_name","opening_dr","opening_cr","debit","credit","closing_dr","closing_cr"] if c in tb.columns]].copy() if not tb.empty else pd.DataFrame(columns=["Group","Particulars","Dr Amount","Cr Amount","Report Type"])
    elif report_title == "Profit Loss":
        df = build_profit_loss_df(tb) if not tb.empty else pd.DataFrame({"Debit Particulars":["To Opening Stock","To Purchases","To Direct Expenses","To Gross Profit c/d","Total","To Salaries","To Rent","To Electricity","To Office Expenses","To Depreciation","To Interest Paid","To Net Profit transferred to Capital A/c"],"Debit Amount (₹)":[0]*12,"Credit Particulars":["By Sales","By Closing Stock","By Other Operating Income","","Total","By Gross Profit b/d","By Commission Received","By Interest Received","","","",""] ,"Credit Amount (₹)":[0]*12,"Format":[fmt]*12})
    elif report_title == "Balance Sheet":
        df = build_balance_sheet_df(tb) if not tb.empty else pd.DataFrame({"Liabilities":["Capital Account","Add: Net Profit","Less: Drawings","Secured Loans","Unsecured Loans","Sundry Creditors","Outstanding Expenses","Duties & Taxes Payable","Total"],"Amount (₹)":[0]*9,"Assets":["Fixed Assets","Less: Depreciation","Net Fixed Assets","Investments","Closing Stock","Sundry Debtors","Cash in Hand","Cash at Bank","Total"],"Asset Amount (₹)":[0]*9,"Format":[fmt]*9})
    elif report_title in ["Sundry Receivable", "Customer Outstanding Ageing"]:
        df = tb[tb.get("ledger_group", pd.Series(dtype=str)).astype(str).isin(["Sundry Debtors","Trade Receivables"])] if not tb.empty else pd.DataFrame(columns=["customer_name","invoice_no","invoice_date","due_date","amount","received","balance","ageing_days"])
    elif report_title in ["Sundry Payable", "Supplier Outstanding Ageing"]:
        df = tb[tb.get("ledger_group", pd.Series(dtype=str)).astype(str).isin(["Sundry Creditors","Trade Payables"])] if not tb.empty else pd.DataFrame(columns=["supplier_name","bill_no","bill_date","due_date","amount","paid","balance","ageing_days"])
    elif report_title in ["Stock Report", "Stock Ageing / Slow Moving Stock"]:
        df = build_stock_summary_df()
        if df.empty: df = pd.DataFrame(columns=["Stock Group","Item Code","Item Name","Opening Qty","Purchase Qty","Sales/Consumption Qty","Closing Qty","Rate","Value","Ageing Days"])
    elif report_title in ["Gst Report", "GST Return Summary", "GST Reconciliation"]:
        df = pd.DataFrame(columns=["GSTIN","Invoice No","Invoice Date","Party Name","Taxable Value","CGST","SGST","IGST","Total GST","Mismatch Status"])
    elif report_title == "Tds Report":
        df = pd.DataFrame(columns=["Date","Party Name","Section","TDS %","Gross Amount","TDS Amount","Paid/Payable","Challan No"])
    else:
        df = pd.DataFrame(columns=["Date","Document No","Party / Item","Debit","Credit","Amount","Status","Remarks"])
    if search and not df.empty:
        df = filter_dataframe(df, search)
    st.caption(f"Report: {report_title} | Format: {fmt} | Rows: {len(df)}")
    st.dataframe(df, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.download_button("Export CSV", df.to_csv(index=False).encode('utf-8'), f"{report_title.replace(' ','_')}.csv", "text/csv", use_container_width=True, key=f"csv_{report_title}")
    c2.download_button("Export Excel", to_excel_bytes(df), f"{report_title.replace(' ','_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{report_title}")
    with st.expander("Drill-down details"):
        st.info("Click/select the relevant ledger/party/item row above, then use search filter to see supporting records. Detailed row-click voucher drill-down can be connected once Streamlit AgGrid/table selection is added.")

def get_module_mapping():
    """Map latest offline desktop module names to online pages. Existing online pages are reused."""
    return {
        "Dashboard": dashboard,

        # Admin
        "Client Master": _page("client_master", "Client Master"),
        "User Management": _page("user_management", "User Management"),
        "Role Permission Control": _page("role_permission_control", "Role Permission Control"),
        "Role Based Security": _page("role_based_security_control", "Role Based Security"),
        "Client License Dashboard": _page("license_manager_module", "Client License Dashboard"),
        "User Password Change": _page("online_generic_module", "User Password Change"),
        "License Status Screen": _page("license_manager_module", "License Status Screen"),
        "Data Purge Control": _page("online_generic_module", "Data Purge Control"),
        "Data Locking Period": _page("online_generic_module", "Data Locking Period"),
        "Mandatory Field Settings": _page("online_generic_module", "Mandatory Field Settings"),
        "Client Group Permission": _page("online_generic_module", "Client Group Permission"),
        "User Group Permission": _page("role_permission_control", "User Group Permission"),
        "Client Module Permission": _page("online_generic_module", "Client Module Permission"),

        # Master
        "Company Profile": _page("company_profile", "Company Profile"),
        "Financial Year Master": _page("financial_year_master", "Financial Year Master"),
        "Cost Center Master": _page("cost_center_master", "Cost Center Master"),
        "Document Series": _page("document_series_master", "Document Series"),
        "GST Settings": _page("gst_settings_master", "GST Settings"),
        "Ledger Group Master": _page("ledger_group_master", "Ledger Group Master"),
        "Ledger Master": _page("ledger_master", "Ledger Master"),
        "Stock Group Master": _page("stock_group_master", "Stock Group Master"),
        "Stock Ledger Master": _page("stock_ledger_master", "Stock Ledger Master"),
        "Auto Invoice Numbering": _page("document_series_master", "Auto Invoice Numbering"),

        # CRM
        "CRM Leads": _page("online_generic_module", "CRM Leads"),
        "CRM Followups": _page("online_generic_module", "CRM Followups"),
        "CRM Customers": _page("online_generic_module", "CRM Customers"),
        "CRM Opportunities": _page("online_generic_module", "CRM Opportunities"),
        "Customer Portal Access": _page("online_generic_module", "Customer Portal Access"),

        # HR
        "Employee Master": _page("employee_master", "Employee Master"),
        "Attendance Management": _page("attendance", "Attendance Management"),
        "Attendance Visits": _page("attendance", "Attendance Visits"),
        "IN / OUT Register": _page("inout_register", "IN / OUT Register"),
        "Visitor Register": _page("visitor_register", "Visitor Register"),
        "Task Delegation": _page("task_delegation", "Task Delegation"),
        "Appointments": _page("appointment_module", "Appointments"),
        "Payroll Salary Structure": _page("online_generic_module", "Payroll Salary Structure"),
        "Payroll Processing": _page("online_generic_module", "Payroll Processing"),
        "Payroll Payslip": _page("online_generic_module", "Payroll Payslip"),

        # Inventory
        "Inventory Item Master": _page("stock_ledger_master", "Inventory Item Master"),
        "Barcode Master": _page("online_generic_module", "Barcode Master"),
        "Barcode Print Log": _page("online_generic_module", "Barcode Print Log"),
        "Warehouse Stock": _page("online_generic_module", "Warehouse Stock"),
        "Raw Material Stock": _page("stock_raw", "Raw Material Stock"),
        "Finished Goods Stock": _page("stock_fg", "Finished Goods Stock"),
        "WIP Stock": _page("stock_wip", "WIP Stock"),
        "Stock Voucher": _page("stock_voucher", "Stock Voucher"),
        "Stock Report": lambda: report_module_screen("Stock Report"),
        "Stock Ageing / Slow Moving Stock": lambda: report_module_screen("Stock Ageing / Slow Moving Stock"),

        # Manufacturing
        "BOM Header": _page("bill_of_material_module", "BOM Header"),
        "BOM Lines": _page("bill_of_material_module", "BOM Lines"),
        "Production Orders": _page("production_order_module", "Production Orders"),
        "Production Entries": _page("production_entry_module", "Production Entries"),
        "Consumption Entries": _page("consumption_entry_module", "Consumption Entries"),
        "FG Entries": _page("finished_goods_entry_module", "FG Entries"),
        "Production Costing": _page("production_costing_module", "Production Costing"),
        "MRP": _page("mrp_module", "MRP"),
        "Manufacturing BOM": _page("bill_of_material_module", "Manufacturing BOM"),
        "Production Planning": _page("online_generic_module", "Production Planning"),
        "Production Schedule": _page("online_generic_module", "Production Schedule"),
        "Capacity Planning": _page("online_generic_module", "Capacity Planning"),
        "Demand Forecasting": _page("online_generic_module", "Demand Forecasting"),
        "Quality Management": _page("online_generic_module", "Quality Management"),
        "Preventive Maintenance": _page("online_generic_module", "Preventive Maintenance"),
        "Batch Management": _page("online_generic_module", "Batch Management"),
        "Serial Number Tracking": _page("online_generic_module", "Serial Number Tracking"),
        "Warehouse Bin Rack Management": _page("online_generic_module", "Warehouse Bin Rack Management"),

        # Accounts
        "Accounting Entries": _page("accounting_entries", "Accounting Entries"),
        "Accounting Entry Lines": _page("online_generic_module", "Accounting Entry Lines"),
        "Fixed Assets": _page("fixed_assets", "Fixed Assets"),
        "Asset Management": _page("asset_management_advanced", "Asset Management"),
        "Asset Maintenance": _page("online_generic_module", "Asset Maintenance"),
        "Payment Receipt Voucher": _page("online_generic_module", "Payment Receipt Voucher"),
        "Bank Payment Voucher": _page("online_generic_module", "Bank Payment Voucher"),
        "Bank Reconciliation": _page("bank_reconciliation", "Bank Reconciliation"),
        "Year Closing / Opening Balance Transfer": _page("online_generic_module", "Year Closing / Opening Balance Transfer"),
        "Budget vs Actual": _page("budget_vs_actual", "Budget vs Actual"),
        "Cash Flow Statement": lambda: report_module_screen("Cash Flow Statement"),

        # Sales/Purchase/Expense
        "Sales GST Invoice": _page("sales_invoice", "Sales GST Invoice"),
        "Sales Order": _page("sales_cycle", "Sales Order"),
        "Delivery Note": _page("sales_cycle", "Delivery Note"),
        "Credit Note": _page("sales_cycle", "Credit Note"),
        "Customer Outstanding Ageing": lambda: report_module_screen("Customer Outstanding Ageing"),
        "Sales Cycle": _page("sales_cycle", "Sales Cycle"),
        "Recurring Invoices": _page("online_generic_module", "Recurring Invoices"),
        "Purchase GST Invoice": _page("purchase_invoice", "Purchase GST Invoice"),
        "Purchase Order": _page("purchase_cycle", "Purchase Order"),
        "Receipt Note": _page("purchase_cycle", "Receipt Note"),
        "Debit Note": _page("purchase_cycle", "Debit Note"),
        "Supplier Outstanding Ageing": lambda: report_module_screen("Supplier Outstanding Ageing"),
        "Purchase Cycle": _page("purchase_cycle", "Purchase Cycle"),
        "GST Reconciliation": lambda: report_module_screen("GST Reconciliation"),
        "Expense GST": _page("expense_gst", "Expense GST"),
        "Service Voucher": _page("service_voucher", "Service Voucher"),
        "Expense Approval": _page("online_generic_module", "Expense Approval"),
        "Recurring Expenses": _page("online_generic_module", "Recurring Expenses"),
        "TDS Report": _page("reports", "TDS Report"),
        "Gst Report": lambda: report_module_screen("Gst Report"),

        # Projects/Quotation
        "Project Accounting": _page("project_accounting_module", "Project Accounting"),
        "Project Income Heads": _page("online_generic_module", "Project Income Heads"),
        "Project Expense Heads": _page("online_generic_module", "Project Expense Heads"),
        "Project Profitability": _page("online_generic_module", "Project Profitability"),
        "Internal Orders": _page("online_generic_module", "Internal Orders"),
        "Budget Control": _page("online_generic_module", "Budget Control"),
        "Quotation": _page("quotation_module", "Quotation"),
        "Quotation Negotiations": _page("quotation_module", "Quotation Negotiations"),
        "Quotation Requirements": _page("quotation_module", "Quotation Requirements"),
        "Quotation Business Users": _page("quotation_module", "Quotation Business Users"),
        "Quotation Access": _page("quotation_module", "Quotation Access"),

        # Enterprise
        "Workflow Engine": _page("workflow_engine", "Workflow Engine"),
        "Approval Matrix": _page("online_generic_module", "Approval Matrix"),
        "Business Process Flow": _page("online_generic_module", "Business Process Flow"),
        "Document Management": _page("document_management", "Document Management"),
        "OCR Invoice Scanner": _page("online_generic_module", "OCR Invoice Scanner"),
        "Global Smart Search": _page("online_generic_module", "Global Smart Search"),
        "AI Audit & Exception Dashboard": _page("digital_audit_module", "AI Audit & Exception Dashboard"),
        "Consolidated Financial Statements": _page("online_generic_module", "Consolidated Financial Statements"),
        "Inter Company Transactions": _page("online_generic_module", "Inter Company Transactions"),
        "Multi Company / Branch": _page("multi_company_branch", "Multi Company / Branch"),
        "Multi Currency": _page("online_generic_module", "Multi Currency"),
        "Customer Portal": _page("online_generic_module", "Customer Portal"),
        "Vendor Portal": _page("online_generic_module", "Vendor Portal"),
        "Profitability Analysis - Customer Product Branch": lambda: report_module_screen("Profitability Analysis - Customer Product Branch"),

        # Support/Audit/Tools
        "Support Desk": _page("support_ticket_module", "Support Desk"),
        "Support Tickets": _page("support_ticket_module", "Support Tickets"),
        "Customer Complaints": _page("online_generic_module", "Customer Complaints"),
        "Service Requests": _page("online_generic_module", "Service Requests"),
        "Client Support Register": _page("online_generic_module", "Client Support Register"),
        "AMC / Subscription": _page("amc_subscription_module", "AMC / Subscription"),
        "License Manager": _page("license_manager_module", "License Manager"),

        "Audit Log": _page("audit_log_report", "Audit Log"),
        "Numbering Series Audit": _page("online_generic_module", "Numbering Series Audit"),
        "Digital Audit": _page("digital_audit_module", "Digital Audit"),
        "Duplicate Payment Detection": _page("digital_audit_module", "Duplicate Payment Detection"),
        "Duplicate Invoice Detection": _page("digital_audit_module", "Duplicate Invoice Detection"),
        "Suspicious Entry Report": _page("digital_audit_module", "Suspicious Entry Report"),
        "Backdated Voucher Report": _page("digital_audit_module", "Backdated Voucher Report"),
        "Weekend Entry Report": _page("digital_audit_module", "Weekend Entry Report"),
        "User Wise Modification Report": _page("digital_audit_module", "User Wise Modification Report"),

        "OneDrive Backup": _page("online_generic_module", "OneDrive Backup"),
        "Optional Online Sync Center": _page("offline_sync_engine", "Optional Online Sync Center"),
        "Data Import": _page("import_center", "Data Import"),
        "Data Export": _page("online_generic_module", "Data Export"),
        "Email Utility": _page("email_sms_settings", "Email Utility"),
        "PDF Print Utility": _page("online_generic_module", "PDF Print Utility"),
        "System Settings": _page("online_generic_module", "System Settings"),
        "AI Chat Assistant": _page("ai_assistant", "AI Chat Assistant"),
        "WhatsApp Integration": _page("email_sms_settings", "WhatsApp Integration"),
        "Email Integration": _page("email_sms_settings", "Email Integration"),
        "OneDrive Backup Advanced": _page("online_generic_module", "OneDrive Backup Advanced"),
        "Mobile App Sync": _page("pwa_mobile_app", "Mobile App Sync"),
        "Notification Center": _page("notification_center", "Notification Center"),
        "Backup Restore System": _page("online_generic_module", "Backup Restore System"),
        "Excel Import Wizard": _page("import_center", "Excel Import Wizard"),
        "Export All Data": _page("online_generic_module", "Export All Data"),
        "Reminder System": _page("notification_center", "Reminder System"),
        "Settings Center": _page("online_generic_module", "Settings Center"),
        "Restore Backup": _page("online_generic_module", "Restore Backup"),
        "Error Log Viewer": _page("online_generic_module", "Error Log Viewer"),
        "Data Health Check": _page("online_generic_module", "Data Health Check"),

        # Reports
        "Registers / Reports": _page("reports", "Registers / Reports"),
        "Import Center": _page("import_center", "Import Center"),
        "Trial Balance": lambda: report_module_screen("Trial Balance"),
        "Ledger Statement": lambda: report_module_screen("Ledger Statement"),
        "Profit Loss": lambda: report_module_screen("Profit Loss"),
        "Balance Sheet": lambda: report_module_screen("Balance Sheet"),
        "Sundry Receivable": lambda: report_module_screen("Sundry Receivable"),
        "Sundry Payable": lambda: report_module_screen("Sundry Payable"),
        "Calculation Book": _page("calculation_book", "Calculation Book"),
        "Import Logs": _page("reports", "Import Logs"),
        "Dashboard Analytics": _page("dashboard_analytics", "Dashboard Analytics"),
        "Chairman MIS": _page("dashboard_analytics", "Chairman MIS"),
        "User Activity Dashboard": _page("reports", "User Activity Dashboard"),
        "Pending Work Dashboard": _page("reports", "Pending Work Dashboard"),
        "GST Return Summary": _page("reports", "GST Return Summary"),
    }



def render_current_page(mapping, choice):
    page_fn = mapping.get(choice)
    if not callable(page_fn):
        online_generic_module(choice)
        return
    try:
        page_fn()
    except TypeError:
        # If an older page function signature does not match Streamlit menu call, open integrated generic module instead.
        online_generic_module(choice)
    except Exception as e:
        st.error(f"Module error in {choice}: {e}")
        st.info("This module is protected by safe fallback so the full ERP will not stop. Please check related Supabase table/columns if save is required.")
        online_generic_module(choice)


def main_app():
    if "sidebar_open" not in st.session_state:
        st.session_state["sidebar_open"] = True

    if "active_group" not in st.session_state:
        st.session_state["active_group"] = "Dashboard"
    if "active_choice" not in st.session_state:
        st.session_state["active_choice"] = "Dashboard"

    mapping = get_module_mapping()

    if st.session_state["sidebar_open"]:
        menu_col, content_col = st.columns([1.15, 4.85], gap="large")
        with menu_col:
            if st.button("☰ Menu", use_container_width=True, key="menu_open_label"):
                pass
            group, choice = render_custom_menu()
        with content_col:
            rbm_header()
            render_current_page(mapping, choice)
    else:
        # When hidden, show the unhide button, but keep the same current module open.
        if st.button("☰ Show Menu", key="show_menu_when_hidden"):
            st.session_state["sidebar_open"] = True
            st.rerun()
        rbm_header()
        st.info("Menu is hidden. Click ☰ Show Menu to show it again.")
        choice = st.session_state.get("active_choice", "Dashboard")
        render_current_page(mapping, choice)



# ================= RBM ONLINE FINAL INTEGRATION PATCH 3 =================
# Purpose: make online modules closer to offline desktop ERP: proper module dropdowns,
# production order flow, printable preview, employee photo upload UI, and safer reports.

def _rbm_safe_df(table, limit=1000):
    try:
        return load_table(table, limit)
    except Exception:
        return pd.DataFrame()


def _production_order_no_list():
    try:
        df = _rbm_safe_df("production_orders", 2000)
        vals = []
        if not df.empty and "order_no" in df.columns:
            vals = [str(x) for x in df["order_no"].dropna().unique().tolist() if str(x).strip()]
        return vals or ["No Production Order Found"]
    except Exception:
        return ["No Production Order Found"]


def _consumption_entry_no_list():
    try:
        df = _rbm_safe_df("consumption_entries", 2000)
        vals = []
        if not df.empty and "entry_no" in df.columns:
            vals = [str(x) for x in df["entry_no"].dropna().unique().tolist() if str(x).strip()]
        return vals or ["No Consumption Entry Found"]
    except Exception:
        return ["No Consumption Entry Found"]


def _module_names_for_group(group_name):
    try:
        return list(ONLINE_MODULE_GROUPS.get(str(group_name), [])) or ["No Module Found"]
    except Exception:
        return ["No Module Found"]


def _render_print_preview_from_row(title, row):
    html = f"""
    <html><head><meta charset='utf-8'><title>{title}</title>
    <style>
      body{{font-family:Arial, sans-serif; padding:24px;}}
      h2{{border-bottom:2px solid #111; padding-bottom:8px;}}
      table{{border-collapse:collapse; width:100%;}}
      td,th{{border:1px solid #777; padding:7px; font-size:13px;}}
      th{{background:#f2f2f2; text-align:left;}}
      .no-print{{margin-bottom:15px;}}
      @media print{{.no-print{{display:none;}}}}
    </style></head><body>
    <div class='no-print'><button onclick='window.print()'>Print / Save PDF</button></div>
    <h2>RBM ERP - {title}</h2>
    <table><tbody>
    """
    for k,v in dict(row).items():
        html += f"<tr><th>{str(k).replace('_',' ').title()}</th><td>{'' if v is None else v}</td></tr>"
    html += "</tbody></table></body></html>"
    st.components.v1.html(html, height=520, scrolling=True)


def _generic_print_preview_ui(module_title, df):
    if df is None or df.empty:
        st.warning("Print Preview: first save or load at least one record.")
        return
    st.subheader(f"Print Preview - {module_title}")
    rec_no = st.selectbox("Select record for print preview", list(range(len(df))), format_func=lambda i: f"Record {i+1}", key=f"pp_select_{module_title}")
    row = df.iloc[int(rec_no)].to_dict()
    _render_print_preview_from_row(module_title, row)


# Override generic lookup with correct module list support.
def _generic_lookup(kind):
    try:
        if kind == "company": return _company_codes()
        if kind == "user":
            df = load_table("users", 500); return [str(x) for x in df.get("username", pd.Series(dtype=str)).dropna().unique().tolist()] or [current_user()]
        if kind == "employee":
            df = load_table("employees", 500); return [str(x) for x in df.get("employee_name", pd.Series(dtype=str)).dropna().unique().tolist()] or ["Sample Employee"]
        if kind == "stock_item": return get_stock_items() or ["Sample Item"]
        if kind == "bom":
            df = load_table("bom_headers", 500); return [str(x) for x in df.get("bom_no", pd.Series(dtype=str)).dropna().unique().tolist()] or ["BOM001"]
        if kind == "production_order": return _production_order_no_list()
        if kind == "consumption_entry": return _consumption_entry_no_list()
        if kind == "plan":
            recs = st.session_state.get(_SPECIAL_STORAGE_KEY, [])
            vals=[r.get("plan_no") for r in recs if r.get("module_name")=="Production Planning" and r.get("plan_no")]
            return vals or ["PLAN001"]
        if kind == "group": return list(ONLINE_MODULE_GROUPS.keys()) if 'ONLINE_MODULE_GROUPS' in globals() else ["Admin","Master","CRM","HR"]
        if kind == "module_name": return all_online_module_names() if 'ONLINE_MODULE_GROUPS' in globals() else ["Dashboard","User Management","Company Profile"]
    except Exception:
        pass
    return []

# Improve field definitions for online generic modules where the old screen was too common.
_GENERIC_MODULE_FIELDS.update({
    "Client Module Permission": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("allowed","Allowed","bool"),("status","Status","status"),("remarks","Remarks","text")],
    "Mandatory Field Settings": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("field_name","Field Name","text"),("is_mandatory","Is Mandatory","bool"),("status","Status","status"),("remarks","Remarks","text")],
    "Data Locking Period": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("lock_from_date","Lock From Date","date"),("lock_to_date","Lock To Date","date"),("lock_status","Lock Status",["Locked","Unlocked","Pending"]),("reason","Reason","text")],
    "Data Purge Control": [("company_code","Company Code","company"),("request_date","Request Date","date"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("from_date","From Date","date"),("to_date","To Date","date"),("purge_status","Purge Status",["Requested","Approved","Rejected","Completed"]),("requested_by","Requested By","user"),("remarks","Remarks","text")],
    "BOM Lines": [("company_code","Company Code","company"),("bom_no","BOM No","bom"),("rm_item","Raw Material Item","stock_item"),("unit","Unit","text"),("rm_qty","RM Qty","number"),("rm_rate","RM Rate","number"),("rm_amount","RM Amount","number"),("remarks","Remarks","text")],
    "Production Planning": [("company_code","Company Code","company"),("plan_no","Plan No","text"),("plan_date","Plan Date","date"),("finished_item","Finished Item","stock_item"),("planned_qty","Planned Qty","number"),("bom_no","BOM No","bom"),("start_date","Start Date","date"),("end_date","End Date","date"),("machine_name","Machine Name","text"),("supervisor","Supervisor","employee"),("plan_status","Plan Status","status")],
    "Production Schedule": [("company_code","Company Code","company"),("schedule_no","Schedule No","text"),("schedule_date","Schedule Date","date"),("production_order_no","Production Order No","production_order"),("finished_item","Finished Item","stock_item"),("qty_scheduled","Qty Scheduled","number"),("machine_name","Machine Name","text"),("shift_name","Shift Name",["Shift A","Shift B","Shift C","General"]),("schedule_status","Schedule Status","status")],
    "Capacity Planning": [("company_code","Company Code","company"),("plan_date","Plan Date","date"),("machine_name","Machine Name","text"),("production_order_no","Production Order No","production_order"),("available_hours","Available Hours","number"),("planned_hours","Planned Hours","number"),("free_capacity","Free Capacity","number"),("status","Status","status"),("remarks","Remarks","text")],
    "Payment Receipt Voucher": [("company_code","Company Code","company"),("voucher_no","Voucher No","text"),("voucher_date","Voucher Date","date"),("party_type","Party Type",["Customer","Vendor","Employee","Item","Other"]),("party_code","Customer/Vendor/Employee/Item Code","text"),("party_name","Customer/Vendor/Employee/Item Name","text"),("qty","Qty if Item","number"),("amount","Amount","number"),("payment_mode","Payment Mode","payment_mode"),("status","Status","status"),("remarks","Remarks","text")],
    "Bank Payment Voucher": [("company_code","Company Code","company"),("voucher_no","Voucher No","text"),("voucher_date","Voucher Date","date"),("party_type","Party Type",["Vendor","Employee","Customer","Item","Other"]),("party_code","Customer/Vendor/Employee/Item Code","text"),("party_name","Customer/Vendor/Employee/Item Name","text"),("qty","Qty if Item","number"),("amount","Amount","number"),("payment_mode","Payment Mode","payment_mode"),("status","Status","status"),("remarks","Remarks","text")],
    "Payroll Payslip": [("company_code","Company Code","company"),("payslip_no","Payslip No","text"),("salary_month","Salary Month","text"),("employee_name","Employee Name","employee"),("gross_salary","Gross Salary","number"),("deduction","Deduction","number"),("net_salary","Net Salary","number"),("payment_date","Payment Date","date"),("status","Status","status"),("remarks","Remarks","text")],
    "Numbering Series Audit": [("company_code","Company Code","company"),("audit_date","Audit Date","date"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("series_name","Series Name","text"),("expected_next_no","Expected Next No","text"),("actual_next_no","Actual Next No","text"),("missing_numbers","Missing Numbers","text"),("duplicate_numbers","Duplicate Numbers","text"),("audit_status","Audit Status",["OK","Mismatch","Missing","Duplicate"]),("remarks","Remarks","text")],
})


def _render_generic_input(col, label, field, typ, module_title):
    opts = _generic_options(typ) if isinstance(typ, str) else None
    if typ == "date": return str(col.date_input(label, value=india_now().date(), format="DD-MM-YYYY", key=f"gen_{module_title}_{field}"))
    if typ == "time": return str(col.time_input(label, value=india_now().time(), key=f"gen_{module_title}_{field}"))
    if typ == "number": return col.number_input(label, value=0.0, key=f"gen_{module_title}_{field}")
    if typ == "bool": return col.checkbox(label, value=True, key=f"gen_{module_title}_{field}")
    if typ == "password": return col.text_input(label, type="password", key=f"gen_{module_title}_{field}")
    if typ == "module_name_by_group":
        g = st.session_state.get(f"gen_{module_title}_group_name", "Dashboard")
        values = _module_names_for_group(g)
        return col.selectbox(label, values + ["Add New..."], key=f"gen_{module_title}_{field}")
    if typ in ["company","user","employee","stock_item","bom","plan","production_order","consumption_entry","group","module_name"]:
        values = _generic_lookup(typ)
        if not values:
            values = ["All", "Add New..."]
        else:
            values = ["All"] + list(dict.fromkeys([str(v) for v in values if str(v).strip() and str(v) != "All"])) + ["Add New..."]
        return col.selectbox(label, values, key=f"gen_{module_title}_{field}")
    if opts: return col.selectbox(label, ["All"] + opts + ["Add New..."], key=f"gen_{module_title}_{field}")
    return col.text_input(label, key=f"gen_{module_title}_{field}")


def online_generic_module(module_title):
    tag = module_tag(module_title)
    cls = {"SAP":"section-master", "QuickBooks":"section-hr", "Tally":"section-rep", "Developer":"section-admin", "RBM":"section-admin"}.get(tag, "section-admin")
    show_header(f"{module_prefix(module_title)} {module_title}", cls)
    st.info(f"{module_title} is now integrated with data entry, save, list, CSV export, import/help screen, permission menu and Print Preview.")
    fields = _GENERIC_MODULE_FIELDS.get(module_title, [("company_code","Company Code","company"),("entry_date","Entry Date","date"),("document_no","Document No","text"),("party_name","Party / Employee / Item Name","text"),("amount","Amount","number"),("status","Status","status"),("remarks","Remarks","text")])
    with st.expander("Module Information / Help", expanded=False):
        st.write(f"**{module_title}** is used to capture and control related ERP records online. Dropdowns use master values; remarks remain free text; saved record can be printed or exported.")
    with st.form(f"form_{module_title}"):
        cols = st.columns(3)
        row = {}
        for i, (field, label, typ) in enumerate(fields):
            # Auto-fill Item Code wherever Item Name is selected, same working style as offline ERP.
            if field == "item_code" and row.get("item_name"):
                auto_code = _item_code_for_name(row.get("item_name"))
                row[field] = cols[i % 3].text_input(label, value=auto_code, key=f"gen_{module_title}_{field}_auto")
            else:
                row[field] = _render_generic_input(cols[i % 3], label, field, typ, module_title)
        c1, c2, c3 = st.columns(3)
        submitted = c1.form_submit_button(f"Save {module_title}", use_container_width=True)
        calc = c2.form_submit_button("Calculate", use_container_width=True)
        clear = c3.form_submit_button("Clear", use_container_width=True)
    if submitted or calc:
        for qty_name in ["qty","opening_qty","inward_qty","outward_qty","planned_qty","qty_scheduled","produced_qty","rm_qty"]:
            for amt_name in ["value","amount","rm_amount"]:
                if qty_name in row and "rate" in row and amt_name in row:
                    row[amt_name] = float(row.get(qty_name) or 0) * float(row.get("rate") or row.get("rm_rate") or 0)
        if {"gross_salary","deduction","net_salary"}.issubset(row):
            row["net_salary"] = float(row.get("gross_salary") or 0)-float(row.get("deduction") or 0)
        if {"available_hours","planned_hours","free_capacity"}.issubset(row):
            row["free_capacity"] = float(row.get("available_hours") or 0)-float(row.get("planned_hours") or 0)
        _generic_save(module_title, row)
        st.success(f"{module_title} record saved."); st.rerun()
    if module_title in ["Data Import", "Excel Import Wizard"]:
        up = st.file_uploader("Upload CSV/Excel file", type=["csv","xlsx","xls"])
        if up is not None:
            try:
                dfup = pd.read_csv(up) if up.name.lower().endswith('.csv') else pd.read_excel(up)
                st.success(f"File loaded: {len(dfup)} rows"); st.dataframe(dfup.head(50), use_container_width=True)
            except Exception as e: st.error(f"Import failed: {e}")
    df = _generic_records_df(module_title)
    st.subheader(f"Saved Records - {module_title}")
    if df.empty:
        sample = {label: f"Sample {label}" for _, label, typ in fields[:6]}
        st.dataframe(pd.DataFrame([sample]), use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)
        c1,c2 = st.columns(2)
        c1.download_button("Export CSV", df.to_csv(index=False).encode(), file_name=f"{module_title.replace(' ','_')}.csv", mime="text/csv", use_container_width=True)
        with c2:
            show_pp = st.button("Print Preview / PDF", use_container_width=True, key=f"pp_btn_{module_title}")
        if show_pp:
            _generic_print_preview_ui(module_title, df)


def production_entry_module():
    simple_module_form("production_entries", "Production Entry", [("entry_no", "Entry No", "text"), ("entry_date", "Entry Date", "date"), ("order_no", "Production Order No", _production_order_no_list()), ("fg_item", "Finished Goods", get_stock_items()), ("produced_qty", "Produced Qty", "number"), ("warehouse", "Warehouse", "text"), ("status", "Status", ["Draft", "Posted", "Cancelled"]), ("remarks", "Remarks", "text")], "section-inv")

def consumption_entry_module():
    simple_module_form("consumption_entries", "Consumption Entry", [("entry_no", "Entry No", "text"), ("entry_date", "Entry Date", "date"), ("order_no", "Production Order No", _production_order_no_list()), ("rm_item", "Raw Material", get_stock_items()), ("consumed_qty", "Consumed Qty", "number"), ("rate", "Rate", "number"), ("amount", "Amount", "number"), ("warehouse", "Warehouse", "text"), ("remarks", "Remarks", "text")], "section-inv")

def finished_goods_entry_module():
    simple_module_form("fg_entries", "Finished Goods Entry", [("entry_no", "Entry No", "text"), ("entry_date", "Entry Date", "date"), ("production_order_no", "Production Order No", _production_order_no_list()), ("consumption_entry_no", "Consumption Entry No", _consumption_entry_no_list()), ("fg_item", "Finished Goods", get_stock_items()), ("qty", "Qty", "number"), ("rate", "Rate", "number"), ("amount", "Amount", "number"), ("warehouse", "Warehouse", "text"), ("remarks", "Remarks", "text")], "section-inv")


def bill_of_material_module():
    show_header("Bill of Material (BOM)", "section-inv")
    st.info("Same online screen for BOM Header and BOM Lines: finished goods recipe + raw material lines + cost per unit + print preview.")
    if "bom_line_count" not in st.session_state: st.session_state["bom_line_count"] = 1
    cadd, crem, creset = st.columns(3)
    if cadd.button("➕ Add Raw Material Line", use_container_width=True, key="bom_add_line_final"):
        st.session_state["bom_line_count"] += 1; st.rerun()
    if crem.button("➖ Remove Last Line", use_container_width=True, key="bom_remove_line_final"):
        if st.session_state["bom_line_count"] > 1: st.session_state["bom_line_count"] -= 1; st.rerun()
    if creset.button("🔄 Reset BOM Lines", use_container_width=True, key="bom_reset_line_final"):
        st.session_state["bom_line_count"] = 1; st.rerun()
    stock_items = get_stock_items()
    with st.form("bom_form_final"):
        c1,c2,c3=st.columns(3)
        bom_no=c1.text_input("BOM No")
        bom_date=c2.date_input("BOM Date", value=india_now().date(), format="DD-MM-YYYY")
        fg_item=c3.selectbox("Finished Goods Item", stock_items, key="bom_fg_item_final")
        fg_qty=c1.number_input("FG Qty", min_value=0.0, value=1.0, step=1.0)
        status=c2.selectbox("Status", ["Draft","Active","Inactive"])
        remarks=c3.text_input("Remarks")
        st.subheader("BOM Lines / Raw Material Consumption")
        line_rows=[]; material_cost=0.0
        for i in range(st.session_state["bom_line_count"]):
            st.markdown(f"**Raw Material Line {i+1}**")
            a,b,c,d,e=st.columns(5)
            rm_item=a.selectbox("RM Item", stock_items, key=f"bom_rm_item_final_{i}")
            unit=b.text_input("Unit", key=f"bom_unit_final_{i}")
            rm_qty=c.number_input("Qty", min_value=0.0, value=0.0, step=1.0, key=f"bom_qty_final_{i}")
            rm_rate=d.number_input("Rate", min_value=0.0, value=0.0, step=1.0, key=f"bom_rate_final_{i}")
            rm_amount=rm_qty*rm_rate; e.metric("Amount", f"{rm_amount:,.2f}")
            line_rows.append({"rm_item":rm_item,"unit":unit,"rm_qty":rm_qty,"rm_rate":rm_rate,"rm_amount":rm_amount}); material_cost += rm_amount
        st.subheader("Costing")
        d1,d2,d3,d4=st.columns(4)
        labour_cost=d1.number_input("Labour Cost", min_value=0.0, value=0.0, step=100.0)
        power_cost=d2.number_input("Power Cost", min_value=0.0, value=0.0, step=100.0)
        packing_cost=d3.number_input("Packing Cost", min_value=0.0, value=0.0, step=100.0)
        other_cost=d4.number_input("Other Cost", min_value=0.0, value=0.0, step=100.0)
        total_cost=material_cost+labour_cost+power_cost+packing_cost+other_cost
        cost_per_unit=total_cost/fg_qty if fg_qty else 0
        st.info(f"Material Cost: {material_cost:,.2f} | Total Cost: {total_cost:,.2f} | Cost Per Unit: {cost_per_unit:,.2f}")
        save=st.form_submit_button("Save BOM Header + Lines", use_container_width=True)
    if save:
        if not bom_no.strip(): st.error("BOM No is required.")
        else:
            res=insert_row("bom_headers", {"bom_no":bom_no.strip(),"bom_date":str(bom_date),"fg_item":fg_item,"fg_qty":fg_qty,"labour_cost":labour_cost,"power_cost":power_cost,"packing_cost":packing_cost,"other_cost":other_cost,"material_cost":material_cost,"total_cost":total_cost,"cost_per_unit":cost_per_unit,"status":status,"remarks":remarks,"created_by":current_user()})
            header_id=""
            try: header_id=res.data[0].get("id","") if res.data else ""
            except Exception: header_id=""
            for line in line_rows:
                if float(line.get("rm_qty") or 0)>0:
                    insert_row("bom_lines", {"bom_header_id":header_id,"bom_no":bom_no.strip(),"rm_item":line["rm_item"],"unit":line["unit"],"rm_qty":line["rm_qty"],"rm_rate":line["rm_rate"],"rm_amount":line["rm_amount"],"created_by":current_user()})
            st.success("BOM saved successfully."); st.rerun()
    tab1,tab2,tab3=st.tabs(["BOM Header Register","BOM Lines Register","Print Preview"])
    with tab1: show_table_with_edit_delete("bom_headers", load_table("bom_headers",1000), "BOM Header Register")
    with tab2: show_table_with_edit_delete("bom_lines", load_table("bom_lines",2000), "BOM Lines Register")
    with tab3:
        df=load_table("bom_headers",1000)
        _generic_print_preview_ui("BOM", df)


def employee_master():
    show_header("Employee Master", "section-admin")
    df = load_table("employees", 500)
    next_id = "EMP001" if df.empty else f"EMP{len(df)+1:03d}"
    with st.form("employee_form_photo_final"):
        c1,c2 = st.columns(2)
        employee_id = c1.text_input("Employee ID", value=next_id)
        employee_name = c2.text_input("Employee Name")
        mobile = c1.text_input("Mobile"); email = c2.text_input("Email")
        department = c1.text_input("Department"); designation = c2.text_input("Designation")
        branch_division = c1.text_input("Branch / Division"); status = c2.selectbox("Status", ["Active","Inactive"])
        photo = st.file_uploader("Employee Photo (preview only unless photo columns are added in Supabase)", type=["png","jpg","jpeg"])
        if st.form_submit_button("Save Employee", use_container_width=True):
            if not employee_name: st.error("Employee Name required")
            else:
                insert_row("employees", {"employee_id":employee_id,"employee_name":employee_name,"mobile":mobile,"email":email,"department":department,"designation":designation,"branch_division":branch_division,"status":status,"created_by":current_user()})
                st.success("Employee saved. Photo upload field is available; add photo columns in DB if permanent storage is required."); st.rerun()
    if 'photo' in locals() and photo is not None:
        st.image(photo, caption="Employee Photo Preview", width=160)
    show_table_with_edit_delete("employees", df, "Employee List")

# Rebuild mapping after patch so overridden functions are used.
def render_current_page(mapping, choice):
    try:
        mapping = get_module_mapping()
    except Exception:
        pass
    page_fn = mapping.get(choice)
    if not callable(page_fn):
        online_generic_module(choice); return
    try:
        page_fn()
    except TypeError:
        online_generic_module(choice)
    except Exception as e:
        st.error(f"Module error in {choice}: {e}")
        st.info("Safe fallback opened. Please check Supabase table/columns if this module requires permanent save.")
        online_generic_module(choice)
# ================= END RBM ONLINE FINAL INTEGRATION PATCH 3 =================


_PATCH5_OLD_GET_MODULE_MAPPING = get_module_mapping


# ================= RBM ONLINE FINAL PATCH 5: OFFLINE-LIKE MASTER LINKING / PATH / WHATSAPP =================

def _clean_opts(vals, fallback=None):
    out=[]
    for v in (vals or []):
        sv=str(v).strip()
        if sv and sv.lower() not in ["nan", "none"] and sv not in out:
            out.append(sv)
    if not out and fallback:
        out=list(fallback)
    return out or ["All"]

def _table_values(table_key, column, fallback=None):
    try:
        df=load_table(table_key, 2000)
        if not df.empty and column in df.columns:
            return _clean_opts(df[column].dropna().astype(str).tolist(), fallback)
    except Exception:
        pass
    return _clean_opts([], fallback)

DEFAULT_UNITS = ["PCS","MTR","KG","GMS","LTR","BOX","BAG","ROLL","SET","NOS"]
DEFAULT_PAYMENT_MODES = ["Cash","Bank","UPI","Cheque","NEFT","RTGS","IMPS","Credit Card","Debit Card","Wallet"]
STOCK_VOUCHER_TYPES = ["Contra","Payment","Receipt","Journal","Sales","Purchase","Credit Note","Debit Note","Purchase Order","Sales Order","Receipt Note","Delivery Note","Stock Journal","Physical Stock","Rejections In","Rejections Out","Payroll","Attendance","Memorandum","Reversing Journal","Optional Voucher","Material In","Material Out"]
DEFAULT_SHIFTS = ["General","Shift A","Shift B","Shift C","Night Shift"]

def _stock_details_by_item(item_name):
    try:
        if not item_name or str(item_name) in ["All", "Add New...", "No Item Found"]:
            return {}
        df=load_table("stock_ledgers", 2000)
        if df.empty or "item_name" not in df.columns:
            return {}
        m=df[df["item_name"].astype(str)==str(item_name)]
        if m.empty:
            return {}
        r=m.iloc[0].to_dict()
        return {"item_code":r.get("item_code",""),"unit":r.get("unit",""),"hsn_code":r.get("hsn_code",""),"gst_rate":r.get("gst_rate",0),"rate":r.get("opening_rate",0),"available_qty":r.get("opening_qty",0)}
    except Exception:
        return {}

def _ledger_details_by_name(name):
    try:
        if not name or str(name) in ["All", "Add New..."]:
            return {}
        df=load_table("ledgers", 2000)
        if df.empty or "ledger_name" not in df.columns:
            return {}
        m=df[df["ledger_name"].astype(str)==str(name)]
        if m.empty:
            return {}
        r=m.iloc[0].to_dict()
        return {"party_code":r.get("ledger_code", r.get("id","")),"gst_no":r.get("gst_no",""),"pan_no":r.get("pan_no",""),"address":r.get("address",""),"mobile":r.get("contact_no","")}
    except Exception:
        return {}

def _all_module_names_for_group(group_name):
    try:
        if str(group_name) in ["All", "", "None"]:
            return all_online_module_names()
        mods = ONLINE_MODULE_GROUPS.get(str(group_name), []) if 'ONLINE_MODULE_GROUPS' in globals() else []
        return _clean_opts(mods, ["Dashboard"])
    except Exception:
        return ["Dashboard"]

def _generic_lookup(kind):
    try:
        if kind == "company": return _company_codes()
        if kind == "user": return _table_values("users", "username", [current_user()])
        if kind == "employee": return _table_values("employees", "employee_name", ["Sample Employee"])
        if kind in ["stock_item", "finished_item", "raw_material"]: return get_stock_items()
        if kind == "unit": return _table_values("stock_ledgers", "unit", DEFAULT_UNITS)
        if kind == "bom": return _table_values("bom_headers", "bom_no", ["BOM001"])
        if kind == "production_order": return _table_values("production_orders", "order_no", ["PO-001"])
        if kind == "consumption_entry": return _table_values("consumption_entries", "entry_no", ["CE-001"])
        if kind == "fg_entry": return _table_values("fg_entries", "entry_no", ["FG-001"])
        if kind == "plan": return _table_values("mrp", "plan_no", ["PLAN001"])
        if kind == "schedule": return _table_values("generic_erp_records", "schedule_no", ["SCH001"])
        if kind == "group": return list(ONLINE_MODULE_GROUPS.keys()) if 'ONLINE_MODULE_GROUPS' in globals() else ["Admin","Master","CRM","HR"]
        if kind == "module_name": return all_online_module_names() if 'ONLINE_MODULE_GROUPS' in globals() else ["Dashboard","User Management","Company Profile"]
        if kind == "ledger": return get_ledger_names(None)
        if kind == "customer": return get_ledger_names("Sundry Debtors")
        if kind == "supplier": return get_ledger_names("Sundry Creditors")
        if kind == "payment_mode": return DEFAULT_PAYMENT_MODES
        if kind == "shift": return DEFAULT_SHIFTS
    except Exception:
        pass
    return []

def _selected_value(module_title, field):
    return st.session_state.get(f"gen_{module_title}_{field}")

def _render_generic_input(col, label, field, typ, module_title):
    opts = _generic_options(typ) if isinstance(typ, str) else None
    k=f"gen_{module_title}_{field}"
    if typ == "date": return str(col.date_input(label, value=india_now().date(), format="DD-MM-YYYY", key=k))
    if typ == "time": return str(col.time_input(label, value=india_now().time(), key=k))
    if typ == "number": return col.number_input(label, value=0.0, key=k)
    if typ == "bool": return col.checkbox(label, value=True, key=k)
    if typ == "password": return col.text_input(label, type="password", key=k)
    if typ == "module_name_by_group":
        g = _selected_value(module_title, "group_name") or "Dashboard"
        return col.selectbox(label, _all_module_names_for_group(g)+["Add New..."], key=k)
    if typ in ["company","user","employee","stock_item","finished_item","raw_material","unit","bom","plan","schedule","production_order","consumption_entry","fg_entry","group","module_name","ledger","customer","supplier","payment_mode","shift"]:
        values=_generic_lookup(typ)
        values=list(dict.fromkeys([str(v) for v in values if str(v).strip()]))+["Add New..."]
        return col.selectbox(label, values, key=k)
    # Auto-fill linked fields from selected stock item / party
    if field in ["item_code","hsn_code","unit","gst_rate","rate","available_qty"]:
        item = _selected_value(module_title,"item_name") or _selected_value(module_title,"finished_item") or _selected_value(module_title,"rm_item") or _selected_value(module_title,"raw_material")
        det=_stock_details_by_item(item)
        val=det.get(field, "")
        if field in ["gst_rate","rate","available_qty"]:
            try: return col.number_input(label, value=float(val or 0), key=k)
            except Exception: pass
        return col.text_input(label, value=str(val or ""), key=k)
    if field in ["customer_code","vendor_code","party_code","gst_no","pan_no"]:
        party = _selected_value(module_title,"customer_name") or _selected_value(module_title,"supplier_name") or _selected_value(module_title,"party_name") or _selected_value(module_title,"ledger_name")
        det=_ledger_details_by_name(party)
        val=det.get("party_code" if field in ["customer_code","vendor_code","party_code"] else field, "")
        return col.text_input(label, value=str(val or ""), key=k)
    if opts: return col.selectbox(label, opts + ["Add New..."], key=k)
    return col.text_input(label, key=k)

# More offline-style fields for modules mentioned by user.
_GENERIC_MODULE_FIELDS.update({
    "OneDrive Backup": [("company_code","Company Code","company"),("backup_date","Backup Date","date"),("backup_type","Backup Type",["Manual","Auto","Daily","Weekly","Monthly","Before Data Purge","Before Sync"]),("onedrive_folder_path","OneDrive Folder Path","text"),("backup_file_name","Backup File Name","text"),("backup_status","Backup Status",["Pending","Completed","Failed"]),("remarks","Remarks","text")],
    "OneDrive Backup Advanced": [("company_code","Company Code","company"),("backup_date","Backup Date","date"),("backup_type","Backup Type",["Full Backup","Database Backup","Reports Backup","Invoice Backup","Master Backup"]),("local_folder_path","Local Folder Path","text"),("onedrive_folder_path","OneDrive Folder Path","text"),("sync_direction","Sync Direction",["Local to OneDrive","OneDrive to Local","Two Way"]),("backup_status","Backup Status",["Pending","Completed","Failed"]),("remarks","Remarks","text")],
    "Data Export": [("company_code","Company Code","company"),("export_date","Export Date","date"),("module_name","Module Name","module_name"),("export_type","Export Type",["CSV","Excel","PDF","JSON","Full Backup"]),("export_folder_path","Export Folder Path","text"),("file_name","File Name","text"),("from_date","From Date","date"),("to_date","To Date","date"),("status","Status","status"),("remarks","Remarks","text")],
    "Export All Data": [("company_code","Company Code","company"),("export_date","Export Date","date"),("export_type","Export Type",["All CSV","All Excel","All JSON","Full ERP Backup"]),("export_folder_path","Export Folder Path","text"),("file_name","File Name","text"),("status","Status","status"),("remarks","Remarks","text")],
    "Data Import": [("company_code","Company Code","company"),("import_date","Import Date","date"),("module_name","Module Name","module_name"),("file_name","File Name","text"),("total_rows","Total Rows","number"),("success_rows","Success Rows","number"),("failed_rows","Failed Rows","number"),("status","Status","status"),("remarks","Remarks","text")],
    "WhatsApp Integration": [("company_code","Company Code","company"),("provider","WhatsApp Provider",["WhatsApp Web","Meta WhatsApp Cloud API","Twilio WhatsApp","Manual Link"]),("mobile_no","Mobile No","text"),("template_name","Template Name","text"),("message","Message","text"),("send_status","Send Status",["Draft","Ready","Sent","Failed"]),("remarks","Remarks","text")],
    "Email Integration": [("company_code","Company Code","company"),("email_provider","Email Provider",["Gmail SMTP","Office365 SMTP","Custom SMTP"]),("to_email","To Email","text"),("subject","Subject","text"),("message","Message","text"),("send_status","Send Status",["Draft","Ready","Sent","Failed"]),("remarks","Remarks","text")],
    "Email Utility": [("company_code","Company Code","company"),("email_type","Email Type",["Invoice","Payment Reminder","Quotation","Report","General"]),("to_email","To Email","text"),("subject","Subject","text"),("message","Message","text"),("attachment_path","Attachment Path","text"),("send_status","Send Status",["Draft","Ready","Sent","Failed"]),("remarks","Remarks","text")],
    "Stock Voucher": [("company_code","Company Code","company"),("voucher_no","Voucher No","text"),("voucher_date","Voucher Date","date"),("voucher_type","Voucher Type",STOCK_VOUCHER_TYPES),("item_name","Item Name","stock_item"),("item_code","Item Code","text"),("unit","Unit","unit"),("qty","Qty","number"),("rate","Rate","number"),("value","Value","number"),("status","Status","status"),("remarks","Remarks","text")],
    "Barcode Master": [("company_code","Company Code","company"),("barcode_no","Barcode No","text"),("item_name","Item Name","stock_item"),("item_code","Item Code","text"),("unit","Unit","unit"),("hsn_code","HSN Code","text"),("gst_rate","GST Rate %","number"),("batch_no","Batch No","text"),("mfg_date","MFG Date","date"),("expiry_date","Expiry Date","date"),("mrp","MRP","number"),("selling_rate","Selling Rate","number"),("qty","Qty","number"),("status","Status","status")],
    "Warehouse Stock": [("company_code","Company Code","company"),("warehouse_name","Warehouse Name","text"),("item_name","Item Name","stock_item"),("item_code","Item Code","text"),("unit","Unit","unit"),("available_qty","Available Qty","number"),("opening_qty","Opening Qty","number"),("inward_qty","Inward Qty","number"),("outward_qty","Outward Qty","number"),("closing_qty","Closing Qty","number"),("rate","Rate","number"),("value","Value","number")],
    "BOM Lines": [("company_code","Company Code","company"),("bom_no","BOM No","bom"),("rm_item","Raw Material Item","stock_item"),("item_code","Item Code","text"),("unit","Unit","unit"),("available_qty","Available Qty","number"),("rm_qty","RM Qty","number"),("rm_rate","RM Rate","number"),("rm_amount","RM Amount","number"),("remarks","Remarks","text")],
    "Production Schedule": [("company_code","Company Code","company"),("schedule_no","Schedule No","text"),("schedule_date","Schedule Date","date"),("production_order_no","Production Order No","production_order"),("finished_item","Finished Item","stock_item"),("item_code","Item Code","text"),("qty_scheduled","Qty Scheduled","number"),("machine_name","Machine Name","text"),("shift_name","Shift Name","shift"),("schedule_status","Schedule Status","status")],
    "Capacity Planning": [("company_code","Company Code","company"),("plan_date","Plan Date","date"),("production_order_no","Production Order No","production_order"),("machine_name","Machine Name","text"),("shift","Shift","shift"),("available_hours","Available Hours","number"),("planned_hours","Planned Hours","number"),("free_capacity","Free Capacity","number"),("status","Status","status"),("remarks","Remarks","text")],
})

def whatsapp_integration_page():
    show_header("✅✅ WhatsApp Integration", "section-tools")
    st.info("WhatsApp setting email jaisa nahi hai. Yahan WhatsApp Web link / WhatsApp Business API provider configure hota hai.")
    c1,c2=st.columns(2)
    provider=c1.selectbox("Provider", ["WhatsApp Web", "Meta WhatsApp Cloud API", "Twilio WhatsApp", "Manual Only"])
    mobile=c2.text_input("Test Mobile No with country code", placeholder="9198xxxxxxxx")
    msg=st.text_area("Test Message", value="Namaste, this is test message from RBM ERP.")
    if st.button("Open WhatsApp Test Message", use_container_width=True):
        url=f"https://wa.me/{mobile}?text={quote(msg)}" if mobile else ""
        if url: st.markdown(f"[Open WhatsApp]({url})")
        else: st.warning("Mobile no required.")
    online_generic_module("WhatsApp Integration")

def email_integration_page():
    email_sms_settings()
    online_generic_module("Email Integration")

def get_module_mapping():
    m = globals().get('_ORIGINAL_GET_MODULE_MAPPING_FOR_PATCH5')
    # Build from prior function saved below if available, otherwise use existing body through old reference.
    base = _PATCH5_OLD_GET_MODULE_MAPPING()
    base["WhatsApp Integration"] = whatsapp_integration_page
    base["Email Integration"] = email_integration_page
    base["Email Utility"] = email_integration_page
    base["OneDrive Backup"] = lambda: online_generic_module("OneDrive Backup")
    base["OneDrive Backup Advanced"] = lambda: online_generic_module("OneDrive Backup Advanced")
    base["Data Export"] = lambda: online_generic_module("Data Export")
    base["Export All Data"] = lambda: online_generic_module("Export All Data")
    base["Stock Voucher"] = lambda: online_generic_module("Stock Voucher")
    return base

# ================= END PATCH 5 =================



# ================= PATCH 6: ALL OPTION + GROUP-WISE MODULE DROPDOWN FIX =================
# Fix requested screens: Data Purge Control, Data Locking Period, Mandatory Field Settings,
# Client Module Permission. Group dropdown has All, and Module Name dropdown shows modules of
# selected Group, not only Dashboard / not group names.

def _with_all(options):
    out = []
    for x in (options or []):
        sx = str(x).strip()
        if sx and sx not in out:
            out.append(sx)
    if "All" not in out:
        out.insert(0, "All")
    return out


def _all_module_names_for_group(group_name):
    try:
        group_name = str(group_name or "All").strip()
        if group_name in ["All", "", "None"]:
            return _with_all(all_online_module_names())
        mods = ONLINE_MODULE_GROUPS.get(group_name, []) if 'ONLINE_MODULE_GROUPS' in globals() else []
        return _with_all(mods)
    except Exception:
        return ["All", "Dashboard"]


def _generic_lookup(kind):
    try:
        if kind == "company": return _with_all(_company_codes())
        if kind == "user": return _with_all(_table_values("users", "username", [current_user()]))
        if kind == "employee": return _with_all(_table_values("employees", "employee_name", ["Sample Employee"]))
        if kind in ["stock_item", "finished_item", "raw_material"]: return _with_all(get_stock_items())
        if kind == "unit": return _with_all(_table_values("stock_ledgers", "unit", DEFAULT_UNITS))
        if kind == "bom": return _with_all(_table_values("bom_headers", "bom_no", ["BOM001"]))
        if kind == "production_order": return _with_all(_table_values("production_orders", "order_no", ["PO-001"]))
        if kind == "consumption_entry": return _with_all(_table_values("consumption_entries", "entry_no", ["CE-001"]))
        if kind == "fg_entry": return _with_all(_table_values("fg_entries", "entry_no", ["FG-001"]))
        if kind == "plan": return _with_all(_table_values("mrp", "plan_no", ["PLAN001"]))
        if kind == "schedule": return _with_all(_table_values("generic_erp_records", "schedule_no", ["SCH001"]))
        if kind == "group": return _with_all(list(ONLINE_MODULE_GROUPS.keys()) if 'ONLINE_MODULE_GROUPS' in globals() else ["Admin","Master","CRM","HR"])
        if kind == "module_name": return _with_all(all_online_module_names() if 'ONLINE_MODULE_GROUPS' in globals() else ["Dashboard","User Management","Company Profile"])
        if kind == "ledger": return _with_all(get_ledger_names(None))
        if kind == "customer": return _with_all(get_ledger_names("Sundry Debtors"))
        if kind == "supplier": return _with_all(get_ledger_names("Sundry Creditors"))
        if kind == "payment_mode": return _with_all(DEFAULT_PAYMENT_MODES)
        if kind == "shift": return _with_all(DEFAULT_SHIFTS)
    except Exception:
        pass
    return ["All"]


def _render_generic_input(col, label, field, typ, module_title):
    opts = _generic_options(typ) if isinstance(typ, str) else None
    k=f"gen_{module_title}_{field}"
    if typ == "date": return str(col.date_input(label, value=india_now().date(), format="DD-MM-YYYY", key=k))
    if typ == "time": return str(col.time_input(label, value=india_now().time(), key=k))
    if typ == "number": return col.number_input(label, value=0.0, key=k)
    if typ == "bool": return col.checkbox(label, value=True, key=k)
    if typ == "password": return col.text_input(label, type="password", key=k)
    if typ == "module_name_by_group":
        # Read current Group Name selectbox value. If user changes group, Streamlit reruns and this
        # list will automatically become that group's modules.
        g = st.session_state.get(f"gen_{module_title}_group_name", "All")
        values = _all_module_names_for_group(g)
        values = values + (["Add New..."] if "Add New..." not in values else [])
        return col.selectbox(label, values, key=k)
    if typ in ["company","user","employee","stock_item","finished_item","raw_material","unit","bom","plan","schedule","production_order","consumption_entry","fg_entry","group","module_name","ledger","customer","supplier","payment_mode","shift"]:
        values=_generic_lookup(typ)
        values=list(dict.fromkeys([str(v) for v in values if str(v).strip()]))
        if "Add New..." not in values:
            values.append("Add New...")
        return col.selectbox(label, values, key=k)
    # Auto-fill linked fields from selected stock item / party
    if field in ["item_code","hsn_code","unit","gst_rate","rate","available_qty"]:
        item = _selected_value(module_title,"item_name") or _selected_value(module_title,"finished_item") or _selected_value(module_title,"rm_item") or _selected_value(module_title,"raw_material")
        det=_stock_details_by_item(item)
        val=det.get(field, "")
        if field in ["gst_rate","rate","available_qty"]:
            try: return col.number_input(label, value=float(val or 0), key=k)
            except Exception: pass
        return col.text_input(label, value=str(val or ""), key=k)
    if field in ["customer_code","vendor_code","party_code","gst_no","pan_no"]:
        party = _selected_value(module_title,"customer_name") or _selected_value(module_title,"supplier_name") or _selected_value(module_title,"party_name") or _selected_value(module_title,"ledger_name")
        det=_ledger_details_by_name(party)
        val=det.get("party_code" if field in ["customer_code","vendor_code","party_code"] else field, "")
        return col.text_input(label, value=str(val or ""), key=k)
    if opts:
        values = _with_all(opts)
        if "Add New..." not in values:
            values.append("Add New...")
        return col.selectbox(label, values, key=k)
    return col.text_input(label, key=k)

# Force these Admin screens to use group-wise module dropdown after all older patches.
_GENERIC_MODULE_FIELDS.update({
    "Data Purge Control": [("company_code","Company Code","company"),("request_date","Request Date","date"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("from_date","From Date","date"),("to_date","To Date","date"),("purge_status","Purge Status",["All","Requested","Approved","Rejected","Completed"]),("requested_by","Requested By","user"),("remarks","Remarks","text")],
    "Data Locking Period": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("lock_from_date","Lock From Date","date"),("lock_to_date","Lock To Date","date"),("lock_status","Lock Status",["All","Locked","Not Locked","Pending"]),("reason","Reason","text")],
    "Mandatory Field Settings": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("field_name","Field Name","text"),("is_mandatory","Is Mandatory","bool"),("status","Status",["All","Active","Inactive"]),("remarks","Remarks","text")],
    "Client Module Permission": [("company_code","Company Code","company"),("group_name","Group Name","group"),("module_name","Module Name","module_name_by_group"),("allowed","Allowed","bool"),("status","Status",["All","Active","Inactive"]),("remarks","Remarks","text")],
})

# ================= END PATCH 6 =================



# ================= PATCH 12: ROLE BASED SECURITY EXACT SCREEN FIX =================
# Requirement: Role Permission Control screen same. Role Based Security screen same also,
# only Select Role dropdown must show USERNAME from User Management.

def _rbm_username_list_for_client(selected_client):
    """Return usernames created in User Management for Role Based Security.
    Robust fallback: first selected client, then current login client, then all users.
    """
    usernames = []
    try:
        df = safe_df(load_table("users", 5000))
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "username" in df.columns:
        try:
            df2 = df.copy()
            if "client_code" in df2.columns and str(selected_client) not in ["", "All"]:
                filtered = df2[df2["client_code"].astype(str).str.strip() == str(selected_client).strip()]
                if filtered.empty and st.session_state.get("client_code"):
                    filtered = df2[df2["client_code"].astype(str).str.strip() == str(st.session_state.get("client_code")).strip()]
                if not filtered.empty:
                    df2 = filtered
            if not is_super_admin() and "role" in df2.columns:
                df2 = df2[~df2["role"].astype(str).isin(["Developer", "Super Admin"])]
            usernames = [str(x).strip() for x in df2["username"].dropna().unique().tolist() if str(x).strip()]
        except Exception:
            usernames = []

    # Final fallback: direct Supabase select, then all usernames.
    if not usernames:
        try:
            data = supabase.table("users").select("username,client_code,role").execute().data or []
            df3 = safe_df(data)
            if not df3.empty and "username" in df3.columns:
                if "client_code" in df3.columns and str(selected_client) not in ["", "All"]:
                    filtered = df3[df3["client_code"].astype(str).str.strip() == str(selected_client).strip()]
                    if not filtered.empty:
                        df3 = filtered
                if not is_super_admin() and "role" in df3.columns:
                    df3 = df3[~df3["role"].astype(str).isin(["Developer", "Super Admin"])]
                usernames = [str(x).strip() for x in df3["username"].dropna().unique().tolist() if str(x).strip()]
        except Exception:
            usernames = []

    # Remove duplicates but keep order.
    return list(dict.fromkeys(usernames))

def _rbm_client_code_options_for_security():
    try:
        if is_super_admin():
            df = safe_df(load_table("clients", 2000))
            vals = []
            if not df.empty and "client_code" in df.columns:
                vals = [str(x) for x in df["client_code"].dropna().unique().tolist() if str(x).strip()]
            vals = list(dict.fromkeys(["RBM"] + vals))
            return vals or ["RBM"]
        return [get_client_code()]
    except Exception:
        return [st.session_state.get("client_code", "RBM")]


def _rbm_enabled_modules_for_permission(selected_client):
    out = []
    for module in ERP_MODULES:
        if not module or module == "No module available":
            continue
        if (not is_super_admin()) and module in SUPER_ADMIN_ONLY_MODULES:
            continue
        # Keep safe: if feature check fails, still show module to avoid blank/error screen.
        try:
            if not module_enabled_for_client_code(module, selected_client):
                continue
        except Exception:
            pass
        out.append(module)
    return out or ["Dashboard"]


def role_based_security_control():
    show_header("Role Based Security", "section-admin")
    if st.session_state.get("role") not in ["Developer", "Super Admin", "Client Super Admin", "Admin"]:
        st.warning("Only Developer, Super Admin, Client Super Admin or Admin can access Role Based Security.")
        return

    st.info("Role Based Security = username/login wise permission. Same as Role Permission Control; only Select Role dropdown shows username created in User Management.")

    selected_client = st.selectbox("Select Client", _rbm_client_code_options_for_security(), key="rbs_fixed_client")
    usernames = _rbm_username_list_for_client(selected_client)
    if not usernames:
        st.warning("No username found for this client. First create username in User Management.")
        return

    selected_username = st.selectbox("Select Username", usernames, key="rbs_fixed_username")

    try:
        existing = safe_df(
            supabase.table("user_permissions")
            .select("*")
            .eq("client_code", selected_client)
            .eq("username", selected_username)
            .execute().data
        )
    except Exception:
        existing = pd.DataFrame()
        st.warning("user_permissions table missing or not accessible. Run supabase_required_patch.sql once if save is required.")

    modules = _rbm_enabled_modules_for_permission(selected_client)
    perm_rows = []
    with st.form("role_based_security_exact_username_form"):
        st.markdown("### Module Permissions")
        header = st.columns([2.5,1,1,1,1,1,1,1,1])
        header[0].markdown("**Module**")
        for i, act in enumerate(PERMISSION_ACTIONS, start=1):
            header[i].markdown(f"**{act.title()}**")

        for module in modules:
            current = pd.DataFrame()
            if not existing.empty and "module_name" in existing.columns:
                current = existing[existing["module_name"].astype(str) == str(module)]
            cols = st.columns([2.5,1,1,1,1,1,1,1,1])
            cols[0].write(module)
            row = {"module_name": module}
            for i, act in enumerate(PERMISSION_ACTIONS, start=1):
                colname = f"can_{act}"
                if not current.empty and colname in current.columns:
                    default_val = bool(current.iloc[0].get(colname, default_permission(module, act)))
                else:
                    default_val = default_permission(module, act)
                row[colname] = cols[i].checkbox("", value=default_val, key=f"rbs_exact_{selected_client}_{selected_username}_{module}_{act}")
            perm_rows.append(row)

        save_btn = st.form_submit_button("Save Role Based Security", use_container_width=True)

    if save_btn:
        try:
            supabase.table("user_permissions").delete().eq("client_code", selected_client).eq("username", selected_username).execute()
            rows = []
            for r in perm_rows:
                rec = {"client_code": selected_client, "username": selected_username, "created_by": current_user()}
                rec.update(r)
                rows.append(rec)
            if rows:
                supabase.table("user_permissions").insert(rows).execute()
            try:
                write_audit_log("Role Based Security", "UPDATE", "", f"Saved username wise permission for {selected_client} / {selected_username}")
            except Exception:
                pass
            st.success("Role Based Security saved successfully for selected username.")
            st.rerun()
        except Exception as e:
            st.error(f"Unable to save Role Based Security. Run updated SQL patch if needed. Error: {e}")

    st.divider()
    try:
        df = safe_df(load_table("user_permissions", 2000))
        if not df.empty:
            if "client_code" in df.columns:
                df = df[df["client_code"].astype(str) == str(selected_client)]
            if "username" in df.columns:
                df = df[df["username"].astype(str) == str(selected_username)]
            st.markdown("### Saved Role Based Security")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No saved username-wise permission found yet.")
    except Exception:
        st.info("Saved Role Based Security list will show after user_permissions table is created.")

# Make sure mapping always uses the fixed function above.
_OLD_GET_MODULE_MAPPING_PATCH12 = get_module_mapping
def get_module_mapping():
    base = _OLD_GET_MODULE_MAPPING_PATCH12()
    base["Role Based Security"] = role_based_security_control
    return base
# ================= END PATCH 12 =================



# ================= PATCH 19: OFFLINE SAME FIELDS + REPORT FORMAT + PRINT PREVIEW =================
# This patch keeps previous working code unchanged and only overrides the generic field layout/report screens.

def _rbm_patch19_all_status_options():
    return ["All", "Active", "Inactive", "Draft", "Parked", "Posted", "Pending", "Approved", "Rejected", "Completed", "Closed", "Cancelled", "Add New..."]

_OLD_GENERIC_OPTIONS_PATCH19 = _generic_options
def _generic_options(label):
    if str(label).lower() == "status":
        return ["Active", "Inactive", "Draft", "Parked", "Posted", "Pending", "Approved", "Rejected", "Completed", "Closed", "Cancelled"]
    return _OLD_GENERIC_OPTIONS_PATCH19(label)

_OFFLINE_SAME_FIELDS_PATCH19 = {'Financial Year Master': [('company_code', 'Company Code', 'company'), ('fy_name', 'Fy Name', 'text'), ('start_date', 'Start Date', 'date'), ('end_date', 'End Date', 'date'), ('status', 'Status', 'status'), ('lock_status', 'Lock Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Cost Center Master': [('company_code', 'Company Code', 'company'), ('cost_center_name', 'Cost Center Name', 'text'), ('department', 'Department', 'text'), ('location', 'Location', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Inventory Item Master': [('item_code', 'Item Code', 'text'), ('barcode_no', 'Barcode No', 'text'), ('item_name', 'Item Name', 'stock_item'), ('stock_group', 'Stock Group', 'text'), ('unit', 'Unit', 'text'), ('hsn_sac', 'HSN/SAC', 'text'), ('gst_rate', 'Gst Rate', 'number'), ('reorder_level', 'Reorder Level', 'number'), ('opening_qty', 'Opening Qty', 'number'), ('opening_rate', 'Opening Rate', 'number'), ('opening_value', 'Opening Value', 'number'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'BOM Header': [('company_code', 'Company Code', 'company'), ('bom_no', 'Bom No', 'bom'), ('bom_date', 'Bom Date', 'date'), ('fg_item', 'Fg Item', 'stock_item'), ('fg_qty', 'Fg Qty', 'number'), ('labour_cost', 'Labour Cost', 'text'), ('power_cost', 'Power Cost', 'text'), ('packing_cost', 'Packing Cost', 'text'), ('other_cost', 'Other Cost', 'text'), ('material_cost', 'Material Cost', 'text'), ('total_cost', 'Total Cost', 'number'), ('cost_per_unit', 'Cost Per Unit', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'BOM Lines': [('company_code', 'Company Code', 'company'), ('bom_header_id', 'Bom Header Id', 'bom'), ('bom_no', 'Bom No', 'bom'), ('rm_item', 'Rm Item', 'stock_item'), ('rm_qty', 'Rm Qty', 'number'), ('rm_rate', 'Rm Rate', 'number'), ('rm_amount', 'Rm Amount', 'number'), ('unit', 'Unit', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Production Orders': [('company_code', 'Company Code', 'company'), ('order_no', 'Order No', 'plan'), ('order_date', 'Order Date', 'date'), ('bom_no', 'Bom No', 'bom'), ('fg_item', 'Fg Item', 'stock_item'), ('planned_qty', 'Planned Qty', 'number'), ('due_date', 'Due Date', 'date'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Production Entries': [('company_code', 'Company Code', 'company'), ('entry_no', 'Entry No', 'text'), ('entry_date', 'Entry Date', 'date'), ('order_no', 'Order No', 'plan'), ('fg_item', 'Fg Item', 'stock_item'), ('produced_qty', 'Produced Qty', 'number'), ('warehouse', 'Warehouse', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Consumption Entries': [('company_code', 'Company Code', 'company'), ('entry_no', 'Entry No', 'text'), ('entry_date', 'Entry Date', 'date'), ('order_no', 'Order No', 'plan'), ('rm_item', 'Rm Item', 'stock_item'), ('consumed_qty', 'Consumed Qty', 'number'), ('rate', 'Rate', 'number'), ('amount', 'Amount', 'number'), ('warehouse', 'Warehouse', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'FG Entries': [('company_code', 'Company Code', 'company'), ('entry_no', 'Entry No', 'text'), ('entry_date', 'Entry Date', 'date'), ('fg_item', 'Fg Item', 'stock_item'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('amount', 'Amount', 'number'), ('warehouse', 'Warehouse', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Production Costing': [('company_code', 'Company Code', 'company'), ('costing_no', 'Costing No', 'text'), ('costing_date', 'Costing Date', 'date'), ('order_no', 'Order No', 'plan'), ('fg_item', 'Fg Item', 'stock_item'), ('material_cost', 'Material Cost', 'text'), ('labour_cost', 'Labour Cost', 'text'), ('overhead_cost', 'Overhead Cost', 'text'), ('total_cost', 'Total Cost', 'number'), ('qty', 'Qty', 'number'), ('cost_per_unit', 'Cost Per Unit', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'MRP': [('company_code', 'Company Code', 'company'), ('plan_no', 'Plan No', 'plan'), ('plan_date', 'Plan Date', 'date'), ('fg_item', 'Fg Item', 'stock_item'), ('required_qty', 'Required Qty', 'number'), ('bom_no', 'Bom No', 'bom'), ('rm_item', 'Rm Item', 'stock_item'), ('rm_required_qty', 'Rm Required Qty', 'number'), ('available_qty', 'Available Qty', 'number'), ('shortage_qty', 'Shortage Qty', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Payroll Salary Structure': [('employee_id', 'Employee Id', 'user'), ('employee_name', 'Employee Name', 'user'), ('basic_salary', 'Basic Salary', 'number'), ('hra', 'HRA', 'text'), ('conveyance', 'Conveyance', 'text'), ('special_allowance', 'Special Allowance', 'number'), ('pf_applicable', 'Pf Applicable', 'number'), ('esi_applicable', 'Esi Applicable', 'number'), ('pt_applicable', 'Pt Applicable', 'number'), ('tds_applicable', 'Tds Applicable', 'number'), ('gross_salary', 'Gross Salary', 'number'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Payroll Processing': [('payroll_month', 'Payroll Month', 'text'), ('employee_id', 'Employee Id', 'user'), ('employee_name', 'Employee Name', 'user'), ('present_days', 'Present Days', 'number'), ('paid_days', 'Paid Days', 'number'), ('basic_salary', 'Basic Salary', 'number'), ('allowances', 'Allowances', 'number'), ('overtime', 'Overtime', 'number'), ('deductions', 'Deductions', 'number'), ('pf', 'PF', 'number'), ('esi', 'ESI', 'number'), ('pt', 'PT', 'number'), ('tds', 'TDS', 'number'), ('net_salary', 'Net Salary', 'number'), ('payment_status', 'Payment Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Payroll Payslip': [('payslip_no', 'Payslip No', 'text'), ('payroll_month', 'Payroll Month', 'text'), ('employee_id', 'Employee Id', 'user'), ('employee_name', 'Employee Name', 'user'), ('gross_salary', 'Gross Salary', 'number'), ('total_deduction', 'Total Deduction', 'number'), ('net_salary', 'Net Salary', 'number'), ('payment_date', 'Payment Date', 'date'), ('bank_name', 'Bank Name', 'text'), ('reference_no', 'Reference No', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Barcode Master': [('barcode_no', 'Barcode No', 'text'), ('item_code', 'Item Code', 'text'), ('item_name', 'Item Name', 'stock_item'), ('batch_no', 'Batch No', 'text'), ('mfg_date', 'Mfg Date', 'date'), ('expiry_date', 'Expiry Date', 'date'), ('mrp', 'MRP', 'number'), ('selling_rate', 'Selling Rate', 'number'), ('qty', 'Qty', 'number'), ('warehouse', 'Warehouse', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Barcode Print Log': [('print_date', 'Print Date', 'date'), ('barcode_no', 'Barcode No', 'text'), ('item_code', 'Item Code', 'text'), ('item_name', 'Item Name', 'stock_item'), ('qty_printed', 'Qty Printed', 'number'), ('printed_by', 'Printed By', 'user'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Warehouse Stock': [('warehouse_code', 'Warehouse Code', 'text'), ('warehouse_name', 'Warehouse Name', 'text'), ('item_code', 'Item Code', 'text'), ('item_name', 'Item Name', 'stock_item'), ('opening_qty', 'Opening Qty', 'number'), ('inward_qty', 'Inward Qty', 'number'), ('outward_qty', 'Outward Qty', 'number'), ('closing_qty', 'Closing Qty', 'number'), ('rate', 'Rate', 'number'), ('value', 'Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Production Planning': [('plan_no', 'Plan No', 'plan'), ('plan_date', 'Plan Date', 'date'), ('finished_item', 'Finished Item', 'stock_item'), ('planned_qty', 'Planned Qty', 'number'), ('bom_no', 'Bom No', 'bom'), ('start_date', 'Start Date', 'date'), ('end_date', 'End Date', 'date'), ('machine_name', 'Machine Name', 'text'), ('supervisor', 'Supervisor', 'user'), ('plan_status', 'Plan Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Production Schedule': [('schedule_no', 'Schedule No', 'text'), ('schedule_date', 'Schedule Date', 'date'), ('plan_no', 'Plan No', 'plan'), ('shift', 'Shift', 'text'), ('machine_name', 'Machine Name', 'text'), ('operator_name', 'Operator Name', 'user'), ('item_name', 'Item Name', 'stock_item'), ('planned_qty', 'Planned Qty', 'number'), ('actual_qty', 'Actual Qty', 'number'), ('variance_qty', 'Variance Qty', 'number'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Profit Loss': [('company_code', 'Company Code', 'company'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('particular', 'Particular', 'text'), ('income', 'Income', 'number'), ('expense', 'Expense', 'number'), ('profit_loss', 'Profit Loss', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Balance Sheet': [('company_code', 'Company Code', 'company'), ('as_on_date', 'As On Date', 'date'), ('particular', 'Particular', 'text'), ('assets', 'Assets', 'text'), ('liabilities', 'Liabilities', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Trial Balance': [('company_code', 'Company Code', 'company'), ('report_date', 'Report Date', 'date'), ('ledger_name', 'Ledger Name', 'text'), ('debit', 'Debit', 'number'), ('credit', 'Credit', 'number'), ('closing_balance', 'Closing Balance', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Sundry Receivable': [('company_code', 'Company Code', 'company'), ('as_on_date', 'As On Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('opening', 'Opening', 'number'), ('debit', 'Debit', 'number'), ('credit', 'Credit', 'number'), ('closing', 'Closing', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Sundry Payable': [('company_code', 'Company Code', 'company'), ('as_on_date', 'As On Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('opening', 'Opening', 'number'), ('debit', 'Debit', 'number'), ('credit', 'Credit', 'number'), ('closing', 'Closing', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Stock Report': [('company_code', 'Company Code', 'company'), ('as_on_date', 'As On Date', 'date'), ('item_name', 'Item Name', 'stock_item'), ('opening_stock', 'Opening Stock', 'number'), ('purchase', 'Purchase', 'text'), ('consumption', 'Consumption', 'number'), ('closing_stock', 'Closing Stock', 'number'), ('value', 'Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Gst Report': [('company_code', 'Company Code', 'company'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('gst_no', 'GST No', 'text'), ('taxable_value', 'Taxable Value', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_gst', 'Total Gst', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Tds Report': [('company_code', 'Company Code', 'company'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('section', 'Section', 'text'), ('party_name', 'Party Name', 'text'), ('amount', 'Amount', 'number'), ('tds', 'TDS', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Company Profile': [('company_code', 'Company Code', 'company'), ('company_name', 'Company Name', 'text'), ('legal_name', 'Legal Name', 'text'), ('gst_no', 'GST No', 'text'), ('pan_no', 'PAN No', 'text'), ('tan_no', 'TAN No', 'text'), ('address', 'Address', 'text'), ('state', 'State', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('financial_year_start', 'Financial Year Start', 'text'), ('books_start_date', 'Books Start Date', 'date'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Financial Year': [('company_code', 'Company Code', 'company'), ('fy_name', 'Fy Name', 'text'), ('start_date', 'Start Date', 'date'), ('end_date', 'End Date', 'date'), ('status', 'Status', 'status'), ('lock_status', 'Lock Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Cost Centers': [('company_code', 'Company Code', 'company'), ('cost_center_name', 'Cost Center Name', 'text'), ('department', 'Department', 'text'), ('location', 'Location', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Document Series': [('company_code', 'Company Code', 'company'), ('module_name', 'Module Name', 'module_name'), ('prefix', 'Prefix', 'text'), ('next_no', 'Next No', 'text'), ('suffix', 'Suffix', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'GST Settings': [('company_code', 'Company Code', 'company'), ('gst_no', 'GST No', 'text'), ('legal_name', 'Legal Name', 'text'), ('state', 'State', 'text'), ('registration_type', 'Registration Type', 'text'), ('default_tax_type', 'Default Tax Type', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Ledger Group Master': [('company_code', 'Company Code', 'company'), ('group_name', 'Group Name', 'group'), ('group_type', 'Group Type', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Ledger Master': [('company_code', 'Company Code', 'company'), ('ledger_name', 'Ledger Name', 'text'), ('ledger_group', 'Ledger Group', 'text'), ('address', 'Address', 'text'), ('contact_no', 'Contact No', 'text'), ('email', 'Email', 'text'), ('tan_no', 'TAN No', 'text'), ('gst_no', 'GST No', 'text'), ('pan_no', 'PAN No', 'text'), ('opening_balance', 'Opening Balance', 'number'), ('balance_type', 'Balance Type', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Stock Group Master': [('company_code', 'Company Code', 'company'), ('stock_group_name', 'Stock Group Name', 'text'), ('stock_type', 'Stock Type', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Stock Ledger Master': [('company_code', 'Company Code', 'company'), ('item_name', 'Item Name', 'stock_item'), ('item_code', 'Item Code', 'text'), ('stock_group', 'Stock Group', 'text'), ('unit', 'Unit', 'text'), ('hsn_code', 'Hsn Code', 'text'), ('opening_qty', 'Opening Qty', 'number'), ('opening_rate', 'Opening Rate', 'number'), ('opening_value', 'Opening Value', 'number'), ('gst_rate', 'Gst Rate', 'number'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Client Master': [('company_code', 'Company Code', 'company'), ('client_name', 'Client Name', 'text'), ('allow_master_group', 'Allow Master Group', 'text'), ('allow_task', 'Allow Task', 'text'), ('allow_attendance', 'Allow Attendance', 'text'), ('allow_inout', 'Allow Inout', 'text'), ('allow_visitor', 'Allow Visitor', 'text'), ('allow_appointment', 'Allow Appointment', 'text'), ('allow_stock_raw', 'Allow Stock Raw', 'text'), ('allow_stock_fg', 'Allow Stock Fg', 'text'), ('allow_stock_wip', 'Allow Stock Wip', 'text'), ('allow_sales', 'Allow Sales', 'text'), ('allow_purchase', 'Allow Purchase', 'text'), ('allow_expense', 'Allow Expense', 'number'), ('allow_service_voucher', 'Allow Service Voucher', 'text'), ('allow_fixed_assets', 'Allow Fixed Assets', 'text'), ('allow_accounting', 'Allow Accounting', 'text'), ('allow_excel_upload', 'Allow Excel Upload', 'text'), ('allow_google_sheet_import', 'Allow Google Sheet Import', 'text'), ('allow_quotation', 'Allow Quotation', 'text'), ('allow_manufacturing', 'Allow Manufacturing', 'text'), ('allow_project_accounting', 'Allow Project Accounting', 'text'), ('allow_subscription', 'Allow Subscription', 'number'), ('allow_support', 'Allow Support', 'text'), ('allow_license_manager', 'Allow License Manager', 'text'), ('allow_admin', 'Allow Admin', 'text'), ('allow_master', 'Allow Master', 'text'), ('allow_crm', 'Allow Crm', 'text'), ('allow_hr', 'Allow Hr', 'text'), ('allow_inventory', 'Allow Inventory', 'text'), ('allow_barcode', 'Allow Barcode', 'text'), ('allow_manufacturing_bom', 'Allow Manufacturing Bom', 'text'), ('allow_production_planning', 'Allow Production Planning', 'text'), ('allow_hr_payroll', 'Allow Hr Payroll', 'text'), ('allow_asset_management', 'Allow Asset Management', 'text'), ('allow_document_management', 'Allow Document Management', 'text'), ('allow_audit_management', 'Allow Audit Management', 'text'), ('allow_ai_chat_assistant', 'Allow Ai Chat Assistant', 'text'), ('allow_whatsapp_integration', 'Allow Whatsapp Integration', 'text'), ('allow_email_integration', 'Allow Email Integration', 'text'), ('allow_onedrive_backup', 'Allow Onedrive Backup', 'text'), ('allow_mobile_app_sync', 'Allow Mobile App Sync', 'text'), ('allow_multi_company', 'Allow Multi Company', 'text'), ('allow_multi_branch', 'Allow Multi Branch', 'text'), ('allow_role_based_security', 'Allow Role Based Security', 'text'), ('allow_dashboard_analytics', 'Allow Dashboard Analytics', 'text'), ('allow_chairman_mis', 'Allow Chairman Mis', 'text'), ('allow_sales_order', 'Allow Sales Order', 'text'), ('allow_purchase_order', 'Allow Purchase Order', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'User Management': [('company_code', 'Company Code', 'company'), ('username', 'Username', 'text'), ('password', 'Password', 'text'), ('role', 'Role', 'text'), ('full_name', 'Full Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Role Permission Control': [('company_code', 'Company Code', 'company'), ('username', 'Username', 'text'), ('role_name', 'Role Name', 'text'), ('module_name', 'Module Name', 'module_name'), ('can_view', 'Can View', 'text'), ('can_add', 'Can Add', 'text'), ('can_edit', 'Can Edit', 'text'), ('can_delete', 'Can Delete', 'text'), ('can_reverse', 'Can Reverse', 'text'), ('can_approve', 'Can Approve', 'text'), ('can_print', 'Can Print', 'text'), ('can_export', 'Can Export', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Audit Log': [('company_code', 'Company Code', 'company'), ('action_date', 'Action Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('action_type', 'Action Type', 'text'), ('record_id', 'Record Id', 'text'), ('details', 'Details', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Employee Master': [('company_code', 'Company Code', 'company'), ('employee_id', 'Employee Id', 'user'), ('employee_name', 'Employee Name', 'user'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('department', 'Department', 'text'), ('designation', 'Designation', 'number'), ('branch_division', 'Branch Division', 'text'), ('employee_photo', 'Employee Photo', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Attendance': [('company_code', 'Company Code', 'company'), ('attendance_date', 'Attendance Date', 'date'), ('financial_year', 'Financial Year', 'text'), ('employee_name', 'Employee Name', 'user'), ('attendance_type', 'Attendance Type', 'text'), ('office_location', 'Office Location', 'text'), ('status', 'Status', 'status'), ('in_time', 'In Time', 'text'), ('out_time', 'Out Time', 'text'), ('working_hours', 'Working Hours', 'number'), ('in_latitude', 'In Latitude', 'text'), ('in_longitude', 'In Longitude', 'text'), ('out_latitude', 'Out Latitude', 'text'), ('out_longitude', 'Out Longitude', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Attendance Visits': [('company_code', 'Company Code', 'company'), ('visit_date', 'Visit Date', 'date'), ('financial_year', 'Financial Year', 'text'), ('employee_name', 'Employee Name', 'user'), ('visit_place', 'Visit Place', 'text'), ('in_time', 'In Time', 'text'), ('out_time', 'Out Time', 'text'), ('in_latitude', 'In Latitude', 'text'), ('in_longitude', 'In Longitude', 'text'), ('out_latitude', 'Out Latitude', 'text'), ('out_longitude', 'Out Longitude', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'IN / OUT Register': [('company_code', 'Company Code', 'company'), ('entry_date', 'Entry Date', 'date'), ('financial_year', 'Financial Year', 'text'), ('person_name', 'Person Name', 'text'), ('purpose', 'Purpose', 'text'), ('in_time', 'In Time', 'text'), ('out_time', 'Out Time', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Visitor Register': [('company_code', 'Company Code', 'company'), ('visit_date', 'Visit Date', 'date'), ('financial_year', 'Financial Year', 'text'), ('visitor_name', 'Visitor Name', 'text'), ('mobile', 'Mobile', 'text'), ('company', 'Company', 'text'), ('meeting_with', 'Meeting With', 'text'), ('purpose', 'Purpose', 'text'), ('in_time', 'In Time', 'text'), ('out_time', 'Out Time', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Task Delegation': [('company_code', 'Company Code', 'company'), ('task_date', 'Task Date', 'date'), ('financial_year', 'Financial Year', 'text'), ('branch_division', 'Branch Division', 'text'), ('task', 'Task', 'text'), ('assigned_to', 'Assigned To', 'user'), ('priority', 'Priority', 'text'), ('due_date', 'Due Date', 'date'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('task_photo_name', 'Task Photo Name', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Appointments': [('company_code', 'Company Code', 'company'), ('appointment_date', 'Appointment Date', 'date'), ('appointment_time', 'Appointment Time', 'text'), ('customer_name', 'Customer Name', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('company', 'Company', 'text'), ('purpose', 'Purpose', 'text'), ('meeting_with', 'Meeting With', 'text'), ('fees', 'Fees', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Raw Material Stock': [('company_code', 'Company Code', 'company'), ('entry_date', 'Entry Date', 'date'), ('item_name', 'Item Name', 'stock_item'), ('item_code', 'Item Code', 'text'), ('unit', 'Unit', 'text'), ('opening_qty', 'Opening Qty', 'number'), ('inward_qty', 'Inward Qty', 'number'), ('outward_qty', 'Outward Qty', 'number'), ('closing_qty', 'Closing Qty', 'number'), ('rate', 'Rate', 'number'), ('value', 'Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Finished Goods Stock': [('company_code', 'Company Code', 'company'), ('entry_date', 'Entry Date', 'date'), ('item_name', 'Item Name', 'stock_item'), ('item_code', 'Item Code', 'text'), ('unit', 'Unit', 'text'), ('opening_qty', 'Opening Qty', 'number'), ('production_qty', 'Production Qty', 'number'), ('sales_qty', 'Sales Qty', 'number'), ('closing_qty', 'Closing Qty', 'number'), ('rate', 'Rate', 'number'), ('value', 'Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'WIP Stock': [('company_code', 'Company Code', 'company'), ('entry_date', 'Entry Date', 'date'), ('process_name', 'Process Name', 'text'), ('item_name', 'Item Name', 'stock_item'), ('item_code', 'Item Code', 'text'), ('unit', 'Unit', 'text'), ('opening_qty', 'Opening Qty', 'number'), ('input_qty', 'Input Qty', 'number'), ('output_qty', 'Output Qty', 'number'), ('closing_qty', 'Closing Qty', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Stock Vouchers': [('company_code', 'Company Code', 'company'), ('voucher_no', 'Voucher No', 'text'), ('voucher_date', 'Voucher Date', 'date'), ('voucher_type', 'Voucher Type', 'text'), ('item_name', 'Item Name', 'stock_item'), ('stock_group', 'Stock Group', 'text'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('value', 'Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Accounting Entries': [('company_code', 'Company Code', 'company'), ('entry_date', 'Entry Date', 'date'), ('voucher_type', 'Voucher Type', 'text'), ('voucher_no', 'Voucher No', 'text'), ('debit_account', 'Debit Account', 'number'), ('credit_account', 'Credit Account', 'number'), ('amount', 'Amount', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_amount', 'Total Amount', 'number'), ('narration', 'Narration', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Accounting Entry Lines': [('company_code', 'Company Code', 'company'), ('entry_id', 'Entry Id', 'text'), ('dr_cr', 'Dr Cr', 'text'), ('ledger_name', 'Ledger Name', 'text'), ('amount', 'Amount', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Fixed Assets': [('company_code', 'Company Code', 'company'), ('asset_code', 'Asset Code', 'text'), ('asset_name', 'Asset Name', 'text'), ('purchase_date', 'Purchase Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('invoice_no', 'Invoice No', 'text'), ('asset_category', 'Asset Category', 'text'), ('location', 'Location', 'text'), ('cost', 'Cost', 'text'), ('depreciation_rate', 'Depreciation Rate', 'number'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Sales GST Invoice': [('company_code', 'Company Code', 'company'), ('invoice_no', 'Invoice No', 'text'), ('invoice_date', 'Invoice Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('gstin', 'GSTIN', 'text'), ('item_name', 'Item Name', 'stock_item'), ('hsn_sac', 'HSN/SAC', 'text'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('taxable_value', 'Taxable Value', 'number'), ('discount', 'Discount', 'number'), ('freight', 'Freight', 'number'), ('other_exp', 'Other Exp', 'text'), ('tds', 'TDS', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Service Voucher': [('company_code', 'Company Code', 'company'), ('voucher_no', 'Voucher No', 'text'), ('voucher_date', 'Voucher Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('service_name', 'Service Name', 'text'), ('sac_code', 'Sac Code', 'text'), ('taxable_value', 'Taxable Value', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('payment_status', 'Payment Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Purchase GST Invoice': [('company_code', 'Company Code', 'company'), ('invoice_no', 'Invoice No', 'text'), ('invoice_date', 'Invoice Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('gstin', 'GSTIN', 'text'), ('item_name', 'Item Name', 'stock_item'), ('hsn_sac', 'HSN/SAC', 'text'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('taxable_value', 'Taxable Value', 'number'), ('discount', 'Discount', 'number'), ('freight', 'Freight', 'number'), ('other_exp', 'Other Exp', 'text'), ('tds', 'TDS', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Expense GST Voucher': [('company_code', 'Company Code', 'company'), ('expense_date', 'Expense Date', 'date'), ('vendor_name', 'Vendor Name', 'text'), ('expense_head', 'Expense Head', 'number'), ('invoice_no', 'Invoice No', 'text'), ('gstin', 'GSTIN', 'text'), ('taxable_value', 'Taxable Value', 'number'), ('discount', 'Discount', 'number'), ('freight', 'Freight', 'number'), ('other_exp', 'Other Exp', 'text'), ('tds', 'TDS', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('payment_mode', 'Payment Mode', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Project Accounting': [('company_code', 'Company Code', 'company'), ('project_name', 'Project Name', 'text'), ('project_code', 'Project Code', 'text'), ('customer_name', 'Customer Name', 'text'), ('income', 'Income', 'number'), ('expense', 'Expense', 'number'), ('profit', 'Profit', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Quotation Requirements': [('company_code', 'Company Code', 'company'), ('requirement_no', 'Requirement No', 'text'), ('requirement_date', 'Requirement Date', 'date'), ('requirement_title', 'Requirement Title', 'text'), ('requirement_details', 'Requirement Details', 'text'), ('item_name', 'Item Name', 'stock_item'), ('qty', 'Qty', 'number'), ('unit', 'Unit', 'text'), ('expected_date', 'Expected Date', 'date'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Quotation Business Users': [('company_code', 'Company Code', 'company'), ('business_name', 'Business Name', 'text'), ('contact_person', 'Contact Person', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('username', 'Username', 'text'), ('password', 'Password', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Quotation Access': [('company_code', 'Company Code', 'company'), ('requirement_id', 'Requirement Id', 'text'), ('requirement_no', 'Requirement No', 'text'), ('business_username', 'Business Username', 'text'), ('business_name', 'Business Name', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Quotations': [('company_code', 'Company Code', 'company'), ('requirement_id', 'Requirement Id', 'text'), ('requirement_no', 'Requirement No', 'text'), ('business_username', 'Business Username', 'text'), ('business_name', 'Business Name', 'text'), ('quotation_no', 'Quotation No', 'text'), ('quotation_date', 'Quotation Date', 'date'), ('amount', 'Amount', 'number'), ('gst_amount', 'Gst Amount', 'number'), ('total_amount', 'Total Amount', 'number'), ('valid_till', 'Valid Till', 'text'), ('quotation_file_name', 'Quotation File Name', 'text'), ('quotation_status', 'Quotation Status', 'text'), ('negotiation_status', 'Negotiation Status', 'text'), ('negotiation_deadline', 'Negotiation Deadline', 'text'), ('negotiation_message', 'Negotiation Message', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Quotation Negotiations': [('company_code', 'Company Code', 'company'), ('quotation_id', 'Quotation Id', 'text'), ('requirement_id', 'Requirement Id', 'text'), ('requirement_no', 'Requirement No', 'text'), ('business_username', 'Business Username', 'text'), ('business_name', 'Business Name', 'text'), ('vendor_email', 'Vendor Email', 'text'), ('original_amount', 'Original Amount', 'number'), ('requested_amount', 'Requested Amount', 'number'), ('negotiation_message', 'Negotiation Message', 'text'), ('deadline', 'Deadline', 'text'), ('status', 'Status', 'status'), ('client_requested_by', 'Client Requested By', 'text'), ('client_requested_at', 'Client Requested At', 'date'), ('vendor_response', 'Vendor Response', 'text'), ('revised_amount', 'Revised Amount', 'number'), ('revised_gst_amount', 'Revised GST Amount', 'number'), ('revised_total_amount', 'Revised Total Amount', 'number'), ('revised_file_name', 'Revised File Name', 'text'), ('submitted_by', 'Submitted By', 'text'), ('submitted_at', 'Submitted At', 'date'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Calculation Book': [('company_code', 'Company Code', 'company'), ('book_name', 'Book Name', 'text'), ('sheet_name', 'Sheet Name', 'text'), ('grid_json', 'Grid Json', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Import Logs': [('company_code', 'Company Code', 'company'), ('import_type', 'Import Type', 'text'), ('module_name', 'Module Name', 'module_name'), ('total_rows', 'Total Rows', 'number'), ('success_rows', 'Success Rows', 'text'), ('failed_rows', 'Failed Rows', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'AMC / Subscriptions': [('company_code', 'Company Code', 'company'), ('plan_name', 'Plan Name', 'text'), ('client_name', 'Client Name', 'text'), ('start_date', 'Start Date', 'date'), ('expiry_date', 'Expiry Date', 'date'), ('no_of_users', 'No Of Users', 'text'), ('storage_limit_mb', 'Storage Limit Mb', 'number'), ('amount', 'Amount', 'number'), ('renewal_status', 'Renewal Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Support Tickets': [('company_code', 'Company Code', 'company'), ('ticket_no', 'Ticket No', 'text'), ('ticket_date', 'Ticket Date', 'date'), ('raised_by', 'Raised By', 'text'), ('subject', 'Subject', 'text'), ('priority', 'Priority', 'text'), ('status', 'Status', 'status'), ('assigned_to', 'Assigned To', 'user'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'License Manager': [('company_code', 'Company Code', 'company'), ('license_key', 'License Key', 'text'), ('client_name', 'Client Name', 'text'), ('machine_id', 'Machine Id', 'text'), ('start_date', 'Start Date', 'date'), ('expiry_date', 'Expiry Date', 'date'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Approval Matrix': [('company_code', 'Company Code', 'company'), ('module_name', 'Module Name', 'module_name'), ('level_no', 'Level No', 'number'), ('approver_role', 'Approver Role', 'text'), ('approver_name', 'Approver Name', 'text'), ('amount_limit', 'Amount Limit', 'number'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Workflow Rules': [('company_code', 'Company Code', 'company'), ('rule_name', 'Rule Name', 'text'), ('module_name', 'Module Name', 'module_name'), ('condition_text', 'Condition Text', 'text'), ('action_text', 'Action Text', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Compliance Register': [('company_code', 'Company Code', 'company'), ('compliance_name', 'Compliance Name', 'text'), ('act_name', 'Act Name', 'text'), ('due_date', 'Due Date', 'date'), ('responsible_person', 'Responsible Person', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Document Control': [('company_code', 'Company Code', 'company'), ('document_no', 'Document No', 'text'), ('document_date', 'Document Date', 'date'), ('document_type', 'Document Type', 'text'), ('document_title', 'Document Title', 'text'), ('owner', 'Owner', 'text'), ('version', 'Version', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Management Mis': [('company_code', 'Company Code', 'company'), ('mis_date', 'Mis Date', 'date'), ('department', 'Department', 'text'), ('kpi', 'Kpi', 'text'), ('target', 'Target', 'text'), ('actual', 'Actual', 'text'), ('variance', 'Variance', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Branch Management': [('company_code', 'Company Code', 'company'), ('branch_code', 'Branch Code', 'text'), ('branch_name', 'Branch Name', 'text'), ('address', 'Address', 'text'), ('state', 'State', 'text'), ('manager_name', 'Manager Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Department Management': [('company_code', 'Company Code', 'company'), ('department_code', 'Department Code', 'text'), ('department_name', 'Department Name', 'text'), ('hod_name', 'Hod Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Customer Complaints': [('company_code', 'Company Code', 'company'), ('complaint_no', 'Complaint No', 'text'), ('complaint_date', 'Complaint Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('subject', 'Subject', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Service Requests': [('company_code', 'Company Code', 'company'), ('request_no', 'Request No', 'text'), ('request_date', 'Request Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('service_name', 'Service Name', 'text'), ('assigned_to', 'Assigned To', 'user'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Onedrive Backup': [('company_code', 'Company Code', 'company'), ('backup_date', 'Backup Date', 'date'), ('backup_file', 'Backup File', 'text'), ('backup_folder', 'Backup Folder', 'text'), ('backup_status', 'Backup Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Optional Sync': [('company_code', 'Company Code', 'company'), ('sync_date', 'Sync Date', 'date'), ('sync_type', 'Sync Type', 'text'), ('table_name', 'Table Name', 'text'), ('records_uploaded', 'Records Uploaded', 'text'), ('records_downloaded', 'Records Downloaded', 'text'), ('sync_status', 'Sync Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Data Import': [('company_code', 'Company Code', 'company'), ('import_date', 'Import Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('file_name', 'File Name', 'text'), ('total_rows', 'Total Rows', 'number'), ('success_rows', 'Success Rows', 'text'), ('failed_rows', 'Failed Rows', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Data Export': [('company_code', 'Company Code', 'company'), ('export_date', 'Export Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('file_name', 'File Name', 'text'), ('export_type', 'Export Type', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Email Utility': [('company_code', 'Company Code', 'company'), ('email_date', 'Email Date', 'date'), ('to_email', 'To Email', 'text'), ('subject', 'Subject', 'text'), ('module_name', 'Module Name', 'module_name'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Pdf Print Utility': [('company_code', 'Company Code', 'company'), ('print_date', 'Print Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('pdf_file', 'Pdf File', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'System Settings': [('company_code', 'Company Code', 'company'), ('setting_name', 'Setting Name', 'text'), ('setting_value', 'Setting Value', 'number'), ('setting_group', 'Setting Group', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Multi Company Master': [('company_code', 'Company Code', 'company'), ('company_name', 'Company Name', 'text'), ('legal_name', 'Legal Name', 'text'), ('gst_no', 'GST No', 'text'), ('pan_no', 'PAN No', 'text'), ('cin_no', 'Cin No', 'text'), ('address', 'Address', 'text'), ('city', 'City', 'text'), ('state', 'State', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Multi Branch Master': [('company_code', 'Company Code', 'company'), ('branch_code', 'Branch Code', 'text'), ('branch_name', 'Branch Name', 'text'), ('branch_type', 'Branch Type', 'text'), ('address', 'Address', 'text'), ('city', 'City', 'text'), ('state', 'State', 'text'), ('manager_name', 'Manager Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'CRM Leads': [('lead_date', 'Lead Date', 'date'), ('lead_no', 'Lead No', 'text'), ('company_name', 'Company Name', 'text'), ('contact_person', 'Contact Person', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('city', 'City', 'text'), ('state', 'State', 'text'), ('source', 'Source', 'text'), ('requirement', 'Requirement', 'text'), ('estimated_value', 'Estimated Value', 'number'), ('lead_status', 'Lead Status', 'text'), ('next_followup_date', 'Next Followup Date', 'date'), ('assigned_to', 'Assigned To', 'user'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'CRM Followups': [('followup_date', 'Followup Date', 'date'), ('lead_no', 'Lead No', 'text'), ('company_name', 'Company Name', 'text'), ('contact_person', 'Contact Person', 'text'), ('followup_mode', 'Followup Mode', 'text'), ('discussion', 'Discussion', 'text'), ('next_followup_date', 'Next Followup Date', 'date'), ('followup_status', 'Followup Status', 'text'), ('assigned_to', 'Assigned To', 'user'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'CRM Customers': [('customer_code', 'Customer Code', 'text'), ('customer_name', 'Customer Name', 'text'), ('contact_person', 'Contact Person', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('gstin', 'GSTIN', 'text'), ('pan_no', 'PAN No', 'text'), ('address', 'Address', 'text'), ('city', 'City', 'text'), ('state', 'State', 'text'), ('customer_type', 'Customer Type', 'text'), ('credit_limit', 'Credit Limit', 'number'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'CRM Opportunities': [('opportunity_date', 'Opportunity Date', 'date'), ('opportunity_no', 'Opportunity No', 'text'), ('customer_name', 'Customer Name', 'text'), ('product_service', 'Product Service', 'text'), ('expected_value', 'Expected Value', 'number'), ('stage', 'Stage', 'text'), ('probability', 'Probability', 'text'), ('expected_close_date', 'Expected Close Date', 'date'), ('assigned_to', 'Assigned To', 'user'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Quotation Register': [('quotation_no', 'Quotation No', 'text'), ('quotation_date', 'Quotation Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('gstin', 'GSTIN', 'text'), ('valid_till', 'Valid Till', 'text'), ('item_name', 'Item Name', 'stock_item'), ('hsn_sac', 'HSN/SAC', 'text'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('taxable_value', 'Taxable Value', 'number'), ('discount', 'Discount', 'number'), ('freight', 'Freight', 'number'), ('other_exp', 'Other Exp', 'text'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('quotation_status', 'Quotation Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Sales Order': [('sales_order_no', 'Sales Order No', 'text'), ('sales_order_date', 'Sales Order Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('gstin', 'GSTIN', 'text'), ('delivery_date', 'Delivery Date', 'date'), ('item_name', 'Item Name', 'stock_item'), ('hsn_sac', 'HSN/SAC', 'text'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('taxable_value', 'Taxable Value', 'number'), ('discount', 'Discount', 'number'), ('freight', 'Freight', 'number'), ('other_exp', 'Other Exp', 'text'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('order_status', 'Order Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Purchase Order': [('purchase_order_no', 'Purchase Order No', 'text'), ('purchase_order_date', 'Purchase Order Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('gstin', 'GSTIN', 'text'), ('delivery_date', 'Delivery Date', 'date'), ('item_name', 'Item Name', 'stock_item'), ('hsn_sac', 'HSN/SAC', 'text'), ('qty', 'Qty', 'number'), ('rate', 'Rate', 'number'), ('taxable_value', 'Taxable Value', 'number'), ('discount', 'Discount', 'number'), ('freight', 'Freight', 'number'), ('other_exp', 'Other Exp', 'text'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('order_status', 'Order Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Manufacturing BOM': [('bom_no', 'Bom No', 'bom'), ('bom_date', 'Bom Date', 'date'), ('finished_item', 'Finished Item', 'stock_item'), ('finished_qty', 'Finished Qty', 'number'), ('raw_material_item', 'Raw Material Item', 'stock_item'), ('raw_material_qty', 'Raw Material Qty', 'number'), ('unit', 'Unit', 'text'), ('rate', 'Rate', 'number'), ('amount', 'Amount', 'number'), ('scrap_percent', 'Scrap Percent', 'number'), ('process_name', 'Process Name', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Asset Management': [('asset_code', 'Asset Code', 'text'), ('asset_name', 'Asset Name', 'text'), ('asset_category', 'Asset Category', 'text'), ('purchase_date', 'Purchase Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('invoice_no', 'Invoice No', 'text'), ('location', 'Location', 'text'), ('department', 'Department', 'text'), ('cost', 'Cost', 'text'), ('depreciation_rate', 'Depreciation Rate', 'number'), ('accumulated_depreciation', 'Accumulated Depreciation', 'text'), ('wdv', 'Wdv', 'text'), ('asset_status', 'Asset Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Asset Maintenance': [('maintenance_no', 'Maintenance No', 'text'), ('maintenance_date', 'Maintenance Date', 'date'), ('asset_code', 'Asset Code', 'text'), ('asset_name', 'Asset Name', 'text'), ('vendor_name', 'Vendor Name', 'text'), ('maintenance_type', 'Maintenance Type', 'text'), ('cost', 'Cost', 'text'), ('next_due_date', 'Next Due Date', 'date'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Document Management': [('document_no', 'Document No', 'text'), ('document_date', 'Document Date', 'date'), ('document_type', 'Document Type', 'text'), ('document_title', 'Document Title', 'text'), ('department', 'Department', 'text'), ('owner_name', 'Owner Name', 'text'), ('version_no', 'Version No', 'text'), ('file_name', 'File Name', 'text'), ('file_location', 'File Location', 'text'), ('review_date', 'Review Date', 'date'), ('approval_status', 'Approval Status', 'status'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Audit Management': [('audit_no', 'Audit No', 'text'), ('audit_date', 'Audit Date', 'date'), ('audit_area', 'Audit Area', 'text'), ('auditor_name', 'Auditor Name', 'text'), ('department', 'Department', 'text'), ('observation', 'Observation', 'text'), ('risk_level', 'Risk Level', 'number'), ('action_required', 'Action Required', 'text'), ('responsible_person', 'Responsible Person', 'text'), ('target_date', 'Target Date', 'date'), ('closure_status', 'Closure Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Audit Checklist': [('checklist_no', 'Checklist No', 'text'), ('audit_area', 'Audit Area', 'text'), ('question', 'Question', 'text'), ('compliance_status', 'Compliance Status', 'text'), ('evidence_required', 'Evidence Required', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'AI Chat Assistant': [('chat_date', 'Chat Date', 'date'), ('user_name', 'User Name', 'text'), ('question', 'Question', 'text'), ('answer', 'Answer', 'text'), ('module_name', 'Module Name', 'module_name'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'WhatsApp Integration': [('message_date', 'Message Date', 'date'), ('mobile_no', 'Mobile No', 'text'), ('party_name', 'Party Name', 'text'), ('template_name', 'Template Name', 'text'), ('message_text', 'Message Text', 'text'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('send_status', 'Send Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Email Integration': [('email_date', 'Email Date', 'date'), ('to_email', 'To Email', 'text'), ('cc_email', 'Cc Email', 'text'), ('party_name', 'Party Name', 'text'), ('subject', 'Subject', 'text'), ('message_text', 'Message Text', 'text'), ('attachment_file', 'Attachment File', 'text'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('send_status', 'Send Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'OneDrive Backup Advanced': [('backup_date', 'Backup Date', 'date'), ('backup_type', 'Backup Type', 'text'), ('backup_folder', 'Backup Folder', 'text'), ('backup_file', 'Backup File', 'text'), ('backup_size', 'Backup Size', 'text'), ('onedrive_status', 'Onedrive Status', 'text'), ('backup_status', 'Backup Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Mobile App Sync': [('sync_date', 'Sync Date', 'date'), ('device_name', 'Device Name', 'text'), ('user_name', 'User Name', 'text'), ('module_name', 'Module Name', 'module_name'), ('records_uploaded', 'Records Uploaded', 'text'), ('records_downloaded', 'Records Downloaded', 'text'), ('sync_status', 'Sync Status', 'text'), ('last_sync_time', 'Last Sync Time', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Role Based Security': [('username', 'Username', 'text'), ('role_name', 'Role Name', 'text'), ('module_name', 'Module Name', 'module_name'), ('can_view', 'Can View', 'text'), ('can_add', 'Can Add', 'text'), ('can_edit', 'Can Edit', 'text'), ('can_delete', 'Can Delete', 'text'), ('can_approve', 'Can Approve', 'text'), ('can_print', 'Can Print', 'text'), ('can_export', 'Can Export', 'text'), ('can_reverse', 'Can Reverse', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Dashboard Analytics': [('report_date', 'Report Date', 'date'), ('kpi_name', 'Kpi Name', 'text'), ('kpi_group', 'Kpi Group', 'text'), ('target_value', 'Target Value', 'number'), ('actual_value', 'Actual Value', 'number'), ('variance_value', 'Variance Value', 'number'), ('variance_percent', 'Variance Percent', 'number'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Chairman MIS': [('mis_date', 'Mis Date', 'date'), ('company_code', 'Company Code', 'company'), ('branch_code', 'Branch Code', 'text'), ('department', 'Department', 'text'), ('kpi', 'Kpi', 'text'), ('today_value', 'Today Value', 'number'), ('month_value', 'Month Value', 'number'), ('year_value', 'Year Value', 'number'), ('target_value', 'Target Value', 'number'), ('variance', 'Variance', 'number'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Approval Center': [('approval_date', 'Approval Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('document_date', 'Document Date', 'date'), ('party_name', 'Party Name', 'text'), ('amount', 'Amount', 'number'), ('approval_level', 'Approval Level', 'number'), ('requested_by', 'Requested By', 'user'), ('approver_name', 'Approver Name', 'text'), ('approval_status', 'Approval Status', 'status'), ('approval_remarks', 'Approval Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('cost_center', 'Cost Center', 'text')], 'Notification Center': [('notification_date', 'Notification Date', 'date'), ('notification_type', 'Notification Type', 'text'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('to_user', 'To User', 'text'), ('to_mobile', 'To Mobile', 'text'), ('to_email', 'To Email', 'text'), ('subject', 'Subject', 'text'), ('message', 'Message', 'text'), ('priority', 'Priority', 'text'), ('read_status', 'Read Status', 'text'), ('send_status', 'Send Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Document Attachment System': [('upload_date', 'Upload Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('document_type', 'Document Type', 'text'), ('party_name', 'Party Name', 'text'), ('file_name', 'File Name', 'text'), ('file_path', 'File Path', 'text'), ('file_category', 'File Category', 'text'), ('version_no', 'Version No', 'text'), ('uploaded_by', 'Uploaded By', 'text'), ('approval_status', 'Approval Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Backup Restore System': [('backup_date', 'Backup Date', 'date'), ('backup_type', 'Backup Type', 'text'), ('backup_file', 'Backup File', 'text'), ('backup_folder', 'Backup Folder', 'text'), ('backup_size', 'Backup Size', 'text'), ('restore_date', 'Restore Date', 'date'), ('restore_by', 'Restore By', 'text'), ('backup_status', 'Backup Status', 'text'), ('restore_status', 'Restore Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Excel Import Wizard': [('import_date', 'Import Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('file_name', 'File Name', 'text'), ('sheet_name', 'Sheet Name', 'text'), ('total_rows', 'Total Rows', 'number'), ('success_rows', 'Success Rows', 'text'), ('failed_rows', 'Failed Rows', 'text'), ('duplicate_rows', 'Duplicate Rows', 'text'), ('import_status', 'Import Status', 'text'), ('error_log', 'Error Log', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Export All Data': [('export_date', 'Export Date', 'date'), ('export_type', 'Export Type', 'text'), ('module_name', 'Module Name', 'module_name'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('file_name', 'File Name', 'text'), ('file_path', 'File Path', 'text'), ('total_records', 'Total Records', 'number'), ('export_status', 'Export Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Client License Dashboard': [('client_name', 'Client Name', 'text'), ('license_key', 'License Key', 'text'), ('machine_id', 'Machine Id', 'text'), ('license_type', 'License Type', 'text'), ('license_plan', 'License Plan', 'text'), ('issue_date', 'Issue Date', 'date'), ('expiry_date', 'Expiry Date', 'date'), ('days_left', 'Days Left', 'number'), ('user_limit', 'User Limit', 'number'), ('module_limit', 'Module Limit', 'number'), ('license_status', 'License Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'User Activity Dashboard': [('activity_date', 'Activity Date', 'date'), ('user_name', 'User Name', 'text'), ('role_name', 'Role Name', 'text'), ('module_name', 'Module Name', 'module_name'), ('activity_type', 'Activity Type', 'text'), ('document_no', 'Document No', 'text'), ('login_time', 'Login Time', 'text'), ('logout_time', 'Logout Time', 'text'), ('ip_address', 'Ip Address', 'text'), ('activity_count', 'Activity Count', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Pending Work Dashboard': [('pending_date', 'Pending Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('party_name', 'Party Name', 'text'), ('pending_type', 'Pending Type', 'text'), ('assigned_to', 'Assigned To', 'user'), ('due_date', 'Due Date', 'date'), ('days_pending', 'Days Pending', 'number'), ('priority', 'Priority', 'text'), ('pending_status', 'Pending Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Reminder System': [('reminder_date', 'Reminder Date', 'date'), ('reminder_time', 'Reminder Time', 'text'), ('reminder_type', 'Reminder Type', 'text'), ('module_name', 'Module Name', 'module_name'), ('document_no', 'Document No', 'text'), ('party_name', 'Party Name', 'text'), ('assigned_to', 'Assigned To', 'user'), ('message', 'Message', 'text'), ('repeat_type', 'Repeat Type', 'text'), ('reminder_status', 'Reminder Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Auto Invoice Numbering': [('module_name', 'Module Name', 'module_name'), ('series_name', 'Series Name', 'text'), ('prefix', 'Prefix', 'text'), ('suffix', 'Suffix', 'text'), ('separator', 'Separator', 'text'), ('financial_year', 'Financial Year', 'text'), ('start_no', 'Start No', 'text'), ('next_no', 'Next No', 'text'), ('padding_digits', 'Padding Digits', 'text'), ('reset_policy', 'Reset Policy', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Payment Receipt Voucher': [('receipt_no', 'Receipt No', 'number'), ('receipt_date', 'Receipt Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('ledger_name', 'Ledger Name', 'text'), ('bank_cash_account', 'Bank Cash Account', 'text'), ('payment_mode', 'Payment Mode', 'text'), ('reference_no', 'Reference No', 'text'), ('invoice_no', 'Invoice No', 'text'), ('amount_received', 'Amount Received', 'number'), ('tds_deducted', 'Tds Deducted', 'number'), ('discount_allowed', 'Discount Allowed', 'number'), ('net_amount', 'Net Amount', 'number'), ('remarks', 'Remarks', 'text'), ('approval_status', 'Approval Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Bank Payment Voucher': [('payment_no', 'Payment No', 'text'), ('payment_date', 'Payment Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('ledger_name', 'Ledger Name', 'text'), ('bank_cash_account', 'Bank Cash Account', 'text'), ('payment_mode', 'Payment Mode', 'text'), ('reference_no', 'Reference No', 'text'), ('bill_no', 'Bill No', 'text'), ('amount_paid', 'Amount Paid', 'number'), ('tds_deducted', 'Tds Deducted', 'number'), ('discount_received', 'Discount Received', 'number'), ('net_amount', 'Net Amount', 'number'), ('remarks', 'Remarks', 'text'), ('approval_status', 'Approval Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Bank Reconciliation': [('reco_date', 'Reco Date', 'date'), ('bank_account', 'Bank Account', 'text'), ('statement_date', 'Statement Date', 'date'), ('voucher_no', 'Voucher No', 'text'), ('voucher_date', 'Voucher Date', 'date'), ('party_name', 'Party Name', 'text'), ('cheque_ref_no', 'Cheque Ref No', 'text'), ('book_amount', 'Book Amount', 'number'), ('bank_amount', 'Bank Amount', 'number'), ('difference', 'Difference', 'text'), ('clearance_date', 'Clearance Date', 'date'), ('reco_status', 'Reco Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'GST Return Summary': [('return_period', 'Return Period', 'text'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('gstin', 'GSTIN', 'text'), ('taxable_sales', 'Taxable Sales', 'number'), ('output_cgst', 'Output Cgst', 'number'), ('output_sgst', 'Output Sgst', 'number'), ('output_igst', 'Output Igst', 'number'), ('taxable_purchase', 'Taxable Purchase', 'number'), ('input_cgst', 'Input Cgst', 'number'), ('input_sgst', 'Input Sgst', 'number'), ('input_igst', 'Input Igst', 'number'), ('net_gst_payable', 'Net GST Payable', 'text'), ('return_status', 'Return Status', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'E-Way Bill Register': [('eway_bill_no', 'Eway Bill No', 'text'), ('eway_bill_date', 'Eway Bill Date', 'date'), ('invoice_no', 'Invoice No', 'text'), ('invoice_date', 'Invoice Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('gstin', 'GSTIN', 'text'), ('vehicle_no', 'Vehicle No', 'text'), ('transport_name', 'Transport Name', 'text'), ('from_place', 'From Place', 'text'), ('to_place', 'To Place', 'text'), ('distance_km', 'Distance Km', 'text'), ('valid_upto', 'Valid Upto', 'number'), ('eway_status', 'Eway Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'E-Invoice Register': [('irn_no', 'Irn No', 'text'), ('ack_no', 'Ack No', 'text'), ('ack_date', 'Ack Date', 'date'), ('invoice_no', 'Invoice No', 'text'), ('invoice_date', 'Invoice Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('gstin', 'GSTIN', 'text'), ('taxable_value', 'Taxable Value', 'number'), ('cgst', 'Cgst', 'number'), ('sgst', 'Sgst', 'number'), ('igst', 'Igst', 'number'), ('total_value', 'Total Value', 'number'), ('qr_code_file', 'Qr Code File', 'text'), ('einvoice_status', 'Einvoice Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Customer Outstanding Ageing': [('as_on_date', 'As On Date', 'date'), ('customer_name', 'Customer Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('invoice_no', 'Invoice No', 'text'), ('invoice_date', 'Invoice Date', 'date'), ('invoice_amount', 'Invoice Amount', 'number'), ('received_amount', 'Received Amount', 'number'), ('outstanding_amount', 'Outstanding Amount', 'number'), ('days_pending', 'Days Pending', 'number'), ('age_0_30', 'Age 0 30', 'text'), ('age_31_60', 'Age 31 60', 'text'), ('age_61_90', 'Age 61 90', 'text'), ('age_above_90', 'Age Above 90', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Supplier Outstanding Ageing': [('as_on_date', 'As On Date', 'date'), ('supplier_name', 'Supplier Name', 'text'), ('email', 'Email', 'text'), ('mobile', 'Mobile', 'text'), ('bill_no', 'Bill No', 'text'), ('bill_date', 'Bill Date', 'date'), ('bill_amount', 'Bill Amount', 'number'), ('paid_amount', 'Paid Amount', 'number'), ('outstanding_amount', 'Outstanding Amount', 'number'), ('days_pending', 'Days Pending', 'number'), ('age_0_30', 'Age 0 30', 'text'), ('age_31_60', 'Age 31 60', 'text'), ('age_61_90', 'Age 61 90', 'text'), ('age_above_90', 'Age Above 90', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Stock Ageing / Slow Moving Stock': [('as_on_date', 'As On Date', 'date'), ('item_code', 'Item Code', 'text'), ('item_name', 'Item Name', 'stock_item'), ('stock_group', 'Stock Group', 'text'), ('batch_no', 'Batch No', 'text'), ('receipt_date', 'Receipt Date', 'date'), ('opening_qty', 'Opening Qty', 'number'), ('inward_qty', 'Inward Qty', 'number'), ('outward_qty', 'Outward Qty', 'number'), ('closing_qty', 'Closing Qty', 'number'), ('stock_value', 'Stock Value', 'number'), ('days_in_stock', 'Days In Stock', 'number'), ('age_bucket', 'Age Bucket', 'text'), ('slow_moving_status', 'Slow Moving Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Settings Center': [('setting_group', 'Setting Group', 'text'), ('setting_key', 'Setting Key', 'text'), ('setting_value', 'Setting Value', 'number'), ('description', 'Description', 'number'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Restore Backup': [('restore_date', 'Restore Date', 'date'), ('backup_file', 'Backup File', 'text'), ('backup_location', 'Backup Location', 'text'), ('restore_type', 'Restore Type', 'text'), ('restore_by', 'Restore By', 'text'), ('restore_status', 'Restore Status', 'text'), ('before_restore_backup', 'Before Restore Backup', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Error Log Viewer': [('error_date', 'Error Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('error_type', 'Error Type', 'text'), ('error_message', 'Error Message', 'text'), ('error_details', 'Error Details', 'text'), ('user_name', 'User Name', 'text'), ('screen_name', 'Screen Name', 'text'), ('resolved_status', 'Resolved Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Data Health Check': [('check_date', 'Check Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('check_type', 'Check Type', 'text'), ('total_records', 'Total Records', 'number'), ('blank_records', 'Blank Records', 'text'), ('duplicate_records', 'Duplicate Records', 'text'), ('invalid_records', 'Invalid Records', 'text'), ('health_status', 'Health Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Year Closing / Opening Balance Transfer': [('closing_date', 'Closing Date', 'date'), ('from_financial_year', 'From Financial Year', 'text'), ('to_financial_year', 'To Financial Year', 'text'), ('ledger_name', 'Ledger Name', 'text'), ('closing_balance', 'Closing Balance', 'number'), ('opening_balance_transfer', 'Opening Balance Transfer', 'number'), ('stock_closing_value', 'Stock Closing Value', 'number'), ('transfer_status', 'Transfer Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Company Switcher': [('switch_date', 'Switch Date', 'date'), ('user_name', 'User Name', 'text'), ('from_company', 'From Company', 'text'), ('to_company', 'To Company', 'text'), ('from_branch', 'From Branch', 'text'), ('to_branch', 'To Branch', 'text'), ('switch_reason', 'Switch Reason', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'User Password Change': [('change_date', 'Change Date', 'date'), ('user_name', 'User Name', 'text'), ('role_name', 'Role Name', 'text'), ('password_changed_by', 'Password Changed By', 'text'), ('change_reason', 'Change Reason', 'text'), ('change_status', 'Change Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'License Status Screen': [('client_name', 'Client Name', 'text'), ('license_type', 'License Type', 'text'), ('license_plan', 'License Plan', 'text'), ('machine_id', 'Machine Id', 'text'), ('issue_date', 'Issue Date', 'date'), ('expiry_date', 'Expiry Date', 'date'), ('days_left', 'Days Left', 'number'), ('user_limit', 'User Limit', 'number'), ('current_users', 'Current Users', 'text'), ('module_count', 'Module Count', 'text'), ('license_status', 'License Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'System Configuration': [('config_date', 'Config Date', 'date'), ('company_code', 'Company Code', 'company'), ('default_financial_year', 'Default Financial Year', 'text'), ('default_branch', 'Default Branch', 'text'), ('default_currency', 'Default Currency', 'text'), ('date_format', 'Date Format', 'date'), ('invoice_prefix', 'Invoice Prefix', 'text'), ('backup_frequency', 'Backup Frequency', 'text'), ('theme_name', 'Theme Name', 'text'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Data Archive': [('archive_date', 'Archive Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('records_archived', 'Records Archived', 'text'), ('archive_file', 'Archive File', 'text'), ('archive_status', 'Archive Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Data Purge Control': [('request_date', 'Request Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('from_date', 'From Date', 'date'), ('to_date', 'To Date', 'date'), ('requested_by', 'Requested By', 'user'), ('approved_by', 'Approved By', 'user'), ('records_to_purge', 'Records To Purge', 'text'), ('purge_status', 'Purge Status', 'status'), ('backup_created', 'Backup Created', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Numbering Series Audit': [('audit_date', 'Audit Date', 'date'), ('module_name', 'Module Name', 'module_name'), ('series_name', 'Series Name', 'text'), ('expected_next_no', 'Expected Next No', 'text'), ('actual_next_no', 'Actual Next No', 'text'), ('missing_numbers', 'Missing Numbers', 'text'), ('duplicate_numbers', 'Duplicate Numbers', 'text'), ('audit_status', 'Audit Status', 'text'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Master Data Approval': [('request_date', 'Request Date', 'date'), ('master_module', 'Master Module', 'text'), ('record_name', 'Record Name', 'text'), ('request_type', 'Request Type', 'text'), ('requested_by', 'Requested By', 'user'), ('approver_name', 'Approver Name', 'text'), ('approval_status', 'Approval Status', 'status'), ('approval_remarks', 'Approval Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('cost_center', 'Cost Center', 'text')], 'Data Locking Period': [('lock_date', 'Lock Date', 'date'), ('financial_year', 'Financial Year', 'text'), ('module_name', 'Module Name', 'module_name'), ('lock_from_date', 'Lock From Date', 'date'), ('lock_to_date', 'Lock To Date', 'date'), ('lock_reason', 'Lock Reason', 'text'), ('locked_by', 'Locked By', 'text'), ('lock_status', 'Lock Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Scheduler Jobs': [('job_name', 'Job Name', 'text'), ('job_type', 'Job Type', 'text'), ('schedule_time', 'Schedule Time', 'text'), ('last_run_time', 'Last Run Time', 'text'), ('next_run_time', 'Next Run Time', 'text'), ('run_status', 'Run Status', 'text'), ('error_message', 'Error Message', 'text'), ('status', 'Status', 'status'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Client Support Register': [('ticket_no', 'Ticket No', 'text'), ('ticket_date', 'Ticket Date', 'date'), ('client_name', 'Client Name', 'text'), ('contact_person', 'Contact Person', 'text'), ('mobile', 'Mobile', 'text'), ('email', 'Email', 'text'), ('issue_type', 'Issue Type', 'text'), ('issue_description', 'Issue Description', 'number'), ('priority', 'Priority', 'text'), ('assigned_to', 'Assigned To', 'user'), ('ticket_status', 'Ticket Status', 'text'), ('closure_date', 'Closure Date', 'date'), ('remarks', 'Remarks', 'text'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')], 'Mandatory Field Settings': [('company_code', 'Company Code', 'company'), ('module_name', 'Module Name', 'module_name'), ('field_name', 'Field Name', 'text'), ('is_mandatory', 'Is Mandatory', 'bool'), ('status', 'Status', 'status'), ('created_by', 'Created By', 'text'), ('parking_status', 'Parking Status', 'status'), ('approval_status', 'Approval Status', 'status'), ('cost_center', 'Cost Center', 'text'), ('approval_remarks', 'Approval Remarks', 'text')]}

# update all online generic modules so their input headers/fields match offline desktop module columns
try:
    _GENERIC_MODULE_FIELDS.update(_OFFLINE_SAME_FIELDS_PATCH19)
except Exception:
    pass

def _offline_pl_df(fmt="Standard"):
    return pd.DataFrame({
        "Debit Particulars": ["To Opening Stock", "To Purchases", "To Direct Expenses", "To Gross Profit c/d", "Total", "Gross Profit Brought Down", "To Salaries", "To Rent", "To Electricity", "To Office Expenses", "To Depreciation", "To Net Profit transferred to Capital A/c", "Total"],
        "Debit Amount (₹)": [0.0]*13,
        "Credit Particulars": ["By Sales", "By Closing Stock", "By Other Operating Income", "", "Total", "", "By Gross Profit b/d", "By Commission Received", "By Interest Received", "", "", "", "Total"],
        "Credit Amount (₹)": [0.0]*13,
        "Format": [fmt]*13
    })

def _offline_bs_df(fmt="Standard"):
    return pd.DataFrame({
        "Liabilities": ["Capital Account", "Add: Net Profit", "Less: Drawings", "Secured Loans", "Unsecured Loans", "Sundry Creditors", "Outstanding Expenses", "Duties & Taxes Payable", "Total"],
        "Amount (₹)": [0.0]*9,
        "Assets": ["Fixed Assets", "Less: Depreciation", "Net Fixed Assets", "Investments", "Closing Stock", "Sundry Debtors", "Cash-in-Hand", "Bank Balance", "Total"],
        "Asset Amount (₹)": [0.0]*9,
        "Format": [fmt]*9
    })

def _offline_tb_df():
    return pd.DataFrame({
        "Group": ["Capital Account", "Capital Account", "Sales Accounts", "Sales Accounts", "Purchase Accounts", "Purchase Accounts", "Direct Expenses", "Direct Incomes", "Current Assets", "Current Assets"],
        "Particulars": ["Capital Account", "Drawings", "Sales Account", "Sales Return", "Purchase Account", "Purchase Return", "Opening Stock", "Closing Stock", "Cash-in-Hand", "Bank Balance"],
        "Dr Amount": [0.0]*10,
        "Cr Amount": [0.0]*10,
        "Report Type": ["Tally Group-Wise Trial Balance"]*10
    })



def build_ledger_statement_df(selected_ledger, from_dt=None, to_dt=None):
    """Ledger statement: opening + Dr/Cr transactions + running/net balance."""
    ledger = str(selected_ledger or "All").strip()
    ledgers = load_table("ledgers", 50000)
    entries = load_table("accounting_entries", 50000)
    lines = load_table("accounting_entry_lines", 50000)

    def _date_ok(v):
        if from_dt is None and to_dt is None:
            return True
        try:
            d = pd.to_datetime(v, dayfirst=True, errors="coerce").date()
            if pd.isna(pd.to_datetime(v, dayfirst=True, errors="coerce")):
                return True
            if from_dt is not None and d < from_dt:
                return False
            if to_dt is not None and d > to_dt:
                return False
            return True
        except Exception:
            return True

    rows = []
    opening_dr = opening_cr = 0.0
    if not ledgers.empty and "ledger_name" in ledgers.columns:
        ldf = ledgers.copy()
        if ledger != "All":
            ldf = ldf[ldf["ledger_name"].astype(str) == ledger]
        for _, r in ldf.iterrows():
            op = num_value(r.get("opening_balance", 0))
            bt = str(r.get("balance_type", "Dr")).strip().lower()
            if bt.startswith("cr"):
                opening_cr += abs(op)
            else:
                opening_dr += abs(op)

    opening_net = opening_dr - opening_cr
    rows.append({
        "Date": "Opening",
        "Voucher Type": "Opening Balance",
        "Voucher No": "",
        "Ledger Name": ledger,
        "Particulars": "Opening Balance",
        "Dr Amount": round(opening_dr, 2),
        "Cr Amount": round(opening_cr, 2),
        "Net Balance": round(abs(opening_net), 2),
        "Balance Type": "Dr" if opening_net >= 0 else "Cr",
        "Narration / Remarks": ""
    })

    entry_lookup = {}
    if not entries.empty and "id" in entries.columns:
        for _, e in entries.iterrows():
            entry_lookup[str(e.get("id"))] = e

    txns = []
    if not lines.empty and "ledger_name" in lines.columns:
        lns = lines.copy()
        if ledger != "All":
            lns = lns[lns["ledger_name"].astype(str) == ledger]
        for _, l in lns.iterrows():
            e = entry_lookup.get(str(l.get("entry_id")), {})
            dt = e.get("entry_date", l.get("entry_date", "")) if hasattr(e, 'get') else l.get("entry_date", "")
            if not _date_ok(dt):
                continue
            dc = str(l.get("dr_cr", "Dr")).lower()
            amt = num_value(l.get("amount", 0))
            txns.append({
                "Date": dt,
                "Voucher Type": e.get("voucher_type", l.get("voucher_type", "")) if hasattr(e, 'get') else l.get("voucher_type", ""),
                "Voucher No": e.get("voucher_no", l.get("voucher_no", "")) if hasattr(e, 'get') else l.get("voucher_no", ""),
                "Ledger Name": l.get("ledger_name", ""),
                "Particulars": "Dr Entry" if dc.startswith("dr") else "Cr Entry",
                "Dr Amount": amt if dc.startswith("dr") else 0.0,
                "Cr Amount": amt if dc.startswith("cr") else 0.0,
                "Narration / Remarks": l.get("remarks", e.get("narration", "") if hasattr(e, 'get') else "")
            })

    # Fallback for old/simple accounting_entries rows without line table
    if not entries.empty:
        for _, e in entries.iterrows():
            dt = e.get("entry_date", "")
            if not _date_ok(dt):
                continue
            amt = num_value(e.get("amount", e.get("total_amount", 0)))
            debit_acc = str(e.get("debit_account", ""))
            credit_acc = str(e.get("credit_account", ""))
            if debit_acc and debit_acc != "Multiple" and (ledger == "All" or debit_acc == ledger):
                txns.append({"Date": dt, "Voucher Type": e.get("voucher_type", ""), "Voucher No": e.get("voucher_no", ""), "Ledger Name": debit_acc, "Particulars": "Debit", "Dr Amount": amt, "Cr Amount": 0.0, "Narration / Remarks": e.get("narration", "")})
            if credit_acc and credit_acc != "Multiple" and (ledger == "All" or credit_acc == ledger):
                txns.append({"Date": dt, "Voucher Type": e.get("voucher_type", ""), "Voucher No": e.get("voucher_no", ""), "Ledger Name": credit_acc, "Particulars": "Credit", "Dr Amount": 0.0, "Cr Amount": amt, "Narration / Remarks": e.get("narration", "")})

    # Sales/Purchase/Expense party impact rows where available
    extra_sources = [
        ("sales", "Sales Invoice", ["invoice_date", "date"], ["invoice_no", "voucher_no"], ["customer_name", "party_name", "ledger_name"], "Dr", ["total_value", "total_amount", "gross_value", "amount"]),
        ("purchase", "Purchase Invoice", ["invoice_date", "date"], ["invoice_no", "voucher_no", "bill_no"], ["vendor_name", "supplier_name", "party_name", "ledger_name"], "Cr", ["total_value", "total_amount", "gross_value", "amount"]),
        ("expenses", "Expense Voucher", ["expense_date", "voucher_date", "date"], ["voucher_no", "invoice_no"], ["vendor_name", "supplier_name", "party_name", "expense_head"], "Cr", ["total_value", "total_amount", "amount", "net_value"]),
        ("service_vouchers", "Service Voucher", ["voucher_date", "date"], ["voucher_no"], ["customer_name", "party_name", "ledger_name"], "Dr", ["total_value", "total_amount", "amount"]),
    ]
    for table, vtype, date_cols, doc_cols, party_cols, side, amt_cols in extra_sources:
        try:
            df = load_table(table, 50000)
            if df.empty:
                continue
            for _, r in df.iterrows():
                party = next((str(r.get(c, "")) for c in party_cols if c in df.columns and str(r.get(c, "")).strip()), "")
                if ledger != "All" and party != ledger:
                    continue
                dt = next((r.get(c, "") for c in date_cols if c in df.columns), "")
                if not _date_ok(dt):
                    continue
                doc = next((r.get(c, "") for c in doc_cols if c in df.columns), "")
                amt = next((num_value(r.get(c, 0)) for c in amt_cols if c in df.columns), 0.0)
                txns.append({"Date": dt, "Voucher Type": vtype, "Voucher No": doc, "Ledger Name": party, "Particulars": vtype, "Dr Amount": amt if side == "Dr" else 0.0, "Cr Amount": amt if side == "Cr" else 0.0, "Narration / Remarks": r.get("remarks", "")})
        except Exception:
            pass

    # Sort transactions by date where possible
    def _sort_key(r):
        d = pd.to_datetime(r.get("Date", ""), dayfirst=True, errors="coerce")
        return d if not pd.isna(d) else pd.Timestamp.max
    txns = sorted(txns, key=_sort_key)

    running = opening_net
    for r in txns:
        running += num_value(r.get("Dr Amount", 0)) - num_value(r.get("Cr Amount", 0))
        r["Dr Amount"] = round(num_value(r.get("Dr Amount", 0)), 2)
        r["Cr Amount"] = round(num_value(r.get("Cr Amount", 0)), 2)
        r["Net Balance"] = round(abs(running), 2)
        r["Balance Type"] = "Dr" if running >= 0 else "Cr"
        rows.append(r)

    total_dr = sum(num_value(r.get("Dr Amount", 0)) for r in rows)
    total_cr = sum(num_value(r.get("Cr Amount", 0)) for r in rows)
    net = total_dr - total_cr
    rows.append({
        "Date": "Total",
        "Voucher Type": "",
        "Voucher No": "",
        "Ledger Name": ledger,
        "Particulars": "Net Closing Balance",
        "Dr Amount": round(total_dr, 2),
        "Cr Amount": round(total_cr, 2),
        "Net Balance": round(abs(net), 2),
        "Balance Type": "Dr" if net >= 0 else "Cr",
        "Narration / Remarks": ""
    })
    return pd.DataFrame(rows)

def report_module_screen(report_title):
    show_header(f"{module_prefix(report_title)} {report_title}", "section-rep")
    c1, c2, c3 = st.columns(3)
    from_dt = c1.date_input("From Date", value=india_now().date().replace(day=1), format="DD-MM-YYYY", key=f"rep19_from_{report_title}")
    to_dt = c2.date_input("To Date", value=india_now().date(), format="DD-MM-YYYY", key=f"rep19_to_{report_title}")
    search = c3.text_input("Search / Ledger / Party / Item", key=f"rep19_search_{report_title}")
    fmt = "Standard"
    if report_title in ["Profit Loss", "Balance Sheet"]:
        fmt = st.selectbox("P&L / B.S. Format", ["Standard", "Overheads"], key=f"rep19_fmt_{report_title}")
    if report_title == "Trial Balance":
        df = _offline_tb_df()
    elif report_title == "Profit Loss":
        df = _offline_pl_df(fmt)
    elif report_title == "Balance Sheet":
        df = _offline_bs_df(fmt)
    elif report_title in ["Sundry Receivable", "Customer Outstanding Ageing"]:
        df = pd.DataFrame(columns=["As On Date","Customer Name","Email","Mobile","Opening","Debit","Credit","Closing","Remarks"])
    elif report_title in ["Sundry Payable", "Supplier Outstanding Ageing"]:
        df = pd.DataFrame(columns=["As On Date","Supplier Name","Email","Mobile","Opening","Debit","Credit","Closing","Remarks"])
    elif report_title in ["Stock Report", "Stock Ageing / Slow Moving Stock"]:
        df = pd.DataFrame(columns=["As On Date","Item Name","Opening Stock","Purchase","Consumption","Closing Stock","Value","Remarks"])
    elif report_title in ["Gst Report", "GST Return Summary", "GST Reconciliation"]:
        df = pd.DataFrame(columns=["From Date","To Date","GST No","Taxable Value","CGST","SGST","IGST","Total GST","Remarks"])
    elif report_title == "Tds Report":
        df = pd.DataFrame(columns=["From Date","To Date","Section","Party Name","Amount","TDS","Remarks"])
    else:
        df = pd.DataFrame(columns=["Date","Document No","Party / Item","Debit","Credit","Amount","Status","Remarks"])
    if search and not df.empty:
        df = filter_dataframe(df, search)
    st.caption(f"Report: {report_title} | Format: {fmt} | Rows: {len(df)}")
    st.dataframe(df, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.download_button("Export CSV", df.to_csv(index=False).encode('utf-8'), f"{report_title.replace(' ','_')}.csv", "text/csv", use_container_width=True, key=f"csv19_{report_title}")
    c2.download_button("Export Excel", to_excel_bytes(df), f"{report_title.replace(' ','_')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx19_{report_title}")
    if c3.button("Print Report", use_container_width=True, key=f"print19_{report_title}"):
        st.markdown(f"### Print Preview - {report_title}")
        st.table(df)

# make report mapping use corrected offline-style reports
_OLD_GET_MODULE_MAPPING_PATCH19 = get_module_mapping
def get_module_mapping():
    base = _OLD_GET_MODULE_MAPPING_PATCH19()
    for _r in ["Trial Balance","Profit Loss","Balance Sheet","Sundry Receivable","Sundry Payable","Stock Report","Gst Report","Tds Report","GST Return Summary","Customer Outstanding Ageing","Supplier Outstanding Ageing","Stock Ageing / Slow Moving Stock","GST Reconciliation","Budget vs Actual","Cash Flow Statement"]:
        base[_r] = (lambda title=_r: report_module_screen(title))
    return base
# ================= END PATCH 19 =================

if "logged_in" not in st.session_state:
    login_page()
else:
    main_app()
