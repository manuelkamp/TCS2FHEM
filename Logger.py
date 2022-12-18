import machine
import utime as time
import uos as os

class Logger():
    def __init__(self):
        pass

    def LogMessage(self, message):
        print(message)
        dt = machine.RTC().datetime()
        file = open("/logs/"+str(dt[0])+"-"+str(dt[1])+"-"+str(dt[2])+".txt", "a")
        file.write(self.DateTimeNow() + ";" + message + "\n")
        file.close()
    
    def DateTimeNow(self):
        tm = time.gmtime()
        return "%02d.%02d.%04d,%02d:%02d" % (tm[2], tm[1], tm[0], tm[3], tm[4])
    
    def Housekeeping(self):
        for file in os.listdir("/logs"):
            if (file.endswith(".txt")):
                fd = file.split('.')[0].split('-')
                fdate = time.mktime((int(fd[0]), int(fd[1]), int(fd[2]), 0, 0, 0, 0, 0))
                if (fdate + (7 * 86400) <= time.time()):
                    os.remove("/logs/" + file)
                    self.LogMessage("Housekeeping: deleted logfile " + file)