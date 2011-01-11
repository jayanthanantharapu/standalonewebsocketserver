##Copyright (c) 2010 Colin Zablocki
##
##Permission is hereby granted, free of charge, to any person obtaining a copy
##of this software and associated documentation files (the "Software"), to deal
##in the Software without restriction, including without limitation the rights
##to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##copies of the Software, and to permit persons to whom the Software is
##furnished to do so, subject to the following conditions:
##
##The above copyright notice and this permission notice shall be included in
##all copies or substantial portions of the Software.
##
##THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
##THE SOFTWARE.

import socket
import logging as log
import hashlib
import struct

STARTBYTE = '\x00'
ENDBYTE = '\xff'

HTTP_101_RESPONSE = 'HTTP/1.1 101 Web Socket Protocol Handshake\x0D\x0A'
HTTP_UPGRADE = 'Upgrade: WebSocket\x0D\x0A'
HTTP_CONNECTION = 'Connection: Upgrade\x0D\x0A'

HTTP_ORIGIN = 'WebSocket-Origin: %s\x0D\x0A'
HTTP_LOCATION = 'WebSocket-Location: ws://%s\x0D\x0A'
HTTP_PROTOCOL = 'WebSocket-Protocol: sample\x0D\x0A'

HTTP_SEC_ORIGIN = 'Sec-WebSocket-Origin: %s\x0D\x0A'
HTTP_SEC_LOCATION = 'Sec-WebSocket-Location: ws://%s\x0D\x0A'
HTTP_SEC_PROTOCOL = 'Sec-WebSocket-Protocol: sample\x0D\x0A'

HTTP_CRLF = '\x0D\x0A'
HTTP_CRLF_x2 = '\x0D\x0A\x0D\x0A'

class WebSocket:
    def __init__(self, socket):
        self.Socket = socket
        self.WebSocketBuffer = ''
        self.ApplicationPath = '/'
        self.Host = None
        self.Origin = None

        self.SecurityResponse = ''
        self.WebSocketSecurityRequired = False
        
        try:
            httpHeader = self.Socket.recv(4096)
            #python 2.6 has issues loggin UTF-8
            print httpHeader
            self.ParseHttpHeader(httpHeader)
            
            if self.Origin != None and self.Host != None:
                #WebSocket-Origin = Origin parameter of HTTP request
                #WebSocket-Location = Host + resource request parameters of HTTP request                    
                log.info("WebSocket sending HTTP response to client")
                if self.WebSocketSecurityRequired:
                    self.Socket.send(HTTP_101_RESPONSE)
                    self.Socket.send(HTTP_UPGRADE)
                    self.Socket.send(HTTP_CONNECTION)
                    self.Socket.send(HTTP_SEC_ORIGIN % self.Origin)                    
                    self.Socket.send(HTTP_SEC_LOCATION % (self.Host + self.ApplicationPath))
                    self.Socket.send(HTTP_SEC_PROTOCOL)
                    self.Socket.send(HTTP_CRLF)
                    self.Socket.send( self.SecurityResponse )
                else:
                    self.Socket.send(HTTP_101_RESPONSE)
                    self.Socket.send(HTTP_UPGRADE)
                    self.Socket.send(HTTP_CONNECTION)
                    self.Socket.send(HTTP_ORIGIN % self.Origin)                    
                    self.Socket.send(HTTP_LOCATION % (self.Host + self.ApplicationPath))
                    self.Socket.send(HTTP_PROTOCOL)
                    self.Socket.send(HTTP_CRLF)
                
            else:
                log.warning("WebSocket could not parse HTTP header")
                raise Exception("WebSocket could not parse HTTP header")
            
        except Exception as ex:
            log.warning("WebSocket could not complete the HTTP handshake to establish a web socket connection")
            log.warning(ex)
            self.Close()
            raise ex
            #raise Exception("WebSocket could not complete the HTTP handshake to establish a web socket connection")

    def ParseHttpHeader(self, header):
        appNameStartIndex = header.find("GET /")
        if appNameStartIndex != -1:
            appNameEndIndex = header.find(" HTTP/1.")
            
            if appNameEndIndex != -1:
                appPath = header[appNameStartIndex + 4:appNameEndIndex]
                self.ApplicationPath = appPath
                log.info("Application Path requested by WebSocket connection: %s" % (appPath))

        hostStartIndex = header.find("Host: ")
        if hostStartIndex != -1:
            hostEndIndex = header.find("\r", hostStartIndex)
            if hostEndIndex != -1:
                host = header[hostStartIndex + 6 : hostEndIndex]
                self.Host = host
                log.info("Host requested by WebSocket connection: %s" % (host))
        else:
            log.info("Could not find Host header of HTTP request")
            
        originStartIndex = header.find("Origin: ")
        if originStartIndex != -1:
            originEndIndex = header.find("\r", originStartIndex)
            if originEndIndex != -1:
                origin = header[originStartIndex + 8 : originEndIndex]
                self.Origin = origin
                log.info("Origin requested by WebSocket connection: %s" % (origin))
        else:
            log.info("Could not find Origin header of HTTP request")
            
        #Web Socket Security protocol
        securityKey1 = self._ExtractField(header, "Sec-WebSocket-Key1: ")
        if securityKey1 != None:
            log.info("Sec-Websocket present, need to create Web Socket security response")

            self.WebSocketSecurityRequired = True
            securityKey2 = self._ExtractField(header, "Sec-WebSocket-Key2: ")
            securityCode = header[-8:] #Last 8 bytes (64 bits) not including the terminating HTTP \r\n's

            #python 2.6 has issues loggin UTF-8
            print 'Security Request: ', securityCode
            self.SecurityResponse = self._CreateSecurityResponse(securityKey1, securityKey2, securityCode)

            log.info("Created security response!")
    
    def _ExtractField(self, header, name):
        startIndex = header.find(name)
        if startIndex != -1:
            endIndex = header.find("\r", startIndex)
            if endIndex != -1:
                retVal = header[startIndex + len(name) : endIndex]

                return retVal

        return None

    def _CreateSecurityResponse(self, key1, key2, code):
        secKey1 = self._GetSecKeyValue(key1)
        secKey2 = self._GetSecKeyValue(key2)

        val = ""
        val += struct.pack('>ii', secKey1, secKey2)
        val += code
        
        response = hashlib.md5(val).digest()
        
        return response

    def _GetSecKeyValue(self, key):
        secKeyInts = '0'
        spaceCount = 0
        for char in key:
            ordinal = ord(char)
            if ordinal == 32:
                spaceCount += 1
            elif ordinal >= 48 and ordinal <= 57:
                secKeyInts += char

        secKeyInts = int(secKeyInts)
        secKeyValue = 0
        if spaceCount > 0:
            secKeyValue = secKeyInts/spaceCount

        log.info('Security Key: ')
        log.info(' Space count: ' + str(spaceCount))
        log.info(' Extracted Integers: ' + str(secKeyInts))
        log.info(' Security Key Value: ' + str(secKeyValue))
        
        return secKeyValue
                
    def Send(self, msg):
        log.debug(u'WebSocket sending data to client: %s' % (repr(msg)))
        self.Socket.send(STARTBYTE + str(msg) + ENDBYTE)

    #Will return a (possibly empty) list of commands,
    #or None if the connection is suspected to be closed or an error occurs
    def Recv(self):

        webSocketCommands = []
        
        try:
            log.debug('WebSocket waiting to receive data from client')
            data = self.Socket.recv(4096)

            if not data:
                raise Exception("WebSocket client connection closed")

            #Buffer incoming data
            self.WebSocketBuffer += data
            
            #Parse as many commands as we can from the data we've received, based on web socket protocol
            bufferIndex = self.WebSocketBuffer.find(ENDBYTE)
            while bufferIndex != -1:
                command = self.WebSocketBuffer[:bufferIndex+1]
                
                #will become '' if index+1 is out of range
                self.WebSocketBuffer = self.WebSocketBuffer[bufferIndex+1:]

                if command.find(STARTBYTE) == 0:
                    #strip protocol bytes from front and end of string
                    command = command[1:-1]
                    webSocketCommands.append(command)
                    log.debug(u'WebSocket got command from client: %s' % (repr(command)))
                else:
                    log.warning(u'WebSocket got incorrectly formatted data from client: %s' % (repr(command)))

                bufferIndex = self.WebSocketBuffer.find(ENDBYTE)

            log.debug('WebSocket got data from client: %s' % (repr(webSocketCommands)))
            return webSocketCommands
        
        except Exception as ex:
            log.warning("WebSocket got an exception while trying to receive from client socket:")
            log.warning(ex)
            return None

    def Close(self):
        log.info('WebSocket closing client socket')
        self.Socket.close()

    #Needed for use with select()
    def fileno(self):
        return self.Socket.fileno()
        
