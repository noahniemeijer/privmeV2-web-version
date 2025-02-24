import curses as c
import ncurses_wrapper as nc
try:
    screen = c.initscr()
    c.noecho()

    maxY, maxX = screen.getmaxyx()

    nc.draw_background(screen)

    #screen.addstr(16, 88, "yoooo wsp gang")
    #nc.draw_text_overflow(screen, 18, 88, "yooooo wsp gang")
    #nc.draw_text(screen, 20, 86, "yooooo wsp gang")

    response = nc.get_input(screen,
                            maxY//2,
                            maxX//2-(len("what is the ip")//2),
                            "what is the ip?")
    nc.clear_line(screen,
                  maxY//2,
                  0,
                  0)

    screen.refresh()

    nc.draw_background(screen, response)
    messages = []

    while 1:

        message = nc.get_input(screen,
                               maxY-1,
                               0,
                               "message:")

        messages.append(message)

        messages = nc.draw_message(screen, messages)

        nc.clear_line(screen,
                      maxY-1,
                      0,
                      maxX-1)

    screen.getch()
finally:
    c.endwin()
