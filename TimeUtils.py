import utime as time

class TimeUtils():
    def __init__(self):
        pass
    
    def DateTimeNow(self):
        tm = time.gmtime()
        return "%02d.%02d.%04d,%02d:%02d" % (tm[2], tm[1], tm[0], tm[3], tm[4])
    
    def IsOlderThanDays(self, date, days):
        fdate = time.mktime((int(date[0]), int(date[1]), int(date[2]), 0, 0, 0, 0, 0))
        if (fdate + (int(days) * 86400) <= time.time()):
            return True
        else:
            return False