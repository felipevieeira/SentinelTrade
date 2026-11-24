import hashlib
import hmac
import secrets
import struct
import time
from typing import Tuple

from src.domain.entities import Investidor, ContaInvestimento
from src.domain.exceptions import AutenticacaoError, ValidacaoEntradaError
from src.interfaces.repositories import IInvestidorRepository, IContaRepository
from src.security.validators import SecurityValidator, RateLimiter
from src.services.audit_service import AuditService


class AuthService:
    """Gerencia cadastro, hash de senhas, autenticação e segundo fator (MFA)."""

    def __init__(
        self,
        investidor_repo: IInvestidorRepository,
        conta_repo: IContaRepository,
        audit_service: AuditService
    ):
        self.investidor_repo = investidor_repo
        self.conta_repo = conta_repo
        self.audit_service = audit_service
        # Bloqueia após 3 tentativas falhas dentro de 60 segundos
        self.rate_limiter = RateLimiter(max_tentativas=3, janela_segundos=60)

    @staticmethod
    def _gerar_hash_senha(senha: str) -> str:
        """Gera hash PBKDF2-SHA256 com salt criptográfico único."""
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"{salt}${dk.hex()}"

    @staticmethod
    def _verificar_senha(senha_fornecida: str, hash_armazenado: str) -> bool:
        """Compara hashes em tempo constante para mitigar Timing Attacks."""
        try:
            salt, hash_original = hash_armazenado.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", senha_fornecida.encode("utf-8"), salt.encode("utf-8"), 100_000)
            return hmac.compare_digest(dk.hex(), hash_original)
        except ValueError:
            return False

    @staticmethod
    def gerar_codigo_totp_atual(mfa_secret: str, janela_offset: int = 0) -> str:
        """
        Gera um token MFA de 6 dígitos válido por janelas de 30 segundos (padrão RFC 6238).
        """
        contador = int(time.time() // 30) + janela_offset
        msg = struct.pack(">Q", contador)
        digest = hmac.new(mfa_secret.encode("utf-8"), msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        codigo_binario = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
        return f"{codigo_binario % 1_000_000:06d}"

    def registrar_investidor(
        self,
        nome: str,
        email: str,
        senha: str,
        saldo_inicial: float = 10000.0
    ) -> Tuple[Investidor, ContaInvestimento]:
        """Valida entradas, cria o investidor com segredo MFA e abre sua conta."""
        email_valido = SecurityValidator.validar_email(email)
        senha_valida = SecurityValidator.validar_senha_forte(senha)
        if not SecurityValidator.REGEX_NOME.match(nome.strip()):
            raise ValidacaoEntradaError("Nome inválido. Use apenas letras e espaços (2 a 80 caracteres).")

        if self.investidor_repo.buscar_por_email(email_valido):
            raise ValidacaoEntradaError("Já existe um cadastro com este e-mail.")

        senha_hash = self._gerar_hash_senha(senha_valida)
        mfa_secret = secrets.token_hex(16)

        investidor = Investidor(
            nome=nome.strip(),
            email=email_valido,
            senha_hash=senha_hash,
            mfa_secret=mfa_secret
        )
        self.investidor_repo.salvar(investidor)

        conta = ContaInvestimento(investidor_id=investidor.id, saldo_inicial=saldo_inicial)
        self.conta_repo.salvar(conta)

        self.audit_service.registrar_evento(
            "CADASTRO_INVESTIDOR",
            f"Novo investidor registrado: {email_valido}",
            investidor.id
        )
        return investidor, conta

    def autenticar_primeiro_fator(self, email: str, senha: str) -> Investidor:
        """Valida e-mail e senha respeitando o limite de tentativas."""
        email_valido = SecurityValidator.validar_email(email)

        if not self.rate_limiter.verificar_e_registrar(f"login:{email_valido}"):
            self.audit_service.registrar_evento("BLOQUEIO_RATE_LIMIT", f"Excesso de tentativas para {email_valido}")
            raise AutenticacaoError("Muitas tentativas falhas. Aguarde 60 segundos antes de tentar novamente.")

        investidor = self.investidor_repo.buscar_por_email(email_valido)
        if not investidor or not self._verificar_senha(senha, investidor.senha_hash):
            self.audit_service.registrar_evento("FALHA_LOGIN", f"Credenciais inválidas para {email_valido}")
            raise AutenticacaoError("E-mail ou senha incorretos.")

        return investidor

    def validar_segundo_fator_mfa(self, investidor: Investidor, codigo_mfa: str) -> bool:
        """Valida o token de 6 dígitos (aceitando janela atual e anterior por tolerância de clock)."""
        codigo_limpo = SecurityValidator.validar_codigo_mfa(codigo_mfa)

        if not self.rate_limiter.verificar_e_registrar(f"mfa:{investidor.id}"):
            self.audit_service.registrar_evento(
                "BLOQUEIO_MFA",
                "Excesso de tentativas inválidas de MFA.",
                investidor.id
            )
            raise AutenticacaoError("Bloqueio temporário por excesso de erros no código MFA.")

        token_atual = self.gerar_codigo_totp_atual(investidor.mfa_secret, 0)
        token_anterior = self.gerar_codigo_totp_atual(investidor.mfa_secret, -1)

        if hmac.compare_digest(codigo_limpo, token_atual) or hmac.compare_digest(codigo_limpo, token_anterior):
            # Limpa contadores de falha após sucesso completo
            self.rate_limiter.resetar(f"login:{investidor.email}")
            self.rate_limiter.resetar(f"mfa:{investidor.id}")
            self.audit_service.registrar_evento("LOGIN_MFA_SUCESSO", "Autenticação completa realizada.", investidor.id)
            return True

        self.audit_service.registrar_evento("FALHA_MFA", "Código MFA inválido ou expirado.", investidor.id)
        raise AutenticacaoError("Código MFA inválido ou expirado.")