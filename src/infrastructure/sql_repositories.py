from datetime import datetime
from typing import List, Optional, Dict

from src.domain.entities import Investidor, ContaInvestimento, Ordem
from src.domain.enums import TipoOrdem, StatusOrdem
from src.infrastructure.database import DatabaseManager
from src.interfaces.repositories import IInvestidorRepository, IContaRepository, IOrdemRepository


class SqlInvestidorRepository(IInvestidorRepository):
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def salvar(self, investidor: Investidor) -> None:
        query = """
            INSERT INTO investidores (id, nome, email, senha_hash, mfa_secret, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (
                investidor.id,
                investidor.nome,
                investidor.email,
                investidor.senha_hash,
                investidor.mfa_secret,
                investidor.criado_em.isoformat()
            ))
            conn.commit()

    def buscar_por_email(self, email: str) -> Optional[Investidor]:
        query = "SELECT * FROM investidores WHERE email = ?"
        with self.db_manager.get_connection() as conn:
            row = conn.execute(query, (email,)).fetchone()
            if not row:
                return None
            return Investidor(
                nome=row["nome"],
                email=row["email"],
                senha_hash=row["senha_hash"],
                mfa_secret=row["mfa_secret"],
                entity_id=row["id"]
            )

    def buscar_por_id(self, investidor_id: str) -> Optional[Investidor]:
        query = "SELECT * FROM investidores WHERE id = ?"
        with self.db_manager.get_connection() as conn:
            row = conn.execute(query, (investidor_id,)).fetchone()
            if not row:
                return None
            return Investidor(
                nome=row["nome"],
                email=row["email"],
                senha_hash=row["senha_hash"],
                mfa_secret=row["mfa_secret"],
                entity_id=row["id"]
            )


class SqlContaRepository(IContaRepository):
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def salvar(self, conta: ContaInvestimento) -> None:
        query = """
            INSERT INTO contas (id, investidor_id, saldo, limite_por_ordem, criado_em)
            VALUES (?, ?, ?, ?, ?)
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (
                conta.id,
                conta.investidor_id,
                conta.saldo,
                conta.limite_por_ordem,
                conta.criado_em.isoformat()
            ))
            conn.commit()

    def buscar_por_investidor_id(self, investidor_id: str) -> Optional[ContaInvestimento]:
        with self.db_manager.get_connection() as conn:
            row_conta = conn.execute(
                "SELECT * FROM contas WHERE investidor_id = ?",
                (investidor_id,)
            ).fetchone()
            if not row_conta:
                return None

            # Reconstrói o dicionário de ativos em custódia daquela conta
            rows_posicoes = conn.execute(
                "SELECT ticker, quantidade FROM posicoes_ativos WHERE conta_id = ?",
                (row_conta["id"],)
            ).fetchall()
            posicoes: Dict[str, int] = {r["ticker"]: r["quantidade"] for r in rows_posicoes}

            return ContaInvestimento(
                investidor_id=row_conta["investidor_id"],
                saldo_inicial=row_conta["saldo"],
                limite_por_ordem=row_conta["limite_por_ordem"],
                posicoes=posicoes,
                entity_id=row_conta["id"]
            )

    def atualizar_saldo_e_posicoes(self, conta: ContaInvestimento) -> None:
        # Atualiza o saldo e sincroniza a carteira dentro da mesma transação
        # para não correr o risco de debitar o dinheiro e falhar ao entregar o ativo
        with self.db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE contas SET saldo = ? WHERE id = ?",
                (conta.saldo, conta.id)
            )
            conn.execute("DELETE FROM posicoes_ativos WHERE conta_id = ?", (conta.id,))
            for ticker, qtd in conta.posicoes.items():
                conn.execute(
                    "INSERT INTO posicoes_ativos (conta_id, ticker, quantidade) VALUES (?, ?, ?)",
                    (conta.id, ticker, qtd)
                )
            conn.commit()


class SqlOrdemRepository(IOrdemRepository):
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _row_to_ordem(row) -> Ordem:
        return Ordem(
            conta_id=row["conta_id"],
            ticker=row["ticker"],
            tipo=TipoOrdem(row["tipo"]),
            quantidade=row["quantidade"],
            preco=row["preco"],
            idempotency_key=row["idempotency_key"],
            status=StatusOrdem(row["status"]),
            entity_id=row["id"]
        )

    def salvar(self, ordem: Ordem) -> None:
        query = """
            INSERT INTO ordens (id, conta_id, ticker, tipo, quantidade, preco, idempotency_key, status, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (
                ordem.id,
                ordem.conta_id,
                ordem.ticker,
                ordem.tipo.value,
                ordem.quantidade,
                ordem.preco,
                ordem.idempotency_key,
                ordem.status.value,
                ordem.criado_em.isoformat()
            ))
            conn.commit()

    def atualizar(self, ordem: Ordem) -> None:
        # Permite atualizar tanto o status quanto quantidade/preço (caso a ordem ainda esteja pendente)
        query = """
            UPDATE ordens
            SET quantidade = ?, preco = ?, status = ?
            WHERE id = ?
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (
                ordem.quantidade,
                ordem.preco,
                ordem.status.value,
                ordem.id
            ))
            conn.commit()

    def buscar_por_id(self, ordem_id: str) -> Optional[Ordem]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute("SELECT * FROM ordens WHERE id = ?", (ordem_id,)).fetchone()
            return self._row_to_ordem(row) if row else None

    def buscar_por_idempotency_key(self, key: str) -> Optional[Ordem]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute("SELECT * FROM ordens WHERE idempotency_key = ?", (key,)).fetchone()
            return self._row_to_ordem(row) if row else None

    def listar_por_conta(self, conta_id: str) -> List[Ordem]:
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ordens WHERE conta_id = ? ORDER BY criado_em DESC",
                (conta_id,)
            ).fetchall()
            return [self._row_to_ordem(r) for r in rows]