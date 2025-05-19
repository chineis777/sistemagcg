# src/routes/user.py

from flask import Blueprint, jsonify, request
from src.models.user import User, UserType, db
from src.models.finance import Wallet # Import Wallet model

# !!! IMPORTANT: Add authentication/authorization checks to all relevant endpoints later !!!
# For MVP prototype, we are omitting complex auth for simplicity.

user_bp = Blueprint("user_auth", __name__) # Renamed blueprint for clarity

@user_bp.route("/register", methods=["POST"])
def register_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    user_type_str = data.get("user_type") # Expecting "Cliente", "Autopeça", or "Admin"
    name = data.get("name")

    if not email or not password or not user_type_str:
        return jsonify({"error": "Email, password, and user_type are required"}), 400

    # Validate user_type
    try:
        user_type = UserType(user_type_str)
    except ValueError:
        return jsonify({"error": f"Invalid user_type: {user_type_str}. Must be one of { [t.value for t in UserType] }"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    try:
        # Create user
        new_user = User(
            email=email,
            user_type=user_type,
            name=name
            # is_approved is False by default, which is correct for Autopeça
        )
        new_user.set_password(password)
        db.session.add(new_user)
        
        # Flush to get the new_user ID before creating the wallet
        db.session.flush()

        # Create a corresponding wallet for the new user
        new_wallet = Wallet(user_id=new_user.id)
        db.session.add(new_wallet)

        # Commit both user and wallet creation
        db.session.commit()

        return jsonify({"message": "User and Wallet registered successfully", "user_id": new_user.id, "user_type": new_user.user_type.value}), 201

    except Exception as e:
        db.session.rollback() # Rollback in case of error
        print(f"Error during registration: {e}") # Log the error server-side
        return jsonify({"error": "An internal error occurred during registration."}), 500


@user_bp.route("/login", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    # Check if Autopeça is approved
    if user.user_type == UserType.AUTOPECA and not user.is_approved:
        return jsonify({"error": "Autopeça account not yet approved"}), 403

    # Basic login success response. Needs JWT later.
    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "user_type": user.user_type.value,
        "name": user.name
        # Consider adding wallet info here if needed immediately after login
    }), 200

# --- Admin Specific Routes ---

@user_bp.route("/admin/pending_autpecas", methods=["GET"])
def get_pending_autpecas():
    # !!! Needs Admin Auth !!!
    pending_users = User.query.filter_by(user_type=UserType.AUTOPECA, is_approved=False).all()
    
    user_list = [
        {"id": user.id, "email": user.email, "name": user.name, "created_at": user.created_at.isoformat()} 
        for user in pending_users
    ]
    return jsonify(user_list), 200

@user_bp.route("/admin/approve_autpeca/<int:user_id>", methods=["PUT"])
def approve_autpeca(user_id):
    # !!! Needs Admin Auth !!!
    user_to_approve = User.query.get_or_404(user_id)

    if user_to_approve.user_type != UserType.AUTOPECA:
        return jsonify({"error": "User is not an Autopeça"}), 400

    if user_to_approve.is_approved:
        return jsonify({"message": "Autopeça already approved"}), 200

    user_to_approve.is_approved = True
    db.session.commit()

    return jsonify({"message": f"Autopeça {user_to_approve.email} approved successfully"}), 200

# --- General User Info (Example - might need auth) ---
@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user_info(user_id):
    # !!! Needs Auth (e.g., user can only get their own info, or admin can get any) !!!
    user = User.query.get_or_404(user_id)
    # Simple dict representation for now
    return jsonify({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "user_type": user.user_type.value,
        "is_approved": user.is_approved,
        "created_at": user.created_at.isoformat()
    }), 200

