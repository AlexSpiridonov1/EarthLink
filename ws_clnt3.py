#!/usr/bin/python
import websocket
import _thread
import time
import serial
import sys
import re  # for regular expressions
import binascii  # for crc16 check
from random import randint,uniform
from time import strftime
from queue import Queue
import inspect  # for lineno function
from tcpping import tcpping  # pip install tcpping

# DBG = 2 # enable websocket trace
DBG = 1
# webserver ip and portnumber

websrv = "10.2.1.11"
webport = "8080"

# the serial line speed in bps
speed = 115200

if not tcpping(host = websrv, port = webport, timeout = 1):
    print("ERROR: Webserver {}, port {} is unreachable - exit ...".format(websrv,webport))
    sys.exit(1)

url_msg = "ws://"+websrv+":8080/sendData"
url_msgb = "ws://"+websrv+":8080/sendPictures"

output_file = 'out_file1.bin'

import logging
logger = logging.getLogger('websockets-client')
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


# enable websocket module trace
if DBG>1: websocket.enableTrace(True)

#defining queues for Data and Text
qText = Queue(maxsize=0)
qData = Queue(maxsize=0)

#-----------------------------------------------
### functions
# print the current program line number
def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

def logit(message, pr):
    if (pr): print(message, flush=True)
    #with open (LFILE, mode='a') as logfile:
        #logfile.write(message+'\n')

# received message from Websocket server == received text data
def _on_message(wsock, message):
    logger.debug("DEBUG[%d](%s): RECV MSG: '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), message)

def _on_error(wsock, error):
    logger.debug("DEBUG[%d](%s): ERROR: '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), error)

def _on_close(wsock):
    logger.debug("DEBUG[%d](%s): CLOSE Websocket", lineno(), strftime("%Y%m%d_%H%M%S"))

#-----------------------------------------------

output = bytearray ()
# received data from websocket server

def _on_data (wsock, message, message_type, is_last):
    global output

    if (message_type == websocket.ABNF.OPCODE_TEXT):
        logger.debug("DEBUG[%d](%s): RECV TXT DATA: Received text data: '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), message)

    # For some reason, we receive the data as type websocket.ABNF.OPCODE_CONT.
    elif (message_type == websocket.ABNF.OPCODE_BINARY or message_type == websocket.ABNF.OPCODE_CONT):
        logger.debug("DEBUG[%d](%s): RECV BIN DATA: Received binary data; is_last: %d", lineno(), strftime("%Y%m%d_%H%M%S"), is_last)
        output = output + message
        if (is_last == True):
            # w = write. b = binary.
            with open (output_file, mode='wb') as file:
                file.write (output)
                logger.debug("DEBUG[%d](%s): SAVE DATA: Wrote data to output file %s", lineno(), strftime("%Y%m%d_%H%M%S"),output_file)
            wsock.close ()
    else:
        logger.debug("DEBUG[%d](%s): RECV DATA: Received data of type %d", lineno(), strftime("%Y%m%d_%H%M%S"), message_type)


# function started after esteblishing the websocket connection
def _on_open(wsock):
    logger.debug("DEBUG[%d](%s): CONNECTED Websocket; START thread", lineno(), strftime("%Y%m%d_%H%M%S"))

    # function to send messages over the websocket connection
    def send_msg(*args):
        while True: 
            # create a message in format expected from server

            while not qText.empty():
                msgText = qText.get()
                qText.task_done()
                logger.debug("DEBUG[%d](%s): RECEIVED MESSAGE from queue 'qText': %s", lineno(), strftime("%Y%m%d_%H%M%S"), msgText)

                logger.debug("DEBUG[%d](%s): SENDING MESSAGE to the websocket server", lineno(), strftime("%Y%m%d_%H%M%S"))
                wsock.send(msgText)
                logger.debug("DEBUG[%d](%s): MESSAGE TRANSMITED", lineno(), strftime("%Y%m%d_%H%M%S"))
            time.sleep(1) 

        time.sleep(1)
        wsock.close()
        logger.debug("DEBUG[%d](%s): TERMINATE thread 'send_msg'", lineno(), strftime("%Y%m%d_%H%M%S"))

    logger.debug("DEBUG[%d](%s): STARTING thread 'send_msg'", lineno(), strftime("%Y%m%d_%H%M%S"))
    _thread.start_new_thread(send_msg, ())
    logger.debug("DEBUG[%d](%s): START: Thread 'send_msg' started", lineno(), strftime("%Y%m%d_%H%M%S"))

#------------------------------------------------------------------#

# function to send binary data (files) over the websocket connection
def _on_openb(wsock):
    logger.debug("DEBUG[%d](%s): CONNECTED Websocket", lineno(), strftime("%Y%m%d_%H%M%S"))

    def send_bindata(*args):
        while True:
            r=randint(10,120)  # random sleep time between the messages

            # r = read. b = binary.
            with open (input_file, mode='rb') as file:
                data = file.read()

            logger.debug("DEBUG[%d](%s): SEND BIN DATA: Sending binary data from %s", lineno(), strftime("%Y%m%d_%H%M%S"),input_file)
            #wsock.send (data, websocket.ABNF.OPCODE_BINARY)
            break
 
        time.sleep(1)
        wsock.close()
        logger.debug("DEBUG[%d](%s): TERMINATE thread 'send_bindata'", lineno(), strftime("%Y%m%d_%H%M%S"))

    logger.debug("DEBUG[%d](%s): STARTING thread 'send_bindata'", lineno(), strftime("%Y%m%d_%H%M%S"))
    _thread.start_new_thread(send_bindata, ())
    logger.debug("DEBUG[%d](%s): START: Thread 'send_bindata' started", lineno(), strftime("%Y%m%d_%H%M%S"))

######################################################################
### main program

if __name__ == "__main__":

    # --------------------------------------------------
    # function for thread 'sendData'
    def sendData():
        ws = websocket.WebSocketApp(url_msg,
                                on_open = _on_open,
                                on_message = _on_message,
                                on_error = _on_error,
                                on_close = _on_close)
        logger.debug("DEBUG[%d](%s)]: SETUP the websocket for URL '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), url_msg)
        #ws.on_open = _on_open
        logger.debug("DEBUG[%d](%s): CONNECT to '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), url_msg)
        ws.run_forever()
        logger.debug("DEBUG[%d](%s): STARTED Task for websocket '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), url_msg)

    # start the function sendData as a thread
    _thread.start_new_thread(sendData, ())

    # --------------------------------------------------
    # function for thread 'sendPictures'
    # this feature is switched off now
    if 0:
        def sendPictures():
            wsb = websocket.WebSocketApp(url_msgb,
                                on_open = _on_openb, 
                                on_message = _on_message,
                                on_error = _on_error,
                                on_close = _on_close)

            logger.debug("DEBUG[%d](%s)]: SETUP the websocket for URL '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), url_msgb)  
            #ws.on_open = _on_open
		
            logger.debug("DEBUG[%d](%s): CONNECT to '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), url_msgb)
            wsb.run_forever()
            logger.debug("DEBUG[%d](%s): STARTED Task for websocket '%s'", lineno(), strftime("%Y%m%d_%H%M%S"), url_msgb)
    
        # start the function sendPictures() as a thread
        _thread.start_new_thread(sendPictures, ())

    # --------------------------------------------------
	
    logger.debug("DEBUG[%d](%s): initialize the serial connection to Arduino", lineno(), strftime("%Y%m%d_%H%M%S"))
    s = serial.Serial('/dev/ttyACM0', speed)
   
    # close the serial connection if it is allready open
    if s.isOpen():
        logger.debug("DEBUG[%d](%s): Serial port allready open - close it ...", lineno(), strftime("%Y%m%d_%H%M%S"))
        s.close()

    # open the serial connection
    logger.debug("DEBUG[%d](%s): open the Serial port ...", lineno(), strftime("%Y%m%d_%H%M%S"))
    s.open()
    # wait to open the connection

    while not s.isOpen():
        pass
    print("Serial Connection open")
    time.sleep(1)

    # loop to read a message from Arduino
    # EVERY message from Arduino must start with <m> and end with "</m>"
    while True:

        msg = b""    

        # loop until end marker "</m>" comes
        while not msg.endswith((b"</m>", b"</m>\r\n")):
            in_bytes=s.in_waiting
            if in_bytes > 0:
                # read in_bytes from Arduino
                msg += s.read(in_bytes)

        msg = msg.rstrip()  # delete newline at end
        logger.debug("DEBUG[%d](%s): RECEIVED from Arduino: %s", lineno(), strftime("%Y%m%d_%H%M%S"),msg)
    
        # check if the message start <m> was received
        #if not msg.startswith(b"<m>"):
        if not b"<m>" in msg:
            print("WARNING[%d]: message received: %s" % (lineno(), msg))
            msg = b''
            continue

        # get a list of messages, if more than one message was received
        # !!! - we need the "re.S = DOTALL" flag in "re" because "\r\n" in the string
        msg_list = re.findall(rb'(<m>.*?</m>)', msg, re.S)

        # process every message in the list
        for msg in msg_list:

            # the received message is a "data" type
            # the data MSG format:
            # '<m><d>T:-45.19,P:351.35,D:17563.98,LA:45.95,LO:10.32,V:28.52TI:13;20;26;531,H:0.04</d><CRC:8633></m>'
            if msg.startswith(b'<m><d>'):

                # get the data in the message
                try:
                    dataArd = re.match(rb'<m><d>(.*?)</d>', msg, re.S).group(1)
                except:
                    print("ERROR[%d]: no data found between <d> and </d> in the message" % lineno() )
                    continue

                # get the CRC sum included in the message
                try:
                    # get the sended CRC
                    crc_send = int( (re.search(rb'<CRC:(\d+)>', msg[-50:])).group(1) )
                except:
                    print("ERROR[%d]: CRC: no CRC found in the received data message" % lineno() )
                    continue

                # calculate the CRC of received data
                crc_recv = binascii.crc_hqx(dataArd,0)

                # compare the CRC of the sended data and the CRC of the received data
                if crc_recv != crc_send:
                    err = "ERROR[%d](%s): CRC in Arduino: %d <> CRC in Raspi: %d" % (lineno(), strftime("%Y%m%d_%H%M%S"), crc_send, crc_recv)
                    logit(err,1)
                elif (DBG):
                    inf = "DBG[%d](%s): CRC OK: Arduino: HEX: 0x%02X, DEC: %d; RasPI: %d" % (lineno(), strftime("%Y%m%d_%H%M%S"), crc_send,crc_send, crc_recv)
                    logit(inf,1)
		    	
                # check again, if this is a data message and put it in the queue qText
                if len(dataArd)<150 and dataArd.startswith(b"T"):
                    logger.debug("DEBUG[%d](%s): insert the message data in the queue qText", lineno(), strftime("%Y%m%d_%H%M%S"))
                    qText.put(dataArd)
                else: 
                    # qData.put(picFilename) # put the picture file name in the queue qData
                    logger.debug("DEBUG[%d](%s): the mesage data are ignored", lineno(), strftime("%Y%m%d_%H%M%S"))

        # unknown message type: print the received message(s)
        else:
            if (DBG): print("DBG[%d]: MSG: %s" % (lineno(),msg))
            for msg_txt in re.findall(rb'<m>(.*?)</m>', msg, re.S):
                inf = "INFO[%d](%s): RECV MSG: %s" % (lineno(), strftime("%Y%m%d_%H%M%S"), msg_txt.decode() )
                logit(inf, 1)


    print("Bye, Bye ...")
    s.close()


