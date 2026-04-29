# CEST Placas Backend

Backend inicial em Python para o sistema de reconhecimento de placas veiculares do CEST.

## Escopo desta etapa

- API em FastAPI
- SQLAlchemy 2.0 configurado para MySQL
- Alembic configurado para migrations
- Pydantic v2 configurado
- PyMySQL configurado por variável de ambiente
- rota `/health`
- tratamento padronizado de erros
- estrutura preparada para evolução do domínio

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

## Configuração local

1. Crie e ative um ambiente virtual.
2. Instale as dependências.
3. Crie um arquivo `.env` com base em `.env.example`.
4. Ajuste a `DATABASE_URL` para apontar para o seu MySQL.
5. Rode as migrations.
6. Suba a API.

## Comandos de instalação

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
- A conexão é feita por `DATABASE_URL`.
- O driver configurado é `PyMySQL`.
- As tabelas iniciais foram preparadas com `InnoDB` e `utf8mb4`.

Exemplo:

```env
DATABASE_URL=mysql+pymysql://cest_user:cest_password@localhost:3306/cest_placas?charset=utf8mb4
```

## Rodar migrations

```powershell
alembic upgrade head
```

## Criar nova migration

```powershell
alembic revision --autogenerate -m "descricao_da_migration"
```

## Subir a API

```powershell
uvicorn app.main:app --reload
```

## Health check

Após subir a aplicação:

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

## Rodar testes

```powershell
pytest
```

## Observações

- Não há frontend nesta etapa.
- Não há OCR nesta etapa.
- Não há integração com banco do CEST nesta etapa.
- A autenticação administrativa foi apenas preparada na base do projeto para evolução posterior.

