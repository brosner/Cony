#!/usr/bin/env python

"""
Cony.py

A python command line daemon for exposing internal RabbitMQ data via a simple JSON HTTP service.
"""

import json
import logging
import optparse
import os
import sys
import time
import uuid
import yaml

from py_interface import erl_node, erl_eventhandler
from py_interface.erl_opts import ErlNodeOpts
from py_interface.erl_term import ErlAtom, ErlBinary, ErlRef, ErlString, ErlTuple

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn

version = '0.1'

config = {}
lastStats = False
mbox = False
process_stack = {}

class HTTPHandler(BaseHTTPRequestHandler):

    """
    Internal HTTP Server Handler Class
    
    Sends out JSON stats data
    """

    def send_data(self, response, mimetype):
        global version
        
        logging.debug('Sending response to request for: %s' % self.path)
        self.send_response(200)
        self.send_header('X-Server', 'Cony/%s' % version)
        self.send_header('Content-type', mimetype)
        self.send_header('Content-length', len(response))
        self.end_headers()
        self.wfile.write(response)                
    
    def do_GET(self):
        global config, mbox

        path = self.path.split('?')
        logging.debug('Received request for %s' % self.path)

        # Initial request for the stats ui
        if path[0] == '/':
            if os.path.isdir('assets'):
                if os.path.isfile('assets/index.html'):
                    f = open('assets/index.html', 'r')
                    response = f.read()
                    f.close()              
                    self.send_data(response, 'text/html')      
                else:
                    self.send_response(404)
            else:
                self.send_response(404)
            return
        
        if path[0].find('assets/') > 0:
            if os.path.isdir('assets'):
                if os.path.isfile(path[0][1:]):
                  
                    # Read in the file
                    f = open(path[0][1:], 'r')
                    response = f.read()
                    f.close()
    
                    # Get the mime type                
                    mime = mimetypes.guess_type(path[0][1:])
                   
                    # Send the response
                    self.send_data(response, mime[0])
                else:
                    self.send_response(404)
            else:
                self.send_response(404)
            return                            

        # 3rd party stub for json data
        elif path[0] == '/stats':
        
          # All Stats
          if len(path) == 1:
            
            stats = {}
            stats['list_queues'] = self.list_queues()

          # Individual Stats
          else:
          
            # List Queues
            if path[1] == '/list_queues':
              stats = self.list_queues()
            
          self.send_data(json.dumps(stats), 'application/json')
            
        # The running processes configuration
        elif path[0] == '/config':
            global config

            response = "jsonp_config(%s);\n" % json.dumps(config)
            self.send_data(response, 'text/javascript')
            return       

        # Unrecognized request
        else:
            self.send_error(404, 'File not found: %s' % self.path)            
        
    def list_queues(self):

        # Define the process id and enter an item in our stack
        process_id = uuid.uuid4()
        process_stack[process_id] = 'running'
        
        # Define our lambda function to listen for our return message
        __msg_handler = lambda msg: msg_list_queues(process_id, msg)
        
        # Send the request for the queue data
        mbox.SendRPC(
            ErlAtom(config['RabbitMQ']['RabbitNode']),
            ErlAtom('rabbit_amqqueue'),
            ErlAtom('info_all'),
            [ ErlBinary(config['RabbitMQ']['VHost']) ],
            __msg_handler
        )
        erl_eventhandler.GetEventHandler().Loop()
    
        #Wait for the process to finish
        while process_stack[process_id] == 'running':
            time.sleep(1)
      
        # Get our stats and remove the dictionary variable
        stats = process_stack[process_id]
        del process_stack[process_id]
    
        # Return to our request handler            
        return stats



class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    
def msg_list_queues(pid, msg):

    """ Handler that receives the queue messages """
    
    global process_stack

    logging.debug('__msg_list_queues called for process id "%s"' % pid)

    status = {}
    for entry in msg:

      # Get the queue name
      queueName = entry[0][1][3].contents

      # Build the stats for this queue     
      status[queueName] = {}
      status[queueName]['durable'] = str(entry[1][1])
      status[queueName]['auto-delete'] = str(entry[2][1])
      status[queueName]['arguments'] = entry[3][1]
      status[queueName]['node'] = str(entry[4][1].node)
      status[queueName]['messages_ready'] = entry[5][1]
      status[queueName]['messages_unacknowledged'] = entry[6][1]
      status[queueName]['messages_uncommitted'] = entry[7][1]
      status[queueName]['messages'] = entry[8][1]
      status[queueName]['acks_uncommitted'] = entry[9][1]
      status[queueName]['consumers'] = entry[10][1]
      status[queueName]['transactions'] = entry[11][1]
      status[queueName]['memory'] = entry[12][1]
      
    process_stack[pid] = status      
    erl_eventhandler.GetEventHandler().StopLooping()       

def main():
  global config, mbox, node
  
  usage = "usage: %prog [options]"
  version_string = "%%prog %s" % version
  description = "cony.py consumer daemon"
  
  # Create our parser and setup our command line options
  parser = optparse.OptionParser(usage=usage,
                                 version=version_string,
                                 description=description)

  parser.add_option("-c", "--config", 
                    action="store", type="string", default="cony.yaml", 
                    help="Specify the configuration file to load.")

  parser.add_option("-f", "--foreground",
                    action="store_true", dest="foreground", default=False,
                    help="Do not fork and stay in foreground")                                                                 

  parser.add_option("-v", "--verbose",
                    action="store_true", dest="verbose", default=False,
                    help="use debug to stdout instead of logging settings")
  
  # Parse our options and arguments                                    
  options, args = parser.parse_args()
   
  # Load the Configuration file
  try:
      stream = file(options.config, 'r')
      config = yaml.load(stream)
  except:
      print "\nError: Invalid or missing configuration file \"%s\"\n" % options.config
      sys.exit(1)
  
  # Set logging levels dictionary
  logging_levels = { 
                    'debug':    logging.DEBUG,
                    'info':     logging.INFO,
                    'warning':  logging.WARNING,
                    'error':    logging.ERROR,
                    'critical': logging.CRITICAL
                   }
  
  # Get the logging value from the dictionary
  logging_level = config['Logging']['level']
  config['Logging']['level'] = logging_levels.get( config['Logging']['level'], 
                                                   logging.NOTSET )

  # If the user says verbose overwrite the settings.
  if options.verbose is True:
  
    # Set the debugging level to verbose
    config['Logging']['level'] = logging.DEBUG
    
    # If we have specified a file, remove it so logging info goes to stdout
    if config['Logging'].has_key('filename'):
      del config['Logging']['filename']

  else:

    # Build a specific path to our log file
    if config['Logging'].has_key('filename'):
      config['Logging']['filename'] = "%s/%s/%s" % ( 
        config['Locations']['base'], 
        config['Locations']['logs'], 
        config['Logging']['filename'] )
    
  # Pass in our logging config 
  logging.basicConfig(**config['Logging'])
  logging.info('Log level set to %s' % logging_level)

  # Fork our process to detach if not told to stay in foreground
  if options.foreground is False:
    try:
      pid = os.fork()
      if pid > 0:
        logging.info('Parent process ending.')
        sys.exit(0)            
    except OSError, e:
      sys.stderr.write("Could not fork: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)
    
    # Second fork to put into daemon mode
    try: 
      pid = os.fork() 
      if pid > 0:
        # exit from second parent, print eventual PID before
        print 'cony.py daemon has started - PID # %d.' % pid
        logging.info('Child forked as PID # %d' % pid)
        sys.exit(0) 
    except OSError, e: 
      sys.stderr.write("Could not fork: %d (%s)\n" % (e.errno, e.strerror))
      sys.exit(1)
    
    # Let the debugging person know we've forked
    logging.debug('After child fork')
    
    # Detach from parent environment
    os.chdir(config['Locations']['base']) 
    os.setsid()
    os.umask(0) 

    # Close stdin    	
    sys.stdin.close()
    
    # Redirect stdout, stderr
    sys.stdout = open('%s/%s/stdout.log' % ( config['Locations']['base'], 
                                             config['Locations']['logs']), 'w')
    sys.stderr = open('%s/%s/stderr.log' % ( config['Locations']['base'], 
                                             config['Locations']['logs']), 'w')    

  logging.debug('Connecting our local erlang node')
  node = erl_node.ErlNode("%s-%d" % ( config['RabbitMQ']['LocalNode'], os.getpid() ),
                          ErlNodeOpts(cookie=config['RabbitMQ']['Cookie']) )

  logging.debug('Creating local MBox')
  mbox = node.CreateMBox(None)
  mboxName = "%s-%d" % ( config['RabbitMQ']['LocalNode'], os.getpid() )
  mbox.RegisterName(mboxName)

  logging.info('Connected as an erlang node')
  
  logging.info('Starting HTTP Server')
  server = ThreadedHTTPServer((config['HTTPServer']['listen'],config['HTTPServer']['port']), HTTPHandler)
  server.serve_forever()

 # Only execute the code if invoked as an application
if __name__ == '__main__':
  main()