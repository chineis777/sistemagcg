"""
Configuração do banco de dados MySQL para o sistema Luxnox
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash
import datetime

# Inicialização do SQLAlchemy
db = SQLAlchemy()
migrate = Migrate()

def init_app(app):
    """Inicializa a conexão com o banco de dados"""
    # Configuração do banco de dados
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://luxnox_user:luxnox_password@localhost/luxnox_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializa o SQLAlchemy com a aplicação
    db.init_app(app)
    migrate.init_app(app, db)
    
    return db

# Modelos do banco de dados
class User(db.Model):
    """Modelo para usuários do sistema"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.Enum('admin', 'mechanic', 'client', 'seller', 'autopart', 'delivery'), nullable=False)
    document = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    wallet = db.relationship('Wallet', backref='user', uselist=False)
    preferences = db.relationship('UserPreference', backref='user')
    
    def set_password(self, password):
        """Define a senha do usuário"""
        self.password_hash = generate_password_hash(password)
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'user_type': self.user_type,
            'document': self.document,
            'phone': self.phone,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'active': self.active
        }

class Product(db.Model):
    """Modelo para produtos"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(100))
    category = db.Column(db.String(100))
    cost_price = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    min_stock_quantity = db.Column(db.Integer, default=5)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    applications = db.relationship('ProductApplication', backref='product')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'manufacturer': self.manufacturer,
            'category': self.category,
            'cost_price': float(self.cost_price),
            'selling_price': float(self.selling_price),
            'stock_quantity': self.stock_quantity,
            'min_stock_quantity': self.min_stock_quantity,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'active': self.active
        }

class Vehicle(db.Model):
    """Modelo para veículos"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    version = db.Column(db.String(100))
    engine = db.Column(db.String(50))
    transmission = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamentos
    applications = db.relationship('ProductApplication', backref='vehicle')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'version': self.version,
            'engine': self.engine,
            'transmission': self.transmission
        }

class ProductApplication(db.Model):
    """Modelo para aplicações de produtos em veículos"""
    __tablename__ = 'product_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('product_id', 'vehicle_id', name='unique_application'),
    )
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'vehicle_id': self.vehicle_id,
            'notes': self.notes,
            'vehicle': self.vehicle.to_dict() if self.vehicle else None
        }

class Checklist(db.Model):
    """Modelo para checklists de veículos"""
    __tablename__ = 'checklists'
    
    id = db.Column(db.Integer, primary_key=True)
    mechanic_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    plate = db.Column(db.String(20))
    mileage = db.Column(db.Integer)
    notes = db.Column(db.Text)
    status = db.Column(db.Enum('open', 'in_progress', 'completed', 'canceled'), default='open')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamentos
    mechanic = db.relationship('User', foreign_keys=[mechanic_id])
    client = db.relationship('User', foreign_keys=[client_id])
    vehicle = db.relationship('Vehicle')
    items = db.relationship('ChecklistItem', backref='checklist')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'mechanic_id': self.mechanic_id,
            'client_id': self.client_id,
            'vehicle_id': self.vehicle_id,
            'plate': self.plate,
            'mileage': self.mileage,
            'notes': self.notes,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'mechanic': self.mechanic.to_dict() if self.mechanic else None,
            'client': self.client.to_dict() if self.client else None,
            'vehicle': self.vehicle.to_dict() if self.vehicle else None,
            'items': [item.to_dict() for item in self.items]
        }

class ChecklistItem(db.Model):
    """Modelo para itens do checklist"""
    __tablename__ = 'checklist_items'
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklists.id'), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('ok', 'attention', 'critical', 'not_checked'), default='not_checked')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'checklist_id': self.checklist_id,
            'item_name': self.item_name,
            'status': self.status,
            'notes': self.notes
        }

class Quote(db.Model):
    """Modelo para orçamentos"""
    __tablename__ = 'quotes'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(20), unique=True, nullable=False)
    mechanic_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False)
    checklist_id = db.Column(db.Integer, db.ForeignKey('checklists.id'))
    total_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    labor_cost = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.Enum('draft', 'pending', 'approved', 'rejected', 'completed', 'canceled'), default='draft')
    notes = db.Column(db.Text)
    valid_until = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamentos
    mechanic = db.relationship('User', foreign_keys=[mechanic_id])
    client = db.relationship('User', foreign_keys=[client_id])
    vehicle = db.relationship('Vehicle')
    checklist = db.relationship('Checklist')
    items = db.relationship('QuoteItem', backref='quote')
    commissions = db.relationship('Commission', backref='quote')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'quote_number': self.quote_number,
            'mechanic_id': self.mechanic_id,
            'client_id': self.client_id,
            'vehicle_id': self.vehicle_id,
            'checklist_id': self.checklist_id,
            'total_amount': float(self.total_amount),
            'labor_cost': float(self.labor_cost),
            'discount': float(self.discount),
            'status': self.status,
            'notes': self.notes,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'mechanic': self.mechanic.to_dict() if self.mechanic else None,
            'client': self.client.to_dict() if self.client else None,
            'vehicle': self.vehicle.to_dict() if self.vehicle else None,
            'items': [item.to_dict() for item in self.items]
        }

class QuoteItem(db.Model):
    """Modelo para itens do orçamento"""
    __tablename__ = 'quote_items'
    
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), default=0)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    is_labor = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relacionamentos
    product = db.relationship('Product')
    commissions = db.relationship('Commission', backref='quote_item')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'quote_id': self.quote_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'discount': float(self.discount),
            'total_price': float(self.total_price),
            'notes': self.notes,
            'is_labor': self.is_labor,
            'product': self.product.to_dict() if self.product else None
        }

class Wallet(db.Model):
    """Modelo para carteiras"""
    __tablename__ = 'wallets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    balance = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamentos
    transactions = db.relationship('WalletTransaction', backref='wallet')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'balance': float(self.balance),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class WalletTransaction(db.Model):
    """Modelo para transações da carteira"""
    __tablename__ = 'wallet_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.Enum('deposit', 'withdrawal', 'commission', 'payment', 'refund'), nullable=False)
    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.Enum('pending', 'completed', 'failed', 'canceled'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'wallet_id': self.wallet_id,
            'amount': float(self.amount),
            'type': self.type,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Commission(db.Model):
    """Modelo para comissões"""
    __tablename__ = 'commissions'
    
    id = db.Column(db.Integer, primary_key=True)
    mechanic_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    quote_item_id = db.Column(db.Integer, db.ForeignKey('quote_items.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'paid', 'canceled'), default='pending')
    wallet_transaction_id = db.Column(db.Integer, db.ForeignKey('wallet_transactions.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relacionamentos
    mechanic = db.relationship('User')
    wallet_transaction = db.relationship('WalletTransaction')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'mechanic_id': self.mechanic_id,
            'quote_id': self.quote_id,
            'quote_item_id': self.quote_item_id,
            'amount': float(self.amount),
            'percentage': float(self.percentage),
            'status': self.status,
            'wallet_transaction_id': self.wallet_transaction_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'mechanic': self.mechanic.to_dict() if self.mechanic else None
        }

class AILog(db.Model):
    """Modelo para logs de IA"""
    __tablename__ = 'ai_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action_type = db.Column(db.String(50), nullable=False)
    data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relacionamentos
    user = db.relationship('User')
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action_type': self.action_type,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UserPreference(db.Model):
    """Modelo para preferências de usuário"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    preference_key = db.Column(db.String(100), nullable=False)
    preference_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'preference_key', name='unique_user_preference'),
    )
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preference_key': self.preference_key,
            'preference_value': self.preference_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

def create_tables(app):
    """Cria as tabelas no banco de dados"""
    with app.app_context():
        db.create_all()

def drop_tables(app):
    """Remove as tabelas do banco de dados"""
    with app.app_context():
        db.drop_all()

def reset_database(app):
    """Reinicia o banco de dados"""
    with app.app_context():
        db.drop_all()
        db.create_all()

def seed_database(app):
    """Popula o banco de dados com dados iniciais"""
    with app.app_context():
        # Criar usuários iniciais
        admin = User(
            email='admin@luxnox.com',
            name='Administrador',
            user_type='admin'
        )
        admin.set_password('123456')
        
        mechanic = User(
            email='mecanico@luxnox.com',
            name='Mecânico Teste',
            user_type='mechanic'
        )
        mechanic.set_password('123456')
        
        client = User(
            email='cliente@exemplo.com',
            name='Cliente Teste',
            user_type='client'
        )
        client.set_password('123456')
        
        db.session.add_all([admin, mechanic, client])
        db.session.commit()
        
        # Criar carteiras para os usuários
        admin_wallet = Wallet(user_id=admin.id)
        mechanic_wallet = Wallet(user_id=mechanic.id)
        client_wallet = Wallet(user_id=client.id)
        
        db.session.add_all([admin_wallet, mechanic_wallet, client_wallet])
        db.session.commit()
        
        # Criar veículos de exemplo
        vehicles = [
            Vehicle(brand='Honda', model='Civic', year=2020, version='EXL', engine='1.5 Turbo'),
            Vehicle(brand='Toyota', model='Corolla', year=2019, version='XEI', engine='2.0'),
            Vehicle(brand='Volkswagen', model='Golf', year=2021, version='GTI', engine='2.0 TSI'),
            Vehicle(brand='Fiat', model='Argo', year=2022, version='Trekking', engine='1.3'),
            Vehicle(brand='Hyundai', model='HB20', year=2020, version='Premium', engine='1.6')
        ]
        
        db.session.add_all(vehicles)
        db.session.commit()
        
        # Criar produtos de exemplo
        products = [
            Product(code='FAR4150', name='Filtro de Ar Premium', description='Filtro de ar de alta qualidade', 
                   manufacturer='Mann', category='Filtros', cost_price=30.50, selling_price=45.90, stock_quantity=45),
            Product(code='FCO0086', name='Filtro de Combustível', description='Filtro de combustível universal', 
                   manufacturer='Fram', category='Filtros', cost_price=25.30, selling_price=38.50, stock_quantity=32),
            Product(code='PFD2234', name='Pastilha de Freio Dianteira', description='Pastilha de freio para veículos de passeio', 
                   manufacturer='Fras-le', category='Freios', cost_price=85.00, selling_price=129.90, stock_quantity=12),
            Product(code='OMS5W30', name='Óleo Motor Sintético 5W30', description='Óleo sintético para motores modernos', 
                   manufacturer='Mobil', category='Óleos', cost_price=25.00, selling_price=35.90, stock_quantity=0),
            Product(code='KCD1050', name='Kit Correia Dentada', description='Kit completo com correia, tensionador e rolamentos', 
                   manufacturer='Gates', category='Motor', cost_price=180.00, selling_price=245.00, stock_quantity=23)
        ]
        
        db.session.add_all(products)
        db.session.commit()
        
        # Criar aplicações de produtos em veículos
        applications = [
            ProductApplication(product_id=1, vehicle_id=1),  # Filtro de ar para Honda Civic
            ProductApplication(product_id=1, vehicle_id=2),  # Filtro de ar para Toyota Corolla
            ProductApplication(product_id=2, vehicle_id=3),  # Filtro de combustível para VW Golf
            ProductApplication(product_id=2, vehicle_id=4),  # Filtro de combustível para Fiat Argo
            ProductApplication(product_id=3, vehicle_id=1),  # Pastilha de freio para Honda Civic
            ProductApplication(product_id=3, vehicle_id=2),  # Pastilha de freio para Toyota Corolla
            ProductApplication(product_id=5, vehicle_id=3),  # Kit correia para VW Golf
        ]
        
        db.session.add_all(applications)
        db.session.commit()
        
        print("Banco de dados populado com sucesso!")
