# Guia de Deploy do Sistema Luxnox

## Visão Geral

Este documento contém instruções detalhadas para realizar o deploy permanente do Sistema Luxnox, uma plataforma completa para gestão de autopeças, mecânicos e clientes.

## Requisitos do Servidor

- Ubuntu 20.04 LTS ou superior
- Python 3.8+
- MySQL 8.0+
- Nginx
- Certbot (para SSL)
- Supervisor (para gerenciamento de processos)

## Passo a Passo para Deploy

### 1. Preparação do Servidor

```bash
# Atualizar pacotes
sudo apt update
sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3 python3-pip python3-venv mysql-server nginx supervisor certbot python3-certbot-nginx

# Configurar MySQL para iniciar automaticamente
sudo systemctl enable mysql
sudo systemctl start mysql
```

### 2. Configuração do Banco de Dados

```bash
# Acessar MySQL como root
sudo mysql

# Executar os seguintes comandos SQL
CREATE DATABASE luxnox_db;
CREATE USER 'luxnox_user'@'localhost' IDENTIFIED BY 'senha_segura_aqui';
GRANT ALL PRIVILEGES ON luxnox_db.* TO 'luxnox_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Instalação do Sistema Luxnox

```bash
# Criar diretório para a aplicação
sudo mkdir -p /opt/luxnox
sudo chown -R $USER:$USER /opt/luxnox

# Extrair o pacote do sistema
unzip luxnox_system.zip -d /opt/luxnox

# Criar ambiente virtual
cd /opt/luxnox
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
echo "export DATABASE_URL='mysql+pymysql://luxnox_user:senha_segura_aqui@localhost/luxnox_db'" > .env
echo "export SECRET_KEY='chave_secreta_muito_segura_aqui'" >> .env
echo "export FLASK_ENV='production'" >> .env
```

### 4. Inicialização do Banco de Dados

```bash
# Ativar ambiente virtual
cd /opt/luxnox
source venv/bin/activate

# Executar migrações e seed inicial
cd src
export FLASK_APP=main.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Importar dados iniciais (opcional)
python import_initial_data.py
```

### 5. Configuração do Supervisor

Crie um arquivo de configuração para o Supervisor:

```bash
sudo nano /etc/supervisor/conf.d/luxnox.conf
```

Adicione o seguinte conteúdo:

```ini
[program:luxnox]
directory=/opt/luxnox
command=/opt/luxnox/venv/bin/python src/main.py
autostart=true
autorestart=true
stderr_logfile=/var/log/luxnox/err.log
stdout_logfile=/var/log/luxnox/out.log
user=www-data
environment=
    DATABASE_URL="mysql+pymysql://luxnox_user:senha_segura_aqui@localhost/luxnox_db",
    SECRET_KEY="chave_secreta_muito_segura_aqui",
    FLASK_ENV="production"
```

Crie o diretório de logs e inicie o serviço:

```bash
sudo mkdir -p /var/log/luxnox
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start luxnox
```

### 6. Configuração do Nginx

Crie um arquivo de configuração para o Nginx:

```bash
sudo nano /etc/nginx/sites-available/luxnox
```

Adicione o seguinte conteúdo:

```nginx
server {
    listen 80;
    server_name seu-dominio.com www.seu-dominio.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ative a configuração e reinicie o Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/luxnox /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Configuração do SSL (HTTPS)

```bash
sudo certbot --nginx -d seu-dominio.com -d www.seu-dominio.com
```

### 8. Verificação do Deploy

Acesse seu domínio no navegador para verificar se o sistema está funcionando corretamente:

```
https://seu-dominio.com
```

## Credenciais de Acesso Inicial

Após o deploy, você pode acessar o sistema com as seguintes credenciais:

- **Administrador**:
  - Email: admin@luxnox.com
  - Senha: 123456

- **Mecânico**:
  - Email: mecanico@luxnox.com
  - Senha: 123456

- **Cliente**:
  - Email: cliente@exemplo.com
  - Senha: 123456

**IMPORTANTE**: Altere essas senhas imediatamente após o primeiro acesso!

## Manutenção e Backup

### Backup do Banco de Dados

Configure backups diários do banco de dados:

```bash
# Criar script de backup
sudo nano /opt/luxnox/backup.sh
```

Adicione o seguinte conteúdo:

```bash
#!/bin/bash
BACKUP_DIR="/opt/luxnox/backups"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
mkdir -p $BACKUP_DIR
mysqldump -u luxnox_user -p'senha_segura_aqui' luxnox_db > $BACKUP_DIR/luxnox_db_$TIMESTAMP.sql
find $BACKUP_DIR -name "luxnox_db_*.sql" -type f -mtime +7 -delete
```

Torne o script executável e configure um cron job:

```bash
sudo chmod +x /opt/luxnox/backup.sh
sudo crontab -e
```

Adicione a seguinte linha para executar o backup diariamente às 2h da manhã:

```
0 2 * * * /opt/luxnox/backup.sh
```

## Suporte e Contato

Para suporte técnico ou dúvidas sobre o sistema, entre em contato:

- Email: suporte@luxnox.com
- Telefone: (XX) XXXX-XXXX
