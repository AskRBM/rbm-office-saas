import streamlit as st
import pandas as pd
import base64
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
}

DISPLAY_COLUMNS = {
    "clients": ["id","client_code","client_name","allow_master_group","allow_task","allow_attendance","allow_inout","allow_visitor","allow_appointment","allow_stock_raw","allow_stock_fg","allow_stock_wip","allow_sales","allow_purchase","allow_expense","allow_service_voucher","allow_fixed_assets","allow_accounting","allow_excel_upload","allow_google_sheet_import","status","created_at"],
    "users": ["id","client_code","username","password","role","full_name","status"],
    "employees": ["id","client_code","employee_id","employee_name","mobile","email","department","designation","branch_division","status"],
    "attendance": ["id","client_code","attendance_date","financial_year","employee_name","attendance_type","office_location","status","in_time","out_time","working_hours","in_latitude","in_longitude","out_latitude","out_longitude","remarks","created_by"],
    "attendance_visits": ["id","client_code","visit_date","financial_year","employee_name","visit_place","in_time","out_time","in_latitude","in_longitude","out_latitude","out_longitude","remarks","created_by"],
    "inout": ["id","client_code","entry_date","financial_year","person_name","purpose","in_time","out_time","remarks","created_by"],
    "visitors": ["id","client_code","visit_date","financial_year","visitor_name","mobile","company","meeting_with","purpose","in_time","out_time","remarks","created_by"],
    "tasks": ["id","client_code","task_date","financial_year","branch_division","task","assigned_to","priority","due_date","status","remarks","task_photo_name","created_by"],
    "appointments": ["id","client_code","appointment_date","appointment_time","customer_name","mobile","email","company","purpose","meeting_with","fees","status","remarks","created_by"],
    "ledger_groups": ["id","client_code","group_name","group_type","status","created_by"],
    "ledgers": ["id","client_code","ledger_name","ledger_group","address","contact_no","tan_no","gst_no","pan_no","opening_balance","balance_type","status","created_by"],
    "stock_groups": ["id","client_code","stock_group_name","stock_type","status","created_by"],
    "stock_ledgers": ["id","client_code","item_name","item_code","stock_group","unit","hsn_code","opening_qty","opening_rate","opening_value","gst_rate","status","created_by"],
    "stock_raw": ["id","client_code","entry_date","item_name","item_code","unit","opening_qty","inward_qty","outward_qty","closing_qty","rate","value","remarks","created_by"],
    "stock_fg": ["id","client_code","entry_date","item_name","item_code","unit","opening_qty","production_qty","sales_qty","closing_qty","rate","value","remarks","created_by"],
    "stock_wip": ["id","client_code","entry_date","process_name","item_name","item_code","unit","opening_qty","input_qty","output_qty","closing_qty","remarks","created_by"],
    "stock_vouchers": ["id","client_code","voucher_no","voucher_date","voucher_type","item_name","stock_group","qty","rate","value","remarks","created_by"],
    "sales": ["id","client_code","invoice_no","invoice_date","customer_name","gstin","item_name","hsn_sac","qty","rate","taxable_value","cgst","sgst","igst","total_value","remarks","created_by"],
    "purchase": ["id","client_code","invoice_no","invoice_date","supplier_name","gstin","item_name","hsn_sac","qty","rate","taxable_value","cgst","sgst","igst","total_value","remarks","created_by"],
    "expenses": ["id","client_code","expense_date","vendor_name","expense_head","invoice_no","gstin","taxable_value","cgst","sgst","igst","total_value","payment_mode","remarks","created_by"],
    "service_vouchers": ["id","client_code","voucher_no","voucher_date","customer_name","mobile","email","service_name","sac_code","taxable_value","cgst","sgst","igst","total_value","payment_status","remarks","created_by"],
    "fixed_assets": ["id","client_code","asset_code","asset_name","purchase_date","supplier_name","invoice_no","asset_category","location","cost","depreciation_rate","status","remarks","created_by"],
    "accounting_entries": ["id","client_code","entry_date","voucher_type","voucher_no","debit_account","credit_account","amount","cgst","sgst","igst","total_amount","narration","created_by"],
    "accounting_entry_lines": ["id","client_code","entry_id","dr_cr","ledger_name","amount","remarks"],
    "import_logs": ["id","client_code","import_type","module_name","total_rows","success_rows","failed_rows","remarks","created_by"],
}

DEFAULT_LEDGER_GROUPS = ["Sundry Debtors", "Sundry Creditors", "Sales Accounts", "Purchase Accounts", "Direct Expenses", "Indirect Expenses", "Bank Accounts", "Cash-in-Hand", "Duties & Taxes", "Fixed Assets", "Loans & Advances", "Capital Account"]
DEFAULT_STOCK_GROUPS = ["Raw Material", "Finished Goods", "Work in Progress", "Packing Material", "Consumables", "Stores & Spares", "Trading Goods"]

st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}
.block-container {padding-top:1rem;padding-bottom:1.5rem;}
.rbm-header {background:linear-gradient(135deg,#082f49,#075985,#0284c7);padding:18px 24px;border-radius:18px;margin-bottom:20px;box-shadow:0 10px 24px rgba(2,132,199,.22);display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
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
[data-testid="stSidebar"] {background:linear-gradient(180deg,#f8fafc,#e0f2fe);}
</style>
""", unsafe_allow_html=True)

# ---------- BASIC HELPERS ----------
def india_now(): return datetime.now(INDIA_TZ)
def safe_df(data): return pd.DataFrame(data or [])
def get_client_code(): return st.session_state.get("client_code", "RBM")
def is_super_admin(): return st.session_state.get("role") == "Super Admin"
def current_user(): return st.session_state.get("username", "system")

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

def insert_row(key, row):
    if key != "clients" and "client_code" not in row:
        row["client_code"] = get_client_code()
    supabase.table(TABLES[key]).insert(row).execute()

def update_row(key, row_id, row):
    row.pop("financial_year", None)
    supabase.table(TABLES[key]).update(row).eq("id", int(row_id)).execute()

def delete_row(key, row_id): supabase.table(TABLES[key]).delete().eq("id", int(row_id)).execute()

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
    search = st.text_input(f"Search {title}", key=f"search_{key}")
    filtered = filter_dataframe(df, search)
    st.dataframe(filtered, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1: st.download_button("Download Excel", to_excel_bytes(filtered), f"{key}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{key}")
    with c2: st.download_button("Download CSV", filtered.to_csv(index=False).encode("utf-8"), f"{key}.csv", "text/csv", use_container_width=True, key=f"csv_{key}")
    if st.session_state.get("role") in ["Admin","Super Admin"] and not df.empty:
        st.divider(); st.subheader("Edit / Delete")
        selected_id = st.selectbox("Select ID", df["id"].tolist(), key=f"select_id_{key}")
        selected_row = df[df["id"] == selected_id].iloc[0]
        with st.expander("Edit Selected Record"):
            edited = {}
            for col in df.columns:
                if col in ["id","financial_year"]: st.text_input(col, str(selected_row[col]), disabled=True, key=f"edit_{key}_{col}")
                else: edited[col] = st.text_input(col, str(selected_row[col]), key=f"edit_{key}_{col}")
            if st.button("Update Record", use_container_width=True, key=f"update_{key}"):
                update_row(key, selected_id, edited); st.success("Record updated"); st.rerun()
        with st.expander("Delete Selected Record"):
            st.warning("This will permanently delete selected record.")
            if st.button("Delete Record", use_container_width=True, key=f"delete_{key}"):
                delete_row(key, selected_id); st.success("Record deleted"); st.rerun()

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

def get_stock_items(group_name=None):
    query = supabase.table("stock_ledgers").select("item_name,stock_group,status")
    if not is_super_admin(): query = query.eq("client_code", get_client_code())
    if group_name: query = query.eq("stock_group", group_name)
    df = safe_df(query.execute().data)
    if not df.empty and "status" in df.columns: df = df[df["status"].astype(str).str.lower() == "active"]
    names = df["item_name"].dropna().astype(str).sort_values().unique().tolist() if not df.empty and "item_name" in df.columns else []
    return names if names else ["No Item Found"]

def get_groups(table_key, col, defaults):
    df = raw_table(table_key, 1000)
    names = df[col].dropna().astype(str).unique().tolist() if not df.empty and col in df.columns else []
    return sorted(list(set(defaults + names)))

def gst_calc(taxable, gst_rate=18, gst_type="CGST+SGST"):
    try: taxable = float(taxable); gst_rate = float(gst_rate)
    except Exception: taxable = 0; gst_rate = 0
    if gst_type == "IGST":
        igst = taxable * gst_rate / 100; cgst = 0; sgst = 0
    else:
        cgst = taxable * gst_rate / 200; sgst = cgst; igst = 0
    return round(cgst,2), round(sgst,2), round(igst,2), round(taxable+cgst+sgst+igst,2)

def invoice_html(title, invoice_no, party, rows, total):
    body = "".join([f"<tr><td>{r.get('item','')}</td><td>{r.get('hsn','')}</td><td>{r.get('qty',0)}</td><td>{r.get('rate',0)}</td><td>{money(r.get('taxable',0))}</td><td>{money(r.get('gst',0))}</td><td>{money(r.get('total',0))}</td></tr>" for r in rows])
    return f"""
    <html><body style='font-family:Arial;padding:25px;'>
    <h1 style='color:#0f3b66'>{title}</h1><h3>Invoice/Voucher No: {invoice_no}</h3><h3>Party: {party}</h3>
    <table border='1' cellspacing='0' cellpadding='8' width='100%'><tr style='background:#0f3b66;color:white;'><th>Item/Service</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>Taxable</th><th>GST</th><th>Total</th></tr>{body}
    <tr><td colspan='6' align='right'><b>Grand Total</b></td><td><b>{money(total)}</b></td></tr></table>
    <p style='margin-top:30px;'>Generated by RBM AI ERP SaaS</p></body></html>"""

# ---------- LOGIN / SIDEBAR ----------
def rbm_header():
    name = st.session_state.get("client_name", get_client_code())
    st.markdown(f'<div class="rbm-header"><div class="rbm-title">RBM AI</div><div class="rbm-divider">|</div><div class="rbm-subtitle">Robotic Business Management</div><div class="rbm-client">RBM ERP SaaS | {name}</div></div>', unsafe_allow_html=True)

def init_users():
    df = safe_df(supabase.table("users").select("*").execute().data)
    if df.empty:
        supabase.table("users").insert({"client_code":"RBM","username":"admin","password":"rbm123","role":"Super Admin","full_name":"RBM Super Admin","status":"Active"}).execute()
        df = safe_df(supabase.table("users").select("*").execute().data)
    return df

def load_client_permissions(client_code):
    data = safe_df(supabase.table("clients").select("*").eq("client_code", client_code).limit(1).execute().data)
    permissions = ["allow_master_group","allow_task","allow_attendance","allow_inout","allow_visitor","allow_appointment","allow_stock_raw","allow_stock_fg","allow_stock_wip","allow_sales","allow_purchase","allow_expense","allow_service_voucher","allow_fixed_assets","allow_accounting","allow_excel_upload","allow_google_sheet_import"]
    for p in permissions: st.session_state[p] = True
    name = client_code
    if not data.empty:
        row = data.iloc[0]; name = str(row.get("client_name", client_code))
        for p in permissions: st.session_state[p] = bool(row.get(p, True))
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
    if st.sidebar.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

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
        labels = [("allow_master_group","Master"),("allow_attendance","Attendance"),("allow_inout","IN/OUT"),("allow_visitor","Visitor"),("allow_task","Task"),("allow_appointment","Appointment"),("allow_stock_raw","Raw Stock"),("allow_stock_fg","FG Stock"),("allow_stock_wip","WIP Stock"),("allow_sales","Sales"),("allow_purchase","Purchase"),("allow_expense","Expense"),("allow_service_voucher","Service Voucher"),("allow_fixed_assets","Assets"),("allow_accounting","Accounting"),("allow_excel_upload","Excel Upload"),("allow_google_sheet_import","Google Sheet")]
        vals = {}
        cols = st.columns(4)
        for i,(k,l) in enumerate(labels): vals[k] = cols[i%4].checkbox(l, value=True)
        if st.form_submit_button("Save Client", use_container_width=True):
            if not client_code or not client_name: st.error("Client Code and Name required")
            else:
                row = {"client_code":client_code,"client_name":client_name,"status":status}; row.update(vals)
                insert_row("clients", row); st.success("Client saved"); st.rerun()
    show_table_with_edit_delete("clients", load_table("clients", 500), "Client List")

def user_management():
    show_header("User Management", "section-admin")
    if st.session_state["role"] not in ["Admin","Super Admin"]: st.warning("Only Admin can access."); return
    clients_df = load_table("clients", 1000)
    with st.form("user_form"):
        c1,c2 = st.columns(2)
        client_code = c1.selectbox("Client Code", clients_df["client_code"].dropna().astype(str).tolist() if is_super_admin() and not clients_df.empty else [get_client_code()]) if is_super_admin() else get_client_code()
        if not is_super_admin(): c1.text_input("Client Code", value=client_code, disabled=True)
        username = c1.text_input("Username")
        password = c2.text_input("Password", type="password")
        role = c1.selectbox("Role", ["Admin","User"])
        full_name = c2.text_input("Full Name")
        status = c2.selectbox("Status", ["Active","Inactive"])
        if st.form_submit_button("Create User", use_container_width=True):
            if not username or not password: st.error("Username and password required")
            else: insert_row("users", {"client_code":client_code,"username":username,"password":password,"role":role,"full_name":full_name,"status":status}); st.success("User created"); st.rerun()
    show_table_with_edit_delete("users", load_table("users", 500), "User List")

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
        tan_no = c1.text_input("TAN No")
        gst_no = c2.text_input("GST No")
        pan_no = c1.text_input("PAN No")
        opening_balance = c2.number_input("Opening Balance", value=0.0)
        balance_type = c1.selectbox("Balance Type", ["Dr", "Cr"])
        status = c2.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Ledger", use_container_width=True):
            if not ledger_name: st.error("Ledger Name required")
            else: insert_row("ledgers", {"ledger_name":ledger_name,"ledger_group":ledger_group,"address":address,"contact_no":contact_no,"tan_no":tan_no,"gst_no":gst_no,"pan_no":pan_no,"opening_balance":opening_balance,"balance_type":balance_type,"status":status,"created_by":current_user()}); st.success("Ledger saved"); st.rerun()
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
            if st.form_submit_button("Save Office Attendance", use_container_width=True): insert_row("attendance", {"attendance_date":str(d),"financial_year":financial_year(d),"employee_name":empname,"attendance_type":"Office","office_location":office_location,"status":status,"in_time":str(in_time),"out_time":str(out_time),"working_hours":calculate_hours(in_time,out_time),"in_latitude":lat,"in_longitude":lon,"remarks":remarks,"created_by":current_user()}); st.success("Saved"); st.rerun()
        else:
            place = c1.text_input("Visit Place"); in_time = c2.time_input("Visit In", value=india_now().time()); out_time = c1.time_input("Visit Out", value=india_now().time()); remarks = c2.text_input("Remarks")
            if st.form_submit_button("Save Visit", use_container_width=True): insert_row("attendance_visits", {"visit_date":str(d),"financial_year":financial_year(d),"employee_name":empname,"visit_place":place,"in_time":str(in_time),"out_time":str(out_time),"in_latitude":lat,"in_longitude":lon,"remarks":remarks,"created_by":current_user()}); st.success("Saved"); st.rerun()
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
        if st.form_submit_button(f"Save {title}", use_container_width=True):
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
        photo = st.file_uploader("Upload Task Photo - Max 2 MB", type=["png","jpg","jpeg"]); photo_name=""; photo_data=""; ok=True
        if photo:
            if photo.size > MAX_FILE_SIZE_MB*1024*1024: st.error("Photo size 2 MB se zyada nahi honi chahiye."); ok=False
            else: photo_name=photo.name; photo_data=base64.b64encode(photo.read()).decode("utf-8")
        if st.form_submit_button("Save Task", use_container_width=True):
            if not task or not ok: st.error("Task required / photo size check")
            else: insert_row("tasks", {"task_date":task_date,"financial_year":financial_year(task_date),"branch_division":branch_division,"task":task,"assigned_to":assigned_to,"priority":priority,"due_date":due_date,"status":status,"remarks":remarks,"task_photo_name":photo_name,"task_photo_data":photo_data,"created_by":current_user()}); st.success("Task saved"); st.rerun()
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
    with st.form(f"{key}_form"):
        c1,c2,c3=st.columns(3)
        inv_no=c1.text_input("Invoice / Voucher No")
        inv_date=str(c2.date_input("Date", value=india_now().date(), format="DD-MM-YYYY"))
        party=c3.selectbox("Customer / Vendor Ledger", party_list)
        gstin=c1.text_input("GSTIN")
        gst_type=c2.selectbox("GST Type", ["CGST+SGST","IGST"])
        no_items=c3.number_input("No. of Items", min_value=1, max_value=10, value=1, step=1)
        rows=[]; grand=0
        for i in range(int(no_items)):
            st.markdown(f"**Item {i+1}**")
            a,b,c,d,e=st.columns(5)
            item=a.selectbox("Item", get_stock_items(), key=f"{key}_item_{i}")
            hsn=b.text_input("HSN/SAC", key=f"{key}_hsn_{i}")
            qty=c.number_input("Qty", value=1.0, key=f"{key}_qty_{i}")
            rate=d.number_input("Rate", value=0.0, key=f"{key}_rate_{i}")
            gst_rate=e.number_input("GST %", value=18.0, key=f"{key}_gst_{i}")
            taxable=qty*rate; cgst,sgst,igst,total=gst_calc(taxable,gst_rate,gst_type); grand += total
            rows.append({"item":item,"hsn":hsn,"qty":qty,"rate":rate,"taxable":taxable,"cgst":cgst,"sgst":sgst,"igst":igst,"gst":cgst+sgst+igst,"total":total})
        remarks=st.text_input("Remarks")
        st.info(f"Grand Total: {money(grand)}")
        if st.form_submit_button(f"Save {title}", use_container_width=True):
            for r in rows:
                row={"invoice_no":inv_no,"invoice_date":inv_date,party_col:party,"gstin":gstin,"item_name":r['item'],"hsn_sac":r['hsn'],"qty":r['qty'],"rate":r['rate'],"taxable_value":r['taxable'],"cgst":r['cgst'],"sgst":r['sgst'],"igst":r['igst'],"total_value":r['total'],"remarks":remarks,"created_by":current_user()}
                insert_row(key,row)
            st.success("Voucher saved"); st.rerun()
    html=invoice_html(title, inv_no if 'inv_no' in locals() else '', party if 'party' in locals() else '', rows if 'rows' in locals() else [], grand if 'grand' in locals() else 0)
    st.download_button("Print / Download Invoice HTML", html.encode("utf-8"), f"{title.replace(' ','_')}.html", "text/html", use_container_width=True)
    show_table_with_edit_delete(key, load_table(key,500), f"{title} Register")

def expense_gst():
    show_header("Expense GST Voucher", "section-acc")
    ledgers=get_ledger_names()
    with st.form("expense_form"):
        c1,c2,c3=st.columns(3)
        expense_date=str(c1.date_input("Expense Date", value=india_now().date(), format="DD-MM-YYYY")); vendor_name=c2.selectbox("Vendor Ledger", ledgers); expense_head=c3.selectbox("Expense Ledger", ledgers)
        invoice_no=c1.text_input("Invoice No"); gstin=c2.text_input("GSTIN"); taxable_value=c3.number_input("Taxable Value", value=0.0)
        gst_rate=c1.number_input("GST %", value=18.0); gst_type=c2.selectbox("GST Type", ["CGST+SGST","IGST"]); payment_mode=c3.selectbox("Payment Mode", ["Cash","Bank","UPI","Credit"])
        cgst,sgst,igst,total_value=gst_calc(taxable_value,gst_rate,gst_type); remarks=st.text_input("Remarks"); st.info(f"Total: {money(total_value)}")
        if st.form_submit_button("Save Expense GST", use_container_width=True): insert_row("expenses", {"expense_date":expense_date,"vendor_name":vendor_name,"expense_head":expense_head,"invoice_no":invoice_no,"gstin":gstin,"taxable_value":taxable_value,"cgst":cgst,"sgst":sgst,"igst":igst,"total_value":total_value,"payment_mode":payment_mode,"remarks":remarks,"created_by":current_user()}); st.success("Saved"); st.rerun()
    show_table_with_edit_delete("expenses", load_table("expenses",500), "Expense Register")

def service_voucher():
    show_header("Service Voucher", "section-acc")
    customers=get_ledger_names("Sundry Debtors")
    with st.form("service_form"):
        c1,c2,c3=st.columns(3)
        voucher_no=c1.text_input("Voucher No"); voucher_date=str(c2.date_input("Date", value=india_now().date(), format="DD-MM-YYYY")); customer_name=c3.selectbox("Customer", customers)
        mobile=c1.text_input("Mobile"); email=c2.text_input("Email"); service_name=c3.text_input("Service Name")
        sac_code=c1.text_input("SAC Code"); taxable_value=c2.number_input("Taxable Value", value=0.0); gst_rate=c3.number_input("GST %", value=18.0)
        gst_type=c1.selectbox("GST Type", ["CGST+SGST","IGST"]); payment_status=c2.selectbox("Payment Status", ["Pending","Received","Partly Received"])
        cgst,sgst,igst,total_value=gst_calc(taxable_value,gst_rate,gst_type); remarks=st.text_input("Remarks"); st.info(f"Total: {money(total_value)}")
        if st.form_submit_button("Save Service Voucher", use_container_width=True): insert_row("service_vouchers", {"voucher_no":voucher_no,"voucher_date":voucher_date,"customer_name":customer_name,"mobile":mobile,"email":email,"service_name":service_name,"sac_code":sac_code,"taxable_value":taxable_value,"cgst":cgst,"sgst":sgst,"igst":igst,"total_value":total_value,"payment_status":payment_status,"remarks":remarks,"created_by":current_user()}); st.success("Saved"); st.rerun()
    html=invoice_html("Service Voucher", voucher_no if 'voucher_no' in locals() else '', customer_name if 'customer_name' in locals() else '', [{"item":service_name if 'service_name' in locals() else '',"hsn":sac_code if 'sac_code' in locals() else '',"qty":1,"rate":taxable_value if 'taxable_value' in locals() else 0,"taxable":taxable_value if 'taxable_value' in locals() else 0,"gst":(cgst+sgst+igst) if 'cgst' in locals() else 0,"total":total_value if 'total_value' in locals() else 0}], total_value if 'total_value' in locals() else 0)
    st.download_button("Print / Download Service Voucher", html.encode("utf-8"), "service_voucher.html", "text/html", use_container_width=True)
    show_table_with_edit_delete("service_vouchers", load_table("service_vouchers",500), "Service Register")

def fixed_assets(): simple_module_form("fixed_assets", "Fixed Assets", [("asset_code","Asset Code","text"),("asset_name","Asset Name","text"),("purchase_date","Purchase Date","date"),("supplier_name","Supplier",get_ledger_names("Sundry Creditors")),("invoice_no","Invoice No","text"),("asset_category","Category","text"),("location","Location","text"),("cost","Cost","number"),("depreciation_rate","Depreciation %","number"),("status","Status",["Active","Sold","Scrapped"]),("remarks","Remarks","text")], "section-acc")

def accounting_entries():
    show_header("Accounting Entries - Multiple Dr / Cr", "section-acc")
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
        st.info(f"Total Dr: {money(total_dr)} | Total Cr: {money(total_cr)} | GST: {money(cgst+sgst+igst)}")
        if st.form_submit_button("Save Accounting Entry", use_container_width=True):
            if round(total_dr,2) != round(total_cr,2): st.error("Total Debit and Credit must be equal")
            else:
                header={"entry_date":entry_date,"voucher_type":voucher_type,"voucher_no":voucher_no,"debit_account":"Multiple","credit_account":"Multiple","amount":total_dr,"cgst":cgst,"sgst":sgst,"igst":igst,"total_amount":total_dr+cgst+sgst+igst,"narration":narration,"created_by":current_user()}
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

def reports():
    show_header("Registers / Reports", "section-rep")
    opts=["employees","ledgers","stock_ledgers","sales","purchase","expenses","service_vouchers","stock_vouchers","fixed_assets","accounting_entries","accounting_entry_lines","appointments","attendance","attendance_visits","inout","visitors","tasks"]
    if is_super_admin(): opts=["clients","users"]+opts
    report = st.selectbox("Select Register", opts)
    rows = st.number_input("Rows to load", 100, 50000, 1000, 100)
    df=load_table(report, int(rows)); search=st.text_input("Search Report"); filtered=filter_dataframe(df, search)
    st.dataframe(filtered, use_container_width=True)
    c1,c2=st.columns(2)
    with c1: st.download_button("Download Excel", to_excel_bytes(filtered), f"{report}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c2: st.download_button("Download CSV", filtered.to_csv(index=False).encode("utf-8"), f"{report}.csv", "text/csv", use_container_width=True)

def placeholder_denied(): st.warning("This module is not enabled for this client.")

# ---------- MAIN MENU ----------
def main_app():
    rbm_header(); compact_sidebar()
    groups = ["Dashboard", "Master", "Admin", "HR", "Inventory", "Accounts", "Reports"]
    group = st.sidebar.selectbox("Group", groups, key="menu_group")
    modules = []
    if group == "Dashboard": modules=["Dashboard"]
    elif group == "Master": modules=["Ledger Group Master","Ledger Master","Stock Group Master","Stock Ledger Master"] if st.session_state.get("allow_master_group", True) else []
    elif group == "Admin":
        modules=[]
        if is_super_admin(): modules += ["Client Master"]
        if st.session_state.get("role") in ["Admin","Super Admin"]: modules += ["User Management","Employee Master"]
        if st.session_state.get("allow_appointment", True): modules += ["Appointments"]
    elif group == "HR":
        if st.session_state.get("allow_attendance", True): modules.append("Attendance Management")
        if st.session_state.get("allow_inout", True): modules.append("IN / OUT Register")
        if st.session_state.get("allow_visitor", True): modules.append("Visitor Register")
        if st.session_state.get("allow_task", True): modules.append("Task Delegation")
    elif group == "Inventory":
        if st.session_state.get("allow_stock_raw", True): modules.append("Raw Material Stock")
        if st.session_state.get("allow_stock_fg", True): modules.append("Finished Goods Stock")
        if st.session_state.get("allow_stock_wip", True): modules.append("WIP Stock")
        modules.append("Stock Voucher")
    elif group == "Accounts":
        if st.session_state.get("allow_sales", True): modules.append("Sales GST Invoice")
        if st.session_state.get("allow_purchase", True): modules.append("Purchase GST Invoice")
        if st.session_state.get("allow_expense", True): modules.append("Expense GST")
        if st.session_state.get("allow_service_voucher", True): modules.append("Service Voucher")
        if st.session_state.get("allow_fixed_assets", True): modules.append("Fixed Assets")
        if st.session_state.get("allow_accounting", True): modules.append("Accounting Entries")
    elif group == "Reports":
        modules=["Registers / Reports"]
        if st.session_state.get("allow_excel_upload", True) or st.session_state.get("allow_google_sheet_import", True): modules.append("Import Center")
    if not modules: modules=["No module available"]
    choice = st.sidebar.radio("Module", modules, key="menu_module")

    mapping={
        "Dashboard": dashboard, "Client Master": client_master, "User Management": user_management, "Employee Master": employee_master,
        "Ledger Group Master": ledger_group_master, "Ledger Master": ledger_master, "Stock Group Master": stock_group_master, "Stock Ledger Master": stock_ledger_master,
        "Attendance Management": attendance, "IN / OUT Register": inout_register, "Visitor Register": visitor_register, "Task Delegation": task_delegation, "Appointments": appointment_module,
        "Raw Material Stock": stock_raw, "Finished Goods Stock": stock_fg, "WIP Stock": stock_wip, "Stock Voucher": stock_voucher,
        "Sales GST Invoice": sales_invoice, "Purchase GST Invoice": purchase_invoice, "Expense GST": expense_gst, "Service Voucher": service_voucher, "Fixed Assets": fixed_assets, "Accounting Entries": accounting_entries,
        "Registers / Reports": reports, "Import Center": import_center,
    }
    mapping.get(choice, placeholder_denied)()

if "logged_in" not in st.session_state:
    login_page()
else:
    main_app()
