import struct
# Decode Modbus/TCP
import threading

class ModbusDecoder():

    def __init__(self):
        # _messages will store ethernet frames for the tap device
        self._messages = []
        # _leftoverdecodebytes will store raw bytes left over, in case
        # an ethernet frame was split into more than one modbus request
        self._leftoverdecodebytes = ""
        self._fragmenteddata = ""
        self._decodelock = threading.Lock()
        return

    def decodeAllPackets(self, data):
        bytesConsumed = 0
        packets = []
        while bytesConsumed < len(data):
            tid, pid, lf, uid, fc, db, size = self.decodeSinglePacket(data[bytesConsumed:])
            packets.append({'tid':tid, 'pid':pid, 'lf':lf, 'uid':uid, 'fc':fc, 'db':db, 'size':size})
            bytesConsumed += size
        return packets

    def decodeSinglePacket(self, data):
        if len(data) < 8:
            print "decodeSinglePacket: not enough data to begin decode"
            # don't even bother processing a frame if there
            # isn't enough data
            return None, None, None, None, None, None, 0
        tid = struct.unpack(">H", data[0:2])[0]
        pid = struct.unpack(">H", data[2:4])[0]
        lf  = struct.unpack(">H", data[4:6])[0]
        uid = struct.unpack("B", data[6])[0]
        fc  = struct.unpack("B", data[7])[0]
        db  = data[8:(8+(lf-2))]
        bytesConsumed = 8+len(db)
            
        if lf != 2 + len(db):
            print "decodeSinglePacket: not enough data to fill data",
            for byte in data:
                print hex(ord(byte)),
            print ""
            # we need more data, this packet isn't ready yet
            return None, None, None, None, None, None, 0
        # now we trim the end bytes, in case it was padded
        if (ord(db[0]) & 0x03 == 0x00) and db[0] != "\x10": # last packet in a thingamabob
            # two bits used to store size of last packet in sequence
            print "last seq has", hex(ord(db[0])), "in control field"
            dbsize = (ord(db[0]) & 0x0c) >> 2
            print "last seq has", dbsize, "usable bytes"
            db = db[0:dbsize+1]
            print "last seq made", len(db), "usable bytes:", db
        return tid, pid, lf, uid, fc, db, bytesConsumed
    
    def decodeModbus(self, data):
        self._decodelock.acquire()
        bytesConsumed = 0
        if self._leftoverdecodebytes != "":
            print "decodeModbus: had leftover bytes"
            data = self._leftoverdecodebytes + data
            self._leftoverdecodebytes = ""
        print "decodeModbus called:",
        for byte in data:
            print hex(ord(byte)),
        print ""
        done = False
        while bytesConsumed < len(data):
            tid, pid, lf, uid, fc, db, size = self.decodeSinglePacket(data[bytesConsumed:])
            if size == 0:
                # need more data from tcp stream
                self._leftoverdecodebytes += data[bytesConsumed:]
                break
            bytesConsumed += size
            #print "decodeModbus: got packet: "
            #for byte in db:
            #    print hex(ord(byte)),
            #print ""
            if 3 == fc: # modbus read request
                if db[0] == "\x10": #probe packet, ignore
                    continue
                seqtype = ord(db[0]) & 0x03

                if seqtype == "\x02": #start of a fragmented request
                    # first frame
                    #print "first frame of fragmented request"
                    # if the last packet wasn't complete, ohwell: we lost it
                    self._fragmenteddata = ""
                self._fragmenteddata += db[1:]
                if seqtype == 0x00:
                    # done!
                    #print "last frame"
                    print "built complete packet:", self._fragmenteddata
                    print "used:", bytesConsumed, "out of", len(data), "bytes"
                    self._messages.append(self._fragmenteddata)
                    self._fragmenteddata = ""
                    done = True
                    # now process the frame
        print "decodeModbus exiting"
        self._decodelock.release()
        return done

    # destroy the data when we're done?
    def getReconstructedPacket(self):
        self._decodelock.acquire()
        if len(self._messages) > 0:
            result = self._messages[0]
            self._messages = self._messages[1:]
            self._decodelock.release()
            return result
        else:
            self._decodelock.release()
            return None

def encodeModbus(tid, fc, db, pid = 0x0000, uid = 0xff, probe = False):
    if 3 == fc:
        results = encodeReadReq(tid, fc, pid, uid, db, probe)
    return results # may be more than one packet

def encodeReadReq(tid, fc, pid, uid, db, probe):
    if probe:
        return ["\x00\x00\x00\x00\x00\x06\xff\x03\x10\x00\x00\x01"]
    #print "encodeReadReq: encoding ", db
    packets = []
    packet = ""
    packet += struct.pack(">H", tid)
    packet += struct.pack(">H", pid)
    packet += struct.pack(">H", 0x6) # fixed length of read multiple regs packet
    packet += struct.pack("B", uid)
    packet += struct.pack("B", fc)
    numpackets = ((len(db) / 3) if ((len(db) % 3) == 0)
                  else ((len(db) / 3) + 1))
    print "encoding requires", numpackets, "packets"
    i = 0
    while i < (numpackets -1):
        tpacket = packet + ("\x02" if (i == 0) else "\x01") + db[i*3:(i+1)*3]
        #print "built packet: ", 
        #for byte in tpacket:
        #    print hex(ord(byte)),
        #print ""
        packets.append(tpacket)
        i += 1
    # last packet won't be the same as the other children
    tpacket = ""
    tpacket += struct.pack(">H", tid)
    tpacket += struct.pack(">H", pid)
    tpacket += struct.pack(">H", 0x6) # always 6 bytes, might need padding
    #tpacket += struct.pack(">H", len(db[i*3:])+3) # length of data, +3 bytes for misc for "\x00"
    tpacket += struct.pack("B", uid)
    tpacket += struct.pack("B", fc)
    # last packet, requires the length encoded in two unused bits of control field
    dblen = len(db[i*3:])
    tpacket += chr(dblen << 2) + db[i*3:]
    padbytes = 3 - len(db[i*3:])
    while padbytes > 0:
        tpacket  += "\x00"
        padbytes -= 1
    
    packets.append(tpacket)
    return packets
    
