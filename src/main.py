import uuid
from src.domain.exceptions import SentinelTradeError
from src.infrastructure.bolsa_simulada import BolsaSimuladaGateway, CotacaoProviderSimulado
from src.infrastructure.database import DatabaseManager
from src.infrastructure.sql_repositories import (
    SqlInvestidorRepository,
    SqlContaRepository,
    SqlOrdemRepository
)
from src.services.audit_service import AuditService
from src.services.auth_service import AuthService
from src.services.ordem_service import OrdemService


def executar_cli():
    db = DatabaseManager("sentinel_trade.db")
    db.inicializar_tabelas()

    investidor_repo = SqlInvestidorRepository(db)
    conta_repo = SqlContaRepository(db)
    ordem_repo = SqlOrdemRepository(db)

    audit_service = AuditService(db)
    auth_service = AuthService(investidor_repo, conta_repo, audit_service)
    bolsa_gateway = BolsaSimuladaGateway(simular_timeout=False)
    cotacao_provider = CotacaoProviderSimulado()
    ordem_service = OrdemService(conta_repo, ordem_repo, bolsa_gateway, audit_service)

    investidor_logado = None

    while True:
        print("\n=== SENTINELTRADE - PLATAFORMA DE OPERAÇÕES ===")
        if not investidor_logado:
            print("1. Cadastrar Investidor")
            print("2. Login (com MFA)")
            print("0. Sair")
            opcao = input("Escolha uma opção: ").strip()

            try:
                if opcao == "1":
                    nome = input("Nome completo: ")
                    email = input("E-mail: ")
                    senha = input("Senha (mín. 8 chars, maiúscula, minúscula e número): ")
                    inv, conta = auth_service.registrar_investidor(nome, email, senha)
                    print(f"\n[OK] Cadastro concluído! Saldo inicial: R$ {conta.saldo:.2f}")

                elif opcao == "2":
                    email = input("E-mail: ")
                    senha = input("Senha: ")
                    candidato = auth_service.autenticar_primeiro_fator(email, senha)

                    # Em ambiente real o token iria para o app autenticador; aqui exibimos para simulação
                    token_simulado = auth_service.gerar_codigo_totp_atual(candidato.mfa_secret)
                    print(f"[SIMULAÇÃO MFA - Código no seu dispositivo]: {token_simulado}")

                    codigo = input("Digite o token MFA de 6 dígitos: ")
                    if auth_service.validar_segundo_fator_mfa(candidato, codigo):
                        investidor_logado = candidato
                        print(f"\n[OK] Bem-vindo(a), {investidor_logado.nome}!")

                elif opcao == "0":
                    print("Encerrando SentinelTrade...")
                    break
                else:
                    print("Opção inválida.")

            except SentinelTradeError as e:
                print(f"\n[AVISO DE SEGURANÇA/NEGÓCIO]: {e}")
            except Exception:
                # Nunca expõe detalhes internos ou stack trace na interface
                print("\n[ERRO]: Não foi possível processar a solicitação.")

        else:
            conta = conta_repo.buscar_por_investidor_id(investidor_logado.id)
            print(f"Investidor: {investidor_logado.nome} | Saldo: R$ {conta.saldo:.2f} | Custódia: {conta.posicoes}")
            print("1. Consultar Cotação")
            print("2. Enviar Ordem (Compra/Venda)")
            print("3. Listar Minhas Ordens")
            print("4. Cancelar Ordem")
            print("5. Alternar Simulação de Queda da Bolsa (Timeout)")
            print("9. Logout")
            opcao = input("Escolha uma opção: ").strip()

            try:
                if opcao == "1":
                    ticker = input("Código do ativo (ex: PETR4): ")
                    preco = cotacao_provider.obter_cotacao_atual(ticker)
                    print(f"Cotação atual de {ticker.upper()}: R$ {preco:.2f}")

                elif opcao == "2":
                    ticker = input("Código do ativo (ex: PETR4): ")
                    tipo = input("Tipo (COMPRA ou VENDA): ")
                    qtd = int(input("Quantidade: "))
                    preco = float(input("Preço unitário: "))
                    chave = str(uuid.uuid4())
                    ordem = ordem_service.criar_e_enviar_ordem(
                        investidor_logado.id, ticker, tipo, qtd, preco, chave
                    )
                    print(f"\n[OK] Ordem {ordem.id} registrada com status: {ordem.status.value}")

                elif opcao == "3":
                    ordens = ordem_service.consultar_ordens(investidor_logado.id)
                    if not ordens:
                        print("Nenhuma ordem encontrada.")
                    for o in ordens:
                        print(f"- ID: {o.id} | {o.tipo.value} {o.quantidade}x {o.ticker} @ R$ {o.preco:.2f} | Status: {o.status.value}")

                elif opcao == "4":
                    ordem_id = input("ID da ordem para cancelar: ").strip()
                    ordem = ordem_service.cancelar_ordem(investidor_logado.id, ordem_id)
                    print(f"\n[OK] Ordem {ordem.id} agora está {ordem.status.value}.")

                elif opcao == "5":
                    bolsa_gateway.simular_timeout = not bolsa_gateway.simular_timeout
                    estado = "ATIVADA (Bolsa offline)" if bolsa_gateway.simular_timeout else "DESATIVADA (Bolsa online)"
                    print(f"\n[INFO] Simulação de timeout da Bolsa: {estado}")

                elif opcao == "9":
                    investidor_logado = None
                    print("Sessão encerrada.")
                else:
                    print("Opção inválida.")

            except ValueError:
                print("\n[ERRO DE ENTRADA]: Verifique os valores numéricos informados.")
            except SentinelTradeError as e:
                print(f"\n[AVISO DE SEGURANÇA/NEGÓCIO]: {e}")
            except Exception:
                print("\n[ERRO]: Falha inesperada ao executar operação.")


if __name__ == "__main__":
    executar_cli()