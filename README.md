# CEST Placas Backend

Backend inicial em Python para o sistema de reconhecimento de placas veiculares do CEST.

## Escopo desta etapa

- API em FastAPI
- SQLAlchemy 2.0 configurado para MySQL
- Alembic configurado para migrations
- Pydantic v2 configurado
- PyMySQL configurado por variavel de ambiente
- rota `/health`
- autenticacao administrativa basica com JWT
- rotas `/api/v1/auth/login` e `/api/v1/auth/me`
- tratamento padronizado de erros
- estrutura preparada para evolucao do dominio

## Tecnologias

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- MySQL
- PyMySQL
- Pytest

## Estrutura

```text
app/
alembic/
tests/
```

## Configuracao local

1. Crie e ative um ambiente virtual.
2. Instale as dependencias.
3. Crie um arquivo `.env` com base em `.env.example`.
4. Ajuste a `DATABASE_URL` para apontar para o seu MySQL.
5. Rode as migrations.
6. Crie o admin inicial.
7. Suba a API.

## Comandos de instalacao

### PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Banco de dados MySQL

- O projeto aceita somente MySQL.
- A conexao e feita por `DATABASE_URL`.
- O driver configurado e `PyMySQL`.
- As tabelas iniciais foram preparadas com `InnoDB` e `utf8mb4`.

Exemplo:

```env
DATABASE_URL=mysql+pymysql://cest_user:cest_password@localhost:3306/cest_placas?charset=utf8mb4
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
SECRET_KEY=change_me_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

## Rodar migrations

```powershell
alembic upgrade head
```

## Criar admin inicial

O primeiro administrador e criado a partir das variaveis `ADMIN_USERNAME` e
`ADMIN_PASSWORD` do `.env`.

```powershell
python -m app.db.seed
```

Se o usuario informado em `ADMIN_USERNAME` ja existir, o comando mantem o
registro atual.

## Criar nova migration

```powershell
alembic revision --autogenerate -m "descricao_da_migration"
```

## Subir a API

```powershell
uvicorn app.main:app --reload
```

## Health check

Apos subir a aplicacao:

```text
GET /health
```

Resposta esperada:

```json
{
  "status": "ok",
  "app_name": "CEST Placas Backend",
  "version": "0.1.0",
  "environment": "local"
}
```

## Autenticacao administrativa

Crie o admin inicial antes do primeiro login:

```powershell
python -m app.db.seed
```

Faca login enviando `ADMIN_USERNAME` e `ADMIN_PASSWORD`:

```text
POST /api/v1/auth/login
```

Corpo `application/x-www-form-urlencoded`:

```text
username=admin&password=change_me
```

Resposta:

```json
{
  "access_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Use o token nas rotas protegidas:

```text
Authorization: Bearer jwt_token
```

Usuario autenticado:

```text
GET /api/v1/auth/me
```

## Rodar testes

```powershell
pytest
```

## Observacoes

- Nao ha frontend nesta etapa.
- Nao ha OCR nesta etapa.
- Nao ha integracao com banco do CEST nesta etapa.
- A autenticacao administrativa usa JWT e senha com hash.
