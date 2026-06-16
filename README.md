RBM ERP Online Update

This package updates your Streamlit online RBM ERP script with the offline desktop version group/module structure.

Files:
- app.py : updated Streamlit code
- requirements.txt : Streamlit Cloud requirements

Main updates:
- Added all major offline ERP groups and modules to online menu
- Added colored tick prefixes:
  Red = Developer only
  Blue = SAP style
  Green = QuickBooks style
  Orange = Tally style
  Purple = RBM native
- Developer role support
- Developer-only modules hidden from client users
- Existing working pages reused wherever they already exist
- Missing/new modules open as safe starter/help pages instead of crashing

Important:
Some newly added modules are menu/starter screens until their Supabase tables and full forms are connected.
Existing working online modules remain unchanged.

UPDATE NOTE:
Client Master now shows Offline Desktop style Group + Module Permission panel.
Run CLIENT_MODULE_PERMISSIONS_SQL.sql in Supabase SQL editor to enable detailed module-wise client permissions.
Old clients table group flags remain backward compatible.
