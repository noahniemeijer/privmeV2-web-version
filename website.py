import socket
import asyncio
import json
import traceback
import websockets
import asymmetric_encryption as ae

CHAT_SERVER_HOST = "127.0.0.1"
CHAT_SERVER_PORT = 5555

WS_HOST = "0.0.0.0"
WS_PORT = 8765     

async def send_to_chat_server(tcp_socket, message, server_public_key_pem):
    # Sends encrypted message to server
    try:
        encrypted_message = await asyncio.to_thread(ae.encrypt_message, message, server_public_key_pem)
        await asyncio.to_thread(tcp_socket.sendall, encrypted_message)
    except Exception as e:
        print(f"Error sending to chat server: {e}")
        raise

async def recv_from_chat_server(tcp_socket, private_key_pem):
    # Receives encrypted message from server
    try:
        data = await asyncio.to_thread(tcp_socket.recv, 4096)
        if not data:
            raise ConnectionError("Chat server disconnected.")
        if data == b'\x10':
            raise ConnectionError("The chat server quit unexpectedly.")
        
        time, message = await asyncio.to_thread(ae.decrypt_message, data, private_key_pem)
        return time, message
    except Exception as e:
        print(f"Error receiving/decrypting from chat server: {e}")
        raise

async def handle_websocket_client(websocket, path):
    """
    Verwerkt een nieuwe WebSocket-verbinding van een browserclient.
    Elke browserclient krijgt zijn eigen TCP-verbinding met de chatserver.
    """
    client_address = websocket.remote_address
    print(f"New WebSocket connection from {client_address}")

    tcp_client_socket = None
    private_key_pem = None
    server_public_key_pem = None

    try:
        # 1. Setup TCP-connection with chatserver
        tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            await asyncio.to_thread(tcp_client_socket.connect, (CHAT_SERVER_HOST, CHAT_SERVER_PORT))
            print(f"Client {client_address}: Connected to chat server at {CHAT_SERVER_HOST}:{CHAT_SERVER_PORT}")
        except ConnectionRefusedError:
            await websocket.send(json.dumps({"type": "error", "message": f"Could not connect to chat server at {CHAT_SERVER_HOST}:{CHAT_SERVER_PORT}. Is it running?"}))
            raise # Her-gooi om de outer try/except te triggeren
        
        # 2. Generating keypair
        private_key_pem, public_key_pem = await asyncio.to_thread(ae.generate_keys, 4096)
        print(f"Client {client_address}: Generated keypair.")

        # 3. Receiving server public key
        server_key_bytes = await asyncio.to_thread(tcp_client_socket.recv, 4096)
        server_public_key_pem = server_key_bytes.decode('utf-8')
        print(f"Client {client_address}: Received server public key.")

        # 4. Sending public key
        await send_to_chat_server(tcp_client_socket, public_key_pem, server_public_key_pem)
        print(f"Client {client_address}: Sent client public key.")

        # 5. Connection handshake
        _, status_ok = await recv_from_chat_server(tcp_client_socket, private_key_pem)
        if status_ok != "OK":
            raise Exception("Server did not send initial 'OK' after key exchange.")
        await websocket.send(json.dumps({"type": "status", "message": "Connected to chat server gateway. Proceeding with handshake."}))

        # Choosing a username
        await send_to_chat_server(tcp_client_socket, "START_NAME_TRANSFER", server_public_key_pem)
        _, max_user_length = await recv_from_chat_server(tcp_client_socket, private_key_pem)
        await websocket.send(json.dumps({"type": "username_prompt", "maxLength": max_user_length}))

        username_accepted = False
        username = ""
        while not username_accepted:
            response_json = await websocket.recv()
            response = json.loads(response_json)
            if response.get("type") != "username_input":
                raise ValueError("Expected username input from browser.")
            username = response["username"]

            await send_to_chat_server(tcp_client_socket, username, server_public_key_pem)
            _, username_status = await recv_from_chat_server(tcp_client_socket, private_key_pem)
            await websocket.send(json.dumps({"type": "username_status", "status": username_status}))
            
            if username_status == "VALID":
                username_accepted = True
            else:
                print(f"Client {client_address}: Username '{username}' invalid: {username_status}")

        print(f"Client {client_address}: Username accepted: {username}")

        # Configuring group
        await send_to_chat_server(tcp_client_socket, "START_GROUP_SELECT", server_public_key_pem)
        _, available_groups = await recv_from_chat_server(tcp_client_socket, private_key_pem)
        await websocket.send(json.dumps({"type": "group_prompt", "groups": available_groups}))

        group_selected = False
        while not group_selected:
            response_json = await websocket.recv()
            response = json.loads(response_json)
            if response.get("type") != "group_action":
                raise ValueError("Expected group action from browser.")

            action = response.get("action")
            group_name = response.get("groupName")
            password = response.get("password", "")

            await send_to_chat_server(tcp_client_socket, action, server_public_key_pem)
            _, action_status = await recv_from_chat_server(tcp_client_socket, private_key_pem)
            if action_status != "OK":
                await websocket.send(json.dumps({"type": "group_status", "status": "ERROR", "message": f"Server rejected action: {action_status}"}))
                continue

            if action == "join":
                await send_to_chat_server(tcp_client_socket, group_name, server_public_key_pem)
                _, join_status = await recv_from_chat_server(tcp_client_socket, private_key_pem)

                if join_status == "BAD":
                    await websocket.send(json.dumps({"type": "group_status", "status": "BAD_GROUP", "message": f"Group '{group_name}' not found."}))
                elif join_status == "NO PASSWORD":
                    await websocket.send(json.dumps({"type": "group_status", "status": "JOINED", "message": f"Joined group '{group_name}' (no password)." }))
                    group_selected = True
                elif join_status == "OK":
                    hashed_password = await asyncio.to_thread(ae.generate_hash, password)
                    await send_to_chat_server(tcp_client_socket, hashed_password, server_public_key_pem)
                    _, password_status = await recv_from_chat_server(tcp_client_socket, private_key_pem)
                    if password_status == "OK":
                        await websocket.send(json.dumps({"type": "group_status", "status": "JOINED", "message": f"Joined group '{group_name}'."}))
                        group_selected = True
                    else:
                        await websocket.send(json.dumps({"type": "group_status", "status": "INCORRECT_PASSWORD", "message": "Incorrect password."}))
            elif action == "create":
                await send_to_chat_server(tcp_client_socket, group_name, server_public_key_pem)
                _, create_status = await recv_from_chat_server(tcp_client_socket, private_key_pem)
                if create_status == "OK":
                    hashed_password = ""
                    if password:
                        hashed_password = await asyncio.to_thread(ae.generate_hash, password)
                    await send_to_chat_server(tcp_client_socket, hashed_password, server_public_key_pem)
                    await websocket.send(json.dumps({"type": "group_status", "status": "CREATED_JOINED", "message": f"Created and joined group '{group_name}'."}))
                    group_selected = True
                elif create_status == "BAD":
                    await websocket.send(json.dumps({"type": "group_status", "status": "GROUP_EXISTS", "message": f"Group '{group_name}' already exists."}))
                elif create_status == "TOO LONG":
                    await websocket.send(json.dumps({"type": "group_status", "status": "NAME_TOO_LONG", "message": "Group name is too long."}))

        print(f"Client {client_address}: Group selected.")

        # Starting Chat Session
        await send_to_chat_server(tcp_client_socket, "START_CONNECTION", server_public_key_pem)
        time_obj, first_chat_message = await recv_from_chat_server(tcp_client_socket, private_key_pem)
        await websocket.send(json.dumps({"type": "chat_message", "content": first_chat_message, "time": time_obj.isoformat()}))
        await websocket.send(json.dumps({"type": "chat_ready", "message": "Chat session started!"}))

        # Sending messages
        async def send_messages_to_chat_server_task():
            while True:
                try:
                    message_json = await websocket.recv()
                    message_data = json.loads(message_json)
                    
                    if message_data["type"] == "chat_message":
                        chat_message_content = message_data["content"]
                        await send_to_chat_server(tcp_client_socket, chat_message_content, server_public_key_pem)
                    elif message_data["type"] == "disconnect":
                        print(f"Client {client_address}: Disconnect request from browser.")
                        await send_to_chat_server(tcp_client_socket, "", server_public_key_pem) 
                        break
                except websockets.exceptions.ConnectionClosedOK:
                    print(f"Client {client_address}: WebSocket connection closed gracefully.")
                    break
                except websockets.exceptions.ConnectionClosedError as e:
                    print(f"Client {client_address}: WebSocket connection closed with error: {e}")
                    break
                except json.JSONDecodeError:
                    print(f"Client {client_address}: Received invalid JSON from browser.")
                except Exception as e:
                    print(f"Client {client_address}: Error sending message to chat server: {e}")
                    traceback.print_exc() # Print de volledige traceback
                    break # Breek de lus af bij kritieke fouten

        # Receive messages
        async def recieve_messages_from_chat_server_task():
            while True:
                try:
                    time_obj, message_content = await recv_from_chat_server(tcp_client_socket, private_key_pem)
                    
                    if message_content == "SPAM":
                        print(f"Client {client_address}: SPAM detected from chat server.")
                        await websocket.send(json.dumps({"type": "error", "message": "SERVER ALERT: SPAM DETECTED. Your messages are being rate-limited."}))
                        continue
                    await websocket.send(json.dumps({"type": "chat_message", "content": message_content, "time": time_obj.isoformat()}))
                except ConnectionError as e:
                    print(f"Client {client_address}: Chat server connection lost: {e}")
                    await websocket.send(json.dumps({"type": "error", "message": f"Chat server disconnected: {e}"}))
                    break # Breek de lus af
                except Exception as e:
                    print(f"Client {client_address}: Error receiving message from chat server: {e}")
                    traceback.print_exc()
                    await websocket.send(json.dumps({"type": "error", "message": f"Error receiving message: {e}"}))
                    break # Breek de lus af bij fouten

        sender_task = asyncio.create_task(send_messages_to_chat_server_task())
        receiver_task = asyncio.create_task(recieve_messages_from_chat_server_task())
        done, pending = await asyncio.wait([sender_task, receiver_task], return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client {client_address}: WebSocket connection closed normally during handshake.")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Client {client_address}: WebSocket connection closed with error during handshake: {e}")
    except ConnectionRefusedError:
        print(f"Client {client_address}: Could not connect to chat server at {CHAT_SERVER_HOST}:{CHAT_SERVER_PORT}. Are you sure it's running?")
    except Exception as e:
        print(f"Client {client_address}: Unhandled error in handle_websocket_client: {e}")
        traceback.print_exc()
        try:
            await websocket.send(json.dumps({"type": "error", "message": f"An internal server error occurred: {e}"}))
        except websockets.exceptions.ConnectionClosed:
            pass
    finally:
        if tcp_client_socket:
            print(f"Client {client_address}: Closing TCP connection to chat server.")
            tcp_client_socket.close()
        print(f"Client {client_address}: WebSocket connection closed for {client_address}.")


# Starting websocket

async def main():
    print(f"Starting WebSocket gateway on ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(handle_websocket_client, WS_HOST, WS_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWebSocket gateway stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred in the main WebSocket gateway loop: {e}")
        traceback.print_exc()