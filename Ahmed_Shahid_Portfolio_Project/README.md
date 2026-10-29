# Ahmed Shahid Portfolio Project

A full-stack, editable personal portfolio built with semantic HTML, CSS, vanilla JavaScript, Python/FastAPI, SQLAlchemy, a persistent SQL database, PDF CV generation, and optional n8n notifications.

## Important accuracy note about the reference

The supplied reference URL (`https://live-age-calculator--abdullah201435.replit.app/`) could not be reached by the browser/network available while building this project. That means a pixel-by-pixel comparison, original content extraction, and original college-name verification were not possible. This project therefore implements the requested portfolio sections and interactions in a polished responsive design, but **it is not certified as an exact visual clone of the reference**. Please compare it with the live reference in a browser and adjust the CSS/assets if exact matching is required.

The initial configuration follows the requested naming rules:

- Public portfolio name: **Ahmed Shahid**
- CV name: **Ahmed Chai** (stored separately)
- School: **Cambridge World High School**
- College: no name has been invented. Since the reference was unavailable, add the correct original college entry after verifying it.
- Profile picture: generated generic placeholder, replaceable in Admin.

No personal email, phone number, qualifications, dates, work experience, achievements, or certifications were fabricated. Add verified information before using the site or CV for real applications.

## Included

- Responsive one-page portfolio with About, Education, Skills, Services, Projects, Reviews, and Contact sections.
- Dark/light theme, mobile navigation, skills search and category filters, project filters, copy-email action, CV download, contact helper, back-to-top control, reveal animations, form validation and status messages.
- FastAPI backend with SQLAlchemy models, SQLite for local use, PostgreSQL support, editable website settings, generic content CRUD, review moderation, private contact submissions, CV content management, uploaded PDF replacement, and profile picture replacement/reset.
- Administrator login with Argon2 password hashes, signed session cookie, session expiry, CSRF token checks on admin mutations, same-origin check on login, generic authentication errors, in-memory login throttling per account and per IP, audit records, restrictive upload handling, and security headers.
- On-demand A4 PDF CV generation from editable CV content and published education/skills/projects; downloadable at `/api/public/cv.pdf`.
- Three importable n8n workflow JSON exports for contact notifications, review notifications, and administrator update alerts.
- Database schema and Alembic migration, automated tests, Dockerfile, Docker Compose PostgreSQL configuration, `.env.example`, and setup/operations documentation.

## 1. Install the requirements

Install Python 3.11 or 3.12. For local use you do not need Node.js, React, npm, or a database server; the frontend is plain HTML/CSS/JavaScript and SQLite is used by default.

### Windows PowerShell

From the extracted project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and replace `SESSION_SECRET` with a random secret. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated text into `SESSION_SECRET` in `.env`. Keep `.env` private. The included placeholder is only for setup guidance; do not publish it or use it for a public deployment.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated random value into `SESSION_SECRET` in `.env`.

## 2. First administrator login

On a brand-new database, the application automatically creates an initial administrator if no administrator account exists:

- Username: `ahmed_admin`
- Password: `AhmedPortfolio@2026!`

**Change this password immediately after your first login.** These bootstrap credentials are hardcoded for convenience and are visible to anyone who can read the source code. The password is stored in the database only as an Argon2 hash. The bootstrap account is not recreated if any administrator account already exists. For a more secure production setup, remove the bootstrap code after creating your account and use the CLI below for future administration.

To create an administrator manually, change into the backend folder and run:

```bash
cd backend
python -m app.cli create-admin
```

To reset a forgotten password, run `python -m app.cli reset-password` from `backend/`, enter the existing admin username, and provide a new password. Resetting a password invalidates existing admin sessions.

The database tables and default site settings are initialized automatically when the server starts. The original college is not prefilled because the source could not be reached; add the verified college name under **Education**.

## 3. Start the website

Remain in `backend/`:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open these local URLs:

- Public portfolio: http://127.0.0.1:8000/
- Administrator login: http://127.0.0.1:8000/admin
- Health check: http://127.0.0.1:8000/healthz
- Development API docs: http://127.0.0.1:8000/docs

Do not stop the terminal while using the local site. To stop the server, press `Ctrl+C`.

## 4. Use the Admin dashboard

Sign in at `/admin` with the username and password created in step 2. Use the left menu to edit:

- **Site settings:** Public name, separate CV name, browser title, descriptions, hero copy, about text, footer, email, WhatsApp, and location.
- **Education:** Add, edit, publish, reorder, and delete education entries. The school is prefilled as Cambridge World High School.
- **Skills / Services / Projects:** Add and edit cards, categorize them, change display order, publish/unpublish, and delete.
- **Reviews:** Review public submissions, approve or reject them. Only published and approved reviews appear publicly.
- **CV & profile image:** Edit the summary/headline/contact/experience/certification/achievement fields; download the generated PDF; upload a replacement PDF; upload a replacement profile image; restore the portrait placeholder; switch back to the generated CV.
- **Contact messages:** Read messages, change unread/read/resolved status, and delete them.
- **Audit log:** See a bounded list of recent administrator actions. Passwords, session cookies, and secret tokens are not written there.

The CV PDF is generated from its editable fields plus published education, skills, and project entries. A replacement PDF upload overrides the generated PDF until the administrator chooses **Use generated CV instead** or saves CV content. Review generated or uploaded CV details before sharing them.

## 5. Database and migrations

Local development uses SQLite at `database/portfolio.db`. The file is created after the app starts. Uploaded profile images and uploaded CV PDFs are stored in `database/uploads/` by default. Both persist when the local process restarts.

Optional Alembic migration commands (run from `backend/`):

```bash
alembic -c alembic.ini upgrade head
alembic -c alembic.ini current
```

The initial migration uses the SQLAlchemy model metadata to create the project's tables. The application also calls `create_all()` at startup to make first-time local setup simpler; for a production release, use a planned migration process and take a backup first.

## 6. n8n notifications

The app stores contact messages and pending reviews in its database whether or not n8n is configured. Notifications are optional and are **not considered connected until configured and tested in your own n8n instance**.

Three importable workflow exports are in `n8n/workflows/`:

- `contact-notification.json`
- `review-notification.json`
- `admin-update-notification.json`

For each workflow you intend to use:

1. In n8n, choose **Import from File** and select a JSON file.
2. Open the **Authenticated Webhook** node and create/select a Header Auth credential. Set the header name to `X-Portfolio-Token` and its value to exactly the same random value you put in `N8N_WEBHOOK_TOKEN` in the backend `.env`.
3. Open the **Email notification** node and add an SMTP credential. Configure a valid sending account; do not put SMTP passwords in workflow JSON.
4. Configure these environment variables for the n8n service: `PORTFOLIO_NOTIFY_FROM` and `PORTFOLIO_NOTIFY_EMAIL`.
5. Activate the workflow. Copy its **production** webhook URL into the matching backend variable: `N8N_CONTACT_WEBHOOK_URL`, `N8N_REVIEW_WEBHOOK_URL`, or `N8N_ADMIN_WEBHOOK_URL`.
6. Restart the Python backend after changing its `.env` and send a test submission. Confirm a successful workflow execution and email delivery.

Set `N8N_WEBHOOK_TOKEN` to a long random secret and keep it private. Backend delivery includes an `Idempotency-Key` header and stable event ID; downstream deduplication should use this ID if a workflow/provider may retry an email. The application retries transient webhook failures up to two times and logs only generic delivery failure metadata. It does not log message bodies or secret tokens.

## 7. Run automated tests

From the project root with the virtual environment active:

```bash
python -m pytest -q backend/tests
```

The current tests cover successful/failed admin authentication, session-protected routes, CSRF enforcement, settings updates, portfolio CRUD, review moderation, contact-message status, CV PDF output, upload validation, and page/health endpoints. The tests create their own disposable SQLite database in `backend/tests/` and a test uploads folder.

## 8. Docker / PostgreSQL option

Docker is optional. It runs the FastAPI website with PostgreSQL and persistent upload storage.

1. Copy `.env.example` to `.env`.
2. Set `POSTGRES_PASSWORD` to a unique password and `SESSION_SECRET` to a different long random secret. For a public deployment, also set `APP_ENV=production`, `COOKIE_SECURE=true`, and `ALLOWED_HOSTS` to your actual hostnames.
3. Start services from the project root:

```bash
docker compose up --build -d
```

4. Create the admin account inside the web container:

```bash
docker compose exec web python -m app.cli create-admin
```

5. Open `http://localhost:8000/` and `http://localhost:8000/admin`.

The Docker Compose example is aimed at local development. For a public deployment, terminate TLS at a properly configured reverse proxy, set secure cookies, replace every sample secret/password, restrict allowed hostnames, use persistent volumes, configure backups, and review proxy forwarding/security configuration before exposing the app.

## 9. Backups and file persistence

**SQLite local mode:** stop the app before copying `database/portfolio.db` and back up the entire `database/uploads/` directory. Keep both in the same backup set.

**PostgreSQL mode:** back up the database with `pg_dump` (or your managed provider's snapshot mechanism) and separately back up the persistent upload volume. Test restores periodically. Uploads and the database contain user-submitted/private information; restrict backup access and retention.

## 10. Troubleshooting

- **`ModuleNotFoundError`:** activate the project virtual environment and install `python -m pip install -r requirements.txt` from the project root.
- **Database path errors:** run the server and the admin CLI from `backend/`, as shown above, so the relative SQLite URL resolves consistently.
- **Cannot sign in:** ensure `python -m app.cli create-admin` completed; there is no built-in default username/password. If you forgot the password, run `python -m app.cli reset-password` from `backend/`.
- **Changes do not appear:** refresh the public page. Most content is fetched from the database; profile images use a cache-busting query when changed in Admin.
- **Image upload rejected:** use a valid JPG, PNG, or WebP file at least 64×64 px and no more than 5 MB.
- **CV upload rejected:** upload a real PDF no more than 5 MB. The endpoint verifies its PDF signature and serves it as a download.
- **n8n email is not sent:** confirm the backend webhook URL, shared token, Header Auth credential, SMTP credential, environment variables, and workflow activation; inspect the n8n execution and backend generic warning logs.
- **Production session error:** ensure `SESSION_SECRET` is a unique random value at least 32 characters long and `COOKIE_SECURE=true` when HTTPS is correctly configured.

## Limitations / verification notes

- The source reference was inaccessible from the build environment, so its exact assets, page copy, original college value, and visual differences could not be confirmed.
- This environment's automated test run verifies local app behavior; it does not provision a production PostgreSQL server, deploy n8n, configure SMTP credentials, test a public HTTPS hostname, or run a full multi-browser visual-regression suite.
- The generated CV starts as an editable template because verified personal/contact/experience details were not supplied. Complete it through the admin dashboard before using it for real applications.
