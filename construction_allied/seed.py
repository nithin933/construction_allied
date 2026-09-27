# Copyright (c) 2026, mugen and contributors
# For license information, please see license.txt

"""Idempotent demo seed for the Construction Allied pilot.

Invoke explicitly (NOT a patch — a fresh install marks all patches complete).
On this bench the bare dotted form fails with ``NameError``; wrap it in
``frappe.get_attr``:

    bench --site <site> execute "frappe.get_attr(\"construction_allied.seed.seed_demo\")"

Every step is query-before-insert, so a second run creates nothing new.
The function never modifies an existing record and never touches
``Global Defaults`` (the host's ``default_company`` stays "Shine Healthcare";
the demo reaches its own company through pinned DTV row defaults instead).
"""

import frappe
from frappe.utils import add_days, today

DEMO_COMPANY = "Fix and Fine Technical Service LLC"
DEMO_ABBR = "FFTS"
DEMO_CUSTOMER = "Al Bahr Facilities Management LLC"
# ``All Customer Groups`` is the tree ROOT (is_group=1); Customers must link to a
# LEAF, so the demo uses its own leaf ``CA Customers`` beneath that root.
DEMO_CUSTOMER_GROUP_ROOT = "All Customer Groups"
DEMO_CUSTOMER_GROUP = "CA Customers"
DEMO_TERRITORY = "All Territories"
PRICE_LIST = "Standard Selling"
ITEM_GROUP_ROOT = "All Item Groups"
ITEM_GROUP = "CA Services"
UOM = "Sqm"

ITEMS = [
    ("CA-TILE-FIX", "Tile Fixing Works", 500),
    ("CA-WATERPROOF", "Waterproofing Works", 1100),
    ("CA-GENERAL", "General Technical Works", 350),
]

STAGES = [
    "Lead Capture / Inquiry",
    "Site Visit",
    "Quotation Preparation",
    "Quotation Approval / LPO",
    "Site & Team Allocation",
    "Material Requisition & Delivery",
    "Daily Site Execution",
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def _log(summary, kind, label):
    summary[kind].append(label)


def _ensure_simple(summary, doctype, key, build):
    """Create ``doctype`` named ``key`` if absent. ``build`` returns a doc dict."""
    if frappe.db.exists(doctype, key):
        _log(summary, "skipped", f"{doctype}:{key}")
        return False
    doc = frappe.get_doc(build())
    doc.insert(ignore_permissions=True)
    _log(summary, "created", f"{doctype}:{key}")
    return True


def _assert_leaf(doctype, name, field):
    """Fail loudly unless ``name`` is a leaf (is_group=0) node of ``doctype``.

    Some ERPNext Link fields point at a taxonomy whose tree ROOT is a group and
    whose leaves are the only legal targets. The canonical case is
    ``Customer.validate_customer_group`` (erpnext/selling/doctype/customer/customer.py),
    which throws "Cannot select a Group type Customer Group. Please select a
    non-group Customer Group." A misconfigured constant would otherwise only fail
    deep inside that hook; asserting here names the offender in one line.
    """
    if frappe.db.get_value(doctype, name, "is_group"):
        frappe.throw(
            f"{field}: {doctype} '{name}' is a group (is_group=1) but this Link "
            f"field requires a leaf (is_group=0)."
        )


# --------------------------------------------------------------------------
# steps
# --------------------------------------------------------------------------
def _masters(summary):
    # 1. UOM ---------------------------------------------------------------
    _ensure_simple(summary, "UOM", UOM, lambda: {"doctype": "UOM", "uom_name": UOM})

    # 2. Item Groups -------------------------------------------------------
    _ensure_simple(summary, "Item Group", ITEM_GROUP_ROOT, lambda: {
        "doctype": "Item Group",
        "item_group_name": ITEM_GROUP_ROOT,
        "is_group": 1,
    })
    _ensure_simple(summary, "Item Group", ITEM_GROUP, lambda: {
        "doctype": "Item Group",
        "item_group_name": ITEM_GROUP,
        "parent_item_group": ITEM_GROUP_ROOT,
        "is_group": 0,
    })
    # ERPNext does not validate a leaf Item Group for Item.item_group, but the
    # seed deliberately keeps taxonomy links on leaves; assert that intent holds.
    _assert_leaf("Item Group", ITEM_GROUP, "Item.item_group")

    # 3. Price List --------------------------------------------------------
    _ensure_simple(summary, "Price List", PRICE_LIST, lambda: {
        "doctype": "Price List",
        "price_list_name": PRICE_LIST,
        "currency": "AED",
        "selling": 1,
    })

    # 4. Customer Group / Territory roots ---------------------------------
    _ensure_simple(summary, "Customer Group", DEMO_CUSTOMER_GROUP_ROOT, lambda: {
        "doctype": "Customer Group",
        "customer_group_name": DEMO_CUSTOMER_GROUP_ROOT,
        "is_group": 1,
    })
    # Leaf beneath the root: Customer.customer_group must be a leaf, because
    # Customer.validate_customer_group (erpnext customer.py) rejects any group
    # node with "Cannot select a Group type Customer Group".
    _ensure_simple(summary, "Customer Group", DEMO_CUSTOMER_GROUP, lambda: {
        "doctype": "Customer Group",
        "customer_group_name": DEMO_CUSTOMER_GROUP,
        "parent_customer_group": DEMO_CUSTOMER_GROUP_ROOT,
        "is_group": 0,
    })
    _assert_leaf("Customer Group", DEMO_CUSTOMER_GROUP, "Customer.customer_group")
    _ensure_simple(summary, "Territory", DEMO_TERRITORY, lambda: {
        "doctype": "Territory",
        "territory_name": DEMO_TERRITORY,
        "is_group": 1,
    })
    # Customer.territory has NO leaf requirement in ERPNext (no validate_territory),
    # so the group root "All Territories" is a legal target here.


def _company(summary):
    # 5. Company (on_update auto-builds COA / warehouses / cost centre...) ---
    if frappe.db.exists("Company", DEMO_COMPANY):
        _log(summary, "skipped", f"Company:{DEMO_COMPANY}")
        return

    existing_abbr = frappe.db.get_value("Company", {"abbr": DEMO_ABBR}, "name")
    if existing_abbr:
        # Abbr is a second natural key — never steal another company's abbr.
        _log(summary, "skipped", f"Company abbr {DEMO_ABBR} already used by {existing_abbr}")
        return

    company = frappe.get_doc({
        "doctype": "Company",
        "company_name": DEMO_COMPANY,
        "abbr": DEMO_ABBR,
        "default_currency": "AED",
        "country": "United Arab Emirates",
        "chart_of_accounts": "Standard",
    })
    company.insert(ignore_permissions=True)
    _log(summary, "created", f"Company:{DEMO_COMPANY}")


def _items_and_customer(summary):
    # 6. Items + Item Prices ----------------------------------------------
    valid_from = add_days(today(), -30)
    for item_code, item_name, rate in ITEMS:
        _ensure_simple(summary, "Item", item_code, lambda item_code=item_code,
                       item_name=item_name: {
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name,
            "item_group": ITEM_GROUP,
            "stock_uom": UOM,
            "is_stock_item": 0,
            "is_sales_item": 1,
            "is_purchase_item": 0,
            "item_type": "Service",
        })
        price_key = f"{item_code}|{PRICE_LIST}"
        if frappe.db.exists("Item Price", {"item_code": item_code, "price_list": PRICE_LIST}):
            _log(summary, "skipped", f"Item Price:{price_key}")
        else:
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": PRICE_LIST,
                "currency": "AED",
                "price_list_rate": rate,
                "valid_from": valid_from,
            }).insert(ignore_permissions=True)
            _log(summary, "created", f"Item Price:{price_key}")

    # 7. Customer ----------------------------------------------------------
    # NOTE (site customization on test18): Property Setter
    # `Customer-disabled-default` sets the `disabled` default to 1, and tsgc's
    # before_insert hook `disable_customer` forces disabled=1 for users without the
    # "Management" role. The demo must be a usable party, so set disabled=0
    # explicitly (Administrator holds Management, so the hook is a no-op here).
    _ensure_simple(summary, "Customer", DEMO_CUSTOMER, lambda: {
        "doctype": "Customer",
        "customer_name": DEMO_CUSTOMER,
        "customer_type": "Company",
        "customer_group": DEMO_CUSTOMER_GROUP,
        "territory": DEMO_TERRITORY,
        "disabled": 0,
    })


def _leads(summary):
    # 8. Leads x3 ----------------------------------------------------------
    leads = [
        ("Ahmed", "Khan", "Emirates Facilities Co", "demo.lead1@fixandfine.example",
         "Sqm-based tiling works for a tower lobby", add_days(today(), 2)),
        ("Sara", "Al Marzooqi", "Gulf Property Group", "demo.lead2@fixandfine.example",
         "Waterproofing for two podium floors", add_days(today(), 4)),
        ("Rakesh", "Nair", "Marina Heights Owners", "demo.lead3@fixandfine.example",
         "General technical maintenance retainer", add_days(today(), 6)),
    ]
    for first, last, company_name, email, requirement, visit_on in leads:
        if frappe.db.exists("Lead", {"email_id": email}):
            _log(summary, "skipped", f"Lead:{email}")
            continue
        frappe.get_doc({
            "doctype": "Lead",
            "first_name": first,
            "last_name": last,
            "company_name": company_name,
            "email_id": email,
            "mobile_no": "+9715000000" + str(len(email) % 10),
            "source": "Campaign",
            "status": "Lead",
            "lead_owner": "Administrator",
            # tsgc field — MUST be set to a valid option for saves to pass.
            "inquiry_type": "Safe Area",
            "ca_requirement": requirement,
            "ca_site_visit_on": visit_on,
            # NOTE: custom_is_site_visit_required is deliberately left unticked —
            # ticking it makes tsgc insert a Site Visit on every save.
        }).insert(ignore_permissions=True)
        _log(summary, "created", f"Lead:{email}")


def _quotations(summary):
    # 9. Quotations x2 -----------------------------------------------------
    # Q1 — awarded, LPO 180,000, revision 0.
    q1_key = {"party_name": DEMO_CUSTOMER, "ca_lpo_no": "LPO-2026-0142"}
    if frappe.db.exists("Quotation", q1_key):
        _log(summary, "skipped", "Quotation:Q1 (rev 0 / LPO-2026-0142)")
    else:
        _make_quotation(
            summary,
            key_label="Quotation:Q1 (rev 0 / LPO-2026-0142)",
            revision=0,
            lpo="LPO-2026-0142",
            items=[
                {"item_code": "CA-TILE-FIX", "qty": 250, "rate": 500},
                {"item_code": "CA-WATERPROOF", "qty": 50, "rate": 1100},
            ],
        )

    # Q2 — revision 1 with rebalanced rates.
    q2_key = {"party_name": DEMO_CUSTOMER, "ca_revision_no": 1}
    if frappe.db.exists("Quotation", q2_key):
        _log(summary, "skipped", "Quotation:Q2 (rev 1)")
    else:
        _make_quotation(
            summary,
            key_label="Quotation:Q2 (rev 1)",
            revision=1,
            lpo=None,
            items=[
                {"item_code": "CA-TILE-FIX", "qty": 250, "rate": 460},
                {"item_code": "CA-WATERPROOF", "qty": 50, "rate": 1120},
            ],
        )


def _make_quotation(summary, key_label, revision, lpo, items):
    doc = frappe.get_doc({
        "doctype": "Quotation",
        "naming_series": "SAL-QTN-.YYYY.-",
        "quotation_to": "Customer",
        "party_name": DEMO_CUSTOMER,
        "company": DEMO_COMPANY,
        "transaction_date": today(),
        "order_type": "Sales",
        "currency": "AED",
        "conversion_rate": 1.0,
        "selling_price_list": PRICE_LIST,
        "price_list_currency": "AED",
        "plc_conversion_rate": 1.0,
        "ca_revision_no": revision,
        "ca_lpo_no": lpo,
        "items": [
            {
                "item_code": row["item_code"],
                "qty": row["qty"],
                "uom": UOM,
                "stock_uom": UOM,
                "conversion_factor": 1,
                "rate": row["rate"],
                "price_list_rate": row["rate"],
            }
            for row in items
        ],
    })
    doc.insert(ignore_permissions=True)
    _log(summary, "created", key_label)


def _employees(summary):
    # 10. Designations + Employees x2 (optional HRMS) ----------------------
    if not frappe.db.exists("DocType", "Employee"):
        _log(summary, "skipped", "Employees (HRMS not installed)")
        return

    for designation in ("Site Supervisor", "Technician"):
        _ensure_simple(summary, "Designation", designation, lambda designation=designation: {
            "doctype": "Designation",
            "designation_name": designation,
        })

    employees = [
        ("Suresh Menon", "Site Supervisor"),
        ("Bilal Ahmad", "Technician"),
    ]
    for name, designation in employees:
        if frappe.db.exists("Employee", {"employee_name": name}):
            _log(summary, "skipped", f"Employee:{name}")
            continue
        frappe.get_doc({
            "doctype": "Employee",
            "first_name": name.split()[0],
            "last_name": name.split()[-1],
            "employee_name": name,
            "company": DEMO_COMPANY,
            "designation": designation,
            "gender": "Male",
            "date_of_birth": "1990-06-15",
            "date_of_joining": "2025-01-15",
            "status": "Active",
        }).insert(ignore_permissions=True)
        _log(summary, "created", f"Employee:{name}")


def _project_exists(project_name):
    return frappe.db.exists("Project", {"project_name": project_name, "company": DEMO_COMPANY})


def _projects(summary):
    # 11. Projects x2 (draft) ---------------------------------------------
    p1 = "Al Bahr Tower \u2013 Tiling Works"

    if _project_exists(p1):
        _log(summary, "skipped", f"Project:{p1}")
    else:
        quotation = frappe.db.get_value(
            "Quotation", {"party_name": DEMO_CUSTOMER, "ca_lpo_no": "LPO-2026-0142"}, "name")
        stages = [
            {
                "stage": stage,
                "planned_date": add_days(today(), -14 + i * 3),
                "actual_date": add_days(today(), -14 + i * 3) if i < 4 else None,
                "status": "Completed" if i < 4 else ("In Progress" if i == 4 else "Pending"),
                "remarks": "" if i < 4 else "Scheduled",
            }
            for i, stage in enumerate(STAGES)
        ]
        frappe.get_doc({
            "doctype": "Project",
            "project_name": p1,
            "company": DEMO_COMPANY,
            "customer": DEMO_CUSTOMER,
            "status": "Open",
            "expected_start_date": add_days(today(), -14),
            "expected_end_date": add_days(today(), 16),
            "ca_quotation": quotation,
            "ca_target_area_sqm": 400,
            "ca_contract_value": 180000,
            "ca_area_progress": [
                {"date": add_days(today(), -14 + i), "area_sqm": 20,
                 "remarks": f"Day {i + 1}: 20 sqm completed"}
                for i in range(9)
            ],
            "ca_stages": stages,
            "ca_costs": [
                {"date": add_days(today(), -10), "cost_type": "Material",
                 "description": "Tile adhesive, grout and waterproofing membrane", "amount": 71500},
                {"date": add_days(today(), -6), "cost_type": "Labor",
                 "description": "Site labor — 9 working days", "amount": 69800},
            ],
            "ca_budget": [
                {"category": "Material", "target_percent": 40, "planned_amount": 72000,
                 "actual_amount": 71500, "variance": 500},
                {"category": "Labor", "target_percent": 40, "planned_amount": 72000,
                 "actual_amount": 69800, "variance": 2200},
            ],
        }).insert(ignore_permissions=True)
        _log(summary, "created", f"Project:{p1}")

    p2 = "Al Bahr Tower \u2013 Waterproofing"
    if _project_exists(p2):
        _log(summary, "skipped", f"Project:{p2}")
    else:
        frappe.get_doc({
            "doctype": "Project",
            "project_name": p2,
            "company": DEMO_COMPANY,
            "customer": DEMO_CUSTOMER,
            "status": "Open",
            "expected_start_date": add_days(today(), -2),
            "expected_end_date": add_days(today(), 28),
            "ca_target_area_sqm": 150,
            "ca_contract_value": 55000,
            "ca_area_progress": [
                {"date": add_days(today(), -2), "area_sqm": 20, "remarks": "Mobilisation"},
                {"date": add_days(today(), -1), "area_sqm": 20, "remarks": "Primer coat"},
            ],
            "ca_stages": [
                {"stage": STAGES[0], "status": "Completed",
                 "actual_date": add_days(today(), -3)},
                {"stage": STAGES[1], "status": "Completed",
                 "actual_date": add_days(today(), -2)},
                {"stage": STAGES[6], "status": "In Progress",
                 "planned_date": add_days(today(), 2)},
            ],
            "ca_costs": [
                {"date": add_days(today(), -1), "cost_type": "Material",
                 "description": "Waterproofing membrane (first batch)", "amount": 12000},
            ],
            "ca_budget": [
                {"category": "Material", "target_percent": 40, "planned_amount": 22000,
                 "actual_amount": 12000, "variance": 10000},
            ],
        }).insert(ignore_permissions=True)
        _log(summary, "created", f"Project:{p2}")


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------
def seed_demo():
    """Create the Construction Allied demo dataset. Idempotent."""
    summary = {"created": [], "skipped": []}

    _masters(summary)
    _company(summary)
    _items_and_customer(summary)
    _leads(summary)
    _quotations(summary)
    _employees(summary)
    _projects(summary)

    frappe.db.commit()

    summary["created_count"] = len(summary["created"])
    summary["skipped_count"] = len(summary["skipped"])
    print(frappe.as_json(summary))
    return summary
