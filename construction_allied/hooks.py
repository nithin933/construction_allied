app_name = "construction_allied"
app_title = "Construction Allied"
app_publisher = "mugen"
app_description = "Construction Allied — Fix and Fine client demo (project tracking, budgets, area progress)"
app_email = "admin@mugen.ae"
app_license = "mit"

# Fixtures
# --------
# Roles are declared here so they are (re)created on install/update. Custom
# Fields carry "module": "Construction Allied" so an app uninstall can remove
# them (Frappe only cleans module-linked Custom Fields on uninstall).
fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["CA Manager", "CA Site Supervisor"]]],
	},
	{
		"dt": "Custom Field",
		"filters": [
			["dt", "in", ["Lead", "Quotation", "Project"]],
			["fieldname", "like", "ca_%"],
		],
	},
]

# Document Events
# ---------------
# compute_project_totals is deterministic, pure arithmetic and MANDATORY
# zero-contract guarded: this hook fires for EVERY Project save on the shared
# host, including existing projects whose ca_contract_value is 0.
doc_events = {
	"Project": {
		"validate": "construction_allied.project_hooks.compute_project_totals"
	}
}
