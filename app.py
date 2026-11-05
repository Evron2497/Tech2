# import os
# import time
# import random
# import math
# import sqlite3
# import hashlib
# import hmac
# import json
# import secrets
# import threading
# import re
# from datetime import timedelta
# from datetime import datetime

# import requests
# from dotenv import load_dotenv

# from werkzeug.security import generate_password_hash, check_password_hash

# from flask import (
#     Flask,
#     request,
#     jsonify,
#     session,
#     redirect,
#     render_template_string,
# )

# # ============================================================
# # CONFIGURATION
# # ============================================================

# # Load .env from the same directory as this app.py.
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# ENV_FILE = os.path.join(BASE_DIR, ".env")
# load_dotenv(ENV_FILE)

# # Database: use an absolute path when DB_NAME is relative so the app
# # always opens the same database regardless of the working directory.
# _db_name = os.getenv("DB_NAME", "aviator_live.db").strip()
# DB_NAME = (
#     _db_name
#     if os.path.isabs(_db_name)
#     else os.path.join(BASE_DIR, _db_name)
# )

# BETTING_WINDOW = 7.0
# MIN_WITHDRAWAL = 1000.0
# MAX_WITHDRAWAL = 250000.0
# CRASH_DISPLAY_TIME = 2.5
# STARTING_BALANCE = 0.0

# # ============================================================
# # NEXUS PAY CONFIGURATION
# # ============================================================

# # Keep all Nexus credentials in .env. Never hard-code them in app.py.
# NEXUS_PAY_PUBLIC_KEY = os.getenv("NEXUS_PAY_PUBLIC_KEY", "").strip()
# NEXUS_PAY_SECRET_KEY = os.getenv("NEXUS_PAY_SECRET_KEY", "").strip()
# NEXUS_PAY_API_KEY = os.getenv("NEXUS_PAY_API_KEY", "").strip()

# NEXUS_PAY_BASE_URL = os.getenv(
#     "NEXUS_PAY_BASE_URL",
#     "https://makamescopay.com"
# ).strip().rstrip("/")

# try:
#     NEXUS_PAY_TIMEOUT = int(
#         os.getenv("NEXUS_PAY_TIMEOUT", "30")
#     )
# except (TypeError, ValueError):
#     NEXUS_PAY_TIMEOUT = 30

# if NEXUS_PAY_TIMEOUT < 5:
#     NEXUS_PAY_TIMEOUT = 5

# # # Optional callback secret. Leave blank until Nexus provides a webhook
# # # signing/verification secret and its exact callback specification.
# # NEXUS_CALLBACK_SECRET = os.getenv("NEXUS_CALLBACK_SECRET", "").strip()
# # NEXUS_WEBHOOK_SECRET = os.getenv("NEXUS_WEBHOOK_SECRET", "").strip()
# # NEXUS_WEBHOOK_PATH = os.getenv("NEXUS_WEBHOOK_PATH", "/api/nexus/webhook").strip() or "/api/nexus/webhook"
# # NEXUS_WEBHOOK_URL = os.getenv("NEXUS_WEBHOOK_URL", "").strip()

# # Africa's Talking SMS OTP configuration. Obtain these from the AT dashboard.
# AT_USERNAME = os.getenv("AT_USERNAME", "").strip()
# AT_API_KEY = os.getenv("AT_API_KEY", "").strip()
# AT_SENDER_ID = os.getenv("AT_SENDER_ID", "").strip()
# OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "5"))
# NEXUS_CALLBACK_SECRET = os.getenv("NEXUS_CALLBACK_SECRET", "").strip()
# NEXUS_WEBHOOK_SECRET = os.getenv("NEXUS_WEBHOOK_SECRET", "").strip()
# NEXUS_WEBHOOK_PATH = os.getenv(
#     "NEXUS_WEBHOOK_PATH",
#     "/api/nexus/webhook"
# ).strip() or "/api/nexus/webhook"

# NEXUS_WEBHOOK_URL = os.getenv("NEXUS_WEBHOOK_URL", "").strip()

# # Africa's Talking SMS OTP configuration. Obtain these from the AT dashboard.
# AT_USERNAME = os.getenv("AT_USERNAME", "").strip()
# AT_API_KEY = os.getenv("AT_API_KEY", "").strip()
# AT_SENDER_ID = os.getenv("AT_SENDER_ID", "").strip()
# OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "5"))
# # # ============================================================


# app = Flask(__name__)

# FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "").strip()

# # Dedicated administrator credentials are configured in .env.
# ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
# ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# if not FLASK_SECRET_KEY:
#     # Development fallback only. Production should always provide
#     # FLASK_SECRET_KEY in .env or the process environment.
#     FLASK_SECRET_KEY = secrets.token_hex(32)
#     print("WARNING: FLASK_SECRET_KEY is not configured; using a temporary development key.")

# app.secret_key = FLASK_SECRET_KEY

# # Persistent browser session: sleeping the computer or closing the browser
# # will not immediately discard the login. SQLite remains the source of truth
# # for balances, bets, rounds, deposits and withdrawals.
# app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
# app.config["SESSION_REFRESH_EACH_REQUEST"] = True
# app.config["SESSION_COOKIE_HTTPONLY"] = True
# app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# app.config["SESSION_COOKIE_SECURE"] = (
#     os.getenv("SESSION_COOKIE_SECURE", "0").strip() == "1"
# )

# GAME_LOCK = threading.RLock()

# # ============================================================
# # DATABASE
# # ============================================================

# def get_db():
#     # Create the configured database directory when deploying to a fresh folder.
#     os.makedirs(os.path.dirname(DB_NAME) or ".", exist_ok=True)
#     conn = sqlite3.connect(
#         DB_NAME,
#         timeout=10,
#         check_same_thread=False
#     )
#     conn.row_factory = sqlite3.Row
#     return conn


# def hash_password(password):
#     """Use Werkzeug's salted PBKDF2 password hash for new/updated passwords."""
#     return generate_password_hash(password, method="pbkdf2:sha256:600000")


# def verify_password(password, hashed):
#     """Verify modern hashes and transparently support legacy SHA-256 rows."""
#     if not hashed:
#         return False
#     if re.fullmatch(r"[0-9a-fA-F]{64}", str(hashed)):
#         return secrets.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), str(hashed))
#     try:
#         return check_password_hash(hashed, password)
#     except (ValueError, TypeError):
#         return False


# def init_db():
#     conn = get_db()

#     try:
#         conn.execute("PRAGMA journal_mode=WAL")

#         conn.execute("""
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT UNIQUE NOT NULL,
#                 password TEXT NOT NULL,
#                 phone_number TEXT UNIQUE NOT NULL,
#                 balance REAL NOT NULL DEFAULT 0.0,
#                 role TEXT NOT NULL DEFAULT 'USER',
#                 created_at TEXT NOT NULL
#             )
#         """)

#         conn.execute("""
#             CREATE TABLE IF NOT EXISTS rounds (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 crash_point REAL NOT NULL,
#                 started_at TEXT NOT NULL,
#                 ended_at TEXT
#             )
#         """)

#         conn.execute("""
#             CREATE TABLE IF NOT EXISTS bets (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT NOT NULL,
#                 round_id INTEGER NOT NULL,
#                 bet_number INTEGER NOT NULL,
#                 amount REAL NOT NULL,
#                 auto_cashout REAL,
#                 cashout_multiplier REAL,
#                 winnings REAL NOT NULL DEFAULT 0,
#                 status TEXT NOT NULL,
#                 created_at TEXT NOT NULL,

#                 UNIQUE(username, round_id, bet_number)
#             )
#         """)

#         # Nexus Pay deposits.
#         conn.execute("""
#             CREATE TABLE IF NOT EXISTS nexus_transactions (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,

#                 username TEXT NOT NULL,
#                 phone_number TEXT NOT NULL,

#                 amount REAL NOT NULL,

#                 reference TEXT UNIQUE NOT NULL,

#                 provider_transaction_id TEXT,

#                 status TEXT NOT NULL DEFAULT 'PENDING',

#                 provider_message TEXT,

#                 created_at TEXT NOT NULL,
#                 updated_at TEXT NOT NULL,

#                 credited_at TEXT
#             )
#         """)

#         # Withdrawal records.
#         #
#         # The current version records withdrawals instead of pretending
#         # that money has actually been sent. A real Nexus B2C/disbursement
#         # implementation should be connected here using the provider's
#         # documented B2C endpoint.
#         conn.execute("""
#             CREATE TABLE IF NOT EXISTS withdrawals (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,

#                 username TEXT NOT NULL,
#                 phone_number TEXT NOT NULL,

#                 amount REAL NOT NULL,

#                 status TEXT NOT NULL DEFAULT 'PENDING',

#                 provider_transaction_id TEXT,
#                 provider_message TEXT,

#                 created_at TEXT NOT NULL,
#                 updated_at TEXT NOT NULL,

#                 completed_at TEXT
#             )
#         """)

#         # Migrate older databases used before Nexus webhook support.
#         # SQLite ignores this only when the column already exists.
#         withdrawal_columns = {
#             row["name"]
#             for row in conn.execute("PRAGMA table_info(withdrawals)").fetchall()
#         }

#         if "reference" not in withdrawal_columns:
#             conn.execute("ALTER TABLE withdrawals ADD COLUMN reference TEXT")

#         if "provider_transaction_id" not in withdrawal_columns:
#             conn.execute("ALTER TABLE withdrawals ADD COLUMN provider_transaction_id TEXT")

#         if "provider_message" not in withdrawal_columns:
#             conn.execute("ALTER TABLE withdrawals ADD COLUMN provider_message TEXT")


#         # Additive migrations: preserve existing users, rounds, bets, transactions and withdrawals.
#         user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
#         if "last_seen_at" not in user_columns:
#             conn.execute("ALTER TABLE users ADD COLUMN last_seen_at TEXT")
#         if "is_active" not in user_columns:
#             conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

#         conn.execute("""CREATE TABLE IF NOT EXISTS password_reset_otps (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT NOT NULL,
#             otp_hash TEXT NOT NULL,
#             expires_at TEXT NOT NULL,
#             attempts INTEGER NOT NULL DEFAULT 0,
#             used_at TEXT,
#             created_at TEXT NOT NULL,
#             request_ip TEXT
#         )""")
#         conn.execute("""CREATE TABLE IF NOT EXISTS admin_audit_logs (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             admin_username TEXT NOT NULL,
#             action TEXT NOT NULL,
#             target_username TEXT,
#             details TEXT,
#             ip_address TEXT,
#             created_at TEXT NOT NULL
#         )""")

#         # Add explicit approval metadata to existing Nexus deposit rows.
#         tx_columns = {row["name"] for row in conn.execute("PRAGMA table_info(nexus_transactions)").fetchall()}
#         if "approved_by" not in tx_columns:
#             conn.execute("ALTER TABLE nexus_transactions ADD COLUMN approved_by TEXT")
#         if "approved_at" not in tx_columns:
#             conn.execute("ALTER TABLE nexus_transactions ADD COLUMN approved_at TEXT")
#         if "verified_at" not in tx_columns:
#             conn.execute("ALTER TABLE nexus_transactions ADD COLUMN verified_at TEXT")

#         # Paid Aviator signal subscriptions and admin-published signal feed.
#         # These are additive tables; existing player/game/payment records are untouched.
#         conn.execute("""CREATE TABLE IF NOT EXISTS signal_orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT NOT NULL,
#             phone_number TEXT NOT NULL,
#             plan_minutes INTEGER NOT NULL CHECK(plan_minutes IN (5,10)),
#             amount REAL NOT NULL,
#             reference TEXT UNIQUE NOT NULL,
#             provider_transaction_id TEXT,
#             status TEXT NOT NULL DEFAULT 'PENDING',
#             provider_message TEXT,
#             created_at TEXT NOT NULL,
#             updated_at TEXT NOT NULL,
#             paid_at TEXT,
#             expires_at TEXT
#         )""")
#         conn.execute("""CREATE TABLE IF NOT EXISTS aviator_signals (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             admin_username TEXT NOT NULL,
#             round_label TEXT NOT NULL,
#             signal_time TEXT NOT NULL,
#             predicted_multiplier REAL NOT NULL,
#             confidence TEXT NOT NULL DEFAULT 'Unrated',
#             notes TEXT,
#             status TEXT NOT NULL DEFAULT 'PUBLISHED',
#             created_at TEXT NOT NULL
#         )""")
#         # Generated round mapping and round entitlements are additive migrations.
#         signal_cols = {row["name"] for row in conn.execute("PRAGMA table_info(aviator_signals)").fetchall()}
#         if "round_number" not in signal_cols:
#             conn.execute("ALTER TABLE aviator_signals ADD COLUMN round_number INTEGER")
#         conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_aviator_signals_round_number ON aviator_signals(round_number) WHERE round_number IS NOT NULL")
#         order_cols = {row["name"] for row in conn.execute("PRAGMA table_info(signal_orders)").fetchall()}
#         if "start_round" not in order_cols:
#             conn.execute("ALTER TABLE signal_orders ADD COLUMN start_round INTEGER")
#         if "end_round" not in order_cols:
#             conn.execute("ALTER TABLE signal_orders ADD COLUMN end_round INTEGER")

#         admin_username = ADMIN_USERNAME
#         admin_password = ADMIN_PASSWORD
#         if admin_username and admin_password and len(admin_password) >= 12:
#             # The .env administrator account is authoritative. Create it on
#             # first boot, or promote/synchronize the same username if it was
#             # previously created as a customer account. Only a password hash
#             # is stored in SQLite; the plaintext remains in the private .env.
#             admin = conn.execute("SELECT id FROM users WHERE username=?", (admin_username,)).fetchone()
#             admin_hash = hash_password(admin_password)
#             if not admin:
#                 admin_phone = os.getenv("ADMIN_PHONE", "254700000000").strip()
#                 conn.execute("""INSERT INTO users (username,password,phone_number,balance,role,created_at)
#                     VALUES (?,?,?,?,?,?)""", (admin_username, admin_hash, admin_phone, 0.0, "ADMIN", datetime.now().isoformat()))
#             else:
#                 conn.execute("UPDATE users SET password=?, role='ADMIN', is_active=1 WHERE username=?", (admin_hash, admin_username))

#         conn.commit()

#     finally:
#         conn.close()


# # ============================================================
# # GAME ENGINE
# # ============================================================

# def generate_crash_point():
#     value = random.random()

#     if value < 0.05:
#         return 1.00

#     if value < 0.25:
#         return round(
#             random.uniform(1.01, 1.50),
#             2
#         )

#     if value < 0.65:
#         return round(
#             random.uniform(1.51, 3.50),
#             2
#         )

#     if value < 0.90:
#         return round(
#             random.uniform(3.51, 15.00),
#             2
#         )

#     return round(
#         random.uniform(15.01, 150.00),
#         2
#     )


# def calculate_multiplier(elapsed):
#     """Calculate an accelerating crash-game multiplier.

#     The multiplier grows smoothly and progressively faster as the round
#     continues. Keep this deterministic for a given elapsed time so server
#     state, bets, and cash-outs all use the same value.
#     """
#     elapsed = max(0.0, float(elapsed))
#     multiplier = math.exp(0.115 * elapsed)
#     return round(max(multiplier, 1.0), 2)


# GAME = {
#     "round_id": None,
#     "crash_point": None,

#     "next_crash_point_1": generate_crash_point(),
#     "next_crash_point_2": generate_crash_point(),

#     "status": "BETTING",

#     "betting_start": None,
#     "run_start": None,

#     "current_multiplier": 1.00,

#     "crash_time": None,

#     "bot_bets": []
# }


# FAKE_USERS = [
#     "***1",
#     "***2",
#     "***3",
#     "***4",
#     "***5",
#     "***6",
#     "***7",
#     "***8",
#     "***9",
#     "alex***",
#     "brian***",
#     "coll***",
#     "david***",
#     "eric***",
#     "frank***",
#     "grace***",
#     "harr***",
#     "ian***",
#     "john***",
#     "kevin***",
#     "lucy***",
#     "mike***",
#     "nick***",
#     "oliver***",
#     "peter***",
#     "queen***",
#     "ray***",
#     "sam***",
#     "tom***",
#     "victor***",
#     "wendy***",
#     "kelv***",
#     "sylv***",
#     "mash***",
#     "kip***",
#     "wanj***",
#     "njeri***",
#     "ochi***",
#     "otien***",
#     "maina***",
#     "chep***",
#     "kiprot***",
#     "kibet***",
#     "baras***"
# ]


# def generate_bot_bets():
#     bets = []

#     count = random.randint(35, 65)

#     selected_users = random.choices(
#         FAKE_USERS,
#         k=count
#     )

#     for i, user in enumerate(selected_users):
#         masked = (
#             user[:3]
#             + "***"
#             + str(random.randint(0, 9))
#         )

#         amount = round(
#             random.choice([
#                 20,
#                 50,
#                 100,
#                 200,
#                 500,
#                 1000,
#                 2500,
#                 5000,
#                 10000
#             ]),
#             2
#         )

#         target_cashout = (
#             round(
#                 random.uniform(1.10, 6.00),
#                 2
#             )
#             if random.random() > 0.20
#             else None
#         )

#         bets.append({
#             "id": f"bot_{i}",
#             "username": masked,
#             "amount": amount,
#             "auto_cashout": target_cashout,
#             "status": "ACTIVE",
#             "cashout_multiplier": None,
#             "winnings": 0.0
#         })

#     return bets


# def create_round_locked():
#     crash_point = GAME["next_crash_point_1"]

#     GAME["next_crash_point_1"] = (
#         GAME["next_crash_point_2"]
#     )

#     GAME["next_crash_point_2"] = (
#         generate_crash_point()
#     )

#     now = datetime.now().isoformat()

#     conn = get_db()

#     try:
#         cursor = conn.execute(
#             """
#             INSERT INTO rounds
#             (
#                 crash_point,
#                 started_at
#             )
#             VALUES (?, ?)
#             """,
#             (
#                 crash_point,
#                 now
#             )
#         )

#         round_id = cursor.lastrowid

#         conn.commit()

#     finally:
#         conn.close()

#     GAME["round_id"] = round_id
#     GAME["crash_point"] = crash_point
#     GAME["status"] = "BETTING"
#     GAME["betting_start"] = time.time()
#     GAME["run_start"] = None
#     GAME["current_multiplier"] = 1.00
#     GAME["crash_time"] = None
#     GAME["bot_bets"] = generate_bot_bets()


# def initialize_game():
#     with GAME_LOCK:
#         if GAME["round_id"] is None:
#             create_round_locked()


# def start_running_locked():
#     if GAME["status"] != "BETTING":
#         return

#     GAME["status"] = "RUNNING"
#     GAME["run_start"] = time.time()
#     GAME["current_multiplier"] = 1.00


# def process_auto_cashouts_locked():
#     if GAME["status"] != "RUNNING":
#         return

#     multiplier = GAME["current_multiplier"]
#     crash_point = GAME["crash_point"]
#     round_id = GAME["round_id"]

#     if multiplier >= crash_point:
#         return

#     # --------------------------------------------------------
#     # BOT AUTO CASHOUTS
#     # --------------------------------------------------------

#     for bot in GAME["bot_bets"]:
#         if (
#             bot["status"] == "ACTIVE"
#             and bot["auto_cashout"] is not None
#             and bot["auto_cashout"] <= multiplier
#             and bot["auto_cashout"] < crash_point
#         ):
#             bot["status"] = "WON"

#             bot["cashout_multiplier"] = (
#                 bot["auto_cashout"]
#             )

#             bot["winnings"] = round(
#                 bot["amount"]
#                 * bot["auto_cashout"],
#                 2
#             )

#     # Some bots manually cash out.
#     for bot in GAME["bot_bets"]:
#         if (
#             bot["status"] == "ACTIVE"
#             and bot["auto_cashout"] is None
#             and multiplier > 1.30
#         ):
#             if random.random() < 0.05:
#                 bot["status"] = "WON"

#                 bot["cashout_multiplier"] = (
#                     multiplier
#                 )

#                 bot["winnings"] = round(
#                     bot["amount"] * multiplier,
#                     2
#                 )

#     # --------------------------------------------------------
#     # REAL USER AUTO CASHOUTS
#     # --------------------------------------------------------

#     conn = get_db()

#     try:
#         bets = conn.execute(
#             """
#             SELECT *
#             FROM bets
#             WHERE round_id = ?
#               AND status = 'ACTIVE'
#               AND auto_cashout IS NOT NULL
#             """,
#             (round_id,)
#         ).fetchall()

#         for bet in bets:
#             target = float(
#                 bet["auto_cashout"]
#             )

#             if (
#                 target <= multiplier
#                 and target < crash_point
#             ):
#                 winnings = round(
#                     float(bet["amount"])
#                     * target,
#                     2
#                 )

#                 cursor = conn.execute(
#                     """
#                     UPDATE bets

#                     SET
#                         status='WON',
#                         cashout_multiplier=?,
#                         winnings=?

#                     WHERE id=?
#                       AND status='ACTIVE'
#                     """,
#                     (
#                         target,
#                         winnings,
#                         bet["id"]
#                     )
#                 )

#                 if cursor.rowcount == 1:
#                     conn.execute(
#                         """
#                         UPDATE users

#                         SET balance =
#                             balance + ?

#                         WHERE username=?
#                         """,
#                         (
#                             winnings,
#                             bet["username"]
#                         )
#                     )

#         conn.commit()

#     finally:
#         conn.close()


# def crash_round_locked():
#     if GAME["status"] == "CRASHED":
#         return

#     GAME["status"] = "CRASHED"

#     GAME["current_multiplier"] = (
#         GAME["crash_point"]
#     )

#     GAME["crash_time"] = time.time()

#     for bot in GAME["bot_bets"]:
#         if bot["status"] == "ACTIVE":
#             bot["status"] = "LOST"

#     conn = get_db()

#     try:
#         conn.execute(
#             """
#             UPDATE bets

#             SET status='LOST'

#             WHERE round_id=?
#               AND status='ACTIVE'
#             """,
#             (GAME["round_id"],)
#         )

#         conn.execute(
#             """
#             UPDATE rounds

#             SET ended_at=?

#             WHERE id=?
#             """,
#             (
#                 datetime.now().isoformat(),
#                 GAME["round_id"]
#             )
#         )

#         conn.commit()

#     finally:
#         conn.close()


# def tick_game_locked():
#     initialize_game()

#     now = time.time()

#     if GAME["status"] == "BETTING":

#         elapsed = (
#             now
#             - GAME["betting_start"]
#         )

#         GAME["current_multiplier"] = 1.00

#         if elapsed >= BETTING_WINDOW:
#             start_running_locked()

#     elif GAME["status"] == "RUNNING":

#         elapsed = (
#             now
#             - GAME["run_start"]
#         )

#         multiplier = calculate_multiplier(
#             elapsed
#         )

#         GAME["current_multiplier"] = (
#             multiplier
#         )

#         process_auto_cashouts_locked()

#         if multiplier >= GAME["crash_point"]:
#             crash_round_locked()

#     elif GAME["status"] == "CRASHED":

#         if (
#             GAME["crash_time"] is not None
#             and (
#                 now
#                 - GAME["crash_time"]
#             ) >= CRASH_DISPLAY_TIME
#         ):
#             create_round_locked()


# def game_loop():
#     while True:

#         try:
#             with GAME_LOCK:
#                 tick_game_locked()

#         except Exception as exc:
#             print(
#                 "Game engine error:",
#                 repr(exc)
#             )

#         time.sleep(0.04)


# # ============================================================
# # USER HELPERS
# # ============================================================

# def get_user(username):
#     conn = get_db()

#     try:
#         return conn.execute(
#             """
#             SELECT
#                 username,
#                 phone_number,
#                 balance,
#                 role

#             FROM users

#             WHERE username=?
#             """,
#             (username,)
#         ).fetchone()

#     finally:
#         conn.close()


# def normalize_mpesa_phone(phone):
#     """
#     Convert common Kenyan formats to:

#         2547XXXXXXXX
#         2541XXXXXXXX
#     """

#     value = str(
#         phone or ""
#     ).strip()

#     value = (
#         value
#         .replace(" ", "")
#         .replace("-", "")
#         .replace("(", "")
#         .replace(")", "")
#     )

#     if value.startswith("+"):
#         value = value[1:]

#     if (
#         value.startswith("0")
#         and len(value) == 10
#     ):
#         value = "254" + value[1:]

#     elif (
#         (
#             value.startswith("7")
#             or value.startswith("1")
#         )
#         and len(value) == 9
#     ):
#         value = "254" + value

#     valid = (
#         len(value) == 12
#         and value.startswith("254")
#         and value[3] in ("7", "1")
#         and value.isdigit()
#     )

#     if not valid:
#         raise ValueError(
#             "Enter a valid Kenyan M-Pesa number, "
#             "for example 0712345678."
#         )

#     return value


# def safe_float(value, default=None):
#     try:
#         number = float(value)

#         if number != number:
#             return default

#         return number

#     except (
#         TypeError,
#         ValueError
#     ):
#         return default


# def make_nexus_reference(prefix, username):
#     return (
#         f"{prefix}-{username[:8]}-"
#         f"{int(time.time())}-"
#         f"{secrets.token_hex(3).upper()}"
#     )


# # ============================================================
# # NEXUS PAY
# # ============================================================

# def nexus_headers():
#     if not NEXUS_PAY_API_KEY:
#         raise RuntimeError(
#             "NEXUS_PAY_API_KEY is not configured. Add it to .env."
#         )

#     return {
#         "X-API-Key": NEXUS_PAY_API_KEY,
#         "Content-Type": "application/json",
#         "Accept": "application/json"
#     }


# def nexus_stk_push(
#     phone_number,
#     amount,
#     username
# ):
#     """
#     Send an M-Pesa STK Push through Nexus Pay.

#     Nexus Pay published request:

#         POST /api/payments/stkpush

#     JSON:

#         {
#             "phoneNumber": "254712345678",
#             "amount": 500,
#             "accountReference": "ORDER-001",
#             "transactionDesc": "Payment for order"
#         }
#     """

#     phone = normalize_mpesa_phone(
#         phone_number
#     )

#     amount = safe_float(amount)

#     if amount is None or amount < 5:
#         raise ValueError(
#             "Minimum deposit is KES 5."
#         )

#     if amount != round(amount):
#         raise ValueError(
#             "Deposit amount must be a whole KES amount."
#         )

#     amount = int(round(amount))

#     # Short unique reference.
#     reference = make_nexus_reference("AV", username)

#     payload = {
#         "phoneNumber": phone,
#         "amount": amount,
#         "accountReference": reference,
#         "transactionDesc": "Aviator deposit"
#     }

#     url = (
#         f"{NEXUS_PAY_BASE_URL}"
#         "/api/payments/stkpush"
#     )

#     response = requests.post(
#         url,
#         json=payload,
#         headers=nexus_headers(),
#         timeout=NEXUS_PAY_TIMEOUT
#     )

#     response.raise_for_status()

#     try:
#         data = response.json()
#     except ValueError:
#         raise RuntimeError(
#             "Nexus Pay returned an invalid response."
#         )

#     # Keep the entire provider response useful,
#     # while trying several common identifiers.
#     provider_transaction_id = (
#         data.get("transactionId")
#         or data.get("transaction_id")
#         or data.get("checkoutRequestId")
#         or data.get("checkout_request_id")
#         or data.get("id")
#     )

#     # Some APIs return success as a boolean,
#     # others return a status/code.
#     success = data.get("success")

#     if success is False:
#         message = (
#             data.get("message")
#             or data.get("error")
#             or data.get("description")
#             or "Nexus Pay rejected the payment request."
#         )

#         raise RuntimeError(str(message))

#     status_value = str(
#         data.get("status", "")
#     ).upper()

#     if status_value in (
#         "FAILED",
#         "FAILURE",
#         "ERROR",
#         "REJECTED"
#     ):
#         message = (
#             data.get("message")
#             or data.get("error")
#             or data.get("description")
#             or "Nexus Pay rejected the payment request."
#         )

#         raise RuntimeError(str(message))

#     now = datetime.now().isoformat()

#     conn = get_db()

#     try:
#         conn.execute(
#             """
#             INSERT INTO nexus_transactions
#             (
#                 username,
#                 phone_number,
#                 amount,
#                 reference,
#                 provider_transaction_id,
#                 status,
#                 provider_message,
#                 created_at,
#                 updated_at
#             )

#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 username,
#                 phone,
#                 float(amount),
#                 reference,
#                 (
#                     str(provider_transaction_id)
#                     if provider_transaction_id
#                     else None
#                 ),
#                 "PENDING",
#                 (
#                     data.get("message")
#                     or data.get("description")
#                     or "STK Push initiated."
#                 ),
#                 now,
#                 now
#             )
#         )

#         conn.commit()

#     finally:
#         conn.close()

#     return {
#         "reference": reference,
#         "provider_transaction_id":
#             provider_transaction_id,
#         "message":
#             data.get("message")
#             or data.get("description")
#             or "M-Pesa prompt sent.",
#         "provider_response": data
#     }


# # ============================================================
# # NEXUS TRANSACTION HELPERS
# # ============================================================

# def get_nexus_transaction(
#     reference,
#     username
# ):
#     conn = get_db()

#     try:
#         return conn.execute(
#             """
#             SELECT *

#             FROM nexus_transactions

#             WHERE reference=?
#               AND username=?
#             """,
#             (
#                 reference,
#                 username
#             )
#         ).fetchone()

#     finally:
#         conn.close()


# def credit_nexus_transaction(
#     reference
# ):
#     """
#     IMPORTANT:

#     This function is intentionally not exposed as a public
#     "mark paid" endpoint.

#     It can be called only after your provider's documented
#     confirmation mechanism has verified the payment.

#     It is idempotent: the same transaction cannot be credited twice.
#     """

#     conn = get_db()

#     try:
#         conn.execute("BEGIN IMMEDIATE")

#         tx = conn.execute(
#             """
#             SELECT *

#             FROM nexus_transactions

#             WHERE reference=?
#             """,
#             (reference,)
#         ).fetchone()

#         if not tx:
#             conn.rollback()
#             return False, "Transaction not found."

#         if tx["status"] in ("APPROVED", "SUCCESS"):
#             conn.commit()
#             return True, "Already credited."
#         if tx["status"] != "PAYMENT_VERIFIED":
#             conn.rollback()
#             return False, "Payment must be verified before admin approval."

#         amount = float(tx["amount"])

#         now = datetime.now().isoformat()

#         cursor = conn.execute(
#             """
#             UPDATE nexus_transactions

#             SET
#                 status='APPROVED',
#                 updated_at=?,
#                 credited_at=?

#             WHERE reference=?
#               AND status='PAYMENT_VERIFIED'
#             """,
#             (
#                 now,
#                 now,
#                 reference
#             )
#         )

#         if cursor.rowcount != 1:
#             conn.rollback()
#             return False, "Transaction could not be credited."

#         conn.execute(
#             """
#             UPDATE users

#             SET balance=balance+?

#             WHERE username=?
#             """,
#             (
#                 amount,
#                 tx["username"]
#             )
#         )

#         conn.commit()

#         return True, (
#             f"Deposit of KES "
#             f"{amount:,.2f} credited."
#         )

#     except Exception:
#         conn.rollback()
#         raise

#     finally:
#         conn.close()


# # ============================================================
# # BALANCE / BET FUNCTIONS
# # ============================================================

# def deduct_balance(
#     username,
#     amount
# ):
#     conn = get_db()

#     try:
#         conn.execute("BEGIN IMMEDIATE")

#         cursor = conn.execute(
#             """
#             UPDATE users

#             SET balance=balance-?

#             WHERE username=?
#               AND balance>=?
#             """,
#             (
#                 amount,
#                 username,
#                 amount
#             )
#         )

#         if cursor.rowcount != 1:
#             conn.rollback()
#             return False

#         conn.commit()

#         return True

#     except Exception:
#         conn.rollback()
#         return False

#     finally:
#         conn.close()


# def place_bet_for_user(
#     username,
#     bet_number,
#     amount,
#     auto_cashout
# ):
#     with GAME_LOCK:

#         tick_game_locked()

#         if bet_number not in (1, 2):
#             return False, "Invalid bet slot."

#         if GAME["status"] != "BETTING":
#             return False, "Betting closed for this round."

#         amount = safe_float(amount)

#         if amount is None:
#             return False, "Invalid amount."

#         if amount <= 0:
#             return False, "Amount must be greater than zero."

#         if auto_cashout in (
#             None,
#             "",
#             False
#         ):
#             auto_cashout = None

#         else:
#             auto_cashout = safe_float(
#                 auto_cashout
#             )

#             if auto_cashout is None:
#                 return False, "Invalid auto cashout."

#             if auto_cashout < 1.01:
#                 return False, (
#                     "Auto cashout minimum is 1.01x."
#                 )

#         conn = get_db()

#         try:
#             conn.execute("BEGIN IMMEDIATE")

#             existing = conn.execute(
#                 """
#                 SELECT id

#                 FROM bets

#                 WHERE username=?
#                   AND round_id=?
#                   AND bet_number=?
#                 """,
#                 (
#                     username,
#                     GAME["round_id"],
#                     bet_number
#                 )
#             ).fetchone()

#             if existing:
#                 conn.rollback()

#                 return False, (
#                     f"Bet {bet_number} already placed."
#                 )

#             user = conn.execute(
#                 """
#                 SELECT balance

#                 FROM users

#                 WHERE username=?
#                 """,
#                 (username,)
#             ).fetchone()

#             if not user:
#                 conn.rollback()
#                 return False, "User not found."

#             if float(user["balance"]) < amount:
#                 conn.rollback()
#                 return False, "Insufficient balance."

#             cursor = conn.execute(
#                 """
#                 UPDATE users

#                 SET balance=balance-?

#                 WHERE username=?
#                   AND balance>=?
#                 """,
#                 (
#                     amount,
#                     username,
#                     amount
#                 )
#             )

#             if cursor.rowcount != 1:
#                 conn.rollback()
#                 return False, "Insufficient balance."

#             conn.execute(
#                 """
#                 INSERT INTO bets
#                 (
#                     username,
#                     round_id,
#                     bet_number,
#                     amount,
#                     auto_cashout,
#                     winnings,
#                     status,
#                     created_at
#                 )

#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#                 """,
#                 (
#                     username,
#                     GAME["round_id"],
#                     bet_number,
#                     amount,
#                     auto_cashout,
#                     0.0,
#                     "ACTIVE",
#                     datetime.now().isoformat()
#                 )
#             )

#             conn.commit()

#             return True, (
#                 f"Bet {bet_number} placed."
#             )

#         except Exception as exc:
#             conn.rollback()

#             print(
#                 "Place bet error:",
#                 repr(exc)
#             )

#             return False, "Failed to place bet."

#         finally:
#             conn.close()


# def manual_cashout(
#     username,
#     bet_number
# ):
#     with GAME_LOCK:

#         tick_game_locked()

#         if GAME["status"] != "RUNNING":
#             return False, "Flight not running."

#         multiplier = GAME["current_multiplier"]

#         if multiplier >= GAME["crash_point"]:
#             return False, "Round crashed."

#         multiplier = round(
#             multiplier,
#             2
#         )

#         conn = get_db()

#         try:
#             conn.execute("BEGIN IMMEDIATE")

#             bet = conn.execute(
#                 """
#                 SELECT *

#                 FROM bets

#                 WHERE username=?
#                   AND round_id=?
#                   AND bet_number=?
#                   AND status='ACTIVE'
#                 """,
#                 (
#                     username,
#                     GAME["round_id"],
#                     bet_number
#                 )
#             ).fetchone()

#             if not bet:
#                 conn.rollback()
#                 return False, (
#                     "No active bet found."
#                 )

#             winnings = round(
#                 float(bet["amount"])
#                 * multiplier,
#                 2
#             )

#             cursor = conn.execute(
#                 """
#                 UPDATE bets

#                 SET
#                     status='WON',
#                     cashout_multiplier=?,
#                     winnings=?

#                 WHERE id=?
#                   AND status='ACTIVE'
#                 """,
#                 (
#                     multiplier,
#                     winnings,
#                     bet["id"]
#                 )
#             )

#             if cursor.rowcount != 1:
#                 conn.rollback()
#                 return False, "Cashout failed."

#             conn.execute(
#                 """
#                 UPDATE users

#                 SET balance=balance+?

#                 WHERE username=?
#                 """,
#                 (
#                     winnings,
#                     username
#                 )
#             )

#             conn.commit()

#             return True, (
#                 f"Cashed out at "
#                 f"{multiplier:.2f}x — "
#                 f"KES {winnings:,.2f}"
#             )

#         except Exception as exc:
#             conn.rollback()

#             print(
#                 "Cashout error:",
#                 repr(exc)
#             )

#             return False, "Cashout error."

#         finally:
#             conn.close()


# # ============================================================
# # SECURITY / ACTIVITY / SMS HELPERS
# # ============================================================
# def touch_user(username):
#     conn = get_db()
#     try:
#         conn.execute("UPDATE users SET last_seen_at=? WHERE username=?", (datetime.now().isoformat(), username))
#         conn.commit()
#     finally:
#         conn.close()


# def audit_admin(action, target_username=None, details=None):
#     if session.get("role") != "ADMIN":
#         return
#     conn = get_db()
#     try:
#         conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
#             (session.get("username", "unknown"), action, target_username, str(details or "")[:1000], request.headers.get("X-Forwarded-For", request.remote_addr), datetime.now().isoformat()))
#         conn.commit()
#     finally:
#         conn.close()


# def admin_required():
#     """Require a current database-backed ADMIN account, not just a session flag."""
#     username = session.get("username")
#     if not username or session.get("role") != "ADMIN":
#         return False
#     conn = get_db()
#     try:
#         row = conn.execute("SELECT role, is_active FROM users WHERE username=?", (username,)).fetchone()
#         return bool(row and row["role"] == "ADMIN" and int(row["is_active"] or 0) == 1)
#     finally:
#         conn.close()


# def send_at_otp(phone, code):
#     if not AT_USERNAME or not AT_API_KEY:
#         raise RuntimeError("Africa's Talking is not configured. Set AT_USERNAME and AT_API_KEY in .env.")
#     message = f"Your Aviator password reset code is {code}. It expires in {OTP_TTL_MINUTES} minutes. If you did not request this, ignore this message."
#     payload = {"username": AT_USERNAME, "to": phone, "message": message}
#     if AT_SENDER_ID:
#         payload["from"] = AT_SENDER_ID
#     response = requests.post("https://api.africastalking.com/version1/messaging", data=payload,
#         headers={"apiKey": AT_API_KEY, "Accept": "application/json"}, timeout=15)
#     response.raise_for_status()
#     body = response.json()
#     recipients = (body.get("SMSMessageData") or {}).get("Recipients") or []
#     if not recipients or str(recipients[0].get("status", "")).lower() not in {"success", "sent", "accepted"}:
#         raise RuntimeError("Africa's Talking did not confirm that the OTP was accepted for sending.")

# def current_next_round_number():
#     """Return the next internal game round number (not its future result)."""
#     with GAME_LOCK:
#         current = GAME.get("round_id")
#         return (int(current) + 1) if current is not None else 1


# def ensure_generated_signals(start_round, count=10):
#     """Create transparent demo estimates for upcoming round IDs.

#     These values are synthetic placeholders, not forecasts or derived from
#     hidden crash outcomes. A unique round index prevents duplicate generation.
#     """
#     start_round = max(1, int(start_round))
#     count = max(1, min(int(count), 20))
#     now = datetime.now()
#     rng = random.SystemRandom()
#     conn = get_db()
#     try:
#         for offset in range(count):
#             round_number = start_round + offset
#             estimate = round(rng.uniform(1.10, 2.50), 2)
#             signal_time = (now + timedelta(seconds=round_number - start_round)).strftime("%H:%M:%S")
#             conn.execute("""INSERT OR IGNORE INTO aviator_signals
#                 (admin_username, round_label, signal_time, predicted_multiplier,
#                  confidence, notes, status, created_at, round_number)
#                 VALUES('SYSTEM', ?, ?, ?, 'SIMULATED',
#                 'Automatically generated sample estimate. Not predictive; Aviator outcomes are random.',
#                 'PUBLISHED', ?, ?)""",
#                 (f"Round {round_number}", signal_time, estimate, now.isoformat(), round_number))
#         conn.commit()
#     finally:
#         conn.close()


# # ============================================================
# # PLAYER LOBBY AND PAID SIGNAL PAGES
# # ============================================================
# LOBBY_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Game Lobby</title><style>
# *{box-sizing:border-box}body{margin:0;background:#0d1016;color:#f4f6fa;font:15px Arial,sans-serif}.top{padding:18px 5%;background:#171c25;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.top a{color:#ffca6b;text-decoration:none}.wrap{max-width:1180px;margin:auto;padding:28px 5%}.hero{padding:26px;border-radius:18px;background:linear-gradient(120deg,#182b26,#17202d);border:1px solid #2d4b40;margin-bottom:22px}.hero h1{margin:0 0 8px;font-size:clamp(25px,5vw,38px)}.muted{color:#aeb8c6;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.game{background:#181e28;border:1px solid #303948;border-radius:14px;padding:20px;min-height:190px;display:flex;flex-direction:column}.game h2{margin:5px 0 8px}.game .emoji{font-size:32px}.game .tag{font-size:11px;color:#ffca6b;text-transform:uppercase;letter-spacing:1px}.game a,.game button{margin-top:auto;display:inline-block;text-align:center;padding:12px;border:0;border-radius:8px;background:#28a745;color:white;text-decoration:none;font-weight:bold;cursor:pointer}.game.disabled{opacity:.75}.game.disabled button{background:#454d59;cursor:not-allowed}.notice{margin-top:20px;padding:14px;border:1px solid #6b5630;background:#2a2418;border-radius:10px;color:#f2d38a;font-size:13px}@media(max-width:520px){.wrap{padding:18px 4%}.hero{padding:20px}.top{padding:14px 4%}}
# </style></head><body><header class="top"><b>✈️ AVIATOR · GAMES</b><span>Welcome, <strong>@{{ username }}</strong> · Available: <strong>KES {{ '%.2f'|format(balance) }}</strong> &nbsp; <a href="/logout">Logout</a></span></header><main class="wrap"><section class="hero"><h1>Choose your game</h1><p class="muted">Explore the game lobby. Aviator is currently available; additional games are shown in the catalogue and will be enabled after their game engines and payment rules are implemented.</p></section><section class="grid">
# <article class="game"><div class="emoji">✈️</div><span class="tag">Available</span><h2>Aviator</h2><p class="muted">Play the live crash game, manage bets and cash out before the round ends.</p><a href="/aviator">PLAY AVIATOR</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">Signals</span><h2>Aviator Signals</h2><p class="muted">Choose a paid signal access package Aviator.</p><a href="/signals">AVIATOR SIGNAL</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">Betika Signals</span><h2>Betika</h2><p class="muted">Choose a paid signal access package Betika.</p><a href="/aviator">PLAY AVIATOR</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">Odibet Signals</span><h2>Odibets</h2><p class="muted">Choose a paid signal access package Odibets.</p><a href="/aviator">PLAY AVIATOR</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">Playmaster Signals</span><h2>Playmaster</h2><p class="muted">Choose a paid signal access package Playmaster.</p><a href="/aviator">PLAY AVIATOR</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">1XBet Signals</span><h2>1XBet</h2><p class="muted">Choose a paid signal access package 1XBet.</p><a href="/aviator">PLAY AVIATOR</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">JetX Signals</span><h2>JetX</h2><p class="muted">Choose a paid signal access package JetX.</p><a href="/aviator">PLAY AVIATOR</a></article>
# <article class="game"><div class="emoji">🚀</div><span class="tag">SportPesa Signals</span><h2>SportPesa</h2><p class="muted">Choose a paid signal access package SportPesa.</p><a href="/aviator">PLAY AVIATOR</a></article>
# </section><p class="notice"> <strong>TECH-STAR</strong><br>
#     Evron Enterprises.</p></main></body></html>"""

# SIGNALS_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aviator Signals</title><meta name="signal-csrf" content="{{ csrf }}"><style>
# *{box-sizing:border-box}body{margin:0;background:#0d1016;color:#f4f6fa;font:15px Arial,sans-serif}.top{padding:16px 5%;background:#171c25;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.top a{color:#8dc5ff;text-decoration:none}.wrap{max-width:1000px;margin:auto;padding:25px 5%}.panel{background:#181e28;border:1px solid #303948;border-radius:14px;padding:20px;margin-bottom:16px}.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.plan{border:1px solid #3a4656;border-radius:12px;padding:18px;background:#111720}.price{font-size:30px;color:#39d98a;font-weight:bold}.btn{display:block;width:100%;padding:13px;border:0;border-radius:8px;background:#28a745;color:white;font-weight:bold;cursor:pointer;margin-top:12px}.muted{color:#aeb8c6;line-height:1.5}.warn{color:#ffd17b;background:#2b2418;border:1px solid #6a552f;padding:12px;border-radius:9px}.status{padding:12px;border-radius:9px;background:#172b22;color:#a8f0c6}.feed{display:grid;gap:10px}.signal{padding:14px;border:1px solid #3b4655;border-radius:10px;background:#111720}.signal strong{color:#ffd17b}.locked{opacity:.95}.field{width:100%;padding:12px;margin-top:7px;background:#0d1016;color:white;border:1px solid #3a4656;border-radius:8px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #303948}.scroll{overflow:auto}@media(max-width:520px){.wrap{padding:16px 4%}.panel{padding:15px}}
# </style></head><body><header class="top"><b>✈️ AVIATOR SIGNAL CENTER</b><span>@{{ username }} &nbsp; <a href="/lobby">Game lobby</a> &nbsp; <a href="/aviator">Play Aviator</a></span></header><main class="wrap"><h1>Aviator signal access</h1><p class="muted">Select a time-limited access package. Nexus Pay will send an M-Pesa STK prompt to your phone. Your access starts only after the signed Nexus webhook verifies the exact amount and an administrator approves the order.</p>
# {% if active %}<section class="panel"><h2>Signal access active</h2><p class="status">Payment confirmed and approved. Access expires at {{ active.expires_at }}.</p><p class="muted">Next Aviator round: <strong id="customer-next-round">#{{ next_round }}</strong></p><p class="muted">Package: {{ active.plan_minutes }} minutes · Rounds: #{{ active.start_round or next_round }}–#{{ active.end_round or (next_round + active.plan_minutes - 1) }} · Paid: KES {{ '%.2f'|format(active.amount) }}</p><h3>Upcoming round estimates</h3><p class="muted">Automatically generated sample values for exactly the rounds included in your package. They are not predictions of actual outcomes.</p><div class="feed">{% for sig in signals %}<article class="signal"><strong>{{ sig.round_label }}</strong> · {{ sig.signal_time }}<h2>{{ '%.2f'|format(sig.predicted_multiplier) }}x estimate</h2><p class="muted">Confidence label: {{ sig.confidence }}{% if sig.notes %}<br>{{ sig.notes }}{% endif %}</p></article>{% else %}<p class="muted">No signals have been published during this access period yet. Refresh this page later.</p>{% endfor %}</div></section>{% else %}<section class="panel locked"><h2>Choose your signal package</h2><div class="plans"><article class="plan"><h3>5-minute signal</h3><div class="price">KES 200</div><p class="muted">Five minutes of access after payment confirmation.</p><button class="btn" onclick="buySignal(5)">PAY KES 200</button></article><article class="plan"><h3>10-minute signal</h3><div class="price">KES 400</div><p class="muted">Ten minutes of access after payment confirmation.</p><button class="btn" onclick="buySignal(10)">PAY KES 400</button></article></div><label for="phone">M-Pesa phone number</label><input class="field" id="phone" placeholder="0712345678" inputmode="tel"><p id="payStatus" class="muted" aria-live="polite">No active signal subscription.</p></section>{% endif %}
# <section class="panel"><h3>Recent signal purchases</h3><div class="scroll"><table><tr><th>Package</th><th>Amount</th><th>Status</th><th>Expires</th></tr>{% for item in history %}<tr><td>{{ item.plan_minutes }} minutes</td><td>KES {{ '%.2f'|format(item.amount) }}</td><td>{{ item.status }}</td><td>{{ item.expires_at or '—' }}</td></tr>{% else %}<tr><td colspan="4">No signal purchases yet.</td></tr>{% endfor %}</table></div></section>
# <p class="warn">TECH-STAR: .
#     Purchasing signals guarantee a successful outcome.</p></main>
# <script>
# async function refreshCustomerNextRound(){const el=document.getElementById('customer-next-round');if(!el)return;try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)return;const d=await r.json();el.textContent='#'+(Number(d.round_id||0)+1);}catch(e){}}
# refreshCustomerNextRound();setInterval(refreshCustomerNextRound,2500);
# async function buySignal(minutes){const amount=minutes===5?200:400;const phone=document.getElementById('phone').value.trim();if(!confirm(`You are about to request an M-Pesa STK prompt for KES ${amount} for ${minutes}-minute Aviator signal access. Continue?`))return;const status=document.getElementById('payStatus');status.textContent='Requesting secure M-Pesa prompt…';try{const r=await fetch('/api/signals/purchase',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=signal-csrf]').content},body:JSON.stringify({minutes,phone_number:phone})});const data=await r.json();if(!r.ok||!data.success)throw new Error(data.message||'Payment request failed.');status.textContent=data.message+' Reference: '+data.reference+' Waiting for payment verification and administrator approval…';let tries=0;const timer=setInterval(async()=>{tries++;try{const sr=await fetch('/api/signals/order/'+encodeURIComponent(data.reference));const st=await sr.json();if(st.status==='PAID'){clearInterval(timer);status.textContent='Payment confirmed. Opening your signal access…';window.location.assign('/signals?payment=confirmed');}else if(st.status==='FAILED'){clearInterval(timer);status.textContent='Payment was not completed. You may try again.';}else if(tries>=60){clearInterval(timer);status.textContent='Still awaiting verification or administrator approval. Do not pay again; refresh later to check status.';}}catch(e){}},3000);}catch(e){status.textContent=e.message;}}
# </script></body></html>"""

# # ============================================================
# # AUTHENTICATION
# # ============================================================

# @app.route("/")
# def index():
#     if "username" not in session:
#         return redirect("/login")
#     touch_user(session["username"])
#     if session.get("role") == "ADMIN":
#         return redirect("/admin")
#     return redirect("/lobby")


# @app.route("/lobby")
# def player_lobby():
#     if "username" not in session:
#         return redirect("/login")
#     if session.get("role") == "ADMIN":
#         return redirect("/admin")
#     touch_user(session["username"])
#     conn = get_db()
#     try:
#         player = conn.execute("SELECT balance FROM users WHERE username=?", (session["username"],)).fetchone()
#         balance = float(player["balance"]) if player else 0.0
#     finally:
#         conn.close()
#     return render_template_string(LOBBY_HTML, username=session["username"], balance=balance)


# @app.route("/aviator")
# def aviator_game_page():
#     if "username" not in session:
#         return redirect("/login")
#     if session.get("role") == "ADMIN":
#         return redirect("/admin")
#     touch_user(session["username"])
#     return render_template_string(HTML, username=session["username"])


# @app.route(
#     "/login",
#     methods=["GET", "POST"]
# )
# def login():

#     error = None

#     if request.method == "POST":

#         username = (
#             request.form
#             .get("username", "")
#             .strip()
#         )

#         password = request.form.get(
#             "password",
#             ""
#         )

#         conn = get_db()

#         try:
#             user = conn.execute(
#                 """
#                 SELECT *

#                 FROM users

#                 WHERE username=?
#                 """,
#                 (username,)
#             ).fetchone()

#         finally:
#             conn.close()

#         env_admin_login = bool(
#             ADMIN_USERNAME and ADMIN_PASSWORD and len(ADMIN_PASSWORD) >= 12
#             and secrets.compare_digest(username, ADMIN_USERNAME)
#             and secrets.compare_digest(password, ADMIN_PASSWORD)
#         )
#         valid_login = bool(
#             user and (
#                 (user["role"] == "ADMIN" and env_admin_login)
#                 or (user["role"] != "ADMIN"
#                     and not (ADMIN_USERNAME and username == ADMIN_USERNAME)
#                     and verify_password(password, user["password"]))
#             )
#         )

#         if valid_login:
#             # When .env admin credentials are used, keep the database admin
#             # hash synchronized without ever storing plaintext credentials.
#             if env_admin_login and not verify_password(ADMIN_PASSWORD, user["password"]):
#                 upgrade_conn = get_db()
#                 try:
#                     upgrade_conn.execute("UPDATE users SET password=?, role='ADMIN' WHERE username=?",
#                                           (hash_password(ADMIN_PASSWORD), ADMIN_USERNAME))
#                     upgrade_conn.commit()
#                 finally:
#                     upgrade_conn.close()
#             # Upgrade legacy SHA-256 hashes after a successful login.
#             if re.fullmatch(r"[0-9a-fA-F]{64}", str(user["password"])):
#                 upgrade_conn = get_db()
#                 try:
#                     upgrade_conn.execute("UPDATE users SET password=? WHERE username=?", (hash_password(password), username))
#                     upgrade_conn.commit()
#                 finally:
#                     upgrade_conn.close()
#             touch_user(username)
#             session.clear()
#             session.permanent = request.form.get("remember") == "1"

#             session["username"] = (
#                 user["username"]
#             )

#             session["role"] = (
#                 user["role"]
#             )

#             return redirect("/" if user["role"] == "ADMIN" else "/lobby")

#         error = "Invalid credentials."

#     return render_template_string(
#         LOGIN_HTML,
#         error=error
#     )


# @app.route(
#     "/register",
#     methods=["GET", "POST"]
# )
# def register():

#     error = None

#     if request.method == "POST":

#         username = (
#             request.form
#             .get("username", "")
#             .strip()
#         )

#         password = request.form.get(
#             "password",
#             ""
#         )

#         phone = (
#             request.form
#             .get("phone_number", "")
#             .strip()
#         )

#         if not username:
#             error = "Username is required."

#         elif len(username) < 3:
#             error = (
#                 "Username must be at least 3 characters."
#             )

#         elif not password:
#             error = "Password is required."

#         elif len(password) < 10:
#             error = (
#                 "Password must be at least 10 characters."
#             )

#         else:
#             try:
#                 phone = normalize_mpesa_phone(
#                     phone
#                 )

#             except ValueError as exc:
#                 error = str(exc)

#         if not error:

#             conn = get_db()

#             try:
#                 conn.execute(
#                     """
#                     INSERT INTO users
#                     (
#                         username,
#                         password,
#                         phone_number,
#                         balance,
#                         role,
#                         created_at
#                     )

#                     VALUES (?, ?, ?, ?, ?, ?)
#                     """,
#                     (
#                         username,
#                         hash_password(password),
#                         phone,
#                         STARTING_BALANCE,
#                         "USER",
#                         datetime.now().isoformat()
#                     )
#                 )

#                 conn.commit()

#                 session.clear()
#                 session.permanent = True

#                 session["username"] = (
#                     username
#                 )

#                 session["role"] = "USER"

#                 return redirect("/lobby")

#             except sqlite3.IntegrityError:
#                 error = (
#                     "Username or phone number "
#                     "is already registered."
#                 )

#             finally:
#                 conn.close()

#     return render_template_string(
#         REGISTER_HTML,
#         error=error
#     )


# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect("/login")


# # ============================================================
# # GAME API
# # ============================================================

# @app.route("/api/state")
# def api_state():

#     if "username" not in session:
#         return jsonify({
#             "error": "Unauthorized"
#         }), 401

#     touch_user(session["username"])
#     with GAME_LOCK:

#         tick_game_locked()

#         username = session["username"]

#         user = get_user(username)

#         if not user:
#             session.clear()

#             return jsonify({
#                 "error": "User not found."
#             }), 401

#         is_admin = (
#             user["role"] == "ADMIN"
#         )

#         conn = get_db()

#         try:

#             history_rows = conn.execute(
#                 """
#                 SELECT crash_point

#                 FROM rounds

#                 WHERE ended_at IS NOT NULL

#                 ORDER BY id DESC

#                 LIMIT 20
#                 """
#             ).fetchall()

#             history = [
#                 float(row["crash_point"])
#                 for row in reversed(
#                     history_rows
#                 )
#             ]

#             bet_rows = conn.execute(
#                 """
#                 SELECT
#                     bet_number,
#                     amount,
#                     auto_cashout,
#                     cashout_multiplier,
#                     winnings,
#                     status

#                 FROM bets

#                 WHERE username=?
#                   AND round_id=?
#                 """,
#                 (
#                     username,
#                     GAME["round_id"]
#                 )
#             ).fetchall()
#             pending_deposit = conn.execute(
#                 "SELECT COALESCE(SUM(amount),0) FROM nexus_transactions WHERE username=? AND status IN ('PENDING','PAYMENT_VERIFIED')",
#                 (username,)
#             ).fetchone()[0]
#             verified_pending_count = conn.execute(
#                 "SELECT COUNT(*) FROM nexus_transactions WHERE username=? AND status='PAYMENT_VERIFIED'",
#                 (username,)
#             ).fetchone()[0]

#         finally:
#             conn.close()

#         user_bets = {}

#         all_live_bets = []

#         # Bot feed.
#         for bot in GAME["bot_bets"]:
#             all_live_bets.append(bot)

#         # Real user bets.
#         for bet in bet_rows:

#             user_bets[
#                 str(bet["bet_number"])
#             ] = dict(bet)

#             all_live_bets.append({
#                 "id":
#                     f"real_{bet['bet_number']}",

#                 "username":
#                     username,

#                 "amount":
#                     float(bet["amount"]),

#                 "auto_cashout":
#                     bet["auto_cashout"],

#                 "status":
#                     bet["status"],

#                 "cashout_multiplier":
#                     bet["cashout_multiplier"],

#                 "winnings":
#                     float(bet["winnings"])
#             })

#         all_live_bets.sort(
#             key=lambda item:
#                 0
#                 if item["status"] == "ACTIVE"
#                 else 1
#         )

#         return jsonify({

#             "status":
#                 GAME["status"],

#             "multiplier":
#                 GAME["current_multiplier"],

#             "crash_point":
#                 (
#                     GAME["crash_point"]
#                     if GAME["status"] == "CRASHED"
#                     else None
#                 ),

#             "next_crash_point_1":
#                 (
#                     GAME["next_crash_point_1"]
#                     if is_admin
#                     else None
#                 ),

#             "next_crash_point_2":
#                 (
#                     GAME["next_crash_point_2"]
#                     if is_admin
#                     else None
#                 ),

#             "is_admin":
#                 is_admin,

#             "balance":
#                 float(user["balance"]),

#             "pending_deposit": float(pending_deposit),
#             "verified_pending_count": int(verified_pending_count),

#             "bets":
#                 user_bets,

#             "live_feed":
#                 all_live_bets,

#             "history":
#                 history,

#             "round_id":
#                 GAME["round_id"]
#         })


# @app.route(
#     "/api/bet",
#     methods=["POST"]
# )
# def api_bet():

#     if "username" not in session:
#         return jsonify({
#             "success": False,
#             "message": "Unauthorized"
#         }), 401

#     data = request.get_json(
#         silent=True
#     ) or {}

#     bet_number = data.get(
#         "bet_number",
#         1
#     )

#     try:
#         bet_number = int(bet_number)

#     except (
#         TypeError,
#         ValueError
#     ):
#         return jsonify({
#             "success": False,
#             "message": "Invalid bet number."
#         })

#     success, message = place_bet_for_user(
#         session["username"],
#         bet_number,
#         data.get("amount", 0),
#         data.get("auto_cashout")
#     )

#     return jsonify({
#         "success": success,
#         "message": message
#     })


# @app.route(
#     "/api/cashout",
#     methods=["POST"]
# )
# def api_cashout():

#     if "username" not in session:
#         return jsonify({
#             "success": False,
#             "message": "Unauthorized"
#         }), 401

#     data = request.get_json(
#         silent=True
#     ) or {}

#     try:
#         bet_number = int(
#             data.get(
#                 "bet_number",
#                 1
#             )
#         )

#     except (
#         TypeError,
#         ValueError
#     ):
#         return jsonify({
#             "success": False,
#             "message": "Invalid bet number."
#         })

#     success, message = manual_cashout(
#         session["username"],
#         bet_number
#     )

#     return jsonify({
#         "success": success,
#         "message": message
#     })


# # ============================================================
# # NEXUS PAY STK PUSH
# # ============================================================

# @app.route(
#     "/api/nexus/stkpush",
#     methods=["POST"]
# )
# def api_nexus_stkpush():

#     if "username" not in session:
#         return jsonify({
#             "success": False,
#             "message": "Unauthorized"
#         }), 401

#     data = request.get_json(
#         silent=True
#     ) or {}

#     username = session["username"]

#     user = get_user(username)

#     if not user:
#         return jsonify({
#             "success": False,
#             "message": "User not found."
#         }), 401

#     amount = safe_float(
#         data.get("amount")
#     )

#     if amount is None:
#         return jsonify({
#             "success": False,
#             "message": "Invalid amount."
#         })

#     if amount < 5:
#         return jsonify({
#             "success": False,
#             "message": "Minimum deposit is KES 200. Please enter KES 200 or more."
#         }), 400

#     phone_input = (
#         data.get("phone")
#         or user["phone_number"]
#     )

#     try:
#         phone = normalize_mpesa_phone(
#             phone_input
#         )

#         result = nexus_stk_push(
#             phone,
#             amount,
#             username
#         )

#         return jsonify({
#             "success": True,

#             "message":
#                 result["message"],

#             "reference":
#                 result["reference"],

#             "provider_transaction_id":
#                 result["provider_transaction_id"]
#         })

#     except ValueError as exc:

#         return jsonify({
#             "success": False,
#             "message": str(exc)
#         })

#     except requests.Timeout:

#         return jsonify({
#             "success": False,
#             "message":
#                 "Nexus Pay request timed out."
#         }), 504

#     except requests.HTTPError as exc:

#         print(
#             "Nexus Pay HTTP error:",
#             repr(exc)
#         )

#         response = getattr(
#             exc,
#             "response",
#             None
#         )

#         provider_message = None

#         if response is not None:
#             try:
#                 payload = response.json()

#                 provider_message = (
#                     payload.get("message")
#                     or payload.get("error")
#                     or payload.get("description")
#                 )

#             except Exception:
#                 provider_message = None

#         return jsonify({
#             "success": False,
#             "message":
#                 provider_message
#                 or "Nexus Pay rejected the request."
#         }), 502

#     except requests.RequestException as exc:

#         print(
#             "Nexus Pay connection error:",
#             repr(exc)
#         )

#         return jsonify({
#             "success": False,
#             "message":
#                 "Could not connect to Nexus Pay."
#         }), 502

#     except Exception as exc:

#         print(
#             "Nexus Pay STK error:",
#             repr(exc)
#         )

#         return jsonify({
#             "success": False,
#             "message": str(exc)
#         }), 500


# # ============================================================
# # NEXUS TRANSACTION STATUS
# # ============================================================

# @app.route(
#     "/api/nexus/status/<path:reference>",
#     methods=["GET"]
# )
# def api_nexus_status(reference):

#     if "username" not in session:
#         return jsonify({
#             "success": False,
#             "message": "Unauthorized"
#         }), 401

#     tx = get_nexus_transaction(
#         reference,
#         session["username"]
#     )

#     if not tx:
#         return jsonify({
#             "success": False,
#             "message": "Transaction not found."
#         }), 404

#     return jsonify({
#         "success": True,

#         "reference":
#             tx["reference"],

#         "status":
#             tx["status"],
#         "available_for_betting": tx["status"] in ("APPROVED", "SUCCESS"),

#         "amount":
#             float(tx["amount"]),

#         "message":
#             tx["provider_message"]
#             or "Waiting for payment confirmation.",

#         "provider_transaction_id":
#             tx["provider_transaction_id"],

#         "created_at":
#             tx["created_at"],

#         "credited_at":
#             tx["credited_at"]
#     })


# # ============================================================
# # NEXUS PAY WEBHOOK
# # ============================================================
# #
# # Nexus sends webhook events for payment.completed and payment.failed.
# # The screenshot/documentation shows a payload shaped like:
# #
# #   {
# #       "event": "payment.completed",
# #       "data": { ... }
# #   }
# #
# # The webhook is the authoritative source for the final transaction
# # state. STK Push/B2C initiation only creates the transaction.
# #
# # Configure this URL in Nexus Pay Webhooks:
# #
# #   https://YOUR-PUBLIC-DOMAIN/api/nexus/webhook
# #
# # ============================================================

# def _nexus_webhook_value(data, *keys):
#     """Return the first non-empty value from a webhook payload."""
#     for key in keys:
#         value = data.get(key)
#         if value not in (None, ""):
#             return value
#     return None


# def _nexus_webhook_payload():
#     """Normalize the Nexus webhook's event/data structure."""
#     body = request.get_json(silent=True) or {}
#     event = str(body.get("event") or body.get("type") or "").strip().lower()
#     data = body.get("data")

#     if not isinstance(data, dict):
#         data = body

#     return event, data, body


# def _verify_nexus_webhook():
#     """Verify Nexus Pay's SHA-256 HMAC webhook signature.

#     Nexus documents X-Webhook-Signature as ``sha256=<hex>`` and says
#     the HMAC-SHA256 is computed with the webhook secret. Verify the exact
#     raw request bytes first. A compact-JSON fallback supports the provider's
#     published Node example, which signs JSON.stringify(req.body).
#     """
#     if not NEXUS_WEBHOOK_SECRET:
#         return False

#     supplied = (request.headers.get("X-Webhook-Signature") or "").strip()
#     if not supplied.startswith("sha256="):
#         return False

#     raw_body = request.get_data(cache=True, as_text=False)
#     candidates = [raw_body]
#     parsed = request.get_json(silent=True)
#     if isinstance(parsed, dict):
#         try:
#             compact = json.dumps(
#                 parsed, separators=(",", ":"), ensure_ascii=False
#             ).encode("utf-8")
#             if compact != raw_body:
#                 candidates.append(compact)
#         except (TypeError, ValueError, UnicodeError):
#             pass

#     for candidate in candidates:
#         digest = hmac.new(
#             NEXUS_WEBHOOK_SECRET.encode("utf-8"),
#             candidate,
#             hashlib.sha256
#         ).hexdigest()
#         expected = "sha256=" + digest
#         if hmac.compare_digest(supplied, expected):
#             return True
#     return False


# def _mark_deposit_webhook(reference, status, provider_transaction_id, message, amount):
#     """Apply a deposit webhook exactly once and verify its amount."""
#     conn = get_db()

#     try:
#         conn.execute("BEGIN IMMEDIATE")

#         tx = conn.execute(
#             "SELECT * FROM nexus_transactions WHERE reference=?",
#             (reference,)
#         ).fetchone()

#         if not tx:
#             conn.rollback()
#             return False, "Deposit transaction not found.", False

#         if status == "SUCCESS" and amount in (None, ""):
#             conn.rollback()
#             return False, "Webhook amount is missing; deposit was not credited.", False

#         if amount not in (None, ""):
#             webhook_amount = safe_float(amount)
#             if webhook_amount is None or abs(webhook_amount - float(tx["amount"])) > 0.001:
#                 conn.rollback()
#                 return False, "Webhook amount does not match the stored deposit.", False

#         now = datetime.now().isoformat()
#         provider_id = (
#             str(provider_transaction_id)
#             if provider_transaction_id not in (None, "")
#             else tx["provider_transaction_id"]
#         )
#         provider_message = str(message or "Nexus webhook received.")

#         if status == "SUCCESS":
#             if tx["status"] in ("PAYMENT_VERIFIED", "APPROVED", "SUCCESS"):
#                 conn.commit()
#                 return True, "Payment already verified or approved; no duplicate credit applied.", False

#             cursor = conn.execute(
#                 """UPDATE nexus_transactions
#                    SET status='PAYMENT_VERIFIED', provider_transaction_id=?,
#                        provider_message=?, updated_at=?, verified_at=?
#                    WHERE reference=? AND status='PENDING'""",
#                 (provider_id, provider_message + " Payment verified; awaiting admin approval.", now, now, reference)
#             )
#             if cursor.rowcount != 1:
#                 conn.rollback()
#                 return False, "Deposit status could not be updated.", False
#             conn.commit()
#             return True, f"Payment of KES {float(tx['amount']):,.2f} verified; awaiting admin approval.", True

#         if status == "FAILED":
#             if tx["status"] == "FAILED":
#                 conn.commit()
#                 return True, "Deposit failure already recorded.", False

#             conn.execute(
#                 """
#                 UPDATE nexus_transactions
#                 SET status='FAILED', provider_transaction_id=?,
#                     provider_message=?, updated_at=?
#                 WHERE reference=? AND status='PENDING'
#                 """,
#                 (provider_id, provider_message, now, reference)
#             )
#             conn.commit()
#             return True, "Deposit failure recorded.", True

#         conn.commit()
#         return True, "Deposit webhook received.", False

#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()


# def _mark_withdrawal_webhook(reference, status, provider_transaction_id, message, amount):
#     """Complete/fail a withdrawal exactly once and refund failures once."""
#     conn = get_db()

#     try:
#         conn.execute("BEGIN IMMEDIATE")

#         withdrawal = conn.execute(
#             """
#             SELECT * FROM withdrawals
#             WHERE reference=? OR provider_transaction_id=?
#             ORDER BY id DESC LIMIT 1
#             """,
#             (reference, provider_transaction_id)
#         ).fetchone()

#         if not withdrawal:
#             conn.rollback()
#             return False, "Withdrawal transaction not found.", False

#         if amount is not None:
#             webhook_amount = safe_float(amount)
#             if webhook_amount is None or abs(webhook_amount - float(withdrawal["amount"])) > 0.001:
#                 conn.rollback()
#                 return False, "Webhook amount does not match the stored withdrawal.", False

#         now = datetime.now().isoformat()
#         provider_id = (
#             str(provider_transaction_id)
#             if provider_transaction_id not in (None, "")
#             else withdrawal["provider_transaction_id"]
#         )
#         provider_message = str(message or "Nexus webhook received.")

#         if status == "SUCCESS":
#             if withdrawal["status"] in {"SUCCESS", "COMPLETED", "PAID"}:
#                 conn.commit()
#                 return True, "Withdrawal already completed.", False

#             cursor = conn.execute(
#                 """
#                 UPDATE withdrawals
#                 SET status='SUCCESS', reference=COALESCE(reference, ?),
#                     provider_transaction_id=?, provider_message=?,
#                     updated_at=?, completed_at=?
#                 WHERE id=? AND status IN ('PENDING', 'PROCESSING')
#                 """,
#                 (
#                     reference,
#                     provider_id,
#                     provider_message,
#                     now,
#                     now,
#                     withdrawal["id"]
#                 )
#             )

#             if cursor.rowcount != 1:
#                 conn.rollback()
#                 return False, "Withdrawal status could not be updated.", False

#             conn.commit()
#             return True, "Withdrawal completed.", True

#         if status == "FAILED":
#             if withdrawal["status"] == "FAILED":
#                 conn.commit()
#                 return True, "Withdrawal failure already recorded.", False

#             # The balance was reserved when the withdrawal was created.
#             # Refund only when transitioning PENDING/PROCESSING -> FAILED.
#             cursor = conn.execute(
#                 """
#                 UPDATE withdrawals
#                 SET status='FAILED', reference=COALESCE(reference, ?),
#                     provider_transaction_id=?, provider_message=?,
#                     updated_at=?
#                 WHERE id=? AND status IN ('PENDING', 'PROCESSING')
#                 """,
#                 (
#                     reference,
#                     provider_id,
#                     provider_message,
#                     now,
#                     withdrawal["id"]
#                 )
#             )

#             if cursor.rowcount != 1:
#                 conn.rollback()
#                 return False, "Withdrawal failure could not be recorded.", False

#             conn.execute(
#                 "UPDATE users SET balance=balance+? WHERE username=?",
#                 (float(withdrawal["amount"]), withdrawal["username"])
#             )
#             conn.commit()
#             return True, "Withdrawal failed and the reserved balance was refunded.", True

#         conn.commit()
#         return True, "Withdrawal webhook received.", False

#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()


# def _mark_signal_payment_webhook(reference, status, provider_transaction_id, message, amount):
#     """Confirm a signal subscription only after a verified Nexus webhook."""
#     conn = get_db()
#     try:
#         conn.execute("BEGIN IMMEDIATE")
#         order = conn.execute("SELECT * FROM signal_orders WHERE reference=?", (reference,)).fetchone()
#         if not order:
#             conn.rollback()
#             return False, "Signal order not found.", False
#         # A signed success event is not enough on its own: require the
#         # provider's amount and compare it with the stored package price.
#         # This prevents a missing/incorrect amount from activating access.
#         if amount in (None, ""):
#             conn.rollback()
#             return False, "Signal payment webhook is missing the paid amount.", False
#         paid_amount = safe_float(amount)
#         if paid_amount is None or abs(paid_amount - float(order["amount"])) > 0.001:
#             conn.rollback()
#             return False, "Signal payment amount does not match the order.", False
#         now = datetime.now()
#         now_s = now.isoformat()
#         provider_id = str(provider_transaction_id) if provider_transaction_id not in (None, "") else order["provider_transaction_id"]
#         if status == "SUCCESS":
#             if order["status"] in ("PAID", "PAYMENT_VERIFIED"):
#                 conn.commit()
#                 return True, "Signal payment already verified; awaiting administrator approval if not active.", False
#             if order["status"] != "PENDING":
#                 conn.rollback()
#                 return False, "Signal order is not pending.", False
#             conn.execute("""UPDATE signal_orders SET status='PAYMENT_VERIFIED', provider_transaction_id=?, provider_message=?, updated_at=? WHERE id=? AND status='PENDING'""",
#                 (provider_id, str(message or "Nexus payment confirmed; awaiting administrator approval."), now_s, order["id"]))
#             conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
#                 ("SYSTEM", "SIGNAL_PAYMENT_VERIFIED", order["username"], f"{order['plan_minutes']} minute signal; KES {float(order['amount']):.2f}; {reference}; awaiting admin approval", "Nexus webhook", now_s))
#             conn.commit()
#             return True, "Signal payment verified; administrator approval is pending.", True
#         if status == "FAILED":
#             if order["status"] == "PENDING":
#                 conn.execute("UPDATE signal_orders SET status='FAILED',provider_transaction_id=?,provider_message=?,updated_at=? WHERE id=? AND status='PENDING'",
#                     (provider_id, str(message or "Nexus payment failed."), now_s, order["id"]))
#             conn.commit()
#             return True, "Signal payment failure recorded.", True
#         conn.commit()
#         return True, "Signal payment event received.", False
#     except Exception:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()


# @app.route("/api/signals/purchase", methods=["POST"])
# def api_signal_purchase():
#     if "username" not in session or session.get("role") == "ADMIN":
#         return jsonify({"success": False, "message": "Please log in as a player."}), 401
#     supplied_csrf = request.headers.get("X-CSRF-Token", "")
#     expected_csrf = session.get("csrf_token", "")
#     if not expected_csrf or not secrets.compare_digest(str(supplied_csrf), str(expected_csrf)):
#         return jsonify({"success": False, "message": "Session token expired. Refresh the page and try again."}), 400
#     body = request.get_json(silent=True) or {}
#     try:
#         minutes = int(body.get("minutes", 0))
#     except (TypeError, ValueError):
#         minutes = 0
#     plans = {5: 200, 10: 400}
#     if minutes not in plans:
#         return jsonify({"success": False, "message": "Choose the 5-minute or 10-minute signal package."}), 400
#     conn = get_db()
#     try:
#         user = conn.execute("SELECT username,phone_number FROM users WHERE username=? AND role='USER' AND is_active=1", (session["username"],)).fetchone()
#     finally:
#         conn.close()
#     if not user:
#         return jsonify({"success": False, "message": "Player account is unavailable."}), 403
#     try:
#         phone = normalize_mpesa_phone(str(body.get("phone_number") or user["phone_number"]))
#     except ValueError as exc:
#         return jsonify({"success": False, "message": str(exc)}), 400
#     amount = plans[minutes]
#     reference = make_nexus_reference("SIG", session["username"])
#     now = datetime.now().isoformat()
#     conn = get_db()
#     try:
#         conn.execute("INSERT INTO signal_orders(username,phone_number,plan_minutes,amount,reference,status,created_at,updated_at) VALUES(?,?,?,?,?,'PENDING',?,?)",
#             (session["username"], phone, minutes, amount, reference, now, now))
#         conn.commit()
#     finally:
#         conn.close()
#     payload = {"phoneNumber": phone, "amount": amount, "accountReference": reference,
#                "transactionDesc": f"Aviator signal access {minutes} minutes"}
#     try:
#         response = requests.post(f"{NEXUS_PAY_BASE_URL}/api/payments/stkpush", json=payload,
#                                  headers=nexus_headers(), timeout=NEXUS_PAY_TIMEOUT)
#         response.raise_for_status()
#         data = response.json()
#         if data.get("success") is False or str(data.get("status", "")).upper() in {"FAILED", "FAILURE", "ERROR", "REJECTED"}:
#             raise RuntimeError(str(data.get("message") or data.get("error") or "Nexus Pay rejected the request."))
#         provider_id = data.get("transactionId") or data.get("transaction_id") or data.get("checkoutRequestId") or data.get("checkout_request_id") or data.get("id")
#         msg = str(data.get("message") or data.get("description") or "STK push initiated. Awaiting verified payment callback.")
#         conn = get_db()
#         try:
#             conn.execute("UPDATE signal_orders SET provider_transaction_id=?,provider_message=?,updated_at=? WHERE reference=?",
#                          (str(provider_id) if provider_id else None, msg, datetime.now().isoformat(), reference))
#             conn.commit()
#         finally:
#             conn.close()
#         return jsonify({"success": True, "reference": reference, "status": "PENDING",
#                         "message": "M-Pesa prompt sent. Complete payment; signal access starts only after Nexus confirms payment."})
#     except Exception as exc:
#         conn = get_db()
#         try:
#             conn.execute("UPDATE signal_orders SET status='FAILED',provider_message=?,updated_at=? WHERE reference=? AND status='PENDING'",
#                          (str(exc)[:500], datetime.now().isoformat(), reference))
#             conn.commit()
#         finally:
#             conn.close()
#         app.logger.exception("Signal STK push failed")
#         return jsonify({"success": False, "message": "Could not initiate the signal payment. Check Nexus configuration and try again."}), 502


# @app.route("/api/signals/order/<path:reference>")
# def api_signal_order_status(reference):
#     if "username" not in session:
#         return jsonify({"success": False, "message": "Unauthorized"}), 401
#     conn = get_db()
#     try:
#         order = conn.execute("SELECT reference,status,plan_minutes,amount,expires_at FROM signal_orders WHERE reference=? AND username=?",
#                              (reference, session["username"])).fetchone()
#     finally:
#         conn.close()
#     if not order:
#         return jsonify({"success": False, "message": "Order not found."}), 404
#     return jsonify({"success": True, "reference": order["reference"], "status": order["status"],
#                     "minutes": order["plan_minutes"], "amount": order["amount"], "expires_at": order["expires_at"]})


# @app.route("/signals")
# def player_signals_page():
#     if "username" not in session or session.get("role") == "ADMIN":
#         return redirect("/login")
#     touch_user(session["username"])
#     next_round = current_next_round_number()
#     conn = get_db()
#     try:
#         now = datetime.now().isoformat()
#         active = conn.execute("SELECT * FROM signal_orders WHERE username=? AND status='PAID' AND expires_at>? ORDER BY expires_at DESC LIMIT 1",
#                               (session["username"], now)).fetchone()
#         signals = []
#         if active:
#             start_round = active["start_round"] or next_round
#             end_round = active["end_round"] or (int(start_round) + int(active["plan_minutes"]) - 1)
#             ensure_generated_signals(start_round, int(active["plan_minutes"]))
#             signals = conn.execute("SELECT * FROM aviator_signals WHERE status='PUBLISHED' AND round_number BETWEEN ? AND ? ORDER BY round_number ASC",
#                                    (start_round, end_round)).fetchall()
#         history = conn.execute("SELECT plan_minutes,amount,status,created_at,expires_at FROM signal_orders WHERE username=? ORDER BY id DESC LIMIT 8",
#                                (session["username"],)).fetchall()
#     finally:
#         conn.close()
#     return render_template_string(SIGNALS_HTML, username=session["username"], active=active, signals=signals, history=history, next_round=next_round, csrf=_csrf_token())


# @app.route("/admin/signals/orders/<int:order_id>/approve", methods=["POST"])
# def admin_approve_signal_order(order_id):
#     if not admin_required():
#         return redirect("/login")
#     if not _check_csrf():
#         return "Invalid request token. Refresh the admin page and try again.", 400
#     conn = get_db()
#     try:
#         conn.execute("BEGIN IMMEDIATE")
#         order = conn.execute("SELECT * FROM signal_orders WHERE id=?", (order_id,)).fetchone()
#         if not order:
#             conn.rollback()
#             return "Signal order not found.", 404
#         if order["status"] == "PAID":
#             conn.commit()
#             return redirect("/admin#signal-approvals")
#         if order["status"] != "PAYMENT_VERIFIED":
#             conn.rollback()
#             return "Only Nexus payment-verified signal orders can be approved.", 409
#         now = datetime.now()
#         now_s = now.isoformat()
#         expires = (now + timedelta(minutes=int(order["plan_minutes"]))).isoformat()
#         start_round = current_next_round_number()
#         end_round = start_round + int(order["plan_minutes"]) - 1
#         cur = conn.execute("UPDATE signal_orders SET status='PAID', paid_at=?, expires_at=?, start_round=?, end_round=?, updated_at=?, provider_message=? WHERE id=? AND status='PAYMENT_VERIFIED'",
#             (now_s, expires, start_round, end_round, now_s, "Payment verified and access approved; round-limited estimates are synthetic and not predictive.", order_id))
#         if cur.rowcount != 1:
#             conn.rollback()
#             return "Signal approval conflict; refresh and retry.", 409
#         conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
#             (session["username"], "SIGNAL_ACCESS_APPROVED", order["username"], f"Reference={order['reference']}; amount={float(order['amount']):.2f}; minutes={order['plan_minutes']}; order_id={order_id}", request.headers.get("X-Forwarded-For", request.remote_addr), now_s))
#         conn.commit()
#     finally:
#         conn.close()
#     return redirect("/admin#signal-approvals")


# @app.route("/admin/signals/publish", methods=["POST"])
# def admin_publish_signal():
#     if not admin_required():
#         return redirect("/login")
#     if not _check_csrf():
#         return "Invalid request token. Refresh and retry.", 400
#     round_label = request.form.get("round_label", "").strip()[:80]
#     signal_time = request.form.get("signal_time", "").strip()[:80]
#     multiplier = safe_float(request.form.get("predicted_multiplier"))
#     confidence = request.form.get("confidence", "Unrated").strip()[:30]
#     notes = request.form.get("notes", "").strip()[:500]
#     if not round_label or not signal_time or multiplier is None or multiplier < 1 or multiplier > 1000:
#         return "Enter a round label, time and a multiplier between 1.00 and 1000.00.", 400
#     now = datetime.now().isoformat()
#     conn = get_db()
#     try:
#         conn.execute("INSERT INTO aviator_signals(admin_username,round_label,signal_time,predicted_multiplier,confidence,notes,status,created_at) VALUES(?,?,?,?,?,?,'PUBLISHED',?)",
#                      (session["username"], round_label, signal_time, multiplier, confidence, notes, now))
#         conn.commit()
#         audit_admin("SIGNAL_PUBLISHED", None, f"{round_label}; estimate={multiplier:.2f}x")
#     finally:
#         conn.close()
#     return redirect("/admin#signal-management")


# @app.route("/admin/signals/<int:signal_id>/delete", methods=["POST"])
# def admin_delete_signal(signal_id):
#     if not admin_required():
#         return redirect("/login")
#     if not _check_csrf():
#         return "Invalid request token. Refresh and retry.", 400
#     conn = get_db()
#     try:
#         conn.execute("UPDATE aviator_signals SET status='REMOVED' WHERE id=?", (signal_id,))
#         conn.commit()
#         audit_admin("SIGNAL_REMOVED", None, f"signal_id={signal_id}")
#     finally:
#         conn.close()
#     return redirect("/admin#signal-management")


# @app.route(NEXUS_WEBHOOK_PATH, methods=["POST"])
# def nexus_webhook():
#     """Handle Nexus Pay payment.completed/payment.failed webhooks."""
#     if not _verify_nexus_webhook():
#         return jsonify({
#             "success": False,
#             "message": "Unauthorized webhook."
#         }), 401

#     event, data, body = _nexus_webhook_payload()

#     if event not in {"payment.completed", "payment.failed", "payment.cancelled"}:
#         # Acknowledge unrelated events so Nexus does not repeatedly retry them.
#         return jsonify({
#             "success": True,
#             "message": "Event ignored.",
#             "event": event or None
#         }), 200

#     reference = _nexus_webhook_value(
#         data,
#         "accountReference",
#         "reference",
#         "invoiceNumber",
#         "invoice_number",
#         "merchantReference",
#         "merchant_reference"
#     )

#     provider_transaction_id = _nexus_webhook_value(
#         data,
#         "transactionId",
#         "transaction_id",
#         "providerTransactionId",
#         "provider_transaction_id",
#         "mpesaReceiptNumber",
#         "checkoutRequestId",
#         "orderTrackingId",
#         "id"
#     )

#     amount = _nexus_webhook_value(data, "amount", "Amount")
#     message = _nexus_webhook_value(
#         data,
#         "message",
#         "description",
#         "statusMessage",
#         "status_message"
#     )

#     if not reference and not provider_transaction_id:
#         return jsonify({
#             "success": False,
#             "message": "Missing transaction reference."
#         }), 400

#     status = "SUCCESS" if event == "payment.completed" else "FAILED"

#     # Match the exact merchant/account reference first. Do not assume a
#     # particular prefix: existing deployments may have references such as
#     # AV-..., AVxxxx..., or AVD.... Fall back to a known provider ID only
#     # when no local reference match exists.
#     try:
#         conn = get_db()
#         try:
#             deposit = conn.execute(
#                 "SELECT reference FROM nexus_transactions WHERE reference=?",
#                 (str(reference),)
#             ).fetchone() if reference else None
#             withdrawal = conn.execute(
#                 "SELECT reference FROM withdrawals WHERE reference=? ORDER BY id DESC LIMIT 1",
#                 (str(reference),)
#             ).fetchone() if reference else None
#             signal_order = conn.execute(
#                 "SELECT reference FROM signal_orders WHERE reference=?",
#                 (str(reference),)
#             ).fetchone() if reference else None

#             if not deposit and not withdrawal and not signal_order and provider_transaction_id:
#                 deposit = conn.execute(
#                     "SELECT reference FROM nexus_transactions WHERE provider_transaction_id=?",
#                     (str(provider_transaction_id),)
#                 ).fetchone()
#                 withdrawal = conn.execute(
#                     "SELECT reference FROM withdrawals WHERE provider_transaction_id=? ORDER BY id DESC LIMIT 1",
#                     (str(provider_transaction_id),)
#                 ).fetchone()
#                 signal_order = conn.execute(
#                     "SELECT reference FROM signal_orders WHERE provider_transaction_id=? ORDER BY id DESC LIMIT 1",
#                     (str(provider_transaction_id),)
#                 ).fetchone()
#         finally:
#             conn.close()

#         if signal_order:
#             ok, msg, changed = _mark_signal_payment_webhook(
#                 signal_order["reference"], status, provider_transaction_id, message, amount
#             )
#         elif withdrawal:
#             ok, msg, changed = _mark_withdrawal_webhook(
#                 withdrawal["reference"], status, provider_transaction_id, message, amount
#             )
#         elif deposit:
#             ok, msg, changed = _mark_deposit_webhook(
#                 deposit["reference"], status, provider_transaction_id, message, amount
#             )
#         else:
#             return jsonify({
#                 "success": False,
#                 "message": "Transaction not found."
#             }), 404

#         return jsonify({
#             "success": ok,
#             "message": msg,
#             "event": event,
#             "reference": reference,
#             "provider_transaction_id": provider_transaction_id,
#             "changed": changed
#         }), (200 if ok else 400)

#     except Exception as exc:
#         print("Nexus webhook error:", repr(exc))
#         return jsonify({
#             "success": False,
#             "message": "Webhook processing failed."
#         }), 500


# # Backward-compatible callback endpoint. New Nexus Webhooks should use
# # /api/nexus/webhook configured in the Nexus dashboard.
# @app.route("/api/nexus/callback", methods=["POST"])
# def nexus_callback():
#     return nexus_webhook()


# # Legacy deposit callback is kept as an alias for older integrations.
# @app.route("/api/deposit/callback", methods=["POST"])
# def nexus_deposit_callback():
#     return nexus_webhook()


# # ============================================================
# # ADMIN PAYMENT CONFIRMATION
# # ============================================================
# #
# # This is intentionally protected by the ADMIN role.
# #
# # It can be used while testing if you have independently verified
# # the payment in Nexus Pay.
# #
# # For production, replace this manual confirmation with Nexus's
# # official webhook/status verification once you have that API
# # documentation.
# #
# # ============================================================

# @app.route("/api/admin/nexus/confirm", methods=["POST"])
# def admin_confirm_nexus():
#     """Manual payment approval is disabled; only verified provider webhooks credit deposits."""
#     return jsonify({
#         "success": False,
#         "message": "Manual deposit approval is disabled. Deposits are confirmed automatically by verified Nexus Pay webhooks."
#     }), 410


# # ============================================================
# # WITHDRAWALS
# # ============================================================

# # ============================================================
# # NEXUS WITHDRAWAL / DEPOSIT CALLBACK PROCESSING
# # ============================================================

# def nexus_b2c_disbursement(phone_number, amount, username, withdrawal_id=None, reference=None):
#     """Send a withdrawal through the configured Nexus Pay.

#     The balance is reserved by api_withdraw before this function is called.
#     This function only calls the provider and records its response.
#     """
#     phone = normalize_mpesa_phone(phone_number)
#     amount = safe_float(amount)

#     if amount is None or amount <= 0:
#         raise ValueError("Invalid withdrawal amount.")

#     if amount < MIN_WITHDRAWAL:
#         raise ValueError(
#             f"Minimum withdrawal is KES {MIN_WITHDRAWAL:,.0f}."
#         )

#     if amount > MAX_WITHDRAWAL:
#         raise ValueError(
#             f"Withdrawal exceeds maximum limit of KES {MAX_WITHDRAWAL:,.2f}."
#         )

#     if amount != round(amount):
#         raise ValueError("Withdrawal amount must be a whole KES amount.")

#     amount = int(round(amount))

#     reference = reference or make_nexus_reference("WD", username)

#     payload = {
#         "phoneNumber": phone,
#         "amount": amount,
#         "accountReference": reference,
#         "transactionDesc": "Aviator winnings payout"
#     }

#     response = requests.post(
#         f"{NEXUS_PAY_BASE_URL}/api/payments/b2c",
#         json=payload,
#         headers=nexus_headers(),
#         timeout=NEXUS_PAY_TIMEOUT
#     )
#     response.raise_for_status()

#     try:
#         data = response.json()
#     except ValueError as exc:
#         raise RuntimeError(
#             "Nexus Pay returned an invalid response for withdrawal."
#         ) from exc

#     provider_transaction_id = (
#         data.get("transactionId")
#         or data.get("transaction_id")
#         or data.get("checkoutRequestId")
#         or data.get("checkout_request_id")
#         or data.get("id")
#     )

#     success = data.get("success")
#     status_value = str(data.get("status", "")).upper()

#     if success is False or status_value in {
#         "FAILED", "FAILURE", "ERROR", "REJECTED"
#     }:
#         message = (
#             data.get("message")
#             or data.get("error")
#             or data.get("description")
#             or "Nexus Pay rejected the withdrawal request."
#         )
#         raise RuntimeError(str(message))

#     provider_message = (
#         data.get("message")
#         or data.get("description")
#         or "payout request accepted by Nexus Pay."
#     )

#     # A provider may accept the request but complete the payout asynchronously.
#     # The webhook is authoritative for final payout status. Even if the
#     # B2C request is accepted with success=true, keep the withdrawal in
#     # PROCESSING until Nexus sends payment.completed.
#     withdrawal_status = "PROCESSING"
#     now = datetime.now().isoformat()

#     conn = get_db()
#     try:
#         if withdrawal_id is not None:
#             conn.execute(
#                 """
#                 UPDATE withdrawals
#                 SET status=?, reference=?, provider_transaction_id=?,
#                     provider_message=?, updated_at=?,
#                     completed_at=?
#                 WHERE id=?
#                 """,
#                 (
#                     withdrawal_status,
#                     reference,
#                     str(provider_transaction_id) if provider_transaction_id else None,
#                     str(provider_message),
#                     now,
#                     None,
#                     withdrawal_id
#                 )
#             )
#         conn.commit()
#     finally:
#         conn.close()

#     return {
#         "reference": reference,
#         "provider_transaction_id": provider_transaction_id,
#         "status": withdrawal_status,
#         "message": str(provider_message)
#     }


# @app.route("/api/withdraw", methods=["POST"])
# def api_withdraw():
#     if "username" not in session:
#         return jsonify({"success": False, "error": "Unauthorized."}), 401

#     data = request.get_json(silent=True) or request.form
#     amount = safe_float(data.get("amount"))

#     if amount is None or amount <= 0:
#         return jsonify({"success": False, "error": "Invalid withdrawal amount."}), 400

#     if amount < MIN_WITHDRAWAL:
#         return jsonify({
#             "success": False,
#             "error": f"Minimum withdrawal is KES {MIN_WITHDRAWAL:,.0f}."
#         }), 400

#     if amount > MAX_WITHDRAWAL:
#         return jsonify({
#             "success": False,
#             "error": f"Maximum withdrawal is KES {MAX_WITHDRAWAL:,.2f}."
#         }), 400

#     if amount != round(amount):
#         return jsonify({
#             "success": False,
#             "error": "Withdrawal amount must be a whole KES amount."
#         }), 400

#     username = session["username"]
#     user = get_user(username)
#     if not user:
#         return jsonify({"success": False, "error": "User not found."}), 404

#     try:
#         target_phone = normalize_mpesa_phone(
#             data.get("phone_number") or user["phone_number"]
#         )
#     except ValueError as exc:
#         return jsonify({"success": False, "error": str(exc)}), 400

#     amount = int(round(amount))
#     reference = make_nexus_reference("WD", username)
#     now = datetime.now().isoformat()

#     # Reserve the money and create a transaction record atomically.
#     conn = get_db()
#     withdrawal_id = None
#     try:
#         conn.execute("BEGIN IMMEDIATE")
#         cursor = conn.execute(
#             """
#             UPDATE users
#             SET balance = balance - ?
#             WHERE username = ? AND balance >= ?
#             """,
#             (amount, username, amount)
#         )
#         if cursor.rowcount != 1:
#             conn.rollback()
#             return jsonify({
#                 "success": False,
#                 "error": "Insufficient balance for withdrawal."
#             }), 400

#         cursor = conn.execute(
#             """
#             INSERT INTO withdrawals
#             (
#                 username, phone_number, amount, status,
#                 reference, provider_message, created_at, updated_at
#             )
#             VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?)
#             """,
#             (
#                 username,
#                 target_phone,
#                 amount,
#                 reference,
#                 "Withdrawal request is being sent to Nexus Pay.",
#                 now,
#                 now
#             )
#         )
#         withdrawal_id = cursor.lastrowid
#         conn.commit()
#     except Exception as exc:
#         conn.rollback()
#         print("Withdrawal reservation error:", repr(exc))
#         return jsonify({"success": False, "error": "Database error during withdrawal."}), 500
#     finally:
#         conn.close()

#     try:
#         result = nexus_b2c_disbursement(
#             target_phone,
#             amount,
#             username,
#             withdrawal_id=withdrawal_id,
#             reference=reference
#         )

#         return jsonify({
#             "success": True,
#             "message": (
#                 f"Withdrawal of KES {amount:,.2f} has been submitted. "
#                 f"Status: {result['status']}."
#             ),
#             "withdrawal_id": withdrawal_id,
#             "reference": result["reference"],
#             "status": result["status"],
#             "provider_transaction_id": result["provider_transaction_id"]
#         }), 200

#     except requests.Timeout:
#         error_message = "Nexus Pay withdrawal request timed out."
#     except requests.HTTPError as exc:
#         response = getattr(exc, "response", None)
#         provider_message = None
#         if response is not None:
#             try:
#                 payload = response.json()
#                 provider_message = (
#                     payload.get("message")
#                     or payload.get("error")
#                     or payload.get("description")
#                 )
#             except Exception:
#                 provider_message = None
#         error_message = provider_message or "Nexus Pay rejected the withdrawal request."
#     except requests.RequestException:
#         error_message = "Could not connect to Nexus Pay for the withdrawal."
#     except Exception as exc:
#         print("Withdrawal provider error:", repr(exc))
#         error_message = str(exc) or "Withdrawal request failed."

#     # Provider failed before payout; return the reserved money to the user.
#     conn = get_db()
#     try:
#         conn.execute("BEGIN IMMEDIATE")
#         conn.execute(
#             "UPDATE users SET balance = balance + ? WHERE username = ?",
#             (amount, username)
#         )
#         conn.execute(
#             """
#             UPDATE withdrawals
#             SET status='FAILED', provider_message=?, updated_at=?
#             WHERE id=?
#             """,
#             (error_message, datetime.now().isoformat(), withdrawal_id)
#         )
#         conn.commit()
#     except Exception as exc:
#         conn.rollback()
#         print("Withdrawal refund error:", repr(exc))
#         error_message = "Withdrawal failed and the automatic refund could not be completed. Check the account before retrying."
#     finally:
#         conn.close()

#     return jsonify({
#         "success": False,
#         "error": error_message,
#         "withdrawal_id": withdrawal_id
#     }), 502


# # ============================================================
# # HEALTH CHECK
# # ============================================================

# @app.route("/health")
# def health():

#     return jsonify({
#         "status": "ok",
#         "game_status": GAME["status"],
#         "nexus_configured": bool(
#             NEXUS_PAY_API_KEY
#         )
#     })


# # ============================================================
# # ADMIN DASHBOARD / DEPOSIT APPROVAL / PASSWORD RESET OTP
# # ============================================================
# ADMIN_HTML = r"""
# <!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aviator Admin</title>
# <style>*{box-sizing:border-box}body{margin:0;background:#0e1015;color:#edf2f7;font:14px Arial,sans-serif}header{padding:16px 4%;background:#181c24;display:flex;justify-content:space-between;align-items:center;gap:12px;position:sticky;top:0;z-index:10}.admin-head-left{display:flex;align-items:center;gap:12px}.admin-menu{display:none;background:#303846;color:#fff;border:1px solid #566174;border-radius:7px;padding:8px 12px;font-size:18px}main{padding:24px 4%;max-width:1400px;margin:auto}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.card,section{background:#181c24;border:1px solid #303846;border-radius:10px;padding:16px;margin-bottom:18px}.num{font-size:25px;color:#39d98a;font-weight:bold}h2{font-size:18px}table{width:100%;border-collapse:collapse;overflow:auto}th,td{text-align:left;padding:10px;border-bottom:1px solid #303846;vertical-align:top}button{background:#28a745;color:white;border:0;border-radius:5px;padding:8px 11px;cursor:pointer}a{color:#7db6ff}small{color:#aab4c4}.scroll{overflow:auto}.warning{color:#ffca6b}@media(max-width:600px){header{padding:10px 4%}.admin-menu{display:inline-flex}main{padding:15px 3%}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.card,section{padding:12px}.num{font-size:20px}th,td{padding:8px;font-size:12px;white-space:normal}section .scroll{max-width:100%}header.admin-collapsed .admin-brand{display:none}header.admin-collapsed{justify-content:flex-start}header.admin-collapsed .admin-head-left{flex:1}header.admin-collapsed .admin-user{display:block}header.admin-collapsed .admin-logout{display:none}header:not(.admin-expanded) .admin-nav{display:none}header.admin-expanded .admin-nav{display:flex;flex-wrap:wrap;gap:12px;width:100%;padding:10px 0}header{flex-wrap:wrap}}</style></head><body>
# <header id="adminHeader" class="admin-collapsed"><div class="admin-head-left"><button class="admin-menu" type="button" onclick="toggleAdminMenu()" aria-label="Toggle admin menu">☰</button><div class="admin-brand"><b>AVIATOR · ADMIN CONSOLE</b><br><small>Signed in as {{ admin }}</small></div><small class="admin-user">@{{ admin }}</small></div><nav class="admin-nav"><a href="#round-monitor">Next round</a><a href="#signal-approvals">Signal approvals</a><a href="#signal-management">Manage signals</a><a href="#deposit-approvals">Deposit approvals</a></nav><a class="admin-logout" href="/logout">Log out</a></header><main>
# <section id="round-monitor"><h2>Live round monitor · Upcoming round number</h2>
# <div class="cards">
# <div class="card">Current round<div class="num" id="admin-current-round">#{{ round_monitor.current_round or '—' }}</div></div>
# <div class="card">Current status<div class="num" id="admin-round-status">{{ round_monitor.status }}</div></div>
# <div class="card">Next round<div class="num" id="admin-next-round">#{{ round_monitor.next_round or '—' }}</div></div>
# <div class="card">Betting window<div class="num"><span id="admin-betting-seconds">{{ round_monitor.betting_seconds }}</span> sec</div></div>
# </div>
# <p><small>Round status updates as the game engine advances. The next round number is shown without revealing its crash result or future outcome.</small></p></section>
# <div class="cards"><div class="card">Registered users<div class="num">{{ stats.users }}</div></div><div class="card">Active players (last 5 min)<div class="num">{{ stats.active }}</div></div><div class="card">Verified deposits awaiting approval<div class="num">{{ stats.pending_count }}</div></div><div class="card">Total confirmed deposits<div class="num">KES {{ '%.2f'|format(stats.deposit_total) }}</div></div><div class="card">Pending deposit value<div class="num">KES {{ '%.2f'|format(stats.pending_total) }}</div></div><div class="card">Confirmed signal sales<div class="num">KES {{ '%.2f'|format(stats.signal_sales_total) }}</div></div><div class="card">Active signal subscriptions<div class="num">{{ stats.signal_active }}</div></div><div class="card">Verified signal payments awaiting approval<div class="num">{{ stats.signal_pending_approval }}</div></div></div>
# <section id="deposit-approvals"><h2>Payment-verified deposits awaiting approval</h2><p class="warning">Approval credits the user's spendable balance. Pending/unverified deposits cannot be used for betting.</p><div class="scroll"><table><tr><th>Reference</th><th>User / phone</th><th>Amount</th><th>Status</th><th>Created</th><th>Action</th></tr>{% for tx in deposits %}<tr><td>{{ tx.reference }}</td><td>{{ tx.username }}<br>{{ tx.phone_number }}</td><td>KES {{ '%.2f'|format(tx.amount) }}</td><td>{{ tx.status }}</td><td>{{ tx.created_at }}</td><td>{% if tx.status == 'PAYMENT_VERIFIED' %}<form method="post" action="/admin/deposits/{{ tx.id }}/approve"><input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Approve & credit</button></form>{% else %}—{% endif %}</td></tr>{% else %}<tr><td colspan="6">No deposits awaiting approval.</td></tr>{% endfor %}</table></div></section>
# <section><h2>Registered users</h2><div class="scroll"><table><tr><th>ID</th><th>Username</th><th>Phone</th><th>Role</th><th>Spendable balance</th><th>Created</th><th>Last active</th></tr>{% for u in users %}<tr><td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ u.phone_number }}</td><td>{{ u.role }}</td><td>KES {{ '%.2f'|format(u.balance) }}</td><td>{{ u.created_at }}</td><td>{{ u.last_seen_at or '—' }}</td></tr>{% endfor %}</table></div></section>
# <section><h2>Recent deposit and withdrawal records</h2><div class="scroll"><table><tr><th>Type</th><th>User</th><th>Amount</th><th>Status</th><th>Reference / Provider ID</th><th>Updated</th></tr>{% for t in tx_history %}<tr><td>Deposit</td><td>{{ t.username }}</td><td>KES {{ '%.2f'|format(t.amount) }}</td><td>{{ t.status }}</td><td>{{ t.reference }}<br>{{ t.provider_transaction_id or '' }}</td><td>{{ t.updated_at }}</td></tr>{% endfor %}{% for w in withdrawals %}<tr><td>Withdrawal</td><td>{{ w.username }}</td><td>KES {{ '%.2f'|format(w.amount) }}</td><td>{{ w.status }}</td><td>{{ w.reference or '—' }}<br>{{ w.provider_transaction_id or '' }}</td><td>{{ w.updated_at }}</td></tr>{% endfor %}</table></div></section>
# <section id="signal-management"><h2>Automatically generated round estimates</h2><p class="warning">The system automatically creates the next 10 round entries. Multipliers are synthetic sample values, not forecasts and not derived from future crash results. No algorithm can reliably know random Aviator outcomes.</p>
# <p class="warning">The system automatically generates the next 10 round entries. The displayed multiplier is a synthetic sample only; it is not a forecast, and no algorithm can reliably know random Aviator outcomes.</p>
# <div class="scroll"><table><tr><th>Round</th><th>Generated time</th><th>Sample estimate</th><th>Type</th><th>Explanation</th><th>Action</th></tr>{% for sig in published_signals %}<tr><td>{{ sig.round_label }}</td><td>{{ sig.signal_time }}</td><td>{{ '%.2f'|format(sig.predicted_multiplier) }}x</td><td>{{ sig.confidence }}</td><td>{{ sig.notes or '—' }}</td><td><form method="post" action="/admin/signals/{{ sig.id }}/delete"><input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Remove</button></form></td></tr>{% else %}<tr><td colspan="6">No published signals.</td></tr>{% endfor %}</table></div></section>
# <section id="signal-approvals"><h2>Aviator prediction / signal payment approvals</h2><p class="warning">Only payment-verified orders can be approved. Verify the payment reference in Nexus Pay before granting signal access. A customer never receives admin permissions.</p><div class="scroll"><table><tr><th>Player</th><th>Package</th><th>Amount</th><th>Status</th><th>Reference</th><th>Action / expiry</th></tr>{% for o in signal_orders %}<tr><td>{{ o.username }}<br>{{ o.phone_number }}</td><td>{{ o.plan_minutes }} minutes</td><td>KES {{ '%.2f'|format(o.amount) }}</td><td>{{ o.status }}</td><td>{{ o.reference }}</td><td>{% if o.status == 'PAYMENT_VERIFIED' %}<form method="post" action="/admin/signals/orders/{{ o.id }}/approve" onsubmit="return confirm('Confirm you independently verified this exact payment in Nexus Pay and want to activate signal access?')"><input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Approve signal access</button></form>{% else %}{{ o.expires_at or '—' }}{% endif %}</td></tr>{% else %}<tr><td colspan="6">No signal orders yet.</td></tr>{% endfor %}</table></div></section>
# <section><h2>Admin audit log</h2><div class="scroll"><table><tr><th>When</th><th>Admin</th><th>Action</th><th>Target</th><th>Details</th><th>IP</th></tr>{% for a in audits %}<tr><td>{{ a.created_at }}</td><td>{{ a.admin_username }}</td><td>{{ a.action }}</td><td>{{ a.target_username or '—' }}</td><td>{{ a.details }}</td><td>{{ a.ip_address }}</td></tr>{% endfor %}</table></div></section>
# </main><script>
# async function refreshRoundMonitor(){
#   try {
#     const response = await fetch('/admin/round-status', {credentials:'same-origin', cache:'no-store'});
#     if(!response.ok) return;
#     const data = await response.json();
#     document.getElementById('admin-current-round').textContent = '#' + (data.current_round ?? '—');
#     document.getElementById('admin-round-status').textContent = data.status;
#     document.getElementById('admin-next-round').textContent = '#' + (data.next_round ?? '—');
#     document.getElementById('admin-betting-seconds').textContent = data.betting_seconds;
#   } catch (_) {}
# }
# setInterval(refreshRoundMonitor, 1000);
# refreshRoundMonitor();
# </script><script>function toggleAdminMenu(){const h=document.getElementById('adminHeader');h.classList.toggle('admin-expanded');h.classList.toggle('admin-collapsed');}</script></body></html>
# """


# def _csrf_token():
#     if "csrf_token" not in session:
#         session["csrf_token"] = secrets.token_urlsafe(32)
#     return session["csrf_token"]


# def _check_csrf():
#     return secrets.compare_digest(str(request.form.get("csrf_token", "")), str(session.get("csrf_token", "")))


# @app.route("/admin/round-status")
# def admin_round_status():
#     if not admin_required():
#         return jsonify({"error": "Unauthorized"}), 401
#     with GAME_LOCK:
#         current_round = GAME.get("round_id")
#         status = str(GAME.get("status") or "WAITING")
#         seconds = BETTING_WINDOW
#         if status == "BETTING" and GAME.get("betting_start") is not None:
#             seconds = max(0, int(BETTING_WINDOW - (time.time() - GAME["betting_start"])))
#         return jsonify({
#             "current_round": current_round,
#             "next_round": (int(current_round) + 1) if current_round is not None else 1,
#             "status": status,
#             "betting_seconds": seconds,
#         })


# @app.route("/admin")
# def admin_dashboard():
#     if not admin_required():
#         return redirect("/lobby" if "username" in session else "/login")
#     touch_user(session["username"])
#     ensure_generated_signals(current_next_round_number(), 10)
#     conn = get_db()
#     try:
#         stats = {
#             "users": conn.execute("SELECT COUNT(*) FROM users WHERE role!='ADMIN'").fetchone()[0],
#             "active": conn.execute("SELECT COUNT(*) FROM users WHERE role!='ADMIN' AND last_seen_at >= ?", ((datetime.now()-timedelta(minutes=5)).isoformat(),)).fetchone()[0],
#             "pending_count": conn.execute("SELECT COUNT(*) FROM nexus_transactions WHERE status='PAYMENT_VERIFIED'").fetchone()[0],
#             "pending_total": conn.execute("SELECT COALESCE(SUM(amount),0) FROM nexus_transactions WHERE status IN ('PENDING','PAYMENT_VERIFIED')").fetchone()[0],
#             "deposit_total": conn.execute("SELECT COALESCE(SUM(amount),0) FROM nexus_transactions WHERE status IN ('APPROVED','SUCCESS')").fetchone()[0],
#             "signal_sales_total": conn.execute("SELECT COALESCE(SUM(amount),0) FROM signal_orders WHERE status='PAID'").fetchone()[0],
#             "signal_active": conn.execute("SELECT COUNT(*) FROM signal_orders WHERE status='PAID' AND expires_at> ?", (datetime.now().isoformat(),)).fetchone()[0],
#             "signal_pending_approval": conn.execute("SELECT COUNT(*) FROM signal_orders WHERE status='PAYMENT_VERIFIED'").fetchone()[0],
#         }
#         users = conn.execute("SELECT id,username,phone_number,role,balance,created_at,last_seen_at FROM users ORDER BY created_at DESC LIMIT 500").fetchall()
#         deposits = conn.execute("SELECT id,username,phone_number,amount,reference,status,created_at FROM nexus_transactions WHERE status IN ('PAYMENT_VERIFIED','PENDING') ORDER BY created_at DESC LIMIT 200").fetchall()
#         tx_history = conn.execute("SELECT username,amount,reference,status,provider_transaction_id,updated_at FROM nexus_transactions ORDER BY created_at DESC LIMIT 100").fetchall()
#         withdrawals = conn.execute("SELECT username,amount,status,reference,provider_transaction_id,updated_at FROM withdrawals ORDER BY created_at DESC LIMIT 100").fetchall()
#         audits = conn.execute("SELECT * FROM admin_audit_logs ORDER BY id DESC LIMIT 100").fetchall()
#         signal_orders = conn.execute("SELECT * FROM signal_orders ORDER BY id DESC LIMIT 100").fetchall()
#         published_signals = conn.execute("SELECT * FROM aviator_signals WHERE status='PUBLISHED' ORDER BY COALESCE(round_number, 0) ASC, id DESC LIMIT 100").fetchall()
#     finally:
#         conn.close()
#     with GAME_LOCK:
#         current_round = GAME.get("round_id")
#         game_status = str(GAME.get("status") or "WAITING")
#         betting_seconds = BETTING_WINDOW
#         if game_status == "BETTING" and GAME.get("betting_start") is not None:
#             betting_seconds = max(0, int(BETTING_WINDOW - (time.time() - GAME["betting_start"])))
#         round_monitor = {
#             "current_round": current_round,
#             "next_round": (int(current_round) + 1) if current_round is not None else 1,
#             "status": game_status,
#             "betting_seconds": betting_seconds,
#         }
#     return render_template_string(ADMIN_HTML, admin=session["username"], stats=stats, users=users, deposits=deposits, tx_history=tx_history, withdrawals=withdrawals, audits=audits, signal_orders=signal_orders, published_signals=published_signals, round_monitor=round_monitor, csrf=_csrf_token())


# @app.route("/admin/deposits/<int:transaction_id>/approve", methods=["POST"])
# def admin_approve_deposit(transaction_id):
#     if not admin_required():
#         return redirect("/login")
#     if not _check_csrf():
#         return "Invalid request token. Refresh the admin page and try again.", 400
#     conn = get_db()
#     try:
#         conn.execute("BEGIN IMMEDIATE")
#         tx = conn.execute("SELECT * FROM nexus_transactions WHERE id=?", (transaction_id,)).fetchone()
#         if not tx:
#             conn.rollback()
#             return "Deposit not found.", 404
#         if tx["status"] in ("APPROVED", "SUCCESS"):
#             conn.commit()
#             return redirect("/admin")
#         if tx["status"] != "PAYMENT_VERIFIED":
#             conn.rollback()
#             return "Only payment-verified deposits can be approved.", 409
#         now = datetime.now().isoformat()
#         cur = conn.execute("UPDATE nexus_transactions SET status='APPROVED', approved_by=?, approved_at=?, credited_at=?, updated_at=?, provider_message=? WHERE id=? AND status='PAYMENT_VERIFIED'",
#             (session["username"], now, now, now, "Payment verified and approved by administrator.", transaction_id))
#         if cur.rowcount != 1:
#             conn.rollback()
#             return "Deposit approval conflict; refresh and retry.", 409
#         cur = conn.execute("UPDATE users SET balance=balance+? WHERE username=?", (float(tx["amount"]), tx["username"]))
#         if cur.rowcount != 1:
#             conn.rollback()
#             return "User not found; no credit applied.", 409
#         conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
#             (session["username"], "DEPOSIT_APPROVED", tx["username"], f"Reference={tx['reference']}; amount={float(tx['amount']):.2f}; transaction_id={transaction_id}", request.headers.get("X-Forwarded-For", request.remote_addr), now))
#         conn.commit()
#     finally:
#         conn.close()
#     return redirect("/admin")


# @app.route("/forgot-password", methods=["GET", "POST"])
# def forgot_password():
#     error = None
#     message = None
#     if request.method == "POST":
#         username = request.form.get("username", "").strip()
#         # Always use a generic response to avoid account enumeration.
#         conn = get_db()
#         try:
#             user = conn.execute("SELECT username,phone_number FROM users WHERE username=? AND role!='ADMIN'", (username,)).fetchone()
#             recent = conn.execute("SELECT COUNT(*) FROM password_reset_otps WHERE username=? AND created_at>=?", (username, (datetime.now()-timedelta(minutes=15)).isoformat())).fetchone()[0]
#             if user and recent < 3:
#                 code = f"{secrets.randbelow(1000000):06d}"
#                 otp_hash = hashlib.sha256((code + str(app.secret_key)).encode()).hexdigest()
#                 now = datetime.now()
#                 conn.execute("INSERT INTO password_reset_otps(username,otp_hash,expires_at,created_at,request_ip) VALUES(?,?,?,?,?)",
#                     (username, otp_hash, (now+timedelta(minutes=OTP_TTL_MINUTES)).isoformat(), now.isoformat(), request.remote_addr))
#                 conn.commit()
#                 try:
#                     send_at_otp(user["phone_number"], code)
#                 except Exception as exc:
#                     app.logger.error("Africa's Talking OTP send failed: %s", exc)
#                     error = "Could not send SMS right now. Check SMS configuration or try later."
#                 else:
#                     session["reset_username"] = username
#                     message = "If the account exists, an OTP has been sent to its registered phone."
#             else:
#                 message = "If the account exists, an OTP has been sent to its registered phone."
#         finally:
#             conn.close()
#     return render_template_string(FORGOT_HTML, error=error, message=message)


# @app.route("/reset-password", methods=["GET", "POST"])
# def reset_password():
#     error = None
#     message = None
#     username = session.get("reset_username")
#     if request.method == "POST":
#         code = request.form.get("otp", "").strip()
#         password = request.form.get("password", "")
#         confirm = request.form.get("confirm_password", "")
#         if not username:
#             error = "Request a password reset code first."
#         elif len(password) < 10:
#             error = "Password must be at least 10 characters."
#         elif password != confirm:
#             error = "Passwords do not match."
#         elif not re.fullmatch(r"\d{6}", code):
#             error = "Enter the 6-digit OTP."
#         else:
#             conn = get_db()
#             try:
#                 conn.execute("BEGIN IMMEDIATE")
#                 otp = conn.execute("SELECT * FROM password_reset_otps WHERE username=? AND used_at IS NULL ORDER BY id DESC LIMIT 1", (username,)).fetchone()
#                 if not otp or datetime.fromisoformat(otp["expires_at"]) < datetime.now() or otp["attempts"] >= 5:
#                     error = "The code expired or is invalid. Request a new one."
#                 else:
#                     digest = hashlib.sha256((code + str(app.secret_key)).encode()).hexdigest()
#                     conn.execute("UPDATE password_reset_otps SET attempts=attempts+1 WHERE id=?", (otp["id"],))
#                     if not secrets.compare_digest(digest, otp["otp_hash"]):
#                         error = "The code expired or is invalid. Request a new one."
#                     else:
#                         now = datetime.now().isoformat()
#                         conn.execute("UPDATE users SET password=? WHERE username=?", (hash_password(password), username))
#                         conn.execute("UPDATE password_reset_otps SET used_at=? WHERE username=? AND used_at IS NULL", (now, username))
#                         conn.commit()
#                         session.pop("reset_username", None)
#                         session.clear()
#                         message = "Password reset successfully. You can now log in."
#                 if error:
#                     conn.commit()
#             finally:
#                 conn.close()
#     return render_template_string(RESET_HTML, error=error, message=message)

# FORGOT_HTML = r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forgot password</title><style>body{background:#0e1015;color:white;font:16px Arial;display:grid;place-items:center;min-height:100vh}.box{background:#181c24;padding:28px;border-radius:12px;width:min(340px,85vw)}input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:6px}input{background:#0e1015;color:white;border:1px solid #303846}button{background:#28a745;color:white;border:0}a{color:#7db6ff}.err{color:#ff8b8b}.ok{color:#5ee09a}</style></head><body><div class="box"><h2>Reset password</h2><p>Enter your username. We'll send a code to the registered phone if eligible.</p>{% if error %}<p class="err">{{ error }}</p>{% endif %}{% if message %}<p class="ok">{{ message }}</p><a href="/reset-password">Enter OTP and set new password</a>{% endif %}<form method="post"><label>Username</label><input name="username" required autocomplete="username"><button>Send OTP by SMS</button></form><a href="/login">Back to login</a></div></body></html>"""
# RESET_HTML = r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Set new password</title><style>body{background:#0e1015;color:white;font:16px Arial;display:grid;place-items:center;min-height:100vh}.box{background:#181c24;padding:28px;border-radius:12px;width:min(340px,85vw)}input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:6px}input{background:#0e1015;color:white;border:1px solid #303846}button{background:#28a745;color:white;border:0}a{color:#7db6ff}.err{color:#ff8b8b}.ok{color:#5ee09a}</style></head><body><div class="box"><h2>Set new password</h2>{% if error %}<p class="err">{{ error }}</p>{% endif %}{% if message %}<p class="ok">{{ message }}</p><a href="/login">Go to login</a>{% else %}<form method="post"><label>6-digit SMS OTP</label><input name="otp" inputmode="numeric" pattern="[0-9]{6}" required><label>New password (minimum 10 characters)</label><input name="password" type="password" minlength="10" required><label>Confirm new password</label><input name="confirm_password" type="password" minlength="10" required><button>Reset password</button></form>{% endif %}<a href="/forgot-password">Request another code</a></div></body></html>"""

# # ============================================================
# # LOGIN PAGE
# # ============================================================

# LOGIN_HTML = r"""
# <!DOCTYPE html>

# <html lang="en">

# <head>

# <meta charset="UTF-8">

# <meta
#     name="viewport"
#     content="width=device-width, initial-scale=1.0"
# >

# <title>Aviator - Login</title>

# <style>

# body {
#     margin: 0;
#     min-height: 100vh;

#     display: flex;
#     justify-content: center;
#     align-items: center;

#     background: #0e1015;

#     font-family: sans-serif;
#     color: #fff;
# }

# .box {
#     width: 100%;
#     max-width: 360px;

#     padding: 30px;

#     border-radius: 12px;

#     background: #181c24;

#     border: 1px solid #282f3d;

#     box-sizing: border-box;
# }

# h2 {
#     text-align: center;
#     color: #28a745;
#     margin-top: 0;
# }

# input {
#     width: 100%;

#     padding: 12px;

#     margin: 8px 0 16px;

#     border-radius: 6px;

#     border: 1px solid #282f3d;

#     background: #0e1015;

#     color: #fff;

#     box-sizing: border-box;
# }

# .remember-row {
#     display: flex;
#     align-items: center;
#     gap: 9px;
#     margin: 2px 0 16px;
#     color: #b9c0cc;
#     font-size: 13px;
#     line-height: 1.4;
# }
# .remember-row input {
#     width: auto;
#     margin: 0;
#     accent-color: #28a745;
# }

# button {
#     width: 100%;

#     padding: 12px;

#     border: none;

#     border-radius: 6px;

#     background: #28a745;

#     color: #fff;

#     font-weight: bold;

#     cursor: pointer;

#     font-size: 16px;
# }

# .error {
#     color: #e53e3e;

#     text-align: center;

#     margin-bottom: 12px;

#     font-size: 14px;
# }

# a {
#     color: #28a745;

#     text-decoration: none;
# }

# </style>

# </head>

# <body>

# <div class="box">

#     <h2>✈️ AVIATOR LOGIN</h2>

#     {% if error %}
#         <div class="error">
#             {{ error }}
#         </div>
#     {% endif %}

#     <form method="POST">

#         <label>Username</label>

#         <input
#             type="text"
#             name="username"
#             required
#             autocomplete="username"
#         >

#         <label>Password</label>

#         <input
#             type="password"
#             name="password"
#             required
#             autocomplete="current-password"
#         >

#         <label class="remember-row">
#             <input type="checkbox" name="remember" value="1" checked>
#             Keep me logged in on this device (30 days)
#         </label>

#         <button type="submit">
#             LOG IN
#         </button>

#     </form>
# <p style="text-align:center"><a href="/forgot-password" style="color:#7db6ff">Forgot password?</a></p>

#     <p
#         style="
#             text-align:center;
#             font-size:14px;
#             color:#888;
#         "
#     >
#         No account?
#         <a href="/register">
#             Register
#         </a>
#     </p>

# </div>

# </body>

# </html>
# """


# # ============================================================
# # REGISTER PAGE
# # ============================================================

# REGISTER_HTML = r"""
# <!DOCTYPE html>

# <html lang="en">

# <head>

# <meta charset="UTF-8">

# <meta
#     name="viewport"
#     content="width=device-width, initial-scale=1.0"
# >

# <title>Aviator - Register</title>

# <style>

# body {
#     margin: 0;

#     min-height: 100vh;

#     display: flex;

#     justify-content: center;

#     align-items: center;

#     background: #0e1015;

#     font-family: sans-serif;

#     color: #fff;
# }

# .box {
#     width: 100%;

#     max-width: 360px;

#     padding: 30px;

#     border-radius: 12px;

#     background: #181c24;

#     border: 1px solid #282f3d;

#     box-sizing: border-box;
# }

# h2 {
#     text-align: center;

#     color: #28a745;

#     margin-top: 0;
# }

# input {
#     width: 100%;

#     padding: 12px;

#     margin: 8px 0 16px;

#     border-radius: 6px;

#     border: 1px solid #282f3d;

#     background: #0e1015;

#     color: #fff;

#     box-sizing: border-box;
# }

# button {
#     width: 100%;

#     padding: 12px;

#     border: none;

#     border-radius: 6px;

#     background: #28a745;

#     color: #fff;

#     font-weight: bold;

#     cursor: pointer;

#     font-size: 16px;
# }

# .error {
#     color: #e53e3e;

#     text-align: center;

#     margin-bottom: 12px;

#     font-size: 14px;
# }

# a {
#     color: #28a745;

#     text-decoration: none;
# }

# </style>

# </head>

# <body>

# <div class="box">

#     <h2>✈️ CREATE ACCOUNT</h2>

#     {% if error %}
#         <div class="error">
#             {{ error }}
#         </div>
#     {% endif %}

#     <form method="POST">

#         <label>Username</label>

#         <input
#             type="text"
#             name="username"
#             required
#             autocomplete="username"
#         >

#         <label>
#             M-Pesa Phone Number
#         </label>

#         <input
#             type="text"
#             name="phone_number"
#             placeholder="0712345678"
#             required
#         >

#         <label>Password</label>

#         <input
#             type="password"
#             name="password"
#             required
#             minlength="6"
#             autocomplete="new-password"
#         >

#         <button type="submit">
#             SIGN UP
#         </button>

#     </form>

#     <p
#         style="
#             text-align:center;
#             font-size:14px;
#             color:#888;
#         "
#     >
#         Already have an account?

#         <a href="/login">
#             Login
#         </a>
#     </p>

# </div>

# </body>

# </html>
# """


# # ============================================================
# # MAIN GAME HTML
# # ============================================================

# HTML = r"""
# <!DOCTYPE html>

# <html lang="en">

# <head>

# <meta charset="UTF-8">

# <meta
#     name="viewport"
#     content="width=device-width, initial-scale=1.0"
# >

# <title>Aviator Game Interface</title>

# <style>

# * {
#     box-sizing: border-box;
# }

# body {
#     margin: 0;

#     padding: 0;

#     background-color: #000;

#     font-family:
#         -apple-system,
#         BlinkMacSystemFont,
#         "Segoe UI",
#         Roboto,
#         sans-serif;

#     color: #fff;

#     user-select: none;
# }

# /* ==========================================================
#    HEADER
#    ========================================================== */

# .header {
#     display: flex;

#     justify-content: space-between;

#     align-items: center;

#     background: #1b1c20;

#     padding: 10px 16px;

#     border-bottom: 1px solid #2a2b30;

#     gap: 12px;
# }

# .brand {
#     font-size: 20px;

#     font-weight: 900;

#     color: #28a745;

#     letter-spacing: 1px;
# }

# .player-username {
#     display: inline-flex;
#     align-items: center;
#     padding: 6px 10px;
#     border: 1px solid #303846;
#     border-radius: 999px;
#     color: #d9e2f0;
#     background: #171b23;
#     font-size: 12px;
#     font-weight: 700;
#     white-space: nowrap;
# }

# .wallet {
#     display: flex;

#     align-items: center;

#     gap: 10px;

#     flex-wrap: wrap;

#     justify-content: flex-end;
# }

# .mobile-menu-toggle {
#     display: none;
#     border: 1px solid #3a4656;
#     border-radius: 8px;
#     background: #171b23;
#     color: #fff;
#     padding: 7px 10px;
#     font-size: 18px;
#     line-height: 1;
#     cursor: pointer;
# }

# .balance {
#     color: #28a745;

#     font-weight: bold;

#     font-size: 16px;
# }

# .deposit-btn,
# .withdraw-btn {
#     color: #fff;

#     font-weight: bold;

#     border: none;

#     padding: 8px 16px;

#     border-radius: 20px;

#     cursor: pointer;

#     font-size: 13px;
# }

# .deposit-btn {
#     background: #28a745;
# }

# .withdraw-btn {
#     background: #007bff;
# }

# /* ==========================================================
#    ADMIN
#    ========================================================== */

# .admin-banner {
#     display: none;

#     background: #d97706;

#     color: #fff;

#     text-align: center;

#     font-weight: bold;

#     padding: 6px;

#     font-size: 14px;

#     border-bottom: 2px solid #b45309;
# }

# /* ==========================================================
#    MODAL
#    ========================================================== */

# .mpesa-modal {
#     display: none;

#     position: fixed;

#     inset: 0;

#     z-index: 9999;

#     background: rgba(0, 0, 0, .72);

#     align-items: center;

#     justify-content: center;
# }

# .mpesa-card {
#     width: min(420px, 92vw);

#     background: #17191f;

#     border: 1px solid #30343e;

#     border-radius: 16px;

#     padding: 22px;

#     box-shadow:
#         0 20px 70px
#         rgba(0, 0, 0, .5);
# }

# .mpesa-card h3 {
#     margin: 0 0 6px;

#     color: #28a745;
# }

# .mpesa-card p {
#     color: #aaa;

#     font-size: 13px;

#     line-height: 1.45;
# }

# .mpesa-card label {
#     display: block;

#     color: #ddd;

#     font-size: 12px;

#     margin: 14px 0 6px;
# }

# .mpesa-card input {
#     width: 100%;

#     padding: 12px;

#     border-radius: 8px;

#     border: 1px solid #333844;

#     background: #0d0f13;

#     color: #fff;
# }

# .mpesa-actions {
#     display: flex;

#     gap: 10px;

#     margin-top: 16px;
# }

# .mpesa-actions button {
#     flex: 1;

#     padding: 12px;

#     border: 0;

#     border-radius: 8px;

#     cursor: pointer;

#     font-weight: 700;
# }

# .mpesa-pay {
#     background: #28a745;

#     color: #fff;
# }

# .mpesa-cancel {
#     background: #30343e;

#     color: #fff;
# }

# .mpesa-status {
#     margin-top: 12px;

#     min-height: 18px;

#     font-size: 12px;

#     color: #bbb;
# }

# .mpesa-amount-warning {
#     display: none;
#     margin-top: 8px;
#     padding: 9px 11px;
#     border: 1px solid #dc2626;
#     border-radius: 6px;
#     background: rgba(220, 38, 38, 0.12);
#     color: #ff4d4f;
#     font-size: 13px;
#     font-weight: 700;
# }

# .mpesa-amount-warning.visible {
#     display: block;
# }

# /* ==========================================================
#    MAIN
#    ========================================================== */

# .main-layout {
#     max-width: 1200px;

#     margin: 0 auto;

#     padding: 10px;
# }

# /* ==========================================================
#    HISTORY
#    ========================================================== */

# .history-line {
#     display: flex;

#     gap: 8px;

#     overflow-x: auto;

#     padding: 6px 0;

#     margin-bottom: 8px;

#     scrollbar-width: none;
# }

# .history-line::-webkit-scrollbar {
#     display: none;
# }

# .hist-item {
#     font-size: 13px;

#     font-weight: 700;

#     padding: 2px 8px;

#     border-radius: 10px;

#     white-space: nowrap;
# }

# .hist-blue {
#     color: #3498db;
# }

# .hist-purple {
#     color: #9b59b6;
# }

# .hist-pink {
#     color: #e91e63;
# }

# /* ==========================================================
#    GAME STAGE
#    ========================================================== */

# .stage {
#     position: relative;

#     width: 100%;

#     height: 320px;

#     background:
#         radial-gradient(
#             circle at 10% 90%,
#             #20081e 0%,
#             #0d060e 100%
#         );

#     border-radius: 12px 12px 0 0;

#     overflow: hidden;

#     border: 1px solid #2a2c33;
# }

# canvas {
#     width: 100%;

#     height: 100%;

#     display: block;
# }

# .multiplier-overlay {
#     position: absolute;

#     top: 40%;

#     left: 50%;

#     transform:
#         translate(-50%, -50%);

#     font-size: 64px;

#     font-weight: 900;

#     text-align: center;

#     color: #fff;

#     z-index: 10;

#     text-shadow:
#         0 0 15px
#         rgba(0, 0, 0, .8);

#     white-space: pre-line;
# }

# .crashed-text {
#     color: #e53e3e;

#     text-shadow:
#         0 0 10px
#         rgba(229, 62, 62, .6);
# }

# /* ==========================================================
#    CONTROLS
#    ========================================================== */

# .panels-container {
#     display: grid;

#     grid-template-columns: 1fr 1fr;

#     gap: 10px;

#     background: #141518;

#     padding: 10px;

#     border-radius: 0 0 12px 12px;

#     border: 1px solid #2a2c33;

#     border-top: none;
# }

# .bet-box {
#     background: #1b1c21;

#     border-radius: 10px;

#     padding: 10px;

#     border: 1px solid #25272e;
# }

# .toggle-bar {
#     display: flex;

#     justify-content: center;

#     background: #0e0f12;

#     border-radius: 15px;

#     padding: 2px;

#     margin-bottom: 8px;

#     width: 160px;

#     margin-left: auto;

#     margin-right: auto;
# }

# .toggle-btn {
#     flex: 1;

#     text-align: center;

#     padding: 4px 0;

#     font-size: 12px;

#     border-radius: 13px;

#     cursor: pointer;

#     color: #888;

#     font-weight: bold;
# }

# .toggle-btn.active {
#     background: #252830;

#     color: #fff;
# }

# .auto-options {
#     display: none;

#     margin-bottom: 8px;

#     gap: 8px;

#     align-items: center;

#     justify-content: center;
# }

# .auto-options.show {
#     display: flex;
# }

# .auto-input {
#     width: 80px;

#     background: #0e1013;

#     border: 1px solid #2a2c33;

#     color: #fff;

#     border-radius: 6px;

#     padding: 4px;

#     text-align: center;

#     font-weight: bold;
# }

# .controls-flex {
#     display: flex;

#     gap: 10px;

#     align-items: center;
# }

# .left-inputs {
#     flex: 1;
# }

# .input-stepper {
#     display: flex;

#     align-items: center;

#     background: #0e1013;

#     border-radius: 20px;

#     padding: 2px;

#     border: 1px solid #2a2c33;
# }

# .step-btn {
#     width: 32px;

#     height: 32px;

#     border-radius: 50%;

#     border: none;

#     background: #1b1c21;

#     color: #888;

#     font-size: 18px;

#     cursor: pointer;

#     display: flex;

#     align-items: center;

#     justify-content: center;
# }

# .step-btn:hover {
#     color: #fff;
# }

# .amount-input {
#     flex: 1;

#     background: transparent;

#     border: none;

#     color: #fff;

#     font-size: 16px;

#     font-weight: bold;

#     text-align: center;

#     width: 100%;

#     outline: none;
# }

# .quick-bets {
#     display: grid;

#     grid-template-columns: 1fr 1fr;

#     gap: 4px;

#     margin-top: 6px;
# }

# .q-btn {
#     background: #121316;

#     border: 1px solid #22242b;

#     color: #aaa;

#     border-radius: 10px;

#     padding: 4px;

#     font-size: 11px;

#     cursor: pointer;

#     text-align: center;
# }

# .q-btn:hover {
#     color: #fff;

#     border-color: #444;
# }

# .action-btn {
#     flex: 1.1;

#     height: 82px;

#     border: none;

#     border-radius: 12px;

#     font-weight: 900;

#     cursor: pointer;

#     display: flex;

#     flex-direction: column;

#     justify-content: center;

#     align-items: center;

#     transition: all .2s;
# }

# .btn-green {
#     background: #28a745;

#     color: #fff;
# }

# .btn-green:hover {
#     background: #218838;
# }

# .btn-orange {
#     background: #d97706;

#     color: #fff;
# }

# .btn-orange:hover {
#     background: #b45309;
# }

# .btn-blue {
#     background: #007bff;

#     color: #fff;
# }

# .btn-disabled {
#     background: #333 !important;

#     color: #666 !important;

#     cursor: not-allowed;
# }

# .btn-title {
#     font-size: 18px;
# }

# .btn-sub {
#     font-size: 16px;

#     margin-top: 2px;
# }

# /* ==========================================================
#    FEED
#    ========================================================== */

# .feed-section {
#     margin-top: 15px;

#     background: #141518;

#     border-radius: 12px;

#     padding: 12px;

#     border: 1px solid #2a2c33;
# }

# .feed-header {
#     font-size: 12px;

#     color: #888;

#     border-bottom: 1px solid #22242b;

#     padding-bottom: 8px;

#     margin-bottom: 8px;
# }

# .feed-row {
#     display: flex;

#     justify-content: space-between;

#     gap: 10px;

#     font-size: 13px;

#     padding: 6px 0;

#     border-bottom: 1px solid #1a1c22;
# }

# @media (max-width: 768px) {

#     /* Keep the desktop header appearance, but make the wallet row
#        horizontally scrollable on narrow screens instead of stacking. */
#     .header {
#         align-items: center;
#         overflow: hidden;
#         padding: 8px 10px;
#     }

#     .brand {
#         flex: 0 0 auto;
#         white-space: nowrap;
#         font-size: 18px;
#     }

#     .wallet {
#         flex: 1 1 auto;
#         min-width: 0;
#         flex-wrap: nowrap;
#         justify-content: flex-start;
#         overflow-x: auto;
#         overflow-y: hidden;
#         white-space: nowrap;
#         scrollbar-width: none;
#         -webkit-overflow-scrolling: touch;
#         padding-bottom: 2px;
#     }

#     .wallet::-webkit-scrollbar {
#         display: none;
#     }

#     .wallet .player-username,
#     .wallet .balance,
#     .wallet .deposit-btn,
#     .wallet .withdraw-btn,
#     .wallet a {
#         flex: 0 0 auto;
#         white-space: nowrap;
#     }

#     .deposit-btn,
#     .withdraw-btn {
#         padding: 8px 12px;
#         font-size: 12px;
#     }

#     .panels-container {
#         grid-template-columns: 1fr;
#     }

#     .stage {
#         height: 250px;
#     }

#     .multiplier-overlay {
#         font-size: 42px;
#     }

#     .feed-row {
#         font-size: 11px;
#     }
# }

# @media (max-width: 480px) {
#     .header {
#         gap: 8px;
#     }

#     .brand {
#         font-size: 16px;
#     }

#     .wallet {
#         gap: 7px;
#     }

#     .balance {
#         font-size: 14px;
#     }

#     .player-username {
#         font-size: 11px;
#         padding: 5px 8px;
#     }

#     .deposit-btn,
#     .withdraw-btn {
#         padding: 7px 10px;
#         font-size: 11px;
#     }

#     .wallet a {
#         font-size: 11px !important;
#     }
# }


# /* Compact phone header: username and balance stay visible while the
#    hamburger hides/reveals the rest of the top-bar actions. */
# @media (max-width: 600px) {
#     .header { display:flex; flex-wrap:wrap; gap:8px; padding:8px 10px; }
#     .mobile-menu-toggle { display:inline-flex; align-items:center; justify-content:center; order:0; }
#     .brand { display:none; }
#     .wallet { order:1; flex:1 1 auto; display:flex; justify-content:flex-end; gap:7px; overflow:visible; }
#     .wallet .player-username, .wallet .balance { display:inline-flex; flex:0 0 auto; }
#     .wallet .topbar-action { display:none; }
#     .header.menu-open .brand { display:block; order:2; flex:1 0 100%; font-size:15px; }
#     .header.menu-open .wallet { order:3; flex:1 0 100%; justify-content:flex-start; flex-wrap:wrap; }
#     .header.menu-open .wallet .topbar-action { display:inline-flex; }
# }
# </style>

# </head>

# <body>

# <div
#     class="admin-banner"
#     id="adminBanner"
# >
#     ⚡ ADMIN CONTROLS:

#     NEXT ROUND:
#     <span id="next1">-</span>

#     |

#     ROUND AFTER:
#     <span id="next2">-</span>
# </div>


# <div class="header" id="gameHeader">

#     <button type="button" class="mobile-menu-toggle" id="mobileMenuToggle" aria-label="Toggle game menu" aria-expanded="false" onclick="toggleMobileGameMenu()">☰</button>

#     <div class="brand">
#         ✈️ AVIATOR
#     </div>

#     <div class="wallet">

#         <a class="topbar-action" href="/lobby" style="color:#7db6ff;text-decoration:none;font-size:12px">GAMES</a>
#         <a class="topbar-action" href="/signals" style="color:#ffca6b;text-decoration:none;font-size:12px">SIGNALS</a>
#         <span class="player-username" title="Signed-in account">@{{ username }}</span>

#         <span
#             class="balance"
#             id="balanceDisplay"
#         >
#             0.00 KES
#         </span>

#         <button
#             class="deposit-btn topbar-action"
#             onclick="openDepositGateway()"
#         >
#             DEPOSIT
#         </button>

#         <button
#             class="withdraw-btn topbar-action"
#             onclick="triggerWithdrawal()"
#         >
#             WITHDRAW
#         </button>

#         <a
#             class="topbar-action"
#             href="/logout"
#             style="
#                 color:#e53e3e;
#                 text-decoration:none;
#                 font-size:12px;
#             "
#         >
#             Logout
#         </a>

#     </div>

# </div>
# <script>
# function toggleMobileGameMenu(){
#   const header=document.getElementById('gameHeader');
#   const toggle=document.getElementById('mobileMenuToggle');
#   if(!header||!toggle)return;
#   const open=header.classList.toggle('menu-open');
#   toggle.setAttribute('aria-expanded',open?'true':'false');
#   toggle.textContent=open?'×':'☰';
# }
# </script>

# <!-- ========================================================
#      NEXUS DEPOSIT MODAL
#      ======================================================== -->

# <div
#     class="mpesa-modal"
#     id="mpesaModal"
# >

#     <div class="mpesa-card">

#         <h3>
#             Deposit with M-Pesa
#         </h3>

#         <p>
#             Enter your amount and M-Pesa number.
#             Nexus Pay will send an M-Pesa payment
#             prompt to your phone.
#         </p>

#         <label for="mpesaAmount">
#             Amount (KES)
#         </label>

#         <input
#             id="mpesaAmount"
#             type="number"
#             min="200"
#             step="10"
#             value="200"
#             required
#             oninput="validateDepositAmount()"
#         >

#         <div id="mpesaAmountWarning" class="mpesa-amount-warning" role="alert" aria-live="polite">
#             ⚠ Minimum deposit is KES 200. Please enter KES 200 or more.
#         </div>

#         <label for="mpesaPhone">
#             M-Pesa phone number
#         </label>

#         <input
#             id="mpesaPhone"
#             type="tel"
#             placeholder="0712345678"
#         >

#         <div
#             class="mpesa-status"
#             id="mpesaStatus"
#         ></div>

#         <div class="mpesa-actions">

#             <button
#                 class="mpesa-cancel"
#                 onclick="closeMpesaModal()"
#             >
#                 CANCEL
#             </button>

#             <button
#                 class="mpesa-pay"
#                 id="mpesaPayBtn"
#                 onclick="requestNexusDeposit()"
#             >
#                 PAY
#             </button>

#         </div>

#     </div>

# </div>


# <div class="main-layout">

#     <!-- HISTORY -->

#     <div
#         class="history-line"
#         id="historyLine"
#     ></div>


#     <!-- GAME -->

#     <div class="stage">

#         <canvas
#             id="flightCanvas"
#         ></canvas>

#         <div
#             class="multiplier-overlay"
#             id="multiplierDisplay"
#         >
#             1.00x
#         </div>

#     </div>


#     <!-- CONTROLS -->

#     <div class="panels-container">

#         <!-- PANEL 1 -->

#         <div class="bet-box">

#             <div class="toggle-bar">

#                 <div
#                     class="toggle-btn active"
#                     id="tabBet1"
#                     onclick="switchTab(1, 'bet')"
#                 >
#                     Bet
#                 </div>

#                 <div
#                     class="toggle-btn"
#                     id="tabAuto1"
#                     onclick="switchTab(1, 'auto')"
#                 >
#                     Auto
#                 </div>

#             </div>


#             <div
#                 class="auto-options"
#                 id="autoOpt1"
#             >

#                 <label
#                     style="
#                         font-size:11px;
#                         color:#aaa;
#                     "
#                 >
#                     Auto Cashout x
#                 </label>

#                 <input
#                     type="number"
#                     id="autoCashout1"
#                     class="auto-input"
#                     value="2.00"
#                     step="0.1"
#                     min="1.01"
#                 >

#             </div>


#             <div class="controls-flex">

#                 <div class="left-inputs">

#                     <div class="input-stepper">

#                         <button
#                             class="step-btn"
#                             onclick="adjustBet(1, -10)"
#                         >
#                             -
#                         </button>

#                         <input
#                             type="number"
#                             id="amount1"
#                             class="amount-input"
#                             value="20.00"
#                             min="20"
#                             step="5"
#                         >

#                         <button
#                             class="step-btn"
#                             onclick="adjustBet(1, 10)"
#                         >
#                             +
#                         </button>

#                     </div>


#                     <div class="quick-bets">

#                         <div
#                             class="q-btn"
#                             onclick="setBet(1, 100)"
#                         >
#                             100
#                         </div>

#                         <div
#                             class="q-btn"
#                             onclick="setBet(1, 200)"
#                         >
#                             200
#                         </div>

#                         <div
#                             class="q-btn"
#                             onclick="setBet(1, 500)"
#                         >
#                             500
#                         </div>

#                         <div
#                             class="q-btn"
#                             onclick="setBet(1, 10000)"
#                         >
#                             10,000
#                         </div>

#                     </div>

#                 </div>


#                 <button
#                     class="action-btn btn-green"
#                     id="btn1"
#                     onclick="handleAction(1)"
#                 >

#                     <span
#                         class="btn-title"
#                         id="btn1Title"
#                     >
#                         Bet
#                     </span>

#                     <span
#                         class="btn-sub"
#                         id="btn1Sub"
#                     >
#                         20.00 KES
#                     </span>

#                 </button>

#             </div>

#         </div>


#         <!-- PANEL 2 -->

#         <div class="bet-box">

#             <div class="toggle-bar">

#                 <div
#                     class="toggle-btn active"
#                     id="tabBet2"
#                     onclick="switchTab(2, 'bet')"
#                 >
#                     Bet
#                 </div>

#                 <div
#                     class="toggle-btn"
#                     id="tabAuto2"
#                     onclick="switchTab(2, 'auto')"
#                 >
#                     Auto
#                 </div>

#             </div>


#             <div
#                 class="auto-options"
#                 id="autoOpt2"
#             >

#                 <label
#                     style="
#                         font-size:11px;
#                         color:#aaa;
#                     "
#                 >
#                     Auto Cashout x
#                 </label>

#                 <input
#                     type="number"
#                     id="autoCashout2"
#                     class="auto-input"
#                     value="2.00"
#                     step="0.1"
#                     min="1.01"
#                 >

#             </div>


#             <div class="controls-flex">

#                 <div class="left-inputs">

#                     <div class="input-stepper">

#                         <button
#                             class="step-btn"
#                             onclick="adjustBet(2, -10)"
#                         >
#                             -
#                         </button>

#                         <input
#                             type="number"
#                             id="amount2"
#                             class="amount-input"
#                             value="20.00"
#                             min="20"
#                             step="5"
#                         >

#                         <button
#                             class="step-btn"
#                             onclick="adjustBet(2, 10)"
#                         >
#                             +
#                         </button>

#                     </div>


#                     <div class="quick-bets">

#                         <div
#                             class="q-btn"
#                             onclick="setBet(2, 100)"
#                         >
#                             100
#                         </div>

#                         <div
#                             class="q-btn"
#                             onclick="setBet(2, 200)"
#                         >
#                             200
#                         </div>

#                         <div
#                             class="q-btn"
#                             onclick="setBet(2, 500)"
#                         >
#                             500
#                         </div>

#                         <div
#                             class="q-btn"
#                             onclick="setBet(2, 10000)"
#                         >
#                             10,000
#                         </div>

#                     </div>

#                 </div>


#                 <button
#                     class="action-btn btn-green"
#                     id="btn2"
#                     onclick="handleAction(2)"
#                 >

#                     <span
#                         class="btn-title"
#                         id="btn2Title"
#                     >
#                         Bet
#                     </span>

#                     <span
#                         class="btn-sub"
#                         id="btn2Sub"
#                     >
#                         20.00 KES
#                     </span>

#                 </button>

#             </div>

#         </div>

#     </div>


#     <!-- FEED -->

#     <div class="feed-section">

#         <div class="feed-header">

#             ALL BETS
#             (<span id="totalBetsCount">0</span>)

#         </div>

#         <div id="liveBetsList"></div>

#     </div>

# </div>


# <script>

# let currentStatus = "BETTING";

# let currentMult = 1.00;

# let userBets = {};

# let currentRoundId = null;

# let lastAutoPlacedRound = {
#     1: null,
#     2: null
# };

# let autoBetEnabled = {
#     1: false,
#     2: false
# };

# let activeTab = {
#     1: "bet",
#     2: "bet"
# };


# /* ==========================================================
#    CANVAS
#    ========================================================== */

# const canvas = document.getElementById(
#     "flightCanvas"
# );

# const ctx = canvas.getContext(
#     "2d"
# );


# function resizeCanvas() {

#     canvas.width =
#         canvas.parentElement.clientWidth;

#     canvas.height =
#         canvas.parentElement.clientHeight;
# }


# window.addEventListener(
#     "resize",
#     resizeCanvas
# );

# resizeCanvas();


# function drawScene() {

#     ctx.clearRect(
#         0,
#         0,
#         canvas.width,
#         canvas.height
#     );


#     /* Grid */

#     ctx.strokeStyle =
#         "rgba(255,255,255,0.03)";

#     ctx.lineWidth = 1;


#     for (
#         let x = 0;
#         x < canvas.width;
#         x += 40
#     ) {

#         ctx.beginPath();

#         ctx.moveTo(x, 0);

#         ctx.lineTo(
#             x,
#             canvas.height
#         );

#         ctx.stroke();
#     }


#     for (
#         let y = 0;
#         y < canvas.height;
#         y += 40
#     ) {

#         ctx.beginPath();

#         ctx.moveTo(0, y);

#         ctx.lineTo(
#             canvas.width,
#             y
#         );

#         ctx.stroke();
#     }


#     if (
#         currentStatus === "RUNNING"
#         ||
#         currentStatus === "CRASHED"
#     ) {

#         // Logarithmic progress keeps the plane moving across the canvas
#         // during long rounds instead of freezing visually at 6x.
#         const progress =
#             Math.max(0, Math.min(
#                 Math.log(Math.max(currentMult, 1)) / Math.log(150),
#                 1.0
#             ));


#         const startX = 0;

#         const startY =
#             canvas.height;


#         const endX =
#             canvas.width
#             * 0.75
#             * Math.min(
#                 progress + 0.1,
#                 1.0
#             );


#         const endY =
#             canvas.height
#             -
#             (
#                 canvas.height
#                 * 0.65
#                 * Math.min(
#                     progress + 0.1,
#                     1.0
#                 )
#             );


#         /* Area */

#         ctx.beginPath();

#         ctx.moveTo(
#             startX,
#             startY
#         );

#         ctx.quadraticCurveTo(
#             endX * 0.5,
#             canvas.height,
#             endX,
#             endY
#         );

#         ctx.lineTo(
#             endX,
#             canvas.height
#         );

#         ctx.closePath();


#         const grad =
#             ctx.createLinearGradient(
#                 0,
#                 0,
#                 0,
#                 canvas.height
#             );

#         grad.addColorStop(
#             0,
#             "rgba(229,62,62,0.5)"
#         );

#         grad.addColorStop(
#             1,
#             "rgba(229,62,62,0)"
#         );

#         ctx.fillStyle = grad;

#         ctx.fill();


#         /* Line */

#         ctx.beginPath();

#         ctx.moveTo(
#             startX,
#             startY
#         );

#         ctx.quadraticCurveTo(
#             endX * 0.5,
#             canvas.height,
#             endX,
#             endY
#         );

#         ctx.strokeStyle =
#             "#e53e3e";

#         ctx.lineWidth = 4;

#         ctx.stroke();


#         /* Aircraft point */

#         if (
#             currentStatus === "RUNNING"
#         ) {

#             ctx.save();

#             ctx.translate(
#                 endX,
#                 endY
#             );

#             ctx.fillStyle =
#                 "#e53e3e";

#             ctx.beginPath();

#             ctx.arc(
#                 0,
#                 0,
#                 8,
#                 0,
#                 Math.PI * 2
#             );

#             ctx.fill();

#             ctx.restore();
#         }
#     }


#     requestAnimationFrame(
#         drawScene
#     );
# }


# requestAnimationFrame(
#     drawScene
# );


# /* ==========================================================
#    TABS
#    ========================================================== */

# function switchTab(
#     num,
#     tab
# ) {

#     activeTab[num] = tab;


#     document.getElementById(
#         "tabBet" + num
#     ).className =
#         "toggle-btn"
#         +
#         (
#             tab === "bet"
#                 ? " active"
#                 : ""
#         );


#     document.getElementById(
#         "tabAuto" + num
#     ).className =
#         "toggle-btn"
#         +
#         (
#             tab === "auto"
#                 ? " active"
#                 : ""
#         );


#     const autoOpt =
#         document.getElementById(
#             "autoOpt" + num
#         );


#     if (tab === "auto") {
#         autoOpt.classList.add(
#             "show"
#         );
#     } else {
#         autoOpt.classList.remove(
#             "show"
#         );
#     }


#     updateButtonUI(num);
# }


# /* ==========================================================
#    STATE
#    ========================================================== */

# async function syncState() {

#     try {

#         const res =
#             await fetch(
#                 "/api/state",
#                 {
#                     cache: "no-store"
#                 }
#             );


#         if (!res.ok) {
#             return;
#         }


#         const data =
#             await res.json();


#         document.getElementById(
#             "balanceDisplay"
#         ).innerText =
#             Number(data.balance)
#                 .toFixed(2)
#             + " KES";

#         currentStatus =
#             data.status;


#         currentMult =
#             Number(data.multiplier);


#         userBets =
#             data.bets || {};


#         currentRoundId =
#             data.round_id;


#         /* Admin telemetry */

#         if (data.is_admin) {

#             document.getElementById(
#                 "adminBanner"
#             ).style.display =
#                 "block";


#             document.getElementById(
#                 "next1"
#             ).innerText =
#                 data.next_crash_point_1
#                     ? Number(
#                         data.next_crash_point_1
#                     ).toFixed(2) + "x"
#                     : "-";


#             document.getElementById(
#                 "next2"
#             ).innerText =
#                 data.next_crash_point_2
#                     ? Number(
#                         data.next_crash_point_2
#                     ).toFixed(2) + "x"
#                     : "-";

#         } else {

#             document.getElementById(
#                 "adminBanner"
#             ).style.display =
#                 "none";
#         }


#         /* Multiplier */

#         const multDisplay =
#             document.getElementById(
#                 "multiplierDisplay"
#             );


#         if (
#             data.status === "BETTING"
#         ) {

#             multDisplay.className =
#                 "multiplier-overlay";

#             multDisplay.innerText =
#                 "WAITING FOR NEXT ROUND";


#             checkAndRunAutoBet(1);

#             checkAndRunAutoBet(2);

#         }

#         else if (
#             data.status === "RUNNING"
#         ) {

#             multDisplay.className =
#                 "multiplier-overlay";

#             multDisplay.innerText =
#                 Number(
#                     data.multiplier
#                 ).toFixed(2)
#                 + "x";

#         }

#         else if (
#             data.status === "CRASHED"
#         ) {

#             multDisplay.className =
#                 "multiplier-overlay crashed-text";

#             multDisplay.innerText =
#                 "FLEW AWAY!\n"
#                 +
#                 (
#                     data.crash_point
#                         ? Number(
#                             data.crash_point
#                         ).toFixed(2)
#                         : Number(
#                             data.multiplier
#                         ).toFixed(2)
#                 )
#                 +
#                 "x";
#         }


#         /* History */

#         const histLine =
#             document.getElementById(
#                 "historyLine"
#             );


#         histLine.innerHTML =
#             (data.history || [])
#                 .map(
#                     function(val) {

#                         let cls =
#                             "hist-blue";

#                         if (
#                             val >= 10
#                         ) {

#                             cls =
#                                 "hist-pink";

#                         } else if (
#                             val >= 2
#                         ) {

#                             cls =
#                                 "hist-purple";
#                         }


#                         return `
#                             <div
#                                 class="hist-item ${cls}"
#                             >
#                                 ${Number(val).toFixed(2)}x
#                             </div>
#                         `;
#                     }
#                 )
#                 .join("");


#         updateButtonUI(1);

#         updateButtonUI(2);


#         /* Feed */

#         const feedData =
#             data.live_feed || [];


#         document.getElementById(
#             "totalBetsCount"
#         ).innerText =
#             feedData.length;


#         const feed =
#             document.getElementById(
#                 "liveBetsList"
#             );


#         feed.innerHTML =
#             feedData
#                 .map(
#                     function(b) {

#                         let statusText =
#                             `
#                             <span
#                                 style="color:#888;"
#                             >
#                                 IN PLAY
#                             </span>
#                             `;


#                         if (
#                             b.status === "WON"
#                         ) {

#                             const cashout =
#                                 Number(
#                                     b.cashout_multiplier
#                                     || 0
#                                 ).toFixed(2);


#                             const winnings =
#                                 Number(
#                                     b.winnings
#                                     || 0
#                                 ).toFixed(2);


#                             statusText =
#                                 `
#                                 <span
#                                     style="
#                                         color:#28a745;
#                                         font-weight:bold;
#                                     "
#                                 >
#                                     ${cashout}x
#                                     (+${winnings})
#                                 </span>
#                                 `;

#                         }

#                         else if (
#                             b.status === "LOST"
#                         ) {

#                             statusText =
#                                 `
#                                 <span
#                                     style="
#                                         color:#e53e3e;
#                                     "
#                                 >
#                                     CRASHED
#                                 </span>
#                                 `;
#                         }


#                         return `
#                             <div class="feed-row">

#                                 <div>
#                                     <b>
#                                         ${escapeHtml(
#                                             b.username
#                                         )}
#                                     </b>
#                                 </div>

#                                 <div>
#                                     ${Number(
#                                         b.amount
#                                     ).toFixed(2)}
#                                     KES
#                                 </div>

#                                 <div>
#                                     ${statusText}
#                                 </div>

#                             </div>
#                         `;
#                     }
#                 )
#                 .join("");


#     } catch (error) {

#         console.error(
#             "State sync error:",
#             error
#         );
#     }
# }


# /* ==========================================================
#    ESCAPE HTML
#    ========================================================== */

# function escapeHtml(value) {

#     const div =
#         document.createElement(
#             "div"
#         );

#     div.textContent =
#         String(value ?? "");

#     return div.innerHTML;
# }


# /* ==========================================================
#    AUTO BET
#    ========================================================== */

# async function checkAndRunAutoBet(
#     num
# ) {

#     if (
#         !autoBetEnabled[num]
#         ||
#         currentStatus !== "BETTING"
#     ) {
#         return;
#     }


#     if (
#         lastAutoPlacedRound[num]
#         === currentRoundId
#     ) {
#         return;
#     }


#     const bet =
#         userBets[num];


#     if (
#         bet
#         &&
#         bet.status === "ACTIVE"
#     ) {

#         lastAutoPlacedRound[num] =
#             currentRoundId;

#         return;
#     }


#     const amount =
#         document.getElementById(
#             "amount" + num
#         ).value;


#     const autoCash =
#         document.getElementById(
#             "autoCashout" + num
#         ).value;


#     try {

#         const res =
#             await fetch(
#                 "/api/bet",
#                 {
#                     method: "POST",

#                     headers: {
#                         "Content-Type":
#                             "application/json"
#                     },

#                     body: JSON.stringify({
#                         bet_number: num,
#                         amount: amount,
#                         auto_cashout:
#                             autoCash
#                     })
#                 }
#             );


#         const data =
#             await res.json();


#         if (data.success) {

#             lastAutoPlacedRound[num] =
#                 currentRoundId;

#         }

#     } catch (error) {

#         console.error(
#             "Auto bet error:",
#             error
#         );
#     }
# }


# /* ==========================================================
#    BUTTON UI
#    ========================================================== */

# function updateButtonUI(
#     num
# ) {

#     const btn =
#         document.getElementById(
#             "btn" + num
#         );


#     const title =
#         document.getElementById(
#             "btn" + num + "Title"
#         );


#     const sub =
#         document.getElementById(
#             "btn" + num + "Sub"
#         );


#     const inputVal =
#         parseFloat(
#             document.getElementById(
#                 "amount" + num
#             ).value
#         )
#         || 20;


#     const bet =
#         userBets[num];


#     if (
#         currentStatus === "RUNNING"
#     ) {

#         if (
#             bet
#             &&
#             bet.status === "ACTIVE"
#         ) {

#             const currentPayout =
#                 (
#                     Number(bet.amount)
#                     * currentMult
#                 ).toFixed(2);


#             btn.className =
#                 "action-btn btn-orange";


#             title.innerText =
#                 "CASH OUT";


#             sub.innerText =
#                 currentPayout
#                 + " KES";


#             btn.disabled = false;

#         } else {

#             btn.className =
#                 "action-btn btn-disabled";

#             title.innerText =
#                 "Bet";

#             sub.innerText =
#                 inputVal.toFixed(2)
#                 + " KES";

#             btn.disabled = true;
#         }

#     }

#     else if (
#         currentStatus === "BETTING"
#     ) {

#         if (
#             activeTab[num] === "auto"
#         ) {

#             if (
#                 autoBetEnabled[num]
#             ) {

#                 btn.className =
#                     "action-btn btn-blue";

#                 title.innerText =
#                     "AUTO ACTIVE";

#                 sub.innerText =
#                     "CANCEL";

#                 btn.disabled = false;

#             } else {

#                 btn.className =
#                     "action-btn btn-green";

#                 title.innerText =
#                     "AUTO BET";

#                 sub.innerText =
#                     inputVal.toFixed(2)
#                     + " KES";

#                 btn.disabled = false;
#             }

#         } else {

#             if (
#                 bet
#                 &&
#                 bet.status === "ACTIVE"
#             ) {

#                 btn.className =
#                     "action-btn btn-disabled";

#                 title.innerText =
#                     "WAITING";

#                 sub.innerText =
#                     "BET PLACED";

#                 btn.disabled = true;

#             } else {

#                 btn.className =
#                     "action-btn btn-green";

#                 title.innerText =
#                     "Bet";

#                 sub.innerText =
#                     inputVal.toFixed(2)
#                     + " KES";

#                 btn.disabled = false;
#             }
#         }

#     }

#     else {

#         btn.className =
#             "action-btn btn-disabled";

#         btn.disabled = true;
#     }
# }


# /* ==========================================================
#    AMOUNT CONTROLS
#    ========================================================== */

# function adjustBet(
#     num,
#     delta
# ) {

#     const input =
#         document.getElementById(
#             "amount" + num
#         );


#     let val =
#         (
#             parseFloat(
#                 input.value
#             )
#             || 0
#         )
#         + delta;


#     if (val < 20) {
#         val = 20;
#     }


#     input.value =
#         val.toFixed(2);


#     updateButtonUI(num);
# }


# function setBet(
#     num,
#     val
# ) {

#     document.getElementById(
#         "amount" + num
#     ).value =
#         Number(val).toFixed(2);


#     updateButtonUI(num);
# }


# /* ==========================================================
#    BET / CASHOUT ACTION
#    ========================================================== */

# async function handleAction(
#     num
# ) {

#     const bet =
#         userBets[num];


#     if (
#         currentStatus === "RUNNING"
#         &&
#         bet
#         &&
#         bet.status === "ACTIVE"
#     ) {

#         try {

#             const res =
#                 await fetch(
#                     "/api/cashout",
#                     {
#                         method: "POST",

#                         headers: {
#                             "Content-Type":
#                                 "application/json"
#                         },

#                         body: JSON.stringify({
#                             bet_number: num
#                         })
#                     }
#                 );


#             const data =
#                 await res.json();


#             if (!data.success) {
#                 alert(
#                     data.message
#                 );
#             }

#         } catch (error) {

#             alert(
#                 "Cashout request failed."
#             );
#         }

#     }

#     else if (
#         currentStatus === "BETTING"
#     ) {

#         if (
#             activeTab[num] === "auto"
#         ) {

#             autoBetEnabled[num] =
#                 !autoBetEnabled[num];


#             if (
#                 autoBetEnabled[num]
#             ) {

#                 await checkAndRunAutoBet(
#                     num
#                 );
#             }

#         } else {

#             const amount =
#                 document.getElementById(
#                     "amount" + num
#                 ).value;


#             try {

#                 const res =
#                     await fetch(
#                         "/api/bet",
#                         {
#                             method: "POST",

#                             headers: {
#                                 "Content-Type":
#                                     "application/json"
#                             },

#                             body:
#                                 JSON.stringify({
#                                     bet_number:
#                                         num,

#                                     amount:
#                                         amount
#                                 })
#                         }
#                     );


#                 const data =
#                     await res.json();


#                 if (!data.success) {

#                     alert(
#                         data.message
#                     );
#                 }

#             } catch (error) {

#                 alert(
#                     "Bet request failed."
#                 );
#             }
#         }
#     }


#     await syncState();
# }


# /* ==========================================================
#    NEXUS DEPOSIT
#    ========================================================== */

# function openDepositGateway() {

#     const modal =
#         document.getElementById(
#             "mpesaModal"
#         );


#     const status =
#         document.getElementById(
#             "mpesaStatus"
#         );


#     const phoneInput =
#         document.getElementById(
#             "mpesaPhone"
#         );


#     modal.style.display =
#         "flex";


#     status.textContent = "";


#     /*
#      * We deliberately do not expose the user's phone
#      * from the server into the HTML.
#      *
#      * They can enter the number here.
#      */

#     phoneInput.focus();
# }


# function closeMpesaModal() {

#     document.getElementById(
#         "mpesaModal"
#     ).style.display =
#         "none";
# }


# function validateDepositAmount() {
#     const amountInput = document.getElementById("mpesaAmount");
#     const warning = document.getElementById("mpesaAmountWarning");
#     const payButton = document.getElementById("mpesaPayBtn");
#     const rawValue = amountInput.value.trim();
#     const amount = Number(rawValue);
#     const isBelowMinimum = rawValue !== "" && (!Number.isFinite(amount) || amount < 200);

#     warning.classList.toggle("visible", isBelowMinimum);
#     amountInput.setCustomValidity(
#         isBelowMinimum ? "Minimum deposit is KES 200." : ""
#     );

#     if (payButton) {
#         payButton.disabled = isBelowMinimum;
#         payButton.style.opacity = isBelowMinimum ? "0.6" : "1";
#         payButton.style.cursor = isBelowMinimum ? "not-allowed" : "pointer";
#     }

#     return !isBelowMinimum;
# }


# async function requestNexusDeposit() {

#     if (!validateDepositAmount()) {
#         return;
#     }

#     const amount =
#         parseFloat(
#             document.getElementById(
#                 "mpesaAmount"
#             ).value
#         );


#     const phone =
#         document.getElementById(
#             "mpesaPhone"
#         ).value.trim();


#     const status =
#         document.getElementById(
#             "mpesaStatus"
#         );


#     const btn =
#         document.getElementById(
#             "mpesaPayBtn"
#         );


#     if (!Number.isFinite(amount)) {
#         status.textContent = "Enter a valid deposit amount.";
#         alert("Minimum deposit is KES 5.");
#         return;
#     }

#     if (amount < 200) {
#         status.textContent = "Minimum deposit is KES 200. Please enter KES 200 or more.";
#         alert("Deposit not allowed: the minimum deposit is KES 200.");
#         return;
#     }


#     if (
#         !Number.isInteger(amount)
#     ) {

#         status.textContent =
#             "Enter a whole KES amount.";

#         return;
#     }


#     if (!phone) {

#         status.textContent =
#             "Enter your M-Pesa phone number.";

#         return;
#     }


#     btn.disabled = true;


#     status.textContent =
#         "Sending M-Pesa prompt...";


#     try {

#         const res =
#             await fetch(
#                 "/api/nexus/stkpush",
#                 {
#                     method: "POST",

#                     headers: {
#                         "Content-Type":
#                             "application/json"
#                     },

#                     body: JSON.stringify({
#                         amount: amount,
#                         phone: phone
#                     })
#                 }
#             );


#         const data =
#             await res.json();


#         if (!data.success) {

#             status.textContent =
#                 data.message
#                 ||
#                 "Unable to start payment.";

#             btn.disabled = false;

#             return;
#         }


#         status.textContent =
#             "M-Pesa prompt sent. "
#             +
#             "Enter your PIN on your phone. "
#             +
#             "Your balance will update only "
#             +
#             "after the payment is confirmed.";


#         /* Wait for the signed Nexus Pay webhook to update the local
#          * transaction. The polling endpoint only reads local verified status;
#          * it never credits a wallet based on browser-submitted data. */

#         setTimeout(
#             function() {
#                 pollNexusStatus(
#                     data.reference
#                 );
#             },
#             3000
#         );


#     } catch (error) {

#         console.error(
#             "Nexus payment error:",
#             error
#         );


#         status.textContent =
#             "Payment request failed. "
#             +
#             "Please try again.";

#     } finally {

#         btn.disabled = false;
#     }
# }


# /* ==========================================================
#    NEXUS STATUS
#    ========================================================== */

# async function pollNexusStatus(
#     reference
# ) {

#     for (
#         let i = 0;
#         i < 100;
#         i++
#     ) {

#         await new Promise(
#             function(resolve) {
#                 setTimeout(
#                     resolve,
#                     3000
#                 );
#             }
#         );


#         try {

#             const res =
#                 await fetch(
#                     "/api/nexus/status/"
#                     +
#                     encodeURIComponent(
#                         reference
#                     )
#                 );


#             const data =
#                 await res.json();


#             if (!data.success) {
#                 return;
#             }


#             if (
#                 data.status === "SUCCESS"
#             ) {

#                 document.getElementById(
#                     "mpesaStatus"
#                 ).textContent =
#                     "Deposit confirmed. KES "
#                     +
#                     Number(
#                         data.amount
#                     ).toFixed(2)
#                     +
#                     " has been added.";


#                 await syncState();


#                 setTimeout(
#                     closeMpesaModal,
#                     1800
#                 );

#                 return;
#             }


#             if (
#                 data.status === "FAILED"
#             ) {

#                 document.getElementById(
#                     "mpesaStatus"
#                 ).textContent =
#                     data.message
#                     ||
#                     "M-Pesa payment was not completed.";

#                 return;
#             }

#         } catch (error) {

#             console.error(
#                 "Nexus status error:",
#                 error
#             );

#             return;
#         }
#     }


#     document.getElementById(
#         "mpesaStatus"
#     ).textContent =
#         "Payment is pending verification. Once Nexus Pay verifies it, it will appear as pending until an administrator approves it. It cannot be used for betting before approval.";
# }


# /* ==========================================================
#    WITHDRAWAL
#    ========================================================== */

# async function triggerWithdrawal() {

#     const currentText =
#         document.getElementById("balanceDisplay").textContent || "";

#     const val = prompt(
#         "Enter amount to withdraw (KES). Minimum: 1000 KES.\nAvailable: " + currentText
#     );

#     if (val === null) {
#         return;
#     }

#     const amount = parseFloat(String(val).replace(/,/g, "").trim());

#     if (!Number.isFinite(amount) || amount <= 0) {
#         alert("Enter a valid withdrawal amount.");
#         return;
#     }

#     if (amount < 1) {
#         alert("Minimum withdrawal is KES 200. Please enter KES 200 or more.");
#         return;
#     }

#     if (!Number.isInteger(amount)) {
#         alert("Withdrawal amount must be a whole KES amount.");
#         return;
#     }

#     const phoneInput = prompt(
#         "M-Pesa number (Cancel = use your registered number):"
#     );

#     const phone = phoneInput === null ? "" : phoneInput.trim();

#     try {
#         const res = await fetch("/api/withdraw", {
#             method: "POST",
#             headers: { "Content-Type": "application/json" },
#             body: JSON.stringify({
#                 amount: amount,
#                 phone_number: phone.trim()
#             })
#         });

#         let data;
#         try {
#             data = await res.json();
#         } catch (e) {
#             data = {
#                 success: false,
#                 error: "Invalid server response."
#             };
#         }

#         const message = data.message || data.error ||
#             (data.success ? "Withdrawal submitted." : "Withdrawal failed.");

#         alert(message);
#         await syncState();

#     } catch (error) {
#         console.error("Withdrawal error:", error);
#         alert("Withdrawal request failed. Please try again.");
#     }
# }


# /* ==========================================================
#    START
#    ========================================================== */

# setInterval(
#     syncState,
#     200
# );

# syncState();

# </script>

# </body>

# </html>
# """


# # ============================================================
# # STARTUP
# # ============================================================

# def print_configuration_status():
#     print("\n=== Aviator configuration ===")
#     print("Database:", DB_NAME)
#     print("Nexus base URL:", NEXUS_PAY_BASE_URL)
#     print("Nexus API key configured:", bool(NEXUS_PAY_API_KEY))
#     print("Nexus public key configured:", bool(NEXUS_PAY_PUBLIC_KEY))
#     print("Nexus secret key configured:", bool(NEXUS_PAY_SECRET_KEY))
#     print("Nexus timeout:", NEXUS_PAY_TIMEOUT)
#     print("Nexus webhook path:", NEXUS_WEBHOOK_PATH)
#     print("Nexus webhook URL:", NEXUS_WEBHOOK_URL or "Set NEXUS_WEBHOOK_URL in .env")
#     print("Webhook signing secret configured:", bool(NEXUS_WEBHOOK_SECRET))
#     print("================================\n")


# def start_application():

#     # Database must exist before the game thread starts.
#     init_db()

#     # Create the first game round.
#     initialize_game()

#     # Start game engine once.
#     thread = threading.Thread(
#         target=game_loop,
#         daemon=True,
#         name="game-engine"
#     )

#     thread.start()


# # ============================================================
# # RUN
# # ============================================================
# init_db()
# print_configuration_status()

# if __name__ == "__main__":

#     start_application()

#     app.run(
#         host="0.0.0.0",
#         port=int(
#             os.environ.get(
#                 "PORT",
#                 "5000"
#             )
#         ),
#         debug=(
#             os.environ.get(
#                 "FLASK_DEBUG",
#                 "0"
#             ) == "1"
#         ),
#         use_reloader=False
#     )




import os
import time
import random
import math
import sqlite3
import hashlib
import hmac
import json
import secrets
import threading
import re
from datetime import timedelta
from datetime import datetime

import requests
from dotenv import load_dotenv

from werkzeug.security import generate_password_hash, check_password_hash

from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    render_template_string,
)

# ============================================================
# CONFIGURATION
# ============================================================

# Load .env from the same directory as this app.py.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

# Database: use an absolute path when DB_NAME is relative so the app
# always opens the same database regardless of the working directory.
_db_name = os.getenv("DB_NAME", "aviator_live.db").strip()
DB_NAME = (
    _db_name
    if os.path.isabs(_db_name)
    else os.path.join(BASE_DIR, _db_name)
)

BETTING_WINDOW = 7.0
MIN_WITHDRAWAL = 1000.0
MAX_WITHDRAWAL = 250000.0
CRASH_DISPLAY_TIME = 2.5
STARTING_BALANCE = 0.0

# ============================================================
# NEXUS PAY CONFIGURATION
# ============================================================

# Keep all Nexus credentials in .env. Never hard-code them in app.py.
NEXUS_PAY_PUBLIC_KEY = os.getenv("NEXUS_PAY_PUBLIC_KEY", "").strip()
NEXUS_PAY_SECRET_KEY = os.getenv("NEXUS_PAY_SECRET_KEY", "").strip()
NEXUS_PAY_API_KEY = os.getenv("NEXUS_PAY_API_KEY", "").strip()

NEXUS_PAY_BASE_URL = os.getenv(
    "NEXUS_PAY_BASE_URL",
    "https://makamescopay.com"
).strip().rstrip("/")

try:
    NEXUS_PAY_TIMEOUT = int(
        os.getenv("NEXUS_PAY_TIMEOUT", "30")
    )
except (TypeError, ValueError):
    NEXUS_PAY_TIMEOUT = 30

if NEXUS_PAY_TIMEOUT < 5:
    NEXUS_PAY_TIMEOUT = 5

# # Optional callback secret. Leave blank until Nexus provides a webhook
# # signing/verification secret and its exact callback specification.
# NEXUS_CALLBACK_SECRET = os.getenv("NEXUS_CALLBACK_SECRET", "").strip()
# NEXUS_WEBHOOK_SECRET = os.getenv("NEXUS_WEBHOOK_SECRET", "").strip()
# NEXUS_WEBHOOK_PATH = os.getenv("NEXUS_WEBHOOK_PATH", "/api/nexus/webhook").strip() or "/api/nexus/webhook"
# NEXUS_WEBHOOK_URL = os.getenv("NEXUS_WEBHOOK_URL", "").strip()

# Africa's Talking SMS OTP configuration. Obtain these from the AT dashboard.
AT_USERNAME = os.getenv("AT_USERNAME", "").strip()
AT_API_KEY = os.getenv("AT_API_KEY", "").strip()
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "").strip()
OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "5"))
NEXUS_CALLBACK_SECRET = os.getenv("NEXUS_CALLBACK_SECRET", "").strip()
NEXUS_WEBHOOK_SECRET = os.getenv("NEXUS_WEBHOOK_SECRET", "").strip()
NEXUS_WEBHOOK_PATH = os.getenv(
    "NEXUS_WEBHOOK_PATH",
    "/api/nexus/webhook"
).strip() or "/api/nexus/webhook"

NEXUS_WEBHOOK_URL = os.getenv("NEXUS_WEBHOOK_URL", "").strip()

# Africa's Talking SMS OTP configuration. Obtain these from the AT dashboard.
AT_USERNAME = os.getenv("AT_USERNAME", "").strip()
AT_API_KEY = os.getenv("AT_API_KEY", "").strip()
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "").strip()
OTP_TTL_MINUTES = int(os.getenv("OTP_TTL_MINUTES", "5"))
# # ============================================================


app = Flask(__name__)

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "").strip()

# Dedicated administrator credentials are configured in .env.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

if not FLASK_SECRET_KEY:
    # Development fallback only. Production should always provide
    # FLASK_SECRET_KEY in .env or the process environment.
    FLASK_SECRET_KEY = secrets.token_hex(32)
    print("WARNING: FLASK_SECRET_KEY is not configured; using a temporary development key.")

app.secret_key = FLASK_SECRET_KEY

# Persistent browser session: sleeping the computer or closing the browser
# will not immediately discard the login. SQLite remains the source of truth
# for balances, bets, rounds, deposits and withdrawals.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "0").strip() == "1"
)

GAME_LOCK = threading.RLock()

# ============================================================
# DATABASE
# ============================================================

def get_db():
    # Create the configured database directory when deploying to a fresh folder.
    os.makedirs(os.path.dirname(DB_NAME) or ".", exist_ok=True)
    conn = sqlite3.connect(
        DB_NAME,
        timeout=10,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    """Use Werkzeug's salted PBKDF2 password hash for new/updated passwords."""
    return generate_password_hash(password, method="pbkdf2:sha256:600000")


def verify_password(password, hashed):
    """Verify modern hashes and transparently support legacy SHA-256 rows."""
    if not hashed:
        return False
    if re.fullmatch(r"[0-9a-fA-F]{64}", str(hashed)):
        return secrets.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), str(hashed))
    try:
        return check_password_hash(hashed, password)
    except (ValueError, TypeError):
        return False


def init_db():
    conn = get_db()

    try:
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone_number TEXT UNIQUE NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                role TEXT NOT NULL DEFAULT 'USER',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crash_point REAL NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                round_id INTEGER NOT NULL,
                bet_number INTEGER NOT NULL,
                amount REAL NOT NULL,
                auto_cashout REAL,
                cashout_multiplier REAL,
                winnings REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,

                UNIQUE(username, round_id, bet_number)
            )
        """)

        # Nexus Pay deposits.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nexus_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL,
                phone_number TEXT NOT NULL,

                amount REAL NOT NULL,

                reference TEXT UNIQUE NOT NULL,

                provider_transaction_id TEXT,

                status TEXT NOT NULL DEFAULT 'PENDING',

                provider_message TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                credited_at TEXT
            )
        """)

        # Withdrawal records.
        #
        # The current version records withdrawals instead of pretending
        # that money has actually been sent. A real Nexus B2C/disbursement
        # implementation should be connected here using the provider's
        # documented B2C endpoint.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL,
                phone_number TEXT NOT NULL,

                amount REAL NOT NULL,

                status TEXT NOT NULL DEFAULT 'PENDING',

                provider_transaction_id TEXT,
                provider_message TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                completed_at TEXT
            )
        """)

        # Migrate older databases used before Nexus webhook support.
        # SQLite ignores this only when the column already exists.
        withdrawal_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(withdrawals)").fetchall()
        }

        if "reference" not in withdrawal_columns:
            conn.execute("ALTER TABLE withdrawals ADD COLUMN reference TEXT")

        if "provider_transaction_id" not in withdrawal_columns:
            conn.execute("ALTER TABLE withdrawals ADD COLUMN provider_transaction_id TEXT")

        if "provider_message" not in withdrawal_columns:
            conn.execute("ALTER TABLE withdrawals ADD COLUMN provider_message TEXT")


        # Additive migrations: preserve existing users, rounds, bets, transactions and withdrawals.
        user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "last_seen_at" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_seen_at TEXT")
        if "is_active" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

        conn.execute("""CREATE TABLE IF NOT EXISTS password_reset_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            used_at TEXT,
            created_at TEXT NOT NULL,
            request_ip TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT NOT NULL,
            action TEXT NOT NULL,
            target_username TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL
        )""")

        # Add explicit approval metadata to existing Nexus deposit rows.
        tx_columns = {row["name"] for row in conn.execute("PRAGMA table_info(nexus_transactions)").fetchall()}
        if "approved_by" not in tx_columns:
            conn.execute("ALTER TABLE nexus_transactions ADD COLUMN approved_by TEXT")
        if "approved_at" not in tx_columns:
            conn.execute("ALTER TABLE nexus_transactions ADD COLUMN approved_at TEXT")
        if "verified_at" not in tx_columns:
            conn.execute("ALTER TABLE nexus_transactions ADD COLUMN verified_at TEXT")

        # Paid Aviator signal subscriptions and admin-published signal feed.
        # These are additive tables; existing player/game/payment records are untouched.
        conn.execute("""CREATE TABLE IF NOT EXISTS signal_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            plan_minutes INTEGER NOT NULL CHECK(plan_minutes IN (5,10)),
            amount REAL NOT NULL,
            reference TEXT UNIQUE NOT NULL,
            provider_transaction_id TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            provider_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            paid_at TEXT,
            expires_at TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS aviator_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT NOT NULL,
            round_label TEXT NOT NULL,
            signal_time TEXT NOT NULL,
            predicted_multiplier REAL NOT NULL,
            confidence TEXT NOT NULL DEFAULT 'Unrated',
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'PUBLISHED',
            created_at TEXT NOT NULL
        )""")

        admin_username = ADMIN_USERNAME
        admin_password = ADMIN_PASSWORD
        if admin_username and admin_password and len(admin_password) >= 12:
            # The .env administrator account is authoritative. Create it on
            # first boot, or promote/synchronize the same username if it was
            # previously created as a customer account. Only a password hash
            # is stored in SQLite; the plaintext remains in the private .env.
            admin = conn.execute("SELECT id FROM users WHERE username=?", (admin_username,)).fetchone()
            admin_hash = hash_password(admin_password)
            if not admin:
                admin_phone = os.getenv("ADMIN_PHONE", "254700000000").strip()
                conn.execute("""INSERT INTO users (username,password,phone_number,balance,role,created_at)
                    VALUES (?,?,?,?,?,?)""", (admin_username, admin_hash, admin_phone, 0.0, "ADMIN", datetime.now().isoformat()))
            else:
                conn.execute("UPDATE users SET password=?, role='ADMIN', is_active=1 WHERE username=?", (admin_hash, admin_username))

        conn.commit()

    finally:
        conn.close()


# ============================================================
# GAME ENGINE
# ============================================================

def generate_crash_point():
    value = random.random()

    if value < 0.05:
        return 1.00

    if value < 0.25:
        return round(
            random.uniform(1.01, 1.50),
            2
        )

    if value < 0.65:
        return round(
            random.uniform(1.51, 3.50),
            2
        )

    if value < 0.90:
        return round(
            random.uniform(3.51, 15.00),
            2
        )

    return round(
        random.uniform(15.01, 150.00),
        2
    )


def calculate_multiplier(elapsed):
    """Calculate an accelerating crash-game multiplier.

    The multiplier grows smoothly and progressively faster as the round
    continues. Keep this deterministic for a given elapsed time so server
    state, bets, and cash-outs all use the same value.
    """
    elapsed = max(0.0, float(elapsed))
    multiplier = math.exp(0.115 * elapsed)
    return round(max(multiplier, 1.0), 2)


GAME = {
    "round_id": None,
    "crash_point": None,

    "next_crash_point_1": generate_crash_point(),
    "next_crash_point_2": generate_crash_point(),

    "status": "BETTING",

    "betting_start": None,
    "run_start": None,

    "current_multiplier": 1.00,

    "crash_time": None,

    "bot_bets": []
}


FAKE_USERS = [
    "***1",
    "***2",
    "***3",
    "***4",
    "***5",
    "***6",
    "***7",
    "***8",
    "***9",
    "alex***",
    "brian***",
    "coll***",
    "david***",
    "eric***",
    "frank***",
    "grace***",
    "harr***",
    "ian***",
    "john***",
    "kevin***",
    "lucy***",
    "mike***",
    "nick***",
    "oliver***",
    "peter***",
    "queen***",
    "ray***",
    "sam***",
    "tom***",
    "victor***",
    "wendy***",
    "kelv***",
    "sylv***",
    "mash***",
    "kip***",
    "wanj***",
    "njeri***",
    "ochi***",
    "otien***",
    "maina***",
    "chep***",
    "kiprot***",
    "kibet***",
    "baras***"
]


def generate_bot_bets():
    bets = []

    count = random.randint(35, 65)

    selected_users = random.choices(
        FAKE_USERS,
        k=count
    )

    for i, user in enumerate(selected_users):
        masked = (
            user[:3]
            + "***"
            + str(random.randint(0, 9))
        )

        amount = round(
            random.choice([
                20,
                50,
                100,
                200,
                500,
                1000,
                2500,
                5000,
                10000
            ]),
            2
        )

        target_cashout = (
            round(
                random.uniform(1.10, 6.00),
                2
            )
            if random.random() > 0.20
            else None
        )

        bets.append({
            "id": f"bot_{i}",
            "username": masked,
            "amount": amount,
            "auto_cashout": target_cashout,
            "status": "ACTIVE",
            "cashout_multiplier": None,
            "winnings": 0.0
        })

    return bets


def create_round_locked():
    crash_point = GAME["next_crash_point_1"]

    GAME["next_crash_point_1"] = (
        GAME["next_crash_point_2"]
    )

    GAME["next_crash_point_2"] = (
        generate_crash_point()
    )

    now = datetime.now().isoformat()

    conn = get_db()

    try:
        cursor = conn.execute(
            """
            INSERT INTO rounds
            (
                crash_point,
                started_at
            )
            VALUES (?, ?)
            """,
            (
                crash_point,
                now
            )
        )

        round_id = cursor.lastrowid

        conn.commit()

    finally:
        conn.close()

    GAME["round_id"] = round_id
    GAME["crash_point"] = crash_point
    GAME["status"] = "BETTING"
    GAME["betting_start"] = time.time()
    GAME["run_start"] = None
    GAME["current_multiplier"] = 1.00
    GAME["crash_time"] = None
    GAME["bot_bets"] = generate_bot_bets()


def initialize_game():
    with GAME_LOCK:
        if GAME["round_id"] is None:
            create_round_locked()


def start_running_locked():
    if GAME["status"] != "BETTING":
        return

    GAME["status"] = "RUNNING"
    GAME["run_start"] = time.time()
    GAME["current_multiplier"] = 1.00


def process_auto_cashouts_locked():
    if GAME["status"] != "RUNNING":
        return

    multiplier = GAME["current_multiplier"]
    crash_point = GAME["crash_point"]
    round_id = GAME["round_id"]

    if multiplier >= crash_point:
        return

    # --------------------------------------------------------
    # BOT AUTO CASHOUTS
    # --------------------------------------------------------

    for bot in GAME["bot_bets"]:
        if (
            bot["status"] == "ACTIVE"
            and bot["auto_cashout"] is not None
            and bot["auto_cashout"] <= multiplier
            and bot["auto_cashout"] < crash_point
        ):
            bot["status"] = "WON"

            bot["cashout_multiplier"] = (
                bot["auto_cashout"]
            )

            bot["winnings"] = round(
                bot["amount"]
                * bot["auto_cashout"],
                2
            )

    # Some bots manually cash out.
    for bot in GAME["bot_bets"]:
        if (
            bot["status"] == "ACTIVE"
            and bot["auto_cashout"] is None
            and multiplier > 1.30
        ):
            if random.random() < 0.05:
                bot["status"] = "WON"

                bot["cashout_multiplier"] = (
                    multiplier
                )

                bot["winnings"] = round(
                    bot["amount"] * multiplier,
                    2
                )

    # --------------------------------------------------------
    # REAL USER AUTO CASHOUTS
    # --------------------------------------------------------

    conn = get_db()

    try:
        bets = conn.execute(
            """
            SELECT *
            FROM bets
            WHERE round_id = ?
              AND status = 'ACTIVE'
              AND auto_cashout IS NOT NULL
            """,
            (round_id,)
        ).fetchall()

        for bet in bets:
            target = float(
                bet["auto_cashout"]
            )

            if (
                target <= multiplier
                and target < crash_point
            ):
                winnings = round(
                    float(bet["amount"])
                    * target,
                    2
                )

                cursor = conn.execute(
                    """
                    UPDATE bets

                    SET
                        status='WON',
                        cashout_multiplier=?,
                        winnings=?

                    WHERE id=?
                      AND status='ACTIVE'
                    """,
                    (
                        target,
                        winnings,
                        bet["id"]
                    )
                )

                if cursor.rowcount == 1:
                    conn.execute(
                        """
                        UPDATE users

                        SET balance =
                            balance + ?

                        WHERE username=?
                        """,
                        (
                            winnings,
                            bet["username"]
                        )
                    )

        conn.commit()

    finally:
        conn.close()


def crash_round_locked():
    if GAME["status"] == "CRASHED":
        return

    GAME["status"] = "CRASHED"

    GAME["current_multiplier"] = (
        GAME["crash_point"]
    )

    GAME["crash_time"] = time.time()

    for bot in GAME["bot_bets"]:
        if bot["status"] == "ACTIVE":
            bot["status"] = "LOST"

    conn = get_db()

    try:
        conn.execute(
            """
            UPDATE bets

            SET status='LOST'

            WHERE round_id=?
              AND status='ACTIVE'
            """,
            (GAME["round_id"],)
        )

        conn.execute(
            """
            UPDATE rounds

            SET ended_at=?

            WHERE id=?
            """,
            (
                datetime.now().isoformat(),
                GAME["round_id"]
            )
        )

        conn.commit()

    finally:
        conn.close()


def tick_game_locked():
    initialize_game()

    now = time.time()

    if GAME["status"] == "BETTING":

        elapsed = (
            now
            - GAME["betting_start"]
        )

        GAME["current_multiplier"] = 1.00

        if elapsed >= BETTING_WINDOW:
            start_running_locked()

    elif GAME["status"] == "RUNNING":

        elapsed = (
            now
            - GAME["run_start"]
        )

        multiplier = calculate_multiplier(
            elapsed
        )

        GAME["current_multiplier"] = (
            multiplier
        )

        process_auto_cashouts_locked()

        if multiplier >= GAME["crash_point"]:
            crash_round_locked()

    elif GAME["status"] == "CRASHED":

        if (
            GAME["crash_time"] is not None
            and (
                now
                - GAME["crash_time"]
            ) >= CRASH_DISPLAY_TIME
        ):
            create_round_locked()


def game_loop():
    while True:

        try:
            with GAME_LOCK:
                tick_game_locked()

        except Exception as exc:
            print(
                "Game engine error:",
                repr(exc)
            )

        time.sleep(0.04)


# ============================================================
# USER HELPERS
# ============================================================

def get_user(username):
    conn = get_db()

    try:
        return conn.execute(
            """
            SELECT
                username,
                phone_number,
                balance,
                role

            FROM users

            WHERE username=?
            """,
            (username,)
        ).fetchone()

    finally:
        conn.close()


def normalize_mpesa_phone(phone):
    """
    Convert common Kenyan formats to:

        2547XXXXXXXX
        2541XXXXXXXX
    """

    value = str(
        phone or ""
    ).strip()

    value = (
        value
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if value.startswith("+"):
        value = value[1:]

    if (
        value.startswith("0")
        and len(value) == 10
    ):
        value = "254" + value[1:]

    elif (
        (
            value.startswith("7")
            or value.startswith("1")
        )
        and len(value) == 9
    ):
        value = "254" + value

    valid = (
        len(value) == 12
        and value.startswith("254")
        and value[3] in ("7", "1")
        and value.isdigit()
    )

    if not valid:
        raise ValueError(
            "Enter a valid Kenyan M-Pesa number, "
            "for example 0712345678."
        )

    return value


def safe_float(value, default=None):
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (
        TypeError,
        ValueError
    ):
        return default


def make_nexus_reference(prefix, username):
    return (
        f"{prefix}-{username[:8]}-"
        f"{int(time.time())}-"
        f"{secrets.token_hex(3).upper()}"
    )


# ============================================================
# NEXUS PAY
# ============================================================

def nexus_headers():
    if not NEXUS_PAY_API_KEY:
        raise RuntimeError(
            "NEXUS_PAY_API_KEY is not configured. Add it to .env."
        )

    return {
        "X-API-Key": NEXUS_PAY_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


def nexus_stk_push(
    phone_number,
    amount,
    username
):
    """
    Send an M-Pesa STK Push through Nexus Pay.

    Nexus Pay published request:

        POST /api/payments/stkpush

    JSON:

        {
            "phoneNumber": "254712345678",
            "amount": 500,
            "accountReference": "ORDER-001",
            "transactionDesc": "Payment for order"
        }
    """

    phone = normalize_mpesa_phone(
        phone_number
    )

    amount = safe_float(amount)

    if amount is None or amount < 5:
        raise ValueError(
            "Minimum deposit is KES 5."
        )

    if amount != round(amount):
        raise ValueError(
            "Deposit amount must be a whole KES amount."
        )

    amount = int(round(amount))

    # Short unique reference.
    reference = make_nexus_reference("AV", username)

    payload = {
        "phoneNumber": phone,
        "amount": amount,
        "accountReference": reference,
        "transactionDesc": "Aviator deposit"
    }

    url = (
        f"{NEXUS_PAY_BASE_URL}"
        "/api/payments/stkpush"
    )

    response = requests.post(
        url,
        json=payload,
        headers=nexus_headers(),
        timeout=NEXUS_PAY_TIMEOUT
    )

    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "Nexus Pay returned an invalid response."
        )

    # Keep the entire provider response useful,
    # while trying several common identifiers.
    provider_transaction_id = (
        data.get("transactionId")
        or data.get("transaction_id")
        or data.get("checkoutRequestId")
        or data.get("checkout_request_id")
        or data.get("id")
    )

    # Some APIs return success as a boolean,
    # others return a status/code.
    success = data.get("success")

    if success is False:
        message = (
            data.get("message")
            or data.get("error")
            or data.get("description")
            or "Nexus Pay rejected the payment request."
        )

        raise RuntimeError(str(message))

    status_value = str(
        data.get("status", "")
    ).upper()

    if status_value in (
        "FAILED",
        "FAILURE",
        "ERROR",
        "REJECTED"
    ):
        message = (
            data.get("message")
            or data.get("error")
            or data.get("description")
            or "Nexus Pay rejected the payment request."
        )

        raise RuntimeError(str(message))

    now = datetime.now().isoformat()

    conn = get_db()

    try:
        conn.execute(
            """
            INSERT INTO nexus_transactions
            (
                username,
                phone_number,
                amount,
                reference,
                provider_transaction_id,
                status,
                provider_message,
                created_at,
                updated_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                phone,
                float(amount),
                reference,
                (
                    str(provider_transaction_id)
                    if provider_transaction_id
                    else None
                ),
                "PENDING",
                (
                    data.get("message")
                    or data.get("description")
                    or "STK Push initiated."
                ),
                now,
                now
            )
        )

        conn.commit()

    finally:
        conn.close()

    return {
        "reference": reference,
        "provider_transaction_id":
            provider_transaction_id,
        "message":
            data.get("message")
            or data.get("description")
            or "M-Pesa prompt sent.",
        "provider_response": data
    }


# ============================================================
# NEXUS TRANSACTION HELPERS
# ============================================================

def get_nexus_transaction(
    reference,
    username
):
    conn = get_db()

    try:
        return conn.execute(
            """
            SELECT *

            FROM nexus_transactions

            WHERE reference=?
              AND username=?
            """,
            (
                reference,
                username
            )
        ).fetchone()

    finally:
        conn.close()


def credit_nexus_transaction(
    reference
):
    """
    IMPORTANT:

    This function is intentionally not exposed as a public
    "mark paid" endpoint.

    It can be called only after your provider's documented
    confirmation mechanism has verified the payment.

    It is idempotent: the same transaction cannot be credited twice.
    """

    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        tx = conn.execute(
            """
            SELECT *

            FROM nexus_transactions

            WHERE reference=?
            """,
            (reference,)
        ).fetchone()

        if not tx:
            conn.rollback()
            return False, "Transaction not found."

        if tx["status"] in ("APPROVED", "SUCCESS"):
            conn.commit()
            return True, "Already credited."
        if tx["status"] != "PAYMENT_VERIFIED":
            conn.rollback()
            return False, "Payment must be verified before admin approval."

        amount = float(tx["amount"])

        now = datetime.now().isoformat()

        cursor = conn.execute(
            """
            UPDATE nexus_transactions

            SET
                status='APPROVED',
                updated_at=?,
                credited_at=?

            WHERE reference=?
              AND status='PAYMENT_VERIFIED'
            """,
            (
                now,
                now,
                reference
            )
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return False, "Transaction could not be credited."

        conn.execute(
            """
            UPDATE users

            SET balance=balance+?

            WHERE username=?
            """,
            (
                amount,
                tx["username"]
            )
        )

        conn.commit()

        return True, (
            f"Deposit of KES "
            f"{amount:,.2f} credited."
        )

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# BALANCE / BET FUNCTIONS
# ============================================================

def deduct_balance(
    username,
    amount
):
    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute(
            """
            UPDATE users

            SET balance=balance-?

            WHERE username=?
              AND balance>=?
            """,
            (
                amount,
                username,
                amount
            )
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return False

        conn.commit()

        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def place_bet_for_user(
    username,
    bet_number,
    amount,
    auto_cashout
):
    with GAME_LOCK:

        tick_game_locked()

        if bet_number not in (1, 2):
            return False, "Invalid bet slot."

        if GAME["status"] != "BETTING":
            return False, "Betting closed for this round."

        amount = safe_float(amount)

        if amount is None:
            return False, "Invalid amount."

        if amount <= 0:
            return False, "Amount must be greater than zero."

        if auto_cashout in (
            None,
            "",
            False
        ):
            auto_cashout = None

        else:
            auto_cashout = safe_float(
                auto_cashout
            )

            if auto_cashout is None:
                return False, "Invalid auto cashout."

            if auto_cashout < 1.01:
                return False, (
                    "Auto cashout minimum is 1.01x."
                )

        conn = get_db()

        try:
            conn.execute("BEGIN IMMEDIATE")

            existing = conn.execute(
                """
                SELECT id

                FROM bets

                WHERE username=?
                  AND round_id=?
                  AND bet_number=?
                """,
                (
                    username,
                    GAME["round_id"],
                    bet_number
                )
            ).fetchone()

            if existing:
                conn.rollback()

                return False, (
                    f"Bet {bet_number} already placed."
                )

            user = conn.execute(
                """
                SELECT balance

                FROM users

                WHERE username=?
                """,
                (username,)
            ).fetchone()

            if not user:
                conn.rollback()
                return False, "User not found."

            if float(user["balance"]) < amount:
                conn.rollback()
                return False, "Insufficient balance."

            cursor = conn.execute(
                """
                UPDATE users

                SET balance=balance-?

                WHERE username=?
                  AND balance>=?
                """,
                (
                    amount,
                    username,
                    amount
                )
            )

            if cursor.rowcount != 1:
                conn.rollback()
                return False, "Insufficient balance."

            conn.execute(
                """
                INSERT INTO bets
                (
                    username,
                    round_id,
                    bet_number,
                    amount,
                    auto_cashout,
                    winnings,
                    status,
                    created_at
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    GAME["round_id"],
                    bet_number,
                    amount,
                    auto_cashout,
                    0.0,
                    "ACTIVE",
                    datetime.now().isoformat()
                )
            )

            conn.commit()

            return True, (
                f"Bet {bet_number} placed."
            )

        except Exception as exc:
            conn.rollback()

            print(
                "Place bet error:",
                repr(exc)
            )

            return False, "Failed to place bet."

        finally:
            conn.close()


def manual_cashout(
    username,
    bet_number
):
    with GAME_LOCK:

        tick_game_locked()

        if GAME["status"] != "RUNNING":
            return False, "Flight not running."

        multiplier = GAME["current_multiplier"]

        if multiplier >= GAME["crash_point"]:
            return False, "Round crashed."

        multiplier = round(
            multiplier,
            2
        )

        conn = get_db()

        try:
            conn.execute("BEGIN IMMEDIATE")

            bet = conn.execute(
                """
                SELECT *

                FROM bets

                WHERE username=?
                  AND round_id=?
                  AND bet_number=?
                  AND status='ACTIVE'
                """,
                (
                    username,
                    GAME["round_id"],
                    bet_number
                )
            ).fetchone()

            if not bet:
                conn.rollback()
                return False, (
                    "No active bet found."
                )

            winnings = round(
                float(bet["amount"])
                * multiplier,
                2
            )

            cursor = conn.execute(
                """
                UPDATE bets

                SET
                    status='WON',
                    cashout_multiplier=?,
                    winnings=?

                WHERE id=?
                  AND status='ACTIVE'
                """,
                (
                    multiplier,
                    winnings,
                    bet["id"]
                )
            )

            if cursor.rowcount != 1:
                conn.rollback()
                return False, "Cashout failed."

            conn.execute(
                """
                UPDATE users

                SET balance=balance+?

                WHERE username=?
                """,
                (
                    winnings,
                    username
                )
            )

            conn.commit()

            return True, (
                f"Cashed out at "
                f"{multiplier:.2f}x — "
                f"KES {winnings:,.2f}"
            )

        except Exception as exc:
            conn.rollback()

            print(
                "Cashout error:",
                repr(exc)
            )

            return False, "Cashout error."

        finally:
            conn.close()


# ============================================================
# SECURITY / ACTIVITY / SMS HELPERS
# ============================================================
def touch_user(username):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET last_seen_at=? WHERE username=?", (datetime.now().isoformat(), username))
        conn.commit()
    finally:
        conn.close()


def audit_admin(action, target_username=None, details=None):
    if session.get("role") != "ADMIN":
        return
    conn = get_db()
    try:
        conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
            (session.get("username", "unknown"), action, target_username, str(details or "")[:1000], request.headers.get("X-Forwarded-For", request.remote_addr), datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()


def admin_required():
    """Require a current database-backed ADMIN account, not just a session flag."""
    username = session.get("username")
    if not username or session.get("role") != "ADMIN":
        return False
    conn = get_db()
    try:
        row = conn.execute("SELECT role, is_active FROM users WHERE username=?", (username,)).fetchone()
        return bool(row and row["role"] == "ADMIN" and int(row["is_active"] or 0) == 1)
    finally:
        conn.close()


def send_at_otp(phone, code):
    if not AT_USERNAME or not AT_API_KEY:
        raise RuntimeError("Africa's Talking is not configured. Set AT_USERNAME and AT_API_KEY in .env.")
    message = f"Your Aviator password reset code is {code}. It expires in {OTP_TTL_MINUTES} minutes. If you did not request this, ignore this message."
    payload = {"username": AT_USERNAME, "to": phone, "message": message}
    if AT_SENDER_ID:
        payload["from"] = AT_SENDER_ID
    response = requests.post("https://api.africastalking.com/version1/messaging", data=payload,
        headers={"apiKey": AT_API_KEY, "Accept": "application/json"}, timeout=15)
    response.raise_for_status()
    body = response.json()
    recipients = (body.get("SMSMessageData") or {}).get("Recipients") or []
    if not recipients or str(recipients[0].get("status", "")).lower() not in {"success", "sent", "accepted"}:
        raise RuntimeError("Africa's Talking did not confirm that the OTP was accepted for sending.")

# ============================================================
# PLAYER LOBBY AND PAID SIGNAL PAGES
# ============================================================
LOBBY_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Game Lobby</title><style>
*{box-sizing:border-box}body{margin:0;background:#0d1016;color:#f4f6fa;font:15px Arial,sans-serif}.top{padding:18px 5%;background:#171c25;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.top a{color:#ffca6b;text-decoration:none}.wrap{max-width:1180px;margin:auto;padding:28px 5%}.hero{padding:26px;border-radius:18px;background:linear-gradient(120deg,#182b26,#17202d);border:1px solid #2d4b40;margin-bottom:22px}.hero h1{margin:0 0 8px;font-size:clamp(25px,5vw,38px)}.muted{color:#aeb8c6;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.game{background:#181e28;border:1px solid #303948;border-radius:14px;padding:20px;min-height:190px;display:flex;flex-direction:column}.game h2{margin:5px 0 8px}.game .emoji{font-size:32px}.game .tag{font-size:11px;color:#ffca6b;text-transform:uppercase;letter-spacing:1px}.game a,.game button{margin-top:auto;display:inline-block;text-align:center;padding:12px;border:0;border-radius:8px;background:#28a745;color:white;text-decoration:none;font-weight:bold;cursor:pointer}.game.disabled{opacity:.75}.game.disabled button{background:#454d59;cursor:not-allowed}.notice{margin-top:20px;padding:14px;border:1px solid #6b5630;background:#2a2418;border-radius:10px;color:#f2d38a;font-size:13px}@media(max-width:520px){.wrap{padding:18px 4%}.hero{padding:20px}.top{padding:14px 4%}}
</style></head><body><header class="top"><b>✈️ AVIATOR · GAME LOBBY</b><span>Welcome, <strong>@{{ username }}</strong> · Available: <strong>KES {{ '%.2f'|format(balance) }}</strong> &nbsp; <a href="/logout">Logout</a></span></header><main class="wrap"><section class="hero"><h1>Choose your game</h1><p class="muted">Explore the game lobby. Aviator is currently available; additional games are shown in the catalogue and will be enabled after their game engines and payment rules are implemented.</p></section><section class="grid">
<article class="game"><div class="emoji">✈️</div><span class="tag">Available</span><h2>Aviator</h2><p class="muted">Play the live crash game, manage bets and cash out before the round ends.</p><a href="/aviator">PLAY AVIATOR</a></article>
<article class="game"><div class="emoji">🚀</div><span class="tag">Signals</span><h2>Aviator Signals</h2><p class="muted">Choose a paid signal access package and view administrator-published estimates after payment is confirmed.</p><a href="/signals">AVIATOR SIGNAL</a></article>
<article class="game disabled"><div class="emoji">💎</div><span class="tag">Coming soon</span><h2>Mines</h2><p class="muted">Grid-based risk game. Not yet enabled for wagering.</p><button disabled>COMING SOON</button></article>
<article class="game disabled"><div class="emoji">🎯</div><span class="tag">Coming soon</span><h2>Plinko</h2><p class="muted">Ball-drop multiplier game. Not yet enabled for wagering.</p><button disabled>COMING SOON</button></article>
<article class="game disabled"><div class="emoji">🎲</div><span class="tag">Coming soon</span><h2>Dice</h2><p class="muted">Number prediction game. Not yet enabled for wagering.</p><button disabled>COMING SOON</button></article>
<article class="game disabled"><div class="emoji">🪐</div><span class="tag">Coming soon</span><h2>Spaceman</h2><p class="muted">Multiplier-style game. Not yet enabled for wagering.</p><button disabled>COMING SOON</button></article>
<article class="game disabled"><div class="emoji">⚡</div><span class="tag">Coming soon</span><h2>JetX</h2><p class="muted">Crash-style game. Not yet enabled for wagering.</p><button disabled>COMING SOON</button></article>
<article class="game disabled"><div class="emoji">🎡</div><span class="tag">Coming soon</span><h2>Lucky Wheel</h2><p class="muted">Wheel game. Not yet enabled for wagering.</p><button disabled>COMING SOON</button></article>
</section><p class="notice"> <strong>TECH-STAR</strong><br>
    Evron Enterprises.</p></main></body></html>"""

SIGNALS_HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aviator Signals</title><meta name="signal-csrf" content="{{ csrf }}"><style>
*{box-sizing:border-box}body{margin:0;background:#0d1016;color:#f4f6fa;font:15px Arial,sans-serif}.top{padding:16px 5%;background:#171c25;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.top a{color:#8dc5ff;text-decoration:none}.wrap{max-width:1000px;margin:auto;padding:25px 5%}.panel{background:#181e28;border:1px solid #303948;border-radius:14px;padding:20px;margin-bottom:16px}.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.plan{border:1px solid #3a4656;border-radius:12px;padding:18px;background:#111720}.price{font-size:30px;color:#39d98a;font-weight:bold}.btn{display:block;width:100%;padding:13px;border:0;border-radius:8px;background:#28a745;color:white;font-weight:bold;cursor:pointer;margin-top:12px}.muted{color:#aeb8c6;line-height:1.5}.warn{color:#ffd17b;background:#2b2418;border:1px solid #6a552f;padding:12px;border-radius:9px}.status{padding:12px;border-radius:9px;background:#172b22;color:#a8f0c6}.feed{display:grid;gap:10px}.signal{padding:14px;border:1px solid #3b4655;border-radius:10px;background:#111720}.signal strong{color:#ffd17b}.locked{opacity:.95}.field{width:100%;padding:12px;margin-top:7px;background:#0d1016;color:white;border:1px solid #3a4656;border-radius:8px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #303948}.scroll{overflow:auto}@media(max-width:520px){.wrap{padding:16px 4%}.panel{padding:15px}}
</style></head><body><header class="top"><b>✈️ AVIATOR SIGNAL CENTER</b><span>@{{ username }} &nbsp; <a href="/lobby">Game lobby</a> &nbsp; <a href="/aviator">Play Aviator</a></span></header><main class="wrap"><h1>Aviator signal access</h1><p class="muted">Select a time-limited access package. Nexus Pay will send an M-Pesa STK prompt to your phone. Your access starts only after the signed Nexus webhook verifies the exact amount and an administrator approves the order.</p>
{% if active %}<section class="panel"><h2>Signal access active</h2><p class="status">Payment confirmed and approved. Access expires at {{ active.expires_at }}.</p><p class="muted">Next Aviator round: <strong id="customer-next-round">#{{ next_round }}</strong></p><p class="muted">Package: {{ active.plan_minutes }} minutes · Paid: KES {{ '%.2f'|format(active.amount) }}</p><h3>Administrator-published signals</h3><p class="muted">These are estimates supplied by the administrator, not guaranteed predictions.</p><div class="feed">{% for sig in signals %}<article class="signal"><strong>{{ sig.round_label }}</strong> · {{ sig.signal_time }}<h2>{{ '%.2f'|format(sig.predicted_multiplier) }}x estimate</h2><p class="muted">Confidence label: {{ sig.confidence }}{% if sig.notes %}<br>{{ sig.notes }}{% endif %}</p></article>{% else %}<p class="muted">No signals have been published during this access period yet. Refresh this page later.</p>{% endfor %}</div></section>{% else %}<section class="panel locked"><h2>Choose your signal package</h2><div class="plans"><article class="plan"><h3>5-minute signal</h3><div class="price">KES 200</div><p class="muted">Five minutes of access after payment confirmation.</p><button class="btn" onclick="buySignal(5)">PAY KES 200</button></article><article class="plan"><h3>10-minute signal</h3><div class="price">KES 400</div><p class="muted">Ten minutes of access after payment confirmation.</p><button class="btn" onclick="buySignal(10)">PAY KES 400</button></article></div><label for="phone">M-Pesa phone number</label><input class="field" id="phone" placeholder="0712345678" inputmode="tel"><p id="payStatus" class="muted" aria-live="polite">No active signal subscription.</p></section>{% endif %}
<section class="panel"><h3>Recent signal purchases</h3><div class="scroll"><table><tr><th>Package</th><th>Amount</th><th>Status</th><th>Expires</th></tr>{% for item in history %}<tr><td>{{ item.plan_minutes }} minutes</td><td>KES {{ '%.2f'|format(item.amount) }}</td><td>{{ item.status }}</td><td>{{ item.expires_at or '—' }}</td></tr>{% else %}<tr><td colspan="4">No signal purchases yet.</td></tr>{% endfor %}</table></div></section>
<p class="warn">Important: Aviator outcomes are random. Premium signals are provided
    to help guide betting decisions.
    Purchasing signals guarantee a successful outcome.</p></main>
<script>
async function refreshCustomerNextRound(){const el=document.getElementById('customer-next-round');if(!el)return;try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)return;const d=await r.json();el.textContent='#'+(Number(d.round_id||0)+1);}catch(e){}}
refreshCustomerNextRound();setInterval(refreshCustomerNextRound,2500);
async function buySignal(minutes){const amount=minutes===5?200:400;const phone=document.getElementById('phone').value.trim();if(!confirm(`You are about to request an M-Pesa STK prompt for KES ${amount} for ${minutes}-minute Aviator signal access. Continue?`))return;const status=document.getElementById('payStatus');status.textContent='Requesting secure M-Pesa prompt…';try{const r=await fetch('/api/signals/purchase',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name=signal-csrf]').content},body:JSON.stringify({minutes,phone_number:phone})});const data=await r.json();if(!r.ok||!data.success)throw new Error(data.message||'Payment request failed.');status.textContent=data.message+' Reference: '+data.reference+' Waiting for payment verification and administrator approval…';let tries=0;const timer=setInterval(async()=>{tries++;try{const sr=await fetch('/api/signals/order/'+encodeURIComponent(data.reference));const st=await sr.json();if(st.status==='PAID'){clearInterval(timer);status.textContent='Payment confirmed. Opening your signal access…';window.location.assign('/signals?payment=confirmed');}else if(st.status==='FAILED'){clearInterval(timer);status.textContent='Payment was not completed. You may try again.';}else if(tries>=60){clearInterval(timer);status.textContent='Still awaiting verification or administrator approval. Do not pay again; refresh later to check status.';}}catch(e){}},3000);}catch(e){status.textContent=e.message;}}
</script></body></html>"""

# ============================================================
# AUTHENTICATION
# ============================================================

@app.route("/")
def index():
    if "username" not in session:
        return redirect("/login")
    touch_user(session["username"])
    if session.get("role") == "ADMIN":
        return redirect("/admin")
    return redirect("/lobby")


@app.route("/lobby")
def player_lobby():
    if "username" not in session:
        return redirect("/login")
    if session.get("role") == "ADMIN":
        return redirect("/admin")
    touch_user(session["username"])
    conn = get_db()
    try:
        player = conn.execute("SELECT balance FROM users WHERE username=?", (session["username"],)).fetchone()
        balance = float(player["balance"]) if player else 0.0
    finally:
        conn.close()
    return render_template_string(LOBBY_HTML, username=session["username"], balance=balance)


@app.route("/aviator")
def aviator_game_page():
    if "username" not in session:
        return redirect("/login")
    # Admins may open the game page to view the admin-only upcoming-round
    # telemetry. The /api/state endpoint still withholds that data from
    # non-admin accounts on the server.
    touch_user(session["username"])
    return render_template_string(HTML, username=session["username"])


@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    error = None

    if request.method == "POST":

        username = (
            request.form
            .get("username", "")
            .strip()
        )

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        try:
            user = conn.execute(
                """
                SELECT *

                FROM users

                WHERE username=?
                """,
                (username,)
            ).fetchone()

        finally:
            conn.close()

        env_admin_login = bool(
            ADMIN_USERNAME and ADMIN_PASSWORD and len(ADMIN_PASSWORD) >= 12
            and secrets.compare_digest(username, ADMIN_USERNAME)
            and secrets.compare_digest(password, ADMIN_PASSWORD)
        )
        valid_login = bool(
            user and (
                (user["role"] == "ADMIN" and env_admin_login)
                or (user["role"] != "ADMIN"
                    and not (ADMIN_USERNAME and username == ADMIN_USERNAME)
                    and verify_password(password, user["password"]))
            )
        )

        if valid_login:
            # When .env admin credentials are used, keep the database admin
            # hash synchronized without ever storing plaintext credentials.
            if env_admin_login and not verify_password(ADMIN_PASSWORD, user["password"]):
                upgrade_conn = get_db()
                try:
                    upgrade_conn.execute("UPDATE users SET password=?, role='ADMIN' WHERE username=?",
                                          (hash_password(ADMIN_PASSWORD), ADMIN_USERNAME))
                    upgrade_conn.commit()
                finally:
                    upgrade_conn.close()
            # Upgrade legacy SHA-256 hashes after a successful login.
            if re.fullmatch(r"[0-9a-fA-F]{64}", str(user["password"])):
                upgrade_conn = get_db()
                try:
                    upgrade_conn.execute("UPDATE users SET password=? WHERE username=?", (hash_password(password), username))
                    upgrade_conn.commit()
                finally:
                    upgrade_conn.close()
            touch_user(username)
            session.clear()
            session.permanent = request.form.get("remember") == "1"

            session["username"] = (
                user["username"]
            )

            session["role"] = (
                user["role"]
            )

            return redirect("/" if user["role"] == "ADMIN" else "/lobby")

        error = "Invalid credentials."

    return render_template_string(
        LOGIN_HTML,
        error=error
    )


@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    error = None

    if request.method == "POST":

        username = (
            request.form
            .get("username", "")
            .strip()
        )

        password = request.form.get(
            "password",
            ""
        )

        phone = (
            request.form
            .get("phone_number", "")
            .strip()
        )

        if not username:
            error = "Username is required."

        elif len(username) < 3:
            error = (
                "Username must be at least 3 characters."
            )

        elif not password:
            error = "Password is required."

        elif len(password) < 10:
            error = (
                "Password must be at least 10 characters."
            )

        else:
            try:
                phone = normalize_mpesa_phone(
                    phone
                )

            except ValueError as exc:
                error = str(exc)

        if not error:

            conn = get_db()

            try:
                conn.execute(
                    """
                    INSERT INTO users
                    (
                        username,
                        password,
                        phone_number,
                        balance,
                        role,
                        created_at
                    )

                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        hash_password(password),
                        phone,
                        STARTING_BALANCE,
                        "USER",
                        datetime.now().isoformat()
                    )
                )

                conn.commit()

                session.clear()
                session.permanent = True

                session["username"] = (
                    username
                )

                session["role"] = "USER"

                return redirect("/lobby")

            except sqlite3.IntegrityError:
                error = (
                    "Username or phone number "
                    "is already registered."
                )

            finally:
                conn.close()

    return render_template_string(
        REGISTER_HTML,
        error=error
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ============================================================
# GAME API
# ============================================================

@app.route("/api/state")
def api_state():

    if "username" not in session:
        return jsonify({
            "error": "Unauthorized"
        }), 401

    touch_user(session["username"])
    with GAME_LOCK:

        tick_game_locked()

        username = session["username"]

        user = get_user(username)

        if not user:
            session.clear()

            return jsonify({
                "error": "User not found."
            }), 401

        is_admin = (
            user["role"] == "ADMIN"
        )

        conn = get_db()

        try:

            history_rows = conn.execute(
                """
                SELECT crash_point

                FROM rounds

                WHERE ended_at IS NOT NULL

                ORDER BY id DESC

                LIMIT 20
                """
            ).fetchall()

            history = [
                float(row["crash_point"])
                for row in reversed(
                    history_rows
                )
            ]

            bet_rows = conn.execute(
                """
                SELECT
                    bet_number,
                    amount,
                    auto_cashout,
                    cashout_multiplier,
                    winnings,
                    status

                FROM bets

                WHERE username=?
                  AND round_id=?
                """,
                (
                    username,
                    GAME["round_id"]
                )
            ).fetchall()
            pending_deposit = conn.execute(
                "SELECT COALESCE(SUM(amount),0) FROM nexus_transactions WHERE username=? AND status IN ('PENDING','PAYMENT_VERIFIED')",
                (username,)
            ).fetchone()[0]
            verified_pending_count = conn.execute(
                "SELECT COUNT(*) FROM nexus_transactions WHERE username=? AND status='PAYMENT_VERIFIED'",
                (username,)
            ).fetchone()[0]

        finally:
            conn.close()

        user_bets = {}

        all_live_bets = []

        # Bot feed.
        for bot in GAME["bot_bets"]:
            all_live_bets.append(bot)

        # Real user bets.
        for bet in bet_rows:

            user_bets[
                str(bet["bet_number"])
            ] = dict(bet)

            all_live_bets.append({
                "id":
                    f"real_{bet['bet_number']}",

                "username":
                    username,

                "amount":
                    float(bet["amount"]),

                "auto_cashout":
                    bet["auto_cashout"],

                "status":
                    bet["status"],

                "cashout_multiplier":
                    bet["cashout_multiplier"],

                "winnings":
                    float(bet["winnings"])
            })

        all_live_bets.sort(
            key=lambda item:
                0
                if item["status"] == "ACTIVE"
                else 1
        )

        return jsonify({

            "status":
                GAME["status"],

            "multiplier":
                GAME["current_multiplier"],

            "crash_point":
                (
                    GAME["crash_point"]
                    if GAME["status"] == "CRASHED"
                    else None
                ),

            "next_crash_point_1":
                (
                    GAME["next_crash_point_1"]
                    if is_admin
                    else None
                ),

            "next_crash_point_2":
                (
                    GAME["next_crash_point_2"]
                    if is_admin
                    else None
                ),

            "is_admin":
                is_admin,

            "balance":
                float(user["balance"]),

            "pending_deposit": float(pending_deposit),
            "verified_pending_count": int(verified_pending_count),

            "bets":
                user_bets,

            "live_feed":
                all_live_bets,

            "history":
                history,

            "round_id":
                GAME["round_id"]
        })


@app.route(
    "/api/bet",
    methods=["POST"]
)
def api_bet():

    if "username" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    bet_number = data.get(
        "bet_number",
        1
    )

    try:
        bet_number = int(bet_number)

    except (
        TypeError,
        ValueError
    ):
        return jsonify({
            "success": False,
            "message": "Invalid bet number."
        })

    success, message = place_bet_for_user(
        session["username"],
        bet_number,
        data.get("amount", 0),
        data.get("auto_cashout")
    )

    return jsonify({
        "success": success,
        "message": message
    })


@app.route(
    "/api/cashout",
    methods=["POST"]
)
def api_cashout():

    if "username" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    try:
        bet_number = int(
            data.get(
                "bet_number",
                1
            )
        )

    except (
        TypeError,
        ValueError
    ):
        return jsonify({
            "success": False,
            "message": "Invalid bet number."
        })

    success, message = manual_cashout(
        session["username"],
        bet_number
    )

    return jsonify({
        "success": success,
        "message": message
    })


# ============================================================
# NEXUS PAY STK PUSH
# ============================================================

@app.route(
    "/api/nexus/stkpush",
    methods=["POST"]
)
def api_nexus_stkpush():

    if "username" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    username = session["username"]

    user = get_user(username)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 401

    amount = safe_float(
        data.get("amount")
    )

    if amount is None:
        return jsonify({
            "success": False,
            "message": "Invalid amount."
        })

    if amount < 5:
        return jsonify({
            "success": False,
            "message": "Minimum deposit is KES 200. Please enter KES 200 or more."
        }), 400

    phone_input = (
        data.get("phone")
        or user["phone_number"]
    )

    try:
        phone = normalize_mpesa_phone(
            phone_input
        )

        result = nexus_stk_push(
            phone,
            amount,
            username
        )

        return jsonify({
            "success": True,

            "message":
                result["message"],

            "reference":
                result["reference"],

            "provider_transaction_id":
                result["provider_transaction_id"]
        })

    except ValueError as exc:

        return jsonify({
            "success": False,
            "message": str(exc)
        })

    except requests.Timeout:

        return jsonify({
            "success": False,
            "message":
                "Nexus Pay request timed out."
        }), 504

    except requests.HTTPError as exc:

        print(
            "Nexus Pay HTTP error:",
            repr(exc)
        )

        response = getattr(
            exc,
            "response",
            None
        )

        provider_message = None

        if response is not None:
            try:
                payload = response.json()

                provider_message = (
                    payload.get("message")
                    or payload.get("error")
                    or payload.get("description")
                )

            except Exception:
                provider_message = None

        return jsonify({
            "success": False,
            "message":
                provider_message
                or "Nexus Pay rejected the request."
        }), 502

    except requests.RequestException as exc:

        print(
            "Nexus Pay connection error:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "message":
                "Could not connect to Nexus Pay."
        }), 502

    except Exception as exc:

        print(
            "Nexus Pay STK error:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "message": str(exc)
        }), 500


# ============================================================
# NEXUS TRANSACTION STATUS
# ============================================================

@app.route(
    "/api/nexus/status/<path:reference>",
    methods=["GET"]
)
def api_nexus_status(reference):

    if "username" not in session:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    tx = get_nexus_transaction(
        reference,
        session["username"]
    )

    if not tx:
        return jsonify({
            "success": False,
            "message": "Transaction not found."
        }), 404

    return jsonify({
        "success": True,

        "reference":
            tx["reference"],

        "status":
            tx["status"],
        "available_for_betting": tx["status"] in ("APPROVED", "SUCCESS"),

        "amount":
            float(tx["amount"]),

        "message":
            tx["provider_message"]
            or "Waiting for payment confirmation.",

        "provider_transaction_id":
            tx["provider_transaction_id"],

        "created_at":
            tx["created_at"],

        "credited_at":
            tx["credited_at"]
    })


# ============================================================
# NEXUS PAY WEBHOOK
# ============================================================
#
# Nexus sends webhook events for payment.completed and payment.failed.
# The screenshot/documentation shows a payload shaped like:
#
#   {
#       "event": "payment.completed",
#       "data": { ... }
#   }
#
# The webhook is the authoritative source for the final transaction
# state. STK Push/B2C initiation only creates the transaction.
#
# Configure this URL in Nexus Pay Webhooks:
#
#   https://YOUR-PUBLIC-DOMAIN/api/nexus/webhook
#
# ============================================================

def _nexus_webhook_value(data, *keys):
    """Return the first non-empty value from a webhook payload."""
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _nexus_webhook_payload():
    """Normalize the Nexus webhook's event/data structure."""
    body = request.get_json(silent=True) or {}
    event = str(body.get("event") or body.get("type") or "").strip().lower()
    data = body.get("data")

    if not isinstance(data, dict):
        data = body

    return event, data, body


def _verify_nexus_webhook():
    """Verify Nexus Pay's SHA-256 HMAC webhook signature.

    Nexus documents X-Webhook-Signature as ``sha256=<hex>`` and says
    the HMAC-SHA256 is computed with the webhook secret. Verify the exact
    raw request bytes first. A compact-JSON fallback supports the provider's
    published Node example, which signs JSON.stringify(req.body).
    """
    if not NEXUS_WEBHOOK_SECRET:
        return False

    supplied = (request.headers.get("X-Webhook-Signature") or "").strip()
    if not supplied.startswith("sha256="):
        return False

    raw_body = request.get_data(cache=True, as_text=False)
    candidates = [raw_body]
    parsed = request.get_json(silent=True)
    if isinstance(parsed, dict):
        try:
            compact = json.dumps(
                parsed, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if compact != raw_body:
                candidates.append(compact)
        except (TypeError, ValueError, UnicodeError):
            pass

    for candidate in candidates:
        digest = hmac.new(
            NEXUS_WEBHOOK_SECRET.encode("utf-8"),
            candidate,
            hashlib.sha256
        ).hexdigest()
        expected = "sha256=" + digest
        if hmac.compare_digest(supplied, expected):
            return True
    return False


def _mark_deposit_webhook(reference, status, provider_transaction_id, message, amount):
    """Apply a deposit webhook exactly once and verify its amount."""
    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        tx = conn.execute(
            "SELECT * FROM nexus_transactions WHERE reference=?",
            (reference,)
        ).fetchone()

        if not tx:
            conn.rollback()
            return False, "Deposit transaction not found.", False

        if status == "SUCCESS" and amount in (None, ""):
            conn.rollback()
            return False, "Webhook amount is missing; deposit was not credited.", False

        if amount not in (None, ""):
            webhook_amount = safe_float(amount)
            if webhook_amount is None or abs(webhook_amount - float(tx["amount"])) > 0.001:
                conn.rollback()
                return False, "Webhook amount does not match the stored deposit.", False

        now = datetime.now().isoformat()
        provider_id = (
            str(provider_transaction_id)
            if provider_transaction_id not in (None, "")
            else tx["provider_transaction_id"]
        )
        provider_message = str(message or "Nexus webhook received.")

        if status == "SUCCESS":
            if tx["status"] in ("PAYMENT_VERIFIED", "APPROVED", "SUCCESS"):
                conn.commit()
                return True, "Payment already verified or approved; no duplicate credit applied.", False

            cursor = conn.execute(
                """UPDATE nexus_transactions
                   SET status='PAYMENT_VERIFIED', provider_transaction_id=?,
                       provider_message=?, updated_at=?, verified_at=?
                   WHERE reference=? AND status='PENDING'""",
                (provider_id, provider_message + " Payment verified; awaiting admin approval.", now, now, reference)
            )
            if cursor.rowcount != 1:
                conn.rollback()
                return False, "Deposit status could not be updated.", False
            conn.commit()
            return True, f"Payment of KES {float(tx['amount']):,.2f} verified; awaiting admin approval.", True

        if status == "FAILED":
            if tx["status"] == "FAILED":
                conn.commit()
                return True, "Deposit failure already recorded.", False

            conn.execute(
                """
                UPDATE nexus_transactions
                SET status='FAILED', provider_transaction_id=?,
                    provider_message=?, updated_at=?
                WHERE reference=? AND status='PENDING'
                """,
                (provider_id, provider_message, now, reference)
            )
            conn.commit()
            return True, "Deposit failure recorded.", True

        conn.commit()
        return True, "Deposit webhook received.", False

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _mark_withdrawal_webhook(reference, status, provider_transaction_id, message, amount):
    """Complete/fail a withdrawal exactly once and refund failures once."""
    conn = get_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        withdrawal = conn.execute(
            """
            SELECT * FROM withdrawals
            WHERE reference=? OR provider_transaction_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (reference, provider_transaction_id)
        ).fetchone()

        if not withdrawal:
            conn.rollback()
            return False, "Withdrawal transaction not found.", False

        if amount is not None:
            webhook_amount = safe_float(amount)
            if webhook_amount is None or abs(webhook_amount - float(withdrawal["amount"])) > 0.001:
                conn.rollback()
                return False, "Webhook amount does not match the stored withdrawal.", False

        now = datetime.now().isoformat()
        provider_id = (
            str(provider_transaction_id)
            if provider_transaction_id not in (None, "")
            else withdrawal["provider_transaction_id"]
        )
        provider_message = str(message or "Nexus webhook received.")

        if status == "SUCCESS":
            if withdrawal["status"] in {"SUCCESS", "COMPLETED", "PAID"}:
                conn.commit()
                return True, "Withdrawal already completed.", False

            cursor = conn.execute(
                """
                UPDATE withdrawals
                SET status='SUCCESS', reference=COALESCE(reference, ?),
                    provider_transaction_id=?, provider_message=?,
                    updated_at=?, completed_at=?
                WHERE id=? AND status IN ('PENDING', 'PROCESSING')
                """,
                (
                    reference,
                    provider_id,
                    provider_message,
                    now,
                    now,
                    withdrawal["id"]
                )
            )

            if cursor.rowcount != 1:
                conn.rollback()
                return False, "Withdrawal status could not be updated.", False

            conn.commit()
            return True, "Withdrawal completed.", True

        if status == "FAILED":
            if withdrawal["status"] == "FAILED":
                conn.commit()
                return True, "Withdrawal failure already recorded.", False

            # The balance was reserved when the withdrawal was created.
            # Refund only when transitioning PENDING/PROCESSING -> FAILED.
            cursor = conn.execute(
                """
                UPDATE withdrawals
                SET status='FAILED', reference=COALESCE(reference, ?),
                    provider_transaction_id=?, provider_message=?,
                    updated_at=?
                WHERE id=? AND status IN ('PENDING', 'PROCESSING')
                """,
                (
                    reference,
                    provider_id,
                    provider_message,
                    now,
                    withdrawal["id"]
                )
            )

            if cursor.rowcount != 1:
                conn.rollback()
                return False, "Withdrawal failure could not be recorded.", False

            conn.execute(
                "UPDATE users SET balance=balance+? WHERE username=?",
                (float(withdrawal["amount"]), withdrawal["username"])
            )
            conn.commit()
            return True, "Withdrawal failed and the reserved balance was refunded.", True

        conn.commit()
        return True, "Withdrawal webhook received.", False

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _mark_signal_payment_webhook(reference, status, provider_transaction_id, message, amount):
    """Confirm a signal subscription only after a verified Nexus webhook."""
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = conn.execute("SELECT * FROM signal_orders WHERE reference=?", (reference,)).fetchone()
        if not order:
            conn.rollback()
            return False, "Signal order not found.", False
        # A signed success event is not enough on its own: require the
        # provider's amount and compare it with the stored package price.
        # This prevents a missing/incorrect amount from activating access.
        if amount in (None, ""):
            conn.rollback()
            return False, "Signal payment webhook is missing the paid amount.", False
        paid_amount = safe_float(amount)
        if paid_amount is None or abs(paid_amount - float(order["amount"])) > 0.001:
            conn.rollback()
            return False, "Signal payment amount does not match the order.", False
        now = datetime.now()
        now_s = now.isoformat()
        provider_id = str(provider_transaction_id) if provider_transaction_id not in (None, "") else order["provider_transaction_id"]
        if status == "SUCCESS":
            if order["status"] in ("PAID", "PAYMENT_VERIFIED"):
                conn.commit()
                return True, "Signal payment already verified; awaiting administrator approval if not active.", False
            if order["status"] != "PENDING":
                conn.rollback()
                return False, "Signal order is not pending.", False
            conn.execute("""UPDATE signal_orders SET status='PAYMENT_VERIFIED', provider_transaction_id=?, provider_message=?, updated_at=? WHERE id=? AND status='PENDING'""",
                (provider_id, str(message or "Nexus payment confirmed; awaiting administrator approval."), now_s, order["id"]))
            conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
                ("SYSTEM", "SIGNAL_PAYMENT_VERIFIED", order["username"], f"{order['plan_minutes']} minute signal; KES {float(order['amount']):.2f}; {reference}; awaiting admin approval", "Nexus webhook", now_s))
            conn.commit()
            return True, "Signal payment verified; administrator approval is pending.", True
        if status == "FAILED":
            if order["status"] == "PENDING":
                conn.execute("UPDATE signal_orders SET status='FAILED',provider_transaction_id=?,provider_message=?,updated_at=? WHERE id=? AND status='PENDING'",
                    (provider_id, str(message or "Nexus payment failed."), now_s, order["id"]))
            conn.commit()
            return True, "Signal payment failure recorded.", True
        conn.commit()
        return True, "Signal payment event received.", False
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.route("/api/signals/purchase", methods=["POST"])
def api_signal_purchase():
    if "username" not in session or session.get("role") == "ADMIN":
        return jsonify({"success": False, "message": "Please log in as a player."}), 401
    supplied_csrf = request.headers.get("X-CSRF-Token", "")
    expected_csrf = session.get("csrf_token", "")
    if not expected_csrf or not secrets.compare_digest(str(supplied_csrf), str(expected_csrf)):
        return jsonify({"success": False, "message": "Session token expired. Refresh the page and try again."}), 400
    body = request.get_json(silent=True) or {}
    try:
        minutes = int(body.get("minutes", 0))
    except (TypeError, ValueError):
        minutes = 0
    plans = {5: 200, 10: 400}
    if minutes not in plans:
        return jsonify({"success": False, "message": "Choose the 5-minute or 10-minute signal package."}), 400
    conn = get_db()
    try:
        user = conn.execute("SELECT username,phone_number FROM users WHERE username=? AND role='USER' AND is_active=1", (session["username"],)).fetchone()
    finally:
        conn.close()
    if not user:
        return jsonify({"success": False, "message": "Player account is unavailable."}), 403
    try:
        phone = normalize_mpesa_phone(str(body.get("phone_number") or user["phone_number"]))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    amount = plans[minutes]
    reference = make_nexus_reference("SIG", session["username"])
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        conn.execute("INSERT INTO signal_orders(username,phone_number,plan_minutes,amount,reference,status,created_at,updated_at) VALUES(?,?,?,?,?,'PENDING',?,?)",
            (session["username"], phone, minutes, amount, reference, now, now))
        conn.commit()
    finally:
        conn.close()
    payload = {"phoneNumber": phone, "amount": amount, "accountReference": reference,
               "transactionDesc": f"Aviator signal access {minutes} minutes"}
    try:
        response = requests.post(f"{NEXUS_PAY_BASE_URL}/api/payments/stkpush", json=payload,
                                 headers=nexus_headers(), timeout=NEXUS_PAY_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if data.get("success") is False or str(data.get("status", "")).upper() in {"FAILED", "FAILURE", "ERROR", "REJECTED"}:
            raise RuntimeError(str(data.get("message") or data.get("error") or "Nexus Pay rejected the request."))
        provider_id = data.get("transactionId") or data.get("transaction_id") or data.get("checkoutRequestId") or data.get("checkout_request_id") or data.get("id")
        msg = str(data.get("message") or data.get("description") or "STK push initiated. Awaiting verified payment callback.")
        conn = get_db()
        try:
            conn.execute("UPDATE signal_orders SET provider_transaction_id=?,provider_message=?,updated_at=? WHERE reference=?",
                         (str(provider_id) if provider_id else None, msg, datetime.now().isoformat(), reference))
            conn.commit()
        finally:
            conn.close()
        return jsonify({"success": True, "reference": reference, "status": "PENDING",
                        "message": "M-Pesa prompt sent. Complete payment; signal access starts only after Nexus confirms payment."})
    except Exception as exc:
        conn = get_db()
        try:
            conn.execute("UPDATE signal_orders SET status='FAILED',provider_message=?,updated_at=? WHERE reference=? AND status='PENDING'",
                         (str(exc)[:500], datetime.now().isoformat(), reference))
            conn.commit()
        finally:
            conn.close()
        app.logger.exception("Signal STK push failed")
        return jsonify({"success": False, "message": "Could not initiate the signal payment. Check Nexus configuration and try again."}), 502


@app.route("/api/signals/order/<path:reference>")
def api_signal_order_status(reference):
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    conn = get_db()
    try:
        order = conn.execute("SELECT reference,status,plan_minutes,amount,expires_at FROM signal_orders WHERE reference=? AND username=?",
                             (reference, session["username"])).fetchone()
    finally:
        conn.close()
    if not order:
        return jsonify({"success": False, "message": "Order not found."}), 404
    return jsonify({"success": True, "reference": order["reference"], "status": order["status"],
                    "minutes": order["plan_minutes"], "amount": order["amount"], "expires_at": order["expires_at"]})


@app.route("/signals")
def player_signals_page():
    if "username" not in session or session.get("role") == "ADMIN":
        return redirect("/login")
    touch_user(session["username"])
    conn = get_db()
    try:
        now = datetime.now().isoformat()
        active = conn.execute("SELECT * FROM signal_orders WHERE username=? AND status='PAID' AND expires_at>? ORDER BY expires_at DESC LIMIT 1",
                              (session["username"], now)).fetchone()
        signals = []
        if active:
            signals = conn.execute("SELECT * FROM aviator_signals WHERE status='PUBLISHED' ORDER BY id DESC LIMIT 100").fetchall()
        history = conn.execute("SELECT plan_minutes,amount,status,created_at,expires_at FROM signal_orders WHERE username=? ORDER BY id DESC LIMIT 8",
                               (session["username"],)).fetchall()
    finally:
        conn.close()
    with GAME_LOCK:
        current_round = GAME.get("round_id")
        next_round = (int(current_round) + 1) if current_round is not None else 1
    return render_template_string(SIGNALS_HTML, username=session["username"], active=active, signals=signals, history=history, next_round=next_round, csrf=_csrf_token())


@app.route("/admin/signals/orders/<int:order_id>/approve", methods=["POST"])
def admin_approve_signal_order(order_id):
    if not admin_required():
        return redirect("/login")
    if not _check_csrf():
        return "Invalid request token. Refresh the admin page and try again.", 400
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        order = conn.execute("SELECT * FROM signal_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            conn.rollback()
            return "Signal order not found.", 404
        if order["status"] == "PAID":
            conn.commit()
            return redirect("/admin#signal-approvals")
        if order["status"] != "PAYMENT_VERIFIED":
            conn.rollback()
            return "Only Nexus payment-verified signal orders can be approved.", 409
        now = datetime.now()
        now_s = now.isoformat()
        expires = (now + timedelta(minutes=int(order["plan_minutes"]))).isoformat()
        cur = conn.execute("UPDATE signal_orders SET status='PAID', paid_at=?, expires_at=?, updated_at=?, provider_message=? WHERE id=? AND status='PAYMENT_VERIFIED'",
            (now_s, expires, now_s, "Payment independently verified and signal access approved by administrator.", order_id))
        if cur.rowcount != 1:
            conn.rollback()
            return "Signal approval conflict; refresh and retry.", 409
        conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
            (session["username"], "SIGNAL_ACCESS_APPROVED", order["username"], f"Reference={order['reference']}; amount={float(order['amount']):.2f}; minutes={order['plan_minutes']}; order_id={order_id}", request.headers.get("X-Forwarded-For", request.remote_addr), now_s))
        conn.commit()
    finally:
        conn.close()
    return redirect("/admin#signal-approvals")


@app.route("/admin/signals/publish", methods=["POST"])
def admin_publish_signal():
    if not admin_required():
        return redirect("/login")
    if not _check_csrf():
        return "Invalid request token. Refresh and retry.", 400
    round_label = request.form.get("round_label", "").strip()[:80]
    signal_time = request.form.get("signal_time", "").strip()[:80]
    multiplier = safe_float(request.form.get("predicted_multiplier"))
    confidence = request.form.get("confidence", "Unrated").strip()[:30]
    notes = request.form.get("notes", "").strip()[:500]
    if not round_label or not signal_time or multiplier is None or multiplier < 1 or multiplier > 1000:
        return "Enter a round label, time and a multiplier between 1.00 and 1000.00.", 400
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        conn.execute("INSERT INTO aviator_signals(admin_username,round_label,signal_time,predicted_multiplier,confidence,notes,status,created_at) VALUES(?,?,?,?,?,?,'PUBLISHED',?)",
                     (session["username"], round_label, signal_time, multiplier, confidence, notes, now))
        conn.commit()
        audit_admin("SIGNAL_PUBLISHED", None, f"{round_label}; estimate={multiplier:.2f}x")
    finally:
        conn.close()
    return redirect("/admin#signal-management")


@app.route("/admin/signals/<int:signal_id>/delete", methods=["POST"])
def admin_delete_signal(signal_id):
    if not admin_required():
        return redirect("/login")
    if not _check_csrf():
        return "Invalid request token. Refresh and retry.", 400
    conn = get_db()
    try:
        conn.execute("UPDATE aviator_signals SET status='REMOVED' WHERE id=?", (signal_id,))
        conn.commit()
        audit_admin("SIGNAL_REMOVED", None, f"signal_id={signal_id}")
    finally:
        conn.close()
    return redirect("/admin#signal-management")


@app.route(NEXUS_WEBHOOK_PATH, methods=["POST"])
def nexus_webhook():
    """Handle Nexus Pay payment.completed/payment.failed webhooks."""
    if not _verify_nexus_webhook():
        return jsonify({
            "success": False,
            "message": "Unauthorized webhook."
        }), 401

    event, data, body = _nexus_webhook_payload()

    if event not in {"payment.completed", "payment.failed", "payment.cancelled"}:
        # Acknowledge unrelated events so Nexus does not repeatedly retry them.
        return jsonify({
            "success": True,
            "message": "Event ignored.",
            "event": event or None
        }), 200

    reference = _nexus_webhook_value(
        data,
        "accountReference",
        "reference",
        "invoiceNumber",
        "invoice_number",
        "merchantReference",
        "merchant_reference"
    )

    provider_transaction_id = _nexus_webhook_value(
        data,
        "transactionId",
        "transaction_id",
        "providerTransactionId",
        "provider_transaction_id",
        "mpesaReceiptNumber",
        "checkoutRequestId",
        "orderTrackingId",
        "id"
    )

    amount = _nexus_webhook_value(data, "amount", "Amount")
    message = _nexus_webhook_value(
        data,
        "message",
        "description",
        "statusMessage",
        "status_message"
    )

    if not reference and not provider_transaction_id:
        return jsonify({
            "success": False,
            "message": "Missing transaction reference."
        }), 400

    status = "SUCCESS" if event == "payment.completed" else "FAILED"

    # Match the exact merchant/account reference first. Do not assume a
    # particular prefix: existing deployments may have references such as
    # AV-..., AVxxxx..., or AVD.... Fall back to a known provider ID only
    # when no local reference match exists.
    try:
        conn = get_db()
        try:
            deposit = conn.execute(
                "SELECT reference FROM nexus_transactions WHERE reference=?",
                (str(reference),)
            ).fetchone() if reference else None
            withdrawal = conn.execute(
                "SELECT reference FROM withdrawals WHERE reference=? ORDER BY id DESC LIMIT 1",
                (str(reference),)
            ).fetchone() if reference else None
            signal_order = conn.execute(
                "SELECT reference FROM signal_orders WHERE reference=?",
                (str(reference),)
            ).fetchone() if reference else None

            if not deposit and not withdrawal and not signal_order and provider_transaction_id:
                deposit = conn.execute(
                    "SELECT reference FROM nexus_transactions WHERE provider_transaction_id=?",
                    (str(provider_transaction_id),)
                ).fetchone()
                withdrawal = conn.execute(
                    "SELECT reference FROM withdrawals WHERE provider_transaction_id=? ORDER BY id DESC LIMIT 1",
                    (str(provider_transaction_id),)
                ).fetchone()
                signal_order = conn.execute(
                    "SELECT reference FROM signal_orders WHERE provider_transaction_id=? ORDER BY id DESC LIMIT 1",
                    (str(provider_transaction_id),)
                ).fetchone()
        finally:
            conn.close()

        if signal_order:
            ok, msg, changed = _mark_signal_payment_webhook(
                signal_order["reference"], status, provider_transaction_id, message, amount
            )
        elif withdrawal:
            ok, msg, changed = _mark_withdrawal_webhook(
                withdrawal["reference"], status, provider_transaction_id, message, amount
            )
        elif deposit:
            ok, msg, changed = _mark_deposit_webhook(
                deposit["reference"], status, provider_transaction_id, message, amount
            )
        else:
            return jsonify({
                "success": False,
                "message": "Transaction not found."
            }), 404

        return jsonify({
            "success": ok,
            "message": msg,
            "event": event,
            "reference": reference,
            "provider_transaction_id": provider_transaction_id,
            "changed": changed
        }), (200 if ok else 400)

    except Exception as exc:
        print("Nexus webhook error:", repr(exc))
        return jsonify({
            "success": False,
            "message": "Webhook processing failed."
        }), 500


# Backward-compatible callback endpoint. New Nexus Webhooks should use
# /api/nexus/webhook configured in the Nexus dashboard.
@app.route("/api/nexus/callback", methods=["POST"])
def nexus_callback():
    return nexus_webhook()


# Legacy deposit callback is kept as an alias for older integrations.
@app.route("/api/deposit/callback", methods=["POST"])
def nexus_deposit_callback():
    return nexus_webhook()


# ============================================================
# ADMIN PAYMENT CONFIRMATION
# ============================================================
#
# This is intentionally protected by the ADMIN role.
#
# It can be used while testing if you have independently verified
# the payment in Nexus Pay.
#
# For production, replace this manual confirmation with Nexus's
# official webhook/status verification once you have that API
# documentation.
#
# ============================================================

@app.route("/api/admin/nexus/confirm", methods=["POST"])
def admin_confirm_nexus():
    """Manual payment approval is disabled; only verified provider webhooks credit deposits."""
    return jsonify({
        "success": False,
        "message": "Manual deposit approval is disabled. Deposits are confirmed automatically by verified Nexus Pay webhooks."
    }), 410


# ============================================================
# WITHDRAWALS
# ============================================================

# ============================================================
# NEXUS WITHDRAWAL / DEPOSIT CALLBACK PROCESSING
# ============================================================

def nexus_b2c_disbursement(phone_number, amount, username, withdrawal_id=None, reference=None):
    """Send a withdrawal through the configured Nexus Pay B2C endpoint.

    The balance is reserved by api_withdraw before this function is called.
    This function only calls the provider and records its response.
    """
    phone = normalize_mpesa_phone(phone_number)
    amount = safe_float(amount)

    if amount is None or amount <= 0:
        raise ValueError("Invalid withdrawal amount.")

    if amount < MIN_WITHDRAWAL:
        raise ValueError(
            f"Minimum withdrawal is KES {MIN_WITHDRAWAL:,.0f}."
        )

    if amount > MAX_WITHDRAWAL:
        raise ValueError(
            f"Withdrawal exceeds maximum limit of KES {MAX_WITHDRAWAL:,.2f}."
        )

    if amount != round(amount):
        raise ValueError("Withdrawal amount must be a whole KES amount.")

    amount = int(round(amount))

    reference = reference or make_nexus_reference("WD", username)

    payload = {
        "phoneNumber": phone,
        "amount": amount,
        "accountReference": reference,
        "transactionDesc": "Aviator winnings payout"
    }

    response = requests.post(
        f"{NEXUS_PAY_BASE_URL}/api/payments/b2c",
        json=payload,
        headers=nexus_headers(),
        timeout=NEXUS_PAY_TIMEOUT
    )
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "Nexus Pay returned an invalid response for withdrawal."
        ) from exc

    provider_transaction_id = (
        data.get("transactionId")
        or data.get("transaction_id")
        or data.get("checkoutRequestId")
        or data.get("checkout_request_id")
        or data.get("id")
    )

    success = data.get("success")
    status_value = str(data.get("status", "")).upper()

    if success is False or status_value in {
        "FAILED", "FAILURE", "ERROR", "REJECTED"
    }:
        message = (
            data.get("message")
            or data.get("error")
            or data.get("description")
            or "Nexus Pay rejected the withdrawal request."
        )
        raise RuntimeError(str(message))

    provider_message = (
        data.get("message")
        or data.get("description")
        or "B2C payout request accepted by Nexus Pay."
    )

    # A provider may accept the request but complete the payout asynchronously.
    # The webhook is authoritative for final payout status. Even if the
    # B2C request is accepted with success=true, keep the withdrawal in
    # PROCESSING until Nexus sends payment.completed.
    withdrawal_status = "PROCESSING"
    now = datetime.now().isoformat()

    conn = get_db()
    try:
        if withdrawal_id is not None:
            conn.execute(
                """
                UPDATE withdrawals
                SET status=?, reference=?, provider_transaction_id=?,
                    provider_message=?, updated_at=?,
                    completed_at=?
                WHERE id=?
                """,
                (
                    withdrawal_status,
                    reference,
                    str(provider_transaction_id) if provider_transaction_id else None,
                    str(provider_message),
                    now,
                    None,
                    withdrawal_id
                )
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "reference": reference,
        "provider_transaction_id": provider_transaction_id,
        "status": withdrawal_status,
        "message": str(provider_message)
    }


@app.route("/api/withdraw", methods=["POST"])
def api_withdraw():
    if "username" not in session:
        return jsonify({"success": False, "error": "Unauthorized."}), 401

    data = request.get_json(silent=True) or request.form
    amount = safe_float(data.get("amount"))

    if amount is None or amount <= 0:
        return jsonify({"success": False, "error": "Invalid withdrawal amount."}), 400

    if amount < MIN_WITHDRAWAL:
        return jsonify({
            "success": False,
            "error": f"Minimum withdrawal is KES {MIN_WITHDRAWAL:,.0f}."
        }), 400

    if amount > MAX_WITHDRAWAL:
        return jsonify({
            "success": False,
            "error": f"Maximum withdrawal is KES {MAX_WITHDRAWAL:,.2f}."
        }), 400

    if amount != round(amount):
        return jsonify({
            "success": False,
            "error": "Withdrawal amount must be a whole KES amount."
        }), 400

    username = session["username"]
    user = get_user(username)
    if not user:
        return jsonify({"success": False, "error": "User not found."}), 404

    try:
        target_phone = normalize_mpesa_phone(
            data.get("phone_number") or user["phone_number"]
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    amount = int(round(amount))
    reference = make_nexus_reference("WD", username)
    now = datetime.now().isoformat()

    # Reserve the money and create a transaction record atomically.
    conn = get_db()
    withdrawal_id = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE username = ? AND balance >= ?
            """,
            (amount, username, amount)
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify({
                "success": False,
                "error": "Insufficient balance for withdrawal."
            }), 400

        cursor = conn.execute(
            """
            INSERT INTO withdrawals
            (
                username, phone_number, amount, status,
                reference, provider_message, created_at, updated_at
            )
            VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?)
            """,
            (
                username,
                target_phone,
                amount,
                reference,
                "Withdrawal request is being sent to Nexus Pay.",
                now,
                now
            )
        )
        withdrawal_id = cursor.lastrowid
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print("Withdrawal reservation error:", repr(exc))
        return jsonify({"success": False, "error": "Database error during withdrawal."}), 500
    finally:
        conn.close()

    try:
        result = nexus_b2c_disbursement(
            target_phone,
            amount,
            username,
            withdrawal_id=withdrawal_id,
            reference=reference
        )

        return jsonify({
            "success": True,
            "message": (
                f"Withdrawal of KES {amount:,.2f} has been submitted. "
                f"Status: {result['status']}."
            ),
            "withdrawal_id": withdrawal_id,
            "reference": result["reference"],
            "status": result["status"],
            "provider_transaction_id": result["provider_transaction_id"]
        }), 200

    except requests.Timeout:
        error_message = "Nexus Pay withdrawal request timed out."
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        provider_message = None
        if response is not None:
            try:
                payload = response.json()
                provider_message = (
                    payload.get("message")
                    or payload.get("error")
                    or payload.get("description")
                )
            except Exception:
                provider_message = None
        error_message = provider_message or "Nexus Pay rejected the withdrawal request."
    except requests.RequestException:
        error_message = "Could not connect to Nexus Pay for the withdrawal."
    except Exception as exc:
        print("Withdrawal provider error:", repr(exc))
        error_message = str(exc) or "Withdrawal request failed."

    # Provider failed before payout; return the reserved money to the user.
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE username = ?",
            (amount, username)
        )
        conn.execute(
            """
            UPDATE withdrawals
            SET status='FAILED', provider_message=?, updated_at=?
            WHERE id=?
            """,
            (error_message, datetime.now().isoformat(), withdrawal_id)
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print("Withdrawal refund error:", repr(exc))
        error_message = "Withdrawal failed and the automatic refund could not be completed. Check the account before retrying."
    finally:
        conn.close()

    return jsonify({
        "success": False,
        "error": error_message,
        "withdrawal_id": withdrawal_id
    }), 502


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "game_status": GAME["status"],
        "nexus_configured": bool(
            NEXUS_PAY_API_KEY
        )
    })


# ============================================================
# ADMIN DASHBOARD / DEPOSIT APPROVAL / PASSWORD RESET OTP
# ============================================================
ADMIN_HTML = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aviator Admin</title>
<style>*{box-sizing:border-box}body{margin:0;background:#0e1015;color:#edf2f7;font:14px Arial,sans-serif}header{padding:16px 4%;background:#181c24;display:flex;justify-content:space-between;align-items:center;gap:12px;position:sticky;top:0;z-index:10}.admin-head-left{display:flex;align-items:center;gap:12px}.admin-menu{display:none;background:#303846;color:#fff;border:1px solid #566174;border-radius:7px;padding:8px 12px;font-size:18px}main{padding:24px 4%;max-width:1400px;margin:auto}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.card,section{background:#181c24;border:1px solid #303846;border-radius:10px;padding:16px;margin-bottom:18px}.num{font-size:25px;color:#39d98a;font-weight:bold}h2{font-size:18px}table{width:100%;border-collapse:collapse;overflow:auto}th,td{text-align:left;padding:10px;border-bottom:1px solid #303846;vertical-align:top}button{background:#28a745;color:white;border:0;border-radius:5px;padding:8px 11px;cursor:pointer}a{color:#7db6ff}small{color:#aab4c4}.scroll{overflow:auto}.warning{color:#ffca6b}@media(max-width:600px){header{padding:10px 4%}.admin-menu{display:inline-flex}main{padding:15px 3%}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.card,section{padding:12px}.num{font-size:20px}th,td{padding:8px;font-size:12px;white-space:normal}section .scroll{max-width:100%}header.admin-collapsed .admin-brand{display:none}header.admin-collapsed{justify-content:flex-start}header.admin-collapsed .admin-head-left{flex:1}header.admin-collapsed .admin-user{display:block}header.admin-collapsed .admin-logout{display:none}header:not(.admin-expanded) .admin-nav{display:none}header.admin-expanded .admin-nav{display:flex;flex-wrap:wrap;gap:12px;width:100%;padding:10px 0}header{flex-wrap:wrap}}</style></head><body>
<header id="adminHeader" class="admin-collapsed"><div class="admin-head-left"><button class="admin-menu" type="button" onclick="toggleAdminMenu()" aria-label="Toggle admin menu">☰</button><div class="admin-brand"><b>AVIATOR · ADMIN CONSOLE</b><br><small>Signed in as {{ admin }}</small></div><small class="admin-user">@{{ admin }}</small></div><nav class="admin-nav"><a href="#round-monitor">Next round</a><a href="#signal-approvals">Signal approvals</a><a href="#signal-management">Manage signals</a><a href="#deposit-approvals">Deposit approvals</a></nav><a class="admin-logout" href="/logout">Log out</a></header><main>
<section id="round-monitor"><h2>Live round monitor · Upcoming round number</h2>
<div class="cards">
<div class="card">Current round<div class="num" id="admin-current-round">#{{ round_monitor.current_round or '—' }}</div></div>
<div class="card">Current status<div class="num" id="admin-round-status">{{ round_monitor.status }}</div></div>
<div class="card">Next round<div class="num" id="admin-next-round">#{{ round_monitor.next_round or '—' }}</div></div>
<div class="card">Betting window<div class="num"><span id="admin-betting-seconds">{{ round_monitor.betting_seconds }}</span> sec</div></div>
</div>
<p><small>Round status updates as the game engine advances. The next round number is shown without revealing its crash result or future outcome.</small></p></section>
<div class="cards"><div class="card">Registered users<div class="num">{{ stats.users }}</div></div><div class="card">Active players (last 5 min)<div class="num">{{ stats.active }}</div></div><div class="card">Verified deposits awaiting approval<div class="num">{{ stats.pending_count }}</div></div><div class="card">Total confirmed deposits<div class="num">KES {{ '%.2f'|format(stats.deposit_total) }}</div></div><div class="card">Pending deposit value<div class="num">KES {{ '%.2f'|format(stats.pending_total) }}</div></div><div class="card">Confirmed signal sales<div class="num">KES {{ '%.2f'|format(stats.signal_sales_total) }}</div></div><div class="card">Active signal subscriptions<div class="num">{{ stats.signal_active }}</div></div><div class="card">Verified signal payments awaiting approval<div class="num">{{ stats.signal_pending_approval }}</div></div></div>
<section id="deposit-approvals"><h2>Payment-verified deposits awaiting approval</h2><p class="warning">Approval credits the user's spendable balance. Pending/unverified deposits cannot be used for betting.</p><div class="scroll"><table><tr><th>Reference</th><th>User / phone</th><th>Amount</th><th>Status</th><th>Created</th><th>Action</th></tr>{% for tx in deposits %}<tr><td>{{ tx.reference }}</td><td>{{ tx.username }}<br>{{ tx.phone_number }}</td><td>KES {{ '%.2f'|format(tx.amount) }}</td><td>{{ tx.status }}</td><td>{{ tx.created_at }}</td><td>{% if tx.status == 'PAYMENT_VERIFIED' %}<form method="post" action="/admin/deposits/{{ tx.id }}/approve"><input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Approve & credit</button></form>{% else %}—{% endif %}</td></tr>{% else %}<tr><td colspan="6">No deposits awaiting approval.</td></tr>{% endfor %}</table></div></section>
<section><h2>Registered users</h2><div class="scroll"><table><tr><th>ID</th><th>Username</th><th>Phone</th><th>Role</th><th>Spendable balance</th><th>Created</th><th>Last active</th></tr>{% for u in users %}<tr><td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ u.phone_number }}</td><td>{{ u.role }}</td><td>KES {{ '%.2f'|format(u.balance) }}</td><td>{{ u.created_at }}</td><td>{{ u.last_seen_at or '—' }}</td></tr>{% endfor %}</table></div></section>
<section><h2>Recent deposit and withdrawal records</h2><div class="scroll"><table><tr><th>Type</th><th>User</th><th>Amount</th><th>Status</th><th>Reference / Provider ID</th><th>Updated</th></tr>{% for t in tx_history %}<tr><td>Deposit</td><td>{{ t.username }}</td><td>KES {{ '%.2f'|format(t.amount) }}</td><td>{{ t.status }}</td><td>{{ t.reference }}<br>{{ t.provider_transaction_id or '' }}</td><td>{{ t.updated_at }}</td></tr>{% endfor %}{% for w in withdrawals %}<tr><td>Withdrawal</td><td>{{ w.username }}</td><td>KES {{ '%.2f'|format(w.amount) }}</td><td>{{ w.status }}</td><td>{{ w.reference or '—' }}<br>{{ w.provider_transaction_id or '' }}</td><td>{{ w.updated_at }}</td></tr>{% endfor %}</table></div></section>
<section id="signal-management"><h2>Aviator signal management</h2><p class="warning">Publish manual estimates only. These are not guaranteed outcomes or certain predictions of a random crash game.</p>
<form method="post" action="/admin/signals/publish" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;align-items:end"><input type="hidden" name="csrf_token" value="{{ csrf }}"><label>Round / reference<input name="round_label" required maxlength="80" placeholder="Round 1234" style="display:block;width:100%;padding:10px;box-sizing:border-box"></label><label>Signal time<input name="signal_time" required maxlength="80" placeholder="14:35 EAT" style="display:block;width:100%;padding:10px;box-sizing:border-box"></label><label>Estimated multiplier<input name="predicted_multiplier" type="number" min="1" max="1000" step="0.01" required placeholder="1.80" style="display:block;width:100%;padding:10px;box-sizing:border-box"></label><label>Confidence label<select name="confidence" style="display:block;width:100%;padding:10px;box-sizing:border-box"><option>Unrated</option><option>Low</option><option>Medium</option><option>High</option></select></label><label>Admin note<input name="notes" maxlength="500" placeholder="Optional context" style="display:block;width:100%;padding:10px;box-sizing:border-box"></label><button type="submit">Publish signal</button></form>
<div class="scroll"><table><tr><th>Round</th><th>Time</th><th>Estimate</th><th>Label</th><th>Note</th><th>Action</th></tr>{% for sig in published_signals %}<tr><td>{{ sig.round_label }}</td><td>{{ sig.signal_time }}</td><td>{{ '%.2f'|format(sig.predicted_multiplier) }}x</td><td>{{ sig.confidence }}</td><td>{{ sig.notes or '—' }}</td><td><form method="post" action="/admin/signals/{{ sig.id }}/delete"><input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Remove</button></form></td></tr>{% else %}<tr><td colspan="6">No published signals.</td></tr>{% endfor %}</table></div></section>
<section id="signal-approvals"><h2>Aviator prediction / signal payment approvals</h2><p class="warning">Only payment-verified orders can be approved. Verify the payment reference in Nexus Pay before granting signal access. A customer never receives admin permissions.</p><div class="scroll"><table><tr><th>Player</th><th>Package</th><th>Amount</th><th>Status</th><th>Reference</th><th>Action / expiry</th></tr>{% for o in signal_orders %}<tr><td>{{ o.username }}<br>{{ o.phone_number }}</td><td>{{ o.plan_minutes }} minutes</td><td>KES {{ '%.2f'|format(o.amount) }}</td><td>{{ o.status }}</td><td>{{ o.reference }}</td><td>{% if o.status == 'PAYMENT_VERIFIED' %}<form method="post" action="/admin/signals/orders/{{ o.id }}/approve" onsubmit="return confirm('Confirm you independently verified this exact payment in Nexus Pay and want to activate signal access?')"><input type="hidden" name="csrf_token" value="{{ csrf }}"><button type="submit">Approve signal access</button></form>{% else %}{{ o.expires_at or '—' }}{% endif %}</td></tr>{% else %}<tr><td colspan="6">No signal orders yet.</td></tr>{% endfor %}</table></div></section>
<section><h2>Admin audit log</h2><div class="scroll"><table><tr><th>When</th><th>Admin</th><th>Action</th><th>Target</th><th>Details</th><th>IP</th></tr>{% for a in audits %}<tr><td>{{ a.created_at }}</td><td>{{ a.admin_username }}</td><td>{{ a.action }}</td><td>{{ a.target_username or '—' }}</td><td>{{ a.details }}</td><td>{{ a.ip_address }}</td></tr>{% endfor %}</table></div></section>
</main><script>
async function refreshRoundMonitor(){
  try {
    const response = await fetch('/admin/round-status', {credentials:'same-origin', cache:'no-store'});
    if(!response.ok) return;
    const data = await response.json();
    document.getElementById('admin-current-round').textContent = '#' + (data.current_round ?? '—');
    document.getElementById('admin-round-status').textContent = data.status;
    document.getElementById('admin-next-round').textContent = '#' + (data.next_round ?? '—');
    document.getElementById('admin-betting-seconds').textContent = data.betting_seconds;
  } catch (_) {}
}
setInterval(refreshRoundMonitor, 1000);
refreshRoundMonitor();
</script><script>function toggleAdminMenu(){const h=document.getElementById('adminHeader');h.classList.toggle('admin-expanded');h.classList.toggle('admin-collapsed');}</script></body></html>
"""


def _csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def _check_csrf():
    return secrets.compare_digest(str(request.form.get("csrf_token", "")), str(session.get("csrf_token", "")))


@app.route("/admin/round-status")
def admin_round_status():
    if not admin_required():
        return jsonify({"error": "Unauthorized"}), 401
    with GAME_LOCK:
        current_round = GAME.get("round_id")
        status = str(GAME.get("status") or "WAITING")
        seconds = BETTING_WINDOW
        if status == "BETTING" and GAME.get("betting_start") is not None:
            seconds = max(0, int(BETTING_WINDOW - (time.time() - GAME["betting_start"])))
        return jsonify({
            "current_round": current_round,
            "next_round": (int(current_round) + 1) if current_round is not None else 1,
            "status": status,
            "betting_seconds": seconds,
        })


@app.route("/admin")
def admin_dashboard():
    if not admin_required():
        return redirect("/lobby" if "username" in session else "/login")
    touch_user(session["username"])
    conn = get_db()
    try:
        stats = {
            "users": conn.execute("SELECT COUNT(*) FROM users WHERE role!='ADMIN'").fetchone()[0],
            "active": conn.execute("SELECT COUNT(*) FROM users WHERE role!='ADMIN' AND last_seen_at >= ?", ((datetime.now()-timedelta(minutes=5)).isoformat(),)).fetchone()[0],
            "pending_count": conn.execute("SELECT COUNT(*) FROM nexus_transactions WHERE status='PAYMENT_VERIFIED'").fetchone()[0],
            "pending_total": conn.execute("SELECT COALESCE(SUM(amount),0) FROM nexus_transactions WHERE status IN ('PENDING','PAYMENT_VERIFIED')").fetchone()[0],
            "deposit_total": conn.execute("SELECT COALESCE(SUM(amount),0) FROM nexus_transactions WHERE status IN ('APPROVED','SUCCESS')").fetchone()[0],
            "signal_sales_total": conn.execute("SELECT COALESCE(SUM(amount),0) FROM signal_orders WHERE status='PAID'").fetchone()[0],
            "signal_active": conn.execute("SELECT COUNT(*) FROM signal_orders WHERE status='PAID' AND expires_at> ?", (datetime.now().isoformat(),)).fetchone()[0],
            "signal_pending_approval": conn.execute("SELECT COUNT(*) FROM signal_orders WHERE status='PAYMENT_VERIFIED'").fetchone()[0],
        }
        users = conn.execute("SELECT id,username,phone_number,role,balance,created_at,last_seen_at FROM users ORDER BY created_at DESC LIMIT 500").fetchall()
        deposits = conn.execute("SELECT id,username,phone_number,amount,reference,status,created_at FROM nexus_transactions WHERE status IN ('PAYMENT_VERIFIED','PENDING') ORDER BY created_at DESC LIMIT 200").fetchall()
        tx_history = conn.execute("SELECT username,amount,reference,status,provider_transaction_id,updated_at FROM nexus_transactions ORDER BY created_at DESC LIMIT 100").fetchall()
        withdrawals = conn.execute("SELECT username,amount,status,reference,provider_transaction_id,updated_at FROM withdrawals ORDER BY created_at DESC LIMIT 100").fetchall()
        audits = conn.execute("SELECT * FROM admin_audit_logs ORDER BY id DESC LIMIT 100").fetchall()
        signal_orders = conn.execute("SELECT * FROM signal_orders ORDER BY id DESC LIMIT 100").fetchall()
        published_signals = conn.execute("SELECT * FROM aviator_signals WHERE status='PUBLISHED' ORDER BY id DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    with GAME_LOCK:
        current_round = GAME.get("round_id")
        game_status = str(GAME.get("status") or "WAITING")
        betting_seconds = BETTING_WINDOW
        if game_status == "BETTING" and GAME.get("betting_start") is not None:
            betting_seconds = max(0, int(BETTING_WINDOW - (time.time() - GAME["betting_start"])))
        round_monitor = {
            "current_round": current_round,
            "next_round": (int(current_round) + 1) if current_round is not None else 1,
            "status": game_status,
            "betting_seconds": betting_seconds,
        }
    return render_template_string(ADMIN_HTML, admin=session["username"], stats=stats, users=users, deposits=deposits, tx_history=tx_history, withdrawals=withdrawals, audits=audits, signal_orders=signal_orders, published_signals=published_signals, round_monitor=round_monitor, csrf=_csrf_token())


@app.route("/admin/deposits/<int:transaction_id>/approve", methods=["POST"])
def admin_approve_deposit(transaction_id):
    if not admin_required():
        return redirect("/login")
    if not _check_csrf():
        return "Invalid request token. Refresh the admin page and try again.", 400
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        tx = conn.execute("SELECT * FROM nexus_transactions WHERE id=?", (transaction_id,)).fetchone()
        if not tx:
            conn.rollback()
            return "Deposit not found.", 404
        if tx["status"] in ("APPROVED", "SUCCESS"):
            conn.commit()
            return redirect("/admin")
        if tx["status"] != "PAYMENT_VERIFIED":
            conn.rollback()
            return "Only payment-verified deposits can be approved.", 409
        now = datetime.now().isoformat()
        cur = conn.execute("UPDATE nexus_transactions SET status='APPROVED', approved_by=?, approved_at=?, credited_at=?, updated_at=?, provider_message=? WHERE id=? AND status='PAYMENT_VERIFIED'",
            (session["username"], now, now, now, "Payment verified and approved by administrator.", transaction_id))
        if cur.rowcount != 1:
            conn.rollback()
            return "Deposit approval conflict; refresh and retry.", 409
        cur = conn.execute("UPDATE users SET balance=balance+? WHERE username=?", (float(tx["amount"]), tx["username"]))
        if cur.rowcount != 1:
            conn.rollback()
            return "User not found; no credit applied.", 409
        conn.execute("INSERT INTO admin_audit_logs(admin_username,action,target_username,details,ip_address,created_at) VALUES(?,?,?,?,?,?)",
            (session["username"], "DEPOSIT_APPROVED", tx["username"], f"Reference={tx['reference']}; amount={float(tx['amount']):.2f}; transaction_id={transaction_id}", request.headers.get("X-Forwarded-For", request.remote_addr), now))
        conn.commit()
    finally:
        conn.close()
    return redirect("/admin")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    message = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        # Always use a generic response to avoid account enumeration.
        conn = get_db()
        try:
            user = conn.execute("SELECT username,phone_number FROM users WHERE username=? AND role!='ADMIN'", (username,)).fetchone()
            recent = conn.execute("SELECT COUNT(*) FROM password_reset_otps WHERE username=? AND created_at>=?", (username, (datetime.now()-timedelta(minutes=15)).isoformat())).fetchone()[0]
            if user and recent < 3:
                code = f"{secrets.randbelow(1000000):06d}"
                otp_hash = hashlib.sha256((code + str(app.secret_key)).encode()).hexdigest()
                now = datetime.now()
                conn.execute("INSERT INTO password_reset_otps(username,otp_hash,expires_at,created_at,request_ip) VALUES(?,?,?,?,?)",
                    (username, otp_hash, (now+timedelta(minutes=OTP_TTL_MINUTES)).isoformat(), now.isoformat(), request.remote_addr))
                conn.commit()
                try:
                    send_at_otp(user["phone_number"], code)
                except Exception as exc:
                    app.logger.error("Africa's Talking OTP send failed: %s", exc)
                    error = "Could not send SMS right now. Check SMS configuration or try later."
                else:
                    session["reset_username"] = username
                    message = "If the account exists, an OTP has been sent to its registered phone."
            else:
                message = "If the account exists, an OTP has been sent to its registered phone."
        finally:
            conn.close()
    return render_template_string(FORGOT_HTML, error=error, message=message)


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    error = None
    message = None
    username = session.get("reset_username")
    if request.method == "POST":
        code = request.form.get("otp", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not username:
            error = "Request a password reset code first."
        elif len(password) < 10:
            error = "Password must be at least 10 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif not re.fullmatch(r"\d{6}", code):
            error = "Enter the 6-digit OTP."
        else:
            conn = get_db()
            try:
                conn.execute("BEGIN IMMEDIATE")
                otp = conn.execute("SELECT * FROM password_reset_otps WHERE username=? AND used_at IS NULL ORDER BY id DESC LIMIT 1", (username,)).fetchone()
                if not otp or datetime.fromisoformat(otp["expires_at"]) < datetime.now() or otp["attempts"] >= 5:
                    error = "The code expired or is invalid. Request a new one."
                else:
                    digest = hashlib.sha256((code + str(app.secret_key)).encode()).hexdigest()
                    conn.execute("UPDATE password_reset_otps SET attempts=attempts+1 WHERE id=?", (otp["id"],))
                    if not secrets.compare_digest(digest, otp["otp_hash"]):
                        error = "The code expired or is invalid. Request a new one."
                    else:
                        now = datetime.now().isoformat()
                        conn.execute("UPDATE users SET password=? WHERE username=?", (hash_password(password), username))
                        conn.execute("UPDATE password_reset_otps SET used_at=? WHERE username=? AND used_at IS NULL", (now, username))
                        conn.commit()
                        session.pop("reset_username", None)
                        session.clear()
                        message = "Password reset successfully. You can now log in."
                if error:
                    conn.commit()
            finally:
                conn.close()
    return render_template_string(RESET_HTML, error=error, message=message)

FORGOT_HTML = r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forgot password</title><style>body{background:#0e1015;color:white;font:16px Arial;display:grid;place-items:center;min-height:100vh}.box{background:#181c24;padding:28px;border-radius:12px;width:min(340px,85vw)}input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:6px}input{background:#0e1015;color:white;border:1px solid #303846}button{background:#28a745;color:white;border:0}a{color:#7db6ff}.err{color:#ff8b8b}.ok{color:#5ee09a}</style></head><body><div class="box"><h2>Reset password</h2><p>Enter your username. We'll send a code to the registered phone if eligible.</p>{% if error %}<p class="err">{{ error }}</p>{% endif %}{% if message %}<p class="ok">{{ message }}</p><a href="/reset-password">Enter OTP and set new password</a>{% endif %}<form method="post"><label>Username</label><input name="username" required autocomplete="username"><button>Send OTP by SMS</button></form><a href="/login">Back to login</a></div></body></html>"""
RESET_HTML = r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Set new password</title><style>body{background:#0e1015;color:white;font:16px Arial;display:grid;place-items:center;min-height:100vh}.box{background:#181c24;padding:28px;border-radius:12px;width:min(340px,85vw)}input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border-radius:6px}input{background:#0e1015;color:white;border:1px solid #303846}button{background:#28a745;color:white;border:0}a{color:#7db6ff}.err{color:#ff8b8b}.ok{color:#5ee09a}</style></head><body><div class="box"><h2>Set new password</h2>{% if error %}<p class="err">{{ error }}</p>{% endif %}{% if message %}<p class="ok">{{ message }}</p><a href="/login">Go to login</a>{% else %}<form method="post"><label>6-digit SMS OTP</label><input name="otp" inputmode="numeric" pattern="[0-9]{6}" required><label>New password (minimum 10 characters)</label><input name="password" type="password" minlength="10" required><label>Confirm new password</label><input name="confirm_password" type="password" minlength="10" required><button>Reset password</button></form>{% endif %}<a href="/forgot-password">Request another code</a></div></body></html>"""

# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_HTML = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Aviator - Login</title>

<style>

body {
    margin: 0;
    min-height: 100vh;

    display: flex;
    justify-content: center;
    align-items: center;

    background: #0e1015;

    font-family: sans-serif;
    color: #fff;
}

.box {
    width: 100%;
    max-width: 360px;

    padding: 30px;

    border-radius: 12px;

    background: #181c24;

    border: 1px solid #282f3d;

    box-sizing: border-box;
}

h2 {
    text-align: center;
    color: #28a745;
    margin-top: 0;
}

input {
    width: 100%;

    padding: 12px;

    margin: 8px 0 16px;

    border-radius: 6px;

    border: 1px solid #282f3d;

    background: #0e1015;

    color: #fff;

    box-sizing: border-box;
}

.remember-row {
    display: flex;
    align-items: center;
    gap: 9px;
    margin: 2px 0 16px;
    color: #b9c0cc;
    font-size: 13px;
    line-height: 1.4;
}
.remember-row input {
    width: auto;
    margin: 0;
    accent-color: #28a745;
}

button {
    width: 100%;

    padding: 12px;

    border: none;

    border-radius: 6px;

    background: #28a745;

    color: #fff;

    font-weight: bold;

    cursor: pointer;

    font-size: 16px;
}

.error {
    color: #e53e3e;

    text-align: center;

    margin-bottom: 12px;

    font-size: 14px;
}

a {
    color: #28a745;

    text-decoration: none;
}

</style>

</head>

<body>

<div class="box">

    <h2>✈️ AVIATOR LOGIN</h2>

    {% if error %}
        <div class="error">
            {{ error }}
        </div>
    {% endif %}

    <form method="POST">

        <label>Username</label>

        <input
            type="text"
            name="username"
            required
            autocomplete="username"
        >

        <label>Password</label>

        <input
            type="password"
            name="password"
            required
            autocomplete="current-password"
        >

        <label class="remember-row">
            <input type="checkbox" name="remember" value="1" checked>
            Keep me logged in on this device (30 days)
        </label>

        <button type="submit">
            LOG IN
        </button>

    </form>
<p style="text-align:center"><a href="/forgot-password" style="color:#7db6ff">Forgot password?</a></p>

    <p
        style="
            text-align:center;
            font-size:14px;
            color:#888;
        "
    >
        No account?
        <a href="/register">
            Register
        </a>
    </p>

</div>

</body>

</html>
"""


# ============================================================
# REGISTER PAGE
# ============================================================

REGISTER_HTML = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Aviator - Register</title>

<style>

body {
    margin: 0;

    min-height: 100vh;

    display: flex;

    justify-content: center;

    align-items: center;

    background: #0e1015;

    font-family: sans-serif;

    color: #fff;
}

.box {
    width: 100%;

    max-width: 360px;

    padding: 30px;

    border-radius: 12px;

    background: #181c24;

    border: 1px solid #282f3d;

    box-sizing: border-box;
}

h2 {
    text-align: center;

    color: #28a745;

    margin-top: 0;
}

input {
    width: 100%;

    padding: 12px;

    margin: 8px 0 16px;

    border-radius: 6px;

    border: 1px solid #282f3d;

    background: #0e1015;

    color: #fff;

    box-sizing: border-box;
}

button {
    width: 100%;

    padding: 12px;

    border: none;

    border-radius: 6px;

    background: #28a745;

    color: #fff;

    font-weight: bold;

    cursor: pointer;

    font-size: 16px;
}

.error {
    color: #e53e3e;

    text-align: center;

    margin-bottom: 12px;

    font-size: 14px;
}

a {
    color: #28a745;

    text-decoration: none;
}

</style>

</head>

<body>

<div class="box">

    <h2>✈️ CREATE ACCOUNT</h2>

    {% if error %}
        <div class="error">
            {{ error }}
        </div>
    {% endif %}

    <form method="POST">

        <label>Username</label>

        <input
            type="text"
            name="username"
            required
            autocomplete="username"
        >

        <label>
            M-Pesa Phone Number
        </label>

        <input
            type="text"
            name="phone_number"
            placeholder="0712345678"
            required
        >

        <label>Password</label>

        <input
            type="password"
            name="password"
            required
            minlength="6"
            autocomplete="new-password"
        >

        <button type="submit">
            SIGN UP
        </button>

    </form>

    <p
        style="
            text-align:center;
            font-size:14px;
            color:#888;
        "
    >
        Already have an account?

        <a href="/login">
            Login
        </a>
    </p>

</div>

</body>

</html>
"""


# ============================================================
# MAIN GAME HTML
# ============================================================

HTML = r"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Aviator Game Interface</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;

    padding: 0;

    background-color: #000;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Roboto,
        sans-serif;

    color: #fff;

    user-select: none;
}

/* ==========================================================
   HEADER
   ========================================================== */

.header {
    display: flex;

    justify-content: space-between;

    align-items: center;

    background: #1b1c20;

    padding: 10px 16px;

    border-bottom: 1px solid #2a2b30;

    gap: 12px;
}

.brand {
    font-size: 20px;

    font-weight: 900;

    color: #28a745;

    letter-spacing: 1px;
}

.player-username {
    display: inline-flex;
    align-items: center;
    padding: 6px 10px;
    border: 1px solid #303846;
    border-radius: 999px;
    color: #d9e2f0;
    background: #171b23;
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
}

.wallet {
    display: flex;

    align-items: center;

    gap: 10px;

    flex-wrap: wrap;

    justify-content: flex-end;
}

.mobile-menu-toggle {
    display: none;
    border: 1px solid #3a4656;
    border-radius: 8px;
    background: #171b23;
    color: #fff;
    padding: 7px 10px;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
}

.balance {
    color: #28a745;

    font-weight: bold;

    font-size: 16px;
}

.deposit-btn,
.withdraw-btn {
    color: #fff;

    font-weight: bold;

    border: none;

    padding: 8px 16px;

    border-radius: 20px;

    cursor: pointer;

    font-size: 13px;
}

.deposit-btn {
    background: #28a745;
}

.withdraw-btn {
    background: #007bff;
}

/* ==========================================================
   ADMIN
   ========================================================== */

.admin-banner {
    display: none;

    background: #d97706;

    color: #fff;

    text-align: center;

    font-weight: bold;

    padding: 6px;

    font-size: 14px;

    border-bottom: 2px solid #b45309;
}

/* ==========================================================
   MODAL
   ========================================================== */

.mpesa-modal {
    display: none;

    position: fixed;

    inset: 0;

    z-index: 9999;

    background: rgba(0, 0, 0, .72);

    align-items: center;

    justify-content: center;
}

.mpesa-card {
    width: min(420px, 92vw);

    background: #17191f;

    border: 1px solid #30343e;

    border-radius: 16px;

    padding: 22px;

    box-shadow:
        0 20px 70px
        rgba(0, 0, 0, .5);
}

.mpesa-card h3 {
    margin: 0 0 6px;

    color: #28a745;
}

.mpesa-card p {
    color: #aaa;

    font-size: 13px;

    line-height: 1.45;
}

.mpesa-card label {
    display: block;

    color: #ddd;

    font-size: 12px;

    margin: 14px 0 6px;
}

.mpesa-card input {
    width: 100%;

    padding: 12px;

    border-radius: 8px;

    border: 1px solid #333844;

    background: #0d0f13;

    color: #fff;
}

.mpesa-actions {
    display: flex;

    gap: 10px;

    margin-top: 16px;
}

.mpesa-actions button {
    flex: 1;

    padding: 12px;

    border: 0;

    border-radius: 8px;

    cursor: pointer;

    font-weight: 700;
}

.mpesa-pay {
    background: #28a745;

    color: #fff;
}

.mpesa-cancel {
    background: #30343e;

    color: #fff;
}

.mpesa-status {
    margin-top: 12px;

    min-height: 18px;

    font-size: 12px;

    color: #bbb;
}

.mpesa-amount-warning {
    display: none;
    margin-top: 8px;
    padding: 9px 11px;
    border: 1px solid #dc2626;
    border-radius: 6px;
    background: rgba(220, 38, 38, 0.12);
    color: #ff4d4f;
    font-size: 13px;
    font-weight: 700;
}

.mpesa-amount-warning.visible {
    display: block;
}

/* ==========================================================
   MAIN
   ========================================================== */

.main-layout {
    max-width: 1200px;

    margin: 0 auto;

    padding: 10px;
}

/* ==========================================================
   HISTORY
   ========================================================== */

.history-line {
    display: flex;

    gap: 8px;

    overflow-x: auto;

    padding: 6px 0;

    margin-bottom: 8px;

    scrollbar-width: none;
}

.history-line::-webkit-scrollbar {
    display: none;
}

.hist-item {
    font-size: 13px;

    font-weight: 700;

    padding: 2px 8px;

    border-radius: 10px;

    white-space: nowrap;
}

.hist-blue {
    color: #3498db;
}

.hist-purple {
    color: #9b59b6;
}

.hist-pink {
    color: #e91e63;
}

/* ==========================================================
   GAME STAGE
   ========================================================== */

.stage {
    position: relative;

    width: 100%;

    height: 320px;

    background:
        radial-gradient(
            circle at 10% 90%,
            #20081e 0%,
            #0d060e 100%
        );

    border-radius: 12px 12px 0 0;

    overflow: hidden;

    border: 1px solid #2a2c33;
}

canvas {
    width: 100%;

    height: 100%;

    display: block;
}

.multiplier-overlay {
    position: absolute;

    top: 40%;

    left: 50%;

    transform:
        translate(-50%, -50%);

    font-size: 64px;

    font-weight: 900;

    text-align: center;

    color: #fff;

    z-index: 10;

    text-shadow:
        0 0 15px
        rgba(0, 0, 0, .8);

    white-space: pre-line;
}

.crashed-text {
    color: #e53e3e;

    text-shadow:
        0 0 10px
        rgba(229, 62, 62, .6);
}

/* ==========================================================
   CONTROLS
   ========================================================== */

.panels-container {
    display: grid;

    grid-template-columns: 1fr 1fr;

    gap: 10px;

    background: #141518;

    padding: 10px;

    border-radius: 0 0 12px 12px;

    border: 1px solid #2a2c33;

    border-top: none;
}

.bet-box {
    background: #1b1c21;

    border-radius: 10px;

    padding: 10px;

    border: 1px solid #25272e;
}

.toggle-bar {
    display: flex;

    justify-content: center;

    background: #0e0f12;

    border-radius: 15px;

    padding: 2px;

    margin-bottom: 8px;

    width: 160px;

    margin-left: auto;

    margin-right: auto;
}

.toggle-btn {
    flex: 1;

    text-align: center;

    padding: 4px 0;

    font-size: 12px;

    border-radius: 13px;

    cursor: pointer;

    color: #888;

    font-weight: bold;
}

.toggle-btn.active {
    background: #252830;

    color: #fff;
}

.auto-options {
    display: none;

    margin-bottom: 8px;

    gap: 8px;

    align-items: center;

    justify-content: center;
}

.auto-options.show {
    display: flex;
}

.auto-input {
    width: 80px;

    background: #0e1013;

    border: 1px solid #2a2c33;

    color: #fff;

    border-radius: 6px;

    padding: 4px;

    text-align: center;

    font-weight: bold;
}

.controls-flex {
    display: flex;

    gap: 10px;

    align-items: center;
}

.left-inputs {
    flex: 1;
}

.input-stepper {
    display: flex;

    align-items: center;

    background: #0e1013;

    border-radius: 20px;

    padding: 2px;

    border: 1px solid #2a2c33;
}

.step-btn {
    width: 32px;

    height: 32px;

    border-radius: 50%;

    border: none;

    background: #1b1c21;

    color: #888;

    font-size: 18px;

    cursor: pointer;

    display: flex;

    align-items: center;

    justify-content: center;
}

.step-btn:hover {
    color: #fff;
}

.amount-input {
    flex: 1;

    background: transparent;

    border: none;

    color: #fff;

    font-size: 16px;

    font-weight: bold;

    text-align: center;

    width: 100%;

    outline: none;
}

.quick-bets {
    display: grid;

    grid-template-columns: 1fr 1fr;

    gap: 4px;

    margin-top: 6px;
}

.q-btn {
    background: #121316;

    border: 1px solid #22242b;

    color: #aaa;

    border-radius: 10px;

    padding: 4px;

    font-size: 11px;

    cursor: pointer;

    text-align: center;
}

.q-btn:hover {
    color: #fff;

    border-color: #444;
}

.action-btn {
    flex: 1.1;

    height: 82px;

    border: none;

    border-radius: 12px;

    font-weight: 900;

    cursor: pointer;

    display: flex;

    flex-direction: column;

    justify-content: center;

    align-items: center;

    transition: all .2s;
}

.btn-green {
    background: #28a745;

    color: #fff;
}

.btn-green:hover {
    background: #218838;
}

.btn-orange {
    background: #d97706;

    color: #fff;
}

.btn-orange:hover {
    background: #b45309;
}

.btn-blue {
    background: #007bff;

    color: #fff;
}

.btn-disabled {
    background: #333 !important;

    color: #666 !important;

    cursor: not-allowed;
}

.btn-title {
    font-size: 18px;
}

.btn-sub {
    font-size: 16px;

    margin-top: 2px;
}

/* ==========================================================
   FEED
   ========================================================== */

.feed-section {
    margin-top: 15px;

    background: #141518;

    border-radius: 12px;

    padding: 12px;

    border: 1px solid #2a2c33;
}

.feed-header {
    font-size: 12px;

    color: #888;

    border-bottom: 1px solid #22242b;

    padding-bottom: 8px;

    margin-bottom: 8px;
}

.feed-row {
    display: flex;

    justify-content: space-between;

    gap: 10px;

    font-size: 13px;

    padding: 6px 0;

    border-bottom: 1px solid #1a1c22;
}

@media (max-width: 768px) {

    /* Keep the desktop header appearance, but make the wallet row
       horizontally scrollable on narrow screens instead of stacking. */
    .header {
        align-items: center;
        overflow: hidden;
        padding: 8px 10px;
    }

    .brand {
        flex: 0 0 auto;
        white-space: nowrap;
        font-size: 18px;
    }

    .wallet {
        flex: 1 1 auto;
        min-width: 0;
        flex-wrap: nowrap;
        justify-content: flex-start;
        overflow-x: auto;
        overflow-y: hidden;
        white-space: nowrap;
        scrollbar-width: none;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 2px;
    }

    .wallet::-webkit-scrollbar {
        display: none;
    }

    .wallet .player-username,
    .wallet .balance,
    .wallet .deposit-btn,
    .wallet .withdraw-btn,
    .wallet a {
        flex: 0 0 auto;
        white-space: nowrap;
    }

    .deposit-btn,
    .withdraw-btn {
        padding: 8px 12px;
        font-size: 12px;
    }

    .panels-container {
        grid-template-columns: 1fr;
    }

    .stage {
        height: 250px;
    }

    .multiplier-overlay {
        font-size: 42px;
    }

    .feed-row {
        font-size: 11px;
    }
}

@media (max-width: 480px) {
    .header {
        gap: 8px;
    }

    .brand {
        font-size: 16px;
    }

    .wallet {
        gap: 7px;
    }

    .balance {
        font-size: 14px;
    }

    .player-username {
        font-size: 11px;
        padding: 5px 8px;
    }

    .deposit-btn,
    .withdraw-btn {
        padding: 7px 10px;
        font-size: 11px;
    }

    .wallet a {
        font-size: 11px !important;
    }
}


/* Compact phone header: username and balance stay visible while the
   hamburger hides/reveals the rest of the top-bar actions. */
@media (max-width: 600px) {
    .header { display:flex; flex-wrap:wrap; gap:8px; padding:8px 10px; }
    .mobile-menu-toggle { display:inline-flex; align-items:center; justify-content:center; order:0; }
    .brand { display:none; }
    .wallet { order:1; flex:1 1 auto; display:flex; justify-content:flex-end; gap:7px; overflow:visible; }
    .wallet .player-username, .wallet .balance { display:inline-flex; flex:0 0 auto; }
    .wallet .topbar-action { display:none; }
    .header.menu-open .brand { display:block; order:2; flex:1 0 100%; font-size:15px; }
    .header.menu-open .wallet { order:3; flex:1 0 100%; justify-content:flex-start; flex-wrap:wrap; }
    .header.menu-open .wallet .topbar-action { display:inline-flex; }
}
</style>

</head>

<body>

<div
    class="admin-banner"
    id="adminBanner"
>
    ⚡ ADMIN CONTROLS:

    NEXT ROUND:
    <span id="next1">-</span>

    |

    ROUND AFTER:
    <span id="next2">-</span>
</div>


<div class="header" id="gameHeader">

    <button type="button" class="mobile-menu-toggle" id="mobileMenuToggle" aria-label="Toggle game menu" aria-expanded="false" onclick="toggleMobileGameMenu()">☰</button>

    <div class="brand">
        ✈️ AVIATOR
    </div>

    <div class="wallet">

        <a class="topbar-action" href="/lobby" style="color:#7db6ff;text-decoration:none;font-size:12px">GAMES</a>
        <a class="topbar-action" href="/signals" style="color:#ffca6b;text-decoration:none;font-size:12px">SIGNALS</a>
        <span class="player-username" title="Signed-in account">@{{ username }}</span>

        <span
            class="balance"
            id="balanceDisplay"
        >
            0.00 KES
        </span>

        <button
            class="deposit-btn topbar-action"
            onclick="openDepositGateway()"
        >
            DEPOSIT
        </button>

        <button
            class="withdraw-btn topbar-action"
            onclick="triggerWithdrawal()"
        >
            WITHDRAW
        </button>

        <a
            class="topbar-action"
            href="/logout"
            style="
                color:#e53e3e;
                text-decoration:none;
                font-size:12px;
            "
        >
            Logout
        </a>

    </div>

</div>
<script>
function toggleMobileGameMenu(){
  const header=document.getElementById('gameHeader');
  const toggle=document.getElementById('mobileMenuToggle');
  if(!header||!toggle)return;
  const open=header.classList.toggle('menu-open');
  toggle.setAttribute('aria-expanded',open?'true':'false');
  toggle.textContent=open?'×':'☰';
}
</script>

<!-- ========================================================
     NEXUS DEPOSIT MODAL
     ======================================================== -->

<div
    class="mpesa-modal"
    id="mpesaModal"
>

    <div class="mpesa-card">

        <h3>
            Deposit with M-Pesa
        </h3>

        <p>
            Enter your amount and M-Pesa number.
            Nexus Pay will send an M-Pesa payment
            prompt to your phone.
        </p>

        <label for="mpesaAmount">
            Amount (KES)
        </label>

        <input
            id="mpesaAmount"
            type="number"
            min="200"
            step="10"
            value="200"
            required
            oninput="validateDepositAmount()"
        >

        <div id="mpesaAmountWarning" class="mpesa-amount-warning" role="alert" aria-live="polite">
            ⚠ Minimum deposit is KES 200. Please enter KES 200 or more.
        </div>

        <label for="mpesaPhone">
            M-Pesa phone number
        </label>

        <input
            id="mpesaPhone"
            type="tel"
            placeholder="0712345678"
        >

        <div
            class="mpesa-status"
            id="mpesaStatus"
        ></div>

        <div class="mpesa-actions">

            <button
                class="mpesa-cancel"
                onclick="closeMpesaModal()"
            >
                CANCEL
            </button>

            <button
                class="mpesa-pay"
                id="mpesaPayBtn"
                onclick="requestNexusDeposit()"
            >
                PAY
            </button>

        </div>

    </div>

</div>


<div class="main-layout">

    <!-- HISTORY -->

    <div
        class="history-line"
        id="historyLine"
    ></div>


    <!-- GAME -->

    <div class="stage">

        <canvas
            id="flightCanvas"
        ></canvas>

        <div
            class="multiplier-overlay"
            id="multiplierDisplay"
        >
            1.00x
        </div>

    </div>


    <!-- CONTROLS -->

    <div class="panels-container">

        <!-- PANEL 1 -->

        <div class="bet-box">

            <div class="toggle-bar">

                <div
                    class="toggle-btn active"
                    id="tabBet1"
                    onclick="switchTab(1, 'bet')"
                >
                    Bet
                </div>

                <div
                    class="toggle-btn"
                    id="tabAuto1"
                    onclick="switchTab(1, 'auto')"
                >
                    Auto
                </div>

            </div>


            <div
                class="auto-options"
                id="autoOpt1"
            >

                <label
                    style="
                        font-size:11px;
                        color:#aaa;
                    "
                >
                    Auto Cashout x
                </label>

                <input
                    type="number"
                    id="autoCashout1"
                    class="auto-input"
                    value="2.00"
                    step="0.1"
                    min="1.01"
                >

            </div>


            <div class="controls-flex">

                <div class="left-inputs">

                    <div class="input-stepper">

                        <button
                            class="step-btn"
                            onclick="adjustBet(1, -10)"
                        >
                            -
                        </button>

                        <input
                            type="number"
                            id="amount1"
                            class="amount-input"
                            value="20.00"
                            min="20"
                            step="5"
                        >

                        <button
                            class="step-btn"
                            onclick="adjustBet(1, 10)"
                        >
                            +
                        </button>

                    </div>


                    <div class="quick-bets">

                        <div
                            class="q-btn"
                            onclick="setBet(1, 100)"
                        >
                            100
                        </div>

                        <div
                            class="q-btn"
                            onclick="setBet(1, 200)"
                        >
                            200
                        </div>

                        <div
                            class="q-btn"
                            onclick="setBet(1, 500)"
                        >
                            500
                        </div>

                        <div
                            class="q-btn"
                            onclick="setBet(1, 10000)"
                        >
                            10,000
                        </div>

                    </div>

                </div>


                <button
                    class="action-btn btn-green"
                    id="btn1"
                    onclick="handleAction(1)"
                >

                    <span
                        class="btn-title"
                        id="btn1Title"
                    >
                        Bet
                    </span>

                    <span
                        class="btn-sub"
                        id="btn1Sub"
                    >
                        20.00 KES
                    </span>

                </button>

            </div>

        </div>


        <!-- PANEL 2 -->

        <div class="bet-box">

            <div class="toggle-bar">

                <div
                    class="toggle-btn active"
                    id="tabBet2"
                    onclick="switchTab(2, 'bet')"
                >
                    Bet
                </div>

                <div
                    class="toggle-btn"
                    id="tabAuto2"
                    onclick="switchTab(2, 'auto')"
                >
                    Auto
                </div>

            </div>


            <div
                class="auto-options"
                id="autoOpt2"
            >

                <label
                    style="
                        font-size:11px;
                        color:#aaa;
                    "
                >
                    Auto Cashout x
                </label>

                <input
                    type="number"
                    id="autoCashout2"
                    class="auto-input"
                    value="2.00"
                    step="0.1"
                    min="1.01"
                >

            </div>


            <div class="controls-flex">

                <div class="left-inputs">

                    <div class="input-stepper">

                        <button
                            class="step-btn"
                            onclick="adjustBet(2, -10)"
                        >
                            -
                        </button>

                        <input
                            type="number"
                            id="amount2"
                            class="amount-input"
                            value="20.00"
                            min="20"
                            step="5"
                        >

                        <button
                            class="step-btn"
                            onclick="adjustBet(2, 10)"
                        >
                            +
                        </button>

                    </div>


                    <div class="quick-bets">

                        <div
                            class="q-btn"
                            onclick="setBet(2, 100)"
                        >
                            100
                        </div>

                        <div
                            class="q-btn"
                            onclick="setBet(2, 200)"
                        >
                            200
                        </div>

                        <div
                            class="q-btn"
                            onclick="setBet(2, 500)"
                        >
                            500
                        </div>

                        <div
                            class="q-btn"
                            onclick="setBet(2, 10000)"
                        >
                            10,000
                        </div>

                    </div>

                </div>


                <button
                    class="action-btn btn-green"
                    id="btn2"
                    onclick="handleAction(2)"
                >

                    <span
                        class="btn-title"
                        id="btn2Title"
                    >
                        Bet
                    </span>

                    <span
                        class="btn-sub"
                        id="btn2Sub"
                    >
                        20.00 KES
                    </span>

                </button>

            </div>

        </div>

    </div>


    <!-- FEED -->

    <div class="feed-section">

        <div class="feed-header">

            ALL BETS
            (<span id="totalBetsCount">0</span>)

        </div>

        <div id="liveBetsList"></div>

    </div>

</div>


<script>

let currentStatus = "BETTING";

let currentMult = 1.00;

let userBets = {};

let currentRoundId = null;

let lastAutoPlacedRound = {
    1: null,
    2: null
};

let autoBetEnabled = {
    1: false,
    2: false
};

let activeTab = {
    1: "bet",
    2: "bet"
};


/* ==========================================================
   CANVAS
   ========================================================== */

const canvas = document.getElementById(
    "flightCanvas"
);

const ctx = canvas.getContext(
    "2d"
);


function resizeCanvas() {

    canvas.width =
        canvas.parentElement.clientWidth;

    canvas.height =
        canvas.parentElement.clientHeight;
}


window.addEventListener(
    "resize",
    resizeCanvas
);

resizeCanvas();


function drawScene() {

    ctx.clearRect(
        0,
        0,
        canvas.width,
        canvas.height
    );


    /* Grid */

    ctx.strokeStyle =
        "rgba(255,255,255,0.03)";

    ctx.lineWidth = 1;


    for (
        let x = 0;
        x < canvas.width;
        x += 40
    ) {

        ctx.beginPath();

        ctx.moveTo(x, 0);

        ctx.lineTo(
            x,
            canvas.height
        );

        ctx.stroke();
    }


    for (
        let y = 0;
        y < canvas.height;
        y += 40
    ) {

        ctx.beginPath();

        ctx.moveTo(0, y);

        ctx.lineTo(
            canvas.width,
            y
        );

        ctx.stroke();
    }


    if (
        currentStatus === "RUNNING"
        ||
        currentStatus === "CRASHED"
    ) {

        // Logarithmic progress keeps the plane moving across the canvas
        // during long rounds instead of freezing visually at 6x.
        const progress =
            Math.max(0, Math.min(
                Math.log(Math.max(currentMult, 1)) / Math.log(150),
                1.0
            ));


        const startX = 0;

        const startY =
            canvas.height;


        const endX =
            canvas.width
            * 0.75
            * Math.min(
                progress + 0.1,
                1.0
            );


        const endY =
            canvas.height
            -
            (
                canvas.height
                * 0.65
                * Math.min(
                    progress + 0.1,
                    1.0
                )
            );


        /* Area */

        ctx.beginPath();

        ctx.moveTo(
            startX,
            startY
        );

        ctx.quadraticCurveTo(
            endX * 0.5,
            canvas.height,
            endX,
            endY
        );

        ctx.lineTo(
            endX,
            canvas.height
        );

        ctx.closePath();


        const grad =
            ctx.createLinearGradient(
                0,
                0,
                0,
                canvas.height
            );

        grad.addColorStop(
            0,
            "rgba(229,62,62,0.5)"
        );

        grad.addColorStop(
            1,
            "rgba(229,62,62,0)"
        );

        ctx.fillStyle = grad;

        ctx.fill();


        /* Line */

        ctx.beginPath();

        ctx.moveTo(
            startX,
            startY
        );

        ctx.quadraticCurveTo(
            endX * 0.5,
            canvas.height,
            endX,
            endY
        );

        ctx.strokeStyle =
            "#e53e3e";

        ctx.lineWidth = 4;

        ctx.stroke();


        /* Aircraft point */

        if (
            currentStatus === "RUNNING"
        ) {

            ctx.save();

            ctx.translate(
                endX,
                endY
            );

            ctx.fillStyle =
                "#e53e3e";

            ctx.beginPath();

            ctx.arc(
                0,
                0,
                8,
                0,
                Math.PI * 2
            );

            ctx.fill();

            ctx.restore();
        }
    }


    requestAnimationFrame(
        drawScene
    );
}


requestAnimationFrame(
    drawScene
);


/* ==========================================================
   TABS
   ========================================================== */

function switchTab(
    num,
    tab
) {

    activeTab[num] = tab;


    document.getElementById(
        "tabBet" + num
    ).className =
        "toggle-btn"
        +
        (
            tab === "bet"
                ? " active"
                : ""
        );


    document.getElementById(
        "tabAuto" + num
    ).className =
        "toggle-btn"
        +
        (
            tab === "auto"
                ? " active"
                : ""
        );


    const autoOpt =
        document.getElementById(
            "autoOpt" + num
        );


    if (tab === "auto") {
        autoOpt.classList.add(
            "show"
        );
    } else {
        autoOpt.classList.remove(
            "show"
        );
    }


    updateButtonUI(num);
}


/* ==========================================================
   STATE
   ========================================================== */

async function syncState() {

    try {

        const res =
            await fetch(
                "/api/state",
                {
                    cache: "no-store"
                }
            );


        if (!res.ok) {
            return;
        }


        const data =
            await res.json();


        document.getElementById(
            "balanceDisplay"
        ).innerText =
            Number(data.balance)
                .toFixed(2)
            + " KES";

        currentStatus =
            data.status;


        currentMult =
            Number(data.multiplier);


        userBets =
            data.bets || {};


        currentRoundId =
            data.round_id;


        /* Admin telemetry */

        if (data.is_admin) {

            document.getElementById(
                "adminBanner"
            ).style.display =
                "block";


            document.getElementById(
                "next1"
            ).innerText =
                data.next_crash_point_1
                    ? Number(
                        data.next_crash_point_1
                    ).toFixed(2) + "x"
                    : "-";


            document.getElementById(
                "next2"
            ).innerText =
                data.next_crash_point_2
                    ? Number(
                        data.next_crash_point_2
                    ).toFixed(2) + "x"
                    : "-";

        } else {

            document.getElementById(
                "adminBanner"
            ).style.display =
                "none";
        }


        /* Multiplier */

        const multDisplay =
            document.getElementById(
                "multiplierDisplay"
            );


        if (
            data.status === "BETTING"
        ) {

            multDisplay.className =
                "multiplier-overlay";

            multDisplay.innerText =
                "WAITING FOR NEXT ROUND";


            checkAndRunAutoBet(1);

            checkAndRunAutoBet(2);

        }

        else if (
            data.status === "RUNNING"
        ) {

            multDisplay.className =
                "multiplier-overlay";

            multDisplay.innerText =
                Number(
                    data.multiplier
                ).toFixed(2)
                + "x";

        }

        else if (
            data.status === "CRASHED"
        ) {

            multDisplay.className =
                "multiplier-overlay crashed-text";

            multDisplay.innerText =
                "FLEW AWAY!\n"
                +
                (
                    data.crash_point
                        ? Number(
                            data.crash_point
                        ).toFixed(2)
                        : Number(
                            data.multiplier
                        ).toFixed(2)
                )
                +
                "x";
        }


        /* History */

        const histLine =
            document.getElementById(
                "historyLine"
            );


        histLine.innerHTML =
            (data.history || [])
                .map(
                    function(val) {

                        let cls =
                            "hist-blue";

                        if (
                            val >= 10
                        ) {

                            cls =
                                "hist-pink";

                        } else if (
                            val >= 2
                        ) {

                            cls =
                                "hist-purple";
                        }


                        return `
                            <div
                                class="hist-item ${cls}"
                            >
                                ${Number(val).toFixed(2)}x
                            </div>
                        `;
                    }
                )
                .join("");


        updateButtonUI(1);

        updateButtonUI(2);


        /* Feed */

        const feedData =
            data.live_feed || [];


        document.getElementById(
            "totalBetsCount"
        ).innerText =
            feedData.length;


        const feed =
            document.getElementById(
                "liveBetsList"
            );


        feed.innerHTML =
            feedData
                .map(
                    function(b) {

                        let statusText =
                            `
                            <span
                                style="color:#888;"
                            >
                                IN PLAY
                            </span>
                            `;


                        if (
                            b.status === "WON"
                        ) {

                            const cashout =
                                Number(
                                    b.cashout_multiplier
                                    || 0
                                ).toFixed(2);


                            const winnings =
                                Number(
                                    b.winnings
                                    || 0
                                ).toFixed(2);


                            statusText =
                                `
                                <span
                                    style="
                                        color:#28a745;
                                        font-weight:bold;
                                    "
                                >
                                    ${cashout}x
                                    (+${winnings})
                                </span>
                                `;

                        }

                        else if (
                            b.status === "LOST"
                        ) {

                            statusText =
                                `
                                <span
                                    style="
                                        color:#e53e3e;
                                    "
                                >
                                    CRASHED
                                </span>
                                `;
                        }


                        return `
                            <div class="feed-row">

                                <div>
                                    <b>
                                        ${escapeHtml(
                                            b.username
                                        )}
                                    </b>
                                </div>

                                <div>
                                    ${Number(
                                        b.amount
                                    ).toFixed(2)}
                                    KES
                                </div>

                                <div>
                                    ${statusText}
                                </div>

                            </div>
                        `;
                    }
                )
                .join("");


    } catch (error) {

        console.error(
            "State sync error:",
            error
        );
    }
}


/* ==========================================================
   ESCAPE HTML
   ========================================================== */

function escapeHtml(value) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        String(value ?? "");

    return div.innerHTML;
}


/* ==========================================================
   AUTO BET
   ========================================================== */

async function checkAndRunAutoBet(
    num
) {

    if (
        !autoBetEnabled[num]
        ||
        currentStatus !== "BETTING"
    ) {
        return;
    }


    if (
        lastAutoPlacedRound[num]
        === currentRoundId
    ) {
        return;
    }


    const bet =
        userBets[num];


    if (
        bet
        &&
        bet.status === "ACTIVE"
    ) {

        lastAutoPlacedRound[num] =
            currentRoundId;

        return;
    }


    const amount =
        document.getElementById(
            "amount" + num
        ).value;


    const autoCash =
        document.getElementById(
            "autoCashout" + num
        ).value;


    try {

        const res =
            await fetch(
                "/api/bet",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        bet_number: num,
                        amount: amount,
                        auto_cashout:
                            autoCash
                    })
                }
            );


        const data =
            await res.json();


        if (data.success) {

            lastAutoPlacedRound[num] =
                currentRoundId;

        }

    } catch (error) {

        console.error(
            "Auto bet error:",
            error
        );
    }
}


/* ==========================================================
   BUTTON UI
   ========================================================== */

function updateButtonUI(
    num
) {

    const btn =
        document.getElementById(
            "btn" + num
        );


    const title =
        document.getElementById(
            "btn" + num + "Title"
        );


    const sub =
        document.getElementById(
            "btn" + num + "Sub"
        );


    const inputVal =
        parseFloat(
            document.getElementById(
                "amount" + num
            ).value
        )
        || 20;


    const bet =
        userBets[num];


    if (
        currentStatus === "RUNNING"
    ) {

        if (
            bet
            &&
            bet.status === "ACTIVE"
        ) {

            const currentPayout =
                (
                    Number(bet.amount)
                    * currentMult
                ).toFixed(2);


            btn.className =
                "action-btn btn-orange";


            title.innerText =
                "CASH OUT";


            sub.innerText =
                currentPayout
                + " KES";


            btn.disabled = false;

        } else {

            btn.className =
                "action-btn btn-disabled";

            title.innerText =
                "Bet";

            sub.innerText =
                inputVal.toFixed(2)
                + " KES";

            btn.disabled = true;
        }

    }

    else if (
        currentStatus === "BETTING"
    ) {

        if (
            activeTab[num] === "auto"
        ) {

            if (
                autoBetEnabled[num]
            ) {

                btn.className =
                    "action-btn btn-blue";

                title.innerText =
                    "AUTO ACTIVE";

                sub.innerText =
                    "CANCEL";

                btn.disabled = false;

            } else {

                btn.className =
                    "action-btn btn-green";

                title.innerText =
                    "AUTO BET";

                sub.innerText =
                    inputVal.toFixed(2)
                    + " KES";

                btn.disabled = false;
            }

        } else {

            if (
                bet
                &&
                bet.status === "ACTIVE"
            ) {

                btn.className =
                    "action-btn btn-disabled";

                title.innerText =
                    "WAITING";

                sub.innerText =
                    "BET PLACED";

                btn.disabled = true;

            } else {

                btn.className =
                    "action-btn btn-green";

                title.innerText =
                    "Bet";

                sub.innerText =
                    inputVal.toFixed(2)
                    + " KES";

                btn.disabled = false;
            }
        }

    }

    else {

        btn.className =
            "action-btn btn-disabled";

        btn.disabled = true;
    }
}


/* ==========================================================
   AMOUNT CONTROLS
   ========================================================== */

function adjustBet(
    num,
    delta
) {

    const input =
        document.getElementById(
            "amount" + num
        );


    let val =
        (
            parseFloat(
                input.value
            )
            || 0
        )
        + delta;


    if (val < 20) {
        val = 20;
    }


    input.value =
        val.toFixed(2);


    updateButtonUI(num);
}


function setBet(
    num,
    val
) {

    document.getElementById(
        "amount" + num
    ).value =
        Number(val).toFixed(2);


    updateButtonUI(num);
}


/* ==========================================================
   BET / CASHOUT ACTION
   ========================================================== */

async function handleAction(
    num
) {

    const bet =
        userBets[num];


    if (
        currentStatus === "RUNNING"
        &&
        bet
        &&
        bet.status === "ACTIVE"
    ) {

        try {

            const res =
                await fetch(
                    "/api/cashout",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            bet_number: num
                        })
                    }
                );


            const data =
                await res.json();


            if (!data.success) {
                alert(
                    data.message
                );
            }

        } catch (error) {

            alert(
                "Cashout request failed."
            );
        }

    }

    else if (
        currentStatus === "BETTING"
    ) {

        if (
            activeTab[num] === "auto"
        ) {

            autoBetEnabled[num] =
                !autoBetEnabled[num];


            if (
                autoBetEnabled[num]
            ) {

                await checkAndRunAutoBet(
                    num
                );
            }

        } else {

            const amount =
                document.getElementById(
                    "amount" + num
                ).value;


            try {

                const res =
                    await fetch(
                        "/api/bet",
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    bet_number:
                                        num,

                                    amount:
                                        amount
                                })
                        }
                    );


                const data =
                    await res.json();


                if (!data.success) {

                    alert(
                        data.message
                    );
                }

            } catch (error) {

                alert(
                    "Bet request failed."
                );
            }
        }
    }


    await syncState();
}


/* ==========================================================
   NEXUS DEPOSIT
   ========================================================== */

function openDepositGateway() {

    const modal =
        document.getElementById(
            "mpesaModal"
        );


    const status =
        document.getElementById(
            "mpesaStatus"
        );


    const phoneInput =
        document.getElementById(
            "mpesaPhone"
        );


    modal.style.display =
        "flex";


    status.textContent = "";


    /*
     * We deliberately do not expose the user's phone
     * from the server into the HTML.
     *
     * They can enter the number here.
     */

    phoneInput.focus();
}


function closeMpesaModal() {

    document.getElementById(
        "mpesaModal"
    ).style.display =
        "none";
}


function validateDepositAmount() {
    const amountInput = document.getElementById("mpesaAmount");
    const warning = document.getElementById("mpesaAmountWarning");
    const payButton = document.getElementById("mpesaPayBtn");
    const rawValue = amountInput.value.trim();
    const amount = Number(rawValue);
    const isBelowMinimum = rawValue !== "" && (!Number.isFinite(amount) || amount < 200);

    warning.classList.toggle("visible", isBelowMinimum);
    amountInput.setCustomValidity(
        isBelowMinimum ? "Minimum deposit is KES 200." : ""
    );

    if (payButton) {
        payButton.disabled = isBelowMinimum;
        payButton.style.opacity = isBelowMinimum ? "0.6" : "1";
        payButton.style.cursor = isBelowMinimum ? "not-allowed" : "pointer";
    }

    return !isBelowMinimum;
}


async function requestNexusDeposit() {

    if (!validateDepositAmount()) {
        return;
    }

    const amount =
        parseFloat(
            document.getElementById(
                "mpesaAmount"
            ).value
        );


    const phone =
        document.getElementById(
            "mpesaPhone"
        ).value.trim();


    const status =
        document.getElementById(
            "mpesaStatus"
        );


    const btn =
        document.getElementById(
            "mpesaPayBtn"
        );


    if (!Number.isFinite(amount)) {
        status.textContent = "Enter a valid deposit amount.";
        alert("Minimum deposit is KES 5.");
        return;
    }

    if (amount < 200) {
        status.textContent = "Minimum deposit is KES 200. Please enter KES 200 or more.";
        alert("Deposit not allowed: the minimum deposit is KES 200.");
        return;
    }


    if (
        !Number.isInteger(amount)
    ) {

        status.textContent =
            "Enter a whole KES amount.";

        return;
    }


    if (!phone) {

        status.textContent =
            "Enter your M-Pesa phone number.";

        return;
    }


    btn.disabled = true;


    status.textContent =
        "Sending M-Pesa prompt...";


    try {

        const res =
            await fetch(
                "/api/nexus/stkpush",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        amount: amount,
                        phone: phone
                    })
                }
            );


        const data =
            await res.json();


        if (!data.success) {

            status.textContent =
                data.message
                ||
                "Unable to start payment.";

            btn.disabled = false;

            return;
        }


        status.textContent =
            "M-Pesa prompt sent. "
            +
            "Enter your PIN on your phone. "
            +
            "Your balance will update only "
            +
            "after the payment is confirmed.";


        /* Wait for the signed Nexus Pay webhook to update the local
         * transaction. The polling endpoint only reads local verified status;
         * it never credits a wallet based on browser-submitted data. */

        setTimeout(
            function() {
                pollNexusStatus(
                    data.reference
                );
            },
            3000
        );


    } catch (error) {

        console.error(
            "Nexus payment error:",
            error
        );


        status.textContent =
            "Payment request failed. "
            +
            "Please try again.";

    } finally {

        btn.disabled = false;
    }
}


/* ==========================================================
   NEXUS STATUS
   ========================================================== */

async function pollNexusStatus(
    reference
) {

    for (
        let i = 0;
        i < 100;
        i++
    ) {

        await new Promise(
            function(resolve) {
                setTimeout(
                    resolve,
                    3000
                );
            }
        );


        try {

            const res =
                await fetch(
                    "/api/nexus/status/"
                    +
                    encodeURIComponent(
                        reference
                    )
                );


            const data =
                await res.json();


            if (!data.success) {
                return;
            }


            if (
                data.status === "SUCCESS"
            ) {

                document.getElementById(
                    "mpesaStatus"
                ).textContent =
                    "Deposit confirmed. KES "
                    +
                    Number(
                        data.amount
                    ).toFixed(2)
                    +
                    " has been added.";


                await syncState();


                setTimeout(
                    closeMpesaModal,
                    1800
                );

                return;
            }


            if (
                data.status === "FAILED"
            ) {

                document.getElementById(
                    "mpesaStatus"
                ).textContent =
                    data.message
                    ||
                    "M-Pesa payment was not completed.";

                return;
            }

        } catch (error) {

            console.error(
                "Nexus status error:",
                error
            );

            return;
        }
    }


    document.getElementById(
        "mpesaStatus"
    ).textContent =
        "Payment is pending verification. Once Nexus Pay verifies it, it will appear as pending until an administrator approves it. It cannot be used for betting before approval.";
}


/* ==========================================================
   WITHDRAWAL
   ========================================================== */

async function triggerWithdrawal() {

    const currentText =
        document.getElementById("balanceDisplay").textContent || "";

    const val = prompt(
        "Enter amount to withdraw (KES). Minimum: 1000 KES.\nAvailable: " + currentText
    );

    if (val === null) {
        return;
    }

    const amount = parseFloat(String(val).replace(/,/g, "").trim());

    if (!Number.isFinite(amount) || amount <= 0) {
        alert("Enter a valid withdrawal amount.");
        return;
    }

    if (amount < 1) {
        alert("Minimum withdrawal is KES 200. Please enter KES 200 or more.");
        return;
    }

    if (!Number.isInteger(amount)) {
        alert("Withdrawal amount must be a whole KES amount.");
        return;
    }

    const phoneInput = prompt(
        "M-Pesa number (Cancel = use your registered number):"
    );

    const phone = phoneInput === null ? "" : phoneInput.trim();

    try {
        const res = await fetch("/api/withdraw", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                amount: amount,
                phone_number: phone.trim()
            })
        });

        let data;
        try {
            data = await res.json();
        } catch (e) {
            data = {
                success: false,
                error: "Invalid server response."
            };
        }

        const message = data.message || data.error ||
            (data.success ? "Withdrawal submitted." : "Withdrawal failed.");

        alert(message);
        await syncState();

    } catch (error) {
        console.error("Withdrawal error:", error);
        alert("Withdrawal request failed. Please try again.");
    }
}


/* ==========================================================
   START
   ========================================================== */

setInterval(
    syncState,
    200
);

syncState();

</script>

</body>

</html>
"""


# ============================================================
# STARTUP
# ============================================================

def print_configuration_status():
    print("\n=== Aviator configuration ===")
    print("Database:", DB_NAME)
    print("Nexus base URL:", NEXUS_PAY_BASE_URL)
    print("Nexus API key configured:", bool(NEXUS_PAY_API_KEY))
    print("Nexus public key configured:", bool(NEXUS_PAY_PUBLIC_KEY))
    print("Nexus secret key configured:", bool(NEXUS_PAY_SECRET_KEY))
    print("Nexus timeout:", NEXUS_PAY_TIMEOUT)
    print("Nexus webhook path:", NEXUS_WEBHOOK_PATH)
    print("Nexus webhook URL:", NEXUS_WEBHOOK_URL or "Set NEXUS_WEBHOOK_URL in .env")
    print("Webhook signing secret configured:", bool(NEXUS_WEBHOOK_SECRET))
    print("================================\n")


def start_application():

    # Database must exist before the game thread starts.
    init_db()

    # Create the first game round.
    initialize_game()

    # Start game engine once.
    thread = threading.Thread(
        target=game_loop,
        daemon=True,
        name="game-engine"
    )

    thread.start()


# ============================================================
# RUN
# ============================================================
init_db()
print_configuration_status()

if __name__ == "__main__":

    start_application()

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                "5000"
            )
        ),
        debug=(
            os.environ.get(
                "FLASK_DEBUG",
                "0"
            ) == "1"
        ),
        use_reloader=False
    )
