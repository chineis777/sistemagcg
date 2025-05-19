
import psycopg2
import os

def create_tables(conn):
    with conn.cursor() as cur:
        # Criação automática das tabelas principais
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            user_type VARCHAR(50) NOT NULL,
            document VARCHAR(20),
            phone VARCHAR(20),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            manufacturer VARCHAR(100),
            category VARCHAR(100),
            cost_price DECIMAL(10, 2),
            selling_price DECIMAL(10, 2),
            stock_quantity INT DEFAULT 0,
            min_stock_quantity INT DEFAULT 5,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active BOOLEAN DEFAULT TRUE
        );

        CREATE TABLE IF NOT EXISTS vehicles (
            id SERIAL PRIMARY KEY,
            brand VARCHAR(100),
            model VARCHAR(100),
            year INT,
            version VARCHAR(100),
            engine VARCHAR(50),
            transmission VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS product_applications (
            id SERIAL PRIMARY KEY,
            product_id INT REFERENCES products(id),
            vehicle_id INT REFERENCES vehicles(id),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (product_id, vehicle_id)
        );
        """)
        conn.commit()
        print("✅ Tabelas criadas com sucesso.")

def ai_greeting():
    print("🤖 ChinaBot v1: Olá! Estou pronto pra ajudar você com qualquer peça ou orçamento.")

def main():
    print("🚀 Iniciando Luxnox com IA e banco automático...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("⚠️ DATABASE_URL não encontrada nas variáveis de ambiente.")

    conn = psycopg2.connect(db_url)
    create_tables(conn)
    ai_greeting()
    conn.close()

if __name__ == "__main__":
    main()
