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
- O grupo é dedicado ao bot: o privacy mode fica desligado no BotFather e toda mensagem de um membro no grupo é tratada como lançamento ou comando.
- O bot recebe mensagens por polling (sem webhook nem rota pública).

**Fluxo de um lançamento**

1. O usuário manda texto livre ("mercado 230,50 no VR") ou foto do comprovante.
2. O modelo de IA extrai valor, descrição, data, categoria e forma de pagamento.
3. O bot responde com o resumo estruturado do lançamento e botões para confirmar ou corrigir.
4. Campos ausentes viram uma pergunta curta (ex.: "Qual forma de pagamento?" com as opções da pessoa).
5. Confirmado, o lançamento é gravado com o autor e a data real. Logo após gravar, um botão "desfazer" permite apagá-lo; no bot ele vale por 10 minutos e só para o autor. Depois disso, o lançamento é desfeito pela página web, a qualquer momento.

**Desfazer:** desfazer um lançamento parcelado remove a compra com todas as parcelas e adiantamentos; desfazer um adiantamento remove o lançamento do valor pago e devolve as parcelas abatidas ao status `ativo`.

Texto sem data assume a data da mensagem, no fuso `America/Sao_Paulo` (configurável). Sem forma de pagamento, o bot pergunta em vez de chutar. As opções de forma de pagamento oferecidas são só as que a pessoa pode usar.

**Data da operação × data do lançamento:** a data real é o dia em que a operação aconteceu; o momento em que ela foi registrada no app é guardado à parte (`registrado_em`, timestamp UTC). Um lançamento feito no dia seguinte a uma compra continua com a data real da compra.

**Correção:** é feita só por botões por campo. O usuário toca no campo (valor, descrição, data, categoria, forma de pagamento, pessoa) e escolhe numa lista ou digita o novo valor; não há nova chamada à IA.

**Pessoa:** por padrão é quem lançou; se o texto citar outro membro ("salário da Ana"), a IA sugere esse membro, corrigível como os demais campos.

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
| Comprovante | Opcional | Opcional | Foto enviada ao bot; ver "Comprovantes" |

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

Novas categorias entram conforme a necessidade. Categorias e lançamentos são editados pela página web.

**Comprovantes**

- A foto fica no banco, numa tabela própria separada do lançamento, para que consultas e relatórios não carreguem o arquivo.
- Ao receber, a imagem é redimensionada (lado maior até 1600 px) e gravada como JPEG; acima de 1 MB após a compressão, é recusada.
- Uma rotina diária apaga comprovantes com mais de 12 meses; o lançamento continua.

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
- O vencimento cai no mês do fechamento se o dia de vencimento for maior que o de fechamento; caso contrário, no mês seguinte.
- Dia de fechamento fixo que não existe no mês (ex.: 31 em fevereiro) vira o último dia daquele mês.

Novas formas de pagamento são cadastradas sem mudar o modelo.

**Compras parceladas**

- Uma compra no crédito pode ser parcelada em N vezes. A IA aceita o total ("geladeira 3000 em 10x") ou o valor da parcela ("10x de 299,90", para compras com juros).
- A compra gera N lançamentos ligados a ela, cada um com número da parcela, valor e mês de competência: a parcela 1 segue a regra da fatura pela data real, e cada parcela seguinte cai na fatura do mês seguinte.
- Quando o total não divide exato, a diferença de centavos fica na primeira parcela.

**Adiantamento de parcelas**

- O usuário informa o adiantamento ao bot depois de feito ("adiantei 5 parcelas da geladeira, paguei 147"). O bot mostra as compras parceladas em aberto para escolher.
- O bot sempre pergunta a data em que o adiantamento foi solicitado (hoje, ontem ou outra), pois o lançamento pode ser feito dias depois e a data muda a fatura.
- São abatidas as últimas parcelas pendentes: numa compra em 10x, adiantar 5 parcelas na parcela 3 marca as parcelas 6 a 10 como `antecipada`; elas saem do fluxo de caixa dos meses futuros.
- O valor efetivamente pago (R$ 147) vira um novo lançamento ligado à mesma compra, com mês de competência pela regra da fatura aplicada à data da solicitação.
- O desconto (R$ 150 − R$ 147 = R$ 3) não é receita: fica implícito na diferença e aparece como economia no detalhe da compra.

## Balanço e fluxo de caixa

A visão principal é o mês de competência: quanto entrou, quanto saiu e o saldo da família, com compras no cartão contadas no mês da fatura.

- **Resumo do mês:** receitas, despesas e saldo.
- **Por categoria:** quanto foi para cada categoria no mês.
- **Por forma de pagamento e por pessoa:** quanto saiu de cada meio e de cada membro.
- **Evolução:** comparação mês a mês.
- **Consulta pelo bot:** perguntas curtas como "quanto gastamos com mercado este mês?".

Relatórios e lista de compras ficam numa página web pensada para o celular. Ela roda em container num servidor doméstico, exposta por um Cloudflare Tunnel com Cloudflare Access na frente: cada membro entra com o próprio e-mail, e o app identifica quem está usando pelo cabeçalho com o e-mail que a Cloudflare repassa, sem login próprio. O e-mail só é aceito depois de validar o token assinado que a Cloudflare envia junto (`Cf-Access-Jwt-Assertion`), para que uma requisição que chegue ao container por fora do túnel não consiga se passar por um membro. Assim a lista funciona no mercado desde o primeiro dia.

## Lista de compras

A lista funciona como uma nota de lista permanente: é montada antes do mercado, marcada durante a compra e reaproveitada na próxima sem duplicar itens.

- **Várias listas com nome:** a família pode ter várias listas ao mesmo tempo, cada uma com um nome ("Mercado", "Festa de Natal"…). Uma lista é permanente: não há "nova lista do mercado" a cada ida, a mesma "Mercado" é reusada. Listas que não servem mais podem ser arquivadas.
- **Duas seções:** em cima, os itens pendentes (o que falta comprar); embaixo, recolhida e com contador, a seção de itens comprados (marcados). Marcar um item o move para baixo; desmarcar o devolve para cima.
- **Ordem:** os pendentes têm ordem manual, reordenada arrastando; item adicionado ou que volta dos comprados entra no fim dos pendentes. Os comprados ficam sempre em ordem alfabética (ignorando maiúsculas e acentos). A reordenação também é sincronizada em tempo real.
- **Um item aparece uma vez por lista:** cada item existe no máximo uma vez em cada lista, pendente ou comprado. Nada é inserido automaticamente; a pessoa escolhe o que volta para cima.
- **Sugestão ao digitar:** ao digitar um item novo, o app sugere itens já existentes, primeiro os comprados da própria lista e depois os do catálogo da família. Aceitar uma sugestão de item comprado o move de volta para os pendentes, em vez de criar outro; digitar o nome de um item que já está pendente não duplica. A comparação ignora maiúsculas, acentos e espaços extras ("agua" encontra "Água").
- **Catálogo da família:** todo item que já apareceu em alguma lista, compartilhado entre as listas e usado nas sugestões. Um item novo entra no catálogo automaticamente.
- **Uso compartilhado em tempo real:** todos veem e marcam a mesma lista ao mesmo tempo; qualquer alteração (adicionar, marcar, desmarcar, remover), feita na web ou pelo bot, aparece nos outros aparelhos em poucos segundos, sem recarregar a página.
- **Histórico:** cada vez que um item é marcado como comprado fica registrado (item, lista, quem, quando), base para o histórico de preços nas fases seguintes.

Itens podem ser adicionados pelo bot ("adiciona leite e ovos na lista"), com a mesma regra de não duplicar: item comprado volta para os pendentes, item já pendente fica como está. Se o texto citar a lista ("na lista da festa"), o item vai para ela; se houver uma só lista, vai para essa; com várias, o bot pergunta com botões; sem nenhuma, cria uma "Mercado". A marcação durante a compra é feita na página web.

## Modelo de dados inicial

Dez entidades cobrem a fase 1; o mês de competência é calculado e gravado no lançamento para simplificar os relatórios.

| Entidade | Campos principais | Relaciona com |
| --- | --- | --- |
| Pessoa | nome, telegram_user_id, email | FormaPagamento, Lançamento |
| Categoria | nome, tipo (despesa/receita), arquivada | Lançamento |
| FormaPagamento | nome, tipo, dono, usuários_permitidos, dia_fechamento?, fecha_ultimo_dia?, dia_vencimento? | Pessoa, Lançamento |
| Lançamento | tipo, valor, descrição, data_real, mes_competencia, registrado_em, pessoa (a quem pertence), autor (quem registrou), status (ativo/antecipada), compra_parcelada?, numero_parcela?, eh_adiantamento | Pessoa, Categoria, FormaPagamento, CompraParcelada, Comprovante |
| CompraParcelada | descrição, valor_total, num_parcelas, data_real | Lançamento |
| Comprovante | imagem (bytea), mime, tamanho, criado_em | Lançamento |
| Item | nome, nome_normalizado (único) | ItemLista |
| ListaCompras | nome, criada_em, arquivada | ItemLista |
| ItemLista | marcado, posicao, quantidade?, marcado_por?, atualizado_em (único por lista + item) | ListaCompras, Item |
| CompraItem | marcado_em, marcado_por | ItemLista (histórico de marcações) |

Campos com `?` são opcionais; fechamento e vencimento só existem no tipo crédito. Listas exibidas em ordem alfabética (categorias, formas, itens comprados) ignoram acentos e maiúsculas, independentemente da collation do banco.

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
- Desenvolvimento e CI rodam via Docker Compose, sem instalar Python ou ferramentas no host.
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
