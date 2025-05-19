from flask import Flask
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

def criar_tabelas(conexao):
    with conexao.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nome VARCHAR(255) NOT NULL,
                user_type VARCHAR(50) NOT NULL,
                documento VARCHAR(30),
                telefone VARCHAR(20),
                endereco TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT TRUE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nome VARCHAR(255) NOT NULL,
                descricao TEXT,
                fabricante VARCHAR(100),
                grupo VARCHAR(100),
                custo_preco DECIMAL(10, 2),
                preco_de_venda DECIMAL(10, 2),
                estoque INT DEFAULT 0,
                min_stock_quantity INT DEFAULT 5,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conexao.commit()

@app.route('/')
def index():
    return "✅ API de IA Luxnox rodando!"

@app.route('/inicializar-banco')
def init_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        criar_tabelas(conn)
        conn.close()
        return "🧠 Banco inicializado com sucesso!"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
