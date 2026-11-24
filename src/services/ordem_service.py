from typing import List
from src.domain.entities import Ordem
from src.domain.enums import TipoOrdem, StatusOrdem
from src.domain.exceptions import (
    SentinelTradeError,
    TransicaoEstadoInvalidaError,
    ValidacaoEntradaError
)
from src.interfaces.gateways import IBolsaGateway
from src.interfaces.repositories import IContaRepository, IOrdemRepository
from src.security.validators import SecurityValidator
from src.services.audit_service import AuditService


class OrdemService:
    def __init__(
        self,
        conta_repo: IContaRepository,
        ordem_repo: IOrdemRepository,
        bolsa_gateway: IBolsaGateway,
        audit_service: AuditService
    ):
        self.conta_repo = conta_repo
        self.ordem_repo = ordem_repo
        self.bolsa_gateway = bolsa_gateway
        self.audit_service = audit_service

    def criar_e_enviar_ordem(
        self,
        investidor_id: str,
        ticker: str,
        tipo_str: str,
        quantidade: int,
        preco: float,
        idempotency_key: str
    ) -> Ordem:
        # 1. Sanitização e validação estrita de todas as entradas
        ticker_valido = SecurityValidator.validar_ticker(ticker)
        tipo_valido = SecurityValidator.validar_tipo_ordem(tipo_str)
        qtd_valida = SecurityValidator.validar_quantidade(quantidade)
        preco_valido = SecurityValidator.validar_preco(preco)
        chave_valida = SecurityValidator.validar_idempotency_key(idempotency_key)

        # 2. Checagem de idempotência: se o usuário deu duplo clique ou reenviou a mesma requisição,
        # devolvemos a ordem já registrada em vez de cobrar duas vezes
        ordem_existente = self.ordem_repo.buscar_por_idempotency_key(chave_valida)
        if ordem_existente:
            self.audit_service.registrar_evento(
                "ORDEM_DUPLICADA_BLOQUEADA",
                f"Reenvio ignorado para chave {chave_valida}. Retornando ordem {ordem_existente.id}.",
                investidor_id
            )
            return ordem_existente

        # 3. Busca a conta e verifica saldo, custódia e limite de risco
        conta = self.conta_repo.buscar_por_investidor_id(investidor_id)
        if not conta:
            raise SentinelTradeError("Conta de investimento não encontrada.")

        conta.verificar_viabilidade_ordem(tipo_valido, ticker_valido, qtd_valida, preco_valido)

        # 4. Cria a ordem como PENDENTE e salva no banco antes de falar com a bolsa
        ordem = Ordem(
            conta_id=conta.id,
            ticker=ticker_valido,
            tipo=tipo_valido,
            quantidade=qtd_valida,
            preco=preco_valido,
            idempotency_key=chave_valida,
            status=StatusOrdem.PENDENTE
        )
        self.ordem_repo.salvar(ordem)

        # 5. Envia para a Bolsa Simulada e trata o retorno
        executou = self.bolsa_gateway.enviar_ordem(ordem)

        if executou:
            ordem.marcar_como_executada()
            # Liquida financeiramente na conta do investidor
            if tipo_valido == TipoOrdem.COMPRA:
                conta.debitar_saldo(ordem.valor_total)
                conta.atualizar_posicao(ticker_valido, qtd_valida)
            else:
                conta.atualizar_posicao(ticker_valido, -qtd_valida)
                conta.creditar_saldo(ordem.valor_total)

            self.conta_repo.atualizar_saldo_e_posicoes(conta)
            self.ordem_repo.atualizar(ordem)
            self.audit_service.registrar_evento(
                "ORDEM_EXECUTADA",
                f"{tipo_valido.value} {qtd_valida}x {ticker_valido} @ R$ {preco_valido:.2f}",
                investidor_id
            )
        else:
            # Se a bolsa não respondeu (timeout), a ordem não se perde: fica na fila para reenvio
            ordem.marcar_como_aguardando_envio()
            self.ordem_repo.atualizar(ordem)
            self.audit_service.registrar_evento(
                "ORDEM_TIMEOUT_BOLSA",
                f"Ordem {ordem.id} movida para AGUARDANDO_ENVIO por indisponibilidade da bolsa.",
                investidor_id
            )

        return ordem

    def atualizar_ordem_pendente(
        self,
        investidor_id: str,
        ordem_id: str,
        nova_quantidade: int,
        novo_preco: float
    ) -> Ordem:
        qtd_valida = SecurityValidator.validar_quantidade(nova_quantidade)
        preco_valido = SecurityValidator.validar_preco(novo_preco)

        conta = self.conta_repo.buscar_por_investidor_id(investidor_id)
        ordem = self.ordem_repo.buscar_por_id(ordem_id)

        if not conta or not ordem or ordem.conta_id != conta.id:
            raise ValidacaoEntradaError("Ordem não encontrada para este investidor.")

        # Só faz sentido editar ordens que ainda não foram executadas nem canceladas
        if ordem.status not in (StatusOrdem.PENDENTE, StatusOrdem.AGUARDANDO_ENVIO):
            raise TransicaoEstadoInvalidaError(
                f"Não é possível alterar uma ordem com status {ordem.status.value}."
            )

        conta.verificar_viabilidade_ordem(ordem.tipo, ordem.ticker, qtd_valida, preco_valido)

        ordem_atualizada = Ordem(
            conta_id=ordem.conta_id,
            ticker=ordem.ticker,
            tipo=ordem.tipo,
            quantidade=qtd_valida,
            preco=preco_valido,
            idempotency_key=ordem.idempotency_key,
            status=ordem.status,
            entity_id=ordem.id
        )
        self.ordem_repo.atualizar(ordem_atualizada)
        self.audit_service.registrar_evento(
            "ORDEM_ATUALIZADA",
            f"Ordem {ordem.id} alterada para {qtd_valida}x @ R$ {preco_valido:.2f}",
            investidor_id
        )
        return ordem_atualizada

    def cancelar_ordem(self, investidor_id: str, ordem_id: str) -> Ordem:
        conta = self.conta_repo.buscar_por_investidor_id(investidor_id)
        ordem = self.ordem_repo.buscar_por_id(ordem_id)

        if not conta or not ordem or ordem.conta_id != conta.id:
            raise ValidacaoEntradaError("Ordem não encontrada para este investidor.")

        # A própria entidade Ordem valida se a transição de estado é permitida
        ordem.cancelar()
        self.bolsa_gateway.cancelar_ordem_na_bolsa(ordem.id)
        self.ordem_repo.atualizar(ordem)

        self.audit_service.registrar_evento(
            "ORDEM_CANCELADA",
            f"Ordem {ordem.id} ({ordem.ticker}) cancelada pelo investidor.",
            investidor_id
        )
        return ordem

    def consultar_ordens(self, investidor_id: str) -> List[Ordem]:
        conta = self.conta_repo.buscar_por_investidor_id(investidor_id)
        if not conta:
            return []
        return self.ordem_repo.listar_por_conta(conta.id)