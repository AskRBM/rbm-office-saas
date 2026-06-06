import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import json
import string
from datetime import datetime, date
from io import BytesIO
from zoneinfo import ZoneInfo
from supabase import create_client, Client
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="RBM ERP SaaS", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

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
}

DISPLAY_COLUMNS = {
    "clients": ["id","client_code","client_name","allow_master_group","allow_task","allow_attendance","allow_inout","allow_visitor","allow_appointment","allow_stock_raw","allow_stock_fg","allow_stock_wip","allow_sales","allow_purchase","allow_expense","allow_service_voucher","allow_fixed_assets","allow_accounting","allow_excel_upload","allow_google_sheet_import","allow_quotation","allow_manufacturing","allow_project_accounting","allow_subscription","allow_support","allow_license_manager","status","created_at"],
    "users": ["id","client_code","username","password","role","full_name","status"],
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
    "quotations": ["id","client_code","requirement_id","requirement_no","business_username","business_name","quotation_no","quotation_date","amount","gst_amount","total_amount","valid_till","quotation_file_name","quotation_status","remarks","created_by","created_at"],
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
}

DEFAULT_LEDGER_GROUPS = ["Sundry Debtors", "Sundry Creditors", "Sales Accounts", "Purchase Accounts", "Direct Expenses", "Indirect Expenses", "Bank Accounts", "Cash-in-Hand", "Duties & Taxes", "Fixed Assets", "Loans & Advances", "Capital Account"]
DEFAULT_STOCK_GROUPS = ["Raw Material", "Finished Goods", "Work in Progress", "Packing Material", "Consumables", "Stores & Spares", "Trading Goods"]

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
def is_super_admin(): return st.session_state.get("role") == "Super Admin"
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
        with c1: st.download_button("Download Excel", to_excel_bytes(filtered), f"{key}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{key}")
        with c2: st.download_button("Download CSV", filtered.to_csv(index=False).encode("utf-8"), f"{key}.csv", "text/csv", use_container_width=True, key=f"csv_{key}")
    if (is_super_admin() or (st.session_state.get("role") == "Admin" and (has_key_permission(key,"edit") or has_key_permission(key,"delete") or has_key_permission(key,"reverse")))) and not df.empty:
        st.divider(); st.subheader("Edit / Delete")
        selected_id = st.selectbox("Select ID", df["id"].tolist(), key=f"select_id_{key}")
        selected_row = df[df["id"] == selected_id].iloc[0]
        with st.expander("Edit Selected Record"):
            edited = {}
            for col in df.columns:
                if col in ["id","financial_year"]: st.text_input(col, str(selected_row[col]), disabled=True, key=f"edit_{key}_{col}")
                else: edited[col] = st.text_input(col, str(selected_row[col]), key=f"edit_{key}_{col}")
            if has_key_permission(key, "edit") or is_super_admin():
                if st.button("Update Record", use_container_width=True, key=f"update_{key}"):
                    update_row(key, selected_id, edited); st.session_state[f"last_action_msg_{key}"] = "Record updated successfully. Details closed."; st.rerun()
            else:
                st.info("You do not have edit permission for this module.")
        if key in REVERSIBLE_TABLE_KEYS:
            with st.expander("Reverse / Cancel Posted Entry"):
                st.warning("This will create a separate reversal entry and mark the original as Reversed. It will not delete original data.")
                reversal_reason = st.text_input("Reversal Reason", key=f"reverse_reason_{key}")
                if has_key_permission(key, "reverse") or is_super_admin():
                    if st.button("Reverse Selected Entry", use_container_width=True, key=f"reverse_{key}"):
                        ok, msg = reverse_record(key, selected_id, reversal_reason)
                        if ok:
                            st.session_state[f"last_action_msg_{key}"] = msg
                            st.rerun()
                        else:
                            st.error(msg)
                else:
                    st.info("You do not have reverse permission for this module.")

        with st.expander("Delete Selected Record"):
            st.warning("This will permanently delete selected record. Prefer Reverse for posted/saved business entries.")
            if has_key_permission(key, "delete") or is_super_admin():
                if st.button("Delete Record", use_container_width=True, key=f"delete_{key}"):
                    delete_row(key, selected_id); st.session_state[f"last_action_msg_{key}"] = "Record deleted successfully. Details closed."; st.rerun()
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
        supabase.table("users").insert({"client_code":"RBM","username":"admin","password":"rbm123","role":"Super Admin","full_name":"RBM Super Admin","status":"Active"}).execute()
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
        st.info("Default Super Admin: admin / rbm123")

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
    if not is_super_admin(): st.warning("Only Super Admin can access Client Master."); return
    with st.form("client_form"):
        c1,c2 = st.columns(2)
        client_code = c1.text_input("Client Code", placeholder="Example: CST01").upper()
        client_name = c2.text_input("Name", placeholder="Example: CST")
        status = c1.selectbox("Status", ["Active","Inactive"])
        st.subheader("Module Access")
        labels = [("allow_master_group","Master"),("allow_attendance","Attendance"),("allow_inout","IN/OUT"),("allow_visitor","Visitor"),("allow_task","Task"),("allow_appointment","Appointment"),("allow_stock_raw","Raw Stock"),("allow_stock_fg","FG Stock"),("allow_stock_wip","WIP Stock"),("allow_sales","Sales"),("allow_purchase","Purchase"),("allow_expense","Expense"),("allow_service_voucher","Service Voucher"),("allow_fixed_assets","Assets"),("allow_accounting","Accounting"),("allow_excel_upload","Excel Upload"),("allow_google_sheet_import","Google Sheet"),("allow_quotation","Quotation"),("allow_manufacturing","Manufacturing / BOM"),("allow_project_accounting","Project Accounting"),("allow_subscription","AMC / Subscription"),("allow_support","Support Desk"),("allow_license_manager","License Manager")]
        vals = {}
        cols = st.columns(4)
        for i,(k,l) in enumerate(labels): vals[k] = cols[i%4].checkbox(l, value=False)
        if st.form_submit_button("Save Client", use_container_width=True):
            if not client_code or not client_name: st.error("Client Code and Name required")
            else:
                row = {"client_code":client_code,"client_name":client_name,"status":status}; row.update(vals)
                insert_row("clients", row); st.success("Client saved"); st.rerun()
    show_table_with_edit_delete("clients", load_table("clients", 500), "Client List")

def user_management():
    show_header("User Management", "section-admin")

    if st.session_state.get("role") not in ["Admin", "Super Admin"]:
        st.warning("Only Admin can access User Management.")
        return

    # Super Admin can create users for any client.
    # Client Admin can create users only for his own client_code/business.
    if is_super_admin():
        clients_df = load_table("clients", 1000)
        client_codes = clients_df["client_code"].dropna().astype(str).tolist() if not clients_df.empty else ["RBM"]
        if "RBM" not in client_codes:
            client_codes = ["RBM"] + client_codes
        selected_client_code = st.selectbox("Client Code", client_codes, key="um_client_code")
        users_df = load_table("users", 1000)
    else:
        selected_client_code = get_client_code()
        st.info(f"You are creating users only for your business: {selected_client_code}")
        users_df = load_table("users", 1000)

    with st.form("user_form"):
        c1, c2 = st.columns(2)

        c1.text_input("Client Code", value=selected_client_code, disabled=True)
        username = c1.text_input("Username")
        password = c2.text_input("Password", type="password")

        if is_super_admin():
            role = c1.selectbox("Role", ["Admin", "User", "Quotation User", "Super Admin"])
        else:
            role = c1.selectbox("Role", ["Admin", "User", "Quotation User"])

        full_name = c2.text_input("Full Name")
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


def quotation_module():
    show_header("Quotation Portal", "section-acc")

    role = st.session_state.get("role", "")
    username = current_user()

    if role in ["Admin", "Super Admin"]:
        tab1, tab2, tab3, tab4 = st.tabs([
            "Our Requirements",
            "Business Users",
            "Requirement Access",
            "Received Quotations",
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

    elif _quote_role():
        st.info("You can see only requirements assigned to your business username and only your own quotations.")
        access_df = load_table("quotation_access", 5000)
        access_df = access_df[access_df["business_username"].astype(str) == username] if not access_df.empty and "business_username" in access_df.columns else pd.DataFrame()
        allowed_ids = access_df["requirement_id"].dropna().astype(int).tolist() if not access_df.empty and "requirement_id" in access_df.columns else []

        tab1, tab2 = st.tabs(["Assigned Requirements", "My Submitted Quotations"])
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
            if report_type == "Trial Balance":
                show_df = tb[["ledger_group","ledger_name","opening_dr","opening_cr","debit","credit","closing_dr","closing_cr"]].copy()
            elif report_type == "Profit & Loss":
                show_df = build_profit_loss_df(tb)
            else:
                show_df = build_balance_sheet_df(tb)
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
    "Client Master": "__super_admin__",
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

    if flag == "__client_admin_normal__":
        return st.session_state.get("role") == "Admin" and _normal_feature_enabled_from_session()

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
    if role == "Super Admin":
        return True
    if module_name in SUPER_ADMIN_ONLY_MODULES:
        return False
    if role == "Admin":
        return True
    if role == "Quotation User":
        return module_name == "Quotation" and action in ["view", "add", "print", "export"]
    if role == "User":
        return action in ["view", "print", "export"]
    return action == "view"

def has_permission(module_name, action="view"):
    try:
        if is_super_admin():
            return True
        if module_name in SUPER_ADMIN_ONLY_MODULES:
            return False
        action = str(action).lower().strip()
        if action not in PERMISSION_ACTIONS:
            return False
        role_name = str(st.session_state.get("role", "User"))
        client_code = get_client_code()
        data = supabase.table("role_permissions").select("*").eq("client_code", client_code).eq("role_name", role_name).eq("module_name", module_name).limit(1).execute().data
        dfp = safe_df(data)
        if dfp.empty:
            return default_permission(module_name, action)
        col = f"can_{action}"
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
        if m in SUPER_ADMIN_ONLY_MODULES:
            continue
        if module_enabled_for_current_client(m) and has_permission(m, "view"):
            allowed.append(m)
    return allowed or ["No module available"]

def role_permission_control():
    show_header("Role-wise Permission Control", "section-admin")
    if st.session_state.get("role") not in ["Admin", "Super Admin"]:
        st.warning("Only Admin can access Role Permission Control.")
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
    role_name = st.selectbox("Select Role", ["Admin", "User", "Quotation User", "Manager", "Approver", "Viewer"], key="perm_role")
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
            if (not is_super_admin()) and module in SUPER_ADMIN_ONLY_MODULES:
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
    modules = []
    if group == "Dashboard":
        modules = ["Dashboard"]
    elif group == "Master":
        modules = ["Company Profile", "Financial Year Master", "Cost Center Master", "Document Series", "GST Settings", "Ledger Group Master", "Ledger Master", "Stock Group Master", "Stock Ledger Master"] if st.session_state.get("allow_master_group", False) else []
    elif group == "Admin":
        if is_super_admin():
            modules += ["Client Master", "User Management", "Role Permission Control", "Employee Master"]
        else:
            # Client Admin sees Admin tools only when normal ERP modules are enabled.
            # Quotation-only clients do not see User Management / Role Permission / Employee Master.
            if st.session_state.get("role") == "Admin" and _normal_feature_enabled_from_session():
                modules += ["User Management", "Role Permission Control"]
                if st.session_state.get("allow_master_group", False):
                    modules += ["Employee Master"]
        if st.session_state.get("allow_appointment", False):
            modules += ["Appointments"]
    elif group == "HR":
        if st.session_state.get("allow_attendance", False):
            modules.append("Attendance Management")
        if st.session_state.get("allow_inout", False):
            modules.append("IN / OUT Register")
        if st.session_state.get("allow_visitor", False):
            modules.append("Visitor Register")
        if st.session_state.get("allow_task", False):
            modules.append("Task Delegation")
    elif group == "Inventory":
        if st.session_state.get("allow_stock_raw", False):
            modules.append("Raw Material Stock")
        if st.session_state.get("allow_stock_fg", False):
            modules.append("Finished Goods Stock")
        if st.session_state.get("allow_stock_wip", False):
            modules.append("WIP Stock")
        if modules:
            modules.append("Stock Voucher")
    elif group == "Accounts":
        if st.session_state.get("allow_sales", False):
            modules.append("Sales GST Invoice")
        if st.session_state.get("allow_purchase", False):
            modules.append("Purchase GST Invoice")
        if st.session_state.get("allow_expense", False):
            modules.append("Expense GST")
        if st.session_state.get("allow_service_voucher", False):
            modules.append("Service Voucher")
        if st.session_state.get("allow_fixed_assets", False):
            modules.append("Fixed Assets")
        if st.session_state.get("allow_accounting", False):
            modules.append("Accounting Entries")
    elif group == "Quotation":
        if is_super_admin() or st.session_state.get("allow_quotation", False) or _quote_role():
            modules = ["Quotation"]
    elif group == "Manufacturing":
        if is_super_admin() or st.session_state.get("allow_manufacturing", False):
            modules = ["Bill of Material", "Production Order", "Production Entry", "Consumption Entry", "Finished Goods Entry", "Production Costing", "Material Requirement Planning"]
    elif group == "Projects":
        if is_super_admin() or st.session_state.get("allow_project_accounting", False):
            modules = ["Project Accounting"]
    elif group == "Support":
        if is_super_admin() or st.session_state.get("allow_support", False) or st.session_state.get("role") == "Admin":
            modules = ["Support Desk"]
        if is_super_admin() or st.session_state.get("allow_subscription", False):
            modules.append("AMC / Subscription")
        if is_super_admin() or st.session_state.get("allow_license_manager", False):
            modules.append("License Manager")
    elif group == "Reports":
        if is_super_admin():
            modules = ["Registers / Reports", "Import Center", "Audit Log"]
        else:
            # Reports group appears only when enabled groups exist.
            modules = ["Registers / Reports"]
            if st.session_state.get("allow_excel_upload", False) or st.session_state.get("allow_google_sheet_import", False):
                modules.append("Import Center")
            if st.session_state.get("role") == "Admin":
                modules.append("Audit Log")
    elif group == "Tools":
        if is_super_admin():
            modules = ["Calculation Book", "ERP Control Center", "Notification Center", "Dashboard Analytics", "PWA Mobile App", "Calculator", "Offline Sync Engine"]
        elif st.session_state.get("role") == "Admin":
            modules = ["Calculation Book"]
    elif group == "Enterprise":
        if is_super_admin():
            modules = ["Workflow Engine", "Budget vs Actual", "Bank Reconciliation", "Document Management", "Purchase Cycle", "Sales Cycle", "Advanced Asset Management", "Digital Audit", "Multi Company / Branch"]
    return filter_modules_by_permission(modules)

def build_group_list():
    # Super Admin can see every group always.
    if _quote_role():
        return ["Quotation"]

    if (not is_super_admin()) and _quotation_only_from_session():
        return ["Quotation"]

    if is_super_admin():
        return ["Dashboard", "Master", "Admin", "HR", "Inventory", "Manufacturing", "Accounts", "Projects", "Quotation", "Reports", "Enterprise", "Support", "Tools"]

    # Client users/admins should see ONLY groups enabled for that client.
    groups = []

    # Dashboard only when user has at least one core ERP module. Optional enterprise defaults do not count.
    has_any_normal_module = _core_feature_enabled_from_session()

    if has_any_normal_module:
        groups.append("Dashboard")

    if st.session_state.get("allow_master_group", False):
        groups.append("Master")

    admin_modules = []
    # Admin group is visible to client Admin only when normal ERP modules are enabled.
    # Quotation-only clients must see only Quotation.
    if st.session_state.get("role") == "Admin" and has_any_normal_module:
        admin_modules.extend(["User Management", "Role Permission Control"])
    if st.session_state.get("allow_appointment", False):
        admin_modules.append("Appointments")
    if admin_modules:
        groups.append("Admin")

    if any([
        st.session_state.get("allow_attendance", False),
        st.session_state.get("allow_inout", False),
        st.session_state.get("allow_visitor", False),
        st.session_state.get("allow_task", False),
    ]):
        groups.append("HR")

    if any([
        st.session_state.get("allow_stock_raw", False),
        st.session_state.get("allow_stock_fg", False),
        st.session_state.get("allow_stock_wip", False),
    ]):
        groups.append("Inventory")

    if st.session_state.get("allow_manufacturing", False):
        groups.append("Manufacturing")

    if any([
        st.session_state.get("allow_sales", False),
        st.session_state.get("allow_purchase", False),
        st.session_state.get("allow_expense", False),
        st.session_state.get("allow_service_voucher", False),
        st.session_state.get("allow_fixed_assets", False),
        st.session_state.get("allow_accounting", False),
    ]):
        groups.append("Accounts")

    if st.session_state.get("allow_project_accounting", False):
        groups.append("Projects")

    if st.session_state.get("allow_quotation", False):
        groups.append("Quotation")

    if any([
        st.session_state.get("allow_excel_upload", False),
        st.session_state.get("allow_google_sheet_import", False),
        has_any_normal_module,
    ]):
        groups.append("Reports")

    if any([st.session_state.get("allow_support", False), st.session_state.get("allow_subscription", False), st.session_state.get("allow_license_manager", False)]):
        groups.append("Support")

    # Enterprise tools are RBM internal / Super Admin only.
    if st.session_state.get("role") == "Admin" and has_any_normal_module:
        groups.append("Tools")

    return groups or ["Quotation"]


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

    choice = st.radio("Module", modules, index=default_module_index, key="menu_module")

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


def get_module_mapping():
    return {
        "Dashboard": dashboard,
        "Client Master": client_master,
        "User Management": user_management,
        "Role Permission Control": role_permission_control,
        "Employee Master": employee_master,
        "Company Profile": company_profile,
        "Financial Year Master": financial_year_master,
        "Cost Center Master": cost_center_master,
        "Document Series": document_series_master,
        "GST Settings": gst_settings_master,
        "Ledger Group Master": ledger_group_master,
        "Ledger Master": ledger_master,
        "Stock Group Master": stock_group_master,
        "Stock Ledger Master": stock_ledger_master,
        "Attendance Management": attendance,
        "IN / OUT Register": inout_register,
        "Visitor Register": visitor_register,
        "Task Delegation": task_delegation,
        "Appointments": appointment_module,
        "Raw Material Stock": stock_raw,
        "Finished Goods Stock": stock_fg,
        "WIP Stock": stock_wip,
        "Stock Voucher": stock_voucher,
        "Bill of Material": bill_of_material_module,
        "Production Order": production_order_module,
        "Production Entry": production_entry_module,
        "Consumption Entry": consumption_entry_module,
        "Finished Goods Entry": finished_goods_entry_module,
        "Production Costing": production_costing_module,
        "Material Requirement Planning": mrp_module,
        "Sales GST Invoice": sales_invoice,
        "Purchase GST Invoice": purchase_invoice,
        "Expense GST": expense_gst,
        "Service Voucher": service_voucher,
        "Fixed Assets": fixed_assets,
        "Accounting Entries": accounting_entries,
        "Registers / Reports": reports,
        "Import Center": import_center,
        "Calculation Book": calculation_book,
        "ERP Control Center": erp_control_center,
        "Audit Log": audit_log_report,
        "Quotation": quotation_module,
        "Workflow Engine": workflow_engine,
        "Notification Center": notification_center,
        "Dashboard Analytics": dashboard_analytics,
        "Budget vs Actual": budget_vs_actual,
        "Bank Reconciliation": bank_reconciliation,
        "Document Management": document_management,
        "Purchase Cycle": purchase_cycle,
        "Sales Cycle": sales_cycle,
        "Advanced Asset Management": asset_management_advanced,
        "PWA Mobile App": pwa_mobile_app,
        "Digital Audit": digital_audit_module,
        "Calculator": ai_assistant,
        "Multi Company / Branch": multi_company_branch,
        "Offline Sync Engine": offline_sync_engine,
        "Project Accounting": project_accounting_module,
        "AMC / Subscription": amc_subscription_module,
        "Support Desk": support_ticket_module,
        "License Manager": license_manager_module,
    }


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
            mapping.get(choice, placeholder_denied)()
    else:
        # When hidden, show the unhide button, but keep the same current module open.
        if st.button("☰ Show Menu", key="show_menu_when_hidden"):
            st.session_state["sidebar_open"] = True
            st.rerun()
        rbm_header()
        st.info("Menu is hidden. Click ☰ Show Menu to show it again.")
        choice = st.session_state.get("active_choice", "Dashboard")
        mapping.get(choice, placeholder_denied)()


if "logged_in" not in st.session_state:
    login_page()
else:
    main_app()
