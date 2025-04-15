# Copyright 2024, 2025 Floris Tabak
#
# This file is part of PrivMe
# PrivMe is a free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public Licence as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# PrivMe is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for more details.
#
# You should have recieved a copy of the GNU General Public License
# along with PrivMe. If not, see <https://www.gnu.org/licenses/>.

import socket, threading
from time import sleep
from datetime import datetime
import asymmetric_encryption as ae
import curses as c
import ncurses_wrapper as nc

messages = [] #insane

# guess what this does
def run_client(stdscr, privateKey, publicKey):
    maxY, maxX = stdscr.getmaxyx()
    
    # prompt user for host and port
    nc.clear_line(stdscr, maxY//2, 0, 0)
    nc.draw_text(stdscr,
                 maxY//2,
                 maxX//2-(len("host:")//2),
                 "host:")
    host = nc.get_input(stdscr,
                        maxY//2+1,
                        maxX//2-(len("host:")//2)-1,
                        "")

    nc.clear_block(stdscr, maxY//2, maxY//2+1, 0, 0)
    nc.draw_text(stdscr,
                 maxY//2,
                 maxX//2-(len("port:")//2),
                 "port:")
    port = int(nc.get_input(stdscr,
                            maxY//2+1,
                            maxX//2-(len("port:")//2)-1,
                            ""))

    # setup client socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((host, port))

    nc.clear_block(stdscr, maxY//2-1, maxY//2+1, 0, 0)
    nc.draw_background(stdscr, host)

    # recieve the server Key
    serverKey = clientSocket.recv(4069).decode('utf-8')

    # From this point onwards we only use asymmetrical encryption
    # Messages must be encrypted with the servers public key

    # send the public key to the server
    send_server(clientSocket, publicKey, serverKey)

    # Wait for the server to ping us
    recv_server(clientSocket, privateKey)

    # start the username protocol
    username_transfer(stdscr, clientSocket, privateKey, serverKey)

    # start the group protocol
    group_transfer(stdscr, clientSocket, privateKey, serverKey)

    # tell the server we are ready to start sending messages
    send_server(clientSocket, "START_CONNECTION", serverKey)

    nc.clear_block(stdscr,
                   4, maxY-4,
                   0, 0)

    #start sending messages
    threading.Thread(target=recieve_messages, args=(stdscr, clientSocket, privateKey,), daemon=True).start()
    send_messages(stdscr, clientSocket, serverKey)


def username_transfer(stdscr, clientSocket, privateKey, serverKey):
    maxY, maxX = stdscr.getmaxyx()
    # start the username transfer
    send_server(clientSocket, "START_NAME_TRANSFER", serverKey)

    # Recieve the max length for usernames
    time, maxUserLength = recv_server(clientSocket, privateKey)

    usernameStatus = "INVALID"

    #continue prompting for username until it meets server requirements
    while usernameStatus != "VALID":

        nc.clear_block(stdscr,
                       maxY//2-1,
                       maxY//2+1,
                       0, 0)

        nc.draw_text(stdscr,
                     maxY//2-1,
                     maxX//2-(len(f"username must be less than {maxUserLength} chars")//2),
                     f"username must be less than {maxUserLength} chars")

        #prompt the user for their name
        nc.draw_text(stdscr,
                     maxY//2,
                     maxX//2-(len("username:")//2),
                     "username:")
        username = nc.get_input(stdscr,
                                maxY//2+1,
                                maxX//2-(len("username:")//2)-1,
                                "")


        # Send the username to the server
        send_server(clientSocket, username, serverKey)
        
        # get the status
        time, usernameStatus = recv_server(clientSocket, privateKey)


def group_transfer(stdscr, clientSocket, privateKey, serverKey):
    maxY, maxX = stdscr.getmaxyx()

    # tell the server that we want to send something
    send_server(clientSocket, "START_GROUP_SELECT", serverKey) # 1

    # recieve the current open groups
    time, groups = recv_server(clientSocket, privateKey) # 2

    # boilerplate text
    nc.clear_block(stdscr,
                   maxY//2-1,
                   maxY//2+1,
                   0,
                   0)

    nc.draw_text_overflow(stdscr,
                          maxY//2-3,
                          maxX//2-(len(f"there are {len(groups) if len(groups) != 0 else 'no available'} groups")//2),
                          f"there are {len(groups) if len(groups) != 0 else 'no available'} groups")

    # display the groups
    row, column = 0, 0
    for i in range(len(groups)):
        row = i//3
        column = i%3

        nc.draw_text(stdscr,
                     maxY//2-2+row,
                     maxX//2+(column*20-20)-(len(groups[i])//2),
                     groups[i])

    stdscr.refresh()

    while 1:
        # prompt the user for an action
        nc.draw_text(stdscr,
                     maxY//2+row,
                     maxX//2-(len("do you want to [join] or [create] a group (join):")//2),
                     "do you want to [join] or [create] a group (join):")

        action = nc.get_input(stdscr,
                       maxY//2+row+1,
                       maxX//2-4,
                       "")

        nc.clear_block(stdscr, maxY//2-3, maxY//2+row+2, 0, 0)
        
        if action != "create":
            #tell the server we want to join
            send_server(clientSocket, "join", serverKey) # 3

            time, status = recv_server(clientSocket, privateKey) # 4

            try:
                # prompt for group
                nc.draw_text(stdscr,
                             maxY//2-1,
                             maxX//2-(len("which group would you like to join?:")//2),
                             "which group would you like to join?:")

                group = nc.get_input(stdscr,
                                     maxY//2,
                                     maxX//2-(len("which group would you like to join?:")//2),
                                     "")
            except KeyboardInterrupt:
                # upon keyboardinterrupt, go back to the previous menu
                send_server(clientSocket, 0x01, serverKey) # 5
                recv_server(clientSocket, privateKey) # 6
                print('\n')
                continue

            # send the group to the server
            send_server(clientSocket, group, serverKey) # 5

            time, status = recv_server(clientSocket, privateKey) # 6

            nc.clear_block(stdscr,
                           maxY//2-2, maxY//2+2,
                           0, 0)

            if status == "BAD":
                # if the status doesn't return ok, repeat the process
                nc.draw_text(stdscr,
                             maxY//2,
                             maxX//2-(len(f"invalid group {group}")//2),
                             f"invalid group {group}")
                nc.wait_for_enter(stdscr)
                nc.clear_line(stdscr,
                              maxY//2,
                              0,0)
                continue

            elif status == "NO PASSWORD":
                # warn the user about the danger in group
                nc.draw_text(stdscr,
                             maxY//2,
                             maxX//2-(len("this server does not have a password")//2),
                             "this server does not have a password")
                nc.draw_text(stdscr,
                             maxY//2+1,
                             maxX//2-(len("proceed with caution")//2),
                             "proceed with caution")
                nc.wait_for_enter(stdscr)
                nc.clear_block(stdscr,
                               maxY//2, maxY//2+1,
                               0, 0)

            else:
                # succes, prompt for password
                nc.draw_text(stdscr,
                             maxY//2,
                             maxX//2-(len("password: ")//2),
                             "password: ")
                password = nc.get_input(stdscr,
                                        maxY//2+1,
                                        maxX//2-(len("password: ")//2),
                                        "")
                password = ae.generate_hash(password)
                send_server(clientSocket, password, serverKey)# 7

                time, status = recv_server(clientSocket, privateKey) # 8
                if status == "INCORRECT":
                    nc.draw_text(stdscr,
                                 maxY//2,
                                 maxX//2-(len("password is incorrect")),
                                 "password is incorrect")
                    continue

            break

        else:
            send_server(clientSocket, "create", serverKey) # 3

            recv_server(clientSocket, privateKey) # 4

            try:
                nc.draw_text(stdscr,
                             maxY//2-1,
                             maxX//2-(len("enter name of group:")//2),
                             "enter name of group:")

                group = nc.get_input(stdscr,
                                     maxY//2,
                                     maxX//2-(len("enter name of group:")//2-1),
                                     "")
            except KeyboardInterrupt:
                send_server(clientSocket, 0x01, serverKey) # 5
                recv_server(clientSocket, privateKey) # 6
                continue

            send_server(clientSocket, group, serverKey) # 5

            time, status = recv_server(clientSocket, privateKey) # 6
            if status == "BAD":
                nc.draw_text(stdscr, maxY//2-3,
                             maxX//2-(len("group already exists")//2),
                             "group already exists")
                continue

            if status == "TOO LONG":
                nc.draw_text(stdscr, maxY//2-3,
                             maxX//2-(len("group name is too long")//2),
                             "group name is too long")
                continue

            nc.clear_block(stdscr, maxY//2-1, maxY//2+1, 0, 0)

            password = nc.get_input(stdscr,
                                    maxY//2,
                                    maxX//2-(len("password:")//2),
                                    "password:")
            if password != "":
                password = ae.generate_hash(password)
            send_server(clientSocket, password, serverKey)# 7

            break



# listen for messages from the server
def recieve_messages(stdscr, client, privateKey):
    global messages
    while 1:
        # recieve a 4096 bit block of data and decrypt it
        time, message = recv_server(client, privateKey)

        if message == "SPAM":
            raise Exception("stop spamming nerd")
            quit()

        # print it to the screen
        messages.append(f"{datetime.now().strftime('%H:%M:%S')}  {message}")
        messages = nc.draw_message(stdscr, messages)
        stdscr.refresh()


# keep asking for and sending messages to server
def send_messages(stdscr, client, serverKey):
    global messages
    while 1:
        # get input and encrypt it using the servers public key
        message = nc.get_input(stdscr, maxY-1, 0, "message:")
        if bytes(message, 'utf-8') == b'':
            continue

        # send the message to the server
        send_server(client, message, serverKey)
        message = datetime.now().strftime('%H:%M:%S') + "  " + "you: " + message
        messages.append(message)
        messages = nc.draw_message(stdscr, messages)
        nc.clear_line(stdscr, maxY-1, 0, maxX-1)


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
    try:
        # screen initialization
        stdscr = c.initscr()
        c.noecho()
        maxY, maxX = stdscr.getmaxyx()

        # draw the background
        nc.draw_background(stdscr)

        nc.draw_text(stdscr,
                     maxY//2,
                     maxX//2-(len("generating keypairs...")//2),
                     "generating keypairs...")

        stdscr.refresh()

        # generate the asymmetrical keypair
        privateKey, publicKey = ae.generate_keys(4096)

        # start the client
        run_client(stdscr, privateKey, publicKey)

    finally:
        c.endwin()
