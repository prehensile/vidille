import logging

import gevent, gevent.server
from telnetsrv.green import TelnetHandler
from telnetsrv import telnetsrvlib

import vidille
import av

import config


"""
A simple video player to be shared across telnet clients.
"""
class Player( object ):
    

    def __init__( self, video_path ):
        # create an instance of av to extract frames from video
        self.container = av.open( video_path )
        self.current_frame = None

    
    def advance_frame( self ):
        """
        Advance av instance by one frame and store an image of that frame.
        """
        f = next(self.container.decode(video=0))
        self.current_frame = f.to_image()


    def run( self ):
        """
        Main frame extraction loop. Runs as a greenlet.
        """
        while True:
            self.advance_frame()
            gevent.sleep( config.FRAME_INTERVAL )


    def render_screen( self, terminal_width=80, terminal_height=25 ):
        """
        Render and return the current frame image as a drawille screen.
        """
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


# global vars
num_clients = 0
player = Player( config.MEDIA_FILE ) 


"""
Telnet connection handler. Represents one connected client.
"""
class MyTelnetHandler(TelnetHandler):
    

    # overwite default prompt and message with nothing, be silent.
    PROMPT = ""
    WELCOME = ""


    """
    Runs when a client connects. 
    Start an update loop for this client or display a capacity-reached message.
    """
    def session_start( self ):

        global num_clients

        if num_clients >= config.MAX_CLIENTS:
            self.writeline(
                config.CAPACITY_MESSAGE
            )
            self.finish()
        else: 
            self.on_delay()
        
        # increment global client counter
        num_clients += 1


    """
    Main update loop for client.
    Handle an update event (gevent) and spawn the next one.
    """
    def on_delay( self ):
        try:
            self.render()
            self.event = gevent.spawn_later(
                config.FRAME_INTERVAL,
                self.on_delay
            )
        except Exception as e:
            logging.exception( e )
            self.finish()
    

    """
    Render a frame to the client. 
    Pull current frame image from global Player instance and render with drawille.
    """
    def render( self ):

        global player

        # request a drawille-rendered frame from the global player
        screen = player.render_screen(
            self.WIDTH, # terminal width, in columns
            self.HEIGHT # terminal height, in rows
        )
      
        # escape sequence: clear screen
        self.write( "\033[2J" )
        # escape sequence: move cursor to top left
        self.write( "\033[H" )

        # send frame to client
        self.write( screen, encoding='utf-8' )
    

    """
    Runs when client disconnects.
    """
    def session_end( self ):
        global num_clients
        logging.info( "Disconnected" )
        # decerement global client counter
        num_clients -= 1
        logging.info( "%d clients currently connected", num_clients )


# log to console
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler()]
)

# set up a server instance
server = gevent.server.StreamServer(("", config.SERVER_PORT), MyTelnetHandler.streamserver_handle)

# spawn a greenlet to run the global video update
greenlet = gevent.spawn( player.run )
greenlet.start()

# start the telnet server
try:
    server.serve_forever()
except KeyboardInterrupt:
    logging.info("Server shut down.")