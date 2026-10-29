# Security and deployment notes

## Controls implemented

- Passwords are hashed with Argon2; the administrator is created through an interactive CLI.
- Session middleware uses a signed, HttpOnly session cookie with a finite maximum age and SameSite=Lax. Enable secure cookies on HTTPS deployments.
- Mutating administrator requests require a session-bound CSRF token. Login checks the `Origin` host when a browser sends an Origin header.
- Login failures are throttled by both username/IP combination and IP. The limiter is in process memory; use a shared rate limiter at the reverse proxy or Redis-backed middleware before running multiple production workers.
- Admin API endpoints validate the session and check that the user remains active. Public endpoints expose only published content and approved reviews, never contact submissions, audit logs, administrator records, or drafts.
- Content is plain text, field lengths and field types are validated, client rendering uses `textContent`, and URLs are restricted to HTTP(S); project image URLs require HTTPS.
- Profile images are limited by request size and decoded with Pillow, dimension-checked, re-encoded to WebP, and stored under a random server-generated filename. CV PDF uploads require the PDF signature, use a size cap, a random filename, and are served as downloads.
- Security headers include CSP, frame denial, MIME-sniffing protection, referrer policy, and permissions policy. Production adds HSTS and requires a non-placeholder secret plus secure cookies.
- Important admin actions are recorded in an audit table without credentials or private message content.

## Deployment checklist

- Use a unique `SESSION_SECRET` of 32+ random characters, `APP_ENV=production`, `COOKIE_SECURE=true`, and accurate `ALLOWED_HOSTS`.
- Terminate HTTPS correctly and restrict direct access to the application port where possible.
- Change the example PostgreSQL password, use managed secrets, and avoid committing `.env`.
- Use durable database and upload volumes. Back up and test recovery for both together.
- Configure n8n Header Auth and SMTP credentials in the n8n credential store, not in workflow exports.
- Use a shared rate limiter if horizontally scaling the API and configure log retention without storing PII.
- Review privacy notice, consent/retention terms, local data-protection requirements, and email delivery policies before publishing.
- Run the automated tests and a manual browser review on the actual deployment.

This package is a runnable starter project, not a substitute for a security review and operational monitoring before public production use.
