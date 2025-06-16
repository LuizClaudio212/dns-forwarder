import socket
import argparse
import struct

def parse_dns_header(data):
    # Desempacotar os 12 bytes do cabeçalho (RFC 1035, Seção 4.1.1)
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
    # Extrair o nome do domínio
    name, offset = parse_dns_name(data, offset)
    # Tipo e classe (2 bytes cada)
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

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('127.0.0.1', port))
    print(f"Servidor DNS ouvindo na porta {port}...")

    while True:
        data, client_address = server_socket.recvfrom(1024)
        print("Mensagem recebida de", client_address)

        # Parsear o cabeçalho
        header = parse_dns_header(data)
        print(f"Cabeçalho - id:{header['id']} flags:{header['flags']} "
              f"questions:{header['questions']} answers:{header['answers']} "
              f"authorities:{header['authorities']} additionals:{header['additionals']}")

        # Parsear a seção de perguntas
        offset = 12  # Após o cabeçalho
        for _ in range(header['questions']):
            question, offset = parse_dns_question(data, offset)
            print(f"Pergunta - nome:{question['name']} tipo:{question['type']} classe:{question['class']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DNS Forwarder - Etapa 2")
    parser.add_argument('--port', type=int, default=1053, help="Porta para ouvir (padrão: 1053)")
    args = parser.parse_args()
    
    start_server(args.port)