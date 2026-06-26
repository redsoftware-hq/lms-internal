## Quality Asia Internal LMS

Custom Frappe app for **Quality Asia Internal LMS** — an internal, staff-only learning
platform built on [Frappe LMS](https://github.com/frappe/lms). It shares the Quality Asia
branding and training-certificate format with the public Quality Asia LMS, but is
**invite-only** and free:

- **No public sign-up** — `LMS Settings.disable_signup = 1`; browsing requires login
  (`allow_guest_access = 0`).
- **Back-end onboarding** — staff accounts are created with
  `quality_asia_internal_lms.setup.invite.invite_employees` (see below).
- **No payments** — no Razorpay / GST; courses are free and logged-in staff self-enroll.
- **No public course catalog** — training content is authored in-app.
- **Kept from the public app** — Quality Asia branding (skin/logo/favicon) and the
  QA training certificate (print format + auto-filled training dates).

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench --site <site> install-app lms quality_asia_internal_lms
```

### Onboarding employees

Public sign-up is disabled, so register staff from the back end. Each gets a Website User
with the `LMS Student` role and Frappe's welcome (set-password) email:

```bash
# a few inline
bench --site <site> execute quality_asia_internal_lms.setup.invite.invite_employees \
  --kwargs "{'rows': [{'email': 'asha@client.com', 'full_name': 'Asha Rao'}]}"

# or from a CSV with header: email,full_name
bench --site <site> execute quality_asia_internal_lms.setup.invite.invite_employees \
  --kwargs "{'csv_path': '/path/to/employees.csv'}"
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/quality_asia_internal_lms
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
