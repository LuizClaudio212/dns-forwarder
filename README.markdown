# DNS Forwarder

Este projeto implementa um **DNS Forwarder** em Python, conforme especificado em um desafio de redes. O DNS Forwarder é um servidor que atua como intermediário para resolver consultas DNS, utilizando um cache local para reduzir o tráfego externo e acelerar respostas. Ele recebe solicitações DNS, verifica se a resposta está no cache e, se não estiver, encaminha a solicitação para um servidor DNS upstream (neste caso, o Google DNS em 8.8.8.8).

O projeto foi desenvolvido em cinco etapas incrementais, cada uma adicionando funcionalidades ao servidor. Ele foi implementado no **Windows 10** usando **Python 3.13** e testado com a ferramenta `dig`.

## Objetivo

Construir um DNS Forwarder que:

- Escuta solicitações DNS em uma porta UDP (padrão: 1053).
- Parseia pacotes DNS (cabeçalho e seção de perguntas).
- Encaminha solicitações para um servidor DNS upstream.
- Recebe e retorna respostas ao cliente.
- Armazena respostas em cache com base no TTL (Time to Live).

## Estrutura do Projeto

O projeto está dividido em cinco arquivos, cada um representando uma etapa do desenvolvimento:

- `step1_dns_forwarder.py`: Servidor UDP básico que escuta na porta especificada e imprime mensagens recebidas.
- `step2_dns_forwarder.py`: Adiciona parsing do cabeçalho e da seção de perguntas do pacote DNS.
- `step3_dns_forwarder.py`: Implementa o encaminhamento de solicitações para o servidor DNS upstream (8.8.8.8).
- `step4_dns_forwarder.py`: Recebe respostas do servidor upstream e as retorna ao cliente.
- `step5_dns_forwarder.py`: Adiciona cache com TTL para armazenar respostas e responder a partir do cache quando possível.

## Pré-requisitos

- **Python 3.x** (testado com Python 3.13).
- Sistema operacional: **Windows 10** (também compatível com Linux/Mac com ajustes mínimos).
- Ferramenta de teste: **dig** (parte do pacote BIND, disponível em https://www.isc.org/download/) ou `nslookup` (nativo no Windows).
- Permissões de firewall: Libere a porta UDP 1053 no Windows Firewall para permitir tráfego.

## Instalação

1. Clone o repositório:

   git clone https://github.com/&lt;seu_usuario&gt;/dns-forwarder.git\
   cd dns-forwarder

2. Instale o Python 3.x, se ainda não estiver instalado:

   - Baixe e instale do site oficial: https://www.python.org/downloads/
   - Verifique a instalação: `python --version`

3. (Opcional) Instale o `dig` para testes:

   - Baixe o BIND para Windows em https://www.isc.org/download/.
   - Alternativamente, use `nslookup`, que é nativo no Windows.

4. Configure o firewall do Windows:

   - Abra o Painel de Controle &gt; Sistema e Segurança &gt; Firewall do Windows Defender &gt; Configurações Avançadas.
   - Crie uma regra de entrada para UDP, porta 1053, permitindo a conexão.

## Como Executar

Cada etapa pode ser executada independentemente. Para executar qualquer etapa:

1. Navegue até o diretório do projeto:

   cd dns-forwarder

2. Execute o arquivo correspondente à etapa desejada:

   python stepX_dns_forwarder.py --port 1053

   Substitua `X` pelo número da etapa (1 a 5). A porta padrão é 1053, mas pode ser alterada com o argumento `--port`.

3. Teste o servidor em outro terminal:

   - Usando `dig`:

   - dig @127.0.0.1 -p 1053 www.google.com

   - Usando `nslookup`:

   - nslookup -port=1053 www.google.com 127.0.0.1

## Saídas Esperadas

- **Etapa 1**: O servidor imprime "Mensagem recebida de (IP, porta)" ao receber uma solicitação.
- **Etapa 2**: Exibe o cabeçalho e a seção de perguntas do pacote DNS (ex.: `Pergunta - nome:www.google.com tipo:1 classe:1`).
- **Etapa 3**: Confirma o encaminhamento da solicitação para 8.8.8.8.
- **Etapa 4**: Retorna a resposta do servidor upstream ao cliente, visível no `dig` (ex.: `www.google.com. IN A 142.250.78.132`).
- **Etapa 5**: Usa o cache para responder consultas repetidas, mostrando "Resposta encontrada no cache" e o TTL restante.

## Exemplo de Saída (Etapa 5)

**Servidor**:

Servidor DNS ouvindo na porta 1053...\
Mensagem recebida de ('127.0.0.1', 57548)\
Pergunta - nome:www.google.com tipo:1 classe:1\
Solicitação encaminhada para 8.8.8.8\
Resposta armazenada no cache para www.google.com com TTL 159 segundos\
Resposta enviada para ('127.0.0.1', 57548)\
Mensagem recebida de ('127.0.0.1', 57550)\
Pergunta - nome:www.google.com tipo:1 classe:1\
Resposta encontrada no cache (TTL restante: 150 segundos)\
Resposta enviada do cache para ('127.0.0.1', 57550)

**Cliente (dig)**:

;; ANSWER SECTION:\
www.google.com.         159     IN      A       142.250.78.132

## Notas

- **Porta 1053**: Usada para testes, pois a porta 53 requer privilégios administrativos.
- **Cache**: A Etapa 5 implementa um cache com TTL, atualizando o ID da transação para evitar erros de "ID mismatch".
- **Limitações**: O projeto suporta principalmente registros A (IPv4). Para outros tipos (ex.: CNAME, MX), seria necessário expandir o parsing.
- **Testes**: Recomenda-se testar com diferentes domínios (ex.: `dns.google.com`, `www.facebook.com`) e verificar o comportamento do cache.

## Autores

- **Nomes**: \[
- LUIZ CLAUDIO VIEIRA DA SILVA JUNIOR
- JOSE GOUVEIA DA SILVA NETO
- Wylker Esperidião da Silva
- \]
- **Contexto**: Projeto desenvolvido para a disciplina de Redes no IFAL, 4º período.