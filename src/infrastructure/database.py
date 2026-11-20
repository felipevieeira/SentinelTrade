import sqlite3
from pathlib import Path

class DatabaseManager:
    """Gerencia a conexão e o schema relacional SQL do SentinelTrade."""

    def __init__(self, db_path: str = "sentinel_trade.db"):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão configurada com chaves estrangeiras ativadas."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def inicializar_tabelas(self) -> None:
        """Cria o schema relacional caso ainda não exista."""
        ddl_script = """
        CREATE TABLE IF NOT EXISTS investidores (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            mfa_secret TEXT NOT NULL,
            criado_em TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contas (
            id TEXT PRIMARY KEY,
            investidor_id TEXT NOT NULL UNIQUE,
            saldo REAL NOT NULL CHECK (saldo >= 0),
            limite_por_ordem REAL NOT NULL CHECK (limite_por_ordem > 0),
            criado_em TEXT NOT NULL,
            FOREIGN KEY (investidor_id) REFERENCES investidores(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS posicoes_ativos (
            conta_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            PRIMARY KEY (conta_id, ticker),
            FOREIGN KEY (conta_id) REFERENCES contas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ordens (
            id TEXT PRIMARY KEY,
            conta_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('COMPRA', 'VENDA')),
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            preco REAL NOT NULL CHECK (preco > 0),
            idempotency_key TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL CHECK (status IN ('PENDENTE', 'AGUARDANDO_ENVIO', 'EXECUTADA', 'CANCELADA', 'REJEITADA')),
            criado_em TEXT NOT NULL,
            FOREIGN KEY (conta_id) REFERENCES contas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS logs_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            investidor_id TEXT,
            evento TEXT NOT NULL,
            detalhes TEXT NOT NULL
        );
        """
        with self.get_connection() as conn:
            conn.executescript(ddl_script)
            conn.commit()