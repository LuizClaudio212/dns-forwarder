# Importação de bibliotecas necessárias
import socket  # Para comunicação de rede via sockets UDP
import argparse  # Para processar argumentos de linha de comando
import struct  # Para manipulação de dados binários (serialização/deserialização)
import time  # Para gerenciar timestamps e TTL do cache

# Dicionário global para armazenar respostas DNS em cache
# Formato: {(nome, tipo, classe): (resposta, timestamp, ttl)}
cache = {}

def parse_dns_header(data):
    """
    Parseia o cabeçalho de um pacote DNS (12 bytes, conforme RFC 1035, Seção 4.1.1).
    Args:
        data: Bytes do pacote DNS recebido.
    Returns:
        Dicionário com os campos do cabeçalho: ID, flags, contagem de perguntas, respostas, etc.
    """
    # Desempacota os 12 bytes do cabeçalho em 6 campos de 16 bits (big-endian)
    header = struct.unpack('!HHHHHH', data[:12])
    return {
        'id': header[0],          # ID da transação (identificador único)
        'flags': header[1],       # Flags (ex.: tipo de consulta, recursão desejada)
        'questions': header[2],   # Número de perguntas
        'answers': header[3],     # Número de respostas
        'authorities': header[4], # Número de registros de autoridade
        'additionals': header[5]  # Número de registros adicionais
    }

def parse_dns_name(data, offset):
    """
    Parseia o nome do domínio codificado no pacote DNS (ex.: 3www6google3com0).
    Suporta compressão de nomes (ponteiros).
    Args:
        data: Bytes do pacote DNS.
        offset: Posição inicial para leitura do nome.
    Returns:
        Tupla (nome do domínio como string, novo offset após o nome).
    """
    name_parts = []
    while True:
        length = data[offset]
        if length & 0xC0 == 0xC0:  # Verifica se é um ponteiro de compressão
            # Extrai o ponteiro (14 bits, ignorando os 2 bits iniciais)
            pointer = struct.unpack('!H', data[offset:offset+2])[0] & 0x3FFF
            # Parseia o nome a partir do ponteiro (recursivamente)
            name, _ = parse_dns_name(data, pointer)
            offset += 2
            name_parts.append(name)
            break
        offset += 1
        if length == 0:  # Fim do nome (byte 0)
            break
        # Lê o segmento do nome (ex.: 'www', 'google') e decodifica como ASCII
        name_parts.append(data[offset:offset+length].decode('ascii'))
        offset += length
    return '.'.join(name_parts), offset  # Retorna nome (ex.: www.google.com) e novo offset

def parse_dns_question(data, offset):
    """
    Parseia a seção de perguntas do pacote DNS (RFC 1035, Seção 4.1.2).
    Args:
        data: Bytes do pacote DNS.
        offset: Posição inicial da seção de perguntas.
    Returns:
        Tupla (dicionário com nome, tipo e classe da pergunta, novo offset).
    """
    # Extrai o nome do domínio
    name, offset = parse_dns_name(data, offset)
    # Lê tipo (ex.: 1 para A) e classe (ex.: 1 para IN) como inteiros de 16 bits
    qtype, qclass = struct.unpack('!HH', data[offset:offset+4])
    offset += 4
    return {
        'name': name,   # Nome do domínio (ex.: www.google.com)
        'type': qtype,  # Tipo do registro (ex.: 1 para A)
        'class': qclass # Classe do registro (ex.: 1 para IN)
    }, offset

def parse_dns_answer(data, offset):
    """
    Parseia a seção de respostas do pacote DNS (RFC 1035, Seção 4.1.3).
    Args:
        data: Bytes do pacote DNS.
        offset: Posição inicial da seção de respostas.
    Returns:
        Tupla (dicionário com informações da resposta, novo offset).
    """
    # Extrai o nome do domínio
    name, offset = parse_dns_name(data, offset)
    # Lê tipo, classe, TTL e comprimento dos dados
    atype, aclass, ttl, rdlength = struct.unpack('!HHIH', data[offset:offset+10])
    offset += 10
    # Lê os dados da resposta (ex.: endereço IP para registros A)
    rdata = data[offset:offset+rdlength]
    offset += rdlength
    if atype == 1:  # Se for registro A (IPv4)
        # Converte os 4 bytes do endereço IP em string (ex.: 142.250.78.132)
        rdata = '.'.join(str(b) for b in rdata)
    return {
        'name': name,    # Nome do domínio
        'type': atype,   # Tipo do registro
        'class': aclass, # Classe do registro
        'ttl': ttl,      # Tempo de vida (em segundos)
        'rdata': rdata   # Dados da resposta (ex.: endereço IP)
    }, offset

def check_cache(question):
    """
    Verifica se a pergunta DNS está no cache e se o TTL ainda é válido.
    Args:
        question: Dicionário com nome, tipo e classe da pergunta.
    Returns:
        Resposta em cache (bytes) se encontrada e válida, ou None.
    """
    key = (question['name'], question['type'], question['class'])
    if key in cache:
        response, timestamp, ttl = cache[key]
        # Verifica se o TTL ainda é válido
        if time.time() < timestamp + ttl:
            print(f"Resposta encontrada no cache (TTL restante: {int(timestamp + ttl - time.time())} segundos)")
            return response
        else:
            del cache[key]  # Remove entrada expirada
            print(f"Entrada expirada removida do cache para {question['name']}")
    return None

def store_in_cache(question, response, answers):
    """
    Armazena a resposta DNS no cache com base no TTL.
    Args:
        question: Dicionário com nome, tipo e classe da pergunta.
        response: Pacote DNS completo (bytes) da resposta.
        answers: Lista de respostas parseadas (para extrair TTL).
    """
    key = (question['name'], question['type'], question['class'])
    # Usa o menor TTL das respostas, ou 3600 segundos se não houver respostas
    ttl = min(answer['ttl'] for answer in answers) if answers else 3600
    cache[key] = (response, time.time(), ttl)
    print(f"Resposta armazenada no cache para {question['name']} com TTL {ttl} segundos")

def forward_request(data, client_address, server_socket, upstream_dns='8.8.8.8', upstream_port=53):
    """
    Encaminha a solicitação DNS para um servidor upstream (ex.: Google DNS) e processa a resposta.
    Args:
        data: Pacote DNS recebido (bytes).
        client_address: Endereço do cliente (IP, porta).
        server_socket: Socket do servidor para enviar respostas.
        upstream_dns: Endereço do servidor DNS upstream (padrão: 8.8.8.8).
        upstream_port: Porta do servidor DNS upstream (padrão: 53).
    """
    # Cria um socket UDP para comunicação com o servidor upstream
    upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    upstream_socket.settimeout(5)  # Define timeout de 5 segundos
    # Envia a solicitação DNS para o servidor upstream
    upstream_socket.sendto(data, (upstream_dns, upstream_port))
    print("Solicitação encaminhada para", upstream_dns)

    try:
        # Recebe a resposta do servidor upstream
        response, _ = upstream_socket.recvfrom(1024)
        # Parseia o cabeçalho da resposta
        header = parse_dns_header(response)
        offset = 12
        questions = []
        # Parseia as perguntas na resposta
        for _ in range(header['questions']):
            question, offset = parse_dns_question(response, offset)
            questions.append(question)
        answers = []
        # Parseia as respostas para extrair TTL
        for _ in range(header['answers']):
            answer, offset = parse_dns_answer(response, offset)
            answers.append(answer)
        # Armazena a resposta no cache, se houver perguntas e respostas
        if questions and answers:
            store_in_cache(questions[0], response, answers)
        # Envia a resposta ao cliente original
        server_socket.sendto(response, client_address)
        print("Resposta enviada para", client_address)
    except socket.timeout:
        print("Timeout ao esperar resposta do servidor DNS")
    finally:
        upstream_socket.close()  # Fecha o socket upstream

def start_server(port):
    """
    Inicia o servidor DNS Forwarder, escutando na porta especificada.
    Args:
        port: Porta para escutar (ex.: 1053).
    """
    # Cria um socket UDP para o servidor
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('127.0.0.1', port))
    print(f"Servidor DNS ouvindo na porta {port}...")

    while True:
        # Recebe solicitações DNS dos clientes
        data, client_address = server_socket.recvfrom(1024)
        print("Mensagem recebida de", client_address)

        # Parseia o cabeçalho da solicitação
        header = parse_dns_header(data)
        offset = 12
        questions = []
        # Parseia todas as perguntas da solicitação
        for _ in range(header['questions']):
            question, offset = parse_dns_question(data, offset)
            questions.append(question)
            print(f"Pergunta - nome:{question['name']} tipo:{question['type']} classe:{question['class']}")

        # Verifica se há uma resposta no cache para a primeira pergunta
        if questions:
            cached_response = check_cache(questions[0])
            if cached_response:
                # Extrai o ID da transação da solicitação atual
                request_id = struct.unpack('!H', data[:2])[0]
                # Cria uma cópia modificável da resposta em cache
                updated_response = bytearray(cached_response)
                # Atualiza o ID da transação na resposta para corresponder à solicitação
                updated_response[:2] = struct.pack('!H', request_id)
                # Envia a resposta atualizada ao cliente
                server_socket.sendto(updated_response, client_address)
                print("Resposta enviada do cache para", client_address)
                continue  # Pula para a próxima solicitação

        # Se não houver resposta no cache, encaminha a solicitação
        forward_request(data, client_address, server_socket)

if __name__ == "__main__":
    # Configura o parser para argumentos de linha de comando
    parser = argparse.ArgumentParser(description="DNS Forwarder - Etapa 5")
    parser.add_argument('--port', type=int, default=1053, help="Porta para ouvir (padrão: 1053)")
    args = parser.parse_args()
    
    # Inicia o servidor na porta especificada
    start_server(args.port)