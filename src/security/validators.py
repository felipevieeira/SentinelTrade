import html
import re
import time
from typing import Dict, List
from src.domain.enums import TipoOrdem
from src.domain.exceptions import ValidacaoEntradaError

class SecurityValidator:
    """
    Centraliza todas as regras de sanitização e validação de entradas (Server-Side)
    e codificação segura de saídas.
    """

    # Allowlists e padrões estritos (Regex)
    REGEX_TICKER = re.compile(r"^[A-Z]{4}[0-9]{1,2}$")  # Ex: PETR4, VALE3, MXRF11
    REGEX_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    REGEX_NOME = re.compile(r"^[a-zA-ZÀ-ÿ\s]{2,80}$")
    REGEX_MFA = re.compile(r"^[0-9]{6}$")
    REGEX_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    # Limites operacionais de segurança
    MAX_QUANTIDADE = 1_000_000
    MAX_PRECO = 1_000_000.0
    MAX_TAMANHO_PAYLOAD = 255

    @classmethod
    def validar_ticker(cls, ticker: str) -> str:
        """Valida e normaliza o código do ativo contra allowlist de formato."""
        if not isinstance(ticker, str):
            raise ValidacaoEntradaError("Ticker deve ser uma string.")
        ticker_limpo = ticker.strip().upper()
        if not cls.REGEX_TICKER.match(ticker_limpo):
            raise ValidacaoEntradaError(f"Código de ativo inválido: '{ticker}'. Esperado padrão como PETR4 ou MXRF11.")
        return ticker_limpo

    @classmethod
    def validar_tipo_ordem(cls, tipo: str) -> TipoOrdem:
        """Aplica allowlist estrita para o tipo de ordem."""
        if not isinstance(tipo, str):
            raise ValidacaoEntradaError("Tipo de ordem inválido.")
        try:
            return TipoOrdem(tipo.strip().upper())
        except ValueError:
            raise ValidacaoEntradaError("Tipo de ordem não permitido. Use apenas COMPRA ou VENDA.")

    @classmethod
    def validar_quantidade(cls, quantidade: int) -> int:
        """Garante que a quantidade seja inteiro positivo dentro do teto operacional."""
        if isinstance(quantidade, bool) or not isinstance(quantidade, int):
            raise ValidacaoEntradaError("Quantidade deve ser um número inteiro.")
        if quantidade <= 0 or quantidade > cls.MAX_QUANTIDADE:
            raise ValidacaoEntradaError(f"Quantidade deve estar entre 1 e {cls.MAX_QUANTIDADE}.")
        return quantidade

    @classmethod
    def validar_preco(cls, preco: float) -> float:
        """Garante que o preço seja numérico positivo e finito."""
        if isinstance(preco, bool) or not isinstance(preco, (int, float)):
            raise ValidacaoEntradaError("Preço deve ser numérico.")
        preco_float = float(preco)
        if preco_float <= 0 or preco_float > cls.MAX_PRECO:
            raise ValidacaoEntradaError(f"Preço deve ser maior que 0 e menor que {cls.MAX_PRECO}.")
        return round(preco_float, 2)

    @classmethod
    def validar_email(cls, email: str) -> str:
        if not isinstance(email, str) or len(email) > cls.MAX_TAMANHO_PAYLOAD:
            raise ValidacaoEntradaError("E-mail inválido ou excede o tamanho máximo.")
        email_limpo = email.strip().lower()
        if not cls.REGEX_EMAIL.match(email_limpo):
            raise ValidacaoEntradaError("Formato de e-mail inválido.")
        return email_limpo

    @classmethod
    def validar_senha_forte(cls, senha: str) -> str:
        """Exige política mínima de complexidade de senha."""
        if not isinstance(senha, str) or len(senha) < 8 or len(senha) > 128:
            raise ValidacaoEntradaError("A senha deve ter entre 8 e 128 caracteres.")
        if not re.search(r"[A-Z]", senha) or not re.search(r"[a-z]", senha) or not re.search(r"[0-9]", senha):
            raise ValidacaoEntradaError("A senha deve conter letras maiúsculas, minúsculas e números.")
        return senha

    @classmethod
    def validar_codigo_mfa(cls, codigo: str) -> str:
        if not isinstance(codigo, str) or not cls.REGEX_MFA.match(codigo.strip()):
            raise ValidacaoEntradaError("Token MFA deve conter exatamente 6 dígitos numéricos.")
        return codigo.strip()

    @classmethod
    def validar_idempotency_key(cls, chave: str) -> str:
        if not isinstance(chave, str) or not cls.REGEX_UUID.match(chave.strip().lower()):
            raise ValidacaoEntradaError("Chave de idempotência inválida (UUID v4 esperado).")
        return chave.strip().lower()

    @staticmethod
    def sanitizar_texto_saida(texto: str) -> str:
        """Escapa caracteres especiais para evitar XSS/injeção em logs e interfaces."""
        if not isinstance(texto, str):
            return ""
        # Remove quebras de linha para evitar Log Injection e escapa HTML
        sem_quebras = texto.replace("\n", " ").replace("\r", " ")
        return html.escape(sem_quebras, quote=True)

    @staticmethod
    def validar_caminho_seguro(nome_arquivo: str) -> str:
        """Rejeita tentativas de Path Traversal (../) ou caminhos absolutos."""
        if not isinstance(nome_arquivo, str) or ".." in nome_arquivo or "/" in nome_arquivo or "\\" in nome_arquivo:
            raise ValidacaoEntradaError("Nome de arquivo inseguro ou inválido.")
        return nome_arquivo


class RateLimiter:
    """
    Controla a frequência de tentativas (ex: login/MFA ou envio de ordens)
    para mitigar força bruta e spam de requisições.
    """
    def __init__(self, max_tentativas: int = 3, janela_segundos: int = 60):
        self.max_tentativas = max_tentativas
        self.janela_segundos = janela_segundos
        self._historico: Dict[str, List[float]] = {}

    def verificar_e_registrar(self, chave_identificadora: str) -> bool:
        """
        Retorna True se a ação é permitida, ou False se o limite foi excedido.
        """
        agora = time.time()
        tentativas = self._historico.get(chave_identificadora, [])
        # Filtra apenas tentativas dentro da janela de tempo ativa
        tentativas_validas = [t for t in tentativas if (agora - t) < self.janela_segundos]

        if len(tentativas_validas) >= self.max_tentativas:
            self._historico[chave_identificadora] = tentativas_validas
            return False

        tentativas_validas.append(agora)
        self._historico[chave_identificadora] = tentativas_validas
        return True

    def resetar(self, chave_identificadora: str) -> None:
        self._historico.pop(chave_identificadora, None)