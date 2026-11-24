from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities import Investidor, ContaInvestimento, Ordem

class IInvestidorRepository(ABC):
    @abstractmethod
    def salvar(self, investidor: Investidor) -> None:
        pass

    @abstractmethod
    def buscar_por_email(self, email: str) -> Optional[Investidor]:
        pass

    @abstractmethod
    def buscar_por_id(self, investidor_id: str) -> Optional[Investidor]:
        pass


class IContaRepository(ABC):
    @abstractmethod
    def salvar(self, conta: ContaInvestimento) -> None:
        pass

    @abstractmethod
    def buscar_por_investidor_id(self, investidor_id: str) -> Optional[ContaInvestimento]:
        pass

    @abstractmethod
    def atualizar_saldo_e_posicoes(self, conta: ContaInvestimento) -> None:
        pass


class IOrdemRepository(ABC):
    @abstractmethod
    def salvar(self, ordem: Ordem) -> None:
        pass

    @abstractmethod
    def atualizar(self, ordem: Ordem) -> None:
        pass

    @abstractmethod
    def buscar_por_id(self, ordem_id: str) -> Optional[Ordem]:
        pass

    @abstractmethod
    def buscar_por_idempotency_key(self, key: str) -> Optional[Ordem]:
        pass

    @abstractmethod
    def listar_por_conta(self, conta_id: str) -> List[Ordem]:
        pass