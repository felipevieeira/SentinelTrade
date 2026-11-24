class SentinelTradeError(Exception):
    """Classe base para todas as exceções de negócio do sistema"""
    pass

class ValidacaoEntradaError(SentinelTradeError):
    """Lançada quando um dado não passa na sanitização ou regra de formato"""
    pass

class SaldoInsuficienteError(SentinelTradeError):
    """Lançada quando o investidor tenta operar sem saldo ou ativos suficientes"""
    pass

class LimiteRiscoExcedidoError(SentinelTradeError):
    """Lançada quando o valor financeiro da ordem ultrapassa o limite permitido"""
    pass

class TransicaoEstadoInvalidaError(SentinelTradeError):
    """Lançada ao tentar cancelar ou alterar uma ordem já executada/cancelada"""
    pass

class AutenticacaoError(SentinelTradeError):
    """Lançada em falhas de login ou token MFA inválido."""
    pass