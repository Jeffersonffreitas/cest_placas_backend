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
- CRUD administrativo local de alunos em `/api/v1/students`
- CRUD administrativo local de veiculos em `/api/v1/vehicles`
- vinculo de 1 aluno para varios veiculos
- busca de aluno por matricula em `/api/v1/students/by-registration/{registration_number}`
- busca de veiculo por placa em `/api/v1/vehicles/by-plate/{plate}`
- leitura manual de placa em `/api/v1/plates/read-manual`
- upload de imagem com OCR para leitura de placa em `/api/v1/plates/read-image`
- registro de eventos de acesso em leituras manuais e uploads
- decisao operacional nas respostas de leitura de placa
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
- As tabelas fisicas usam nomes em portugues com prefixo `tbl`, como
  `tblalunos`, `tblveiculos`, `tblleiturasplacas`, `tbleventosacesso`,
  `tblusuarios` e `tbllogsauditoria`.
- As colunas fisicas usam o padrao solicitado pela faculdade: `Int` para
  inteiros/identificadores, `Str` para textos, `Dtd` para datas e `Dec` para
  decimais.
- A API preserva os nomes JSON em snake_case, como `student_id`,
  `registration_number`, `full_name`, `vehicle_id`, `plate`, `source`,
  `status`, `confidence`, `created_at` e `updated_at`.
- O mapeamento entre os nomes publicos da API e os nomes fisicos do banco e
  feito nos models SQLAlchemy.

Exemplos de colunas fisicas:

```text
tblalunos.IntAlunoid
tblalunos.StrMatricula
tblveiculos.IntVeiculoid
tblveiculos.StrPlaca
tblleiturasplacas.DecConfianca
tbleventosacesso.StrPlacaNormalizada
tbleventosacesso.DtdCriacao
tblusuarios.StrUsuario
tbllogsauditoria.StrAcao
```

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

CRUD administrativo local de alunos. Todas as rotas de alunos exigem o header:

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

Listar alunos com paginacao:

```powershell
curl "http://localhost:8000/api/v1/students?skip=0&limit=20" `
  -H "Authorization: Bearer jwt_token"
```

Consultar aluno por id:

```powershell
curl "http://localhost:8000/api/v1/students/1" `
  -H "Authorization: Bearer jwt_token"
```

Consultar aluno por matricula:

```powershell
curl "http://localhost:8000/api/v1/students/by-registration/20260001" `
  -H "Authorization: Bearer jwt_token"
```

Atualizar aluno:

```powershell
curl -X PUT "http://localhost:8000/api/v1/students/1" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"phone":"85888880000","is_active":true}'
```

Desativar aluno sem apagar do banco:

```powershell
curl -X DELETE "http://localhost:8000/api/v1/students/1" `
  -H "Authorization: Bearer jwt_token"
```

A desativacao marca `is_active=false` e mantem o registro em `tblalunos`.
Matriculas ativas duplicadas sao rejeitadas.

## Veiculos

CRUD administrativo local de veiculos. Todas as rotas de veiculos exigem o header:

```text
Authorization: Bearer jwt_token
```

A placa e normalizada antes de salvar e consultar. Exemplos como `abc-1234`,
`ABC1234` e `abc 1234` sao tratados como `ABC1234`. Placas invalidas retornam
erro `invalid_plate` antes do cadastro.

Criar veiculo vinculado a um aluno existente e ativo:

```powershell
curl -X POST "http://localhost:8000/api/v1/vehicles" `
  -H "Authorization: Bearer jwt_token" `
  -H "Content-Type: application/json" `
  -d '{"student_id":1,"plate":"abc-1234","brand":"Fiat","model":"Mobi","color":"Branco"}'
```

Listar veiculos com paginacao:

```powershell
curl "http://localhost:8000/api/v1/vehicles?skip=0&limit=20" `
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

Desativar veiculo sem apagar do banco:

```powershell
curl -X DELETE "http://localhost:8000/api/v1/vehicles/1" `
  -H "Authorization: Bearer jwt_token"
```

A desativacao marca `is_active=false` e mantem o registro em `tblveiculos`.
Placas ativas duplicadas sao rejeitadas.

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

As respostas de leitura tambem retornam `operational_decision`, pensado para o
uso na portaria:

```text
ACESSO_LIBERADO       placa encontrada com veiculo e aluno ativos
VEICULO_NAO_CADASTRADO placa valida, mas sem cadastro de veiculo
OCR_BAIXA_CONFIANCA   OCR real abaixo da confianca minima
CADASTRO_INATIVO      placa encontrada, mas veiculo ou aluno inativo
```

Em erros de leitura, a decisao aparece em `error.details.operational_decision`:

```text
PLACA_INVALIDA formato de placa invalido
ERRO_OCR       OCR indisponivel, imagem invalida ou placa nao reconhecida
```

Exemplo de resposta com veiculo encontrado:

```json
{
  "id": 1,
  "plate_input": "ABC1D23",
  "plate_normalized": "ABC1D23",
  "source": "manual",
  "status": "matched",
  "operational_decision": "ACESSO_LIBERADO",
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

Exemplo sem veiculo cadastrado:

```json
{
  "id": 2,
  "plate_input": "ZZZ9Z99",
  "plate_normalized": "ZZZ9Z99",
  "source": "manual",
  "status": "not_found",
  "operational_decision": "VEICULO_NAO_CADASTRADO",
  "vehicle": null,
  "student": null,
  "created_at": "2026-05-12T15:32:00"
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
aplica pre-processamentos de contraste, nitidez, escala, binarizacao e inversao
de tons, e tenta reconhecer a placa com OCR usando multiplas configuracoes do
Tesseract.

O OCR tambem normaliza candidatos de placa e corrige confusoes comuns por
posicao do padrao brasileiro, como `0/O`, `1/I`, `8/B`, `5/S`, `2/Z` e `A/4`.
Assim, ruidos frequentes do Tesseract podem ser convertidos para placas validas
antes da consulta em veiculos. Quando houver mais de uma candidata, a selecao
prioriza placas em padrao brasileiro que aparecem de forma consistente entre as
tentativas de pre-processamento, em vez de depender apenas de uma leitura isolada
com confianca alta.

Para o OCR real, a API exige confianca minima de `70.0` em uma escala de 0 a
100. Leituras com confianca ausente ou abaixo desse valor continuam sendo
registradas em `tblleiturasplacas` e geram evento em `tbleventosacesso`, mas sao
tratadas de forma segura como `status` igual a `not_found`, sem vincular
veiculo ou aluno. Quando `mock_plate` for enviado, essa regra de confianca nao
e aplicada, preservando o fluxo de testes e simulacoes.

A leitura salva a imagem em `uploads/plate_reads/`, registra uma linha em
`tblleiturasplacas` com JSON publico `image_path`, `source` igual a `upload` e
`confidence` quando o OCR fornecer essa informacao. Depois registra normalmente
um evento de acesso com `source` igual a `upload`.

Sem `mock_plate`, o ambiente precisa ter o Tesseract OCR instalado, alem das
dependencias Python instaladas por `requirements.txt`. No Windows, a integracao
procura automaticamente o executavel em
`C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`, depois em
`C:\Program Files\Tesseract-OCR\tesseract.exe`, e por fim usa o Tesseract
disponivel no PATH.

Exemplo de resposta:

```json
{
  "id": 2,
  "plate_input": "ABC1D23",
  "plate_normalized": "ABC1D23",
  "source": "upload",
  "status": "matched",
  "operational_decision": "ACESSO_LIBERADO",
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

Exemplo com OCR abaixo da confianca minima:

```json
{
  "id": 3,
  "plate_input": "ABC1D23",
  "plate_normalized": "ABC1D23",
  "source": "upload",
  "status": "not_found",
  "operational_decision": "OCR_BAIXA_CONFIANCA",
  "vehicle": null,
  "student": null,
  "image_path": "uploads/plate_reads/arquivo.jpg",
  "confidence": 69.99,
  "created_at": "2026-05-12T15:33:00"
}
```

Exemplo de erro quando o OCR nao reconhece uma placa:

```json
{
  "success": false,
  "error": {
    "code": "plate_not_recognized",
    "message": "Could not identify a Brazilian plate in the image.",
    "details": {
      "operational_decision": "ERRO_OCR"
    }
  },
  "path": "/api/v1/plates/read-image",
  "timestamp": "2026-05-12T15:34:00+00:00"
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
- Ha OCR real por upload de imagem, com suporte a `mock_plate` para testes e
  simulacoes.
- Nao ha integracao com banco do CEST nesta etapa.
- A autenticacao administrativa usa JWT e senha com hash.
