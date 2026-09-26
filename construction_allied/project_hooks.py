# Copyright (c) 2026, mugen and contributors
# For license information, please see license.txt

"""Project document hooks for construction_allied.

Pure, deterministic arithmetic over the ``ca_*`` custom fields and child
tables. This hook is wired to ``Project.validate`` and therefore fires for
EVERY Project save on the host, including projects that have nothing to do
with Construction Allied.

ZERO-CONTRACT GUARD (mandatory): a project without a ``ca_contract_value``
(i.e. every pre-existing project on a shared site) must be left untouched.
Without the guard the percentage computation would divide by zero and break
every Project save site-wide.
"""

import frappe
from frappe.utils import flt


def _zero_outputs(doc):
	"""Set every computed field to 0. Used by the zero-contract guard."""
	doc.ca_material_total = 0
	doc.ca_labor_total = 0
	doc.ca_profit_total = 0
	doc.ca_material_pct = 0
	doc.ca_labor_pct = 0
	doc.ca_profit_pct = 0
	doc.ca_completed_area_sqm = 0
	doc.ca_pending_area_sqm = 0
	doc.ca_progress_pct = 0


def compute_project_totals(doc, method=None):
	"""Recompute tracking + budget totals from the child tables.

	Touches ONLY ``ca_*`` fields.

	material/labor totals = sum of ``ca_costs.amount`` grouped by
	``cost_type``; profit = contract - material - labor; the three
	percentages are each total / contract * 100 rounded to 1 dp.
	"""
	contract = flt(doc.get("ca_contract_value"))

	# --- MANDATORY zero-contract guard -------------------------------------
	# No contract value => nothing to compute. Zero the outputs and return so
	# that unrelated projects (all of them, on a shared site) are unaffected.
	if not contract:
		_zero_outputs(doc)
		return

	material_total = 0.0
	labor_total = 0.0
	for row in doc.get("ca_costs") or []:
		amount = flt(row.get("amount"))
		cost_type = (row.get("cost_type") or "").strip()
		if cost_type == "Material":
			material_total += amount
		elif cost_type == "Labor":
			labor_total += amount

	profit_total = contract - material_total - labor_total

	doc.ca_material_total = material_total
	doc.ca_labor_total = labor_total
	doc.ca_profit_total = profit_total
	doc.ca_material_pct = round(material_total / contract * 100, 1)
	doc.ca_labor_pct = round(labor_total / contract * 100, 1)
	doc.ca_profit_pct = round(profit_total / contract * 100, 1)

	# --- Area progress -----------------------------------------------------
	target = flt(doc.get("ca_target_area_sqm"))
	completed = 0.0
	for row in doc.get("ca_area_progress") or []:
		completed += flt(row.get("area_sqm"))

	doc.ca_completed_area_sqm = completed
	doc.ca_pending_area_sqm = max(target - completed, 0)
	doc.ca_progress_pct = round(completed / target * 100, 1) if target else 0
