import logging
import time

import gevent, gevent.server
from telnetsrv.green import TelnetHandler
from telnetsrv import telnetsrvlib

import vidille
import av

import config


# global client count
num_clients = 0


"""
A simple video player to be shared across telnet clients.
"""
class Player( object ):
    

    def __init__( self, video_path ):
        # create an instance of av to extract frames from video
        self.container = av.open( video_path )
        self.current_frame = None
        self.playing = False

    
    def advance_frame( self ):
        """
        Advance av instance by one frame and store an image of that frame.
        """
        try:
            f = next( self.container.decode(video=0) )
            self.current_frame = f.to_image()
        except StopIteration:
            # loop container if we've hit the end
            self.container.seek( 0 )


    def run( self ):
        """
        Main frame extraction loop. Runs from a greenlet.
        """ 
        while True:
            if self.playing:
                self.advance_frame()
            gevent.sleep( config.FRAME_INTERVAL )
       

    def play( self ):

        logging.info( "Player.play()")
        
        if not self.playing:

            # rewind to start
            self.container.seek( 0 )

            # set playing flag. affects behaviour of self.run
            self.playing = True


    def stop( self ):
        
        logging.info( "Player.stop()")

        # set playing flag. affects behaviour of self.run
        self.playing = False


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


# global player instance
player = Player( config.MEDIA_FILE ) 


"""
Telnet connection handler. Represents one connected client.
"""
class MyTelnetHandler( TelnetHandler ):
    

    # overwite default prompt and message with nothing, be silent.
    PROMPT = ""
    WELCOME = ""


    """
    Runs when a client connects. 
    Start an update loop for this client or display a capacity-reached message.
    """
    def session_start( self ):

        global num_clients

         # we'll use these to keep track of render rate
        self.frames_rendered = 0
        self.time_connected = time.time()

        # increment global client counter
        num_clients += 1
        logging.info( "%d clients connected", num_clients )
        
        if num_clients > config.MAX_CLIENTS:

            # display capacity message if we're at capacity
            self.writeline(
                config.CAPACITY_MESSAGE
            )

            logging.info( "-> server at capacity, send CAPACITY_MESSAGE to client")

            # disconnect client
            self.finish()
        
        else: 
            ## start a new rendering session

            if not player.playing:
                player.play()

            # start update timer and render first frame
            self.on_delay()


    """
    Main update loop for client.
    Handle an update event (gevent) and spawn the next one.
    """
    def on_delay( self ):
        try:
            
            # render a frame to the client
            self.render()
            
            # store some stats
            self.frames_rendered += 1
            
            # run this function again in FRAME_INTERVAL's worth of time
            self.event = gevent.spawn_later(
                config.FRAME_INTERVAL,
                self.on_delay
            )
       
        except BrokenPipeError:
            # disconnect client if remote client has, in fact, disconnected
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
        
        if (self.frames_rendered is not None) and (self.frames_rendered > 0):
            # calculate and output some stats
            now = time.time()
            connected_time = now - self.time_connected
            logging.info(
                "-> rendered {:d} frames in {:2.2f} seconds (avg {:2.2f} fps)".format(
                    self.frames_rendered,
                    connected_time,
                    self.frames_rendered / connected_time
                )
            )
        
        # decrement global client counter
        num_clients -= 1
        logging.info( "%d clients currently connected", num_clients )

        # stop the global player instance if we're the last connected client
        if num_clients <=0:
            player.stop()


# log to console
logging.basicConfig(
    level= config.LOG_LEVEL,
    handlers = [logging.StreamHandler()]
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