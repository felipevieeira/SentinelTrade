classDiagram
    direction TB

    %% --- DOMÍNIO (ENTIDADES E ENUMS) ---
    class EntidadeBase {
        <<Abstract>>
        #_id: str
        #_criado_em: datetime
        +id() str
        +criado_em() datetime
        +validar_integridade()* void
    }

    class Investidor {
        -__nome: str
        -__email: str
        -__senha_hash: str
        -__mfa_secret: str
        +nome() str
        +email() str
        +validar_integridade() void
    }

    class ContaInvestimento {
        -__investidor_id: str
        -__saldo: float
        -__limite_por_ordem: float
        -__posicoes: Dict~str, int~
        +saldo() float
        +posicoes() Dict~str, int~
        +verificar_viabilidade_ordem(tipo, ticker, qtd, preco) void
        +debitar_saldo(valor) void
        +creditar_saldo(valor) void
        +atualizar_posicao(ticker, delta) void
    }

    class Ordem {
        -__conta_id: str
        -__ticker: str
        -__tipo: TipoOrdem
        -__quantidade: int
        -__preco: float
        -__idempotency_key: str
        -__status: StatusOrdem
        +valor_total() float
        +marcar_como_executada() void
        +marcar_como_aguardando_envio() void
        +cancelar() void
        +rejeitar() void
    }

    class TipoOrdem {
        <<Enumeration>>
        COMPRA
        VENDA
    }

    class StatusOrdem {
        <<Enumeration>>
        PENDENTE
        AGUARDANDO_ENVIO
        EXECUTADA
        CANCELADA
        REJEITADA
    }

    %% --- INTERFACES (CONTRATOS) ---
    class IInvestidorRepository {
        <<Interface>>
        +salvar(investidor)* void
        +buscar_por_email(email)* Investidor
        +buscar_por_id(id)* Investidor
    }

    class IContaRepository {
        <<Interface>>
        +salvar(conta)* void
        +buscar_por_investidor_id(id)* ContaInvestimento
        +atualizar_saldo_e_posicoes(conta)* void
    }

    class IOrdemRepository {
        <<Interface>>
        +salvar(ordem)* void
        +atualizar(ordem)* void
        +buscar_por_id(id)* Ordem
        +buscar_por_idempotency_key(key)* Ordem
        +listar_por_conta(conta_id)* List~Ordem~
    }

    class IBolsaGateway {
        <<Interface>>
        +enviar_ordem(ordem)* bool
        +cancelar_ordem_na_bolsa(ordem_id)* bool
    }

    %% --- INFRAESTRUTURA ---
    class SqlInvestidorRepository {
        -db_manager: DatabaseManager
    }
    class SqlContaRepository {
        -db_manager: DatabaseManager
    }
    class SqlOrdemRepository {
        -db_manager: DatabaseManager
    }
    class BolsaSimuladaGateway {
        +simular_timeout: bool
    }

    %% --- SERVIÇOS ---
    class AuthService {
        +registrar_investidor(nome, email, senha) Tuple
        +autenticar_primeiro_fator(email, senha) Investidor
        +validar_segundo_fator_mfa(investidor, codigo) bool
    }

    class OrdemService {
        +criar_e_enviar_ordem(...) Ordem
        +atualizar_ordem_pendente(...) Ordem
        +cancelar_ordem(investidor_id, ordem_id) Ordem
        +consultar_ordens(investidor_id) List~Ordem~
    }

    class AuditService {
        +registrar_evento(evento, detalhes, investidor_id) void
    }

    %% --- RELACIONAMENTOS ---
    EntidadeBase <|-- Investidor : herda
    EntidadeBase <|-- ContaInvestimento : herda
    EntidadeBase <|-- Ordem : herda

    Investidor "1" -- "1" ContaInvestimento : possui
    ContaInvestimento "1" -- "0..*" Ordem : realiza
    Ordem --> TipoOrdem
    Ordem --> StatusOrdem

    IInvestidorRepository <|.. SqlInvestidorRepository : implementa
    IContaRepository <|.. SqlContaRepository : implementa
    IOrdemRepository <|.. SqlOrdemRepository : implementa
    IBolsaGateway <|.. BolsaSimuladaGateway : implementa

    AuthService --> IInvestidorRepository
    AuthService --> IContaRepository
    AuthService --> AuditService

    OrdemService --> IContaRepository
    OrdemService --> IOrdemRepository
    OrdemService --> IBolsaGateway
    OrdemService --> AuditService