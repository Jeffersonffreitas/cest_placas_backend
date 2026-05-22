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
- CRUD administrativo de alunos em `/api/v1/students`
- CRUD administrativo de veiculos em `/api/v1/vehicles`
- vinculo de 1 aluno para varios veiculos
- busca de veiculo por placa em `/api/v1/vehicles/by-plate/{plate}`
- leitura manual de placa em `/api/v1/plates/read-manual`
- upload de imagem com OCR para leitura de placa em `/api/v1/plates/read-image`
- registro de eventos de acesso em leituras manuais e uploads
- consulta administrativa de eventos de acesso em `/api/v1/access-events`
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
- Pillow
- pytesseract
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
3. Instale o executavel do Tesseract OCR no sistema.
4. Crie um arquivo `.env` com base em `.env.example`.
5. Ajuste a `DATABASE_URL` para apontar para o seu MySQL.
6. Rode as migrations.
7. Crie o admin inicial.
8. Suba a API.

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
python -m alembic upgrade head
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
python -m uvicorn app.main:app --reload
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

## Alunos

Todas as rotas de alunos exigem o header:

```text
Authorization: Bearer jwt_token
```

Criar aluno:

```powershell
curl -X POST "http://localhost:8000/api/v1/students" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"registration_number":"20260001","full_name":"Maria Silva","email":"maria.silva@example.com","phone":"85999990000"}'
```

Listar alunos:

```powershell
curl "http://localhost:8000/api/v1/students" `
  -H "Authorization: Bearer jwt_token"
```

Consultar aluno por id:

```powershell
curl "http://localhost:8000/api/v1/students/1" `
  -H "Authorization: Bearer jwt_token"
```

Atualizar aluno:

```powershell
curl -X PUT "http://localhost:8000/api/v1/students/1" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"phone":"85888880000","is_active":true}'
```

Excluir aluno:

```powershell
curl -X DELETE "http://localhost:8000/api/v1/students/1" `
  -H "Authorization: Bearer jwt_token"
```

Alunos com veiculos vinculados nao podem ser excluidos antes da remocao dos
veiculos.

## Veiculos

Todas as rotas de veiculos exigem o header:

```text
Authorization: Bearer jwt_token
```

A placa e normalizada antes de salvar e consultar. Exemplos como `abc-1234`,
`ABC1234` e `abc 1234` sao tratados como `ABC1234`.

Criar veiculo vinculado a um aluno:

```powershell
curl -X POST "http://localhost:8000/api/v1/vehicles" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"student_id":1,"plate":"abc-1234","brand":"Fiat","model":"Mobi","color":"Branco"}'
```

Listar veiculos:

```powershell
curl "http://localhost:8000/api/v1/vehicles" `
  -H "Authorization: Bearer jwt_token"
```

Listar veiculos de um aluno:

```powershell
curl "http://localhost:8000/api/v1/vehicles?student_id=1" `
  -H "Authorization: Bearer jwt_token"
```

Buscar veiculo por placa:

```powershell
curl "http://localhost:8000/api/v1/vehicles/by-plate/abc-1234" `
  -H "Authorization: Bearer jwt_token"
```

Consultar veiculo por id:

```powershell
curl "http://localhost:8000/api/v1/vehicles/1" `
  -H "Authorization: Bearer jwt_token"
```

Atualizar veiculo:

```powershell
curl -X PUT "http://localhost:8000/api/v1/vehicles/1" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"color":"Preto","is_active":true}'
```

Excluir veiculo:

```powershell
curl -X DELETE "http://localhost:8000/api/v1/vehicles/1" `
  -H "Authorization: Bearer jwt_token"
```

## Leitura manual de placa

A rota de leitura manual exige autenticacao administrativa:

```text
Authorization: Bearer jwt_token
```

Registrar leitura manual:

```powershell
curl -X POST "http://localhost:8000/api/v1/plates/read-manual" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"plate":"ABC1D23"}'
```

Quando a placa normalizada for encontrada em veiculos, a resposta retorna
`status` como `matched`, alem dos dados do veiculo e do aluno. Quando nao houver
veiculo cadastrado, a resposta retorna `status` como `not_found` e registra o
evento de acesso mesmo assim.

Exemplo de resposta com veiculo encontrado:

```json
{
  "id": 1,
  "plate_input": "ABC1D23",
  "plate_normalized": "ABC1D23",
  "source": "manual",
  "status": "matched",
  "vehicle": {
    "id": 1,
    "student_id": 1,
    "plate": "ABC1D23",
    "brand": "Fiat",
    "model": "Mobi",
    "color": "Branco",
    "is_active": true,
    "created_at": "2026-05-12T15:30:00",
    "updated_at": "2026-05-12T15:30:00"
  },
  "student": {
    "id": 1,
    "registration_number": "20260001",
    "full_name": "Maria Silva",
    "email": "maria.silva@example.com",
    "phone": "85999990000",
    "is_active": true,
    "created_at": "2026-05-12T15:30:00",
    "updated_at": "2026-05-12T15:30:00"
  },
  "created_at": "2026-05-12T15:30:00"
}
```

## Leitura de placa por upload de imagem

A rota de upload exige autenticacao administrativa:

```text
Authorization: Bearer jwt_token
```

Registrar leitura a partir de uma imagem:

```powershell
curl -X POST "http://localhost:8000/api/v1/plates/read-image" `
  -H "Authorization: Bearer jwt_token" `
  -F "file=@C:\caminho\para\ABC1D23.jpg" `
  -F "mock_plate=ABC1D23"
```

O campo `file` e obrigatorio. O campo `mock_plate` e opcional. Quando
`mock_plate` for enviado, ele sera usado como placa reconhecida, preservando o
fluxo de testes e simulacoes. Quando nao for enviado, a API salva a imagem,
aplica um pre-processamento simples e tenta reconhecer a placa com OCR.

A leitura salva a imagem em `uploads/plate_reads/`, registra uma linha em
`plate_reads` com `image_path`, `source` igual a `upload` e `confidence` quando
o OCR fornecer essa informacao. Depois registra normalmente um evento de acesso
com `source` igual a `upload`.

Sem `mock_plate`, o ambiente precisa ter o Tesseract OCR instalado e disponivel
no PATH do sistema, alem das dependencias Python instaladas por
`requirements.txt`.

Exemplo de resposta:

```json
{
  "id": 2,
  "plate_input": "ABC1D23",
  "plate_normalized": "ABC1D23",
  "source": "upload",
  "status": "matched",
  "vehicle": {
    "id": 1,
    "student_id": 1,
    "plate": "ABC1D23",
    "brand": "Fiat",
    "model": "Mobi",
    "color": "Branco",
    "is_active": true,
    "created_at": "2026-05-12T15:30:00",
    "updated_at": "2026-05-12T15:30:00"
  },
  "student": {
    "id": 1,
    "registration_number": "20260001",
    "full_name": "Maria Silva",
    "email": "maria.silva@example.com",
    "phone": "85999990000",
    "is_active": true,
    "created_at": "2026-05-12T15:30:00",
    "updated_at": "2026-05-12T15:30:00"
  },
  "image_path": "uploads/plate_reads/arquivo.jpg",
  "confidence": 91.42,
  "created_at": "2026-05-12T15:31:00"
}
```

## Eventos de acesso

A rota de eventos de acesso exige autenticacao administrativa:

```text
Authorization: Bearer jwt_token
```

Listar eventos, ordenados do mais recente para o mais antigo:

```powershell
curl "http://localhost:8000/api/v1/access-events" `
  -H "Authorization: Bearer jwt_token"
```

Filtros e paginacao disponiveis no Swagger em:

```text
http://localhost:8000/docs
```

Parametros aceitos:

```text
skip=0
limit=100
plate=ABC1D23
source=manual
status=matched
student_id=1
vehicle_id=1
date_from=2026-05-12T00:00:00
date_to=2026-05-12T23:59:59
```

Exemplo combinando filtros:

```powershell
curl "http://localhost:8000/api/v1/access-events?plate=abc-1d23&status=matched&skip=0&limit=20" `
  -H "Authorization: Bearer jwt_token"
```

O filtro `plate` e normalizado antes da busca. Assim, `abc-1d23`,
`ABC1D23` e `abc 1d23` consultam a placa `ABC1D23`. O filtro `status`
aceita apenas `matched` e `not_found`. O filtro `source` aceita `manual`
e `upload`.

## Rodar testes

```powershell
python -m pytest
```

## Observacoes

- Nao ha frontend nesta etapa.
- Nao ha OCR nesta etapa.
- Nao ha integracao com banco do CEST nesta etapa.
- A autenticacao administrativa usa JWT e senha com hash.
