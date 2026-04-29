# AGENTS.md

## Objetivo do projeto
Construir apenas o backend em Python para um sistema de reconhecimento de placas veiculares do CEST.

## Escopo desta fase
Nesta fase, o projeto deve entregar somente:
- API backend em Python
- banco de dados MySQL
- autenticação administrativa básica
- cadastro de alunos
- cadastro de veículos
- consulta por placa
- registro de leitura manual de placa
- registro de eventos de acesso

## Tecnologias obrigatórias
- Python 3.11+
- FastAPI
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- MySQL
- PyMySQL
- Pytest

## Restrições
- Não criar frontend nesta fase
- Não usar outra linguagem no backend
- Não integrar ainda com banco do CEST
- Não implementar ainda YOLO, EasyOCR ou Tesseract
- Apenas preparar a base do sistema

## Estrutura desejada
- app/main.py
- app/api/
- app/core/
- app/db/
- app/models/
- app/schemas/
- app/repositories/
- app/services/
- app/integrations/
- tests/

## Regras de arquitetura
- Separar rotas, regras de negócio e acesso a banco
- Usar variáveis de ambiente para dados sensíveis
- Criar código limpo e pronto para rodar
- Criar migrations do banco com Alembic
- Criar README com comandos de instalação e execução
- Explicar antes de mudanças grandes
- Listar sempre os arquivos criados ou alterados ao final

## Regras específicas do MySQL
- Usar engine InnoDB
- Usar charset utf8mb4
- Criar índices para campos de consulta frequente
- Garantir unicidade da placa em vehicles
- Compatibilizar tipos com MySQL

## Entidades iniciais
- users
- students
- vehicles
- plate_reads
- access_events
- audit_logs