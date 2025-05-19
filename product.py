# src/routes/product.py

from flask import Blueprint, jsonify, request
from src.models.product import db, Product, ProductCategory, Manufacturer, ProductBrand, ProductImage, VehicleBrand, VehicleModel, VehicleApplication, KitComponent
import json
import os

product_bp = Blueprint('product', __name__)

# Rotas para produtos
@product_bp.route('/api/products', methods=['GET'])
def get_products():
    """
    Listar produtos com filtros e paginação
    
    Query params:
    - search: termo de busca geral
    - category: ID da categoria
    - manufacturer: ID do fabricante
    - brand: ID da marca da peça
    - vehicle_brand: ID da marca do veículo
    - vehicle_model: ID do modelo do veículo
    - year: ano do veículo
    - engine: detalhes do motor
    - min_price: preço mínimo
    - max_price: preço máximo
    - in_stock_only: apenas produtos em estoque (true/false)
    - page: número da página
    - per_page: itens por página
    - sort_by: campo para ordenação
    """
    # Parâmetros de busca e filtros
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    manufacturer_id = request.args.get('manufacturer', type=int)
    brand_id = request.args.get('brand', type=int)
    vehicle_brand_id = request.args.get('vehicle_brand', type=int)
    vehicle_model_id = request.args.get('vehicle_model', type=int)
    year = request.args.get('year', type=int)
    engine = request.args.get('engine', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock_only = request.args.get('in_stock_only', '').lower() == 'true'
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'name')
    
    # Construir a query base
    query = Product.query
    
    # Aplicar filtros
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) | 
            (Product.code.ilike(f'%{search}%')) | 
            (Product.description.ilike(f'%{search}%')) |
            (Product.manufacturer_code.ilike(f'%{search}%'))
        )
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if manufacturer_id:
        query = query.filter(Product.manufacturer_id == manufacturer_id)
    
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    
    if min_price:
        query = query.filter(Product.sale_price >= min_price)
    
    if max_price:
        query = query.filter(Product.sale_price <= max_price)
    
    if in_stock_only:
        query = query.filter(Product.stock_quantity > 0)
    
    # Filtrar por aplicação de veículo
    if vehicle_brand_id or vehicle_model_id or year or engine:
        query = query.join(VehicleApplication)
        
        if vehicle_model_id:
            query = query.filter(VehicleApplication.vehicle_model_id == vehicle_model_id)
        elif vehicle_brand_id:
            query = query.join(VehicleModel).filter(VehicleModel.vehicle_brand_id == vehicle_brand_id)
        
        if year:
            query = query.filter(
                (VehicleApplication.year_start <= year) & 
                ((VehicleApplication.year_end >= year) | (VehicleApplication.year_end.is_(None)))
            )
        
        if engine:
            query = query.filter(VehicleApplication.engine_details.ilike(f'%{engine}%'))
    
    # Ordenação
    if sort_by == 'price_asc':
        query = query.order_by(Product.sale_price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.sale_price.desc())
    elif sort_by == 'name':
        query = query.order_by(Product.name.asc())
    elif sort_by == 'code':
        query = query.order_by(Product.code.asc())
    
    # Paginação
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Preparar resposta
    result = {
        'total': paginated.total,
        'page': page,
        'per_page': per_page,
        'pages': paginated.pages,
        'products': []
    }
    
    for product in paginated.items:
        # Buscar imagem principal
        primary_image = ProductImage.query.filter_by(product_id=product.id, is_primary=True).first()
        image_url = primary_image.image_url if primary_image else None
        
        # Buscar aplicações de veículos
        applications = []
        for app in product.applications.limit(5).all():  # Limitar para não sobrecarregar
            vehicle_model = VehicleModel.query.get(app.vehicle_model_id)
            vehicle_brand = VehicleBrand.query.get(vehicle_model.vehicle_brand_id) if vehicle_model else None
            
            if vehicle_model and vehicle_brand:
                applications.append({
                    'brand': vehicle_brand.name,
                    'model': vehicle_model.name,
                    'year_start': app.year_start,
                    'year_end': app.year_end,
                    'engine': app.engine_details,
                    'version': app.version_details
                })
        
        # Adicionar produto ao resultado
        result['products'].append({
            'id': product.id,
            'code': product.code,
            'name': product.name,
            'description': product.description,
            'price': float(product.sale_price),
            'stock': product.stock_quantity,
            'image_url': image_url,
            'applications': applications,
            'manufacturer': product.manufacturer.name if product.manufacturer else None,
            'brand': product.brand.name if product.brand else None
        })
    
    return jsonify(result)

@product_bp.route('/api/products/<int:id>', methods=['GET'])
def get_product(id):
    """Obter detalhes de um produto específico"""
    product = Product.query.get_or_404(id)
    
    # Buscar imagens
    images = []
    for img in product.images.all():
        images.append({
            'id': img.id,
            'url': img.image_url,
            'is_primary': img.is_primary
        })
    
    # Buscar aplicações de veículos
    applications = []
    for app in product.applications.all():
        vehicle_model = VehicleModel.query.get(app.vehicle_model_id)
        vehicle_brand = VehicleBrand.query.get(vehicle_model.vehicle_brand_id) if vehicle_model else None
        
        if vehicle_model and vehicle_brand:
            applications.append({
                'id': app.id,
                'brand': vehicle_brand.name,
                'brand_id': vehicle_brand.id,
                'model': vehicle_model.name,
                'model_id': vehicle_model.id,
                'year_start': app.year_start,
                'year_end': app.year_end,
                'engine_details': app.engine_details,
                'version_details': app.version_details,
                'notes': app.notes
            })
    
    # Buscar componentes se for um kit
    components = []
    if product.is_kit:
        for comp in product.kit_components.all():
            component_product = Product.query.get(comp.component_product_id)
            if component_product:
                components.append({
                    'id': component_product.id,
                    'code': component_product.code,
                    'name': component_product.name,
                    'quantity': comp.quantity
                })
    
    # Montar resposta detalhada
    result = {
        'id': product.id,
        'code': product.code,
        'name': product.name,
        'description': product.description,
        'cost_price': float(product.cost_price),
        'sale_price': float(product.sale_price),
        'stock_quantity': product.stock_quantity,
        'category_id': product.category_id,
        'category': product.category.name if product.category else None,
        'manufacturer_id': product.manufacturer_id,
        'manufacturer': product.manufacturer.name if product.manufacturer else None,
        'brand_id': product.brand_id,
        'brand': product.brand.name if product.brand else None,
        'product_line': product.product_line,
        'manufacturer_code': product.manufacturer_code,
        'ean_barcode': product.ean_barcode,
        'unit_of_measure': product.unit_of_measure,
        'status': product.status,
        'is_kit': product.is_kit,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None,
        'images': images,
        'applications': applications,
        'components': components if product.is_kit else None
    }
    
    return jsonify(result)

@product_bp.route('/api/products', methods=['POST'])
def create_product():
    """Criar novo produto"""
    data = request.json
    
    # Validar dados obrigatórios
    if not data.get('code') or not data.get('name') or not data.get('cost_price') or not data.get('sale_price'):
        return jsonify({'error': 'Campos obrigatórios: code, name, cost_price, sale_price'}), 400
    
    # Verificar se código já existe
    existing = Product.query.filter_by(code=data['code']).first()
    if existing:
        return jsonify({'error': f'Código de produto já existe: {data["code"]}'}), 400
    
    # Criar novo produto
    product = Product(
        code=data['code'],
        name=data['name'],
        description=data.get('description'),
        cost_price=data['cost_price'],
        sale_price=data['sale_price'],
        stock_quantity=data.get('stock_quantity', 0),
        category_id=data.get('category_id'),
        manufacturer_id=data.get('manufacturer_id'),
        brand_id=data.get('brand_id'),
        product_line=data.get('product_line'),
        manufacturer_code=data.get('manufacturer_code'),
        ean_barcode=data.get('ean_barcode'),
        unit_of_measure=data.get('unit_of_measure'),
        status=data.get('status', 'active'),
        is_kit=data.get('is_kit', False)
    )
    
    db.session.add(product)
    db.session.commit()
    
    # Processar imagens se fornecidas
    if 'images' in data and isinstance(data['images'], list):
        for img_data in data['images']:
            image = ProductImage(
                product_id=product.id,
                image_url=img_data['url'],
                is_primary=img_data.get('is_primary', False)
            )
            db.session.add(image)
    
    # Processar aplicações de veículos se fornecidas
    if 'applications' in data and isinstance(data['applications'], list):
        for app_data in data['applications']:
            # Verificar se o modelo existe
            vehicle_model_id = app_data.get('vehicle_model_id')
            if not vehicle_model_id:
                # Se não fornecido, tentar encontrar ou criar com base na marca e nome do modelo
                vehicle_brand_id = app_data.get('vehicle_brand_id')
                model_name = app_data.get('model_name')
                
                if vehicle_brand_id and model_name:
                    vehicle_model = VehicleModel.query.filter_by(
                        vehicle_brand_id=vehicle_brand_id, 
                        name=model_name
                    ).first()
                    
                    if not vehicle_model:
                        vehicle_model = VehicleModel(
                            vehicle_brand_id=vehicle_brand_id,
                            name=model_name
                        )
                        db.session.add(vehicle_model)
                        db.session.flush()  # Para obter o ID
                    
                    vehicle_model_id = vehicle_model.id
            
            if vehicle_model_id:
                application = VehicleApplication(
                    product_id=product.id,
                    vehicle_model_id=vehicle_model_id,
                    year_start=app_data.get('year_start'),
                    year_end=app_data.get('year_end'),
                    engine_details=app_data.get('engine_details'),
                    version_details=app_data.get('version_details'),
                    notes=app_data.get('notes')
                )
                db.session.add(application)
    
    # Processar componentes do kit se for um kit
    if product.is_kit and 'components' in data and isinstance(data['components'], list):
        for comp_data in data['components']:
            component = KitComponent(
                kit_product_id=product.id,
                component_product_id=comp_data['product_id'],
                quantity=comp_data.get('quantity', 1)
            )
            db.session.add(component)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Produto criado com sucesso',
        'id': product.id,
        'code': product.code
    }), 201

@product_bp.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    """Atualizar produto existente"""
    product = Product.query.get_or_404(id)
    data = request.json
    
    # Atualizar campos básicos
    if 'code' in data and data['code'] != product.code:
        # Verificar se novo código já existe
        existing = Product.query.filter_by(code=data['code']).first()
        if existing and existing.id != id:
            return jsonify({'error': f'Código de produto já existe: {data["code"]}'}), 400
        product.code = data['code']
    
    if 'name' in data:
        product.name = data['name']
    
    if 'description' in data:
        product.description = data['description']
    
    if 'cost_price' in data:
        product.cost_price = data['cost_price']
    
    if 'sale_price' in data:
        product.sale_price = data['sale_price']
    
    if 'stock_quantity' in data:
        product.stock_quantity = data['stock_quantity']
    
    if 'category_id' in data:
        product.category_id = data['category_id']
    
    if 'manufacturer_id' in data:
        product.manufacturer_id = data['manufacturer_id']
    
    if 'brand_id' in data:
        product.brand_id = data['brand_id']
    
    if 'product_line' in data:
        product.product_line = data['product_line']
    
    if 'manufacturer_code' in data:
        product.manufacturer_code = data['manufacturer_code']
    
    if 'ean_barcode' in data:
        product.ean_barcode = data['ean_barcode']
    
    if 'unit_of_measure' in data:
        product.unit_of_measure = data['unit_of_measure']
    
    if 'status' in data:
        product.status = data['status']
    
    if 'is_kit' in data:
        product.is_kit = data['is_kit']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Produto atualizado com sucesso',
        'id': product.id
    })

@product_bp.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    """Deletar produto"""
    product = Product.query.get_or_404(id)
    
    # Verificar se pode ser excluído (regras de negócio)
    # Por exemplo, verificar se não está em pedidos ativos
    
    # Excluir relacionamentos
    ProductImage.query.filter_by(product_id=id).delete()
    VehicleApplication.query.filter_by(product_id=id).delete()
    KitComponent.query.filter_by(kit_product_id=id).delete()
    KitComponent.query.filter_by(component_product_id=id).delete()
    
    # Excluir produto
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({
        'message': 'Produto excluído com sucesso'
    })

# Rota para adicionar imagem a um produto
@product_bp.route('/api/products/<int:id>/images', methods=['POST'])
def add_product_image(id):
    """Adicionar imagem a um produto"""
    product = Product.query.get_or_404(id)
    data = request.json
    
    if not data.get('image_url'):
        return jsonify({'error': 'URL da imagem é obrigatória'}), 400
    
    # Se marcada como primária, desmarcar outras
    if data.get('is_primary', False):
        ProductImage.query.filter_by(product_id=id, is_primary=True).update({'is_primary': False})
    
    image = ProductImage(
        product_id=id,
        image_url=data['image_url'],
        is_primary=data.get('is_primary', False)
    )
    
    db.session.add(image)
    db.session.commit()
    
    return jsonify({
        'message': 'Imagem adicionada com sucesso',
        'id': image.id
    }), 201

# Rota para adicionar aplicação de veículo a um produto
@product_bp.route('/api/products/<int:id>/applications', methods=['POST'])
def add_product_application(id):
    """Adicionar aplicação de veículo a um produto"""
    product = Product.query.get_or_404(id)
    data = request.json
    
    # Verificar se o modelo existe
    vehicle_model_id = data.get('vehicle_model_id')
    if not vehicle_model_id:
        # Se não fornecido, tentar encontrar ou criar com base na marca e nome do modelo
        vehicle_brand_id = data.get('vehicle_brand_id')
        model_name = data.get('model_name')
        
        if not vehicle_brand_id or not model_name:
            return jsonify({'error': 'vehicle_model_id ou (vehicle_brand_id e model_name) são obrigatórios'}), 400
        
        vehicle_model = VehicleModel.query.filter_by(
            vehicle_brand_id=vehicle_brand_id, 
            name=model_name
        ).first()
        
        if not vehicle_model:
            vehicle_model = VehicleModel(
                vehicle_brand_id=vehicle_brand_id,
                name=model_name
            )
            db.session.add(vehicle_model)
            db.session.flush()  # Para obter o ID
        
        vehicle_model_id = vehicle_model.id
    
    # Verificar se aplicação já existe
    existing = VehicleApplication.query.filter_by(
        product_id=id,
        vehicle_model_id=vehicle_model_id,
        year_start=data.get('year_start'),
        year_end=data.get('year_end')
    ).first()
    
    if existing:
        return jsonify({'error': 'Esta aplicação já existe para este produto'}), 400
    
    application = VehicleApplication(
        product_id=id,
        vehicle_model_id=vehicle_model_id,
        year_start=data.get('year_start'),
        year_end=data.get('year_end'),
        engine_details=data.get('engine_details'),
        version_details=data.get('version_details'),
        notes=data.get('notes')
    )
    
    db.session.add(application)
    db.session.commit()
    
    return jsonify({
        'message': 'Aplicação adicionada com sucesso',
        'id': application.id
    }), 201

# Rotas para categorias
@product_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """Listar categorias"""
    categories = ProductCategory.query.all()
    result = []
    
    for category in categories:
        result.append({
            'id': category.id,
            'name': category.name,
            'parent_id': category.parent_category_id
        })
    
    return jsonify(result)

@product_bp.route('/api/categories', methods=['POST'])
def create_category():
    """Criar categoria"""
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Nome da categoria é obrigatório'}), 400
    
    # Verificar se já existe
    existing = ProductCategory.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': f'Categoria já existe: {data["name"]}'}), 400
    
    category = ProductCategory(
        name=data['name'],
        parent_category_id=data.get('parent_id')
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'message': 'Categoria criada com sucesso',
        'id': category.id
    }), 201

# Rotas para fabricantes
@product_bp.route('/api/manufacturers', methods=['GET'])
def get_manufacturers():
    """Listar fabricantes"""
    manufacturers = Manufacturer.query.all()
    result = []
    
    for manufacturer in manufacturers:
        result.append({
            'id': manufacturer.id,
            'name': manufacturer.name
        })
    
    return jsonify(result)

@product_bp.route('/api/manufacturers', methods=['POST'])
def create_manufacturer():
    """Criar fabricante"""
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Nome do fabricante é obrigatório'}), 400
    
    # Verificar se já existe
    existing = Manufacturer.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': f'Fabricante já existe: {data["name"]}'}), 400
    
    manufacturer = Manufacturer(name=data['name'])
    
    db.session.add(manufacturer)
    db.session.commit()
    
    return jsonify({
        'message': 'Fabricante criado com sucesso',
        'id': manufacturer.id
    }), 201

# Rotas para marcas de peças
@product_bp.route('/api/product_brands', methods=['GET'])
def get_product_brands():
    """Listar marcas de peças"""
    brands = ProductBrand.query.all()
    result = []
    
    for brand in brands:
        result.append({
            'id': brand.id,
            'name': brand.name
        })
    
    return jsonify(result)

@product_bp.route('/api/product_brands', methods=['POST'])
def create_product_brand():
    """Criar marca de peça"""
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Nome da marca é obrigatório'}), 400
    
    # Verificar se já existe
    existing = ProductBrand.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': f'Marca já existe: {data["name"]}'}), 400
    
    brand = ProductBrand(name=data['name'])
    
    db.session.add(brand)
    db.session.commit()
    
    return jsonify({
        'message': 'Marca criada com sucesso',
        'id': brand.id
    }), 201

# Rotas para marcas de veículos
@product_bp.route('/api/vehicle_brands', methods=['GET'])
def get_vehicle_brands():
    """Listar marcas de veículos"""
    brands = VehicleBrand.query.all()
    result = []
    
    for brand in brands:
        result.append({
            'id': brand.id,
            'name': brand.name
        })
    
    return jsonify(result)

@product_bp.route('/api/vehicle_brands/<int:brand_id>/models', methods=['GET'])
def get_vehicle_models(brand_id):
    """Listar modelos de uma marca de veículo"""
    models = VehicleModel.query.filter_by(vehicle_brand_id=brand_id).all()
    result = []
    
    for model in models:
        result.append({
            'id': model.id,
            'name': model.name,
            'brand_id': model.vehicle_brand_id
        })
    
    return jsonify(result)

# Rota para importar aplicações de veículos de arquivos JSON
@product_bp.route('/api/import/vehicle_applications', methods=['POST'])
def import_vehicle_applications():
    """Importar aplicações de veículos de arquivos JSON"""
    data_dir = '/home/ubuntu/catalogo_data'
    
    if not os.path.exists(data_dir):
        return jsonify({'error': 'Diretório de dados não encontrado'}), 404
    
    # Contadores para relatório
    stats = {
        'processed_files': 0,
        'processed_products': 0,
        'created_applications': 0,
        'errors': 0
    }
    
    # Processar arquivos JSON no diretório
    for filename in os.listdir(data_dir):
        if filename.endswith('.json') and 'aplicacoes' in filename:
            stats['processed_files'] += 1
            file_path = os.path.join(data_dir, filename)
            
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                
                # Processar aplicações
                if 'aplicacoes_veiculos' in data:
                    for item in data['aplicacoes_veiculos']:
                        # Buscar produto pelo código
                        product = Product.query.filter_by(code=item['codigo_filtro']).first()
                        
                        if not product:
                            # Produto não encontrado, pular
                            stats['errors'] += 1
                            continue
                        
                        stats['processed_products'] += 1
                        
                        # Processar aplicações para este produto
                        for aplicacao in item['aplicacoes']:
                            marca = aplicacao['marca']
                            
                            # Buscar ou criar marca de veículo
                            vehicle_brand = VehicleBrand.query.filter_by(name=marca).first()
                            if not vehicle_brand:
                                vehicle_brand = VehicleBrand(name=marca)
                                db.session.add(vehicle_brand)
                                db.session.flush()
                            
                            # Processar modelos
                            for modelo in aplicacao['modelos']:
                                nome_modelo = modelo['nome']
                                
                                # Buscar ou criar modelo de veículo
                                vehicle_model = VehicleModel.query.filter_by(
                                    vehicle_brand_id=vehicle_brand.id,
                                    name=nome_modelo
                                ).first()
                                
                                if not vehicle_model:
                                    vehicle_model = VehicleModel(
                                        vehicle_brand_id=vehicle_brand.id,
                                        name=nome_modelo
                                    )
                                    db.session.add(vehicle_model)
                                    db.session.flush()
                                
                                # Determinar anos
                                anos = modelo.get('anos', '')
                                year_start = None
                                year_end = None
                                
                                if anos and anos != 'TODOS':
                                    # Tentar extrair anos do formato "YYYY-YYYY" ou "YYYY-ATUAL"
                                    anos_parts = anos.split('-')
                                    if len(anos_parts) == 2:
                                        try:
                                            year_start = int(anos_parts[0])
                                            if anos_parts[1].lower() not in ['atual', 'present']:
                                                year_end = int(anos_parts[1])
                                        except ValueError:
                                            pass
                                
                                # Criar aplicação para cada versão
                                versoes = modelo.get('versoes', ['TODOS OS MOTORES'])
                                for versao in versoes:
                                    # Verificar se aplicação já existe
                                    existing = VehicleApplication.query.filter_by(
                                        product_id=product.id,
                                        vehicle_model_id=vehicle_model.id,
                                        year_start=year_start,
                                        year_end=year_end,
                                        version_details=versao
                                    ).first()
                                    
                                    if not existing:
                                        application = VehicleApplication(
                                            product_id=product.id,
                                            vehicle_model_id=vehicle_model.id,
                                            year_start=year_start,
                                            year_end=year_end,
                                            engine_details=versao if 'MOTOR' in versao else None,
                                            version_details=versao
                                        )
                                        db.session.add(application)
                                        stats['created_applications'] += 1
                
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                stats['errors'] += 1
                print(f"Erro ao processar arquivo {filename}: {str(e)}")
    
    return jsonify({
        'message': 'Importação concluída',
        'stats': stats
    })

# Rota para integração com o Painel do Mecânico
@product_bp.route('/api/mechanic/products_for_quote', methods=['GET'])
def get_products_for_quote():
    """
    Buscar produtos para adicionar a orçamentos no Painel do Mecânico
    
    Query params:
    - search: termo de busca (código, descrição)
    - vehicle_brand: marca do veículo
    - vehicle_model: modelo do veículo
    - vehicle_year: ano do veículo
    - page: número da página
    - per_page: itens por página
    """
    search = request.args.get('search', '')
    vehicle_brand = request.args.get('vehicle_brand', '')
    vehicle_model = request.args.get('vehicle_model', '')
    vehicle_year = request.args.get('vehicle_year', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Construir a query base
    query = Product.query.filter(Product.status == 'active')
    
    # Aplicar filtros
    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) | 
            (Product.code.ilike(f'%{search}%')) | 
            (Product.description.ilike(f'%{search}%')) |
            (Product.manufacturer_code.ilike(f'%{search}%'))
        )
    
    # Filtrar por aplicação de veículo
    if vehicle_brand or vehicle_model or vehicle_year:
        query = query.join(VehicleApplication).join(VehicleModel).join(VehicleBrand)
        
        if vehicle_brand:
            query = query.filter(VehicleBrand.name.ilike(f'%{vehicle_brand}%'))
        
        if vehicle_model:
            query = query.filter(VehicleModel.name.ilike(f'%{vehicle_model}%'))
        
        if vehicle_year:
            query = query.filter(
                (VehicleApplication.year_start <= vehicle_year) & 
                ((VehicleApplication.year_end >= vehicle_year) | (VehicleApplication.year_end.is_(None)))
            )
    
    # Paginação
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Preparar resposta
    result = {
        'total': paginated.total,
        'page': page,
        'per_page': per_page,
        'pages': paginated.pages,
        'products': []
    }
    
    for product in paginated.items:
        # Buscar aplicações de veículos
        applications = []
        for app in product.applications.limit(5).all():
            vehicle_model = VehicleModel.query.get(app.vehicle_model_id)
            vehicle_brand = VehicleBrand.query.get(vehicle_model.vehicle_brand_id) if vehicle_model else None
            
            if vehicle_model and vehicle_brand:
                year_info = ""
                if app.year_start and app.year_end:
                    year_info = f"{app.year_start}-{app.year_end}"
                elif app.year_start:
                    year_info = f"{app.year_start}-atual"
                
                applications.append(f"{vehicle_brand.name} {vehicle_model.name} {year_info} {app.version_details or ''}")
        
        # Adicionar produto ao resultado
        result['products'].append({
            'id': product.id,
            'code': product.code,
            'name': product.name,
            'description': product.description,
            'price': float(product.sale_price),
            'stock': product.stock_quantity,
            'manufacturer': product.manufacturer.name if product.manufacturer else None,
            'applications_summary': applications[:3],  # Limitar a 3 aplicações para resumo
            'has_more_applications': len(applications) > 3
        })
    
    return jsonify(result)

# Registrar o blueprint na aplicação principal
# Em main.py:
# from src.routes.product import product_bp
# app.register_blueprint(product_bp)
