# src/routes/order.py

from flask import Blueprint, jsonify, request
from decimal import Decimal

# Assuming JWT or similar auth is implemented later
# from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import db, User
from src.models.finance import Wallet, Transaction, TransactionType, TransactionStatus
from src.models.order import Order, OrderStatus, PaymentStatus # Import Order model and enums

order_bp = Blueprint("order", __name__)

# --- Helper Function (Placeholder for getting current user) ---
def get_current_user_id():
    # Placeholder - Replace with actual auth
    user_id = request.args.get("user_id", default=1, type=int)
    return user_id

# --- Automated Commission Payment Logic --- 
def _process_commission_payment(order):
    """Handles the automated commission payment when an order is completed."""
    if not order.mechanic_id or not order.commission_amount or order.commission_amount <= 0:
        print(f"Order {order.id}: No mechanic or commission amount, skipping commission payment.")
        return True # Not an error, just nothing to process

    mechanic_wallet = Wallet.query.filter_by(user_id=order.mechanic_id).first()
    autpeca_wallet = Wallet.query.filter_by(user_id=order.autpeca_id).first()

    if not mechanic_wallet or not autpeca_wallet:
        print(f"Error processing commission for Order {order.id}: Wallet not found for mechanic or autopeça.")
        # In a real system, this should raise an alert or handle the error more robustly
        return False

    commission = Decimal(order.commission_amount) # Ensure it's Decimal

    # Check autopeça balance
    if autpeca_wallet.balance_brl < commission:
        print(f"Error processing commission for Order {order.id}: Autopeça {order.autpeca_id} has insufficient balance ({autpeca_wallet.balance_brl} < {commission}).")
        # Mark commission as pending? Or notify admin?
        # For now, we just fail the automatic processing for this attempt.
        return False

    try:
        # Deduct from autopeça, add to mechanic
        autpeca_wallet.balance_brl -= commission
        mechanic_wallet.balance_brl += commission

        # Create transaction records
        commission_out_tx = Transaction(
            wallet_id=autpeca_wallet.id,
            type=TransactionType.COMMISSION_OUT,
            amount_brl=-commission,
            description=f"Comissão referente ao Pedido #{order.id}",
            related_order_id=order.id,
            related_user_id=order.mechanic_id,
            status=TransactionStatus.COMPLETED
        )
        commission_in_tx = Transaction(
            wallet_id=mechanic_wallet.id,
            type=TransactionType.COMMISSION_IN,
            amount_brl=commission,
            description=f"Comissão recebida referente ao Pedido #{order.id} (Autopeça: {order.autpeca_id})",
            related_order_id=order.id,
            related_user_id=order.autpeca_id,
            status=TransactionStatus.COMPLETED
        )

        db.session.add_all([autpeca_wallet, mechanic_wallet, commission_out_tx, commission_in_tx])
        # db.session.commit() will be called by the calling function (update_order_status)
        print(f"Order {order.id}: Commission payment processed successfully.")
        return True

    except Exception as e:
        # db.session.rollback() will be called by the calling function
        print(f"Error during commission payment processing for Order {order.id}: {e}")
        return False

# --- Order Endpoints --- 

# Example endpoint to create an order (basic)
# @jwt_required()
@order_bp.route("/orders", methods=["POST"])
def create_order():
    # user_id = get_jwt_identity() # Customer creating order
    customer_id = get_current_user_id()
    data = request.json

    # Simplified: Assume autpeca_id, mechanic_id, total_amount, commission_amount are provided
    autpeca_id = data.get("autpeca_id")
    mechanic_id = data.get("mechanic_id") # Optional
    total_amount_str = data.get("total_amount")
    commission_amount_str = data.get("commission_amount", "0.00")

    if not autpeca_id or not total_amount_str:
        return jsonify({"error": "autpeca_id and total_amount are required"}), 400

    try:
        total_amount = Decimal(total_amount_str)
        commission_amount = Decimal(commission_amount_str)
        if total_amount <= 0:
            raise ValueError("Total amount must be positive")
        if commission_amount < 0:
             raise ValueError("Commission amount cannot be negative")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount format"}), 400

    try:
        new_order = Order(
            customer_id=customer_id,
            autpeca_id=autpeca_id,
            mechanic_id=mechanic_id,
            total_amount=total_amount,
            commission_amount=commission_amount,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING
        )
        db.session.add(new_order)
        db.session.commit()
        return jsonify({"message": "Order created successfully", "order_id": new_order.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating order: {e}")
        return jsonify({"error": "An internal error occurred while creating order."}), 500

# Endpoint to update order status (e.g., by Autopeça or Admin)
# @jwt_required()
@order_bp.route("/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    # user_id = get_jwt_identity() # User performing the update (e.g., Autopeça)
    # Add authorization check: Ensure user is allowed to update this order
    
    order = Order.query.get_or_404(order_id)
    data = request.json
    new_status_str = data.get("status")
    new_payment_status_str = data.get("payment_status")

    if not new_status_str and not new_payment_status_str:
        return jsonify({"error": "New status or payment_status is required"}), 400

    updated = False
    commission_processed = None

    try:
        if new_status_str:
            try:
                new_status = OrderStatus(new_status_str)
                if order.status != new_status:
                    order.status = new_status
                    updated = True
            except ValueError:
                return jsonify({"error": f"Invalid order status: {new_status_str}"}), 400

        if new_payment_status_str:
            try:
                new_payment_status = PaymentStatus(new_payment_status_str)
                if order.payment_status != new_payment_status:
                    order.payment_status = new_payment_status
                    updated = True
            except ValueError:
                 return jsonify({"error": f"Invalid payment status: {new_payment_status_str}"}), 400

        if updated:
            db.session.add(order)
            
            # --- Trigger Commission Payment --- 
            # Check if order is considered complete for commission (e.g., Delivered and Paid)
            if order.status == OrderStatus.DELIVERED and order.payment_status == PaymentStatus.PAID:
                 # Attempt to process commission
                 success = _process_commission_payment(order)
                 if success:
                     commission_processed = True
                     # Optionally, update order status to COMPLETED here if commission success is required
                     # order.status = OrderStatus.COMPLETED 
                     # db.session.add(order)
                 else:
                     commission_processed = False
                     # Decide how to handle failure: retry later? notify admin?
                     # For now, we commit the status update but note commission failure.
            
            db.session.commit()
            
            response = {"message": f"Order {order_id} updated successfully"}
            if commission_processed is not None:
                response["commission_status"] = "Processed" if commission_processed else "Failed (Check Logs/Balance)"
            return jsonify(response), 200
        else:
            return jsonify({"message": "No changes detected in status or payment_status"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating order status for {order_id}: {e}")
        return jsonify({"error": "An internal error occurred while updating order status."}), 500

# Add other order endpoints (GET order details, list orders, etc.) later

