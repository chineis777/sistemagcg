# Modelagem do Banco de Dados MySQL para Luxnox

## Entidades Principais

### Usuários
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    user_type ENUM('admin', 'mechanic', 'client', 'seller', 'autopart', 'delivery') NOT NULL,
    document VARCHAR(20), -- CPF ou CNPJ
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);
```

### Produtos
```sql
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    manufacturer VARCHAR(100),
    category VARCHAR(100),
    cost_price DECIMAL(10, 2) NOT NULL,
    selling_price DECIMAL(10, 2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    min_stock_quantity INT DEFAULT 5,
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);
```

### Veículos
```sql
CREATE TABLE vehicles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    version VARCHAR(100),
    engine VARCHAR(50),
    transmission VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Aplicações de Produtos em Veículos
```sql
CREATE TABLE product_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    vehicle_id INT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    UNIQUE KEY unique_application (product_id, vehicle_id)
);
```

### Checklists
```sql
CREATE TABLE checklists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mechanic_id INT NOT NULL,
    client_id INT,
    vehicle_id INT NOT NULL,
    plate VARCHAR(20),
    mileage INT,
    notes TEXT,
    status ENUM('open', 'in_progress', 'completed', 'canceled') DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mechanic_id) REFERENCES users(id),
    FOREIGN KEY (client_id) REFERENCES users(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
);
```

### Itens do Checklist
```sql
CREATE TABLE checklist_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checklist_id INT NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    status ENUM('ok', 'attention', 'critical', 'not_checked') DEFAULT 'not_checked',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (checklist_id) REFERENCES checklists(id)
);
```

### Orçamentos
```sql
CREATE TABLE quotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quote_number VARCHAR(20) NOT NULL UNIQUE,
    mechanic_id INT NOT NULL,
    client_id INT,
    vehicle_id INT NOT NULL,
    checklist_id INT,
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    labor_cost DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount DECIMAL(10, 2) DEFAULT 0,
    status ENUM('draft', 'pending', 'approved', 'rejected', 'completed', 'canceled') DEFAULT 'draft',
    notes TEXT,
    valid_until DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mechanic_id) REFERENCES users(id),
    FOREIGN KEY (client_id) REFERENCES users(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
    FOREIGN KEY (checklist_id) REFERENCES checklists(id)
);
```

### Itens do Orçamento
```sql
CREATE TABLE quote_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quote_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    total_price DECIMAL(10, 2) NOT NULL,
    notes TEXT,
    is_labor BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quote_id) REFERENCES quotes(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### Carteiras
```sql
CREATE TABLE wallets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    balance DECIMAL(10, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY unique_user_wallet (user_id)
);
```

### Transações da Carteira
```sql
CREATE TABLE wallet_transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wallet_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    type ENUM('deposit', 'withdrawal', 'commission', 'payment', 'refund') NOT NULL,
    reference_id INT,
    reference_type VARCHAR(50),
    description TEXT,
    status ENUM('pending', 'completed', 'failed', 'canceled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id)
);
```

### Comissões
```sql
CREATE TABLE commissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mechanic_id INT NOT NULL,
    quote_id INT NOT NULL,
    quote_item_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    percentage DECIMAL(5, 2) NOT NULL,
    status ENUM('pending', 'approved', 'paid', 'canceled') DEFAULT 'pending',
    wallet_transaction_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mechanic_id) REFERENCES users(id),
    FOREIGN KEY (quote_id) REFERENCES quotes(id),
    FOREIGN KEY (quote_item_id) REFERENCES quote_items(id),
    FOREIGN KEY (wallet_transaction_id) REFERENCES wallet_transactions(id)
);
```

### Logs de IA
```sql
CREATE TABLE ai_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action_type VARCHAR(50) NOT NULL,
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Preferências de Usuário
```sql
CREATE TABLE user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY unique_user_preference (user_id, preference_key)
);
```

## Índices Adicionais

```sql
-- Índices para melhorar performance de busca
CREATE INDEX idx_products_code ON products(code);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_manufacturer ON products(manufacturer);

CREATE INDEX idx_vehicles_brand_model ON vehicles(brand, model);
CREATE INDEX idx_vehicles_year ON vehicles(year);

CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_mechanic ON quotes(mechanic_id);
CREATE INDEX idx_quotes_client ON quotes(client_id);

CREATE INDEX idx_wallet_transactions_type ON wallet_transactions(type);
CREATE INDEX idx_wallet_transactions_status ON wallet_transactions(status);

CREATE INDEX idx_commissions_status ON commissions(status);
CREATE INDEX idx_commissions_mechanic ON commissions(mechanic_id);
```

## Scripts de Inicialização

```sql
-- Inserir usuários iniciais
INSERT INTO users (email, password_hash, name, user_type) VALUES 
('admin@luxnox.com', '$2b$12$1xxxxxxxxxxxxxxxxxxxxuZLbwxnpY0o58unSvIPxddLxGystLu', 'Administrador', 'admin'),
('mecanico@luxnox.com', '$2b$12$1xxxxxxxxxxxxxxxxxxxxuZLbwxnpY0o58unSvIPxddLxGystLu', 'Mecânico Teste', 'mechanic'),
('cliente@exemplo.com', '$2b$12$1xxxxxxxxxxxxxxxxxxxxuZLbwxnpY0o58unSvIPxddLxGystLu', 'Cliente Teste', 'client');

-- Criar carteiras para usuários iniciais
INSERT INTO wallets (user_id) VALUES 
((SELECT id FROM users WHERE email = 'admin@luxnox.com')),
((SELECT id FROM users WHERE email = 'mecanico@luxnox.com')),
((SELECT id FROM users WHERE email = 'cliente@exemplo.com'));

-- Inserir veículos de exemplo
INSERT INTO vehicles (brand, model, year, version, engine) VALUES
('Honda', 'Civic', 2020, 'EXL', '1.5 Turbo'),
('Toyota', 'Corolla', 2019, 'XEI', '2.0'),
('Volkswagen', 'Golf', 2021, 'GTI', '2.0 TSI'),
('Fiat', 'Argo', 2022, 'Trekking', '1.3'),
('Hyundai', 'HB20', 2020, 'Premium', '1.6');
```
