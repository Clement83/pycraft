import socket

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        print(f"Connected to server at {self.host}:{self.port}")

        # Receive the seed
        data = self.socket.recv(1024).decode('utf-8')
        if data.startswith("seed:"):
            seed = data.split(":")[1].strip()
            print(f"Received seed: {seed}")
            return seed
        return None

    def close(self):
        if self.socket:
            self.socket.close()
            print("Connection closed")
