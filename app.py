-- RBM Office SaaS / Mini ERP Phase 5 SQL

-- Client permissions
alter table clients add column if not exists allow_task boolean default true;
alter table clients add column if not exists allow_attendance boolean default true;
alter table clients add column if not exists allow_inout boolean default true;
alter table clients add column if not exists allow_visitor boolean default true;
alter table clients add column if not exists allow_appointment boolean default true;
alter table clients add column if not exists allow_stock_raw boolean default true;
alter table clients add column if not exists allow_stock_fg boolean default true;
alter table clients add column if not exists allow_stock_wip boolean default true;
alter table clients add column if not exists allow_sales boolean default true;
alter table clients add column if not exists allow_purchase boolean default true;
alter table clients add column if not exists allow_expense boolean default true;
alter table clients add column if not exists allow_service_voucher boolean default true;
alter table clients add column if not exists allow_fixed_assets boolean default true;
alter table clients add column if not exists allow_accounting boolean default true;
alter table clients add column if not exists allow_master_group boolean default true;
alter table clients add column if not exists allow_excel_upload boolean default true;
alter table clients add column if not exists allow_google_sheet_import boolean default true;

-- Users
alter table users add column if not exists client_code text;
alter table users add column if not exists status text default 'Active';

-- Employee / HR
alter table employees add column if not exists client_code text;
alter table employees add column if not exists branch_division text;
alter table attendance add column if not exists client_code text;
alter table attendance add column if not exists financial_year text;
alter table attendance add column if not exists attendance_type text;
alter table attendance add column if not exists office_location text;
alter table attendance add column if not exists in_latitude text;
alter table attendance add column if not exists in_longitude text;
alter table attendance add column if not exists out_latitude text;
alter table attendance add column if not exists out_longitude text;
alter table inout_register add column if not exists client_code text;
alter table visitors add column if not exists client_code text;
alter table tasks add column if not exists client_code text;
alter table tasks add column if not exists branch_division text;
alter table tasks add column if not exists task_photo_name text;
alter table tasks add column if not exists task_photo_data text;

create table if not exists attendance_visits (
    id bigint generated always as identity primary key,
    client_code text,
    visit_date date,
    financial_year text,
    employee_name text,
    visit_place text,
    in_time text,
    out_time text,
    in_latitude text,
    in_longitude text,
    out_latitude text,
    out_longitude text,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists appointments (
    id bigint generated always as identity primary key,
    client_code text,
    appointment_date date,
    appointment_time text,
    customer_name text,
    mobile text,
    email text,
    company text,
    purpose text,
    meeting_with text,
    fees numeric default 0,
    status text,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

alter table appointments add column if not exists fees numeric default 0;

-- Master group
create table if not exists ledger_groups (
    id bigint generated always as identity primary key,
    client_code text,
    group_name text,
    group_type text,
    status text default 'Active',
    created_by text,
    created_at timestamp default now()
);

create table if not exists ledgers (
    id bigint generated always as identity primary key,
    client_code text,
    ledger_name text,
    ledger_group text,
    address text,
    contact_no text,
    tan_no text,
    gst_no text,
    pan_no text,
    opening_balance numeric default 0,
    balance_type text,
    status text default 'Active',
    created_by text,
    created_at timestamp default now()
);

create table if not exists stock_groups (
    id bigint generated always as identity primary key,
    client_code text,
    stock_group_name text,
    stock_type text,
    status text default 'Active',
    created_by text,
    created_at timestamp default now()
);

create table if not exists stock_ledgers (
    id bigint generated always as identity primary key,
    client_code text,
    item_name text,
    item_code text,
    stock_group text,
    unit text,
    hsn_code text,
    opening_qty numeric default 0,
    opening_rate numeric default 0,
    opening_value numeric default 0,
    gst_rate numeric default 0,
    status text default 'Active',
    created_by text,
    created_at timestamp default now()
);

-- Inventory
create table if not exists stock_raw_material (
    id bigint generated always as identity primary key,
    client_code text,
    entry_date date,
    item_name text,
    item_code text,
    unit text,
    opening_qty numeric default 0,
    inward_qty numeric default 0,
    outward_qty numeric default 0,
    closing_qty numeric default 0,
    rate numeric default 0,
    value numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists stock_finished_goods (
    id bigint generated always as identity primary key,
    client_code text,
    entry_date date,
    item_name text,
    item_code text,
    unit text,
    opening_qty numeric default 0,
    production_qty numeric default 0,
    sales_qty numeric default 0,
    closing_qty numeric default 0,
    rate numeric default 0,
    value numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists stock_wip (
    id bigint generated always as identity primary key,
    client_code text,
    entry_date date,
    process_name text,
    item_name text,
    item_code text,
    unit text,
    opening_qty numeric default 0,
    input_qty numeric default 0,
    output_qty numeric default 0,
    closing_qty numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

-- Sales/Purchase/Expense/Service vouchers
create table if not exists sales (
    id bigint generated always as identity primary key,
    client_code text,
    invoice_no text,
    invoice_date date,
    customer_name text,
    gstin text,
    item_name text,
    hsn_sac text,
    qty numeric default 0,
    rate numeric default 0,
    taxable_value numeric default 0,
    cgst numeric default 0,
    sgst numeric default 0,
    igst numeric default 0,
    total_value numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists purchase (
    id bigint generated always as identity primary key,
    client_code text,
    invoice_no text,
    invoice_date date,
    supplier_name text,
    gstin text,
    item_name text,
    hsn_sac text,
    qty numeric default 0,
    rate numeric default 0,
    taxable_value numeric default 0,
    cgst numeric default 0,
    sgst numeric default 0,
    igst numeric default 0,
    total_value numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists expenses (
    id bigint generated always as identity primary key,
    client_code text,
    expense_date date,
    vendor_name text,
    expense_head text,
    invoice_no text,
    gstin text,
    taxable_value numeric default 0,
    cgst numeric default 0,
    sgst numeric default 0,
    igst numeric default 0,
    total_value numeric default 0,
    payment_mode text,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists service_vouchers (
    id bigint generated always as identity primary key,
    client_code text,
    voucher_no text,
    voucher_date date,
    customer_name text,
    mobile text,
    email text,
    service_name text,
    sac_code text,
    taxable_value numeric default 0,
    cgst numeric default 0,
    sgst numeric default 0,
    igst numeric default 0,
    total_value numeric default 0,
    payment_status text,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

-- Fixed assets and accounts
create table if not exists fixed_assets (
    id bigint generated always as identity primary key,
    client_code text,
    asset_code text,
    asset_name text,
    purchase_date date,
    supplier_name text,
    invoice_no text,
    asset_category text,
    location text,
    cost numeric default 0,
    depreciation_rate numeric default 0,
    status text,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists accounting_entries (
    id bigint generated always as identity primary key,
    client_code text,
    entry_date date,
    voucher_type text,
    voucher_no text,
    debit_account text,
    credit_account text,
    amount numeric default 0,
    cgst numeric default 0,
    sgst numeric default 0,
    igst numeric default 0,
    total_amount numeric default 0,
    narration text,
    created_by text,
    created_at timestamp default now()
);

alter table accounting_entries add column if not exists cgst numeric default 0;
alter table accounting_entries add column if not exists sgst numeric default 0;
alter table accounting_entries add column if not exists igst numeric default 0;
alter table accounting_entries add column if not exists total_amount numeric default 0;

create table if not exists accounting_entry_lines (
    id bigint generated always as identity primary key,
    client_code text,
    entry_id bigint,
    dr_cr text,
    ledger_name text,
    amount numeric default 0,
    remarks text,
    created_at timestamp default now()
);

create table if not exists stock_vouchers (
    id bigint generated always as identity primary key,
    client_code text,
    voucher_no text,
    voucher_date date,
    voucher_type text,
    item_name text,
    stock_group text,
    qty numeric default 0,
    rate numeric default 0,
    value numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);

create table if not exists import_logs (
    id bigint generated always as identity primary key,
    client_code text,
    import_type text,
    module_name text,
    total_rows numeric default 0,
    success_rows numeric default 0,
    failed_rows numeric default 0,
    remarks text,
    created_by text,
    created_at timestamp default now()
);
