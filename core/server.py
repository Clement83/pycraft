import socket
import threading

class Server:
    def __init__(self, port, seed):
        self.port = port
        self.seed = seed
        self.clients = []
        self.server_socket = None
        self.running = False

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(5)
        print(f"Server started on port {self.port}")

        thread = threading.Thread(target=self.accept_clients)
        thread.daemon = True
        thread.start()

    def accept_clients(self):
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"Client connected from {client_address}")
                self.clients.append(client_socket)
                self.handle_client(client_socket)
            except OSError:
                break

    def handle_client(self, client_socket):
        try:
            # Send the seed to the client
            client_socket.send(f"seed:{self.seed}\n".encode('utf-8'))

            # Handle client messages
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                # For now, just print the data
                print(f"Received from client: {data.decode('utf-8')}")
        except ConnectionResetError:
            print("Client disconnected")
        finally:
            self.clients.remove(client_socket)
            client_socket.close()

    def stop(self):
        self.running = False
        for client in self.clients:
            client.close()
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.server_socket.close()
        print("Server stopped")

    def get_client_count(self):
        return len(self.clients)
