from enum import Enum

class TipoOrdem(str, Enum):
    """Define os tipos permitidos de ordem (Allowlist)"""
    COMPRA = "COMPRA"
    VENDA = "VENDA"

class StatusOrdem(str, Enum):
    """Define a maquina de estados possivel para uma ordem"""
    PENDENTE = "PENDENTE"
    AGUARDANDO_ENVIO = "AGUARDANDO_ENVIO"
    EXECUTADA = "EXECUTADA"
    CANCELADA = "CANCELADA"
    REJEITADA = "REJEITADA"