import machine
import uos as os
import TimeUtils

class Logger():
    def __init__(self, hk_days):
        self.hk_days = hk_days
        self.TimeUtils = TimeUtils.TimeUtils()
        if not "/logs" in os.listdir():
            os.mkdir("/logs")            

    def LogMessage(self, message):
        print(message)
        dt = machine.RTC().datetime()
        file = open("/logs/"+str(dt[0])+"-"+str(dt[1])+"-"+str(dt[2])+".txt", "a")
        file.write(self.TimeUtils.DateTimeNow() + ";" + message + "\n")
        file.close()
    
    def Housekeeping(self):
        for file in os.listdir("/logs"):
            if (file.endswith(".txt")):
                fd = file.split('.')[0].split('-')
                if (self.TimeUtils.IsOlderThanDays(fd, self.hk_days)):
                    os.remove("/logs/" + file)
                    self.LogMessage("Housekeeping: deleted logfile " + file)