from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict
import uuid

from src.domain.enums import TipoOrdem, StatusOrdem
from src.domain.exceptions import (
    SaldoInsuficienteError,
    LimiteRiscoExcedidoError,
    TransicaoEstadoInvalidaError,
    ValidacaoEntradaError
)

class EntidadeBase(ABC):
    """
    Classe Abstrata base para entidades do domínio.
    Garante que toda entidade tenha um identificador único e data de criação
    """
    def __init__(self, entity_id: str | None = None):
        self._id = entity_id or str(uuid.uuid4())
        self._criado_em = datetime.now()

    @property
    def id(self) -> str:
        return self._id

    @property
    def criado_em(self) -> datetime:
        return self._criado_em

    @abstractmethod
    def validar_integridade(self) -> None:
        """Contrato obrigatório para validação interna de cada entidade"""
        pass


class Investidor(EntidadeBase):
    """Representa o usuário investidor com dados sensíveis encapsulados"""
    def __init__(
        self,
        nome: str,
        email: str,
        senha_hash: str,
        mfa_secret: str,
        entity_id: str | None = None
    ):
        super().__init__(entity_id)
        self.__nome = nome
        self.__email = email
        self.__senha_hash = senha_hash
        self.__mfa_secret = mfa_secret
        self.validar_integridade()

    @property
    def nome(self) -> str:
        return self.__nome

    @property
    def email(self) -> str:
        return self.__email

    @property
    def senha_hash(self) -> str:
        return self.__senha_hash

    @property
    def mfa_secret(self) -> str:
        return self.__mfa_secret

    def validar_integridade(self) -> None:
        if not self.__nome or not self.__email or "@" not in self.__email:
            raise ValidacaoEntradaError("Dados básicos do investidor invalidos")


class ContaInvestimento(EntidadeBase):
    """
    Gerencia o saldo financeiro, limite de risco e a custódia (carteira) de ativos.
    O saldo e as posições só podem ser alterados via métodos de negócio validados
    """
    def __init__(
        self,
        investidor_id: str,
        saldo_inicial: float = 0.0,
        limite_por_ordem: float = 50000.0,
        posicoes: Dict[str, int] | None = None,
        entity_id: str | None = None
    ):
        super().__init__(entity_id)
        self.__investidor_id = investidor_id
        self.__saldo = float(saldo_inicial)
        self.__limite_por_ordem = float(limite_por_ordem)
        # Dicionário mapeando Ticker -> Quantidade (ex: {"PETR4": 100})
        self.__posicoes: Dict[str, int] = posicoes.copy() if posicoes else {}
        self.validar_integridade()

    @property
    def investidor_id(self) -> str:
        return self.__investidor_id

    @property
    def saldo(self) -> float:
        return self.__saldo

    @property
    def limite_por_ordem(self) -> float:
        return self.__limite_por_ordem

    @property
    def posicoes(self) -> Dict[str, int]:
        # Retorna uma cópia para evitar mutação externa indevida (encapsulamento)
        return self.__posicoes.copy()

    def validar_integridade(self) -> None:
        if self.__saldo < 0 or self.__limite_por_ordem <= 0:
            raise ValidacaoEntradaError("Saldo ou limite de risco inválido na conta.")

    def verificar_viabilidade_ordem(self, tipo: TipoOrdem, ticker: str, quantidade: int, preco: float) -> None:
        """Valida limites de risco, saldo financeiro (compra) e custódia (venda)."""
        valor_total = quantidade * preco

        if valor_total > self.__limite_por_ordem:
            raise LimiteRiscoExcedidoError(
                f"Valor da ordem (R$ {valor_total:.2f}) excede o limite de R$ {self.__limite_por_ordem:.2f}"
            )

        if tipo == TipoOrdem.COMPRA:
            if self.__saldo < valor_total:
                raise SaldoInsuficienteError("Saldo financeiro insuficiente para cobrir a ordem de compra")
        elif tipo == TipoOrdem.VENDA:
            qtd_atual = self.__posicoes.get(ticker, 0)
            if qtd_atual < quantidade:
                raise SaldoInsuficienteError(f"Quantidade insuficiente de {ticker} em custódia para venda")

    def debitar_saldo(self, valor: float) -> None:
        if valor <= 0 or self.__saldo < valor:
            raise SaldoInsuficienteError("Operação de débito inválida ou saldo insuficiente")
        self.__saldo -= valor

    def creditar_saldo(self, valor: float) -> None:
        if valor <= 0:
            raise ValidacaoEntradaError("Valor de crédito deve ser positivo")
        self.__saldo += valor

    def atualizar_posicao(self, ticker: str, delta_quantidade: int) -> None:
        """Adiciona (compra) ou remove (venda) ativos da carteira"""
        atual = self.__posicoes.get(ticker, 0)
        novo_saldo_ativo = atual + delta_quantidade
        if novo_saldo_ativo < 0:
            raise SaldoInsuficienteError(f"Posição de {ticker} não pode ficar negativa")
        if novo_saldo_ativo == 0:
            self.__posicoes.pop(ticker, None)
        else:
            self.__posicoes[ticker] = novo_saldo_ativo


class Ordem(EntidadeBase):
    """
    Representa uma ordem financeira com máquina de estados protegida
    e chave de idempotência para evitar duplicidade
    """
    def __init__(
        self,
        conta_id: str,
        ticker: str,
        tipo: TipoOrdem,
        quantidade: int,
        preco: float,
        idempotency_key: str,
        status: StatusOrdem = StatusOrdem.PENDENTE,
        entity_id: str | None = None
    ):
        super().__init__(entity_id)
        self.__conta_id = conta_id
        self.__ticker = ticker
        self.__tipo = tipo
        self.__quantidade = quantidade
        self.__preco = preco
        self.__idempotency_key = idempotency_key
        self.__status = status
        self.validar_integridade()

    @property
    def conta_id(self) -> str:
        return self.__conta_id

    @property
    def ticker(self) -> str:
        return self.__ticker

    @property
    def tipo(self) -> TipoOrdem:
        return self.__tipo

    @property
    def quantidade(self) -> int:
        return self.__quantidade

    @property
    def preco(self) -> float:
        return self.__preco

    @property
    def valor_total(self) -> float:
        return self.__quantidade * self.__preco

    @property
    def idempotency_key(self) -> str:
        return self.__idempotency_key

    @property
    def status(self) -> StatusOrdem:
        return self.__status

    def validar_integridade(self) -> None:
        if self.__quantidade <= 0 or self.__preco <= 0:
            raise ValidacaoEntradaError("Quantidade e preço da ordem devem ser maiores que zero.")
        if not self.__idempotency_key:
            raise ValidacaoEntradaError("Chave de idempotência é obrigatória.")

    def marcar_como_executada(self) -> None:
        if self.__status not in (StatusOrdem.PENDENTE, StatusOrdem.AGUARDANDO_ENVIO):
            raise TransicaoEstadoInvalidaError(f"Não é possível executar ordem no status {self.__status.value}.")
        self.__status = StatusOrdem.EXECUTADA

    def marcar_como_aguardando_envio(self) -> None:
        if self.__status != StatusOrdem.PENDENTE:
            raise TransicaoEstadoInvalidaError(f"Transição inválida de {self.__status.value} para AGUARDANDO_ENVIO.")
        self.__status = StatusOrdem.AGUARDANDO_ENVIO

    def cancelar(self) -> None:
        if self.__status not in (StatusOrdem.PENDENTE, StatusOrdem.AGUARDANDO_ENVIO):
            raise TransicaoEstadoInvalidaError(f"Ordem com status {self.__status.value} não pode ser cancelada.")
        self.__status = StatusOrdem.CANCELADA

    def rejeitar(self) -> None:
        if self.__status != StatusOrdem.PENDENTE:
            raise TransicaoEstadoInvalidaError(f"Ordem com status {self.__status.value} não pode ser rejeitada.")
        self.__status = StatusOrdem.REJEITADA