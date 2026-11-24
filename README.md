# **SentinelTrade**
Projeto N1 - Projeto de Software

---

## Integrantes
* **Felipe Vieira de Castro** - 10738719
* **João Victor Oliveira Ramalho** - 10435754
* **Pedro Henrique Rossigalli Rodrigues** - 10730520

---

## Visão Geral
O **SentinelTrade** é uma plataforma de negociação financeira de alta criticidade projetada sob princípios de arquitetura limpa, tolerância a falhas e segurança defensiva. O sistema permite que investidores acompanhem cotações, gerenciem sua carteira de ativos, enviem/cancelem ordens de compra e venda e consultem seu histórico operacional.

Para garantir integridade financeira e resiliência, a aplicação conta com autenticação multifator (MFA TOTP), validação rigorosa de saldo e limites de risco, prevenção de duplicidade via chaves de idempotência, tratamento de indisponibilidade externa (timeout da bolsa) e trilhas de auditoria estruturadas.

---

## Arquitetura e Segurança Implementadas
* **Orientação a Objetos e Desacoplamento:** Separação clara entre domínio (`domain/`), contratos abstratos (`interfaces/`), serviços de negócio (`services/`), persistência/integrações (`infrastructure/`) e sanitização (`security/`).
* **Persistência Relacional (SQL):** Banco de dados SQLite com integridade referencial ativada, restrições `CHECK` e consultas 100% parametrizadas para mitigação de *SQL Injection*.
* **Segurança Defensiva:**
  * Validação *server-side* com *allowlists* e expressões regulares estritas para tickers, e-mails, valores e UUIDs.
  * Hashing de senhas com `PBKDF2-HMAC-SHA256` + *salt* criptográfico e comparação em tempo constante.
  * Segundo fator de autenticação (MFA) baseado em tempo (TOTP) e *Rate Limiting* contra ataques de força bruta.
  * Sanitização de saídas para prevenção de *Log Injection* e *Path Traversal*.

---

## Tecnologias Utilizadas
* **Linguagem:** Python 3.10+ (Standard Library: `sqlite3`, `unittest`, `abc`, `hashlib`, `hmac`, `re`)
* **Banco de Dados:** SQLite (SQL Relacional)
* **IDE:** Visual Studio Code
* **Modelagem UML:** draw.io

---

## Estrutura do Repositório
```text
SentinelTrade/
├── docs/                  # Requisitos, casos de uso, contexto e diagramas UML (.png / .pdf)
├── src/
│   ├── domain/            # Entidades encapsuladas, enums e exceções de negócio
│   ├── infrastructure/    # Conexão SQL, repositórios parametrizados e bolsa simulada
│   ├── interfaces/        # Classes abstratas (contratos de repositório e gateways)
│   ├── security/          # Validadores, allowlists, sanitização e rate limiter
│   ├── services/          # Regras de negócio (autenticação MFA, ordens e auditoria)
│   └── main.py            # Interface CLI do sistema
├── tests/                 # Suíte de testes unitários automatizados
├── .env.example           # Template de variáveis de ambiente
├── .gitignore             # Arquivos ignorados no controle de versão (bancos locais, logs, cache)
├── run.bat                # Script auxiliar de testes e execução (Windows)
└── README.md              # Documentação principal do projeto
```

# Instruções de execução

1. Clone o repositório no seu computador:

   ```bash
   git clone https://github.com/felipevieeira/SentinelTrade
   ```

2. Para compilar corretamente o projeto:
   ```bash
   python -m src.main
   ```

3. Executar os testes automatizados: 
   ```bash
   python -m unittest discover -s tests -v
   ```