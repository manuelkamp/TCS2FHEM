import rp2
import network
import ubinascii
import machine
import urequests as requests
import time
from secrets import secrets
from configs import configs
import sys
import socket
import utime as time
import ustruct as struct
import framebuf
import Oled
import uasyncio as asyncio

rp2.country(configs['country'])
wlan = network.WLAN(network.STA_IF)
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
version = "0.1-alpha"
addr = socket.getaddrinfo('0.0.0.0', configs['api_port'])[0][-1]
led = machine.Pin('LED', machine.Pin.OUT)
Oled = Oled.Oled()

# WLAN-Verbindung herstellen
def wlanConnect():
    wlan.active(True)
    if(configs['disable_wifi_powersavingmode']):
        wlan.config(pm = 0xa11140)
    Log("mac = " + str(mac))
    Log("channel = " + str(wlan.config('channel')))
    Log("essid = " + str(wlan.config('essid')))
    Log("txpower = " + str(wlan.config('txpower')))
    wlan.connect(secrets['ssid'], secrets['pw'])
    timeout = 10
    while timeout > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        timeout -= 1
        Log('Waiting for connection...')
        time.sleep(1)

# Blinkfunktion der Onboard-LED für Errorcodes   
def blink_onboard_led(num_blinks):
    for i in range(num_blinks):
        led.on()
        time.sleep(.2)
        led.off()
        time.sleep(.2)
        
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
def wlanStatus():
    wlan_status = wlan.status()
    blink_onboard_led(wlan_status)
    if wlan_status != 3:
        #raise RuntimeError('Wi-Fi connection failed')
        return False
    else:
        Log('Connected')
        status = wlan.ifconfig()
        Log('ip = ' + status[0])
        return True

# Zeit von NTP holen und setzen
def setRTCTimeNTP():
    Log("getting date and time from NTP " + configs['ntp_host'])
    NTP_DELTA = 2208988800
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(configs['ntp_host'], 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(5)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    except Exception as err:
        Log("Error: " + str(err))
        return False
    finally:
        s.close()
    ntp_time = struct.unpack("!I", msg[40:44])[0] + (3600 * configs['gmt_offset']) #gmt offset from config
    tm = time.gmtime(ntp_time - NTP_DELTA)
    if (configs['auto_summertime']):
        Log("performing auto_summertime adjustment")
        #Time of March change for the current year
        t1 = time.mktime((tm[0],3,(31-(int(5*tm[0]/4+4))%7),1,0,0,0,0))
        #Time of October change for the current year
        t2 = time.mktime((tm[0],10,(31-(int(5*tm[0]/4+1))%7),1,0,0,0,0))
        t = time.mktime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
        if t >= t1 and t < t2:
            tm = time.gmtime(tm + 3600)
    machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))
    return True

# Zeigt Text am Display an
def ShowText(line1, line2, line3):
    Oled.fill(0x0000)
    Oled.text(line1,1,2,Oled.white)
    Oled.text(line2,1,12,Oled.white)
    Oled.text(line3,1,22,Oled.white)  
    Oled.show()

# Loggt messages in log.txt
def Log(message):
    print(message)
    file = open("log.txt", "a")
    file.write(DateTimeNow() + ";" + message + "\n")
    file.close()

# Funktion, die das aktuelle Datum und Uhrzeit zurück gibt
def DateTimeNow():
    tm = time.gmtime()
    return str(tm[2])+"."+str(tm[1])+"."+str(tm[0])+","+str(tm[3])+":"+str(tm[4])#

# Führt einen Reboot des Pico aus (z.B. im Fehlerfall)
def Reboot():
    Log("Performing Reboot")
    machine.reset()

# Berechnet die Uptime in Sekunden
def Uptime(boottime):
    now = time.time()
    return now-boottime

# API
html = """<!DOCTYPE html>
<html>
    <head> <title>Pico W</title> </head>
    <body> <h1>Pico W</h1>
        <p>%s</p>
    </body>
</html>
"""
async def serve_client(reader, writer):
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line)
    led_on = request.find('/light/on')
    led_off = request.find('/light/off')
    print( 'led on = ' + str(led_on))
    print( 'led off = ' + str(led_off))

    stateis = ""
    if led_on == 6:
        print("led on")
        led.on()
        stateis = "LED is ON"
    
    if led_off == 6:
        print("led off")
        led.off()
        stateis = "LED is OFF"
        
    response = html % stateis
    writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")

def BuildScreen():
    #todo screen neu aufbauen
    ShowText("TCS<->FHEM", DateTimeNow(), "Auf Lic Par Set")

# Hauptroutine, die dauerhaft ausgeführt wird
async def MainLoop():
    Log("Entering MainLoop")
    boottime = time.time()
    ShowText("Booting [3/3]", "API Setup: key", secrets['api'])
    Log("Setting up API on port " + str(configs['api_port']) + " with key " + secrets['api'])
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", configs['api_port']))
    #SetUpApi()
    time.sleep(0.8)
    ShowText("TCS<->FHEM", "Firmware:", version)
    Log("Booting complete with Firmware " + version)
    time.sleep(0.8)
    while True:
        #print(Uptime(boottime))
        time.sleep(0.5)
        #todo blink led as heartbeat
        BuildScreen()

#####################################################################

# Booten des Device
def Boot():
    ShowText("Booting [1/3]", "Conn. Wifi:", secrets['ssid'] + "...")
    ShowText("Booting [1/3]", "Conn. Wifi: MAC", mac)
    wlanConnect()
    if (wlanStatus()):
        ShowText("Booting [1/3]", "Conn. Wifi: IP", wlan.ifconfig()[0])
        time.sleep(0.8)
        ShowText("Booting [2/3]", "NTP time:", configs['ntp_host'])
        setRTCTimeNTP()
        ShowText("Booting [2/3]", "NTP time:", DateTimeNow())
        time.sleep(0.8)
        try:
            asyncio.run(MainLoop())
        finally:
            asyncio.new_event_loop()
    else:
        ShowText("Booting [1/3]", "Conn. Wifi:", "ERROR!")
        
Boot()