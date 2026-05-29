import streamlit as st
import pandas as pd
from datetime import datetime, date
from io import BytesIO
from supabase import create_client, Client

st.set_page_config(page_title="RBM Office SaaS", page_icon="🏢", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLES = {
    "clients": "clients",
    "users": "users",
    "employees": "employees",
    "attendance": "attendance",
    "inout": "inout_register",
    "visitors": "visitors",
    "tasks": "tasks",
}

DISPLAY_COLUMNS = {
    "clients": ["id", "client_code", "client_name", "status", "created_at"],
    "users": ["id", "client_code", "username", "password", "role", "full_name", "status"],
    "employees": ["id", "client_code", "employee_id", "employee_name", "mobile", "email", "department", "designation", "status"],
    "attendance": ["id", "client_code", "attendance_date", "employee_name", "status", "in_time", "out_time", "working_hours", "remarks", "created_by"],
    "inout": ["id", "client_code", "entry_date", "person_name", "purpose", "in_time", "out_time", "remarks", "created_by"],
    "visitors": ["id", "client_code", "visit_date", "visitor_name", "mobile", "company", "meeting_with", "purpose", "in_time", "out_time", "remarks", "created_by"],
    "tasks": ["id", "client_code", "task_date", "task", "assigned_to", "priority", "due_date", "status", "remarks", "created_by"],
}

st.markdown("""
<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
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
.stButton button, .stDownloadButton button {border-radius:12px;font-weight:700;}
</style>
""", unsafe_allow_html=True)


def safe_df(data):
    return pd.DataFrame(data or [])


def get_client_code():
    return st.session_state.get("client_code", "RBM")


def is_super_admin():
    return st.session_state.get("role") == "Super Admin"


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


def show_metric_card(label, value):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def show_table_with_edit_delete(key, df, title):
    st.subheader(title)
    st.caption("Latest 500 records shown for speed.")

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
                if col == "id":
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
                client_code = str(row.get("client_code", "RBM"))

                client_name = client_code
                client_data = safe_df(
                    supabase.table("clients").select("*").eq("client_code", client_code).limit(1).execute().data
                )
                if not client_data.empty:
                    client_name = str(client_data.iloc[0].get("client_name", client_code))

                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = str(row.get("role", "User"))
                st.session_state["full_name"] = str(row.get("full_name", username))
                st.session_state["client_code"] = client_code
                st.session_state["client_name"] = client_name
                st.rerun()

        st.info("Super Admin Login: admin / rbm123")


def dashboard():
    st.header("Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        show_metric_card("Employees", get_count("employees"))
    with c2:
        show_metric_card("Attendance", get_count("attendance"))
    with c3:
        show_metric_card("Visitors", get_count("visitors"))
    with c4:
        show_metric_card("Tasks", get_count("tasks"))

    st.divider()
    st.subheader("Latest Tasks")
    st.dataframe(load_table("tasks", 100), use_container_width=True)


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

        if st.form_submit_button("Save Client", use_container_width=True):
            if client_code.strip() == "" or client_name.strip() == "":
                st.error("Client Code and Client Name are required.")
            else:
                insert_row("clients", {
                    "client_code": client_code.strip().upper(),
                    "client_name": client_name.strip(),
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
        password = c2.text_input("Password")
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
        status = c1.selectbox("Status", ["Active", "Inactive"])

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
                    "status": status
                })
                st.success("Employee saved successfully.")
                st.rerun()

    show_table_with_edit_delete("employees", df, "Employee List")


def attendance():
    st.header("Attendance Management")

    df = load_table("attendance", 500)
    emp = load_table("employees", 1000)

    emp_list = emp["employee_name"].dropna().astype(str).tolist() if not emp.empty else []
    if not emp_list:
        emp_list = ["No Employee Found"]

    with st.form("attendance_form"):
        c1, c2 = st.columns(2)

        attendance_date = c1.date_input("Date", value=date.today())
        employee_name = c2.selectbox("Employee Name", emp_list)
        status = c1.selectbox("Status", ["Present", "Absent", "Half Day", "Leave"])
        in_time = c2.time_input("In Time")
        out_time = c1.time_input("Out Time")
        remarks = c2.text_input("Remarks")

        if st.form_submit_button("Save Attendance", use_container_width=True):
            if employee_name == "No Employee Found":
                st.error("Please create employee first.")
            else:
                insert_row("attendance", {
                    "attendance_date": str(attendance_date),
                    "employee_name": employee_name,
                    "status": status,
                    "in_time": str(in_time),
                    "out_time": str(out_time),
                    "working_hours": calculate_hours(in_time, out_time),
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Attendance saved successfully.")
                st.rerun()

    show_table_with_edit_delete("attendance", df, "Attendance Records")


def inout_register():
    st.header("IN / OUT Register")

    df = load_table("inout", 500)

    with st.form("inout_form"):
        c1, c2 = st.columns(2)

        entry_date = c1.date_input("Date", value=date.today())
        person_name = c2.text_input("Person Name")
        purpose = c1.text_input("Purpose")
        in_time = c2.time_input("In Time")
        out_time = c1.time_input("Out Time")
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

        visit_date = c1.date_input("Date", value=date.today())
        visitor_name = c2.text_input("Visitor Name")
        mobile = c1.text_input("Mobile")
        company = c2.text_input("Company")
        meeting_with = c1.text_input("Meeting With")
        purpose = c2.text_input("Purpose")
        in_time = c1.time_input("In Time")
        out_time = c2.time_input("Out Time")
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

    st.subheader("Assign Type")
    assign_mode = st.radio(
        "Choose assign method",
        ["Select Employee", "Manual Entry"],
        horizontal=True,
        key="task_assign_mode_radio"
    )

    with st.form("task_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        task_date = c1.date_input("Task Date", value=date.today())
        task = c2.text_area("Task")

        priority = c1.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
        status = c1.selectbox("Status", ["Pending", "In Progress", "Completed"])

        if assign_mode == "Manual Entry":
            assigned_to = c2.text_input("Assigned To", placeholder="Type manual name here")
        else:
            if emp_list:
                assigned_to = c2.selectbox("Assigned To", emp_list)
            else:
                assigned_to = c2.text_input("Assigned To", placeholder="No employee found, type name here")

        due_date = c2.date_input("Due Date", value=date.today())
        remarks = c2.text_input("Remarks")

        if st.form_submit_button("Save Task", use_container_width=True):
            if task.strip() == "":
                st.error("Task is required.")
            elif str(assigned_to).strip() == "":
                st.error("Assigned To is required.")
            else:
                insert_row("tasks", {
                    "task_date": str(task_date),
                    "task": task,
                    "assigned_to": str(assigned_to),
                    "priority": priority,
                    "due_date": str(due_date),
                    "status": status,
                    "remarks": remarks,
                    "created_by": st.session_state["username"]
                })
                st.success("Task saved successfully.")
                st.rerun()

    show_table_with_edit_delete("tasks", df, "Task Records")


def export_reports():
    st.header("Excel / CSV Export Reports")

    report_options = ["employees", "attendance", "inout", "visitors", "tasks"]

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
        st.download_button(
            "Download CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"{report}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with c2:
        st.download_button(
            "Download Excel",
            data=to_excel_bytes(filtered),
            file_name=f"{report}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


def main_app():
    rbm_header()

    st.sidebar.title("RBM AI")
    st.sidebar.write(f"Client: {st.session_state.get('client_name')}")
    st.sidebar.write(f"Client Code: {get_client_code()}")
    st.sidebar.write(f"User: {st.session_state.get('full_name')}")
    st.sidebar.write(f"Role: {st.session_state.get('role')}")

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    if is_super_admin():
        menu = [
            "Dashboard",
            "Client Master",
            "User Management",
            "Employee Master",
            "Attendance Management",
            "IN / OUT Register",
            "Visitor Register",
            "Task Delegation",
            "Excel Export Reports",
        ]
    elif st.session_state["role"] == "Admin":
        menu = [
            "Dashboard",
            "User Management",
            "Employee Master",
            "Attendance Management",
            "IN / OUT Register",
            "Visitor Register",
            "Task Delegation",
            "Excel Export Reports",
        ]
    else:
        menu = [
            "Attendance Management",
            "IN / OUT Register",
            "Visitor Register",
            "Task Delegation",
            "Excel Export Reports",
        ]

    choice = st.sidebar.radio("Select Module", menu)

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
    elif choice == "Excel Export Reports":
        export_reports()


if "logged_in" not in st.session_state:
    login_page()
else:
    main_app()
