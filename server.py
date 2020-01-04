import logging
import curses, _curses
import gevent, gevent.server
from telnetsrv.green import TelnetHandler, command
from telnetsrv import telnetsrvlib
import vidille
import av


class Player( object ):
    
    def __init__( self, video_path, terminal_width=80, terminal_height=25 ):
        self.container = av.open( video_path )
        self.canvas_width = terminal_width *2
        self.canvas_height = terminal_height *4
    
    def next_frame( self ):
        frame = next(self.container.decode(video=0))
        i = frame.to_image()
        return vidille.image2term(
            i.convert("L"),
            canvas_width = self.canvas_width,
            canvas_height = self.canvas_height,
            dither = False,
            invert = True
        )


num_clients = 0

class MyTelnetHandler(TelnetHandler):
    
    PROMPT = ""
    WELCOME = ""

    def session_start( self ):

        global num_clients
        num_clients += 1

        if num_clients >= 4:
            self.writeline(
                "Maximum number of connections reached. Please try later!"
            )
            self.finish()
        else:
            self.player = Player(
                "media/rick.mp4",
                terminal_width=self.WIDTH,
                terminal_height=self.HEIGHT
            ) 
            self.on_delay()

    def on_delay( self ):
        try:
            self.update()
            self.event = gevent.spawn_later(
                1.0 / 25.0,
                self.on_delay
            )
        except Exception as e:
            logging.exception( e )
            self.finish()
    
    def update( self ):
        screen = self.player.next_frame()
        # screen = screen.replace( "\n", "\r\n" )

        # clear screen
        self.write( "\033[2J" )
        # move cursor to top left
        self.write( "\033[H" )

        self.write( screen, encoding='utf-8' )
    
    def session_end( self ):
        global num_clients
        logging.info( "Disconnected" )
        num_clients -= 1
        logging.info( "%d clients currently connected", num_clients )


logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()]
)

server = gevent.server.StreamServer(("", 2020), MyTelnetHandler.streamserver_handle)

try:
    server.serve_forever()
except KeyboardInterrupt:
    logging.info("Server shut down.")