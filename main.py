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
import urequests as requests
from machine import ADC, Pin

from secrets import secrets
from configs import configs

rp2.country(configs['country'])
version = "0.9-beta"

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
busline = ADC(28)
triggerline = Pin(15, Pin.OUT)
writerActive = False

# Checks if string is integer
def IsInt(possibleint):
    try:
        int(possibleint)
    except:
            return False
    else:
            return True

# Reboots the Pico W (f.e. in case of an error)
def Reboot():
    Logger.LogMessage("Performing Reboot")
    machine.reset()

# Calculates the uptime in hours and minutes
def Uptime():
    global boottime
    seconds = (time.time() - boottime) % (24 * 3600)
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d" % (hours, minutes)

# Shows text on the display
def ShowText(line1, line2, line3):
    Oled.fill(0x0000)
    Oled.text(line1,1,2,Oled.white)
    Oled.text(line2,1,12,Oled.white)
    Oled.text(line3,1,22,Oled.white)  
    Oled.show()

# Main method for display output
heartbeat = "H"
def BuildScreen():
    global subscreen, partyMode, lastActionTicks, displayOff, heartbeat
    if heartbeat == "H":
        heartbeat = " "
    else:
        heartbeat = "H"
    lastActionTicks += 1
    # after 10 Seconds of no activity, go back to main screen
    if (lastActionTicks >= 20):
        subscreen = 0
    # after X Minutes turn off the display
    if (lastActionTicks >= (configs['displayoff'] * 60 * 2)):
        displayOff = True
        ShowText("","","")
    else:
        if (subscreen == 0):
            ShowText("TCS<->FHEM " + PartyModeActive() + " " + Networking.IsWifiConnected() + " " + heartbeat + "", TimeUtils.DateTimeNow(), "Auf LiG PaM Chk")
        elif (subscreen == 1):
            ShowText("Eingangstuer", "getriggert", "            Ext")
        elif (subscreen == 2):
            ShowText("Licht am Gang", "getriggert", "            Ext")
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
            ShowText("CPU Frequency:", str(machine.freq()/1000000) + " MHz", "Up  Dwn     Ext")
        elif (subscreen == 9):
            ShowText("Firmware vers.:", version, "Up  Dwn     Ext")
        elif (subscreen == 10):
            ShowText("Uptime (H:m):", Uptime(), "Up  Dwn     Ext")
        elif (subscreen == 11):
            ShowText("Perform", "reboot now", "Up  Dwn OK  Ext")
        else:
            ShowText("Error","Invalid Screen", "            Ext")

# Helper-method for the systemcheck-output on the display
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

# Activates/deactivates the party-mode
def TogglePartyMode():
    global subscreen, partyMode
    if (partyMode):
        partyMode = False
        ExternalAPI("partymode" + PartyModeState())
        Logger.LogMessage("Party-Mode off")
    else:
        partyMode = True
        ExternalAPI("partymode" + PartyModeState())
        Logger.LogMessage("Party-Mode on")
    subscreen = 3

# Sets the party-mode active/inactive
def SetPartyMode(newValue):
    global partyMode
    partyMode = newValue
    ExternalAPI("partymode" + PartyModeState())
    Logger.LogMessage("Setting Party-Mode via API to " + PartyModeState())

# Returns status of party-mode
def PartyModeState():
    global partyMode
    if (partyMode):
        return "enabled"
    else:
        return "disabled"

# Returns status symbol if party-mode is active
def PartyModeActive():
    global PartyMode
    if (partyMode):
        return "P"
    else:
        return " "

#####################################################################

# Helper-method to allow error handling and output in asyncio
def set_global_exception():
    def handle_exception(loop, context):
        Logger.LogMessage("Fatal error: " + str(context["exception"]))
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
        Reboot()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

# Main method for all the UI-handling
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
                        subscreen = 2
                        Logger.LogMessage("Triggering Licht")
                        await TCSBusWriter(configs['light_trigger_message'])
                    elif (Keypad.tastePressed == Keypad.taste4):
                        subscreen = 1
                        Logger.LogMessage("Triggering Door")
                        await TCSBusWriter(configs['door_trigger_message'])
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

# Main method for the API
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
    while await reader.readline() != b"\r\n":
        pass
    request = str(request_line)
    try:
        request = request.split()[1]
    except IndexError:
        pass
    client_ip = writer.get_extra_info('peername')[0]
    Logger.LogMessage("API request: " + request + " - from client IP: " + client_ip)
    if (configs['api_client_ip'] != "") and (configs['api_client_ip'] != client_ip):
        Logger.LogMessage("Unauthorized client! Aborting API Handling now.")
        stateis = "<b>Error 401:</b> Client '" + client_ip + "' is not authorized to use the API!<br><br>Set authorized client IP in configs.py!"
        response = html % stateis
        writer.write('HTTP/1.0 401 Unauthorized\r\nContent-type: text/html\r\n\r\n')
    else:
        req = request.split('/')
        stateis = ""
        if (len(req) == 3 or len(req) == 4 or len(req) == 5):
            if (req[1] == secrets['api']):
                if (req[2] == "triggerdoor"):
                    Logger.LogMessage("Triggering Door")
                    await TCSBusWriter(configs['door_trigger_message'])
                    stateis = "Triggered front door opener"
                elif (req[2] == "triggerlight"):
                    Logger.LogMessage("Triggering Licht")
                    await TCSBusWriter(configs['light_trigger_message'])
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
                elif (req[2] == "ping"):
                    stateis = "OK"
                elif (req[2] == "stats"):
                    stateis = "IP address: " + Networking.GetIPAddress() + "<br>MAC address: " + Networking.GetMACAddress() + "<br>Hostname: " + configs['hostname'] + "<br>API Port: " + str(configs['api_port']) + "<br>Uptime (h:m): " + Uptime() + "<br>Date/Time: " + TimeUtils.DateTimeNow() + "<br>Version: " + version + "<br>GMT Timezone Offset (hours): " + str(configs['gmt_offset']) + "<br>Auto summertime: " + str(configs['auto_summertime']) + "<br>Display off time (mins): " + str(configs['displayoff']) + "<br>Log incoming bus messages: " + str(configs['log_incoming_bus_messages']) + "<br>Housekeep logfiles after days: " + str(configs['log_housekeeping_days']) + "<br>Message 'Front door ringing': " + str(configs['frontdoor_ringing_message']) + "<br>Message 'Door ringing': " + str(configs['door_ringing_message']) + "<br>Message 'Door opener triggered': " + str(configs['door_trigger_message']) + "<br>Message 'Light triggered': " + str(configs['light_trigger_message']) + "<br>CPU frequency (MHz): " + str(machine.freq()/1000000)
                elif (req[2] == "reboot"):
                    stateis = "Rebooting device now..."
                    Reboot()
                elif (req[2] == "ringdoor"):
                    stateis = "Ringing doorbell"
                    await TCSBusWriter(configs['door_ringing_message'])
                elif (req[2] == "ringfrontdoor"):
                    stateis = "Ringing front doorbell"
                    await TCSBusWriter(configs['frontdoor_ringing_message'])
                elif (req[2] == "logs"):
                    if (len(req) >= 4 and req[3] != "json"):
                        if (IsInt(req[3])):
                            stateis = Logger.LastLogs(int(req[3]))
                        else:
                            stateis = "<b>Error:</b> Parameter for log length not an integer!"
                    else:
                        stateis = Logger.LastLogs(50)
                else:
                    stateis = "<b>Error:</b> Unknown command!"
            else:
                stateis = "<b>Error:</b> API key is invalid!"
            if ((len(req) == 4 and req[3] == "json") or (len(req) == 5 and req[4] == "json")):
                response = json % stateis
                writer.write('HTTP/1.0 200 OK\r\nContent-type: text/json\r\n\r\n')
            else:
                response = html % stateis
                writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        else:
            stateis = "<b>Error 400:</b> Invalid usage of API!<br><br><u>Usage:</u> http://servername/api_key/command[/json]<br><br><u>Commands:</u><ul><li>triggerdoor</li><li>triggerlight</li><li>togglepartymode</li><li>partymodeon</li><li>partymodeoff</li><li>partymodestate</li><li>ping</li><li>stats</li><li>reboot</li><li>ringdoor</li><li>ringfrontdoor</li></ul><br><u>API Key:</u> set 'api' in secrets.py file."
            response = html % stateis
            writer.write('HTTP/1.0 400 Bad Request\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)
    await writer.drain()
    await writer.wait_closed()

microsFlanke = 0
def microsSeitLetzterFlanke():
    global microsFlanke
    return time.ticks_us() - microsFlanke

# Main method for the TCS:Bus reader
async def TCSBusReader():
    global busline, microsFlanke, partyMode, writerActive
    zustand = False
    Logger.LogMessage("TCS Busreader started")
    message = []
    while True:
        if not writerActive:
            busValue = busline.read_u16()
            val = 1
            if (busValue >= 30000): #voltage on TCS:Bus 0...65535
                val = 1
            else:
                val = 0
            #measure voltage changes and time in between
            dauer = microsSeitLetzterFlanke()
            if (dauer > 10000) and (message): #handle recieved message, and reset message
                message.pop(0) #remove first timing, because we do not need it
                for i in range(len(message)): #encode bus message (lazy, because the TCS:Bus is not as precise as we are ;) )
                    if (message[i] >= 1000 and message[i] <= 2999):
                        message[i] = 0
                    elif (message[i] >= 3000 and message[i] <= 4999):
                        message[i] = 1
                    elif (message[i] >= 5000 and message[i] <= 6999):
                        message[i] = 2
                    elif (message[i] >= 7000): #this may be an invalid message bit, but for not having numbers like '7543', we encode all this to '3'
                        message[i] = 3
                if (message == configs['light_trigger_message']):
                    if (configs['log_incoming_bus_messages']):
                        Logger.LogMessage("Incoming TCS:Bus message for triggering light: " + str(message))
                    #nothing else to do
                    pass
                elif (message == configs['door_trigger_message']):
                    if (configs['log_incoming_bus_messages']):
                        Logger.LogMessage("Incoming TCS:Bus message for door trigger: " + str(message))
                    #nothing else to do
                    pass
                elif (message == configs['tcs_message']):
                    if (configs['log_incoming_bus_messages']):
                        Logger.LogMessage("Incoming TCS:Bus message from device: " + str(message))
                    #nothing else to do
                    pass
                elif (message == configs['door_ringing_message']):
                    if (configs['log_incoming_bus_messages']):
                        Logger.LogMessage("Incoming TCS:Bus message for door ringing: " + str(message))
                    await ExternalAPI("doorbell")
                elif (message == configs['frontdoor_ringing_message']):
                    if (configs['log_incoming_bus_messages']):
                        Logger.LogMessage("Incoming TCS:Bus message for frontdoor ringing: " + str(message))
                    if (partyMode):
                        asyncio.sleep(1)
                        Logger.LogMessage("Triggering Door and Light for Party-Mode")
                        await TCSBusWriter(configs['door_trigger_message'])
                        asyncio.sleep(1)
                        await TCSBusWriter(configs['light_trigger_message'])
                    await ExternalAPI("frontdoorbell")
                else:
                    if (configs['log_incoming_bus_messages']):
                        Logger.LogMessage("Unknown TCS:Bus message: " + str(message))
                message = []
            else:
                if (val == 0 and zustand == False):
                    message.append(dauer)
                    zustand = True
                    microsFlanke = time.ticks_us()
                if (val == 1 and zustand == True):
                    message.append(dauer)
                    zustand = False
                    microsFlanke = time.ticks_us()
            await asyncio.sleep(0)

# Main method for the TCS:Bus writer
async def TCSBusWriter(message):
    global writerActive
    if (message):
        busMessage = list(message)
        writerActive = True
        for i in range(len(busMessage)): #decode message
            busMessage[i] = int((busMessage[i] + 1) * 2000)
        #start sending message
        sendZero = True
        triggerline.on()
        for i in range(len(busMessage)):
            time.sleep_us(busMessage[i])
            sendZero = not sendZero
            if sendZero:
                triggerline.on()
            else:
                triggerline.off()
        #finally end sending message
        triggerline.off()
        writerActive = False

# Main method for external API (=FHEM)
async def ExternalAPI(action):
    Logger.LogMessage("External API action: " + action)
    if (action == "doorbell"):
        if (configs['fhem_door_ringed'] is not ""):
            response = requests.get(configs['fhem_door_ringed'])
            response.close()
        else:
            Logger.LogMessage("Warning: No fhem_door_ringed setting!")
    elif (action == "frontdoorbell"):
        if (configs['fhem_frontdoor_ringed'] is not ""):
            response = requests.get(configs['fhem_frontdoor_ringed'])
            response.close()
        else:
            Logger.LogMessage("Warning: No fhem_frontdoor_ringed setting!")
    else:
        Logger.LogMessage("Error: Unknown ExternalAPI action!")
    pass

# Main method for daily housekeeping
async def Housekeeper():
    Logger.LogMessage("Housekeeper started")
    while True:
        Logger.LogMessage("Housekeeper is performing actions")
        Logger.Housekeeping()
        Logger.LogMessage("Housekeeper is performing NTP sync")
        NTP.SetRTCTimeFromNTP(configs['ntp_host'], configs['gmt_offset'], configs['auto_summertime'])
        Logger.LogMessage("Housekeeper has finished its jobs")
        await asyncio.sleep(86400)

# Main entry point after booting
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
    loop.create_task(Housekeeper())
    loop.run_forever()

# Booting the device
def Boot():
    ShowText("Booting [1/3]", "Conn. Wifi:", secrets['ssid'] + "...")
    ShowText("Booting [1/3]", "Conn. Wifi: MAC", Networking.GetMACAddress())
    Networking.Connect(configs['disable_wifi_powersavingmode'])
    if (Networking.Status()):
        ShowText("Booting [1/3]", "Conn. Wifi: IP", Networking.GetIPAddress())
        ShowText("Booting [2/3]", "NTP time:", configs['ntp_host'])
        if (NTP.SetRTCTimeFromNTP(configs['ntp_host'], configs['gmt_offset'], configs['auto_summertime'])):
            Logger.DisableTempLogfile()
        ShowText("Booting [2/3]", "NTP time:", TimeUtils.DateTimeNow())
    else:
        ShowText("Booting [1/3]", "Conn. Wifi:", "ERROR!")
        time.sleep(3)
        Reboot()

#####################################################################
        
Boot()
try:
    asyncio.run(Main())
except KeyboardInterrupt:
    Logger.LogMessage("Shutdown.")
    Oled.fill(0x0000)
    Oled.show()
finally:
    asyncio.new_event_loop()
