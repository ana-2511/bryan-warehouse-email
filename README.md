# Bryan Weekly Email

Every **Monday at 11:00 AM IST** GitHub Actions opens Bryan's dashboard, waits for Zoho and the
Unaccounted Item sheet to load, and sends **"Action required by Bryan for Unshipped orders and
Unaccounted inventory"** from team@virventures.com.

- **To:** Bryan  **CC:** Rupesh, Ankush, Krishna, Pankaj, Rohitash, Akash, Vijay
  (addresses at the top of `send_bryan_email.py`; one left as "" is skipped)
- **Body:** the template, with the Pending Outgoing + Ageing Unshipped picture under section 1 and the
  Ageing Range of Unaccounted Item picture under section 2, plus the link to Bryan's dashboard
- **Attachments:** Unaccounted-Inventory-Details (Excel) and Unshipped-Orders-VVI_FBM (CSV)

## Settings → Secrets and variables → Actions
Secrets: `SMTP_HOST` smtp.gmail.com · `SMTP_PORT` 587 · `SMTP_USER` team@virventures.com ·
`SMTP_PASSWORD` app password of team@virventures.com · `MAIL_FROM` optional
Variables: `BRYAN_DASHBOARD_URL` = Bryan's Netlify site address

## Test
Actions → Bryan weekly email → Run workflow, tick "Test only". Pictures appear under Artifacts.
