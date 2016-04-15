import sys

from Board import Color
from Board import Board
from Board import color_names

def color_from_str(s):
    if 'w' in s or 'W' in s: return Color.White
    else: return Color.Black

def coords_from_str(s):
    x = ord(s[0].upper()) - ord('A')
    if x >= 9: x -= 1
    y = int(s[1:])
    y -= 1
    return x,y

def str_from_coords(x, y):
    if x >= 8: x += 1
    return chr(ord('A')+x) + str(y+1)

class Move:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def is_pass(self):
        return self.x == self.y == -1
    def is_resign(self):
        return self.x == self.y == -2
    def is_play(self):
        return not self.is_pass() and not self.is_resign()
Move.Pass = Move(-1, -1)
Move.Resign = Move(-2, -2)

class GTP:
    def __init__(self, engine, fclient):
        self.engine = engine
        self.fclient = fclient

    def tell_client(self, s):
        self.fclient.write('= ' + s + '\n\n')
        self.fclient.flush()
        print "GTP: Told client: " + s


    def error_client(self, s):
        self.fclient.write('? ' + s + '\n\n')
        self.fclient.flush()
        print "GTP: Sent error message to client: " + s
    
    def list_commands(self):
        commands = ["protocol_version", "name", "version", "boardsize", "clear_board", "komi", "play", "genmove", "undo", 
                    "list_commands", "quit", "gogui-analyze_commands", "kgs-game_over", "time_left" , "kgs-genmove_cleanup"]
        if self.engine.supports_final_status_list():
            commands.append("final_status_list")
        self.tell_client("\n".join(commands))

    def quit(self):
        print "GTP: Quitting"
        self.engine.quit()
        self.tell_client("")
        sys.stdout.close() # Close log file
        exit(0)

    def set_board_size(self, line):
        board_size = int(line.split()[1])
        print "GTP: setting board size to", board_size
        if self.engine.set_board_size(board_size):
            self.tell_client("")
        else:
            self.error_client("Unsupported board size")

    def clear_board(self):
        print "GTP: clearing board"
        self.engine.clear_board()
        self.tell_client("")

    def set_komi(self, line):
        komi = float(line.split()[1])
        print "GTP: setting komi to", komi
        self.engine.set_komi(komi)
        self.tell_client("")

    def stone_played(self, line):
        parts = line.split()
        color = color_from_str(parts[1])
        if "pass" in parts[2].lower():
            print "GTP: %s passed" % color_names[color]
            self.engine.player_passed(color)
        else:
            x,y = coords_from_str(parts[2])
            print "GTP: %s played at (%d,%d)" % (color_names[color], x, y)
            self.engine.stone_played(x, y, color)
        self.tell_client("")

    def generate_move(self, line, cleanup=False):
        color = color_from_str(line.split()[1])
        print "GTP: asked to generate a move for", color_names[color]
        move = self.engine.generate_move(color, cleanup)
        if move.is_play():
            print "GTP: engine generated move (%d,%d)" % (move.x,move.y)
            self.tell_client(str_from_coords(move.x, move.y))
        elif move.is_pass():
            print "GTP: engine passed"
            self.tell_client("pass")
        elif move.is_resign():
            print "GTP: engine resigned"
            self.tell_client("resign")
        else:
            assert False

    def kgs_genmove_cleanup(self, line):
        self.generate_move(line, cleanup=True)

    def undo(self):
        print "GTP: got undo"
        self.engine.undo()
        self.tell_client("")

    def gogui_analyze_commands(self):
        print "GTP: got gogui-analyze_commands"
        analyze_commands = ["string/Hello World/hello_world",
                            "dboard/Show Influence Map/show_influence_map"]
        self.tell_client("\n".join(analyze_commands))

    def hello_world(self):
        print "GTP: got hello_world"
        self.tell_client("hello world!")

    def show_influence_map(self):
        print "GTP: got show_influence_map"
        #self.tell_client(("-1.0 "*19 + "\n")*19)
        influence_map = self.engine.make_influence_map()
        str_map = [[str(influence_map[x,y]) for x in xrange(influence_map.shape[0])] for y in xrange(influence_map.shape[1]-1, -1, -1)]
        big_str = "\n".join(" ".join(val for val in row) for row in str_map)
        self.tell_client(big_str)

    def game_over(self):
        #exit(0)
        self.tell_client("")

    def send_final_status_list(self, line):
        status = line.split()[-1]
        self.tell_client(self.engine.final_status_list(status))

    def time_left(self, line):
        print "GTP: got time_left"
        self.tell_client("")

    def loop(self):
        while True:
            line = sys.stdin.readline().strip()
            if len(line) == 0: return
            line = line.strip()
            print "GTP: client sent: " + line
    
            if line.startswith("protocol_version"): # GTP protocol version
                self.tell_client("2")
            elif line.startswith("name"): # Engine name
                self.tell_client(self.engine.name())
            elif line.startswith("version"): # Engine version
                self.tell_client(self.engine.version())
            elif line.startswith("list_commands"): # List supported commands
                self.list_commands()
            elif line.startswith("quit"): # Quit
                self.quit()
            elif line.startswith("boardsize"): # Board size
                self.set_board_size(line)
            elif line.startswith("clear_board"): # Clear board
                self.clear_board()
            elif line.startswith("komi"): # Set komi
                self.set_komi(line)
            elif line.startswith("play"): # A stone has been placed
                self.stone_played(line)
            elif line.startswith("genmove"): # We must generate a move
                self.generate_move(line)
            elif line.startswith("undo"): # Undo the previous move
                self.undo()
            elif line.startswith("gogui-analyze_commands"): # List supported GoGui analyze commands
                self.gogui_analyze_commands()
            elif line.startswith("hello_world"): # hello world
                self.hello_world()
            elif line.startswith("show_influence_map"):
                self.show_influence_map()
            elif line.startswith("kgs-game_over"):
                self.game_over()
            elif line.startswith("final_status_list"):
                self.send_final_status_list(line)
            elif line.startswith("time_left"):
                self.time_left(line)
            elif line.startswith("kgs-genmove_cleanup"):
                self.kgs_genmove_cleanup(line)
            else:
                self.error_client("Don't recognize that command")


