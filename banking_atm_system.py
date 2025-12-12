import json
import os
import datetime
from typing import Dict, Any, Optional

DATA_FILE = "accounts_data.json"


# ---------------------- DATA HANDLING ---------------------- #

def load_accounts() -> Dict[str, Dict[str, Any]]:
    """Load account data from JSON file or create default accounts if file missing."""
    if not os.path.exists(DATA_FILE):
        accounts = create_default_accounts()
        save_accounts(accounts)
        return accounts

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure keys are strings
            return {str(k): v for k, v in data.items()}
    except (json.JSONDecodeError, FileNotFoundError):
        accounts = create_default_accounts()
        save_accounts(accounts)
        return accounts


def save_accounts(accounts: Dict[str, Dict[str, Any]]) -> None:
    """Save account data to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=4, ensure_ascii=False)


def create_default_accounts() -> Dict[str, Dict[str, Any]]:
    """Create some sample accounts for first run."""
    today = datetime.date.today().isoformat()
    return {
        "1001": {
            "name": "Rahul Sharma",
            "pin": "1234",
            "balance": 15000.0,
            "type": "savings",  # savings / current
            "transactions": [],
            "failed_attempts": 0,
            "locked": False,
            "daily_limit": 20000.0,
            "withdrawn_today": 0.0,
            "last_withdraw_date": today,
            "interest_rate": 0.04,  # 4% yearly (for savings)
            "last_interest_date": today,
        },
        "1002": {
            "name": "Priya Verma",
            "pin": "4321",
            "balance": 8000.0,
            "type": "current",
            "transactions": [],
            "failed_attempts": 0,
            "locked": False,
            "daily_limit": 30000.0,
            "withdrawn_today": 0.0,
            "last_withdraw_date": today,
            "interest_rate": 0.0,
            "last_interest_date": today,
        },
    }


# ---------------------- UTILITY FUNCTIONS ---------------------- #

def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.date.today().isoformat()


def log_transaction(account: Dict[str, Any], t_type: str, amount: float,
                    balance_after: float, note: str = "") -> None:
    """Append a transaction to account history."""
    account["transactions"].append({
        "time": now_str(),
        "type": t_type,  # deposit / withdraw / transfer_out / transfer_in / interest
        "amount": amount,
        "balance_after": balance_after,
        "note": note
    })
    # Keep only last 20 transactions for safety
    if len(account["transactions"]) > 50:
        account["transactions"] = account["transactions"][-50:]


def reset_daily_withdraw_if_new_day(account: Dict[str, Any]) -> None:
    """Reset withdrawn_today if date changed."""
    today = today_str()
    if account.get("last_withdraw_date") != today:
        account["withdrawn_today"] = 0.0
        account["last_withdraw_date"] = today


# ---------------------- AUTHENTICATION ---------------------- #

def authenticate(accounts: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Handle login with account number and PIN, with lockout on failures."""
    acc_no = input("Enter Account Number: ").strip()
    if acc_no not in accounts:
        print("Account not found.")
        return None

    account = accounts[acc_no]

    if account.get("locked", False):
        print("This account is LOCKED due to too many failed attempts. Contact admin.")
        return None

    for attempt in range(3):
        pin = input("Enter 4-digit PIN: ").strip()
        if pin == account["pin"]:
            print(f"\nWelcome, {account['name']}!")
            account["failed_attempts"] = 0
            save_accounts(accounts)
            return acc_no
        else:
            print("Incorrect PIN.")
            account["failed_attempts"] = account.get("failed_attempts", 0) + 1
            remaining = 2 - attempt
            if remaining >= 0:
                print(f"Attempts remaining: {remaining}")

        if account["failed_attempts"] >= 3:
            account["locked"] = True
            print("Too many failed attempts. Your account has been LOCKED.")
            save_accounts(accounts)
            return None

    save_accounts(accounts)
    return None


# ---------------------- BANKING OPERATIONS ---------------------- #

def check_balance(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    bal = accounts[acc_no]["balance"]
    print(f"\nCurrent Balance: ₹{bal:.2f}")


def deposit_amount(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    try:
        amount = float(input("Enter amount to deposit: "))
    except ValueError:
        print("Invalid amount.")
        return

    if amount <= 0:
        print("Amount must be positive.")
        return

    account = accounts[acc_no]
    account["balance"] += amount
    log_transaction(account, "deposit", amount, account["balance"], "Cash deposit")
    save_accounts(accounts)
    print(f"Deposited ₹{amount:.2f} successfully.")
    print(f"New Balance: ₹{account['balance']:.2f}")


def withdraw_amount(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    try:
        amount = float(input("Enter amount to withdraw: "))
    except ValueError:
        print("Invalid amount.")
        return

    if amount <= 0:
        print("Amount must be positive.")
        return

    account = accounts[acc_no]

    reset_daily_withdraw_if_new_day(account)

    if amount > account["balance"]:
        print("Insufficient funds.")
        return

    # Daily limit check
    withdrawn_today = account.get("withdrawn_today", 0.0)
    limit = account.get("daily_limit", 20000.0)
    if withdrawn_today + amount > limit:
        print(f"Daily withdrawal limit exceeded! Limit: ₹{limit:.2f}, "
              f"Already withdrawn today: ₹{withdrawn_today:.2f}")
        return

    account["balance"] -= amount
    account["withdrawn_today"] = withdrawn_today + amount
    account["last_withdraw_date"] = today_str()

    log_transaction(account, "withdraw", amount, account["balance"], "Cash withdrawal")
    save_accounts(accounts)
    print(f"Withdrawn ₹{amount:.2f} successfully.")
    print(f"New Balance: ₹{account['balance']:.2f}")


def transfer_funds(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    target_acc_no = input("Enter target Account Number: ").strip()
    if target_acc_no not in accounts:
        print("Target account not found.")
        return
    if target_acc_no == acc_no:
        print("Cannot transfer to the same account.")
        return

    try:
        amount = float(input("Enter amount to transfer: "))
    except ValueError:
        print("Invalid amount.")
        return

    if amount <= 0:
        print("Amount must be positive.")
        return

    source = accounts[acc_no]
    target = accounts[target_acc_no]

    reset_daily_withdraw_if_new_day(source)

    if amount > source["balance"]:
        print("Insufficient funds.")
        return

    # Apply daily limit on transfers as well
    withdrawn_today = source.get("withdrawn_today", 0.0)
    limit = source.get("daily_limit", 20000.0)
    if withdrawn_today + amount > limit:
        print(f"Daily transaction limit exceeded! Limit: ₹{limit:.2f}, "
              f"Already used today: ₹{withdrawn_today:.2f}")
        return

    # Debit source
    source["balance"] -= amount
    source["withdrawn_today"] = withdrawn_today + amount
    source["last_withdraw_date"] = today_str()
    log_transaction(source, "transfer_out", amount, source["balance"],
                    f"Transfer to {target_acc_no}")

    # Credit target
    target["balance"] += amount
    log_transaction(target, "transfer_in", amount, target["balance"],
                    f"Transfer from {acc_no}")

    save_accounts(accounts)
    print(f"Transferred ₹{amount:.2f} to Account {target_acc_no} successfully.")
    print(f"Your New Balance: ₹{source['balance']:.2f}")


def mini_statement(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    account = accounts[acc_no]
    txns = account.get("transactions", [])
    print("\n=== MINI STATEMENT (Last 10 Transactions) ===")
    if not txns:
        print("No transactions found.")
        return

    for t in txns[-10:]:
        print(f"{t['time']} | {t['type'].upper():12} | "
              f"₹{t['amount']:10.2f} | Bal: ₹{t['balance_after']:10.2f} | {t['note']}")


def apply_interest_if_savings(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    account = accounts[acc_no]
    if account.get("type") != "savings":
        print("Interest applies only to savings accounts.")
        return

    rate = account.get("interest_rate", 0.0)
    if rate <= 0:
        print("No interest rate set for this account.")
        return

    last_date_str = account.get("last_interest_date", today_str())
    last_date = datetime.date.fromisoformat(last_date_str)
    today = datetime.date.today()

    # Calculate full months between last interest date and today
    months = (today.year - last_date.year) * 12 + (today.month - last_date.month)
    if months <= 0:
        print("Interest is already up to date.")
        return

    # Simple interest: balance * (rate/12) * months
    balance = account["balance"]
    interest = balance * (rate / 12) * months

    if interest <= 0:
        print("No interest to apply.")
        return

    account["balance"] += interest
    account["last_interest_date"] = today_str()
    log_transaction(account, "interest", interest, account["balance"],
                    f"Interest for {months} month(s) at {rate*100:.2f}% p.a.")
    save_accounts(accounts)

    print(f"Interest of ₹{interest:.2f} applied for {months} month(s).")
    print(f"New Balance: ₹{account['balance']:.2f}")


# ---------------------- ADMIN FEATURES ---------------------- #

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def admin_login() -> bool:
    print("\n--- ADMIN LOGIN ---")
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        print("Admin login successful.")
        return True
    print("Invalid admin credentials.")
    return False


def create_account(accounts: Dict[str, Dict[str, Any]]) -> None:
    print("\n--- CREATE NEW ACCOUNT ---")
    acc_no = input("Enter new Account Number: ").strip()
    if acc_no in accounts:
        print("Account number already exists.")
        return

    name = input("Account Holder Name: ").strip()
    pin = input("Set 4-digit PIN: ").strip()
    if not (pin.isdigit() and len(pin) == 4):
        print("PIN must be a 4-digit number.")
        return

    try:
        opening_balance = float(input("Opening Balance: "))
    except ValueError:
        print("Invalid amount.")
        return

    acc_type = input("Account Type (savings/current): ").strip().lower()
    if acc_type not in ("savings", "current"):
        print("Invalid account type.")
        return

    today = today_str()
    interest_rate = 0.04 if acc_type == "savings" else 0.0

    accounts[acc_no] = {
        "name": name,
        "pin": pin,
        "balance": opening_balance,
        "type": acc_type,
        "transactions": [],
        "failed_attempts": 0,
        "locked": False,
        "daily_limit": 20000.0,
        "withdrawn_today": 0.0,
        "last_withdraw_date": today,
        "interest_rate": interest_rate,
        "last_interest_date": today,
    }

    log_transaction(accounts[acc_no], "deposit", opening_balance,
                    opening_balance, "Opening deposit")
    save_accounts(accounts)
    print(f"Account {acc_no} created successfully for {name}.")


def delete_account(accounts: Dict[str, Dict[str, Any]]) -> None:
    print("\n--- DELETE ACCOUNT ---")
    acc_no = input("Enter Account Number to delete: ").strip()
    if acc_no not in accounts:
        print("Account not found.")
        return

    confirm = input(f"Are you sure you want to delete account {acc_no}? (y/n): ").strip().lower()
    if confirm == "y":
        accounts.pop(acc_no)
        save_accounts(accounts)
        print("Account deleted successfully.")
    else:
        print("Deletion cancelled.")


def unlock_account(accounts: Dict[str, Dict[str, Any]]) -> None:
    print("\n--- UNLOCK ACCOUNT ---")
    acc_no = input("Enter Account Number to unlock: ").strip()
    if acc_no not in accounts:
        print("Account not found.")
        return

    account = accounts[acc_no]
    account["locked"] = False
    account["failed_attempts"] = 0
    save_accounts(accounts)
    print(f"Account {acc_no} has been unlocked.")


def view_all_accounts(accounts: Dict[str, Dict[str, Any]]) -> None:
    print("\n--- ALL ACCOUNTS ---")
    if not accounts:
        print("No accounts available.")
        return

    for acc_no, acc in accounts.items():
        print(f"Account: {acc_no} | Name: {acc['name']} | "
              f"Type: {acc['type']} | Balance: ₹{acc['balance']:.2f} | "
              f"Locked: {acc.get('locked', False)}")


def admin_menu(accounts: Dict[str, Dict[str, Any]]) -> None:
    if not admin_login():
        return

    while True:
        print("\n=== ADMIN DASHBOARD ===")
        print("1. Create Account")
        print("2. Delete Account")
        print("3. Unlock Account")
        print("4. View All Accounts")
        print("5. Back to Main Menu")

        choice = input("Enter choice (1-5): ").strip()

        if choice == "1":
            create_account(accounts)
        elif choice == "2":
            delete_account(accounts)
        elif choice == "3":
            unlock_account(accounts)
        elif choice == "4":
            view_all_accounts(accounts)
        elif choice == "5":
            break
        else:
            print("Invalid choice. Try again.")


# ---------------------- ATM MENU ---------------------- #

def atm_menu(accounts: Dict[str, Dict[str, Any]], acc_no: str) -> None:
    while True:
        print("\n=== ATM MENU ===")
        print("1. Balance Enquiry")
        print("2. Deposit")
        print("3. Withdraw")
        print("4. Fund Transfer")
        print("5. Mini Statement")
        print("6. Apply Interest (Savings)")
        print("7. Logout")

        choice = input("Enter choice (1-7): ").strip()

        if choice == "1":
            check_balance(accounts, acc_no)
        elif choice == "2":
            deposit_amount(accounts, acc_no)
        elif choice == "3":
            withdraw_amount(accounts, acc_no)
        elif choice == "4":
            transfer_funds(accounts, acc_no)
        elif choice == "5":
            mini_statement(accounts, acc_no)
        elif choice == "6":
            apply_interest_if_savings(accounts, acc_no)
        elif choice == "7":
            print("Logging out from ATM...")
            break
        else:
            print("Invalid choice. Try again.")


# ---------------------- MAIN APPLICATION LOOP ---------------------- #

def main():
    accounts = load_accounts()

    while True:
        print("\n" + "=" * 50)
        print("BANKING & ATM SIMULATION SYSTEM")
        print("1. Login to ATM")
        print("2. Admin Dashboard")
        print("3. Exit")

        choice = input("Enter choice (1-3): ").strip()

        if choice == "1":
            acc_no = authenticate(accounts)
            if acc_no:
                atm_menu(accounts, acc_no)
        elif choice == "2":
            admin_menu(accounts)
        elif choice == "3":
            print("Thank you for using the Banking & ATM Simulation System!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
