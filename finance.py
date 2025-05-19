# src/routes/finance.py

from flask import Blueprint, jsonify, request, current_app # Added current_app for logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func, case
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
import json # For handling crypto balances

# Assuming JWT or similar auth is implemented later to get current_user
# For now, we might pass user_id in requests or use a placeholder
# from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import db, User
from src.models.finance import Wallet, Transaction, TransactionType, TransactionStatus, CashControlSession, CashSessionStatus, AccountsPayableReceivable, AccountType, AccountStatus

finance_bp = Blueprint("finance", __name__)

# --- Mock Exchange Rates --- 
MOCK_RATES = {
    "BRL_USDT": Decimal("5.10"), # 1 USDT = 5.10 BRL
    "USDT_BRL": Decimal("5.05"), # 1 USDT = 5.05 BRL (Simulating spread/fees)
}
SUPPORTED_CRYPTO = ["USDT"] # Initially support only USDT
CRYPTO_PRECISION = 8 # Decimal places for crypto amounts
BRL_PRECISION = 2 # Decimal places for BRL amounts

# --- Helper Function (Placeholder for getting current user) ---
def get_current_user_id():
    # Placeholder - Replace with actual auth
    user_id = request.args.get("user_id", default=1, type=int)
    return user_id

# --- Helper Function for Crypto Balance Update ---
def _update_crypto_balance(balance_json, asset, amount_change):
    """Updates the crypto balance JSON field."""
    if not isinstance(amount_change, Decimal):
        amount_change = Decimal(str(amount_change))
    current_balances = balance_json if balance_json else {}
    current_amount = Decimal(str(current_balances.get(asset, "0.0")))
    new_amount = current_amount + amount_change
    if new_amount < 0:
        raise ValueError(f"Insufficient balance for {asset}")
    current_balances[asset] = str(new_amount.quantize(Decimal("1e-" + str(CRYPTO_PRECISION)), rounding=ROUND_HALF_UP))
    if new_amount == 0:
        del current_balances[asset]
    return current_balances

# --- Wallet Endpoints --- 

# @jwt_required()
@finance_bp.route("/wallets/my", methods=["GET"])
def get_my_wallet():
    current_app.logger.info("Accessed /wallets/my endpoint") # Added logging
    user_id = get_current_user_id()
    current_app.logger.info(f"Attempting to find wallet for user_id: {user_id}") # Added logging
    try:
        wallet = Wallet.query.filter_by(user_id=user_id).first_or_404()
        current_app.logger.info(f"Wallet found for user_id: {user_id}") # Added logging
    except Exception as e:
        current_app.logger.error(f"Error finding wallet for user_id {user_id}: {e}") # Added logging
        # Let first_or_404 handle the 404 response if not found
        raise e
        
    recent_transactions = Transaction.query.filter_by(wallet_id=wallet.id)\
                                         .order_by(Transaction.created_at.desc())\
                                         .limit(20).all()
    transactions_data = [
        {
            "id": t.id,
            "type": t.type.value,
            "amount_brl": str(t.amount_brl.quantize(Decimal("1e-" + str(BRL_PRECISION)))) if t.amount_brl is not None else None,
            "amount_crypto": str(t.amount_crypto.quantize(Decimal("1e-" + str(CRYPTO_PRECISION)))) if t.amount_crypto is not None else None,
            "crypto_asset": t.crypto_asset,
            "description": t.description,
            "status": t.status.value,
            "created_at": t.created_at.isoformat()
        } for t in recent_transactions
    ]
    return jsonify({
        "user_id": wallet.user_id,
        "balance_brl": str(wallet.balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "balance_crypto": wallet.balance_crypto, 
        "updated_at": wallet.updated_at.isoformat(),
        "recent_transactions": transactions_data
    }), 200

# @jwt_required()
@finance_bp.route("/wallets/transfer", methods=["POST"])
def transfer_balance():
    sender_user_id = get_current_user_id()
    data = request.json
    recipient_email = data.get("recipient_email")
    amount_str = data.get("amount_brl")
    description = data.get("description", "Transferência interna")
    if not recipient_email or not amount_str:
        return jsonify({"error": "Recipient email and amount_brl are required"}), 400
    try:
        amount = Decimal(amount_str).quantize(Decimal("1e-" + str(BRL_PRECISION)))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount_brl format"}), 400
    sender_wallet = Wallet.query.filter_by(user_id=sender_user_id).first()
    recipient_user = User.query.filter_by(email=recipient_email).first()
    if not sender_wallet:
        return jsonify({"error": "Sender wallet not found"}), 404
    if not recipient_user:
        return jsonify({"error": "Recipient user not found"}), 404
    if recipient_user.id == sender_user_id:
        return jsonify({"error": "Cannot transfer to yourself"}), 400
    recipient_wallet = Wallet.query.filter_by(user_id=recipient_user.id).first()
    if not recipient_wallet:
        return jsonify({"error": "Recipient wallet not found"}), 404
    if sender_wallet.balance_brl < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    try:
        sender_wallet.balance_brl -= amount
        recipient_wallet.balance_brl += amount
        sender_transaction = Transaction(wallet_id=sender_wallet.id, type=TransactionType.TRANSFER_OUT, amount_brl=-amount, description=f"{description} para {recipient_email}", related_user_id=recipient_user.id, status=TransactionStatus.COMPLETED)
        recipient_transaction = Transaction(wallet_id=recipient_wallet.id, type=TransactionType.TRANSFER_IN, amount_brl=amount, description=f"{description} de {sender_wallet.user.email}", related_user_id=sender_user_id, status=TransactionStatus.COMPLETED)
        db.session.add_all([sender_transaction, recipient_transaction, sender_wallet, recipient_wallet])
        db.session.commit()
        return jsonify({"message": "Transfer successful", "sender_new_balance_brl": str(sender_wallet.balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION))))}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error during transfer: {e}")
        return jsonify({"error": "An internal error occurred during transfer."}), 500

# @jwt_required()
@finance_bp.route("/wallets/convert", methods=["POST"])
def convert_currency():
    user_id = get_current_user_id()
    wallet = Wallet.query.filter_by(user_id=user_id).first_or_404()
    data = request.json
    from_currency = data.get("from_currency")
    to_currency = data.get("to_currency")
    amount_str = data.get("amount")
    if not from_currency or not to_currency or not amount_str:
        return jsonify({"error": "from_currency, to_currency, and amount are required"}), 400
    if from_currency == to_currency:
        return jsonify({"error": "Cannot convert to the same currency"}), 400
    if to_currency not in SUPPORTED_CRYPTO and to_currency != "BRL":
        return jsonify({"error": f"Conversion to {to_currency} is not supported"}), 400
    if from_currency not in SUPPORTED_CRYPTO and from_currency != "BRL":
        return jsonify({"error": f"Conversion from {from_currency} is not supported"}), 400
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount format"}), 400
    rate_key = f"{from_currency}_{to_currency}"
    if rate_key not in MOCK_RATES:
        return jsonify({"error": f"Conversion rate for {rate_key} not available"}), 500
    rate = MOCK_RATES[rate_key]
    converted_amount = Decimal("0.0")
    transaction_out, transaction_in = None, None
    try:
        if from_currency == "BRL" and to_currency in SUPPORTED_CRYPTO:
            amount = amount.quantize(Decimal("1e-" + str(BRL_PRECISION)))
            if wallet.balance_brl < amount:
                return jsonify({"error": "Insufficient BRL balance"}), 400
            converted_amount = (amount / rate).quantize(Decimal("1e-" + str(CRYPTO_PRECISION)), rounding=ROUND_HALF_UP)
            if converted_amount == 0:
                return jsonify({"error": "Converted amount is too small"}), 400
            wallet.balance_brl -= amount
            wallet.balance_crypto = _update_crypto_balance(wallet.balance_crypto, to_currency, converted_amount)
            transaction_out = Transaction(wallet_id=wallet.id, type=TransactionType.CRYPTO_CONVERT_OUT, amount_brl=-amount, description=f"Convert {amount} BRL to {to_currency}", status=TransactionStatus.COMPLETED)
            transaction_in = Transaction(wallet_id=wallet.id, type=TransactionType.CRYPTO_CONVERT_IN, amount_brl=Decimal("0.0"), amount_crypto=converted_amount, crypto_asset=to_currency, description=f"Convert BRL to {converted_amount} {to_currency}", status=TransactionStatus.COMPLETED)
        elif from_currency in SUPPORTED_CRYPTO and to_currency == "BRL":
            amount = amount.quantize(Decimal("1e-" + str(CRYPTO_PRECISION)))
            current_crypto_balances = wallet.balance_crypto if wallet.balance_crypto else {}
            current_asset_balance = Decimal(str(current_crypto_balances.get(from_currency, "0.0")))
            if current_asset_balance < amount:
                return jsonify({"error": f"Insufficient {from_currency} balance"}), 400
            converted_amount = (amount * rate).quantize(Decimal("1e-" + str(BRL_PRECISION)), rounding=ROUND_HALF_UP)
            if converted_amount == 0:
                return jsonify({"error": "Converted amount is too small"}), 400
            wallet.balance_crypto = _update_crypto_balance(wallet.balance_crypto, from_currency, -amount)
            wallet.balance_brl += converted_amount
            transaction_out = Transaction(wallet_id=wallet.id, type=TransactionType.CRYPTO_CONVERT_OUT, amount_brl=Decimal("0.0"), amount_crypto=-amount, crypto_asset=from_currency, description=f"Convert {amount} {from_currency} to BRL", status=TransactionStatus.COMPLETED)
            transaction_in = Transaction(wallet_id=wallet.id, type=TransactionType.CRYPTO_CONVERT_IN, amount_brl=converted_amount, description=f"Convert {from_currency} to {converted_amount} BRL", status=TransactionStatus.COMPLETED)
        else:
            return jsonify({"error": "Unsupported conversion direction"}), 400
        
        db.session.add(wallet)
        db.session.add(transaction_out)
        db.session.add(transaction_in)
        db.session.commit()
        
        return jsonify({
            "message": "Conversion successful",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount_converted": str(amount),
            "amount_received": str(converted_amount),
            "new_balance_brl": str(wallet.balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
            "new_balance_crypto": wallet.balance_crypto
        }), 200
    except ValueError as ve:
        db.session.rollback()
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error during currency conversion: {e}")
        return jsonify({"error": "An internal error occurred during conversion."}), 500

# --- Cash Control Endpoints --- 
@finance_bp.route("/cash_control/open", methods=["POST"])
def open_cash_session():
    user_id = get_current_user_id()
    data = request.json
    initial_balance_str = data.get("initial_balance_brl")
    initial_details = data.get("initial_balance_details", {})
    if initial_balance_str is None:
        return jsonify({"error": "initial_balance_brl is required"}), 400
    try:
        initial_balance = Decimal(initial_balance_str)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid initial_balance_brl format"}), 400
        
    existing_open_session = CashControlSession.query.filter_by(user_id=user_id, status=CashSessionStatus.OPEN).first()
    if existing_open_session:
        return jsonify({"error": "An open cash session already exists for this user"}), 409
    try:
        new_session = CashControlSession(user_id=user_id, initial_balance_brl=initial_balance, initial_balance_details=initial_details, status=CashSessionStatus.OPEN)
        db.session.add(new_session)
        db.session.commit()
        return jsonify({"message": "Cash session opened successfully", "session_id": new_session.id, "start_time": new_session.start_time.isoformat()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error opening cash session: {e}")
        return jsonify({"error": "An internal error occurred while opening cash session."}), 500

@finance_bp.route("/cash_control/close", methods=["POST"])
def close_cash_session():
    user_id = get_current_user_id()
    session_to_close = CashControlSession.query.filter_by(user_id=user_id, status=CashSessionStatus.OPEN).first()
    if not session_to_close:
        return jsonify({"error": "No open cash session found for this user"}), 404
        
    transactions_in_session = Transaction.query.filter(Transaction.cash_session_id == session_to_close.id, Transaction.status == TransactionStatus.COMPLETED).all()
    calculated_change = sum(t.amount_brl for t in transactions_in_session if t.type in [TransactionType.CASH_IN, TransactionType.CASH_OUT])
    calculated_final_balance = session_to_close.initial_balance_brl + calculated_change
    data = request.json
    final_details = data.get("final_balance_details", {})
    try:
        session_to_close.end_time = datetime.utcnow()
        session_to_close.final_balance_brl = calculated_final_balance
        session_to_close.final_balance_details = final_details
        session_to_close.status = CashSessionStatus.CLOSED
        db.session.add(session_to_close)
        db.session.commit()
        return jsonify({"message": "Cash session closed successfully", "session_id": session_to_close.id, "end_time": session_to_close.end_time.isoformat(), "calculated_final_brl": str(calculated_final_balance.quantize(Decimal("1e-" + str(BRL_PRECISION))))}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error closing cash session: {e}")
        return jsonify({"error": "An internal error occurred while closing cash session."}), 500

@finance_bp.route("/cash_control/current", methods=["GET"])
def get_current_cash_session():
    user_id = get_current_user_id()
    current_session = CashControlSession.query.filter_by(user_id=user_id, status=CashSessionStatus.OPEN).first()
    if not current_session:
        return jsonify({"message": "No open cash session found"}), 404
        
    transactions_in_session = Transaction.query.filter(Transaction.cash_session_id == current_session.id, Transaction.status == TransactionStatus.COMPLETED).all()
    calculated_change = sum(t.amount_brl for t in transactions_in_session if t.type in [TransactionType.CASH_IN, TransactionType.CASH_OUT])
    current_expected_balance = current_session.initial_balance_brl + calculated_change
    return jsonify({
        "session_id": current_session.id,
        "user_id": current_session.user_id,
        "start_time": current_session.start_time.isoformat(),
        "initial_balance_brl": str(current_session.initial_balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "initial_balance_details": current_session.initial_balance_details,
        "current_expected_brl": str(current_expected_balance.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "status": current_session.status.value
    }), 200

@finance_bp.route("/cash_control/record_cash_transaction", methods=["POST"])
def record_cash_transaction():
    user_id = get_current_user_id()
    current_session = CashControlSession.query.filter_by(user_id=user_id, status=CashSessionStatus.OPEN).first()
    if not current_session:
        return jsonify({"error": "No open cash session found to record transaction"}), 404
        
    data = request.json
    transaction_type_str = data.get("type")
    amount_str = data.get("amount_brl")
    description = data.get("description")
    if not transaction_type_str or not amount_str or not description:
        return jsonify({"error": "Type (CASH_IN/CASH_OUT), amount_brl, and description are required"}), 400
    try:
        transaction_type = TransactionType(transaction_type_str)
        if transaction_type not in [TransactionType.CASH_IN, TransactionType.CASH_OUT]:
            raise ValueError("Invalid transaction type for cash control")
        amount = Decimal(amount_str).quantize(Decimal("1e-" + str(BRL_PRECISION)))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid type or amount_brl format"}), 400
        
    actual_amount = amount if transaction_type == TransactionType.CASH_IN else -amount
    user_wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not user_wallet:
        return jsonify({"error": "User wallet not found"}), 404
    try:
        user_wallet.balance_brl += actual_amount
        cash_transaction = Transaction(wallet_id=user_wallet.id, cash_session_id=current_session.id, type=transaction_type, amount_brl=actual_amount, description=description, status=TransactionStatus.COMPLETED)
        db.session.add(cash_transaction)
        db.session.add(user_wallet)
        db.session.commit()
        return jsonify({"message": "Cash transaction recorded successfully", "transaction_id": cash_transaction.id, "new_wallet_balance_brl": str(user_wallet.balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION))))}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error recording cash transaction: {e}")
        return jsonify({"error": "An internal error occurred while recording cash transaction."}), 500

# --- Accounts Payable/Receivable Endpoints --- 
@finance_bp.route("/accounts", methods=["POST"])
def create_account():
    user_id = get_current_user_id()
    data = request.json
    account_type_str = data.get("type")
    description = data.get("description")
    due_date_str = data.get("due_date")
    amount_str = data.get("amount")
    related_user_email = data.get("related_user_email")
    if not account_type_str or not description or not due_date_str or not amount_str:
        return jsonify({"error": "type, description, due_date, and amount are required"}), 400
    try:
        account_type = AccountType(account_type_str)
        due_date = date.fromisoformat(due_date_str)
        amount = Decimal(amount_str).quantize(Decimal("1e-" + str(BRL_PRECISION)))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input format: {e}"}), 400
        
    related_user_id = None
    if related_user_email:
        related_user = User.query.filter_by(email=related_user_email).first()
        related_user_id = related_user.id if related_user else None
        
    try:
        new_account = AccountsPayableReceivable(user_id=user_id, type=account_type, description=description, due_date=due_date, amount=amount, related_user_id=related_user_id, status=AccountStatus.PENDING)
        db.session.add(new_account)
        db.session.commit()
        return jsonify({"message": f"{account_type.value} account created successfully", "account_id": new_account.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating account: {e}")
        return jsonify({"error": "An internal error occurred while creating account."}), 500

@finance_bp.route("/accounts", methods=["GET"])
def list_accounts():
    user_id = get_current_user_id()
    account_type_str = request.args.get("type")
    status_str = request.args.get("status")
    due_before_str = request.args.get("due_before")
    due_after_str = request.args.get("due_after")
    query = AccountsPayableReceivable.query.filter_by(user_id=user_id)
    
    if account_type_str:
        try:
            query = query.filter_by(type=AccountType(account_type_str))
        except ValueError:
            return jsonify({"error": "Invalid type filter"}), 400
    if status_str:
        try:
            query = query.filter_by(status=AccountStatus(status_str))
        except ValueError:
            return jsonify({"error": "Invalid status filter"}), 400
    if due_before_str:
        try:
            due_before = date.fromisoformat(due_before_str)
            query = query.filter(AccountsPayableReceivable.due_date <= due_before)
        except ValueError:
            return jsonify({"error": "Invalid due_before date format (YYYY-MM-DD)"}), 400
    if due_after_str:
        try:
            due_after = date.fromisoformat(due_after_str)
            query = query.filter(AccountsPayableReceivable.due_date >= due_after)
        except ValueError:
            return jsonify({"error": "Invalid due_after date format (YYYY-MM-DD)"}), 400
            
    accounts = query.order_by(AccountsPayableReceivable.due_date).all()
    accounts_data = [
        {
            "id": acc.id,
            "type": acc.type.value,
            "description": acc.description,
            "due_date": acc.due_date.isoformat(),
            "amount": str(acc.amount.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
            "status": acc.status.value,
            "related_user_id": acc.related_user_id,
            "related_user_email": acc.related_user.email if acc.related_user else None,
            "created_at": acc.created_at.isoformat(),
            "paid_received_at": acc.paid_received_at.isoformat() if acc.paid_received_at else None
        }
        for acc in accounts
    ]
    return jsonify(accounts_data), 200

@finance_bp.route("/accounts/<int:account_id>/status", methods=["PUT"])
def update_account_status(account_id):
    user_id = get_current_user_id()
    account = AccountsPayableReceivable.query.filter_by(id=account_id, user_id=user_id).first_or_404()
    if account.status not in [AccountStatus.PENDING, AccountStatus.OVERDUE]:
        return jsonify({"error": f"Cannot update status of account with status {account.status.value}"}), 400
        
    data = request.json
    new_status_str = data.get("status")
    if not new_status_str:
        return jsonify({"error": "New status is required"}), 400
    try:
        new_status = AccountStatus(new_status_str)
        if new_status not in [AccountStatus.PAID, AccountStatus.RECEIVED, AccountStatus.CANCELLED]:
            raise ValueError("Invalid target status")
        if (account.type == AccountType.PAYABLE and new_status == AccountStatus.RECEIVED) or \
           (account.type == AccountType.RECEIVABLE and new_status == AccountStatus.PAID):
            raise ValueError("Status does not match account type")
    except ValueError as e:
        return jsonify({"error": f"Invalid status: {e}"}), 400
        
    transaction_needed = new_status in [AccountStatus.PAID, AccountStatus.RECEIVED]
    user_wallet = Wallet.query.filter_by(user_id=user_id).first()
    if transaction_needed and not user_wallet:
        return jsonify({"error": "User wallet not found to record transaction"}), 404
        
    try:
        account.status = new_status
        account.paid_received_at = datetime.utcnow() if new_status != AccountStatus.CANCELLED else None
        db.session.add(account)
        if transaction_needed:
            amount_brl = -account.amount if account.type == AccountType.PAYABLE else account.amount
            transaction_type = TransactionType.PAYABLE_PAID if account.type == AccountType.PAYABLE else TransactionType.RECEIVABLE_RECEIVED
            user_wallet.balance_brl += amount_brl
            settlement_transaction = Transaction(wallet_id=user_wallet.id, type=transaction_type, amount_brl=amount_brl, description=f"Settlement for Account ID: {account.id} - {account.description}", account_payable_receivable_id=account.id, status=TransactionStatus.COMPLETED)
            db.session.add(settlement_transaction)
            db.session.add(user_wallet)
        db.session.commit()
        return jsonify({"message": f"Account {account_id} status updated to {new_status.value}"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating account status: {e}")
        return jsonify({"error": "An internal error occurred while updating account status."}), 500

@finance_bp.route("/accounts/<int:account_id>", methods=["DELETE"])
def delete_account(account_id):
    user_id = get_current_user_id()
    account = AccountsPayableReceivable.query.filter_by(id=account_id, user_id=user_id).first_or_404()
    try:
        db.session.delete(account)
        db.session.commit()
        return jsonify({"message": f"Account {account_id} deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting account: {e}")
        return jsonify({"error": "An internal error occurred while deleting account."}), 500

# --- Basic Financial AI Endpoints --- 

# @jwt_required() # Add Autopeça/Admin check decorator later
@finance_bp.route("/ai/forecast", methods=["GET"])
def get_financial_forecast():
    user_id = get_current_user_id()
    wallet = Wallet.query.filter_by(user_id=user_id).first_or_404()
    days_to_forecast = request.args.get("days", default=30, type=int)
    history_days = request.args.get("history", default=90, type=int)

    if days_to_forecast <= 0 or history_days <= 0:
        return jsonify({"error": "Forecast days and history days must be positive"}), 400

    # --- Simple Forecast Logic --- 
    past_date_limit = datetime.utcnow() - timedelta(days=history_days)
    future_date_limit = datetime.utcnow().date() + timedelta(days=days_to_forecast)

    # Calculate historical net change
    historical_transactions = Transaction.query.filter(
        Transaction.wallet_id == wallet.id,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= past_date_limit
    ).all()
    
    total_historical_change = sum(t.amount_brl for t in historical_transactions if t.amount_brl is not None)
    average_daily_change = (total_historical_change / history_days) if history_days > 0 and len(historical_transactions) > 0 else Decimal("0.0")

    # Calculate future known changes from accounts payable/receivable
    upcoming_accounts = AccountsPayableReceivable.query.filter(
        AccountsPayableReceivable.user_id == user_id,
        AccountsPayableReceivable.status == AccountStatus.PENDING,
        AccountsPayableReceivable.due_date <= future_date_limit,
        AccountsPayableReceivable.due_date >= datetime.utcnow().date() # Only future or today
    ).all()

    total_upcoming_receivables = sum(acc.amount for acc in upcoming_accounts if acc.type == AccountType.RECEIVABLE)
    total_upcoming_payables = sum(acc.amount for acc in upcoming_accounts if acc.type == AccountType.PAYABLE)
    net_upcoming_known_change = total_upcoming_receivables - total_upcoming_payables

    # Project future balance
    projected_change_from_average = average_daily_change * days_to_forecast
    projected_final_balance = wallet.balance_brl + projected_change_from_average + net_upcoming_known_change

    # --- Generate Alerts --- 
    alerts = []
    if projected_final_balance < 0:
        alerts.append({"type": "RISK_FLOW", "message": "Alerta: Previsão de fluxo de caixa negativo nos próximos {} dias.".format(days_to_forecast)})
        
    overdue_accounts = AccountsPayableReceivable.query.filter(
        AccountsPayableReceivable.user_id == user_id,
        AccountsPayableReceivable.status == AccountStatus.PENDING,
        AccountsPayableReceivable.due_date < datetime.utcnow().date()
    ).count()
    if overdue_accounts > 0:
         alerts.append({"type": "OVERDUE_ACCOUNTS", "message": f"Alerta: Existem {overdue_accounts} contas pendentes vencidas."}) 

    return jsonify({
        "current_balance_brl": str(wallet.balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "forecast_days": days_to_forecast,
        "average_daily_change_brl": str(average_daily_change.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "net_upcoming_known_change_brl": str(net_upcoming_known_change.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "projected_final_balance_brl": str(projected_final_balance.quantize(Decimal("1e-" + str(BRL_PRECISION)))),
        "alerts": alerts
    }), 200

# @jwt_required() # Add Autopeça/Admin check decorator later
@finance_bp.route("/ai/recommendations", methods=["GET"])
def get_financial_recommendations():
    user_id = get_current_user_id()
    wallet = Wallet.query.filter_by(user_id=user_id).first_or_404()
    
    recommendations = []
    
    # Recommendation: Invest idle BRL balance
    idle_threshold = Decimal("1000.00") # Example threshold
    if wallet.balance_brl > idle_threshold and "USDT" in SUPPORTED_CRYPTO and "BRL_USDT" in MOCK_RATES:
        rate = MOCK_RATES["BRL_USDT"]
        # Suggest converting half of the idle balance above the threshold
        amount_to_convert = (wallet.balance_brl - idle_threshold) / 2 
        if amount_to_convert > 10: # Only suggest if amount is somewhat significant
            amount_to_convert = amount_to_convert.quantize(Decimal("1e-" + str(BRL_PRECISION)))
            potential_usdt = (amount_to_convert / rate).quantize(Decimal("1e-" + str(CRYPTO_PRECISION)))
            if potential_usdt > 0:
                 recommendations.append({
                     "type": "INVEST_IDLE_CASH",
                     "message": f"Recomendação: Considere converter parte do seu saldo BRL ocioso (ex: R$ {amount_to_convert}) em aprox. {potential_usdt} USDT para potencial proteção contra inflação ou rendimento.",
                     "details": {"convert_amount_brl": str(amount_to_convert), "to_asset": "USDT"}
                 })

    # Add more recommendations (e.g., pay upcoming bills, offer discounts on slow-moving stock based on financial data)
    
    return jsonify(recommendations), 200

# @jwt_required() # Add Autopeça/Admin check decorator later
@finance_bp.route("/ai/audit", methods=["GET"])
def get_audit_suggestions():
    user_id = get_current_user_id()
    wallet = Wallet.query.filter_by(user_id=user_id).first_or_404()
    
    suggestions = []
    
    # Audit: Find potentially duplicate transactions (same amount, type, description within a short time)
    time_window = timedelta(minutes=5)
    # Correct approach: Find transactions, then group in Python or use window functions if DB supports well
    recent_transactions = Transaction.query.filter(
        Transaction.wallet_id == wallet.id,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= datetime.utcnow() - timedelta(days=7) # Check last 7 days
    ).order_by(Transaction.created_at).all()

    potential_duplicates_groups = {}
    for i, tx1 in enumerate(recent_transactions):
        for j in range(i + 1, len(recent_transactions)):
            tx2 = recent_transactions[j]
            # Check time window
            if tx2.created_at - tx1.created_at > time_window:
                break # Since transactions are ordered, no need to check further for tx1
            
            # Check for similarity
            if tx1.type == tx2.type and \
               tx1.amount_brl == tx2.amount_brl and \
               tx1.amount_crypto == tx2.amount_crypto and \
               tx1.crypto_asset == tx2.crypto_asset and \
               tx1.description == tx2.description: # Consider fuzzy matching for description?
                
                # Group duplicates
                group_key = (tx1.type, tx1.amount_brl, tx1.amount_crypto, tx1.crypto_asset, tx1.description)
                if group_key not in potential_duplicates_groups:
                    potential_duplicates_groups[group_key] = set()
                potential_duplicates_groups[group_key].add(tx1.id)
                potential_duplicates_groups[group_key].add(tx2.id)

    for key, ids_set in potential_duplicates_groups.items():
        if len(ids_set) > 1:
            type, amount_brl, amount_crypto, crypto_asset, desc = key
            amount_str = f"BRL: {amount_brl}" if amount_brl is not None else f"{amount_crypto} {crypto_asset}"
            suggestions.append({
                "type": "POTENTIAL_DUPLICATE_TRANSACTION",
                "message": f"Auditoria: Encontradas {len(ids_set)} transações potencialmente duplicadas (Valor: {amount_str}, Tipo: {type.value}, Desc: 	'{desc}	') próximas no tempo. Verifique os IDs: {list(ids_set)}",
                "details": {"amount_brl": str(amount_brl), "amount_crypto": str(amount_crypto), "crypto_asset": crypto_asset, "type": type.value, "description": desc, "count": len(ids_set), "ids": list(ids_set)}
            })
            
    # Add more audit checks (e.g., negative balances, large unexpected transactions)

    return jsonify(suggestions), 200

# --- Admin Specific Finance Routes ---

# @jwt_required() # Add admin check decorator later
@finance_bp.route("/admin/add_balance", methods=["POST"])
def admin_add_balance():
    data = request.json
    target_user_email = data.get("target_user_email")
    amount_str = data.get("amount_brl")
    description = data.get("description", "Ajuste manual de saldo pelo Admin")
    if not target_user_email or not amount_str:
        return jsonify({"error": "Target user email and amount_brl are required"}), 400
    try:
        amount = Decimal(amount_str).quantize(Decimal("1e-" + str(BRL_PRECISION)))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount_brl format"}), 400
        
    target_user = User.query.filter_by(email=target_user_email).first()
    if not target_user:
        return jsonify({"error": "Target user not found"}), 404
    target_wallet = Wallet.query.filter_by(user_id=target_user.id).first()
    if not target_wallet:
        return jsonify({"error": "Target wallet not found"}), 404
    try:
        target_wallet.balance_brl += amount
        adjustment_transaction = Transaction(wallet_id=target_wallet.id, type=TransactionType.MANUAL_ADJUST, amount_brl=amount, description=description, status=TransactionStatus.COMPLETED)
        db.session.add(adjustment_transaction)
        db.session.add(target_wallet)
        db.session.commit()
        return jsonify({"message": "Balance adjusted successfully", "target_user_email": target_user_email, "new_balance_brl": str(target_wallet.balance_brl.quantize(Decimal("1e-" + str(BRL_PRECISION))))}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error during admin balance adjustment: {e}")
        return jsonify({"error": "An internal error occurred during balance adjustment."}), 500

# Add other finance endpoints here (withdraw, deposit etc.) later

