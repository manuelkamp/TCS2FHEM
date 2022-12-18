import rp2
import TimeUtils
import Logger
import Oled
import Networking
import NTP
import uasyncio as asyncio
import utime as time
import Keypad
import usocket as socket

from secrets import secrets
from configs import configs

rp2.country(configs['country'])
version = "0.2-alpha"

Oled = Oled.Oled()
TimeUtils = TimeUtils.TimeUtils()
Logger = Logger.Logger(configs['log_housekeeping_days'])
Networking = Networking.Networking(Logger, secrets['ssid'], secrets['pw'])
NTP = NTP.NTP(Logger)
Keypad = Keypad.Keypad()

boottime = time.time()
lastActionTicks = 0
subscreen = 0
sc = 0
partyMode = False
displayOff = False
busline = machine.ADC(28)

# Führt einen Reboot des Pico aus (z.B. im Fehlerfall)
def Reboot():
    Logger.LogMessage("Performing Reboot")
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

# Zeigt Text am Display an
def ShowText(line1, line2, line3):
    Oled.fill(0x0000)
    Oled.text(line1,1,2,Oled.white)
    Oled.text(line2,1,12,Oled.white)
    Oled.text(line3,1,22,Oled.white)  
    Oled.show()

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
            ShowText("TCS<->FHEM", TimeUtils.DateTimeNow(), "Auf LiG PaM Chk")
        elif (subscreen == 1):
            ShowText("Eingangstuer", "getriggert", "            Ext")
        elif (subscreen == 2):
            ShowText("Licht im Gang", "getriggert", "            Ext")
        elif (subscreen == 3):
            ShowText("Party-Mode", ("aktiviert" if partyMode else "deaktiviert"), "            Ext")
        elif (subscreen == 4):
            ShowText("Hostname:", configs['hostname'], "Up  Dwn     Ext")
        elif (subscreen == 5):
            ShowText("MAC Address:", Networking.GetMACAddress(), "Up  Dwn     Ext")
        elif (subscreen == 6):
            ShowText("IP Address:", Networking.GetIPAddress(), "Up  Dwn     Ext")
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

# Helfermethode für Systemcheck-Anzeige
def ShowSystemCheck(screen):
    global subscreen, sc
    if (screen == "start"):
        Logger.LogMessage("Showing Systemcheck")
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

# Aktiviert/Deaktiviert den Party-Mode
def TogglePartyMode():
    global subscreen, partyMode
    if (partyMode):
        partyMode = False
        Logger.LogMessage("Party-Mode off")
    else:
        partyMode = True
        Logger.LogMessage("Party-Mode on")
    subscreen = 3

# Setzt den Party-Mode auf Aktiv/Inaktiv
def SetPartyMode(newValue):
    global partyMode
    partyMode = newValue
    Logger.LogMessage("Setting Party-Mode via API to " + PartyModeState())

# Gibt den Status des Party-Mode zurück
def PartyModeState():
    global partyMode
    if (partyMode):
        return "enabled"
    else:
        return "disabled"

# Triggert das Licht am Gang
def TriggerLicht():
    #todo
    global subscreen
    subscreen = 2
    Logger.LogMessage("Triggering Licht")

# Triggert den Türöffner
def TriggerDoor():
    #todo
    global subscreen
    subscreen = 1
    Logger.LogMessage("Triggering Door")

#####################################################################

# Helfer-Methode, um Fehler auch in asyncio ausgeben zu können
def set_global_exception():
    def handle_exception(loop, context):
        Logger.LogMessage("Fatal error: " + str(context["exception"]))
        #import sys
        #sys.print_exception(context["exception"])
        #sys.exit()
        Reboot()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

# Haupt-Methode für das ganze UI-Handling
async def UiHandling():
    global interrupt_flag, lastActionTicks, displayOff, subscreen
    Logger.LogMessage("UI handling started")
    while True:
        BuildScreen()
        if Keypad.interrupt_flag is 1:
            Keypad.interrupt_flag = 0
            lastActionTicks = 0
            if (displayOff):
                displayOff = False
            else:
                Keypad.interrupt_flag = 0
                if (subscreen == 0):
                    if (Keypad.tastePressed == Keypad.taste1):
                        ShowSystemCheck("start")
                    elif (Keypad.tastePressed == Keypad.taste2):
                        TogglePartyMode()
                    elif (Keypad.tastePressed == Keypad.taste3):
                        TriggerLicht()
                    elif (Keypad.tastePressed == Keypad.taste4):
                        TriggerDoor()
                    else:
                        Logger.LogMessage("Error: Invalid Button pressed!")
                elif (subscreen == 1 or subscreen == 2 or subscreen == 3):
                    if (Keypad.tastePressed == Keypad.taste1):
                        subscreen = 0
                elif (subscreen == 4 or subscreen == 5 or subscreen == 6 or subscreen == 7 or subscreen == 8 or subscreen == 9 or subscreen == 10 or subscreen == 11):
                    if (Keypad.tastePressed == Keypad.taste1):
                        subscreen = 0
                    elif (subscreen == 11 and Keypad.tastePressed == Keypad.taste2):
                        Reboot()
                    elif (Keypad.tastePressed == Keypad.taste3):
                        ShowSystemCheck("next")
                    elif (Keypad.tastePressed == Keypad.taste4):
                        ShowSystemCheck("prev")
                    else:
                        Logger.LogMessage("Error: Invalid Button pressed!")
                else:
                    if (Keypad.tastePressed == Keypad.taste1):
                        subscreen = 0
        await asyncio.sleep(0.5)

# Hauptmethode für die API
html = """<!DOCTYPE html>
<html>
    <head> <title>TCS<->FHEM</title> </head>
    <body> <h1>TCS<->FHEM</h1>
        <p>%s</p>
    </body>
</html>"""
json = """{ "TCS<->FHEM API":"%s" }"""
async def APIHandling(reader, writer):
    request_line = await reader.readline()
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass
    request = str(request_line)
    try:
        request = request.split()[1]
    except IndexError:
        pass
    Logger.LogMessage("API request: " + request)
    req = request.split('/')
    stateis = ""
    if (len(req) == 3 or len(req) == 4):
        if (req[1] == secrets['api']):
            if (req[2] == "triggerdoor"):
                TriggerDoor()
                stateis = "Triggered front door opener"
            elif (req[2] == "triggerlight"):
                TriggerLicht()
                stateis = "Triggered light"
            elif (req[2] == "togglepartymode"):
                TogglePartyMode()
                stateis = "Toggled Party-Mode"
            elif (req[2] == "partymodeon"):
                SetPartyMode(True)
                stateis = "Enabled Party-Mode"
            elif (req[2] == "partymodeoff"):
                SetPartyMode(False)
                stateis = "Disabled Party-Mode"
            elif (req[2] == "partymodestate"):
                stateis = "Party-Mode is " + PartyModeState()
            else:
                stateis = "Error: Unknown command!"
        else:
            stateis = "<b>Error:</b> API key is invalid!"
        if (len(req) == 4 and req[3] == "json"):
            response = json % stateis
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/json\r\n\r\n')
        else:
            response = html % stateis
            writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    else:
        stateis = "<b>Error:</b> Invalid usage of API!<br><br><u>Usage:</u> http://servername/api_key/command[/json]<br><br><u>Commands:</u><ul><li>triggerdoor</li><li>triggerlight</li><li>togglepartymode</li><li>partymodeon</li><li>partymodeoff</li><li>partymodestate</li></ul><br><u>API Key:</u> set 'api' in secrets.py file."
        response = html % stateis
        writer.write('HTTP/1.0 500 Server Error\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    await writer.drain()
    await writer.wait_closed()

# Hauptmethode für den TCS Bus Reader
async def TCSBusReader():
    global busline
    Logger.LogMessage("TCS Busreader started")
    reading = busline.read_u16()
    while True:
        #todo
        i = 2
        #print("tcs")
        #if doorbell ringing is recognized, trigger external api
        #if frontdoorbell ringing is recognized, trigger external api
        #if frontdoorbell ringing is recognized and party-mode enabled, wait a short time and trigger DoorOpener and Licht
        #if any other message and log_bus_messages is true, log the messages to the bus (it may help identify useful messages, or if someone ringed at your neighbours door)
        await asyncio.sleep(0.5)

# Hauptroutine
async def Main():
    set_global_exception()
    Logger.LogMessage("Entering MainLoop")
    boottime = time.time()
    loop = asyncio.get_event_loop()
    ShowText("Booting [3/3]", "API Setup: key", secrets['api'])
    Logger.LogMessage("Setting up API on port " + str(configs['api_port']) + " with key " + secrets['api'])
    loop.create_task(asyncio.start_server(APIHandling, Networking.GetIPAddress(), configs['api_port']))
    Logger.LogMessage("API started")
    ShowText("TCS<->FHEM", "Firmware:", version)
    Logger.LogMessage("Booting complete with Firmware " + version)
    loop.create_task(UiHandling())
    loop.create_task(TCSBusReader())
    loop.run_forever()

# Booten des Device
def Boot():
    Logger.Housekeeping()
    ShowText("Booting [1/3]", "Conn. Wifi:", secrets['ssid'] + "...")
    ShowText("Booting [1/3]", "Conn. Wifi: MAC", Networking.GetMACAddress())
    Networking.Connect(configs['disable_wifi_powersavingmode'])
    if (Networking.Status()):
        ShowText("Booting [1/3]", "Conn. Wifi: IP", Networking.GetIPAddress())
        ShowText("Booting [2/3]", "NTP time:", configs['ntp_host'])
        NTP.SetRTCTimeFromNTP(configs['ntp_host'], configs['gmt_offset'], configs['auto_summertime'])
        ShowText("Booting [2/3]", "NTP time:", TimeUtils.DateTimeNow())
    else:
        ShowText("Booting [1/3]", "Conn. Wifi:", "ERROR!")

#####################################################################
        
Boot()
try:
    asyncio.run(Main())
finally:
    asyncio.new_event_loop()