import socket
import argparse
import struct

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
        offset += 1
        if length == 0:
            break
        name_parts.append(data[offset:offset+length].decode('ascii'))
        offset += length
    return '.'.join(name_parts), offset

def forward_request(data, client_address, server_socket, upstream_dns='8.8.8.8', upstream_port=53):
    upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    upstream_socket.settimeout(5)  # Timeout de 5 segundos
    upstream_socket.sendto(data, (upstream_dns, upstream_port))
    print("Solicitação encaminhada para", upstream_dns)

    try:
        # Receber resposta
        response, _ = upstream_socket.recvfrom(1024)
        # Enviar resposta ao cliente original
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

        # Parsear o cabeçalho e a pergunta (para depuração)
        header = parse_dns_header(data)
        print(f"Cabeçalho - id:{header['id']} flags:{header['flags']} "
              f"questions:{header['questions']} answers:{header['answers']} "
              f"authorities:{header['authorities']} additionals:{header['additionals']}")

        offset = 12
        for _ in range(header['questions']):
            question, offset = parse_dns_question(data, offset)
            print(f"Pergunta - nome:{question['name']} tipo:{question['type']} classe:{question['class']}")

        # Encaminhar a solicitação e enviar a resposta
        forward_request(data, client_address, server_socket)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DNS Forwarder - Etapa 4")
    parser.add_argument('--port', type=int, default=1053, help="Porta para ouvir (padrão: 1053)")
    args = parser.parse_args()
    
    start_server(args.port)