import socket
import json
import threading
import time # Added for time.time() and time.sleep()
from core.player_sprite import PlayerSprite

class Client:
    def __init__(self, host, port, program=None): # Added program
        self.host = host
        self.port = port
        self.socket = None
        self.other_players = {} # To store other players' sprites
        self._running = False # Flag to control the receiver thread
        self._receive_thread = None # To hold the receiver thread object
        self.program = program # Store the program

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5) # 5 seconds timeout for connection
        try:
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            self.socket.settimeout(None) # Remove timeout after successful connection
            self.socket.setblocking(False) # Set socket to non-blocking mode

            # --- Handle initial seed reception in a non-blocking way ---
            seed_data = ""
            start_time = time.time()
            while time.time() - start_time < 5: # Try for up to 5 seconds to get the seed
                try:
                    data = self.socket.recv(1024).decode('utf-8')
                    if data:
                        seed_data += data
                        if "seed:" in seed_data: # Check if we have enough data for the seed
                            break
                except BlockingIOError:
                    time.sleep(0.01) # Wait a bit before retrying
                except Exception as e:
                    print(f"Error receiving seed: {e}")
                    self.close()
                    return None
            
            if seed_data.startswith("seed:"):
                seed = seed_data.split(":")[1].strip()
                print(f"Received seed: {seed}")

                # Start the receiver thread
                self._running = True
                self._receive_thread = threading.Thread(target=self._receive_data_loop, daemon=True)
                self._receive_thread.start()

                return seed
            else:
                print("Did not receive seed from server within timeout.")
                self.close()
                return None
            # --- End of seed reception handling ---

        except socket.timeout:
            print(f"Connection to {self.host}:{self.port} timed out.")
            self.close()
            return None
        except ConnectionRefusedError:
            print(f"Connection to {self.host}:{self.port} refused. Is the server running?")
            self.close()
            return None
        except Exception as e:
            print(f"Error during connection: {e}")
            self.close()
            return None

    def close(self):
        self._running = False # Stop the receiver thread
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=1) # Wait for thread to finish, with a timeout
            if self._receive_thread.is_alive():
                print("Warning: Receiver thread did not terminate gracefully.")

        if self.socket:
            self.socket.close()
            print("Connection closed")
            self.socket = None # Clear the socket reference

    def send_player_data(self, position, rotation):
        if self.socket and self._running: # Only send if connected and running
            data = {
                "type": "player_update",
                "position": position,
                "rotation": rotation
            }
            try:
                # sendall might still block if the buffer is full, even with non-blocking socket.
                # For a game, you might want to queue data and send it in chunks.
                # For now, we'll just catch BlockingIOError.
                self.socket.sendall(json.dumps(data).encode('utf-8'))
            except BlockingIOError:
                # This means the send buffer is full, try again later
                pass
            except Exception as e:
                print(f"Error sending player data: {e}")
                self.close() # Close connection on send error

    def _receive_data_loop(self):
        buffer = "" # To handle partial messages
        while self._running:
            try:
                # Try to receive data. This will raise BlockingIOError if no data is available.
                data = self.socket.recv(4096).decode('utf-8')
                if not data: # Server closed the connection
                    print("Server closed the connection.")
                    self._running = False
                    break

                buffer += data
                while '}' in buffer: # Process complete JSON objects
                    end_index = buffer.find('}')
                    if end_index == -1: # Should not happen if '}' is in buffer
                        break
                    
                    json_str = buffer[:end_index + 1]
                    buffer = buffer[end_index + 1:] # Remove processed part from buffer

                    try:
                        parsed_data = json.loads(json_str)
                        if parsed_data.get("type") == "player_update" and "players" in parsed_data: # Corrected condition
                            for player_id, player_info in parsed_data["players"].items():
                                position = player_info["position"]
                                rotation = player_info["rotation"]

                                if player_id not in self.other_players:
                                    # Pass self.program to PlayerSprite constructor
                                    self.other_players[player_id] = PlayerSprite(position, rotation, program=self.program)
                                else:
                                    # PlayerSprite.update now expects view_matrix, will be passed from draw_other_players
                                    self.other_players[player_id].update(position, rotation)
                        elif parsed_data.get("type") == "player_disconnect" and "player_id" in parsed_data:
                            player_id = parsed_data["player_id"]
                            if player_id in self.other_players:
                                # When a player disconnects, delete their sprite's vertex list
                                if self.other_players[player_id].vertex_list:
                                    self.other_players[player_id].vertex_list.delete()
                                del self.other_players[player_id]
                        # Handle "all_player_data" type for initial sync
                        elif parsed_data.get("type") == "all_player_data" and "players" in parsed_data:
                            for player_id, player_info in parsed_data["players"].items():
                                position = player_info["position"]
                                rotation = player_info["rotation"]
                                if player_id not in self.other_players:
                                    # Pass self.program to PlayerSprite constructor
                                    self.other_players[player_id] = PlayerSprite(position, rotation, program=self.program)
                                else:
                                    # PlayerSprite.update now expects view_matrix, will be passed from draw_other_players
                                    self.other_players[player_id].update(position, rotation)
                    except json.JSONDecodeError:
                        print(f"Received malformed JSON: {json_str}")
                        # If malformed, try to find the next '{' to resync
                        next_start = buffer.find('{')
                        if next_start != -1:
                            buffer = buffer[next_start:]
                        else:
                            buffer = "" # Clear buffer if no start found
            except BlockingIOError:
                # No data available, wait a bit before trying again to avoid busy-waiting
                time.sleep(0.01) # Small delay
            except Exception as e:
                print(f"Error in receive thread: {e}")
                self._running = False # Stop thread on error
                self.close() # Close connection
                break

    # The original receive_player_data is no longer needed as it's handled by the thread
    # Keeping it for now, but it will be removed or refactored.
    def receive_player_data(self):
        # This method is now effectively a no-op as data reception is threaded.
        # It's kept for compatibility with existing calls in ui/window.py for now.
        pass

    def draw_other_players(self, view_matrix): # Added view_matrix parameter
        for player_sprite in self.other_players.values():
            player_sprite.update(player_sprite.position, player_sprite.rotation, view_matrix) # Update with current position/rotation and view_matrix
            player_sprite.draw()
