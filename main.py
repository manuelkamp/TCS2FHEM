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
import uos as os
from machine import Pin

rp2.country(configs['country'])
wlan = network.WLAN(network.STA_IF)
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
version = "0.1-alpha"
led = machine.Pin('LED', machine.Pin.OUT)
Oled = Oled.Oled()
boottime = time.time()
interrupt_flag = 0
debounce_time = 0
taste1 = Pin(18, Pin.IN, Pin.PULL_UP)
taste2 = Pin(19, Pin.IN, Pin.PULL_UP)
taste3 = Pin(20, Pin.IN, Pin.PULL_UP)
taste4 = Pin(21, Pin.IN, Pin.PULL_UP)
tasteA = taste1
subscreen = 0
sc = 0
partyMode = False
lastActionTicks = 0
displayOff = False

def callback(pin):
    global interrupt_flag, debounce_time, tasteA
    if (time.ticks_ms() - debounce_time) > 300:
        interrupt_flag = 1
        debounce_time = time.ticks_ms()
        tasteA = pin

taste1.irq(trigger=Pin.IRQ_FALLING, handler=callback)
taste2.irq(trigger=Pin.IRQ_FALLING, handler=callback)
taste3.irq(trigger=Pin.IRQ_FALLING, handler=callback)
taste4.irq(trigger=Pin.IRQ_FALLING, handler=callback)

# WLAN-Verbindung herstellen
def wlanConnect():
    wlan.active(True)
    #wlan.config(hostname=configs['hostname'])
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

# Loggt messages in täglichen Logfiles im Ordner logs
def Log(message):
    print(message)
    dt = machine.RTC().datetime()
    file = open("/logs/"+str(dt[0])+"-"+str(dt[1])+"-"+str(dt[2])+".txt", "a")
    file.write(DateTimeNow() + ";" + message + "\n")
    file.close()

# Funktion, die das aktuelle Datum und Uhrzeit zurück gibt
def DateTimeNow():
    tm = time.gmtime()
    return "%02d.%02d.%04d,%02d:%02d" % (tm[2], tm[1], tm[0], tm[3], tm[4])

# Führt einen Reboot des Pico aus (z.B. im Fehlerfall)
def Reboot():
    Log("Performing Reboot")
    machine.reset()

# Berechnet die Uptime in Sekunden
def Uptime():
    global boottime
    seconds = (time.time() - boottime) % (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d" % (hours, minutes)

# Löscht alle Logs die nicht von heute sind
def HousekeepingLogs():
    for file in os.listdir("/logs"):
        if(file.endswith(".txt")):
            print(file)
            #todo delete files older than x days

# API
html = """<!DOCTYPE html>
<html>
    <head> <title>Pico W</title> </head>
    <body> <h1>Pico W</h1>
        <p>%s</p>
    </body>
</html>
"""
async def ServeApi(reader, writer):
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

# Bildschirmausgabe
def BuildScreen():
    global subscreen, partyMode, lastActionTicks, displayOff
    lastActionTicks += 1
    # after 10 Seconds of no activity, go back to main screen
    if (lastActionTicks >= 20):
        subscreen = 0
    # after 5 Minutes turn off the display
    if (lastActionTicks >= (configs['displayoff'] * 60 * 2)):
        displayOff = True
        ShowText("","","")
    else:
        if (subscreen == 0):
            ShowText("TCS<->FHEM", DateTimeNow(), "Auf LiG PaM Chk")
        elif (subscreen == 1):
            ShowText("Eingangstuer", "getriggert", "            Ext")
        elif (subscreen == 2):
            ShowText("Licht im Gang", "getriggert", "            Ext")
        elif (subscreen == 3):
            ShowText("Party-Mode", ("aktiviert" if partyMode else "deaktiviert"), "            Ext")
        elif (subscreen == 4):
            ShowText("Hostname:", configs['hostname'], "Up  Dwn     Ext")
        elif (subscreen == 5):
            ShowText("MAC Address:", ubinascii.hexlify(network.WLAN().config('mac'),':').decode(), "Up  Dwn     Ext")
        elif (subscreen == 6):
            ShowText("IP Address:", wlan.ifconfig()[0], "Up  Dwn     Ext")
        elif (subscreen == 7):
            ShowText("API key:", secrets['api'], "Up  Dwn     Ext")
        elif (subscreen == 8):
            ShowText("CPU Frequency:", str(machine.freq()) + " Hz", "Up  Dwn     Ext")
        elif (subscreen == 9):
            ShowText("Firmware vers.:", version, "Up  Dwn     Ext")
        elif (subscreen == 10):
            ShowText("Uptime (H:m):", Uptime(), "Up  Dwn     Ext")
        elif (subscreen == 11):
            ShowText("Perform", "reboot now", "Up  Dwn OK  Ext")
        else:
            ShowText("Error","Invalid Screen", "            Ext")

def ShowSystemCheck(screen):
    global subscreen, sc
    if (screen == "start"):
        Log("Showing Systemcheck")
        sc = 0
    elif (screen == "next"):
        sc = sc + 1
    else:
        sc = sc - 1
    if (sc > 7):
        sc = 0
    elif (sc < 0):
        sc = 7
    subscreen = sc + 4

def TogglePartyMode():
    global subscreen, partyMode
    if (partyMode):
        partyMode = False
        Log("Party-Mode off")
    else:
        partyMode = True
        Log("Party-Mode on")
    subscreen = 3
    
def TriggerLicht():
    #todo
    global subscreen
    subscreen = 2
    Log("Triggering Licht")
    
def TriggerDoor():
    #todo
    global subscreen
    subscreen = 1
    Log("Triggering Door")

# Hauptroutine, die dauerhaft ausgeführt wird
async def MainLoop():
    global interrupt_flag, debounce_time, tasteA, subscreen, boottime, lastActionTicks, displayOff
    Log("Entering MainLoop")
    boottime = time.time()
    ShowText("Booting [3/3]", "API Setup: key", secrets['api'])
    Log("Setting up API on port " + str(configs['api_port']) + " with key " + secrets['api'])
    asyncio.create_task(asyncio.start_server(ServeApi, "0.0.0.0", configs['api_port']))
    ShowText("TCS<->FHEM", "Firmware:", version)
    Log("Booting complete with Firmware " + version)
    while True:
        time.sleep(0.5)
        BuildScreen()
        if interrupt_flag is 1:
            interrupt_flag = 0
            lastActionTicks = 0
            if (displayOff):
                displayOff = False
            else:
                interrupt_flag = 0
                if (subscreen == 0):
                    if (tasteA == taste1):
                        ShowSystemCheck("start")
                    elif (tasteA == taste2):
                        TogglePartyMode()
                    elif (tasteA == taste3):
                        TriggerLicht()
                    elif (tasteA == taste4):
                        TriggerDoor()
                    else:
                        Log("Error: Invalid Button pressed!")
                elif (subscreen == 1 or subscreen == 2 or subscreen == 3):
                    if (tasteA == taste1):
                        subscreen = 0
                elif (subscreen == 4 or subscreen == 5 or subscreen == 6 or subscreen == 7 or subscreen == 8 or subscreen == 9 or subscreen == 10 or subscreen == 11):
                    if (tasteA == taste1):
                        subscreen = 0
                    elif (subscreen == 11 and tasteA == taste2):
                        Reboot()
                    elif (tasteA == taste3):
                        ShowSystemCheck("next")
                    elif (tasteA == taste4):
                        ShowSystemCheck("prev")
                    else:
                        Log("Error: Invalid Button pressed!")
                else:
                    if (tasteA == taste1):
                        subscreen = 0

#####################################################################

# Booten des Device
def Boot():
    HousekeepingLogs()
    ShowText("Booting [1/3]", "Conn. Wifi:", secrets['ssid'] + "...")
    ShowText("Booting [1/3]", "Conn. Wifi: MAC", mac)
    wlanConnect()
    if (wlanStatus()):
        ShowText("Booting [1/3]", "Conn. Wifi: IP", wlan.ifconfig()[0])
        ShowText("Booting [2/3]", "NTP time:", configs['ntp_host'])
        setRTCTimeNTP()
        ShowText("Booting [2/3]", "NTP time:", DateTimeNow())
        try:
            asyncio.run(MainLoop())
        finally:
            asyncio.new_event_loop()
    else:
        ShowText("Booting [1/3]", "Conn. Wifi:", "ERROR!")
        
Boot()