# src/routes/mechanic.py

from flask import Blueprint, request, jsonify
from ..models import db # Supondo que db seja inicializado em main.py ou __init__.py dos models
from ..models.user import User
from ..models.mechanic import VehicleChecklist, Quote, QuoteItem
from ..models.product import Product # Supondo que Product esteja em models.product
from datetime import datetime, timedelta

# Supondo a existência de um decorator para autenticação e verificação de papel
# Exemplo: from ..utils.decorators import token_required, mechanic_required
# Por enquanto, vamos simular a obtenção do mechanic_id
def get_current_mechanic_id():
    # Em um sistema real, isso viria do token JWT ou sessão
    # Para testes iniciais, vamos assumir que o usuário com email "mecanico@test.com" é o mecânico.
    # Esta parte precisará ser integrada com o sistema de autenticação real.
    # Busque por um usuário que seja mecânico para testes. Se não existir, crie um no DB.
    user = User.query.filter_by(user_type="Mecanico").first() 
    if user:
        return user.id
    # Fallback para um ID de mecânico de teste, se nenhum mecânico for encontrado.
    # Idealmente, a aplicação não deveria rodar sem um mecânico de teste se esta função for usada.
    print("AVISO: Nenhum usuário do tipo Mecanico encontrado no banco. Usando ID de fallback 1.")
    print("Considere criar um usuário mecânico para testes.")
    return 1 

mechanic_bp = Blueprint("mechanic_api", __name__, url_prefix="/api/mechanic")

# --- Checklist Routes ---
@mechanic_bp.route("/checklists", methods=["POST"])
# @token_required
# @mechanic_required
def create_checklist():
    data = request.get_json()
    mechanic_id = get_current_mechanic_id()
    customer_id = data.get("customer_id")

    if not all([data.get("plate_number"), customer_id]):
        return jsonify({"error": "Placa e ID do cliente são obrigatórios"}), 400
    
    # Validação simples se o cliente existe
    customer = User.query.get(customer_id)
    if not customer:
        return jsonify({"error": f"Cliente com ID {customer_id} não encontrado."}), 404

    try:
        new_checklist = VehicleChecklist(
            plate_number=data["plate_number"],
            brand=data.get("brand"),
            model=data.get("model"),
            year=data.get("year"),
            color=data.get("color"),
            customer_id=customer_id,
            mechanic_id=mechanic_id,
            fuel_level=data.get("fuel_level"),
            current_km=data.get("current_km"),
            customer_notes=data.get("customer_notes"),
            inspection_items=data.get("inspection_items", {}),
            customer_belongings=data.get("customer_belongings"),
            status=data.get("status", "Aberto")
        )
        db.session.add(new_checklist)
        db.session.commit()
        return jsonify({"message": "Checklist criado com sucesso", "checklist_id": new_checklist.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@mechanic_bp.route("/checklists", methods=["GET"])
# @token_required
# @mechanic_required
def get_checklists():
    mechanic_id = get_current_mechanic_id()
    checklists = VehicleChecklist.query.filter_by(mechanic_id=mechanic_id).order_by(VehicleChecklist.entry_datetime.desc()).all()
    output = []
    for checklist in checklists:
        output.append({
            "id": checklist.id,
            "plate_number": checklist.plate_number,
            "customer_id": checklist.customer_id,
            "entry_datetime": checklist.entry_datetime.isoformat() if checklist.entry_datetime else None,
            "status": checklist.status
        })
    return jsonify(output), 200

@mechanic_bp.route("/checklists/<int:checklist_id>", methods=["GET"])
# @token_required
# @mechanic_required
def get_checklist_detail(checklist_id):
    mechanic_id = get_current_mechanic_id()
    checklist = VehicleChecklist.query.filter_by(id=checklist_id, mechanic_id=mechanic_id).first()
    if not checklist:
        return jsonify({"error": "Checklist não encontrado ou não pertence a este mecânico"}), 404
    
    return jsonify({
        "id": checklist.id,
        "plate_number": checklist.plate_number,
        "brand": checklist.brand,
        "model": checklist.model,
        "year": checklist.year,
        "color": checklist.color,
        "customer_id": checklist.customer_id,
        "mechanic_id": checklist.mechanic_id,
        "entry_datetime": checklist.entry_datetime.isoformat() if checklist.entry_datetime else None,
        "fuel_level": checklist.fuel_level,
        "current_km": checklist.current_km,
        "customer_notes": checklist.customer_notes,
        "inspection_items": checklist.inspection_items,
        "customer_belongings": checklist.customer_belongings,
        "status": checklist.status
    }), 200

@mechanic_bp.route("/checklists/<int:checklist_id>", methods=["PUT"])
# @token_required
# @mechanic_required
def update_checklist(checklist_id):
    data = request.get_json()
    mechanic_id = get_current_mechanic_id()
    checklist = VehicleChecklist.query.filter_by(id=checklist_id, mechanic_id=mechanic_id).first()

    if not checklist:
        return jsonify({"error": "Checklist não encontrado ou não pertence a este mecânico"}), 404

    try:
        checklist.plate_number = data.get("plate_number", checklist.plate_number)
        checklist.brand = data.get("brand", checklist.brand)
        checklist.model = data.get("model", checklist.model)
        checklist.year = data.get("year", checklist.year)
        checklist.color = data.get("color", checklist.color)
        checklist.fuel_level = data.get("fuel_level", checklist.fuel_level)
        checklist.current_km = data.get("current_km", checklist.current_km)
        checklist.customer_notes = data.get("customer_notes", checklist.customer_notes)
        checklist.inspection_items = data.get("inspection_items", checklist.inspection_items)
        checklist.customer_belongings = data.get("customer_belongings", checklist.customer_belongings)
        checklist.status = data.get("status", checklist.status)
        
        db.session.commit()
        return jsonify({"message": "Checklist atualizado com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Quote Routes ---
@mechanic_bp.route("/quotes", methods=["POST"])
# @token_required
# @mechanic_required
def create_quote():
    data = request.get_json()
    mechanic_id = get_current_mechanic_id()
    customer_id = data.get("customer_id")
    
    if not customer_id:
        return jsonify({"error": "ID do cliente é obrigatório"}), 400

    customer = User.query.get(customer_id)
    if not customer:
        return jsonify({"error": f"Cliente com ID {customer_id} não encontrado."}), 404

    try:
        new_quote = Quote(
            checklist_id=data.get("checklist_id"),
            plate_number_if_no_checklist=data.get("plate_number_if_no_checklist"),
            customer_id=customer_id,
            mechanic_id=mechanic_id,
            expiry_date=datetime.utcnow() + timedelta(days=data.get("validity_days", 7)), # Default 7 dias de validade
            observations=data.get("observations"),
            status=data.get("status", "Pendente Aprovação Cliente")
        )

        items_data = data.get("items", [])
        for item_data in items_data:
            if not item_data.get("description") or item_data.get("unit_price") is None:
                return jsonify({"error": "Descrição e preço unitário são obrigatórios para cada item."}), 400
            
            new_item = QuoteItem(
                item_type=item_data.get("item_type", "part"), # part ou labor
                product_id=item_data.get("product_id"),
                description=item_data["description"],
                quantity=item_data.get("quantity", 1),
                unit_price=item_data["unit_price"],
                subject_to_change_after_disassembly=item_data.get("subject_to_change_after_disassembly", False)
            )
            new_item.calculate_subtotal() # Calcula o subtotal do item
            new_quote.items.append(new_item)
        
        new_quote.update_totals() # Calcula os totais do orçamento
        
        db.session.add(new_quote)
        db.session.commit()
        return jsonify({"message": "Orçamento criado com sucesso", "quote_id": new_quote.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@mechanic_bp.route("/quotes", methods=["GET"])
# @token_required
# @mechanic_required
def get_quotes():
    mechanic_id = get_current_mechanic_id()
    quotes = Quote.query.filter_by(mechanic_id=mechanic_id).order_by(Quote.quote_date.desc()).all()
    output = []
    for quote in quotes:
        output.append({
            "id": quote.id,
            "customer_id": quote.customer_id,
            "quote_date": quote.quote_date.isoformat() if quote.quote_date else None,
            "total_quote_value": float(quote.total_quote_value) if quote.total_quote_value else 0.0,
            "status": quote.status
        })
    return jsonify(output), 200

@mechanic_bp.route("/quotes/<int:quote_id>", methods=["GET"])
# @token_required
# @mechanic_required
def get_quote_detail(quote_id):
    mechanic_id = get_current_mechanic_id()
    quote = Quote.query.filter_by(id=quote_id, mechanic_id=mechanic_id).first()
    if not quote:
        return jsonify({"error": "Orçamento não encontrado ou não pertence a este mecânico"}), 404

    items_output = []
    for item in quote.items:
        items_output.append({
            "id": item.id,
            "item_type": item.item_type,
            "product_id": item.product_id,
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price) if item.unit_price else 0.0,
            "subtotal": float(item.subtotal) if item.subtotal else 0.0,
            "subject_to_change_after_disassembly": item.subject_to_change_after_disassembly
        })

    return jsonify({
        "id": quote.id,
        "checklist_id": quote.checklist_id,
        "plate_number_if_no_checklist": quote.plate_number_if_no_checklist,
        "customer_id": quote.customer_id,
        "mechanic_id": quote.mechanic_id,
        "quote_date": quote.quote_date.isoformat() if quote.quote_date else None,
        "expiry_date": quote.expiry_date.isoformat() if quote.expiry_date else None,
        "total_parts_value": float(quote.total_parts_value) if quote.total_parts_value else 0.0,
        "total_labor_value": float(quote.total_labor_value) if quote.total_labor_value else 0.0,
        "discount_value": float(quote.discount_value) if quote.discount_value else 0.0,
        "total_quote_value": float(quote.total_quote_value) if quote.total_quote_value else 0.0,
        "observations": quote.observations,
        "status": quote.status,
        "sent_to_customer_datetime": quote.sent_to_customer_datetime.isoformat() if quote.sent_to_customer_datetime else None,
        "items": items_output
    }), 200

@mechanic_bp.route("/quotes/<int:quote_id>", methods=["PUT"])
# @token_required
# @mechanic_required
def update_quote(quote_id):
    data = request.get_json()
    mechanic_id = get_current_mechanic_id()
    quote = Quote.query.filter_by(id=quote_id, mechanic_id=mechanic_id).first()

    if not quote:
        return jsonify({"error": "Orçamento não encontrado ou não pertence a este mecânico"}), 404

    try:
        # Atualizar campos do orçamento
        quote.checklist_id = data.get("checklist_id", quote.checklist_id)
        quote.plate_number_if_no_checklist = data.get("plate_number_if_no_checklist", quote.plate_number_if_no_checklist)
        # customer_id e mechanic_id geralmente não mudam
        if data.get("expiry_date"): # Espera data no formato YYYY-MM-DD
            quote.expiry_date = datetime.strptime(data.get("expiry_date"), "%Y-%m-%d").date()
        quote.observations = data.get("observations", quote.observations)
        quote.status = data.get("status", quote.status)
        quote.discount_value = data.get("discount_value", quote.discount_value)

        # Atualizar itens (complexo: pode adicionar, remover, atualizar itens existentes)
        # Para simplificar no MVP, vamos permitir apenas a atualização da lista inteira de itens.
        # Uma abordagem mais robusta envolveria identificar itens por ID para update/delete.
        items_data = data.get("items")
        if items_data is not None: # Se a lista de itens for fornecida, substitui todos os itens
            # Remover itens antigos
            for old_item in quote.items:
                db.session.delete(old_item)
            # Adicionar novos itens
            for item_data in items_data:
                if not item_data.get("description") or item_data.get("unit_price") is None:
                    return jsonify({"error": "Descrição e preço unitário são obrigatórios para cada item."}), 400
                new_item = QuoteItem(
                    item_type=item_data.get("item_type", "part"),
                    product_id=item_data.get("product_id"),
                    description=item_data["description"],
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data["unit_price"],
                    subject_to_change_after_disassembly=item_data.get("subject_to_change_after_disassembly", False)
                )
                new_item.calculate_subtotal()
                quote.items.append(new_item)
        
        quote.update_totals()
        db.session.commit()
        return jsonify({"message": "Orçamento atualizado com sucesso"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@mechanic_bp.route("/quotes/<int:quote_id>/send_to_customer", methods=["POST"])
# @token_required
# @mechanic_required
def send_quote_to_customer(quote_id):
    mechanic_id = get_current_mechanic_id()
    quote = Quote.query.filter_by(id=quote_id, mechanic_id=mechanic_id).first()

    if not quote:
        return jsonify({"error": "Orçamento não encontrado ou não pertence a este mecânico"}), 404

    try:
        quote.sent_to_customer_datetime = datetime.utcnow()
        # Aqui poderia ter lógica para enviar email/notificação para o cliente
        # Ex: send_email_notification(quote.customer.email, "Seu orçamento está pronto!", quote_details_html)
        db.session.commit()
        return jsonify({"message": "Orçamento marcado como enviado ao cliente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Product Search for Quote (Placeholder) ---
@mechanic_bp.route("/products_for_quote", methods=["GET"])
# @token_required
# @mechanic_required
def search_products_for_quote():
    query_term = request.args.get("query", "")
    # Lógica para buscar produtos no catálogo. 
    # Supondo que temos um modelo Product e queremos buscar por nome ou código.
    if not query_term:
        return jsonify([]), 200 # Retorna lista vazia se não houver query
        
    products = Product.query.filter(
        (Product.name.ilike(f"%{query_term}%")) |
        (Product.code.ilike(f"%{query_term}%"))
    ).limit(10).all() # Limita a 10 resultados para performance
    
    output = []
    for prod in products:
        output.append({
            "id": prod.id,
            "name": prod.name,
            "code": prod.code,
            "price": float(prod.price) if prod.price else 0.0, # Preço de venda para o orçamento
            "stock": prod.stock_quantity
        })
    return jsonify(output), 200

# --- Commission and Wallet Routes (Placeholders - a serem integradas com o módulo financeiro) ---
@mechanic_bp.route("/commissions", methods=["GET"])
# @token_required
# @mechanic_required
def get_commissions():
    # Lógica para buscar comissões na carteira do mecânico
    # Isso dependerá de como as transações de comissão são registradas no módulo financeiro
    return jsonify([{"message": "Endpoint de comissões a ser implementado"}]), 200

@mechanic_bp.route("/wallet", methods=["GET"])
# @token_required
# @mechanic_required
def get_mechanic_wallet():
    # Lógica para buscar dados da carteira do mecânico no módulo financeiro
    mechanic_id = get_current_mechanic_id()
    # Exemplo: wallet = Wallet.query.filter_by(user_id=mechanic_id).first()
    return jsonify([{"message": "Endpoint da carteira do mecânico a ser implementado"}]), 200

# --- Service History Routes (Placeholder) ---
@mechanic_bp.route("/service_history", methods=["GET"])
# @token_required
# @mechanic_required
def get_service_history():
    mechanic_id = get_current_mechanic_id()
    # Similar a get_quotes, mas filtrando por status como "Serviço Concluído"
    completed_quotes = Quote.query.filter_by(mechanic_id=mechanic_id, status="Serviço Concluído").order_by(Quote.quote_date.desc()).all()
    output = []
    for quote in completed_quotes:
        output.append({
            "id": quote.id,
            "customer_id": quote.customer_id,
            "quote_date": quote.quote_date.isoformat() if quote.quote_date else None,
            "total_quote_value": float(quote.total_quote_value) if quote.total_quote_value else 0.0,
            "status": quote.status
        })
    return jsonify(output), 200

# --- AI Diagnostics Routes (Placeholder) ---
@mechanic_bp.route("/diagnostics/suggest_parts", methods=["POST"])
# @token_required
# @mechanic_required
def suggest_parts_diagnostics():
    data = request.get_json()
    symptoms = data.get("symptoms_description")
    # Lógica da IA (MVP: regras simples)
    suggestions = {"suggested_parts": [], "possible_issues": []}
    if symptoms:
        if "barulho na suspensão" in symptoms.lower():
            suggestions["suggested_parts"].extend(["Amortecedor", "Bieleta", "Pivô"])
            suggestions["possible_issues"].append("Problemas na suspensão dianteira")
        if "carro falhando" in symptoms.lower():
            suggestions["suggested_parts"].extend(["Velas de ignição", "Cabos de vela", "Bomba de combustível"])
            suggestions["possible_issues"].append("Problemas no sistema de ignição ou combustível")
    
    return jsonify(suggestions), 200


# É necessário registrar este blueprint na aplicação Flask principal (main.py)
# from .routes.mechanic import mechanic_bp
# app.register_blueprint(mechanic_bp)

