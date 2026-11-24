# Finanças da Família — Especificação

## Visão geral

Um app de finanças para uma família em que lançar uma despesa é mandar uma mensagem: sem instalar nada, pelo Telegram, com texto livre ou foto do comprovante. A partir desses lançamentos, o app mostra o fluxo de caixa da família e cuida da lista de compras do mercado.

- **Usuários:** os membros da família cadastrados (configuráveis), todos lançando despesas e receitas.
- **Princípio:** lançar tem que levar segundos; a organização (categoria, forma de pagamento, mês de competência) é trabalho do app.
- **Escopo da fase 1:** entrada via bot, despesas e receitas categorizadas, formas de pagamento com regra de fatura do cartão, fluxo de caixa, lista de compras e backup.

Dados da família (membros, IDs do Telegram, e-mails, formas de pagamento, datas do cartão) não ficam no repositório: vêm de variáveis de ambiente e de um arquivo de seed local fora do Git.

## Entrada via bot do Telegram

O bot é criado pelo BotFather e não precisa de número próprio: cada membro conversa com ele pela sua conta normal, e o autor de cada lançamento vem do ID do usuário.

**Privacidade**

- O bot é encontrável por qualquer pessoa; o código só responde a uma lista configurada de IDs e ignora o resto.
- Uso individual (conversa privada) e em um grupo da família. Depois de adicionar o bot ao grupo, desativar no BotFather a opção de adicioná-lo a outros grupos.

**Fluxo de um lançamento**

1. O usuário manda texto livre ("mercado 230,50 no VR") ou foto do comprovante.
2. O modelo de IA extrai valor, descrição, data, categoria e forma de pagamento.
3. O bot responde com o resumo estruturado do lançamento e botões para confirmar ou corrigir.
4. Campos ausentes viram uma pergunta curta (ex.: "Qual forma de pagamento?" com as opções da pessoa).
5. Confirmado, o lançamento é gravado com o autor e a data real.

Texto sem data assume a data da mensagem. Sem forma de pagamento, o bot pergunta em vez de chutar.

## Lançamento de despesas e receitas

Despesas e receitas são o mesmo tipo de registro, diferenciado pelo tipo, e as duas entram no mesmo fluxo de caixa.

| Campo | Despesa | Receita | Observação |
| --- | --- | --- | --- |
| Valor (R$) | Sim | Sim | |
| Descrição | Sim | Sim | Texto livre |
| Data real | Sim | Sim | Dia da compra ou do recebimento |
| Mês de competência | Sim | Sim | Calculado; difere da data real no cartão de crédito |
| Categoria | Sim | Sim | Listas separadas para despesa e receita |
| Pessoa | Sim | Sim | Quem lançou ou a quem pertence |
| Forma de pagamento | Sim | Não | Ver seção seguinte |
| Comprovante | Opcional | Opcional | Foto enviada ao bot |

**Receitas:** proventos e vale-refeição de cada membro, com valores diferentes. O VR entra como receita normal no mesmo fluxo de caixa; o controle de onde ele foi gasto é feito pela forma de pagamento.

**Categorias:** editáveis pela família. Um mesmo tipo de gasto pode cair em categorias diferentes conforme o contexto (ex.: restaurante como Alimentação ou Entretenimento), então a categoria sugerida pela IA é sempre corrigível. Categorias iniciais:

| Categoria | Tipo | Exemplos |
| --- | --- | --- |
| Residência | Despesa | Financiamento ou aluguel, energia, água, internet, condomínio |
| Escola | Despesa | Mensalidade, material escolar, uniforme |
| Alimentação | Despesa | Mercado, padaria, restaurante, delivery |
| Entretenimento | Despesa | Passeios, restaurante a lazer |
| Assinaturas | Despesa | Streaming e outros serviços recorrentes |
| Automóvel | Despesa | Combustível, manutenção, seguro |
| Saúde | Despesa | Farmácia, consultas, plano de saúde |
| Vestuário | Despesa | Roupas e calçados fora da escola |
| Pets | Despesa | Ração, areia, veterinário, banho e tosa |
| Presentes e datas | Despesa | Aniversários, Natal |
| Viagens | Despesa | Hospedagem, passagens, gastos durante a viagem |
| Impostos, taxas e multas | Despesa | IPTU, IPVA, licenciamento, multas, tarifas bancárias |
| Outros | Despesa | O que não se encaixa nas demais |
| Proventos | Receita | Salário, 13º, férias |
| Vale-refeição | Receita | VR de cada membro |
| Remuneração financeira | Receita | Dividendos, juros, rendimentos de investimentos |

Novas categorias entram conforme a necessidade.

## Formas de pagamento e cartão de crédito

Cada forma de pagamento tem um dono, quem pode usá-la e um tipo. O custo cai no mês da data real, exceto no cartão de crédito, onde cai no mês de vencimento da fatura.

| Tipo | Dono | Quem usa | Mês do custo |
| --- | --- | --- | --- |
| Dinheiro | Família | Todos | Data da compra |
| Pix | Um membro | O próprio dono | Data da compra |
| Débito | Um membro | O próprio dono (sai da conta de quem paga) | Data da compra |
| Vale-refeição | Um membro | O próprio dono | Data da compra |
| Cartão de crédito | Um membro (titular) | Titular e adicionais configurados | Vencimento da fatura |

Um cartão de crédito pode ser usado por mais de um membro: cada despesa registra quem comprou, e todas caem na mesma fatura do titular. As formas de pagamento reais da família ficam no seed local.

**Regra da fatura**

O cartão tem dia de fechamento e dia de vencimento configuráveis; o fechamento aceita um dia fixo ou "último dia do mês". A compra guarda a data real; o app calcula a fatura em que ela entra e lança o custo no mês do vencimento.

- Compra até o dia de fechamento → fatura que fecha naquele mês.
- Compra depois do fechamento → fatura do mês seguinte.
- Exemplo com fechamento no último dia do mês e vencimento no dia 7: toda compra feita em novembro entra na fatura que vence em 7 de dezembro e pesa no fluxo de caixa de dezembro.
- Exemplo com fechamento no dia 3 e vencimento no dia 12: compra no dia 2 pesa no mesmo mês; compra no dia 20 pesa no mês seguinte.

Novas formas de pagamento são cadastradas sem mudar o modelo.

## Balanço e fluxo de caixa

A visão principal é o mês de competência: quanto entrou, quanto saiu e o saldo da família, com compras no cartão contadas no mês da fatura.

- **Resumo do mês:** receitas, despesas e saldo.
- **Por categoria:** quanto foi para cada categoria no mês.
- **Por forma de pagamento e por pessoa:** quanto saiu de cada meio e de cada membro.
- **Evolução:** comparação mês a mês.
- **Consulta pelo bot:** perguntas curtas como "quanto gastamos com mercado este mês?".

Relatórios e lista de compras ficam numa página web pensada para o celular. Ela roda em container num servidor doméstico, exposta por um Cloudflare Tunnel com Cloudflare Access na frente: cada membro entra com o próprio e-mail, e o app identifica quem está usando pelo cabeçalho com o e-mail que a Cloudflare repassa, sem login próprio. Assim a lista funciona no mercado desde o primeiro dia.

## Lista de compras

A lista é montada antes do mercado, marcada durante a compra e reaproveitada na próxima.

- **Catálogo da família:** itens permanentes (água, pão, macarrão, frutas…), criados automaticamente quando aparecem numa lista pela primeira vez.
- **Lista / sessão de compra:** cada ida ao mercado é uma sessão com os itens escolhidos; durante a compra, cada um marca o que já foi para o carrinho e vê o que falta.
- **Uso compartilhado:** todos veem e marcam a mesma lista ao mesmo tempo.
- **Reaproveitamento:** ao criar uma nova lista, dá para puxar os itens frequentes ou os que ficaram sem marcar na última sessão.
- **Histórico:** cada sessão fica guardada com os itens comprados, base para o histórico de preços nas fases seguintes.

Itens podem ser adicionados pelo bot ("adiciona leite e ovos na lista"); a marcação durante a compra é feita na página web.

## Modelo de dados inicial

Sete entidades cobrem a fase 1; o mês de competência é calculado e gravado no lançamento para simplificar os relatórios.

| Entidade | Campos principais | Relaciona com |
| --- | --- | --- |
| Pessoa | nome, telegram_user_id, email | FormaPagamento, Lançamento |
| Categoria | nome, tipo (despesa/receita) | Lançamento |
| FormaPagamento | nome, tipo, dono, usuários_permitidos, dia_fechamento?, fecha_ultimo_dia?, dia_vencimento? | Pessoa, Lançamento |
| Lançamento | tipo, valor, descrição, data_real, mes_competencia, comprovante? | Pessoa, Categoria, FormaPagamento |
| Item | nome | ItemLista |
| ListaCompras | criada_em, status (aberta/concluída) | ItemLista |
| ItemLista | marcado, quantidade?, marcado_por? | ListaCompras, Item |

Campos com `?` são opcionais; fechamento e vencimento só existem no tipo crédito.

## Stack e hospedagem

Tudo em Python, rodando em containers num único Docker Compose, num servidor doméstico (primeiro em WSL para testes, depois numa máquina dedicada).

| Peça | Escolha | Observação |
| --- | --- | --- |
| Linguagem | Python | |
| Banco | PostgreSQL | Leve em container e aguenta web e bot gravando ao mesmo tempo |
| Web / API | FastAPI | |
| Página para celular | Templates Jinja + HTMX | Dispensa um frontend separado |
| Bot | python-telegram-bot | |
| Acesso ao banco | SQLAlchemy + Alembic | Alembic cuida das migrações |
| Extração dos lançamentos | Gemini Flash (API, plano pago) | Lê texto livre e foto do comprovante. Cobrança pós-paga no Google Cloud, com alerta de orçamento. Plano gratuito descartado: o Google pode usar os dados enviados. Um modelo local (Ollama) pode ser testado depois pela mesma interface |
| Exposição | cloudflared + Cloudflare Access | |

Serviços do Compose: `web`, `bot`, `db`, `cloudflared` e `backup`. O bot divide a mesma infraestrutura, já que a demanda é baixa.

**Backup**

- O serviço `backup` roda `pg_dump` uma vez por dia e compacta o arquivo.
- O dump vai para o Google Drive pelo `rclone`, criptografado com o remote `crypt` do próprio rclone, já que são dados financeiros.
- Retenção: últimos 7 diários e 4 semanais; os mais antigos são apagados automaticamente.
- O bot avisa no Telegram se um backup falhar.
- Testar a restauração de um dump antes de começar a usar o app de verdade.

## Qualidade e entrega

Testes unitários cobrem tudo desde o primeiro commit; o pipeline de deploy vem logo depois que a estrutura estiver estável.

**Testes e qualidade**

- `pytest` com `pytest-cov`, e o CI falha se a cobertura cair abaixo de 90%.
- Regras de negócio em funções puras, testadas sem banco nem rede: cálculo do mês de competência pela fatura, parsing dos lançamentos, regras da lista de compras.
- Chamadas ao modelo de IA e ao Telegram isoladas atrás de interfaces e substituídas por dublês nos testes unitários.
- Testes de integração com Postgres real em container, separados dos unitários.
- `ruff` para lint e formatação, rodando no CI e em pre-commit.

**Repositório e pipeline**

1. Repositório no GitHub.
2. Fase 1: GitHub Actions roda lint e testes a cada push e pull request.
3. Em seguida: deploy automático ao entrar na branch principal, por um runner self-hosted no servidor doméstico, que puxa o código e sobe o Docker Compose. Nenhuma porta fica aberta para a internet.

**Repositório público**

- Dados pessoais (nomes, datas do cartão, formas de pagamento de cada membro, IDs do Telegram, e-mails, domínio) ficam em `.env` e num arquivo de seed local, ambos no `.gitignore`. O repositório traz apenas um `.env.example` e um seed de exemplo com dados fictícios.
- Runner self-hosted em repositório público é arriscado: um pull request de fora poderia executar código no servidor. O workflow de deploy roda só em push na branch principal, e workflows de forks ficam bloqueados ou exigem aprovação.
- O runner roda com um usuário sem privilégios, com acesso apenas à pasta do projeto e ao Docker.

## Fases futuras

- **Leitura da NFC-e:** o QR code do cupom traz o link da nota no portal da Sefaz, que lista itens, quantidades e preços; extrair esses dados lança a despesa e alimenta o histórico. Depende do layout do portal de cada estado, que pode mudar.
- **Histórico de preços:** preço de cada item por mercado e por data, a partir das notas lidas.
- **WhatsApp:** canal alternativo ao Telegram; exige número dedicado e a API oficial da Meta.
