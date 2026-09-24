Requisitos funcionais:

    ID   |              RF             |  Descrição
RF-01    | Autentificação dos usuários | O sistema deve permitir a autenticação dos usuários utilizando MFA
RF-02    | API                         | O sistema deve receber cotações em tempo real através de uma API externa
RF-03    | Gestão de contas            | O sistema deve manter dados das contas, carteiras, investidores, ativos, etc.
RF-04    | Ordens                      | Deve perimitir ordens de compra, venda, cancelamento e consulta
RF-05    | Validação de operações      | O sistema deve validar saldo e limites antes do processamento de uma operação
RF-06    | Histórico, notificações     | O sistema deve permitir a consulta do histórico de operações, acompanhamento de ordens, 
         | e auditoria                 | envio de notificações e registro de eventos para auditoria.


Requisitos não-funcionais:
    ID   |              RF             |  Descrição
RNF-01   | Segurança                   | O sistema deve proteger as senhas e os dados dos usuários.
RNF-02   | Resiliência                 | O sistema deve realizar novas tentativas em caso de falha na comunicação com as APIs.
RNF-03   | Consistência                | O sistema deve evitar o processamento duplicado de ordens e manter os dados atualizados.
RNF-04   | Disponibilidade             | O sistema deve continuar funcionando de forma consistente mesmo quando ocorrerem falhas 
         |                             | em algum serviço.
RNF-05   | Auditoria                   | O sistema deve registrar as operações realizadas pelos usuários para permitir o        
         |                             | acompanhamento e a verificação das ações.