from src.domain.entities import Ordem
from src.domain.exceptions import ValidacaoEntradaError
from src.interfaces.gateways import IBolsaGateway, ICotacaoProvider
from src.security.validators import SecurityValidator


class BolsaSimuladaGateway(IBolsaGateway):
    def __init__(self, simular_timeout: bool = False):
        self.simular_timeout = simular_timeout

    def enviar_ordem(self, ordem: Ordem) -> bool:
        if self.simular_timeout:
            return False
        return True

    def cancelar_ordem_na_bolsa(self, ordem_id: str) -> bool:
        return not self.simular_timeout


class CotacaoProviderSimulado(ICotacaoProvider):
    _PRECOS_MOCK = {
        "PETR4": 38.50,
        "VALE3": 62.10,
        "ITUB4": 34.20,
        "WEGE3": 53.80,
        "MXRF11": 10.15
    }

    def obter_cotacao_atual(self, ticker: str) -> float:
        ticker_valido = SecurityValidator.validar_ticker(ticker)
        preco_externo = self._PRECOS_MOCK.get(ticker_valido, 25.00)

        if not isinstance(preco_externo, (int, float)) or preco_externo <= 0:
            raise ValidacaoEntradaError("Cotação inválida recebida do provedor externo.")

        return SecurityValidator.validar_preco(preco_externo)