# construction_allied

Custom Frappe app for the **Fix and Fine Technical Service & Contracting LLC**
client demo on `test18.m-fractal.com`.

It ships:

- **Roles** `CA Manager` and `CA Site Supervisor` (fixtures).
- **Custom Fields** (`ca_*`) on `Lead`, `Quotation` and `Project` (fixtures, module
  `Construction Allied`).
- **Four child doctypes** on `Project`: `CA Project Stage`, `CA Area Progress`,
  `CA Cost Entry`, `CA Budget Line`.
- **`Project.validate` hook** (`project_hooks.compute_project_totals`) that rolls up
  area progress and 40/40/20 material / labor / profit figures.
- **`seed.py::seed_demo()`** — an idempotent, explicit `bench execute` seed of the
  demo dataset.

The app adds **no new whitelisted endpoints** and does not run any patch.

## Layout

```
construction_allied/
  hooks.py            # fixtures (Role + Custom Field) + doc_events Project.validate
  modules.txt         # "Construction Allied"
  patches.txt         # EMPTY for v1
  seed.py             # seed_demo()
  project_hooks.py    # compute_project_totals (zero-contract guarded)
  fixtures/           # role.json, custom_field.json (module = "Construction Allied")
  construction_allied/doctype/   # the 4 child doctypes
```

## Deploy runbook (git-flow only — never scp)

All server changes go through git. From a machine with the repo:

1. **Push** the app branch tip:

   ```bash
   git push origin main
   ```

2. On the bench (`/home/mugenerpadmin/test18`, user `mugenerpadmin`), pull the
   **branch tip** (never a pinned SHA):

   ```bash
   cd apps/construction_allied && git fetch origin main && git pull origin main
   ```

3. Install the app on the demo site:

   ```bash
   bench --site test18.m-fractal.com install-app construction_allied
   ```

4. Clear cache and do a **full** restart (gunicorn runs `--preload`; a worker
   respawn alone keeps stale modules, and the new `doc_events` hook needs the
   web tier restarted):

   ```bash
   bench --site test18.m-fractal.com clear-cache
   bench restart
   ```

5. Verify the fixtures landed (roles + custom fields):

   ```bash
   bench --site test18.m-fractal.com execute frappe.client.get_list \
     --kwargs '{"doctype":"Role","filters":[["name","like","CA%"]]}'
   ```

## Seed the demo data

The seed is deliberately **not** a patch: a fresh install marks every patch of
the app complete (`set_all_patches_as_completed`), so seeding must be invoked
explicitly. It is idempotent — re-running it creates nothing new.

```bash
bench --site test18.m-fractal.com execute construction_allied.seed.seed_demo
```

It prints a `{created, skipped}` summary. What it creates:

- UOM `Sqm`; Item Group `All Item Groups` + `CA Services`; Price List
  `Standard Selling` (AED); Customer Group / Territory roots.
- Company `Fix and Fine Technical Service LLC` (abbr `FFTS`, AED, UAE, chart
  `Standard` — the standard chart auto-builds the accounting skeleton).
- Items `CA-TILE-FIX`, `CA-WATERPROOF`, `CA-GENERAL` (services, `Sqm`) with
  `Standard Selling` price rows; Customer `Al Bahr Facilities Management LLC`.
- 3 Leads, 2 Quotations (Q1 awarded rev 0 + LPO 180,000; Q2 rev 1 rebalanced),
  2 Projects ("Al Bahr Tower – Tiling Works" active, "Al Bahr Tower –
  Waterproofing" early stage) and 2 Employees.

`Global Defaults` is **not** touched — the host's `default_company` stays as it
is, and the demo reaches the demo company through pinned DTV row defaults.

## Demo script

> The Project dashboard is a **per-record Overview tab**: open a seeded Project
> and the Overview tab is shown first, with the Tracking tab (Area Progress,
> Lifecycle & Stages, Cost Entries, Budget & Margin) alongside it.

1. Open the **CA Project** list, open "Al Bahr Tower – Tiling Works".
2. The **Overview** tab shows contract value, completed / target sqm, progress %,
   material / labor / margin %.
3. Switch to the **Tracking** tab: area progress rows (9 × 20 sqm), lifecycle
   stages, cost entries (material 71,500 + labor 69,800) and the budget table
   (40/40/20 planned vs actual).
4. Project totals: contract 180,000 − 71,500 − 69,800 = **38,700 profit**
   (Material 39.7 % / Labor 38.8 % / Profit 21.5 %).
5. Open the **CA Lead** and **CA Quotation** forms to show the trimmed capture
   and revision/LPO flow.

## Patches policy

`patches.txt` is intentionally **empty** for v1. This bench's `mstartnew`
`update_app` **does** run an app's patches automatically, so any patch added in
future **must be idempotent** (exists-check before insert/update), because it may
run again on every deploy.

## Rollback (plan §10, verbatim)

1. Delete DTVs `CA Lead`, `CA Quotation`, `CA Project` (by name).
2. Delete sidebar `CA Lead`, `CA Quotation`, `CA Project`, then parent `CA`.
3. Delete `ca_*` Custom Fields by name (Lead ×2, Quotation ×2, Project ~24) → `clear-cache`.
4. `doc_events` are removed only by app uninstall; full teardown =
   `uninstall-app construction_allied` (+ `bench restart`).
5. Seed artifacts: transactions → customer → items → masters (Company may be left as harmless master data,
   stated explicitly).
6. Delete/disable the temp recording user. 7. `clear-cache` (+ restart if `doc_events` changed).
