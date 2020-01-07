import logging
import curses, _curses
import gevent, gevent.server
from telnetsrv.green import TelnetHandler, command
from telnetsrv import telnetsrvlib
import vidille
import av


class Player( object ):
    
    def __init__( self, video_path ):
        self.container = av.open( video_path )
        self.current_frame = None

    
    def advance_frame( self ):
        f = next(self.container.decode(video=0))
        self.current_frame = f.to_image()


    def run( self ):
        while True:
            self.advance_frame()
            gevent.sleep( 1.0 / 18.0 )

    def render_screen( self, terminal_width=80, terminal_height=25 ):
        screen = None
        if self.current_frame:
            return vidille.image2term(
                self.current_frame.convert("L"),
                canvas_width = terminal_width * 2,
                canvas_height = terminal_height * 4,
                dither = False,
                invert = True
            )
        return screen


num_clients = 0
player = Player( "media/rick.mp4" ) 


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
            self.on_delay()


    def on_delay( self ):
        try:
            self.update()
            self.event = gevent.spawn_later(
                1.0 / 18.0,
                self.on_delay
            )
        except Exception as e:
            logging.exception( e )
            self.finish()
    

    def update( self ):

        global player

        #player.advance_frame()
        screen = player.render_screen(
            self.WIDTH,
            self.HEIGHT
        )
      
        # escape sequence: clear screen
        self.write( "\033[2J" )
        # escape sequence: move cursor to top left
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

greenlet = gevent.spawn( player.run )
greenlet.start()

try:
    server.serve_forever()
except KeyboardInterrupt:
    logging.info("Server shut down.")