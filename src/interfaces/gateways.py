from abc import ABC, abstractmethod
from src.domain.entities import Ordem

class IBolsaGateway(ABC):
    @abstractmethod
    def enviar_ordem(self, ordem: Ordem) -> bool:
        """Envia a ordem para execução. Retorna True se executada ou False se houve timeout."""
        pass

    @abstractmethod
    def cancelar_ordem_na_bolsa(self, ordem_id: str) -> bool:
        pass


class ICotacaoProvider(ABC):
    @abstractmethod
    def obter_cotacao_atual(self, ticker: str) -> float:
        pass