# Aviator Flask application — expanded game lobby and signal access

This project extends the supplied Flask application. It is an additive update: the existing users, balances, Aviator rounds, bets, cashouts, Nexus Pay deposit and withdrawal records, SMS password reset, and administrator approval workflow remain in the application.


## Administrator login

Set the administrator login only in the private `.env` file beside `app.py`:

```env
ADMIN_USERNAME=your-admin-username
ADMIN_PASSWORD=use-a-unique-password-at-least-12-characters-long
ADMIN_PHONE=2547XXXXXXXX
```

Copy `.env.example` to `.env` and replace the example values before starting the app.
The app creates or synchronizes this administrator account at startup and stores only
a password hash in SQLite. Do not commit `.env` to GitHub or include it in the ZIP.
Sign in through `/login`; an administrator is redirected to `/admin`. The admin
dashboard displays the live current round and next round number, but never reveals
the next round's future crash result.

## Paid signal access

After Nexus Pay confirms the exact package amount through the configured signed
webhook, the order changes to `PAYMENT_VERIFIED` and appears in the admin approval
queue. The customer sees the signal feed only after an administrator approves the
verified order; access then lasts for the purchased 5 or 10 minutes. This is the customer signal page, not the administrator
dashboard; customer accounts must never receive admin privileges.

## Added in this version

- **Player lobby:** New registrations and customer logins land on `/lobby`. The lobby shows the username and available balance.
- **Existing Aviator game:** The existing Aviator game is now at `/aviator`. Its game engine and bet/cashout APIs are retained. The game header links back to the lobby and signal center.
- **Game catalogue:** Aviator is enabled. Mines, Plinko, Dice, Spaceman, JetX and Lucky Wheel are displayed as *Coming soon*. They are catalogue entries only; they do not accept bets until their individual game engines, rules and payment controls are implemented and tested.
- **Paid Aviator signal access:**
  - 5 minutes: **KES 200**
  - 10 minutes: **KES 400**
  - Customer chooses a package and confirms the M-Pesa prompt. The app calls the existing Nexus Pay STK Push endpoint.
  - Signal access does **not** activate just because the STK prompt was initiated. It activates only after the configured, signature-verified Nexus `payment.completed` webhook confirms the matching reference and exact amount. A missing amount is rejected.
  - The paid access timer begins when an administrator approves the payment-verified order and expires after the selected 5 or 10 minutes.
- **Signal administration:** The `/admin` dashboard includes a payment-verified signal approval queue, an automatically generated list of the next 10 round estimates, signal payment history, confirmed signal sales and active subscription count. The admin must verify the transaction in Nexus Pay before approving. A successful provider webhook does not by itself grant customer signal access. After payment approval, the system anchors the customer package to the next round and generates the exact number of sample entries. A 5-minute package receives rounds 1–5 of its access window; a 10-minute package receives 10 rounds. The admin dashboard shows the next 10 generated entries.
- **Security:** Signal purchase POST requests require a session CSRF token. Signal payment references are separate from player wallet deposits, so signal purchases do not increase or deduct the betting wallet balance. Repeated webhooks do not extend an already activated package.
- **Risk notice:** The signal page clearly explains that Aviator results are random and that administrator estimates are not guaranteed predictions. The software does not claim that signals can guarantee winnings. Signals are manually published by an administrator; this project does not contain a proven algorithm that can predict future crash points.

## Windows / VS Code setup

1. Extract the ZIP and open the extracted folder in VS Code.
2. Create a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `py -m pip` commands without activating the environment.
3. Install dependencies:
   ```powershell
   py -m pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and set a long random `FLASK_SECRET_KEY`, the Africa's Talking values, and the Nexus Pay API key. Keep `.env` private.
5. Point `DB_NAME` to your existing SQLite database. Example:
   ```env
   DB_NAME=./data/aviator_live.db
   ```
   Copy your existing database to that path if needed. **Do not replace your old database with a blank one** if you need your previous accounts, balances, bets, rounds, deposits and withdrawals.
6. Configure `NEXUS_WEBHOOK_SECRET` to the signing secret provided by Nexus Pay. In the Nexus Pay dashboard, configure the webhook URL as:
   ```text
   https://YOUR-DOMAIN/api/nexus/webhook
   ```
   Keep the webhook secret identical between Nexus and `.env`. The same verified webhook endpoint processes both existing wallet transactions and signal purchases.
7. Configure your initial administrator using `ADMIN_USERNAME`, `ADMIN_PASSWORD` (at least 12 characters) and optionally `ADMIN_PHONE` before the first database initialization. If an admin account already exists, these settings do not overwrite it.
8. Start the app:
   ```powershell
   py app.py
   ```
9. Open `http://127.0.0.1:5000`.

## Customer journey

1. Customer registers or logs in.
2. Customer lands on the game lobby.
3. **Play Aviator** opens the existing Aviator game at `/aviator`.
4. **Aviator Signals** opens `/signals`.
5. Customer selects the 5-minute or 10-minute package and confirms the M-Pesa prompt.
6. Nexus Pay sends a signed payment webhook. Only after successful signature, reference and amount verification does the app activate access.
7. The customer sees only the generated round entries included in the approved package, while the subscription timer remains active.

## Administrator journey

1. Log in using the administrator account; admins are redirected to `/admin`.
2. In **Aviator signal management**, publish a round/reference, signal time, estimated multiplier, confidence label and optional note.
3. Remove an outdated signal when necessary.
4. Review signal payment orders. A signed successful payment webhook moves an order to `PAYMENT_VERIFIED`; independently verify the reference in Nexus Pay and click **Approve signal access**. The access period starts when you approve it. Orders can also be `PENDING`, `PAID` or `FAILED`.

## Existing data and hosting

- The new `signal_orders` and `aviator_signals` tables are created automatically using additive `CREATE TABLE IF NOT EXISTS` migrations. Existing application tables are not dropped or recreated.
- Keep the database file on persistent storage. On Render, configure a persistent disk/volume and set `DB_NAME` to its mounted path. An ephemeral filesystem can lose SQLite data after redeploy.
- Keep `FLASK_SECRET_KEY` stable. Changing it invalidates existing signed browser sessions.
- Use `SESSION_COOKIE_SECURE=1` when serving over HTTPS.
- The previous SMS OTP password reset still requires valid Africa's Talking credentials and an eligible sender configuration.

## Important testing and operational notes

- The ZIP contains application source and configuration examples, not your private production SQLite database or provider secrets.
- Nexus payment initiation, callbacks and settlement must be tested against the provider's approved environment. A successful STK prompt response is **not** proof of payment.
- Signal access depends on a properly configured signed Nexus webhook and a separate administrator approval. If the webhook is not configured or cannot be verified, the order remains pending and signal access is not granted. Unverified wallet deposits cannot be approved or credited; only `PAYMENT_VERIFIED` deposits can be approved by an administrator.
- The additional game tiles are placeholders only. Do not advertise Mines, Plinko, Dice, Spaceman, JetX or Lucky Wheel as playable until their independent game logic, odds, wallet handling, audits and testing have been completed.
- This project does not certify gambling licensing, legal compliance, payment settlement or guaranteed outcomes. Confirm applicable Kenyan legal and regulatory requirements before offering real-money play.


## Admin-only access and mobile navigation

- Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`. Use a unique password of at least 12 characters. The application creates/synchronizes this administrator account on startup; do not register a customer account with the admin username.
- Admin access is checked against the database role on protected routes. Customer accounts cannot open `/admin`, `/admin/round-status`, deposit approvals, signal approvals, user records or admin audit logs. A customer who buys signal access remains a customer and only receives the paid signal page and the public next-round number.
- On phones, the Aviator game header uses a hamburger control to hide navigation/actions while keeping the customer username and wallet balance visible. The admin dashboard has its own collapsible navigation.
- The admin round monitor displays the upcoming round number and timing only. It does not expose future crash outcomes.


## Automatic round estimates (important limitation)

- The application automatically creates entries for the next 10 internal round IDs and stores one entry per round. The 5-minute package is assigned 5 upcoming round IDs; the 10-minute package is assigned 10.
- The entries contain synthetic sample multipliers to demonstrate the round-feed workflow. They are labeled `SIMULATED` and explicitly disclose that they are not forecasts. They are not calculated from, and cannot reveal, future crash outcomes.
- Aviator crash outcomes are random. Do not market the generated values as reliable predictions or guaranteed returns.
- The original SQLite database is intentionally not bundled in the updated ZIP. Keep your existing database and set `DB_NAME` to its path; the app applies additive schema migrations at startup.
