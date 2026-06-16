RBM ERP ONLINE FINAL PATCH 8

Use this updated app.py in your Streamlit/GitHub project.

Main correction in this patch:
1. Role Permission Control remains role-wise permission screen.
   - Dropdown: Select Role
   - Used for Admin/User/Accounts User/HR User etc.

2. Role Based Security is now username-wise permission screen.
   - Dropdown: Select Username
   - It overrides role-wise permission for selected username.

3. User Group Permission is also mapped to username-wise security.

4. Client Super Admin / Admin cannot see Developer and Super Admin users in username dropdown.

5. If user_permissions table does not exist, run supabase_required_patch.sql once in Supabase SQL Editor.

Files:
- app.py
- requirements.txt
- supabase_required_patch.sql
