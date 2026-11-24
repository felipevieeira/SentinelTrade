import os
import unittest
import uuid

from src.domain.enums import StatusOrdem
from src.domain.exceptions import (
    SaldoInsuficienteError,
    LimiteRiscoExcedidoError,
    TransicaoEstadoInvalidaError,
    ValidacaoEntradaError
)
from src.infrastructure.bolsa_simulada import BolsaSimuladaGateway
from src.infrastructure.database import DatabaseManager
from src.infrastructure.sql_repositories import (
    SqlInvestidorRepository,
    SqlContaRepository,
    SqlOrdemRepository
)
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.services.ordem_service import OrdemService


class TestOrdemService(unittest.TestCase):
    def setUp(self):
        # Usa um banco temporário isolado para cada teste não interferir no outro
        self.test_db = "test_sentinel.db"
        self.test_log = "test_audit.log"
        self.db = DatabaseManager(self.test_db)
        self.db.inicializar_tabelas()

        self.inv_repo = SqlInvestidorRepository(self.db)
        self.conta_repo = SqlContaRepository(self.db)
        self.ordem_repo = SqlOrdemRepository(self.db)
        self.audit = AuditService(self.db, self.test_log)
        self.auth = AuthService(self.inv_repo, self.conta_repo, self.audit)
        self.bolsa = BolsaSimuladaGateway(simular_timeout=False)
        self.ordem_service = OrdemService(self.conta_repo, self.ordem_repo, self.bolsa, self.audit)

        self.investidor, self.conta = self.auth.registrar_investidor(
            "Felipe Castro", "felipe@teste.com", "SenhaForte123", saldo_inicial=10000.0
        )

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        if os.path.exists(self.test_log):
            os.remove(self.test_log)

    def test_compra_sucesso_atualiza_saldo_e_custodia(self):
        ordem = self.ordem_service.criar_e_enviar_ordem(
            self.investidor.id, "PETR4", "COMPRA", 100, 30.0, str(uuid.uuid4())
        )
        self.assertEqual(ordem.status, StatusOrdem.EXECUTADA)

        conta_atualizada = self.conta_repo.buscar_por_investidor_id(self.investidor.id)
        self.assertEqual(conta_atualizada.saldo, 7000.0)
        self.assertEqual(conta_atualizada.posicoes["PETR4"], 100)

    def test_bloqueia_compra_sem_saldo_suficiente(self):
        with self.assertRaises(SaldoInsuficienteError):
            self.ordem_service.criar_e_enviar_ordem(
                self.investidor.id, "VALE3", "COMPRA", 500, 50.0, str(uuid.uuid4())
            )

    def test_bloqueia_venda_sem_ativos_em_custodia(self):
        with self.assertRaises(SaldoInsuficienteError):
            self.ordem_service.criar_e_enviar_ordem(
                self.investidor.id, "PETR4", "VENDA", 10, 35.0, str(uuid.uuid4())
            )

    def test_bloqueia_ordem_acima_do_limite_de_risco(self):
        with self.assertRaises(LimiteRiscoExcedidoError):
            # Limite padrão da conta é R$ 50.000
            self.ordem_service.criar_e_enviar_ordem(
                self.investidor.id, "WEGE3", "COMPRA", 2000, 50.0, str(uuid.uuid4())
            )

    def test_prevencao_duplicidade_por_idempotency_key(self):
        chave_unica = str(uuid.uuid4())
        ordem1 = self.ordem_service.criar_e_enviar_ordem(
            self.investidor.id, "ITUB4", "COMPRA", 10, 30.0, chave_unica
        )
        # Reenvia exatamente a mesma chave
        ordem2 = self.ordem_service.criar_e_enviar_ordem(
            self.investidor.id, "ITUB4", "COMPRA", 10, 30.0, chave_unica
        )
        self.assertEqual(ordem1.id, ordem2.id)

        # Garante que o saldo foi debitado apenas uma vez (10000 - 300 = 9700)
        conta = self.conta_repo.buscar_por_investidor_id(self.investidor.id)
        self.assertEqual(conta.saldo, 9700.0)

    def test_transicao_estado_timeout_e_cancelamento(self):
        # Simula queda da bolsa para a ordem ficar AGUARDANDO_ENVIO
        self.bolsa.simular_timeout = True
        ordem = self.ordem_service.criar_e_enviar_ordem(
            self.investidor.id, "MXRF11", "COMPRA", 50, 10.0, str(uuid.uuid4())
        )
        self.assertEqual(ordem.status, StatusOrdem.AGUARDANDO_ENVIO)

        # Cancela enquanto ainda não foi executada
        ordem_cancelada = self.ordem_service.cancelar_ordem(self.investidor.id, ordem.id)
        self.assertEqual(ordem_cancelada.status, StatusOrdem.CANCELADA)

        # Tentar cancelar novamente deve falhar na máquina de estados
        with self.assertRaises(TransicaoEstadoInvalidaError):
            self.ordem_service.cancelar_ordem(self.investidor.id, ordem.id)

    def test_rejeita_sql_injection_no_ticker(self):
        with self.assertRaises(ValidacaoEntradaError):
            self.ordem_service.criar_e_enviar_ordem(
                self.investidor.id, "PETR4'; DROP TABLE ordens;--", "COMPRA", 10, 30.0, str(uuid.uuid4())
            )


if __name__ == "__main__":
    unittest.main()