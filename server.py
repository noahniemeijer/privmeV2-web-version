import socket, threading
from cryptidy import asymmetric_encryption as ae

# Some server constants
HOST = "0.0.0.0"
PORT = 5556
USERNAME_MAX_LENGTH = 20
USERNAME_ALLOW_SPACES = False
SERVER_VERSION = 0.0

# Server variables
clients = []      # These variables are synced
keys = []       # This means users[1] corresponds to keys[1]
users = []


# Send a message to all clients except the sender
def send_message(message, sender=None):
    # Loop over all of the connected clients
    for i in range(len(clients)):
        # Check if the current client is the sender, if it is, skip it
        if clients[i] == sender:
            continue

        # Send the message to the client with their respective key
        msg = ae.encrypt_message(message, keys[i])
        clients[i].send(msg)


# Handle the clients
# This function is run for every connected client
def handle_client(client, publicKey, privateKey, clientKey):

    # Start the handshake
    Recieving = False

    try:
        while not Recieving:
            # Setup the connection as per the clients requests
            message = client.recv(4096)
            time, message = ae.decrypt_message(message, privateKey)

            if message == "START_CONNECTION":
                # Start recieving messages from client
                Recieving = True
                send_message(f"{username} Joined the chat")

            elif message == "START_NAME_TRANSFER":
                # encrypt the username info to send
                info = ae.encrypt_message(USERNAME_MAX_LENGTH, clientKey)
                client.send(info)

                usernameAccepted = False
                while not usernameAccepted:
                    # recieve the username from the user
                    username = client.recv(4096)
                    time, username = ae.decrypt_message(username, privateKey)

                    status = ae.encrypt_message("VALID", clientKey)
                    usernameAccepted = True

                    #check if the username is valid
                    if len(username) > USERNAME_MAX_LENGTH:
                        status = ae.encrypt_message("INVALID", clientKey)
                        usernameAccepted = False

                    if " " in username and not USERNAME_ALLOW_SPACES:
                        status = ae.encrypt_message("INVALID", clientKey)
                        usernameAccepted = False

                    client.send(status)

                # append the accepted name into the list
                users.append(username)

        # Recieve messages from the client
        while 1:
            message = client.recv(4096)

            # If the message is completely empty, (this occurs when someone
            # Leaves), remove the user from all lists, and break the
            # connection to prevent ERROR 32: broken pipe
            if message == b'':
                remove_client(client, username)
                return

            time, message = ae.decrypt_message(message, privateKey)

            print(time, username,  message)
            send_message(f"{username}: {message}", client)

    except Exception as error:
        print(f"Error: {error}")


# Removes a client
def remove_client(client, username):
    clientId = clients.index(client)
    clients.pop(clientId)
    keys.pop(clientId)
    users.remove(username)

    client.close()

    send_message(f"{username} Left the chat")


# Guess what this does
def run_server():
    print("starting server...")

    # Initialise the keys
    print("creating keypair...")
    privateKey, publicKey = ae.generate_keys(4096)

    print("setting up socket...")
    # Initialise the server
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind((HOST, PORT))
    serverSocket.listen()

    print("succes!")

    print(f"started server on {HOST}:{PORT}")

    while 1:
        # Recieve clients
        client, address = serverSocket.accept()

        # Register the user
        clients.append(client)

        # Send public key to the client
        client.send(publicKey.encode())

        # Recieve clients public key and decrypt it
        clientKey = client.recv(4096)
        time, clientKey = ae.decrypt_message(clientKey, privateKey)

        # Add the key to the list of keys
        keys.append(clientKey)

        # Start a worker thread that will handle this client
        threading.Thread(target=handle_client, args=(client, publicKey, privateKey, clientKey)).start()



if __name__ == "__main__":
    run_server()
