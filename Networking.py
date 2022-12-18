import network
import ubinascii
import Logger
import machine
import time

wlan = network.WLAN(network.STA_IF)
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
led = machine.Pin('LED', machine.Pin.OUT)

class Networking():
    def __init__(self, Logger, ssid, pw):
        self.ssid = ssid
        self.pw = pw
        self.Logger = Logger
    
    def Connect(self, disable_wifi_powersavingmode):
        wlan.active(True)
        #wlan.config(hostname=configs['hostname'])
        if(disable_wifi_powersavingmode):
            wlan.config(pm = 0xa11140)
        self.Logger.LogMessage("mac = " + str(mac))
        self.Logger.LogMessage("channel = " + str(wlan.config('channel')))
        self.Logger.LogMessage("essid = " + str(wlan.config('essid')))
        self.Logger.LogMessage("txpower = " + str(wlan.config('txpower')))
        wlan.connect(self.ssid, self.pw)
        timeout = 30
        while timeout > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            timeout -= 1
            self.Logger.LogMessage('Waiting for connection...')
            time.sleep(1)
    
    # Wlan Status on LED
    # Handle connection error
    # Error meanings
    # 0  Link Down
    # 1  Link Join
    # 2  Link NoIp
    # 3  Link Up
    # -1 Link Fail
    # -2 Link NoNet
    # -3 Link BadAuth
    def Status(self):
        wlan_status = wlan.status()
        self.BlinkOnboardLED(wlan_status)
        if wlan_status != 3:
            #raise RuntimeError('Wi-Fi connection failed')
            return False
        else:
            self.Logger.LogMessage('Connected')
            status = wlan.ifconfig()
            self.Logger.LogMessage('ip = ' + status[0])
            return True

    # Blinkfunktion der Onboard-LED für Errorcodes   
    def BlinkOnboardLED(self, num_blinks):
        for i in range(num_blinks):
            led.on()
            time.sleep(.2)
            led.off()
            time.sleep(.2)
    
    def GetMACAddress(self):
        return mac
    
    def GetIPAddress(self):
        return wlan.ifconfig()[0]