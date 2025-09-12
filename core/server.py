import socket
import threading
import json
import uuid

class Server:
    def __init__(self, port, seed):
        self.port = port
        self.seed = seed
        self.clients = {} # Dictionary to store client_socket and player_id
        self.player_data = {} # Dictionary to store player_id -> {position, rotation}
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
        self.server_socket.settimeout(1.0) # Set a timeout for accept()
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_socket.setblocking(False) # Set client socket to non-blocking
                player_id = str(uuid.uuid4()) # Generate a unique ID for the player
                print(f"Client {player_id} connected from {client_address}")
                self.clients[player_id] = client_socket
                self.player_data[player_id] = {"position": (0,0,0), "rotation": (0,0)} # Initial data

                thread = threading.Thread(target=self.handle_client, args=(client_socket, player_id))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                pass # No new connection, check self.running again
            except OSError:
                break
            except Exception as e:
                print(f"Error accepting client: {e}")
                break

    def handle_client(self, client_socket, player_id):
        try:
            # Send the seed to the client
            client_socket.send(f"seed:{self.seed}\n".encode('utf-8'))

            # Send initial player data to the newly connected client
            self.send_all_player_data_to_client(client_socket, player_id)

            # Handle client messages
            while self.running:
                try:
                    data = client_socket.recv(4096) # Increased buffer size
                    if not data: # Client disconnected
                        break
                    
                    try:
                        messages = data.decode('utf-8').split('}{') # Handle multiple JSON objects
                        for msg in messages:
                            if not msg.startswith('{'):
                                msg = '{' + msg
                            if not msg.endswith('}'):
                                msg = msg + '}'
                            
                            parsed_data = json.loads(msg)
                            if parsed_data.get("type") == "player_update":
                                position = parsed_data["position"]
                                rotation = parsed_data["rotation"]
                                self.player_data[player_id] = {"position": position, "rotation": rotation}
                                self.broadcast_player_data(player_id)

                    except json.JSONDecodeError:
                        print(f"Received malformed JSON from {player_id}: {data.decode('utf-8')}")
                    except Exception as e:
                        print(f"Error processing data from {player_id}: {e}")

                except BlockingIOError:
                    # No data available, wait a bit before trying again to avoid busy-waiting
                    time.sleep(0.01) # Small delay
                except ConnectionResetError:
                    print(f"Client {player_id} disconnected unexpectedly.")
                    break # Exit loop on disconnect
                except Exception as e:
                    print(f"Error receiving data from {player_id}: {e}")
                    break # Exit loop on other errors

        except ConnectionResetError:
            print(f"Client {player_id} disconnected")
        finally:
            if player_id in self.clients:
                del self.clients[player_id]
            if player_id in self.player_data:
                del self.player_data[player_id]
            client_socket.close()
            self.broadcast_player_disconnect(player_id)

    def send_all_player_data_to_client(self, client_socket, current_player_id):
        # Send data of all other players to the newly connected client
        players_to_send = {}
        for p_id, p_data in self.player_data.items():
            if p_id != current_player_id:
                players_to_send[p_id] = p_data
        
        if players_to_send:
            message = {"type": "all_player_data", "players": players_to_send}
            try:
                client_socket.sendall(json.dumps(message).encode('utf-8'))
            except Exception as e:
                print(f"Error sending all player data to {current_player_id}: {e}")

    def broadcast_player_data(self, sender_id):
        # Prepare data for broadcasting
        data_to_broadcast = {}
        for player_id, player_info in self.player_data.items():
            if player_id != sender_id: # Don't send back to the sender
                data_to_broadcast[player_id] = player_info

        if not data_to_broadcast: # No other players to broadcast to
            return

        message = {"type": "player_update", "players": data_to_broadcast}
        encoded_message = json.dumps(message).encode('utf-8')

        for player_id, client_socket in self.clients.items():
            if player_id != sender_id: # Send to all other clients
                try:
                    client_socket.sendall(encoded_message)
                except Exception as e:
                    print(f"Error broadcasting to client {player_id}: {e}")

    def broadcast_player_disconnect(self, disconnected_player_id):
        message = {"type": "player_disconnect", "player_id": disconnected_player_id}
        encoded_message = json.dumps(message).encode('utf-8')

        for player_id, client_socket in self.clients.items():
            try:
                client_socket.sendall(encoded_message)
            except Exception as e:
                print(f"Error broadcasting disconnect to client {player_id}: {e}")

    def stop(self):
        self.running = False
        for client_socket in self.clients.values():
            client_socket.close()
        if self.server_socket:
            try:
                self.server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.server_socket.close()
        print("Server stopped")

    def get_client_count(self):
        return len(self.clients)
