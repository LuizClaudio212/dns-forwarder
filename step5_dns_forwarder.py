import socket
import argparse
import struct
import time

# Cache para armazenar respostas DNS
cache = {}  # Formato: {(nome, tipo, classe): (resposta, timestamp, ttl)}

def parse_dns_header(data):
    header = struct.unpack('!HHHHHH', data[:12])
    return {
        'id': header[0],
        'flags': header[1],
        'questions': header[2],
        'answers': header[3],
        'authorities': header[4],
        'additionals': header[5]
    }

def parse_dns_question(data, offset):
    name, offset = parse_dns_name(data, offset)
    qtype, qclass = struct.unpack('!HH', data[offset:offset+4])
    offset += 4
    return {
        'name': name,
        'type': qtype,
        'class': qclass
    }, offset

def parse_dns_name(data, offset):
    name_parts = []
    while True:
        length = data[offset]
        if length & 0xC0 == 0xC0:  # Ponteiro de compressão
            pointer = struct.unpack('!H', data[offset:offset+2])[0] & 0x3FFF
            name, _ = parse_dns_name(data, pointer)
            offset += 2
            name_parts.append(name)
            break
        offset += 1
        if length == 0:
            break
        name_parts.append(data[offset:offset+length].decode('ascii'))
        offset += length
    return '.'.join(name_parts), offset

def parse_dns_answer(data, offset):
    name, offset = parse_dns_name(data, offset)
    atype, aclass, ttl, rdlength = struct.unpack('!HHIH', data[offset:offset+10])
    offset += 10
    rdata = data[offset:offset+rdlength]
    offset += rdlength
    if atype == 1:  # Tipo A (IPv4)
        rdata = '.'.join(str(b) for b in rdata)
    return {
        'name': name,
        'type': atype,
        'class': aclass,
        'ttl': ttl,
        'rdata': rdata
    }, offset

def check_cache(question):
    key = (question['name'], question['type'], question['class'])
    if key in cache:
        response, timestamp, ttl = cache[key]
        if time.time() < timestamp + ttl:
            print("Resposta encontrada no cache")
            return response
        else:
            del cache[key]  # Remover entrada expirada
    return None

def store_in_cache(question, response, answers):
    key = (question['name'], question['type'], question['class'])
    ttl = min(answer['ttl'] for answer in answers) if answers else 3600
    cache[key] = (response, time.time(), ttl)
    print(f"Resposta armazenada no cache para {question['name']}")

def forward_request(data, client_address, server_socket, upstream_dns='8.8.8.8', upstream_port=53):
    upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    upstream_socket.settimeout(5)
    upstream_socket.sendto(data, (upstream_dns, upstream_port))
    print("Solicitação encaminhada para", upstream_dns)

    try:
        response, _ = upstream_socket.recvfrom(1024)
        # Parsear a resposta para extrair TTL
        header = parse_dns_header(response)
        offset = 12
        questions = []
        for _ in range(header['questions']):
            question, offset = parse_dns_question(response, offset)
            questions.append(question)
        answers = []
        for _ in range(header['answers']):
            answer, offset = parse_dns_answer(response, offset)
            answers.append(answer)
        # Armazenar no cache
        if questions and answers:
            store_in_cache(questions[0], response, answers)
        # Enviar resposta ao cliente
        server_socket.sendto(response, client_address)
        print("Resposta enviada para", client_address)
    except socket.timeout:
        print("Timeout ao esperar resposta do servidor DNS")
    finally:
        upstream_socket.close()

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('127.0.0.1', port))
    print(f"Servidor DNS ouvindo na porta {port}...")

    while True:
        data, client_address = server_socket.recvfrom(1024)
        print("Mensagem recebida de", client_address)

        header = parse_dns_header(data)
        offset = 12
        questions = []
        for _ in range(header['questions']):
            question, offset = parse_dns_question(data, offset)
            questions.append(question)
            print(f"Pergunta - nome:{question['name']} tipo:{question['type']} classe:{question['class']}")

        # Verificar cache
        if questions:
            cached_response = check_cache(questions[0])
            if cached_response:
                # Atualizar o ID da transação na resposta em cache
                request_id = struct.unpack('!H', data[:2])[0]
                updated_response = bytearray(cached_response)
                updated_response[:2] = struct.pack('!H', request_id)
                server_socket.sendto(updated_response, client_address)
                print("Resposta enviada do cache para", client_address)
                continue

        # Encaminhar a solicitação
        forward_request(data, client_address, server_socket)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DNS Forwarder - Etapa 5")
    parser.add_argument('--port', type=int, default=1053, help="Porta para ouvir (padrão: 1053)")
    args = parser.parse_args()
    
    start_server(args.port)