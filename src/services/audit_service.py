from datetime import datetime
from src.infrastructure.database import DatabaseManager
from src.security.validators import SecurityValidator

class AuditService:
    """Registra trilhas de auditoria imutáveis para eventos críticos do sistema."""

    def __init__(self, db_manager: DatabaseManager, log_file: str = "audit.log"):
        self.db_manager = db_manager
        self.log_file = SecurityValidator.validar_caminho_seguro(log_file)

    def registrar_evento(self, evento: str, detalhes: str, investidor_id: str | None = None) -> None:
        timestamp = datetime.now().isoformat()
        evento_seguro = SecurityValidator.sanitizar_texto_saida(evento)
        detalhes_seguros = SecurityValidator.sanitizar_texto_saida(detalhes)

        # 1. Persistência relacional parametrizada (zero SQL Injection)
        query = """
            INSERT INTO logs_auditoria (timestamp, investidor_id, evento, detalhes)
            VALUES (?, ?, ?, ?)
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (timestamp, investidor_id, evento_seguro, detalhes_seguros))
            conn.commit()

        # 2. Gravação em arquivo local em modo append
        linha_log = f"[{timestamp}] [USER:{investidor_id or 'ANONIMO'}] [{evento_seguro}] {detalhes_seguros}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(linha_log)