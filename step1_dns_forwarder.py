import socket
import argparse

def start_server(port):
    # Criar socket UDP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('127.0.0.1', port))
    print(f"Servidor DNS ouvindo na porta {port}...")

    while True:
        # Receber dados
        data, client_address = server_socket.recvfrom(1024)
        print("Mensagem recebida de", client_address)

if __name__ == "__main__":
    # Configurar argumento de linha de comando para a porta
    parser = argparse.ArgumentParser(description="DNS Forwarder")
    parser.add_argument('--port', type=int, default=1053, help="Porta para ouvir (padrão: 1053)")
    args = parser.parse_args()
    
    start_server(args.port)