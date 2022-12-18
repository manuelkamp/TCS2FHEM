import utime as time
import socket

class NTP():
    def __init__(self, Logger):
        self.Logger = Logger
    
    def SetRTCTimeFromNTP(self, host, gmt_offset, auto_summertime):
        self.Logger.LogMessage("getting date and time from NTP " + host)
        NTP_DELTA = 2208988800
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1B
        addr = socket.getaddrinfo(host, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(5)
            res = s.sendto(NTP_QUERY, addr)
            msg = s.recv(48)
        except Exception as err:
            self.Logger.LogMessage("Error: " + str(err))
            return False
        finally:
            s.close()
        ntp_time = struct.unpack("!I", msg[40:44])[0] + (3600 * gmt_offset) #gmt offset from config
        tm = time.gmtime(ntp_time - NTP_DELTA)
        if (auto_summertime):
            self.Logger.LogMessage("performing auto_summertime adjustment")
            #Time of March change for the current year
            t1 = time.mktime((tm[0],3,(31-(int(5*tm[0]/4+4))%7),1,0,0,0,0))
            #Time of October change for the current year
            t2 = time.mktime((tm[0],10,(31-(int(5*tm[0]/4+1))%7),1,0,0,0,0))
            t = time.mktime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
            if t >= t1 and t < t2:
                tm = time.gmtime(tm + 3600)
        machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        return True
