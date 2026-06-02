
import streamlit as st
import pandas as pd
import base64
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo
from supabase import create_client, Client
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(
    page_title="RBM Office SaaS",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

INDIA_TZ = ZoneInfo("Asia/Kolkata")
MAX_FILE_SIZE_MB = 2

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLES = {
    "clients": "clients",
    "users": "users",
    "employees": "employees",
    "attendance": "attendance",
    "attendance_visits": "attendance_visits",
    "inout": "inout_register",
    "visitors": "visitors",
    "tasks": "tasks",
    "appointments": "appointments",
    "stock_raw_material": "stock_raw_material",
    "stock_finished_goods": "stock_finished_goods",
    "stock_wip": "stock_wip",
    "sales": "sales",
    "purchase": "purchase",
    "expenses": "expenses",
    "service_vouchers": "service_vouchers",
    "fixed_assets": "fixed_assets",
    "accounting_entries": "accounting_entries",
}

DISPLAY_COLUMNS = {
    "clients": [
        "id", "client_code", "client_name",
        "allow_task", "allow_attendance", "allow_inout", "allow_visitor",
        "allow_appointment", "allow_raw_material", "allow_finished_goods", "allow_wip",
        "allow_sales", "allow_purchase", "allow_expense", "allow_service_voucher",
        "allow_fixed_assets", "allow_accounting_entries", "allow_excel_upload",
        "allow_google_sheet_import", "status", "created_at"
    ],
    "users": ["id", "client_code", "username", "password", "role", "full_name", "status"],
    "employees": ["id", "client_code", "employee_id", "employee_name", "mobile", "email", "department", "designation", "branch_division", "status"],
    "attendance": ["id", "client_code", "attendance_date", "financial_year", "employee_name", "attendance_type", "office_location", "status", "in_time", "out_time", "working_hours", "in_latitude", "in_longitude", "out_latitude", "out_longitude", "remarks", "created_by"],
    "attendance_visits": ["id", "client_code", "visit_date", "financial_year", "employee_name", "visit_place", "in_time", "out_time", "in_latitude", "in_longitude", "out_latitude", "out_longitude", "remarks", "created_by"],
    "inout": ["id", "client_code", "entry_date", "financial_year", "person_name", "purpose", "in_time", "out_time", "remarks", "created_by"],
    "visitors": ["id", "client_code", "visit_date", "financial_year", "visitor_name", "mobile", "company", "meeting_with", "purpose", "in_time", "out_time", "remarks", "created_by"],
    "tasks": ["id", "client_code", "task_date", "financial_year", "branch_division", "task", "assigned_to", "priority", "due_date", "status", "remarks", "task_photo_name", "created_by"],
    "appointments": ["id", "client_code", "appointment_date", "financial_year", "appointment_time", "customer_name", "mobile", "email", "company", "purpose", "meeting_with", "fees", "status", "remarks", "created_by"],
    "stock_raw_material": ["id", "client_code", "entry_date", "financial_year", "item_code", "item_name", "uom", "opening_qty", "inward_qty", "outward_qty", "closing_qty", "rate", "value", "remarks", "created_by"],
    "stock_finished_goods": ["id", "client_code", "entry_date", "financial_year", "item_code", "item_name", "uom", "opening_qty", "production_qty", "sales_qty", "closing_qty", "rate", "value", "remarks", "created_by"],
    "stock_wip": ["id", "client_code", "entry_date", "financial_year", "process_name", "item_name", "uom", "opening_qty", "input_qty", "output_qty", "closing_qty", "rate", "value", "remarks", "created_by"],
    "sales": ["id", "client_code", "invoice_no", "invoice_date", "financial_year", "customer_name", "gstin", "place_of_supply", "item_name", "hsn_sac", "qty", "rate", "taxable_value", "cgst", "sgst", "igst", "total_value", "remarks", "created_by"],
    "purchase": ["id", "client_code", "invoice_no", "invoice_date", "financial_year", "vendor_name", "gstin", "place_of_supply", "item_name", "hsn_sac", "qty", "rate", "taxable_value", "cgst", "sgst", "igst", "total_value", "remarks", "created_by"],
    "expenses": ["id", "client_code", "expense_date", "financial_year", "expense_head", "vendor_name", "gstin", "invoice_no", "taxable_value", "cgst", "sgst", "igst", "total_value", "payment_mode", "remarks", "created_by"],
    "service_vouchers": ["id", "client_code", "voucher_no", "voucher_date", "financial_year", "customer_name", "mobile", "email", "service_name", "sac_code", "taxable_value", "cgst", "sgst", "igst", "total_value", "payment_status", "remarks", "created_by"],
    "fixed_assets": ["id", "client_code", "asset_code", "asset_name", "purchase_date", "financial_year", "vendor_name", "invoice_no", "asset_category", "location", "cost", "gst_amount", "total_cost", "useful_life_years", "status", "remarks", "created_by"],
    "accounting_entries": ["id", "client_code", "entry_date", "financial_year", "voucher_type", "voucher_no", "ledger_dr", "ledger_cr", "amount", "narration", "created_by"],
}

MODULE_PERMISSIONS = {
    "Attendance Management": "allow_attendance",
    "IN / OUT Register": "allow_inout",
    "Visitor Register": "allow_visitor",
    "Task Delegation": "allow_task",
    "Appointments": "allow_appointment",
    "Raw Material Stock": "allow_raw_material",
    "Finished Goods Stock": "allow_finished_goods",
    "WIP Stock": "allow_wip",
    "Sales GST Invoice": "allow_sales",
    "Purchase GST Invoice": "allow_purchase",
    "Expense GST": "allow_expense",
    "Service Voucher": "allow_service_voucher",
    "Fixed Assets": "allow_fixed_assets",
    "Accounting Entries": "allow_accounting_entries",
}

st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
.block-container {padding-top:1.5rem;padding-bottom:2rem;}
.rbm-header {
    background:linear-gradient(135deg,#001f54,#003566);
    padding:24px 28px;border-radius:18px;margin-bottom:25px;
    box-shadow:0px 8px 25px rgba(0,31,84,0.25);
    display:flex;align-items:center;gap:16px;flex-wrap:wrap;
}
.rbm-title {color:white;font-size:38px;font-weight:900;margin:0;line-height:1;}
.rbm-divider {color:white;font-size:34px;font-weight:300;}
.rbm-subtitle {color:white;font-size:17px;font-weight:500;}
.rbm-client {background:#002855;color:#38bdf8;font-size:15px;font-weight:600;padding:8px 12px;border-radius:4px;}
.metric-card {background:white;padding:22px;border-radius:18px;box-shadow:0px 6px 18px rgba(0,0,0,0.08);border:1px solid #e5e7eb;text-align:center;}
.metric-number {font-size:34px;font-weight:800;color:#001f54;}
.metric-label {color:#64748b;font-size:15px;}
.invoice-box {border:1px solid #d1d5db; padding:18px; border-radius:12px; background:white;}
.stButton button, .stDownloadButton button {border-radius:12px;font-weight:700;}
.group-admin {background:#dbeafe;padding:10px;border-radius:12px;font-weight:800;color:#1e3a8a;margin-top:8px;}
.group-hr {background:#dcfce7;padding:10px;border-radius:12px;font-weight:800;color:#14532d;margin-top:8px;}
.group-stock {background:#ffedd5;padding:10px;border-radius:12px;font-weight:800;color:#7c2d12;margin-top:8px;}
.group-accounts {background:#f3e8ff;padding:10px;border-radius:12px;font-weight:800;color:#581c87;margin-top:8px;}
.group-reports {background:#fee2e2;padding:10px;border-radius:12px;font-weight:800;color:#7f1d1d;margin-top:8px;}
</style>
""", unsafe_allow_html=True)


def india_now():
    return datetime.now(INDIA_TZ)


def safe_df(data):
    return pd.DataFrame(data or [])


def indian_date(value):
    try:
        if value in ["", None]:
            return ""
        return pd.to_datetime(value).strftime("%d-%m-%Y")
    except Exception:
        return value


def indian_time(value):
    try:
        if value in ["", None]:
            return ""
        return str(value)[:5]
    except Exception:
        return value


def financial_year(value):
    try:
        d = pd.to_datetime(value)
        if d.month >= 4:
            return f"{d.year}-{str(d.year + 1)[-2:]}"
        return f"{d.year - 1}-{str(d.year)[-2:]}"
    except Exception:
        return ""


def format_df_for_display(df):
    if df.empty:
        return df
    df = df.copy()

    fy_source_cols = [
        "attendance_date", "visit_date", "entry_date", "task_date", "due_date", "created_at",
        "appointment_date", "invoice_date", "expense_date", "purchase_date", "voucher_date"
    ]

    for col in fy_source_cols:
        if col in df.columns and "financial_year" not in df.columns:
            df["financial_year"] = df[col].apply(financial_year)
            break

    date_cols = [
        "attendance_date", "visit_date", "entry_date", "task_date", "due_date", "created_at",
        "appointment_date", "invoice_date", "expense_date", "purchase_date", "voucher_date"
    ]

    for col in date_cols:
        if col in df.columns:
            df[col] = df[col].apply(indian_date)

    time_cols = ["in_time", "out_time", "appointment_time"]
    for col in time_cols:
        if col in df.columns:
            df[col] = df[col].apply(indian_time)

    return df


def get_client_code():
    return st.session_state.get("client_code", "RBM")


def is_super_admin():
    return st.session_state.get("role") == "Super Admin"


def is_allowed(module_name):
    if is_super_admin():
        return True
    key = MODULE_PERMISSIONS.get(module_name)
    if not key:
        return True
    return st.session_state.get(key, True)


def get_gps():
    loc = streamlit_geolocation()
    lat = ""
    lon = ""
    if loc:
        lat = str(loc.get("latitude", "") or "")
        lon = str(loc.get("longitude", "") or "")
    return lat, lon


def map_link(lat, lon):
    if str(lat).strip() == "" or str(lon).strip() == "":
        return ""
    return f"https://www.google.com/maps?q={lat},{lon}"


def rbm_header():
    client_name = st.session_state.get("client_name", get_client_code())
    st.markdown(f"""
    <div class="rbm-header">
        <div class="rbm-title">RBM AI</div>
        <div class="rbm-divider">|</div>
        <div class="rbm-subtitle">Robotic Business Management</div>
        <div class="rbm-client">RBM Office SaaS | {client_name}</div>
    </div>
    """, unsafe_allow_html=True)


def load_table(key, limit_rows=500):
    query = supabase.table(TABLES[key]).select("*")
    if key != "clients" and not is_super_admin():
        query = query.eq("client_code", get_client_code())

    response = query.order("id", desc=True).limit(limit_rows).execute()
    df = safe_df(response.data)
    df = format_df_for_display(df)

    if key in DISPLAY_COLUMNS:
        for col in DISPLAY_COLUMNS[key]:
            if col not in df.columns:
                df[col] = ""
        df = df[DISPLAY_COLUMNS[key]]
    return df


def insert_row(key, row):
    if key != "clients" and "client_code" not in row:
        row["client_code"] = get_client_code()
    supabase.table(TABLES[key]).insert(row).execute()


def update_row(key, row_id, row):
    if "financial_year" in row:
        row.pop("financial_year")
    supabase.table(TABLES[key]).update(row).eq("id", row_id).execute()


def delete_row(key, row_id):
    supabase.table(TABLES[key]).delete().eq("id", row_id).execute()


def get_count(key):
    query = supabase.table(TABLES[key]).select("id", count="exact")
    if key != "clients" and not is_super_admin():
        query = query.eq("client_code", get_client_code())
    response = query.execute()
    return response.count or 0


def filter_dataframe(df, keyword):
    if keyword.strip() == "":
        return df
    keyword = keyword.lower()
    mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(keyword, na=False).any(), axis=1)
    return df[mask]


def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()


def calculate_hours(in_time, out_time):
    try:
        t1 = datetime.strptime(str(in_time), "%H:%M:%S")
        t2 = datetime.strptime(str(out_time), "%H:%M:%S")
        return round((t2 - t1).seconds / 3600, 2)
    except Exception:
        return 0


def calc_gst(qty, rate, cgst_rate=0, sgst_rate=0, igst_rate=0):
    taxable = round(float(qty or 0) * float(rate or 0), 2)
    cgst = round(taxable * float(cgst_rate or 0) / 100, 2)
    sgst = round(taxable * float(sgst_rate or 0) / 100, 2)
    igst = round(taxable * float(igst_rate or 0) / 100, 2)
    total = round(taxable + cgst + sgst + igst, 2)
    return taxable, cgst, sgst, igst, total


def show_metric_card(label, value):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def next_employee_id(df):
    if df.empty:
        return "EMP001"
    nums = []
    for x in df["employee_id"].dropna().astype(str):
        if x.upper().startswith("EMP"):
            n = x.upper().replace("EMP", "")
            if n.isdigit():
                nums.append(int(n))
    return f"EMP{max(nums) + 1:03d}" if nums else "EMP001"


def show_table_with_edit_delete(key, df, title):
    st.subheader(title)
    st.caption("Latest records shown for speed. Date format: DD-MM-YYYY. Time format: 24-hour.")

    search = st.text_input(f"Search {title}", key=f"search_{key}")
    filtered = filter_dataframe(df, search)
    st.dataframe(filtered, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Download Excel",
            data=to_excel_bytes(filtered),
            file_name=f"{key}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"xlsx_{key}"
        )
    with c2:
        st.download_button(
            "Download CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"{key}.csv",
            mime="text/csv",
            use_container_width=True,
            key=f"csv_{key}"
        )

    if st.session_state.get("role") in ["Admin", "Super Admin"] and not df.empty:
        st.divider()
        st.subheader("Edit / Delete")
        selected_id = st.selectbox("Select ID", df["id"].tolist(), key=f"select_id_{key}")
        selected_row = df[df["id"] == selected_id].iloc[0]

        with st.expander("Edit Selected Record"):
            edited_values = {}
            for col in df.columns:
                if col in ["id", "financial_year"]:
                    st.text_input(col, value=str(selected_row[col]), disabled=True, key=f"edit_{key}_{col}")
                else:
                    edited_values[col] = st.text_input(col, value=str(selected_row[col]), key=f"edit_{key}_{col}")

            if st.button("Update Record", use_container_width=True, key=f"update_{key}"):
                update_row(key, int(selected_id), edited_values)
                st.success("Record updated successfully")
                st.rerun()

        with st.expander("Delete Selected Record"):
            st.warning("This will permanently delete selected record.")
            if st.button("Delete Record", use_container_width=True, key=f"delete_{key}"):
                delete_row(key, int(selected_id))
                st.success("Record deleted successfully")
                st.rerun()


def login_page():
    rbm_header()
    st.subheader("Secure Login")

    users = safe_df(supabase.table("users").select("*").execute().data)
    c1, c2, c3 = st.columns([1, 2, 1])

    with c2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if users.empty:
                st.error("No user found in database.")
                return

            match = users[
                (users["username"].astype(str) == username) &
                (users["password"].astype(str) == password)
            ]

            if match.empty:
                st.error("Wrong username or password")
            else:
                row = match.iloc[0]
                if "status" in users.columns and str(row.get("status", "Active")) == "Inactive":
                    st.error("This user is inactive.")
                    return

                client_code = str(row.get("client_code", "RBM"))
                client_name = client_code
                client_data = safe_df(
                    supabase.table("clients")
                    .select("*")
                    .eq("client_code", client_code)
                    .limit(1)
                    .execute()
                    .data
                )

                permission_keys = list(set(MODULE_PERMISSIONS.values()))

                if not client_data.empty:
                    client_row = client_data.iloc[0]
                    client_name = str(client_row.get("client_name", client_code))
                    for key in permission_keys:
                        st.session_state[key] = bool(client_row.get(key, True))
                else:
                    for key in permission_keys:
                        st.session_state[key] = True

                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = str(row.get("role", "User"))
                st.session_state["full_name"] = str(row.get("full_name", username))
                st.session_state["client_code"] = client_code
                st.session_state["client_name"] = client_name
                st.rerun()

        st.info("Super Admin Login: RBM / ******")


def dashboard():
    st.header("Dashboard")

    today_india = india_now().strftime("%d-%m-%Y")
    current_fy = financial_year(india_now().date())
    st.info(f"Today: {today_india} | India Time Zone: Asia/Kolkata | Financial Year: {current_fy}")

    metric_items = [
        ("Employees", "employees"),
        ("Attendance", "attendance"),
        ("Visits", "attendance_visits"),
        ("Visitors", "visitors"),
        ("Tasks", "tasks"),
        ("Appointments", "appointments"),
        ("Sales", "sales"),
        ("Purchase", "purchase"),
        ("Expenses", "expenses"),
        ("Services", "service_vouchers"),
        ("Assets", "fixed_assets"),
    ]

    cols = st.columns(5)
    for i, (label, table_key) in enumerate(metric_items):
        with cols[i % 5]:
            show_metric_card(label, get_count(table_key))

    st.divider()
    st.subheader("Latest Tasks")
    st.dataframe(load_table("tasks", 50), use_container_width=True)


def client_master():
    st.header("Client Master")

    if not is_super_admin():
        st.warning("Only Super Admin can access Client Master.")
        return

    with st.form("client_form"):
        c1, c2 = st.columns(2)
        client_code = c1.text_input("Client Code", placeholder="Example: CHOICE")
        client_name = c2.text_input("Client Name", placeholder="Example: Choice Group")
        status = c1.selectbox("Status", ["Active", "Inactive"])

        st.subheader("Office Module Access")
        m1, m2, m3, m4, m5 = st.columns(5)
        allow_task = m1.checkbox("Task", value=True)
        allow_attendance = m2.checkbox("Attendance", value=True)
        allow_inout = m3.checkbox("IN / OUT", value=True)
        allow_visitor = m4.checkbox("Visitor", value=True)
        allow_appointment = m5.checkbox("Appointment", value=True)

        st.subheader("ERP / Inventory Module Access")
        e1, e2, e3, e4 = st.columns(4)
        allow_raw_material = e1.checkbox("Raw Material", value=True)
        allow_finished_goods = e2.checkbox("Finished Goods", value=True)
        allow_wip = e3.checkbox("WIP", value=True)
        allow_sales = e4.checkbox("Sales", value=True)

        e5, e6, e7, e8 = st.columns(4)
        allow_purchase = e5.checkbox("Purchase", value=True)
        allow_expense = e6.checkbox("Expense", value=True)
        allow_service_voucher = e7.checkbox("Service Voucher", value=True)
        allow_fixed_assets = e8.checkbox("Fixed Assets", value=True)

        e9, e10, e11 = st.columns(3)
        allow_accounting_entries = e9.checkbox("Accounting Entries", value=True)
        allow_excel_upload = e10.checkbox("Excel Upload", value=True)
        allow_google_sheet_import = e11.checkbox("Google Sheet Import", value=True)

        if st.form_submit_button("Save Client", use_container_width=True):
            if client_code.strip() == "" or client_name.strip() == "":
                st.error("Client Code and Client Name are required.")
            else:
                insert_row("clients", {
                    "client_code": client_code.strip().upper(),
                    "client_name": client_name.strip(),
                    "allow_task": allow_task,
                    "allow_attendance": allow_attendance,
                    "allow_inout": allow_inout,
                    "allow_visitor": allow_visitor,
                    "allow_appointment": allow_appointment,
                    "allow_raw_material": allow_raw_material,
                    "allow_finished_goods": allow_finished_goods,
                    "allow_wip": allow_wip,
                    "allow_sales": allow_sales,
                    "allow_purchase": allow_purchase,
                    "allow_expense": allow_expense,
                    "allow_service_voucher": allow_service_voucher,
                    "allow_fixed_assets": allow_fixed_assets,
                    "allow_accounting_entries": allow_accounting_entries,
                    "allow_excel_upload": allow_excel_upload,
                    "allow_google_sheet_import": allow_google_sheet_import,
                    "status": status
                })
                st.success("Client saved successfully.")
                st.rerun()

    df = load_table("clients", 500)
    show_table_with_edit_delete("clients", df, "Client List")


def user_management():
    st.header("User Management")

    if st.session_state["role"] not in ["Admin", "Super Admin"]:
        st.warning("Only Admin can access User Management.")
        return

    clients_df = load_table("clients", 1000)

    with st.form("user_form"):
        c1, c2 = st.columns(2)
        if is_super_admin():
            client_codes = clients_df["client_code"].dropna().astype(str).tolist() if not clients_df.empty else ["RBM"]
            client_code = c1.selectbox("Client Code", client_codes)
        else:
            client_code = get_client_code()
            c1.text_input("Client Code", value=client_code, disabled=True)

        username = c1.text_input("Username")
        password = c2.text_input("Password", type="password")
        role = c1.selectbox("Role", ["Admin", "User"])
        full_name = c2.text_input("Full Name")
        status = c2.selectbox("Status", ["Active", "Inactive"])

        if st.form_submit_button("Create User", use_container_width=True):
            if username.strip() == "" or password.strip() == "":
                st.error("Username and password are required.")
            else:
                insert_row("users", {
                    "client_code": client_code,
                    "username": username,
                    "password": password,
                    "role": role,
                    "full_name": full_name,
                    "status": status
                })
                st.success("User created successfully.")
                st.rerun()

    df = load_table("users", 500)
    show_table_with_edit_delete("users", df, "User List")


def employee_master():
    st.header("Employee Master")

    df = load_table("employees", 500)
    auto_id = next_employee_id(df)

    with st.form("employee_form"):
        c1, c2 = st.columns(2)
        employee_id = c1.text_input("Employee ID", value=auto_id)
        employee_name = c2.text_input("Employee Name")
        mobile = c1.text_input("Mobile")
        email = c2.text_input("Email")
        department = c1.text_input("Department")
        designation = c2.text_input("Designation")
        branch_division = c1.text_input("Branch / Division")
        status = c2.selectbox("Status", ["Active", "Inactive"])

        if st.form_submit_button("Save Employee", use_container_width=True):
            if employee_name.strip() == "":
                st.error("Employee Name is required.")
            else:
                insert_row("employees", {
                    "employee_id": employee_id,
                    "employee_name": employee_name,
                    "mobile": mobile,
                    "email": email,
                    "department": department,
                    "designation": designation,
                    "branch_division": branch_division,
                    "status": status
                })
                st.success("Employee saved successfully.")
                st.rerun()

    show_table_with_edit_delete("employees", df, "Employee List")


def attendance():
    st.header("Attendance Management with GPS")

    emp = load_table("employees", 1000)
    emp_list = emp["employee_name"].dropna().astype(str).tolist() if not emp.empty else []
    if not emp_list:
        emp_list = ["No Employee Found"]

    st.info("Mobile/browser location permission Allow karna hoga. GPS tabhi capture hoga.")
    lat, lon = get_gps()

    if lat and lon:
        st.success(f"GPS Captured: {lat}, {lon}")
        st.markdown(f"[Open Current Location in Google Maps]({map_link(lat, lon)})")
    else:
        st.warning("GPS location not captured yet. Browser permission Allow karein.")

    attendance_type = st.radio("Attendance Type", ["Office", "Visit"], horizontal=True, key="attendance_type_radio")
    if attendance_type == "Office":
        office_attendance_form(emp_list, lat, lon)
    else:
        visit_attendance_form(emp_list, lat, lon)

    st.divider()
    show_table_with_edit_delete("attendance", load_table("attendance", 500), "Office Attendance")
    st.divider()
    show_table_with_edit_delete("attendance_visits", load_table("attendance_visits", 500), "Visit / Field Work Attendance")


def office_attendance_form(emp_list, lat, lon):
    st.subheader("Office Attendance")

    with st.form("office_attendance_form"):
        c1, c2 = st.columns(2)
        attendance_date = c1.date_input("Date", value=india_now().date(), format="DD-MM-YYYY")
        employee_name = c2.selectbox("Employee Name", emp_list)
        office_location = c1.text_input("Office Location", value="Office")
        status = c2.selectbox("Status", ["Present", "Absent", "Half Day", "Leave"])
        in_time = c1.time_input("In Time", value=india_now().time())
        out_time = c2.time_input("Out Time", value=india_now().time())
        gps_for = c1.selectbox("GPS Save For", ["In Location", "Out Location", "Both"])
        remarks = c2.text_input("Remarks")

        if st.form_submit_button("Save Office Attendance", use_container_width=True):
            if employee_name == "No Employee Found":
                st.error("Please create employee first.")
                return

            insert_row("attendance", {
                "attendance_date": str(attendance_date),
                "employee_name": employee_name,
                "attendance_type": "Office",
                "office_location": office_location,
                "status": status,
                "in_time": str(in_time),
                "out_time": str(out_time),
                "working_hours": calculate_hours(in_time, out_time),
                "in_latitude": lat if gps_for in ["In Location", "Both"] else "",
                "in_longitude": lon if gps_for in ["In Location", "Both"] else "",
                "out_latitude": lat if gps_for in ["Out Location", "Both"] else "",
                "out_longitude": lon if gps_for in ["Out Location", "Both"] else "",
                "remarks": remarks,
                "created_by": st.session_state["username"]
            })
            st.success("Office attendance saved successfully.")
            st.rerun()


def visit_attendance_form(emp_list, lat, lon):
    st.subheader("Visit / Field Work Attendance")

    with st.form("visit_attendance_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        visit_date = c1.date_input("Visit Date", value=india_now().date(), format="DD-MM-YYYY")
        employee_name = c2.selectbox("Employee Name", emp_list)
        visit_place = c1.text_input("Visit Place / Client / Vendor / Site")
        in_time = c2.time_input("Visit In Time", value=india_now().time())
        out_time = c1.time_input("Visit Out Time", value=india_now().time())
        gps_for = c2.selectbox("GPS Save For", ["In Location", "Out Location", "Both"])
        remarks = c1.text_input("Remarks")

        if st.form_submit_button("Save Visit Entry", use_container_width=True):
            if employee_name == "No Employee Found":
                st.error("Please create employee first.")
                return
            if visit_place.strip() == "":
                st.error("Visit place is required.")
                return

            insert_row("attendance_visits", {
                "visit_date": str(visit_date),
                "employee_name": employee_name,
                "visit_place": visit_place,
                "in_time": str(in_time),
                "out_time": str(out_time),
                "in_latitude": lat if gps_for in ["In Location", "Both"] else "",
                "in_longitude": lon if gps_for in ["In Location", "Both"] else "",
                "out_latitude": lat if gps_for in ["Out Location", "Both"] else "",
                "out_longitude": lon if gps_for in ["Out Location", "Both"] else "",
                "remarks": remarks,
                "created_by": st.session_state["username"]
            })
            st.success("Visit entry saved successfully.")
            st.rerun()


def inout_register():
    st.header("IN / OUT Register")
    df = load_table("inout", 500)

    with st.form("inout_form"):
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Date", value=india_now().date(), format="DD-MM-YYYY")
        person_name = c2.text_input("Person Name")
        purpose = c1.text_input("Purpose")
        in_time = c2.time_input("In Time", value=india_now().time())
        out_time = c1.time_input("Out Time", value=india_now().time())
        remarks = c2.text_input("Remarks")

        if st.form_submit_button("Save IN / OUT Entry", use_container_width=True):
            if person_name.strip() == "":
                st.error("Person Name is required.")
            else:
                insert_row("inout", {
                    "entry_date": str(entry_date),
                    "person_name": person_name,
                    "purpose": purpose,
                    "in_time": str(in_time),
                    "out_time": str(out_time),
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("IN / OUT entry saved successfully.")
                st.rerun()

    show_table_with_edit_delete("inout", df, "IN / OUT Records")


def visitor_register():
    st.header("Visitor Register")
    df = load_table("visitors", 500)

    with st.form("visitor_form"):
        c1, c2 = st.columns(2)
        visit_date = c1.date_input("Date", value=india_now().date(), format="DD-MM-YYYY")
        visitor_name = c2.text_input("Visitor Name")
        mobile = c1.text_input("Mobile")
        company = c2.text_input("Company")
        meeting_with = c1.text_input("Meeting With")
        purpose = c2.text_input("Purpose")
        in_time = c1.time_input("In Time", value=india_now().time())
        out_time = c2.time_input("Out Time", value=india_now().time())
        remarks = c1.text_input("Remarks")

        if st.form_submit_button("Save Visitor", use_container_width=True):
            if visitor_name.strip() == "":
                st.error("Visitor Name is required.")
            else:
                insert_row("visitors", {
                    "visit_date": str(visit_date),
                    "visitor_name": visitor_name,
                    "mobile": mobile,
                    "company": company,
                    "meeting_with": meeting_with,
                    "purpose": purpose,
                    "in_time": str(in_time),
                    "out_time": str(out_time),
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Visitor saved successfully.")
                st.rerun()

    show_table_with_edit_delete("visitors", df, "Visitor Records")


def task_delegation():
    st.header("Task Delegation")

    df = load_table("tasks", 500)
    emp = load_table("employees", 1000)
    emp_list = emp["employee_name"].dropna().astype(str).tolist() if not emp.empty else []
    emp_list = ["All"] + emp_list

    if not emp.empty and "branch_division" in emp.columns:
        branch_list = emp["branch_division"].dropna().astype(str).unique().tolist()
        branch_list = ["All"] + sorted([x for x in branch_list if x.strip() != ""])
    else:
        branch_list = ["All"]

    st.subheader("Assign Type")
    assign_mode = st.radio("Choose assign method", ["Select Employee", "Manual Entry"], horizontal=True, key="task_assign_mode_radio")

    with st.form("task_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        task_date = c1.date_input("Task Date", value=india_now().date(), format="DD-MM-YYYY")
        branch_division = c1.selectbox("Branch / Division", branch_list)
        task = c2.text_area("Task")
        priority = c1.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
        status = c1.selectbox("Status", ["Pending", "In Progress", "Completed"])

        if assign_mode == "Manual Entry":
            assigned_to = c2.text_input("Assigned To", placeholder="Type manual name here")
        else:
            assigned_to = c2.selectbox("Assigned To", emp_list)

        due_date = c2.date_input("Due Date", value=india_now().date(), format="DD-MM-YYYY")
        remarks = c2.text_input("Remarks")
        task_photo = st.file_uploader("Upload Task Photo / Screenshot - Max 2 MB", type=["png", "jpg", "jpeg"], key="task_photo_upload")

        task_photo_name = ""
        task_photo_data = ""
        file_size_ok = True

        if task_photo is not None:
            if task_photo.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                st.error("Photo size 2 MB se zyada nahi honi chahiye.")
                file_size_ok = False
            else:
                task_photo_name = task_photo.name
                task_photo_data = base64.b64encode(task_photo.read()).decode("utf-8")
                st.success(f"Photo ready: {task_photo_name}")

        if st.form_submit_button("Save Task", use_container_width=True):
            if task.strip() == "":
                st.error("Task is required.")
            elif str(assigned_to).strip() == "":
                st.error("Assigned To is required.")
            elif not file_size_ok:
                st.error("Task save nahi hoga. Photo size 2 MB se kam rakho.")
            else:
                insert_row("tasks", {
                    "task_date": str(task_date),
                    "branch_division": branch_division,
                    "task": task,
                    "assigned_to": str(assigned_to),
                    "priority": priority,
                    "due_date": str(due_date),
                    "status": status,
                    "remarks": remarks,
                    "task_photo_name": task_photo_name,
                    "task_photo_data": task_photo_data,
                    "created_by": st.session_state["username"]
                })
                st.success("Task saved successfully.")
                st.rerun()

    show_table_with_edit_delete("tasks", df, "Task Records")
    show_task_photo_viewer()


def show_task_photo_viewer():
    st.divider()
    st.subheader("View Task Photo")
    photo_query = supabase.table("tasks").select("*")

    if not is_super_admin():
        photo_query = photo_query.eq("client_code", get_client_code())

    raw_df = safe_df(photo_query.order("id", desc=True).limit(500).execute().data)

    if raw_df.empty or "task_photo_data" not in raw_df.columns:
        st.info("No task photo found.")
        return

    photo_df = raw_df[raw_df["task_photo_name"].astype(str).str.strip() != ""]
    if photo_df.empty:
        st.info("No task photo found.")
        return

    selected_photo_id = st.selectbox("Select Task ID to View Photo", photo_df["id"].tolist(), key="view_task_photo_id")
    row = photo_df[photo_df["id"] == selected_photo_id].iloc[0]
    photo_data = row.get("task_photo_data", "")

    if str(photo_data).strip() != "":
        st.image(base64.b64decode(photo_data), caption=f"Task ID: {selected_photo_id} | {row.get('task_photo_name', '')}", use_container_width=True)



def excel_upload_section(table_key, title, required_columns=None):
    if not st.session_state.get("allow_excel_upload", True) and not is_super_admin():
        return

    with st.expander(f"Excel Upload - {title}"):
        st.caption("Upload .xlsx or .csv file. Column names should match database column names shown in the register.")
        uploaded_file = st.file_uploader(f"Upload {title} Excel/CSV", type=["xlsx", "csv"], key=f"upload_{table_key}")

        if uploaded_file is not None:
            try:
                if uploaded_file.name.lower().endswith(".csv"):
                    upload_df = pd.read_csv(uploaded_file)
                else:
                    upload_df = pd.read_excel(uploaded_file)

                st.dataframe(upload_df.head(20), use_container_width=True)

                if required_columns:
                    missing = [c for c in required_columns if c not in upload_df.columns]
                    if missing:
                        st.error("Missing columns: " + ", ".join(missing))
                        return

                if st.button(f"Import {len(upload_df)} rows to {title}", use_container_width=True, key=f"import_{table_key}"):
                    ok = 0
                    fail = 0
                    allowed_cols = [c for c in DISPLAY_COLUMNS.get(table_key, []) if c not in ["id", "financial_year", "created_at"]]

                    for _, r in upload_df.iterrows():
                        row = {}
                        for col in allowed_cols:
                            if col in upload_df.columns:
                                val = r[col]
                                if pd.isna(val):
                                    val = ""
                                row[col] = val
                        row["created_by"] = st.session_state.get("username", "")
                        try:
                            insert_row(table_key, row)
                            ok += 1
                        except Exception:
                            fail += 1

                    try:
                        insert_row("import_logs", {
                            "import_type": "Excel",
                            "module_name": table_key,
                            "total_rows": len(upload_df),
                            "success_rows": ok,
                            "failed_rows": fail,
                            "remarks": uploaded_file.name,
                            "created_by": st.session_state.get("username", "")
                        })
                    except Exception:
                        pass

                    st.success(f"Import completed. Success: {ok}, Failed: {fail}")
                    st.rerun()
            except Exception as e:
                st.error(f"Upload failed: {e}")


def google_sheet_import_section(table_key, title):
    if not st.session_state.get("allow_google_sheet_import", True) and not is_super_admin():
        return

    with st.expander(f"Google Sheet Import - {title}"):
        st.caption("Paste public Google Sheet CSV export link. Private Google Sheet integration can be added later using Google service account.")
        sheet_url = st.text_input("Google Sheet CSV URL", key=f"gsheet_{table_key}")
        if st.button("Import from Google Sheet", use_container_width=True, key=f"gsheet_import_{table_key}"):
            if sheet_url.strip() == "":
                st.error("Please paste Google Sheet CSV URL.")
            else:
                try:
                    gdf = pd.read_csv(sheet_url)
                    st.dataframe(gdf.head(20), use_container_width=True)
                    st.info("Preview loaded. For safety, use Excel Upload import button for final import, or ask me to enable direct Google import.")
                except Exception as e:
                    st.error(f"Could not read Google Sheet: {e}")

def appointment_module():
    st.header("Appointment of Clients / Customers")
    df = load_table("appointments", 500)

    with st.form("appointment_form"):
        c1, c2 = st.columns(2)
        appointment_date = c1.date_input("Appointment Date", value=india_now().date(), format="DD-MM-YYYY")
        appointment_time = c2.time_input("Appointment Time", value=india_now().time())
        customer_name = c1.text_input("Client / Customer Name")
        mobile = c2.text_input("Mobile")
        email = c1.text_input("Email")
        company = c2.text_input("Company")
        purpose = c1.text_input("Purpose")
        meeting_with = c2.text_input("Meeting With")
        fees = c1.number_input("Fees", value=0.0)
        status = c2.selectbox("Status", ["Scheduled", "Completed", "Cancelled"])
        remarks = c1.text_input("Remarks")

        if st.form_submit_button("Save Appointment", use_container_width=True):
            if customer_name.strip() == "":
                st.error("Client / Customer Name is required.")
            else:
                insert_row("appointments", {
                    "appointment_date": str(appointment_date),
                    "appointment_time": str(appointment_time),
                    "customer_name": customer_name,
                    "mobile": mobile,
                    "email": email,
                    "company": company,
                    "purpose": purpose,
                    "meeting_with": meeting_with,
                    "fees": fees,
                    "status": status,
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Appointment saved successfully.")
                st.rerun()

    show_table_with_edit_delete("appointments", df, "Appointment Records")
    excel_upload_section("appointments", "Appointments", ["appointment_date", "customer_name"])
    google_sheet_import_section("appointments", "Appointments")


def stock_form(module_key, title, mode):
    st.header(title)
    df = load_table(module_key, 500)

    with st.form(f"{module_key}_form"):
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Entry Date", value=india_now().date(), format="DD-MM-YYYY")

        if module_key == "stock_wip":
            process_name = c2.text_input("Process Name")
            item_code = ""
        else:
            item_code = c2.text_input("Item Code")
            process_name = ""

        item_name = c1.text_input("Item Name")
        uom = c2.text_input("UOM", value="PCS")

        opening_qty = c1.number_input("Opening Qty", value=0.0)
        if mode == "raw":
            in_qty = c2.number_input("Inward Qty", value=0.0)
            out_qty = c1.number_input("Outward Qty", value=0.0)
        elif mode == "fg":
            in_qty = c2.number_input("Production Qty", value=0.0)
            out_qty = c1.number_input("Sales Qty", value=0.0)
        else:
            in_qty = c2.number_input("Input Qty", value=0.0)
            out_qty = c1.number_input("Output Qty", value=0.0)

        closing_qty = opening_qty + in_qty - out_qty
        rate = c2.number_input("Rate", value=0.0)
        value = round(closing_qty * rate, 2)
        remarks = c1.text_input("Remarks")

        st.info(f"Calculated Closing Qty: {closing_qty} | Value: {value}")

        if st.form_submit_button("Save Stock", use_container_width=True):
            row = {
                "entry_date": str(entry_date),
                "item_name": item_name,
                "uom": uom,
                "opening_qty": opening_qty,
                "closing_qty": closing_qty,
                "rate": rate,
                "value": value,
                "remarks": remarks,
                "created_by": st.session_state["username"]
            }

            if module_key == "stock_raw_material":
                row.update({"item_code": item_code, "inward_qty": in_qty, "outward_qty": out_qty})
            elif module_key == "stock_finished_goods":
                row.update({"item_code": item_code, "production_qty": in_qty, "sales_qty": out_qty})
            else:
                row.update({"process_name": process_name, "input_qty": in_qty, "output_qty": out_qty})

            insert_row(module_key, row)
            st.success("Stock saved successfully.")
            st.rerun()

    show_table_with_edit_delete(module_key, df, title)
    excel_upload_section(module_key, title)
    google_sheet_import_section(module_key, title)


def sales_purchase_form(module_key, title, party_label):
    st.header(title)
    df = load_table(module_key, 500)

    with st.form(f"{module_key}_form"):
        c1, c2 = st.columns(2)
        invoice_no = c1.text_input("Invoice No")
        invoice_date = c2.date_input("Invoice Date", value=india_now().date(), format="DD-MM-YYYY")
        party_name = c1.text_input(party_label)
        gstin = c2.text_input("GSTIN")
        place_of_supply = c1.text_input("Place of Supply")
        item_name = c2.text_input("Item / Service Name")
        hsn_sac = c1.text_input("HSN / SAC")
        qty = c2.number_input("Qty", value=1.0)
        rate = c1.number_input("Rate", value=0.0)
        cgst_rate = c2.number_input("CGST %", value=0.0)
        sgst_rate = c1.number_input("SGST %", value=0.0)
        igst_rate = c2.number_input("IGST %", value=0.0)
        remarks = c1.text_input("Remarks")

        taxable, cgst, sgst, igst, total = calc_gst(qty, rate, cgst_rate, sgst_rate, igst_rate)

        st.markdown(f"""
        <div class="invoice-box">
        <h4>Invoice Preview</h4>
        <b>Invoice No:</b> {invoice_no}<br>
        <b>{party_label}:</b> {party_name}<br>
        <b>GSTIN:</b> {gstin}<br>
        <b>Item:</b> {item_name}<br>
        <b>Taxable:</b> ₹ {taxable:,.2f}<br>
        <b>CGST:</b> ₹ {cgst:,.2f} | <b>SGST:</b> ₹ {sgst:,.2f} | <b>IGST:</b> ₹ {igst:,.2f}<br>
        <h3>Total: ₹ {total:,.2f}</h3>
        </div>
        """, unsafe_allow_html=True)

        if st.form_submit_button("Save Invoice", use_container_width=True):
            if invoice_no.strip() == "" or party_name.strip() == "":
                st.error("Invoice No and Party Name are required.")
            else:
                party_col = "customer_name" if module_key == "sales" else "vendor_name"
                insert_row(module_key, {
                    "invoice_no": invoice_no,
                    "invoice_date": str(invoice_date),
                    party_col: party_name,
                    "gstin": gstin,
                    "place_of_supply": place_of_supply,
                    "item_name": item_name,
                    "hsn_sac": hsn_sac,
                    "qty": qty,
                    "rate": rate,
                    "taxable_value": taxable,
                    "cgst": cgst,
                    "sgst": sgst,
                    "igst": igst,
                    "total_value": total,
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Invoice saved successfully.")
                st.rerun()

    show_table_with_edit_delete(module_key, df, title)
    excel_upload_section(module_key, title, ["invoice_no", "invoice_date"])
    google_sheet_import_section(module_key, title)


def expense_module():
    st.header("Expense with GST")
    df = load_table("expenses", 500)

    with st.form("expense_form"):
        c1, c2 = st.columns(2)
        expense_date = c1.date_input("Expense Date", value=india_now().date(), format="DD-MM-YYYY")
        expense_head = c2.text_input("Expense Head")
        vendor_name = c1.text_input("Vendor Name")
        gstin = c2.text_input("GSTIN")
        invoice_no = c1.text_input("Invoice No")
        taxable = c2.number_input("Taxable Value", value=0.0)
        cgst_rate = c1.number_input("CGST %", value=0.0)
        sgst_rate = c2.number_input("SGST %", value=0.0)
        igst_rate = c1.number_input("IGST %", value=0.0)
        cgst = round(taxable * cgst_rate / 100, 2)
        sgst = round(taxable * sgst_rate / 100, 2)
        igst = round(taxable * igst_rate / 100, 2)
        total = round(taxable + cgst + sgst + igst, 2)
        payment_mode = c2.selectbox("Payment Mode", ["Cash", "Bank", "UPI", "Credit"])
        remarks = c1.text_input("Remarks")

        st.info(f"Taxable: ₹ {taxable:,.2f} | CGST: ₹ {cgst:,.2f} | SGST: ₹ {sgst:,.2f} | IGST: ₹ {igst:,.2f} | Total: ₹ {total:,.2f}")

        if st.form_submit_button("Save Expense", use_container_width=True):
            if expense_head.strip() == "":
                st.error("Expense Head is required.")
            else:
                insert_row("expenses", {
                    "expense_date": str(expense_date),
                    "expense_head": expense_head,
                    "vendor_name": vendor_name,
                    "gstin": gstin,
                    "invoice_no": invoice_no,
                    "taxable_value": taxable,
                    "cgst": cgst,
                    "sgst": sgst,
                    "igst": igst,
                    "total_value": total,
                    "payment_mode": payment_mode,
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Expense saved successfully.")
                st.rerun()

    show_table_with_edit_delete("expenses", df, "Expense Register")
    excel_upload_section("expenses", "Expense GST", ["expense_date", "expense_head"])
    google_sheet_import_section("expenses", "Expense GST")



def service_voucher_module():
    st.header("Service Voucher")
    df = load_table("service_vouchers", 500)

    with st.form("service_voucher_form"):
        c1, c2 = st.columns(2)
        voucher_no = c1.text_input("Service Voucher No")
        voucher_date = c2.date_input("Voucher Date", value=india_now().date(), format="DD-MM-YYYY")
        customer_name = c1.text_input("Customer Name")
        mobile = c2.text_input("Mobile")
        email = c1.text_input("Email")
        service_name = c2.text_input("Service Name")
        sac_code = c1.text_input("SAC Code")
        taxable = c2.number_input("Taxable Value", value=0.0)
        cgst_rate = c1.number_input("CGST %", value=0.0, key="svc_cgst")
        sgst_rate = c2.number_input("SGST %", value=0.0, key="svc_sgst")
        igst_rate = c1.number_input("IGST %", value=0.0, key="svc_igst")
        payment_status = c2.selectbox("Payment Status", ["Pending", "Partly Received", "Received"])
        remarks = c1.text_input("Remarks")

        cgst = round(taxable * cgst_rate / 100, 2)
        sgst = round(taxable * sgst_rate / 100, 2)
        igst = round(taxable * igst_rate / 100, 2)
        total = round(taxable + cgst + sgst + igst, 2)

        st.markdown(f"""
        <div class="invoice-box">
        <h4>Service Voucher Preview</h4>
        <b>Voucher No:</b> {voucher_no}<br>
        <b>Customer:</b> {customer_name}<br>
        <b>Service:</b> {service_name}<br>
        <b>Taxable:</b> ₹ {taxable:,.2f}<br>
        <b>CGST:</b> ₹ {cgst:,.2f} | <b>SGST:</b> ₹ {sgst:,.2f} | <b>IGST:</b> ₹ {igst:,.2f}<br>
        <h3>Total: ₹ {total:,.2f}</h3>
        </div>
        """, unsafe_allow_html=True)

        if st.form_submit_button("Save Service Voucher", use_container_width=True):
            if voucher_no.strip() == "" or customer_name.strip() == "":
                st.error("Voucher No and Customer Name are required.")
            else:
                insert_row("service_vouchers", {
                    "voucher_no": voucher_no,
                    "voucher_date": str(voucher_date),
                    "customer_name": customer_name,
                    "mobile": mobile,
                    "email": email,
                    "service_name": service_name,
                    "sac_code": sac_code,
                    "taxable_value": taxable,
                    "cgst": cgst,
                    "sgst": sgst,
                    "igst": igst,
                    "total_value": total,
                    "payment_status": payment_status,
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Service voucher saved successfully.")
                st.rerun()

    show_table_with_edit_delete("service_vouchers", df, "Service Voucher Register")
    excel_upload_section("service_vouchers", "Service Voucher", ["voucher_no", "voucher_date", "customer_name"])
    google_sheet_import_section("service_vouchers", "Service Voucher")

def fixed_assets_module():
    st.header("Fixed Assets Register")
    df = load_table("fixed_assets", 500)

    with st.form("fixed_assets_form"):
        c1, c2 = st.columns(2)
        asset_code = c1.text_input("Asset Code")
        asset_name = c2.text_input("Asset Name")
        purchase_date = c1.date_input("Purchase Date", value=india_now().date(), format="DD-MM-YYYY")
        vendor_name = c2.text_input("Vendor Name")
        invoice_no = c1.text_input("Invoice No")
        asset_category = c2.text_input("Asset Category")
        location = c1.text_input("Location")
        cost = c2.number_input("Cost", value=0.0)
        gst_amount = c1.number_input("GST Amount", value=0.0)
        total_cost = round(cost + gst_amount, 2)
        useful_life_years = c2.number_input("Useful Life Years", value=5.0)
        status = c1.selectbox("Status", ["Active", "Sold", "Scrapped"])
        remarks = c2.text_input("Remarks")

        st.info(f"Total Asset Cost: ₹ {total_cost:,.2f}")

        if st.form_submit_button("Save Asset", use_container_width=True):
            if asset_name.strip() == "":
                st.error("Asset Name is required.")
            else:
                insert_row("fixed_assets", {
                    "asset_code": asset_code,
                    "asset_name": asset_name,
                    "purchase_date": str(purchase_date),
                    "vendor_name": vendor_name,
                    "invoice_no": invoice_no,
                    "asset_category": asset_category,
                    "location": location,
                    "cost": cost,
                    "gst_amount": gst_amount,
                    "total_cost": total_cost,
                    "useful_life_years": useful_life_years,
                    "status": status,
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Asset saved successfully.")
                st.rerun()

    show_table_with_edit_delete("fixed_assets", df, "Fixed Assets Records")
    excel_upload_section("fixed_assets", "Fixed Assets", ["asset_name"])
    google_sheet_import_section("fixed_assets", "Fixed Assets")


def accounting_entries_module():
    st.header("Accounting Entries Form")
    df = load_table("accounting_entries", 500)

    with st.form("accounting_entries_form"):
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Entry Date", value=india_now().date(), format="DD-MM-YYYY")
        voucher_type = c2.selectbox("Voucher Type", ["Journal", "Payment", "Receipt", "Contra", "Sales", "Purchase", "Expense"])
        voucher_no = c1.text_input("Voucher No")
        ledger_dr = c2.text_input("Ledger Dr")
        ledger_cr = c1.text_input("Ledger Cr")
        amount = c2.number_input("Amount", value=0.0)
        narration = c1.text_area("Narration")

        st.markdown(f"""
        <div class="invoice-box">
        <b>Accounting Entry Preview</b><br>
        {ledger_dr} Dr &nbsp;&nbsp; ₹ {amount:,.2f}<br>
        &nbsp;&nbsp;&nbsp;&nbsp;To {ledger_cr} &nbsp;&nbsp; ₹ {amount:,.2f}<br>
        <b>Narration:</b> {narration}
        </div>
        """, unsafe_allow_html=True)

        if st.form_submit_button("Save Accounting Entry", use_container_width=True):
            if ledger_dr.strip() == "" or ledger_cr.strip() == "":
                st.error("Ledger Dr and Ledger Cr are required.")
            else:
                insert_row("accounting_entries", {
                    "entry_date": str(entry_date),
                    "voucher_type": voucher_type,
                    "voucher_no": voucher_no,
                    "ledger_dr": ledger_dr,
                    "ledger_cr": ledger_cr,
                    "amount": amount,
                    "narration": narration,
                    "created_by": st.session_state["username"]
                })
                st.success("Accounting entry saved successfully.")
                st.rerun()

    show_table_with_edit_delete("accounting_entries", df, "Accounting Entries")
    excel_upload_section("accounting_entries", "Accounting Entries", ["entry_date", "ledger_dr", "ledger_cr"])
    google_sheet_import_section("accounting_entries", "Accounting Entries")


def export_reports():
    st.header("Excel / CSV Export Reports")

    report_options = ["employees"]
    module_map = {
        "attendance": ("attendance", "allow_attendance"),
        "attendance_visits": ("attendance_visits", "allow_attendance"),
        "inout": ("inout", "allow_inout"),
        "visitors": ("visitors", "allow_visitor"),
        "tasks": ("tasks", "allow_task"),
        "appointments": ("appointments", "allow_appointment"),
        "stock_raw_material": ("stock_raw_material", "allow_raw_material"),
        "stock_finished_goods": ("stock_finished_goods", "allow_finished_goods"),
        "stock_wip": ("stock_wip", "allow_wip"),
        "sales": ("sales", "allow_sales"),
        "purchase": ("purchase", "allow_purchase"),
        "expenses": ("expenses", "allow_expense"),
        "service_vouchers": ("service_vouchers", "allow_service_voucher"),
        "fixed_assets": ("fixed_assets", "allow_fixed_assets"),
        "accounting_entries": ("accounting_entries", "allow_accounting_entries"),
    }

    for table_key, permission_key in module_map.values():
        if st.session_state.get(permission_key, True):
            report_options.append(table_key)

    if is_super_admin():
        report_options = ["clients", "users"] + report_options

    report = st.selectbox("Select Report", report_options)
    rows = st.number_input("Rows to load", min_value=100, max_value=10000, value=1000, step=100)

    df = load_table(report, int(rows))
    search = st.text_input("Search Report")
    filtered = filter_dataframe(df, search)
    st.dataframe(filtered, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download CSV", data=filtered.to_csv(index=False).encode("utf-8"), file_name=f"{report}.csv", mime="text/csv", use_container_width=True)
    with c2:
        st.download_button("Download Excel", data=to_excel_bytes(filtered), file_name=f"{report}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def get_dynamic_menu():
    if is_super_admin():
        return [
            "Dashboard", "Client Master", "User Management", "Employee Master",
            "Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation",
            "Appointments", "Raw Material Stock", "Finished Goods Stock", "WIP Stock",
            "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher",
            "Fixed Assets", "Accounting Entries", "Excel Export Reports"
        ]

    if st.session_state["role"] == "Admin":
        menu = ["Dashboard", "User Management", "Employee Master"]
    else:
        menu = []

    ordered_modules = [
        "Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation",
        "Appointments", "Raw Material Stock", "Finished Goods Stock", "WIP Stock",
        "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher",
        "Fixed Assets", "Accounting Entries"
    ]

    for module in ordered_modules:
        if is_allowed(module):
            menu.append(module)

    menu.append("Excel Export Reports")
    return menu



def select_grouped_menu():
    available = get_dynamic_menu()

    groups = {
        "🔵 Admin": ("group-admin", ["Dashboard", "Client Master", "User Management", "Employee Master", "Appointments"]),
        "🟢 HR / Office": ("group-hr", ["Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation"]),
        "🟠 Stock": ("group-stock", ["Raw Material Stock", "Finished Goods Stock", "WIP Stock"]),
        "🟣 Accounts": ("group-accounts", ["Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Fixed Assets", "Accounting Entries"]),
        "🔴 Reports": ("group-reports", ["Excel Export Reports"]),
    }

    available_groups = []
    for group_name, (_, items) in groups.items():
        if any(item in available for item in items):
            available_groups.append(group_name)

    selected_group = st.sidebar.selectbox("Select Group", available_groups, key="selected_group_menu")
    css_class, items = groups[selected_group]
    allowed_items = [x for x in items if x in available]

    st.sidebar.markdown(f"<div class='{css_class}'>{selected_group}</div>", unsafe_allow_html=True)
    return st.sidebar.radio("Select Module", allowed_items, key=f"module_{selected_group}")


def main_app():
    rbm_header()

    st.sidebar.title("RBM AI")
    st.sidebar.write(f"Client: {st.session_state.get('client_name')}")
    st.sidebar.write(f"Client Code: {get_client_code()}")
    st.sidebar.write(f"User: {st.session_state.get('full_name')}")
    st.sidebar.write(f"Role: {st.session_state.get('role')}")
    st.sidebar.write(f"Date: {india_now().strftime('%d-%m-%Y')}")
    st.sidebar.write("Time Zone: Asia/Kolkata")

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    choice = select_grouped_menu()

    if choice == "Dashboard":
        dashboard()
    elif choice == "Client Master":
        client_master()
    elif choice == "User Management":
        user_management()
    elif choice == "Employee Master":
        employee_master()
    elif choice == "Attendance Management":
        attendance()
    elif choice == "IN / OUT Register":
        inout_register()
    elif choice == "Visitor Register":
        visitor_register()
    elif choice == "Task Delegation":
        task_delegation()
    elif choice == "Appointments":
        appointment_module()
    elif choice == "Raw Material Stock":
        stock_form("stock_raw_material", "Raw Material Stock", "raw")
    elif choice == "Finished Goods Stock":
        stock_form("stock_finished_goods", "Finished Goods Stock", "fg")
    elif choice == "WIP Stock":
        stock_form("stock_wip", "Work in Progress Stock", "wip")
    elif choice == "Sales GST Invoice":
        sales_purchase_form("sales", "Sales GST Invoice", "Customer Name")
    elif choice == "Purchase GST Invoice":
        sales_purchase_form("purchase", "Purchase GST Invoice", "Vendor Name")
    elif choice == "Expense GST":
        expense_module()
    elif choice == "Service Voucher":
        service_voucher_module()
    elif choice == "Fixed Assets":
        fixed_assets_module()
    elif choice == "Accounting Entries":
        accounting_entries_module()
    elif choice == "Excel Export Reports":
        export_reports()


# ================= RBM ERP PHASE 3 OVERRIDES =================
import streamlit.components.v1 as components

# New/updated tables and display columns
TABLES.update({
    "ledgers": "ledgers",
    "stock_vouchers": "stock_vouchers",
})

DISPLAY_COLUMNS.update({
    "ledgers": ["id", "client_code", "ledger_name", "ledger_group", "gstin", "mobile", "email", "opening_balance", "status", "created_by", "created_at"],
    "stock_vouchers": ["id", "client_code", "voucher_no", "voucher_date", "voucher_type", "stock_category", "item_code", "item_name", "uom", "qty", "rate", "value", "stock_ledger", "remarks", "created_by"],
    "accounting_entries": ["id", "client_code", "entry_date", "financial_year", "voucher_type", "voucher_no", "ledger_dr", "ledger_cr", "taxable_value", "cgst", "sgst", "igst", "amount", "narration", "created_by"],
})

MODULE_PERMISSIONS.update({
    "Ledger Master": "allow_accounting_entries",
    "Stock Voucher": "allow_stock_voucher",
})

st.markdown("""
<style>
.erp-title {
    background: linear-gradient(135deg,#0f172a,#1d4ed8);
    color: white;
    padding: 18px 22px;
    border-radius: 16px;
    margin-bottom: 18px;
    box-shadow: 0 8px 22px rgba(15,23,42,.18);
    font-size: 30px;
    font-weight: 900;
}
.erp-subtitle {font-size:15px;color:#dbeafe;margin-top:4px;font-weight:500;}
.erp-card {background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:16px;box-shadow:0 8px 20px rgba(0,0,0,.07);}
.stFormSubmitButton button {
    background: linear-gradient(135deg,#2563eb,#0f766e) !important;
    color:white !important;
    border:none !important;
    border-radius:14px !important;
    font-weight:900 !important;
    min-height:42px !important;
}
.stDownloadButton button {
    background: linear-gradient(135deg,#7c3aed,#db2777) !important;
    color:white !important;
    border:none !important;
}
.print-box {background:white;border:1px solid #cbd5e1;border-radius:14px;padding:18px;margin-top:14px;}
.print-title {font-size:24px;font-weight:900;color:#0f172a;text-align:center;border-bottom:2px solid #0f172a;padding-bottom:8px;margin-bottom:12px;}
.print-table {width:100%;border-collapse:collapse;font-size:13px;}
.print-table th {background:#e0f2fe;color:#0f172a;border:1px solid #94a3b8;padding:7px;}
.print-table td {border:1px solid #cbd5e1;padding:7px;}
.print-total {font-size:20px;font-weight:900;text-align:right;margin-top:12px;color:#1e3a8a;}
.group-admin {background:linear-gradient(135deg,#dbeafe,#bfdbfe);padding:12px;border-radius:14px;font-weight:900;color:#1e3a8a;margin-top:8px;border-left:6px solid #2563eb;}
.group-hr {background:linear-gradient(135deg,#dcfce7,#bbf7d0);padding:12px;border-radius:14px;font-weight:900;color:#14532d;margin-top:8px;border-left:6px solid #16a34a;}
.group-stock {background:linear-gradient(135deg,#ffedd5,#fed7aa);padding:12px;border-radius:14px;font-weight:900;color:#7c2d12;margin-top:8px;border-left:6px solid #f97316;}
.group-accounts {background:linear-gradient(135deg,#f3e8ff,#e9d5ff);padding:12px;border-radius:14px;font-weight:900;color:#581c87;margin-top:8px;border-left:6px solid #7c3aed;}
.group-reports {background:linear-gradient(135deg,#fee2e2,#fecaca);padding:12px;border-radius:14px;font-weight:900;color:#7f1d1d;margin-top:8px;border-left:6px solid #dc2626;}
</style>
""", unsafe_allow_html=True)


def page_header(title, subtitle=""):
    st.markdown(f"<div class='erp-title'>{title}<div class='erp-subtitle'>{subtitle}</div></div>", unsafe_allow_html=True)


def get_ledgers(group_filter=None):
    try:
        q = supabase.table("ledgers").select("*")
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        data = q.order("ledger_name").execute().data or []
        df = safe_df(data)
        if group_filter and not df.empty and "ledger_group" in df.columns:
            df = df[df["ledger_group"].astype(str).isin(group_filter)]
        names = df["ledger_name"].dropna().astype(str).tolist() if not df.empty and "ledger_name" in df.columns else []
    except Exception:
        names = []
    fallback = [
        "Cash", "Bank", "Sales Account", "Purchase Account", "Expense Account", "Service Income",
        "Input CGST", "Input SGST", "Input IGST", "Output CGST", "Output SGST", "Output IGST",
        "Customer", "Vendor", "Stock Raw Material", "Stock Finished Goods", "Stock WIP"
    ]
    final = sorted(list(dict.fromkeys([x for x in names + fallback if str(x).strip() != ""])))
    return final


def ledger_select(label, key, group_filter=None):
    options = get_ledgers(group_filter) + ["➕ Add New Ledger"]
    choice = st.selectbox(label, options, key=key)
    if choice == "➕ Add New Ledger":
        return st.text_input(f"New {label}", key=f"new_{key}")
    return choice


def ensure_ledger(name, group="General", gstin="", mobile="", email=""):
    name = str(name).strip()
    if not name or name == "➕ Add New Ledger":
        return
    try:
        existing = supabase.table("ledgers").select("id").eq("client_code", get_client_code()).eq("ledger_name", name).limit(1).execute().data or []
        if not existing:
            insert_row("ledgers", {
                "ledger_name": name,
                "ledger_group": group,
                "gstin": gstin,
                "mobile": mobile,
                "email": email,
                "opening_balance": 0,
                "status": "Active",
                "created_by": st.session_state.get("username", "")
            })
    except Exception:
        pass


def rows_editor(module_key, default_name="Item"):
    base = pd.DataFrame([
        {"item_name": default_name, "hsn_sac": "", "qty": 1.0, "rate": 0.0, "cgst_rate": 0.0, "sgst_rate": 0.0, "igst_rate": 0.0}
    ])
    rows = st.data_editor(
        base,
        num_rows="dynamic",
        use_container_width=True,
        key=f"items_editor_{module_key}",
        column_config={
            "item_name": st.column_config.TextColumn("Item / Service Name", required=True),
            "hsn_sac": st.column_config.TextColumn("HSN / SAC"),
            "qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
            "rate": st.column_config.NumberColumn("Rate", min_value=0.0, step=1.0),
            "cgst_rate": st.column_config.NumberColumn("CGST %", min_value=0.0, step=0.5),
            "sgst_rate": st.column_config.NumberColumn("SGST %", min_value=0.0, step=0.5),
            "igst_rate": st.column_config.NumberColumn("IGST %", min_value=0.0, step=0.5),
        }
    )
    rows = rows.fillna("")
    return rows


def calculate_items(rows):
    out = []
    totals = {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "total": 0.0}
    for _, r in rows.iterrows():
        item = str(r.get("item_name", "")).strip()
        if not item:
            continue
        qty = float(r.get("qty") or 0)
        rate = float(r.get("rate") or 0)
        cgst_rate = float(r.get("cgst_rate") or 0)
        sgst_rate = float(r.get("sgst_rate") or 0)
        igst_rate = float(r.get("igst_rate") or 0)
        taxable, cgst, sgst, igst, total = calc_gst(qty, rate, cgst_rate, sgst_rate, igst_rate)
        row = {
            "item_name": item,
            "hsn_sac": str(r.get("hsn_sac", "")),
            "qty": qty,
            "rate": rate,
            "taxable_value": taxable,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "total_value": total,
        }
        out.append(row)
        totals["taxable"] += taxable
        totals["cgst"] += cgst
        totals["sgst"] += sgst
        totals["igst"] += igst
        totals["total"] += total
    return out, totals


def invoice_html(title, voucher_no, voucher_date, party_label, party_name, gstin, place, items, totals, remarks=""):
    item_rows = "".join([
        f"<tr><td>{i+1}</td><td>{r['item_name']}</td><td>{r.get('hsn_sac','')}</td><td style='text-align:right'>{r['qty']:,.2f}</td><td style='text-align:right'>{r['rate']:,.2f}</td><td style='text-align:right'>{r['taxable_value']:,.2f}</td><td style='text-align:right'>{r['cgst']:,.2f}</td><td style='text-align:right'>{r['sgst']:,.2f}</td><td style='text-align:right'>{r['igst']:,.2f}</td><td style='text-align:right'>{r['total_value']:,.2f}</td></tr>"
        for i, r in enumerate(items)
    ])
    html = f"""
    <div class='print-box' id='invoice_print_area'>
      <div class='print-title'>{title}</div>
      <table style='width:100%;margin-bottom:12px;'>
        <tr><td><b>No:</b> {voucher_no}</td><td><b>Date:</b> {voucher_date}</td></tr>
        <tr><td><b>{party_label}:</b> {party_name}</td><td><b>GSTIN:</b> {gstin}</td></tr>
        <tr><td><b>Place:</b> {place}</td><td><b>Client:</b> {get_client_code()}</td></tr>
      </table>
      <table class='print-table'>
        <tr><th>#</th><th>Item</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>Taxable</th><th>CGST</th><th>SGST</th><th>IGST</th><th>Total</th></tr>
        {item_rows}
      </table>
      <div class='print-total'>Grand Total: ₹ {totals['total']:,.2f}</div>
      <p><b>Remarks:</b> {remarks}</p>
    </div>
    """
    return html


def render_print_invoice(html, file_name):
    st.markdown(html, unsafe_allow_html=True)
    components.html(f"""
    <html><body>
    <button onclick='window.print()' style='background:#2563eb;color:white;border:none;padding:10px 20px;border-radius:10px;font-weight:bold;'>Print Invoice / Voucher</button>
    <div>{html}</div>
    </body></html>
    """, height=80, scrolling=False)
    st.download_button("Download Printable HTML", data=html.encode("utf-8"), file_name=file_name, mime="text/html", use_container_width=True)


def ledger_master():
    page_header("Ledger Master", "Create ledgers for Customers, Vendors, GST, Bank, Cash and Stock accounts")
    df = load_table("ledgers", 500)
    with st.form("ledger_form"):
        c1, c2 = st.columns(2)
        ledger_name = c1.text_input("Ledger Name")
        ledger_group = c2.selectbox("Ledger Group", ["Customer", "Vendor", "Sales", "Purchase", "Expense", "Service", "GST", "Bank", "Cash", "Stock", "Asset", "General"])
        gstin = c1.text_input("GSTIN")
        mobile = c2.text_input("Mobile")
        email = c1.text_input("Email")
        opening_balance = c2.number_input("Opening Balance", value=0.0)
        status = c1.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Ledger", use_container_width=True):
            if ledger_name.strip() == "":
                st.error("Ledger Name is required.")
            else:
                insert_row("ledgers", {"ledger_name": ledger_name, "ledger_group": ledger_group, "gstin": gstin, "mobile": mobile, "email": email, "opening_balance": opening_balance, "status": status, "created_by": st.session_state.get("username", "")})
                st.success("Ledger saved successfully.")
                st.rerun()
    show_table_with_edit_delete("ledgers", df, "Ledger Register")
    excel_upload_section("ledgers", "Ledgers", ["ledger_name"])


def sales_purchase_form(module_key, title, party_label):
    page_header(title, "Multiple items, GST calculation, ledger dropdown and printable invoice")
    df = load_table(module_key, 500)
    is_sales = module_key == "sales"
    party_col = "customer_name" if is_sales else "vendor_name"
    ledger_group = ["Customer"] if is_sales else ["Vendor"]

    c1, c2 = st.columns(2)
    invoice_no = c1.text_input("Invoice / Voucher No", key=f"{module_key}_no")
    invoice_date = c2.date_input("Invoice Date", value=india_now().date(), format="DD-MM-YYYY", key=f"{module_key}_date")
    party_name = ledger_select(party_label, f"{module_key}_party", ledger_group)
    gstin = c2.text_input("GSTIN", key=f"{module_key}_gstin")
    place_of_supply = c1.text_input("Place of Supply", key=f"{module_key}_place")
    remarks = c2.text_input("Remarks", key=f"{module_key}_remarks")

    st.subheader("Invoice Items")
    rows = rows_editor(module_key, "Item")
    items, totals = calculate_items(rows)

    st.info(f"Taxable: ₹ {totals['taxable']:,.2f} | CGST: ₹ {totals['cgst']:,.2f} | SGST: ₹ {totals['sgst']:,.2f} | IGST: ₹ {totals['igst']:,.2f} | Total: ₹ {totals['total']:,.2f}")
    html = invoice_html(title, invoice_no, invoice_date, party_label, party_name, gstin, place_of_supply, items, totals, remarks)
    render_print_invoice(html, f"{module_key}_{invoice_no or 'invoice'}.html")

    if st.button("Save Invoice / Voucher", use_container_width=True, key=f"save_{module_key}_voucher"):
        if invoice_no.strip() == "" or str(party_name).strip() == "":
            st.error("Invoice No and Party Name are required.")
        elif not items:
            st.error("At least one item is required.")
        else:
            ensure_ledger(party_name, "Customer" if is_sales else "Vendor", gstin=gstin)
            for item in items:
                row = {
                    "invoice_no": invoice_no,
                    "invoice_date": str(invoice_date),
                    party_col: party_name,
                    "gstin": gstin,
                    "place_of_supply": place_of_supply,
                    "item_name": item["item_name"],
                    "hsn_sac": item.get("hsn_sac", ""),
                    "qty": item["qty"],
                    "rate": item["rate"],
                    "taxable_value": item["taxable_value"],
                    "cgst": item["cgst"],
                    "sgst": item["sgst"],
                    "igst": item["igst"],
                    "total_value": item["total_value"],
                    "remarks": remarks,
                    "created_by": st.session_state.get("username", "")
                }
                insert_row(module_key, row)
            auto_entry_from_voucher("Sales" if is_sales else "Purchase", invoice_no, invoice_date, party_name, totals)
            st.success("Invoice saved successfully with multiple items.")
            st.rerun()

    st.divider()
    show_table_with_edit_delete(module_key, df, title + " Register")
    excel_upload_section(module_key, title, ["invoice_no", "invoice_date"])
    google_sheet_import_section(module_key, title)


def auto_entry_from_voucher(voucher_type, voucher_no, voucher_date, party_name, totals):
    try:
        if voucher_type == "Sales":
            dr = party_name
            cr = "Sales Account"
        elif voucher_type == "Purchase":
            dr = "Purchase Account"
            cr = party_name
        elif voucher_type == "Expense":
            dr = "Expense Account"
            cr = party_name
        elif voucher_type == "Service":
            dr = party_name
            cr = "Service Income"
        else:
            return
        insert_row("accounting_entries", {
            "entry_date": str(voucher_date),
            "voucher_type": voucher_type,
            "voucher_no": voucher_no,
            "ledger_dr": dr,
            "ledger_cr": cr,
            "taxable_value": totals.get("taxable", 0),
            "cgst": totals.get("cgst", 0),
            "sgst": totals.get("sgst", 0),
            "igst": totals.get("igst", 0),
            "amount": totals.get("total", 0),
            "narration": f"Auto entry for {voucher_type} voucher {voucher_no}",
            "created_by": st.session_state.get("username", "")
        })
    except Exception:
        pass


def expense_module():
    page_header("Expense GST Voucher", "GST enabled expense voucher with ledger dropdown and register")
    df = load_table("expenses", 500)
    with st.form("expense_form_v3"):
        c1, c2 = st.columns(2)
        expense_date = c1.date_input("Expense Date", value=india_now().date(), format="DD-MM-YYYY")
        invoice_no = c2.text_input("Voucher / Invoice No")
        expense_head = ledger_select("Expense Ledger", "expense_head_ledger", ["Expense"])
        vendor_name = ledger_select("Vendor / Paid To Ledger", "expense_vendor_ledger", ["Vendor", "Cash", "Bank"])
        gstin = c1.text_input("GSTIN")
        taxable = c2.number_input("Taxable Value", value=0.0)
        cgst_rate = c1.number_input("CGST %", value=0.0)
        sgst_rate = c2.number_input("SGST %", value=0.0)
        igst_rate = c1.number_input("IGST %", value=0.0)
        payment_mode = c2.selectbox("Payment Mode", ["Cash", "Bank", "Credit", "UPI", "Cheque"])
        remarks = c1.text_input("Remarks")
        taxable_value, cgst, sgst, igst, total = calc_gst(1, taxable, cgst_rate, sgst_rate, igst_rate)
        st.info(f"Total Expense Voucher: ₹ {total:,.2f}")
        if st.form_submit_button("Save Expense Voucher", use_container_width=True):
            if str(expense_head).strip() == "" or str(vendor_name).strip() == "":
                st.error("Expense Ledger and Vendor Ledger are required.")
            else:
                ensure_ledger(expense_head, "Expense")
                ensure_ledger(vendor_name, "Vendor", gstin=gstin)
                insert_row("expenses", {"expense_date": str(expense_date), "expense_head": expense_head, "vendor_name": vendor_name, "gstin": gstin, "invoice_no": invoice_no, "taxable_value": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "total_value": total, "payment_mode": payment_mode, "remarks": remarks, "created_by": st.session_state.get("username", "")})
                auto_entry_from_voucher("Expense", invoice_no, expense_date, vendor_name, {"taxable": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "total": total})
                st.success("Expense voucher saved successfully.")
                st.rerun()
    show_table_with_edit_delete("expenses", df, "Expense Register")
    excel_upload_section("expenses", "Expense Register", ["expense_date", "expense_head"])
    google_sheet_import_section("expenses", "Expense Register")


def service_voucher_module():
    page_header("Service Voucher", "Separate service voucher and service register with GST and print option")
    df = load_table("service_vouchers", 500)
    c1, c2 = st.columns(2)
    voucher_no = c1.text_input("Service Voucher No", key="service_no")
    voucher_date = c2.date_input("Voucher Date", value=india_now().date(), format="DD-MM-YYYY", key="service_date")
    customer_name = ledger_select("Customer Ledger", "service_customer", ["Customer"])
    mobile = c2.text_input("Mobile", key="service_mobile")
    email = c1.text_input("Email", key="service_email")
    service_name = c2.text_input("Service Name", key="service_name")
    sac_code = c1.text_input("SAC Code", key="service_sac")
    taxable = c2.number_input("Taxable Value", value=0.0, key="service_taxable")
    cgst_rate = c1.number_input("CGST %", value=0.0, key="service_cgst")
    sgst_rate = c2.number_input("SGST %", value=0.0, key="service_sgst")
    igst_rate = c1.number_input("IGST %", value=0.0, key="service_igst")
    payment_status = c2.selectbox("Payment Status", ["Pending", "Received", "Partly Received"], key="service_payment")
    remarks = c1.text_input("Remarks", key="service_remarks")
    taxable_value, cgst, sgst, igst, total = calc_gst(1, taxable, cgst_rate, sgst_rate, igst_rate)
    items = [{"item_name": service_name, "hsn_sac": sac_code, "qty": 1, "rate": taxable, "taxable_value": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "total_value": total}]
    html = invoice_html("Service Voucher", voucher_no, voucher_date, "Customer", customer_name, "", "", items, {"taxable": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "total": total}, remarks)
    render_print_invoice(html, f"service_{voucher_no or 'voucher'}.html")
    if st.button("Save Service Voucher", use_container_width=True, key="save_service_voucher_v3"):
        if voucher_no.strip() == "" or str(customer_name).strip() == "":
            st.error("Voucher No and Customer are required.")
        else:
            ensure_ledger(customer_name, "Customer", mobile=mobile, email=email)
            insert_row("service_vouchers", {"voucher_no": voucher_no, "voucher_date": str(voucher_date), "customer_name": customer_name, "mobile": mobile, "email": email, "service_name": service_name, "sac_code": sac_code, "taxable_value": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "total_value": total, "payment_status": payment_status, "remarks": remarks, "created_by": st.session_state.get("username", "")})
            auto_entry_from_voucher("Service", voucher_no, voucher_date, customer_name, {"taxable": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "total": total})
            st.success("Service voucher saved successfully.")
            st.rerun()
    show_table_with_edit_delete("service_vouchers", df, "Service Register")
    excel_upload_section("service_vouchers", "Service Register", ["voucher_no", "voucher_date"])
    google_sheet_import_section("service_vouchers", "Service Register")


def accounting_entries_module():
    page_header("Accounting Entries Form", "Ledger dropdowns with GST fields and voucher preview")
    df = load_table("accounting_entries", 500)
    with st.form("accounting_entries_form_v3"):
        c1, c2 = st.columns(2)
        entry_date = c1.date_input("Entry Date", value=india_now().date(), format="DD-MM-YYYY")
        voucher_type = c2.selectbox("Voucher Type", ["Journal", "Payment", "Receipt", "Contra", "Sales", "Purchase", "Expense", "Service", "Stock"])
        voucher_no = c1.text_input("Voucher No")
        ledger_dr = ledger_select("Ledger Dr", "entry_ledger_dr")
        ledger_cr = ledger_select("Ledger Cr", "entry_ledger_cr")
        taxable_value = c1.number_input("Taxable Value", value=0.0)
        cgst = c2.number_input("CGST", value=0.0)
        sgst = c1.number_input("SGST", value=0.0)
        igst = c2.number_input("IGST", value=0.0)
        amount = taxable_value + cgst + sgst + igst
        narration = c1.text_area("Narration")
        st.markdown(f"""
        <div class="print-box">
        <b>Accounting Entry Preview</b><br>
        {ledger_dr} Dr &nbsp;&nbsp; ₹ {amount:,.2f}<br>
        &nbsp;&nbsp;&nbsp;&nbsp;To {ledger_cr} &nbsp;&nbsp; ₹ {amount:,.2f}<br>
        Taxable: ₹ {taxable_value:,.2f} | CGST: ₹ {cgst:,.2f} | SGST: ₹ {sgst:,.2f} | IGST: ₹ {igst:,.2f}<br>
        <b>Narration:</b> {narration}
        </div>
        """, unsafe_allow_html=True)
        if st.form_submit_button("Save Accounting Entry", use_container_width=True):
            if str(ledger_dr).strip() == "" or str(ledger_cr).strip() == "":
                st.error("Ledger Dr and Ledger Cr are required.")
            else:
                ensure_ledger(ledger_dr)
                ensure_ledger(ledger_cr)
                insert_row("accounting_entries", {"entry_date": str(entry_date), "voucher_type": voucher_type, "voucher_no": voucher_no, "ledger_dr": ledger_dr, "ledger_cr": ledger_cr, "taxable_value": taxable_value, "cgst": cgst, "sgst": sgst, "igst": igst, "amount": amount, "narration": narration, "created_by": st.session_state.get("username", "")})
                st.success("Accounting entry saved successfully.")
                st.rerun()
    show_table_with_edit_delete("accounting_entries", df, "Accounting Entries")
    excel_upload_section("accounting_entries", "Accounting Entries", ["entry_date", "ledger_dr", "ledger_cr"])
    google_sheet_import_section("accounting_entries", "Accounting Entries")


def stock_voucher_module():
    page_header("Stock Voucher Entries", "Separate stock inward / outward / production / transfer voucher register")
    df = load_table("stock_vouchers", 500)
    with st.form("stock_voucher_form"):
        c1, c2 = st.columns(2)
        voucher_no = c1.text_input("Stock Voucher No")
        voucher_date = c2.date_input("Voucher Date", value=india_now().date(), format="DD-MM-YYYY")
        voucher_type = c1.selectbox("Voucher Type", ["Raw Material Inward", "Raw Material Issue", "Finished Goods Production", "Finished Goods Sales Issue", "WIP Input", "WIP Output", "Stock Transfer", "Adjustment"])
        stock_category = c2.selectbox("Stock Category", ["Raw Material", "Finished Goods", "WIP"])
        item_code = c1.text_input("Item Code")
        item_name = c2.text_input("Item Name")
        uom = c1.text_input("UOM", value="PCS")
        qty = c2.number_input("Qty", value=0.0)
        rate = c1.number_input("Rate", value=0.0)
        value = round(qty * rate, 2)
        stock_ledger = ledger_select("Stock Ledger", "stock_voucher_ledger", ["Stock"])
        remarks = c2.text_input("Remarks")
        st.info(f"Stock Voucher Value: ₹ {value:,.2f}")
        if st.form_submit_button("Save Stock Voucher", use_container_width=True):
            if voucher_no.strip() == "" or item_name.strip() == "":
                st.error("Voucher No and Item Name are required.")
            else:
                ensure_ledger(stock_ledger, "Stock")
                insert_row("stock_vouchers", {"voucher_no": voucher_no, "voucher_date": str(voucher_date), "voucher_type": voucher_type, "stock_category": stock_category, "item_code": item_code, "item_name": item_name, "uom": uom, "qty": qty, "rate": rate, "value": value, "stock_ledger": stock_ledger, "remarks": remarks, "created_by": st.session_state.get("username", "")})
                st.success("Stock voucher saved successfully.")
                st.rerun()
    show_table_with_edit_delete("stock_vouchers", df, "Stock Voucher Register")
    excel_upload_section("stock_vouchers", "Stock Voucher Register", ["voucher_no", "voucher_date", "item_name"])
    google_sheet_import_section("stock_vouchers", "Stock Voucher Register")


def show_register_report(title, df):
    page_header(title, "Register view with search and Excel / CSV download")
    search = st.text_input(f"Search {title}", key=f"search_register_{title}")
    filtered = filter_dataframe(df, search)
    st.dataframe(filtered, use_container_width=True)
    c1, c2 = st.columns(2)
    c1.download_button("Download Register CSV", data=filtered.to_csv(index=False).encode("utf-8"), file_name=f"{title.replace(' ','_').lower()}.csv", mime="text/csv", use_container_width=True)
    c2.download_button("Download Register Excel", data=to_excel_bytes(filtered), file_name=f"{title.replace(' ','_').lower()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


def build_gst_register():
    frames = []
    mapping = [("Sales", "sales", "invoice_date"), ("Purchase", "purchase", "invoice_date"), ("Expense", "expenses", "expense_date"), ("Service", "service_vouchers", "voucher_date")]
    for source, key, date_col in mapping:
        try:
            df = load_table(key, 5000)
            if not df.empty:
                df = df.copy()
                df["source"] = source
                df["voucher_date"] = df[date_col] if date_col in df.columns else ""
                keep = [c for c in ["source", "client_code", "voucher_date", "invoice_no", "voucher_no", "customer_name", "vendor_name", "expense_head", "service_name", "gstin", "taxable_value", "cgst", "sgst", "igst", "total_value"] if c in df.columns]
                frames.append(df[keep])
        except Exception:
            pass
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_stock_register():
    frames = []
    for source, key in [("Raw Material", "stock_raw_material"), ("Finished Goods", "stock_finished_goods"), ("WIP", "stock_wip"), ("Stock Voucher", "stock_vouchers")]:
        try:
            df = load_table(key, 5000)
            if not df.empty:
                df = df.copy()
                df["source"] = source
                frames.append(df)
        except Exception:
            pass
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def export_reports():
    page_header("Reports & Registers", "Sales, Purchase, Stock, Expense, GST and all master registers")
    report_labels = ["Sales Register", "Purchase Register", "Stock Register", "Expense Register", "Service Register", "GST Register", "Ledger Register", "Accounting Register", "Fixed Assets Register", "All Table Export"]
    report = st.selectbox("Select Register", report_labels)
    rows = st.number_input("Rows to load", min_value=100, max_value=20000, value=5000, step=100)
    if report == "Sales Register":
        df = load_table("sales", int(rows))
    elif report == "Purchase Register":
        df = load_table("purchase", int(rows))
    elif report == "Stock Register":
        df = build_stock_register()
    elif report == "Expense Register":
        df = load_table("expenses", int(rows))
    elif report == "Service Register":
        df = load_table("service_vouchers", int(rows))
    elif report == "GST Register":
        df = build_gst_register()
    elif report == "Ledger Register":
        df = load_table("ledgers", int(rows))
    elif report == "Accounting Register":
        df = load_table("accounting_entries", int(rows))
    elif report == "Fixed Assets Register":
        df = load_table("fixed_assets", int(rows))
    else:
        options = list(DISPLAY_COLUMNS.keys())
        table_key = st.selectbox("Select Table", options)
        df = load_table(table_key, int(rows))
    show_register_report(report, df)


def client_master():
    page_header("Client Master", "Control module access client-wise")
    if not is_super_admin():
        st.warning("Only Super Admin can access Client Master.")
        return
    with st.form("client_form_v3"):
        c1, c2 = st.columns(2)
        client_code = c1.text_input("Client Code", placeholder="Example: CHOICE")
        client_name = c2.text_input("Client Name", placeholder="Example: Choice Group")
        status = c1.selectbox("Status", ["Active", "Inactive"])
        st.subheader("Office Module Access")
        o1, o2, o3, o4, o5 = st.columns(5)
        allow_task = o1.checkbox("Task", value=True)
        allow_attendance = o2.checkbox("Attendance", value=True)
        allow_inout = o3.checkbox("IN / OUT", value=True)
        allow_visitor = o4.checkbox("Visitor", value=True)
        allow_appointment = o5.checkbox("Appointment", value=True)
        st.subheader("Inventory / Accounting Module Access")
        e1, e2, e3, e4, e5 = st.columns(5)
        allow_raw_material = e1.checkbox("Raw Material", value=True)
        allow_finished_goods = e2.checkbox("Finished Goods", value=True)
        allow_wip = e3.checkbox("WIP", value=True)
        allow_stock_voucher = e4.checkbox("Stock Voucher", value=True)
        allow_sales = e5.checkbox("Sales", value=True)
        e6, e7, e8, e9, e10 = st.columns(5)
        allow_purchase = e6.checkbox("Purchase", value=True)
        allow_expense = e7.checkbox("Expense", value=True)
        allow_service_voucher = e8.checkbox("Service Voucher", value=True)
        allow_fixed_assets = e9.checkbox("Fixed Assets", value=True)
        allow_accounting_entries = e10.checkbox("Accounting / Ledger", value=True)
        e11, e12 = st.columns(2)
        allow_excel_upload = e11.checkbox("Excel Upload", value=True)
        allow_google_sheet_import = e12.checkbox("Google Sheet Import", value=True)
        if st.form_submit_button("Save Client", use_container_width=True):
            if client_code.strip() == "" or client_name.strip() == "":
                st.error("Client Code and Client Name are required.")
            else:
                insert_row("clients", {
                    "client_code": client_code.strip().upper(), "client_name": client_name.strip(),
                    "allow_task": allow_task, "allow_attendance": allow_attendance, "allow_inout": allow_inout, "allow_visitor": allow_visitor,
                    "allow_appointment": allow_appointment, "allow_raw_material": allow_raw_material, "allow_finished_goods": allow_finished_goods, "allow_wip": allow_wip,
                    "allow_stock_voucher": allow_stock_voucher, "allow_sales": allow_sales, "allow_purchase": allow_purchase, "allow_expense": allow_expense,
                    "allow_service_voucher": allow_service_voucher, "allow_fixed_assets": allow_fixed_assets, "allow_accounting_entries": allow_accounting_entries,
                    "allow_excel_upload": allow_excel_upload, "allow_google_sheet_import": allow_google_sheet_import, "status": status
                })
                st.success("Client saved successfully.")
                st.rerun()
    df = load_table("clients", 500)
    show_table_with_edit_delete("clients", df, "Client List")


def get_dynamic_menu():
    if is_super_admin():
        return ["Dashboard", "Client Master", "User Management", "Employee Master", "Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation", "Appointments", "Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher", "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Ledger Master", "Fixed Assets", "Accounting Entries", "Excel Export Reports"]
    if st.session_state["role"] == "Admin":
        menu = ["Dashboard", "User Management", "Employee Master"]
    else:
        menu = []
    ordered_modules = ["Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation", "Appointments", "Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher", "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Ledger Master", "Fixed Assets", "Accounting Entries"]
    for module in ordered_modules:
        if is_allowed(module):
            menu.append(module)
    menu.append("Excel Export Reports")
    return menu


def select_grouped_menu():
    available = get_dynamic_menu()
    groups = {
        "🔵 Admin": ("group-admin", ["Dashboard", "Client Master", "User Management", "Employee Master", "Appointments"]),
        "🟢 HR / Office": ("group-hr", ["Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation"]),
        "🟠 Stock": ("group-stock", ["Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher"]),
        "🟣 Accounts": ("group-accounts", ["Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Ledger Master", "Fixed Assets", "Accounting Entries"]),
        "🔴 Reports": ("group-reports", ["Excel Export Reports"]),
    }
    available_groups = [g for g, (_, items) in groups.items() if any(item in available for item in items)]
    selected_group = st.sidebar.selectbox("Select Group", available_groups, key="selected_group_menu")
    css_class, items = groups[selected_group]
    allowed_items = [x for x in items if x in available]
    st.sidebar.markdown(f"<div class='{css_class}'>{selected_group}</div>", unsafe_allow_html=True)
    return st.sidebar.radio("Select Module", allowed_items, key=f"module_{selected_group}")


def main_app():
    rbm_header()
    st.sidebar.title("RBM AI")
    st.sidebar.write(f"Client: {st.session_state.get('client_name')}")
    st.sidebar.write(f"Client Code: {get_client_code()}")
    st.sidebar.write(f"User: {st.session_state.get('full_name')}")
    st.sidebar.write(f"Role: {st.session_state.get('role')}")
    st.sidebar.write(f"Date: {india_now().strftime('%d-%m-%Y')}")
    st.sidebar.write("Time Zone: Asia/Kolkata")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear(); st.rerun()
    choice = select_grouped_menu()
    if choice == "Dashboard": dashboard()
    elif choice == "Client Master": client_master()
    elif choice == "User Management": user_management()
    elif choice == "Employee Master": employee_master()
    elif choice == "Attendance Management": attendance()
    elif choice == "IN / OUT Register": inout_register()
    elif choice == "Visitor Register": visitor_register()
    elif choice == "Task Delegation": task_delegation()
    elif choice == "Appointments": appointment_module()
    elif choice == "Raw Material Stock": stock_form("stock_raw_material", "Raw Material Stock", "raw")
    elif choice == "Finished Goods Stock": stock_form("stock_finished_goods", "Finished Goods Stock", "fg")
    elif choice == "WIP Stock": stock_form("stock_wip", "Work in Progress Stock", "wip")
    elif choice == "Stock Voucher": stock_voucher_module()
    elif choice == "Sales GST Invoice": sales_purchase_form("sales", "Sales GST Invoice", "Customer Name")
    elif choice == "Purchase GST Invoice": sales_purchase_form("purchase", "Purchase GST Invoice", "Vendor Name")
    elif choice == "Expense GST": expense_module()
    elif choice == "Service Voucher": service_voucher_module()
    elif choice == "Ledger Master": ledger_master()
    elif choice == "Fixed Assets": fixed_assets_module()
    elif choice == "Accounting Entries": accounting_entries_module()
    elif choice == "Excel Export Reports": export_reports()
# ================= END RBM ERP PHASE 3 OVERRIDES =================



# ================= RBM ERP PHASE 4 MASTER GROUP OVERRIDES =================

TABLES.update({
    "ledger_groups": "ledger_groups",
    "stock_groups": "stock_groups",
    "stock_ledgers": "stock_ledgers",
})

DISPLAY_COLUMNS.update({
    "ledger_groups": ["id", "client_code", "group_name", "group_type", "status", "created_by", "created_at"],
    "ledgers": ["id", "client_code", "ledger_name", "ledger_group", "address", "contact_no", "tan_no", "gst_no", "pan_no", "opening_balance", "balance_type", "status", "created_by", "created_at"],
    "stock_groups": ["id", "client_code", "stock_group_name", "stock_type", "status", "created_by", "created_at"],
    "stock_ledgers": ["id", "client_code", "item_name", "item_code", "stock_group", "unit", "hsn_code", "opening_qty", "opening_rate", "opening_value", "gst_rate", "status", "created_by", "created_at"],
})

MODULE_PERMISSIONS.update({
    "Ledger Group Master": "allow_master_group",
    "Ledger Master": "allow_master_group",
    "Stock Group Master": "allow_master_group",
    "Stock Ledger Master": "allow_master_group",
})

DEFAULT_LEDGER_GROUPS = [
    "Sundry Debtors", "Sundry Creditors", "Sales Accounts", "Purchase Accounts",
    "Direct Expenses", "Indirect Expenses", "Bank Accounts", "Cash-in-Hand",
    "Duties & Taxes", "Fixed Assets", "Loans & Advances", "Capital Account",
    "Service Income", "Current Assets", "Current Liabilities", "Suspense Account"
]

DEFAULT_STOCK_GROUPS = [
    "Raw Material", "Finished Goods", "Work in Progress", "Packing Material",
    "Consumables", "Stores & Spares", "Trading Goods", "Service Items"
]

st.markdown("""
<style>
.master-box {background:linear-gradient(135deg,#fef3c7,#fde68a);border-left:7px solid #f59e0b;padding:16px;border-radius:16px;margin-bottom:16px;box-shadow:0 7px 18px rgba(0,0,0,.07);} 
.master-title {font-size:26px;font-weight:900;color:#78350f;} 
.master-note {font-size:14px;color:#92400e;font-weight:600;} 
.group-master {background:linear-gradient(135deg,#fef3c7,#fde68a);padding:12px;border-radius:14px;font-weight:900;color:#78350f;margin-top:8px;border-left:6px solid #f59e0b;}
</style>
""", unsafe_allow_html=True)


def master_header(title, note="Create and maintain ERP master data"):
    st.markdown(f"<div class='master-box'><div class='master-title'>🧾 {title}</div><div class='master-note'>{note}</div></div>", unsafe_allow_html=True)


def get_ledger_group_options():
    try:
        q = supabase.table("ledger_groups").select("group_name")
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        data = q.execute().data or []
        names = [str(x.get("group_name", "")).strip() for x in data if str(x.get("group_name", "")).strip()]
    except Exception:
        names = []
    return sorted(list(dict.fromkeys(DEFAULT_LEDGER_GROUPS + names)))


def get_stock_group_options():
    try:
        q = supabase.table("stock_groups").select("stock_group_name")
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        data = q.execute().data or []
        names = [str(x.get("stock_group_name", "")).strip() for x in data if str(x.get("stock_group_name", "")).strip()]
    except Exception:
        names = []
    return sorted(list(dict.fromkeys(DEFAULT_STOCK_GROUPS + names)))


def get_stock_items(group_filter=None):
    try:
        q = supabase.table("stock_ledgers").select("*")
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        data = q.order("item_name").execute().data or []
        df = safe_df(data)
        if group_filter and not df.empty and "stock_group" in df.columns:
            df = df[df["stock_group"].astype(str).isin(group_filter)]
        names = df["item_name"].dropna().astype(str).tolist() if not df.empty and "item_name" in df.columns else []
    except Exception:
        names = []
    fallback = ["Raw Material Item", "Finished Goods Item", "WIP Item", "Service Item"]
    return sorted(list(dict.fromkeys([x for x in names + fallback if str(x).strip()])))


def get_ledgers(group_filter=None):
    try:
        q = supabase.table("ledgers").select("*")
        if not is_super_admin():
            q = q.eq("client_code", get_client_code())
        data = q.order("ledger_name").execute().data or []
        df = safe_df(data)
        if group_filter and not df.empty and "ledger_group" in df.columns:
            df = df[df["ledger_group"].astype(str).isin(group_filter)]
        names = df["ledger_name"].dropna().astype(str).tolist() if not df.empty and "ledger_name" in df.columns else []
    except Exception:
        names = []
    fallback = [
        "Cash", "Bank", "Sales Account", "Purchase Account", "Expense Account", "Service Income",
        "Input CGST", "Input SGST", "Input IGST", "Output CGST", "Output SGST", "Output IGST",
        "Customer", "Vendor", "Fixed Assets", "Depreciation", "Capital Account"
    ]
    return sorted(list(dict.fromkeys([x for x in names + fallback if str(x).strip()])))


def ensure_ledger(name, group="General", gstin="", mobile="", email=""):
    name = str(name).strip()
    if not name or name == "➕ Add New Ledger":
        return
    try:
        existing = supabase.table("ledgers").select("id").eq("client_code", get_client_code()).eq("ledger_name", name).limit(1).execute().data or []
        if not existing:
            insert_row("ledgers", {
                "ledger_name": name,
                "ledger_group": group,
                "address": "",
                "contact_no": mobile,
                "tan_no": "",
                "gst_no": gstin,
                "pan_no": "",
                "opening_balance": 0,
                "balance_type": "Dr",
                "status": "Active",
                "created_by": st.session_state.get("username", "")
            })
    except Exception:
        pass


def ledger_group_master():
    master_header("Ledger Group Master", "Create accounting ledger groups used in Ledger Master and voucher dropdowns")
    df = load_table("ledger_groups", 500)
    with st.form("ledger_group_form_v4"):
        c1, c2, c3 = st.columns(3)
        group_name = c1.text_input("Ledger Group Name", placeholder="Example: Sundry Debtors")
        group_type = c2.selectbox("Group Type", ["Asset", "Liability", "Income", "Expense", "GST / Tax", "Bank / Cash", "Other"])
        status = c3.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Ledger Group", use_container_width=True):
            if group_name.strip() == "":
                st.error("Ledger Group Name is required.")
            else:
                insert_row("ledger_groups", {
                    "group_name": group_name.strip(),
                    "group_type": group_type,
                    "status": status,
                    "created_by": st.session_state.get("username", "")
                })
                st.success("Ledger Group saved successfully.")
                st.rerun()
    show_table_with_edit_delete("ledger_groups", df, "Ledger Group List")


def ledger_master():
    master_header("Ledger Master", "Create customer, vendor, bank, GST, expense and income ledgers")
    df = load_table("ledgers", 500)
    group_options = get_ledger_group_options()
    with st.form("ledger_master_form_v4"):
        c1, c2 = st.columns(2)
        ledger_name = c1.text_input("Ledger Name")
        ledger_group = c2.selectbox("Ledger Group", group_options)
        address = c1.text_area("Address")
        contact_no = c2.text_input("Contact No")
        tan_no = c1.text_input("TAN No")
        gst_no = c2.text_input("GST No")
        pan_no = c1.text_input("PAN No")
        opening_balance = c2.number_input("Opening Balance", value=0.0, step=100.0)
        balance_type = c1.selectbox("Balance Type", ["Dr", "Cr"])
        status = c2.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Ledger", use_container_width=True):
            if ledger_name.strip() == "":
                st.error("Ledger Name is required.")
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
                    "status": status,
                    "created_by": st.session_state.get("username", "")
                })
                st.success("Ledger saved successfully.")
                st.rerun()
    show_table_with_edit_delete("ledgers", df, "Ledger List")


def stock_group_master():
    master_header("Stock Group Master", "Create stock groups for Raw Material, Finished Goods, WIP and other items")
    df = load_table("stock_groups", 500)
    with st.form("stock_group_form_v4"):
        c1, c2, c3 = st.columns(3)
        stock_group_name = c1.text_input("Stock Group Name", placeholder="Example: Raw Material")
        stock_type = c2.selectbox("Stock Type", ["Raw Material", "Finished Goods", "Work in Progress", "Packing Material", "Consumables", "Stores & Spares", "Trading Goods", "Service Items", "Other"])
        status = c3.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Stock Group", use_container_width=True):
            if stock_group_name.strip() == "":
                st.error("Stock Group Name is required.")
            else:
                insert_row("stock_groups", {
                    "stock_group_name": stock_group_name.strip(),
                    "stock_type": stock_type,
                    "status": status,
                    "created_by": st.session_state.get("username", "")
                })
                st.success("Stock Group saved successfully.")
                st.rerun()
    show_table_with_edit_delete("stock_groups", df, "Stock Group List")


def stock_ledger_master():
    master_header("Stock Ledger / Item Master", "Create stock items with HSN, unit, GST rate and opening quantity")
    df = load_table("stock_ledgers", 500)
    stock_group_options = get_stock_group_options()
    with st.form("stock_ledger_form_v4"):
        c1, c2 = st.columns(2)
        item_name = c1.text_input("Item / Stock Ledger Name")
        item_code = c2.text_input("Item Code")
        stock_group = c1.selectbox("Stock Group", stock_group_options)
        unit = c2.selectbox("Unit", ["Nos", "Kg", "Meter", "Ltr", "Box", "Pcs", "Set", "Bag", "Roll", "Other"])
        hsn_code = c1.text_input("HSN Code")
        gst_rate = c2.number_input("GST Rate %", value=0.0, step=0.5)
        opening_qty = c1.number_input("Opening Qty", value=0.0, step=1.0)
        opening_rate = c2.number_input("Opening Rate", value=0.0, step=1.0)
        opening_value = opening_qty * opening_rate
        c1.metric("Opening Value", f"{opening_value:,.2f}")
        status = c2.selectbox("Status", ["Active", "Inactive"])
        if st.form_submit_button("Save Stock Ledger", use_container_width=True):
            if item_name.strip() == "":
                st.error("Item / Stock Ledger Name is required.")
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
                    "status": status,
                    "created_by": st.session_state.get("username", "")
                })
                st.success("Stock Ledger saved successfully.")
                st.rerun()
    show_table_with_edit_delete("stock_ledgers", df, "Stock Ledger List")


def rows_editor(module_key, default_name="Item"):
    stock_options = get_stock_items()
    first_item = stock_options[0] if stock_options else default_name
    base = pd.DataFrame([
        {"item_name": first_item, "hsn_sac": "", "qty": 1.0, "rate": 0.0, "cgst_rate": 0.0, "sgst_rate": 0.0, "igst_rate": 0.0}
    ])
    rows = st.data_editor(
        base,
        num_rows="dynamic",
        use_container_width=True,
        key=f"items_editor_{module_key}_v4",
        column_config={
            "item_name": st.column_config.SelectboxColumn("Item / Service Name", options=stock_options + ["Manual Item"], required=True),
            "hsn_sac": st.column_config.TextColumn("HSN / SAC"),
            "qty": st.column_config.NumberColumn("Qty", min_value=0.0, step=1.0),
            "rate": st.column_config.NumberColumn("Rate", min_value=0.0, step=1.0),
            "cgst_rate": st.column_config.NumberColumn("CGST %", min_value=0.0, step=0.5),
            "sgst_rate": st.column_config.NumberColumn("SGST %", min_value=0.0, step=0.5),
            "igst_rate": st.column_config.NumberColumn("IGST %", min_value=0.0, step=0.5),
        }
    )
    rows = rows.fillna("")
    return rows


def client_master():
    page_header("Client Master", "Control module access client-wise")
    if not is_super_admin():
        st.warning("Only Super Admin can access Client Master.")
        return
    with st.form("client_form_v4"):
        c1, c2 = st.columns(2)
        client_code = c1.text_input("Client Code", placeholder="Example: CHOICE")
        client_name = c2.text_input("Client Name", placeholder="Example: Choice Group")
        status = c1.selectbox("Status", ["Active", "Inactive"])
        st.subheader("Master / Office Module Access")
        a1, a2, a3, a4, a5 = st.columns(5)
        allow_master_group = a1.checkbox("Master Group", value=True)
        allow_task = a2.checkbox("Task", value=True)
        allow_attendance = a3.checkbox("Attendance", value=True)
        allow_inout = a4.checkbox("IN / OUT", value=True)
        allow_visitor = a5.checkbox("Visitor", value=True)
        a6, a7 = st.columns(2)
        allow_appointment = a6.checkbox("Appointment", value=True)
        allow_accounting_entries = a7.checkbox("Accounting / Ledger", value=True)
        st.subheader("Inventory / Accounting Module Access")
        e1, e2, e3, e4, e5 = st.columns(5)
        allow_raw_material = e1.checkbox("Raw Material", value=True)
        allow_finished_goods = e2.checkbox("Finished Goods", value=True)
        allow_wip = e3.checkbox("WIP", value=True)
        allow_stock_voucher = e4.checkbox("Stock Voucher", value=True)
        allow_sales = e5.checkbox("Sales", value=True)
        e6, e7, e8, e9 = st.columns(4)
        allow_purchase = e6.checkbox("Purchase", value=True)
        allow_expense = e7.checkbox("Expense", value=True)
        allow_service_voucher = e8.checkbox("Service Voucher", value=True)
        allow_fixed_assets = e9.checkbox("Fixed Assets", value=True)
        e10, e11 = st.columns(2)
        allow_excel_upload = e10.checkbox("Excel Upload", value=True)
        allow_google_sheet_import = e11.checkbox("Google Sheet Import", value=True)
        if st.form_submit_button("Save Client", use_container_width=True):
            if client_code.strip() == "" or client_name.strip() == "":
                st.error("Client Code and Client Name are required.")
            else:
                insert_row("clients", {
                    "client_code": client_code.strip().upper(), "client_name": client_name.strip(),
                    "allow_master_group": allow_master_group,
                    "allow_task": allow_task, "allow_attendance": allow_attendance, "allow_inout": allow_inout, "allow_visitor": allow_visitor,
                    "allow_appointment": allow_appointment, "allow_raw_material": allow_raw_material, "allow_finished_goods": allow_finished_goods, "allow_wip": allow_wip,
                    "allow_stock_voucher": allow_stock_voucher, "allow_sales": allow_sales, "allow_purchase": allow_purchase, "allow_expense": allow_expense,
                    "allow_service_voucher": allow_service_voucher, "allow_fixed_assets": allow_fixed_assets, "allow_accounting_entries": allow_accounting_entries,
                    "allow_excel_upload": allow_excel_upload, "allow_google_sheet_import": allow_google_sheet_import, "status": status
                })
                st.success("Client saved successfully.")
                st.rerun()
    df = load_table("clients", 500)
    show_table_with_edit_delete("clients", df, "Client List")


def export_reports():
    page_header("Reports & Registers", "Sales, Purchase, Stock, Expense, GST, Masters and all registers")
    report_labels = ["Sales Register", "Purchase Register", "Stock Register", "Expense Register", "Service Register", "GST Register", "Ledger Register", "Ledger Group Register", "Stock Ledger Register", "Stock Group Register", "Accounting Register", "Fixed Assets Register", "All Table Export"]
    report = st.selectbox("Select Register", report_labels)
    rows = st.number_input("Rows to load", min_value=100, max_value=20000, value=5000, step=100)
    if report == "Sales Register":
        df = load_table("sales", int(rows))
    elif report == "Purchase Register":
        df = load_table("purchase", int(rows))
    elif report == "Stock Register":
        df = build_stock_register()
    elif report == "Expense Register":
        df = load_table("expenses", int(rows))
    elif report == "Service Register":
        df = load_table("service_vouchers", int(rows))
    elif report == "GST Register":
        df = build_gst_register()
    elif report == "Ledger Register":
        df = load_table("ledgers", int(rows))
    elif report == "Ledger Group Register":
        df = load_table("ledger_groups", int(rows))
    elif report == "Stock Ledger Register":
        df = load_table("stock_ledgers", int(rows))
    elif report == "Stock Group Register":
        df = load_table("stock_groups", int(rows))
    elif report == "Accounting Register":
        df = load_table("accounting_entries", int(rows))
    elif report == "Fixed Assets Register":
        df = load_table("fixed_assets", int(rows))
    else:
        options = list(DISPLAY_COLUMNS.keys())
        table_key = st.selectbox("Select Table", options)
        df = load_table(table_key, int(rows))
    show_register_report(report, df)


def get_dynamic_menu():
    if is_super_admin():
        return ["Dashboard", "Client Master", "User Management", "Employee Master", "Ledger Group Master", "Ledger Master", "Stock Group Master", "Stock Ledger Master", "Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation", "Appointments", "Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher", "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Fixed Assets", "Accounting Entries", "Excel Export Reports"]
    if st.session_state["role"] == "Admin":
        menu = ["Dashboard", "User Management", "Employee Master"]
    else:
        menu = []
    ordered_modules = ["Ledger Group Master", "Ledger Master", "Stock Group Master", "Stock Ledger Master", "Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation", "Appointments", "Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher", "Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Fixed Assets", "Accounting Entries"]
    for module in ordered_modules:
        if is_allowed(module):
            menu.append(module)
    menu.append("Excel Export Reports")
    return menu


def select_grouped_menu():
    available = get_dynamic_menu()
    groups = {
        "🔵 Admin": ("group-admin", ["Dashboard", "Client Master", "User Management", "Employee Master"]),
        "🧾 Master": ("group-master", ["Ledger Group Master", "Ledger Master", "Stock Group Master", "Stock Ledger Master"]),
        "🟢 HR / Office": ("group-hr", ["Attendance Management", "IN / OUT Register", "Visitor Register", "Task Delegation", "Appointments"]),
        "🟠 Stock": ("group-stock", ["Raw Material Stock", "Finished Goods Stock", "WIP Stock", "Stock Voucher"]),
        "🟣 Accounts": ("group-accounts", ["Sales GST Invoice", "Purchase GST Invoice", "Expense GST", "Service Voucher", "Fixed Assets", "Accounting Entries"]),
        "🔴 Reports": ("group-reports", ["Excel Export Reports"]),
    }
    available_groups = [g for g, (_, items) in groups.items() if any(item in available for item in items)]
    selected_group = st.sidebar.selectbox("Select Group", available_groups, key="selected_group_menu_v4")
    css_class, items = groups[selected_group]
    allowed_items = [x for x in items if x in available]
    st.sidebar.markdown(f"<div class='{css_class}'>{selected_group}</div>", unsafe_allow_html=True)
    return st.sidebar.radio("Select Module", allowed_items, key=f"module_{selected_group}_v4")


def main_app():
    rbm_header()
    st.sidebar.title("RBM AI")
    st.sidebar.write(f"Client: {st.session_state.get('client_name')}")
    st.sidebar.write(f"Client Code: {get_client_code()}")
    st.sidebar.write(f"User: {st.session_state.get('full_name')}")
    st.sidebar.write(f"Role: {st.session_state.get('role')}")
    st.sidebar.write(f"Date: {india_now().strftime('%d-%m-%Y')}")
    st.sidebar.write("Time Zone: Asia/Kolkata")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear(); st.rerun()
    choice = select_grouped_menu()
    if choice == "Dashboard": dashboard()
    elif choice == "Client Master": client_master()
    elif choice == "User Management": user_management()
    elif choice == "Employee Master": employee_master()
    elif choice == "Ledger Group Master": ledger_group_master()
    elif choice == "Ledger Master": ledger_master()
    elif choice == "Stock Group Master": stock_group_master()
    elif choice == "Stock Ledger Master": stock_ledger_master()
    elif choice == "Attendance Management": attendance()
    elif choice == "IN / OUT Register": inout_register()
    elif choice == "Visitor Register": visitor_register()
    elif choice == "Task Delegation": task_delegation()
    elif choice == "Appointments": appointment_module()
    elif choice == "Raw Material Stock": stock_form("stock_raw_material", "Raw Material Stock", "raw")
    elif choice == "Finished Goods Stock": stock_form("stock_finished_goods", "Finished Goods Stock", "fg")
    elif choice == "WIP Stock": stock_form("stock_wip", "Work in Progress Stock", "wip")
    elif choice == "Stock Voucher": stock_voucher_module()
    elif choice == "Sales GST Invoice": sales_purchase_form("sales", "Sales GST Invoice", "Customer Name")
    elif choice == "Purchase GST Invoice": sales_purchase_form("purchase", "Purchase GST Invoice", "Vendor Name")
    elif choice == "Expense GST": expense_module()
    elif choice == "Service Voucher": service_voucher_module()
    elif choice == "Fixed Assets": fixed_assets_module()
    elif choice == "Accounting Entries": accounting_entries_module()
    elif choice == "Excel Export Reports": export_reports()

# ================= END RBM ERP PHASE 4 MASTER GROUP OVERRIDES =================


if "logged_in" not in st.session_state:
    login_page()
else:
    main_app()
