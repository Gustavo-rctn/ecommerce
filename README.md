# Ecommerce

Draw DB
![](imagens/Ecommerce.png)

## Banco de Dados

O banco de dados possui 5 tabelas:

- **Login:** guarda os dados do cliente.
- **Produto:** guarda os produtos e seus preços.
- **Carrinho:** guarda os produtos escolhidos e a quantidade.
- **Pagamento:** guarda as informações do pagamento.
- **Pedidos:** guarda os pedidos feitos pelos clientes.

As tabelas estão ligadas entre si para organizar os dados do sistema.



## Sobre o projeto
A ideia foi criar um sistema de vendas online usando Python e SQLite, integrando o checkout web ao Mercado Pago.

O sistema começa pelo cadastro do usuário e passa pela escolha dos produtos, carrinho, criação do pedido e pagamento.

## Como funciona

O funcionamento do projeto foi dividido em algumas partes:

- Cadastro e login dos usuários
- Cadastro e controle dos produtos
- Carrinho de compras
- Criação dos pedidos
- Processamento de pagamentos

O usuário pode escolher os produtos, informar a quantidade, adicionar ao carrinho e conferir o valor da compra. Depois disso, o pedido pode ser criado e o pagamento processado.

## Contas e preferências

O cadastro e o login são processados pelo servidor e armazenados no SQLite em `database/loja.db`. As senhas novas são salvas com hash PBKDF2; após entrar, uma sessão protegida por cookie é mantida por até 30 dias. Nome, e-mail, foto de perfil e tema ficam vinculados à conta, então continuam disponíveis quando a pessoa entrar novamente pelo mesmo servidor. A foto aceita PNG, JPEG, WebP ou GIF de até 2 MB.

O carrinho continua salvo localmente no navegador. Contas antigas criadas apenas pela versão demonstrativa do site não têm senha no banco; para usar o novo login, crie uma conta pelo botão **Criar conta**. Contas já existentes no banco podem entrar com a senha cadastrada.

## Publicar no Vercel com Neon

O `index.html` da raiz é a página inicial do deploy. As outras páginas, o CSS e o JavaScript continuam em `front_end/HTML`; as rotas em `vercel.json` e o servidor local encaminham os endereços do site para esses arquivos. A API Python é exposta como uma Vercel Function em `api/index.py`.

1. Crie um projeto PostgreSQL no Neon e copie a connection string (`postgresql://...`) da opção **Pooled connection**.
2. Importe este repositório no Vercel, mantendo a raiz do projeto como **Root Directory**. O Vercel instala as dependências de `requirements.txt` e cria a função Python.
3. Em **Settings → Environment Variables** no Vercel, configure `DATABASE_URL` com a connection string do Neon. Configure também `MERCADOPAGO_ACCESS_TOKEN` e `MERCADOPAGO_PUBLIC_KEY` para pagamentos reais; sem elas, o checkout continua em modo de demonstração.
4. Faça o deploy. Na primeira chamada à API, as tabelas necessárias são criadas no Neon. Cadastre as contas novamente no site publicado; o SQLite local não é copiado automaticamente.

Não publique um arquivo `.env` nem coloque credenciais no código. O SQLite em `database/loja.db` continua sendo usado somente no desenvolvimento local; no Vercel, a ausência de `DATABASE_URL` faz a API retornar indisponibilidade, em vez de aparentar salvar dados em disco temporário.

## Dados fictícios para teste

O catálogo do frontend já inclui 8 produtos fictícios para exibição imediata. Quando conectado ao servidor, ele atualiza a lista com os dados do catálogo da loja. O servidor usa Faker para gerar produtos de demonstração; instale as dependências antes de iniciá-lo:

```powershell
py -3 -m pip install -r requirements.txt
```

Para conferir outros produtos gerados com Faker:

```powershell
py -3 back_end/fake.py
```

O script aceita `--quantidade` (de 1 a 12) e `--seed` para repetir a mesma seleção. Os produtos aparecem no catálogo do site junto aos quatro produtos originais; seus preços e estoques são gerados para demonstração e não são gravados no banco.

## Banco de dados

Para organizar o banco de dados, utilizamos o DrawDB antes de começar a programação.

O projeto utiliza SQLite para armazenar as informações.

As principais tabelas são:

- Login
- Produto
- Carrinho
- Pedidos
- Pagamento

Essas tabelas possuem relacionamentos entre si para organizar os usuários, produtos, pedidos e pagamentos.

O arquivo do banco utilizado no projeto é:

`loja.db`

## Tecnologias utilizadas

- Python
- SQLite
- SQL
- DrawDB
- Git e GitHub

## Bibliotecas utilizadas

Durante o desenvolvimento foram utilizados alguns módulos do Python:

- `sqlite3` para trabalhar com o banco SQLite
- `os` para trabalhar com caminhos e pastas
- `re` para fazer algumas validações
- `uuid` para gerar códigos de transação
- `decimal` para trabalhar com valores financeiros

## Carrinho

O carrinho guarda os produtos escolhidos pelo usuário e suas quantidades.

Também é possível calcular o subtotal, aplicar um cupom de desconto e adicionar o valor do frete.

Antes de adicionar um produto, o sistema verifica a quantidade, o preço e o estoque disponível.
O catálogo exibido pelo site é carregado de `GET /api/produtos`; preços, nomes e estoque usados na confirmação são validados novamente pelo backend.

## Pedidos

Depois que os produtos são escolhidos, o sistema pode criar um pedido.

Antes disso, é verificado se o carrinho possui produtos e se existe estoque suficiente.

O pedido possui informações como cliente, produtos, valores e status.

Inicialmente, o pedido fica com o status:

`AGUARDANDO_PAGAMENTO`

## Pagamentos

Sem credenciais do Mercado Pago, o site usa o **modo demonstração local** para permitir testar o checkout. O pedido fica marcado como `DEMONSTRACAO`, a confirmação informa que não houve pagamento e os exemplos de PIX/boleto são identificados como inválidos para pagamento. Nenhum dado de cartão é solicitado nesse modo.

Para processar pagamentos reais, configure as credenciais de teste ou produção do Mercado Pago. O Access Token e a Public Key devem estar definidos juntos. No cartão, o navegador carrega o SDK do Mercado Pago e tokeniza os dados; o número e o CVV não são enviados ao servidor da loja.

### Configuração local

Crie uma aplicação em [Mercado Pago Developers > Integrações](https://www.mercadopago.com.br/developers/panel/app), abra a aplicação e selecione o ambiente **Teste**. Copie a **Public Key** e o **Access Token** na página **Credenciais**. O Access Token de teste pode começar com `APP_USR`; confira que o seletor de ambiente está em **Teste** antes de copiar:

```powershell
$env:MERCADOPAGO_ACCESS_TOKEN = "cole_aqui_o_access_token_de_teste"
$env:MERCADOPAGO_PUBLIC_KEY = "cole_aqui_a_public_key_de_teste"
py -3 main.py
```

O comando inicia o servidor web. Abra `http://127.0.0.1:8000/`. O Access Token é secreto e deve ficar somente no ambiente do servidor; não o coloque no frontend, no Git ou em mensagens. A chave pública é usada pelo SDK do navegador. Para usar sem gateway, inicie simplesmente com `py -3 main.py`, sem definir as variáveis de credenciais. Para voltar ao modo de demonstração, pare o servidor e inicie-o sem essas duas variáveis. Se apenas uma das credenciais estiver definida, o checkout avisa que a configuração está incompleta. O fluxo antigo de pagamentos pelo terminal foi desativado para não registrar cobranças simuladas como reais.

No modo real, PIX e boleto ficam pendentes até o Mercado Pago confirmar o recebimento. Enquanto a página de pagamento estiver aberta, o site consulta o status periodicamente; ao retornar ao checkout no mesmo navegador, a consulta é retomada. Em uma implantação com URL pública HTTPS, configure também `MERCADOPAGO_NOTIFICATION_URL` com a URL `/api/mercado-pago/webhook` e `MERCADOPAGO_WEBHOOK_SECRET` com a chave secreta de Webhooks da aplicação. O servidor valida a assinatura e consulta o pagamento diretamente no Mercado Pago antes de atualizar o pedido. Não configure um webhook local inacessível pela internet.

## Organização do projeto

O código foi separado em diferentes partes para facilitar a organização e o entendimento do sistema.

Cada parte possui uma função específica, como cadastro de usuários, carrinho, pedidos e pagamentos.

## Objetivo

O principal objetivo do projeto foi colocar em prática os conhecimentos aprendidos durante o curso, principalmente em Python, funções, banco de dados, SQL e organização de código.

Também utilizamos o GitHub para acompanhar o desenvolvimento do projeto e registrar as alterações feitas durante o trabalho.

## Equipe

Guilherme e Gustavo