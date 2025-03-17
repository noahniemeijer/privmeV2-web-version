from curses import *

def draw_background(stdscr, connectedIP=None):
    maxY, maxX = stdscr.getmaxyx()
    draw_top_bar(stdscr, maxX, connectedIP)
    draw_lines(stdscr, maxY)


def draw_lines(stdscr, maxY):
    draw_line(stdscr, 2, 0, 0)
    draw_line(stdscr, maxY-2, 0, 0)


def draw_top_bar(stdscr, maxX, connectedIP):
    neededLength = len("connected to 255.255.255 " +
                       "privme tui v2 ")

    if maxX >= neededLength:
        if connectedIP:
            draw_text(stdscr,
                      0,
                      0,
                      f"CONNECTED TO {connectedIP}")

        else:
            draw_text(stdscr,
                      0,
                      0,
                      "NOT CONNECTED")

        draw_text(stdscr,
                  0,
                  maxX-(len("privme tui v2")),
                  "PRIVME TUI V2")

    else:
        draw_text(stdscr,
                  0,
                  maxX//2-(len("privme tui v2")//2),
                  "PRIVME TUI V2")


def draw_message(stdscr, messages):
    maxY, maxX = stdscr.getmaxyx()
    if len(messages) > (maxY-5):
        messages = messages[1:]
    for i in range(len(messages)):
        clear_line(stdscr,
                   3+i,
                   0,
                   0)
        draw_text_overflow(stdscr,
                           3+i,
                           0,
                           messages[i])

    return messages


def draw_line(stdscr, y, startX, stopX):
    maxY, maxX = stdscr.getmaxyx()
    if stopX == 0 or stopX > maxX:
        stopX = maxX

    for i in range(stopX - startX):
        stdscr.addstr(y, startX+i, "_")


def clear_line(stdscr, y, startX, stopX):
    maxY, maxX = stdscr.getmaxyx()
    if stopX == 0 or stopX > maxX:
        stopX = maxX

    for i in range(stopX - startX):
        stdscr.addstr(y, startX+i, " ")


def clear_block(stdscr, startY, stopY, startX, stopX):
    maxY, maxX = stdscr.getmaxyx()
    if stopY == 0 or stopY > maxY:
        stopY = maxY

    for i in range(startY, stopY+1):
        clear_line(stdscr, i, startX, stopX)


def get_input(stdscr, y, x, prompt):
    maxY, maxX = stdscr.getmaxyx()
    stdscr.addstr(y, x, prompt)

    response = ""

    xOffset = len(prompt)+1
    yOffset = 0

    while 1:
        ch = stdscr.getch()
        if ch == 10:
            break

        if ch == 127:
            response = response[:-1]
            if xOffset > len(prompt)+1: xOffset -= 1
            stdscr.addstr(y+yOffset, x+xOffset, " ")
            stdscr.move(y+yOffset, x+xOffset)
            continue

        response += chr(ch)
        stdscr.addstr(y+yOffset, x+xOffset, chr(ch))

        xOffset += 1
        if xOffset == maxX:
            xOffset = len(prompt)+1
            yOffset += 1

    return response


def wait_for_enter(stdscr):
    while 1:
        ch = stdscr.getch()
        if ch == 10:
            break
    return


def draw_text(stdscr, y, x, text):
    maxY, maxX = stdscr.getmaxyx()
    if maxX-x-3 <= 0:
        raise ValueError
    if x + len(text) > maxX:
        text = text[:maxX-x-3]+"..."
    stdscr.addstr(y, x, text)


def draw_text_overflow(stdscr, y, x, text):
    maxY, maxX = stdscr.getmaxyx()
    if maxX-x <= 0:
        raise ValueError
    if x + len(text) >= maxX:
        text1 = text[:maxX-x]
        text2 = text[maxX-x:]
        stdscr.addstr(y, x, text1)
        stdscr.addstr(y+1, x, text2)
    else:
        stdscr.addstr(y, x, text)

