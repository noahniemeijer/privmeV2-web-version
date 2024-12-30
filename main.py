import socket, threading
from time import sleep
import asymmetric_encryption as ae

# guess what this does
def run_client(privateKey, publicKey):
    # prompt user for host and port
    host = input("host: ")
    port = int(input("port: "))

    # setup client socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((host, port))

    # recieve the server Key
    serverKey = clientSocket.recv(4069).decode('utf-8')

    # From this point onwards we only use asymmetrical encryption
    # Messages must be encrypted with the servers public key

    # send the public key to the server
    send_server(clientSocket, publicKey, serverKey)

    # Wait for the server to ping us
    recv_server(clientSocket, privateKey)

    # start the username transfer
    send_server(clientSocket, "START_NAME_TRANSFER", serverKey)

    # Recieve the max length for usernames
    time, maxUserLength = recv_server(clientSocket, privateKey)

    usernameStatus = "INVALID"

    #continue prompting for username until it meets server requirements
    while usernameStatus != "VALID":

        print(f"username must be less than {maxUserLength} chars")

        #prompt the user for their name
        username = input("username: ")

        # Send the username to the server
        send_server(clientSocket, username, serverKey)

        time, usernameStatus = recv_server(clientSocket, privateKey)
        print(usernameStatus)

    # tell the server we are ready to start sending messages
    send_server(clientSocket, "START_CONNECTION", serverKey)

    #start sending messages
    threading.Thread(target=recieve_messages, args=(clientSocket, privateKey,), daemon=True).start()
    send_messages(clientSocket, serverKey)


# listen for messages from the server
def recieve_messages(client, privateKey):
    while 1:
        # recieve a 4096 bit block of data and decrypt it
        time, message = recv_server(client, privateKey)
        # print it to the screen
        print(time, message)


# keep asking for and sending messages to server
def send_messages(client, serverKey):
    while 1:
        # get input and encrypt it using the servers public key
        message = input()

        # send the message to the server
        send_server(client, message, serverKey)


# Send the specified message t the server, using its key as encryption
def send_server(socket, message, serverKey):
    message = ae.encrypt_message(message, serverKey)
    socket.send(message)


# get and decrypt a message from the server
def recv_server(socket, privateKey):
    message = socket.recv(4096)
    time, message = ae.decrypt_message(message, privateKey)
    return time, message


if __name__ == "__main__":
    print("starting client...")
    # generate the keypair
    print("generating keypairs...")

    privateKey, publicKey = ae.generate_keys(4096)

    print("succes!")
    run_client(privateKey, publicKey)
