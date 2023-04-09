# TCS2FHEM

If you have a TCS:Bus door intercom system and want to integrate it into your FHEM instance, this is a project for you. The goal of this project is to have a device, that connects the TCS:Bus intercom to FHEM. It should allow to trigger the dooropener and other functions (such as switching on the light) in FHEM. Also it should send events (like someone ringed the bell at the front door, or someone ringed the bell at the main door) to FHEM, so you can automate it (send notifications, interact...)  
## ATTENTION: THIS REPOSITORY IS A COPY AND WILL NOT BE UPDATED ON REGULAR BASIS. PLEASE GO TO https://git.kmpr.at/kamp/TCS2FHEM TO SEE THE LATEST CODE AND/OR SUBMIT PULL REQUESTS OR ISSUES!

## Hardware  
* [Raspberry Pico W](https://mk0.at/pico-w)  
* [Waveshare 2,23" OLED Display](https://mk0.at/waveshare-oled)  
* [4-Button Keypad](https://mk0.at/4-keypad)  
* PCB for your need (see kicad folder for examples)  
* 3D-printed Custom Case for Pico and Button Keypad and power circuit (see case_5v_PCB folder as an example)  

## Prereqisites
You need your PCB fully soldered with everything (you can use a Breadboard temporarily), including keypad and display. Load the Micropython firmware onto your Pico W. I used the v1.19.1-782-g699477d12 (2022-12-20).uf2. It is highly recommended to load the newest firmware from the official repository: https://micropython.org/download/rp2-pico-w/ - But you can use the one I used too, see firmware folder in this repository. Then upload all *.py files to the Pico W's root path (follow the instructions for configuration) and connect the TCS Bus lines accordingly. Finally plug in power (if not powered by TCS:Bus).

## Instructions/Setup
In the file configs.py set your configurations:  
country: your countrycode (AT=Austria, DE=Germany...) (2-digit string)  
ntp_host: set a ntp server (string url)  
gmt_offset: offset to gmt for your timezone in hours (int)  
auto_summertime: Enables changing to summertime (and back) automatically (True/False)  
disable_wifi_powersavingmode: Wifi powersavingmode is enabled per default. Set to true to disable powersavingmode for Wifi (True/False)  
api_port: Port on which the API is available (int)  
displayoff: Minutes after last action, display goes off automatically (int)  
log_incoming_bus_messages: Logs every incoming bus message, which is useful to find out relevant messages for initial setup (bool)  
log_housekeeping_days: Logfiles older than this value in days get deleted by housekeeping (int)  
frontdoor_ringing_message: The TCS:Bus message if someone rings the front door (list)  
door_ringing_message: The TCS:Bus message if someone rings the door (list)  
door_trigger_message: The TCS:Bus message to trigger the front door opener (list)  
light_trigger_message: The TCS:Bus message to trigger the light (list)  
tcs_message: The TCS:Bus message sent every 37 minutes from the TCS:Bus device to check devices - no action, just for filtering (list)  
api_client_ip: Only this IP is allowed to use the API. Leave blank to allow all connections from all IPs (string)  
fhem_door_ringed: URL of FHEM command, when the door is ringed (string)  
fhem_frontdoor_ringed: URL of FHEM command, when the front door is ringed (string)  

In the file secrets.py set your configurations:  
ssid: Wifi name (string)  
pw: Wifi password (string)  
api: API key (string)  

**Hint:** use `openssl rand -hex 20` to generate the api_key

## Wiring of Display  
```
OLED   =>    Pico  
VCC    ->    VSYS  
GND    ->    GND  
DIN    ->    11  
CLK    ->    10  
CS     ->    9  
DC     ->    8  
RST    ->    12  
SDA    ->    6  
SCL    ->    7   
```

## Wiring of 4-Button Keypad  
![picture](https://git.kmpr.at/kamp/TCS2FHEM/raw/branch/main/docs/4-key-pad-connector.png)  

## Power circuit  
### Power from TCS Bus  
The power circuit allows you to run the Pico W directly from the TCS:Bus system's power. It also connects the bus to the Pico to read and write from it. The circuit files for KiCad are stored in the kicad subfolder 'power_from_tcs_bus' of this repo. You can order/print your own PCB with that files.  
![picture](https://git.kmpr.at/kamp/TCS2FHEM/raw/branch/main/docs/pico_tcs_bus.png)  

### Power from 5V power source
The power circuit allows you to run the Pico W with a separate 5 Volt power source (f.e. a USB power adapter). It also connects the bus to the Pico to read and write from it. The circuit files for KiCad are stored in the kicad subfolder 'power_via_5v_source' of this repo. You can order/print your own PCB with that files.  
![picture](https://git.kmpr.at/kamp/TCS2FHEM/raw/branch/main/docs/pico_tcs_5v.png)  

### Power from 9-24V power source
The power circuit allows you to run the Pico W with a separate power source from 9 Volt to 24 Volt. It also connects the bus to the Pico to read and write from it. The circuit files for KiCad are stored in the kicad subfolder 'power_via_9-24v_source' of this repo. You can order/print your own PCB with that files.  
![picture](https://git.kmpr.at/kamp/TCS2FHEM/raw/branch/main/docs/pico_tcs_9-24v.png)  

## Networking  
Be sure that you give your Pico a static IP address on your router, so you know where the webservice is available and can set it up in FHEM.

## TCS2FHEM API  
You can configure the port, on which the API runs in configs.py in the 'api_port'-value. You also have to set an API-Key in secrets.py in the 'api'-value. Then you can call the API as follows:  
http://servername/api_key/command[/json]  

You can use the following commands:  
triggerdoor - Triggers the front door opener  
triggerlight - Triggers the light  
togglepartymode - Enables/disables the Party-Mode  
partymodeon - Sets Party-Mode enabled  
partymodeoff - Sets Party-Mode disabled  
partymodestate - Returns the state of the Party-Mode  
ping - Check if the API is up and running  
stats - Returns some stats of the device  
reboot - Reboots the device  
ringdoor - Sends "ring doorbell" message to TCS:Bus  
ringfrontdoor - Sends "ring front doorbell" message to TCS:Bus  

## FHEM API  

With the FHEM API you interconnect your FHEM instance with your TCS2FHEM device. It allows you for example control the door trigger via FHEM, or handle incoming TCS:Bus messages within FHEM to send you a notification or anything else. In this example configuration, we set up a HTTPMOD device in FHEM to control your TCS2FHEM device within FHEM, using the above explained API commands.  

### Example Setup of FHEMWEB

You need to give your TCS2FHEM device a static IP address within your network. Then you need to create a new FHEMWEB and configure it to work only with the static IP of your TCS2FHEM device without the csrfToken.  

```
define WEBapi FHEMWEB 8086 global
attr WEBapi csrfToken none
attr WEBapi allowfrom your-TCS2FHEM-static-IP|127.0.0.1
```

### Exampe of a HTTPMOD device in FHEM to control TCS2FHEM

This device is used to trigger actions from FHEM via the TCS2FHEM API. In this Example you can trigger the dooropener, the light and the builtin partymode of the TCS2FHEM device.  

```
define TCS2FHEM HTTPMOD 0
setuuid TCS2FHEM 63b875f4-f33f-1b7d-61d3-9101ee190fa5bae1
attr TCS2FHEM icon Todoist
attr TCS2FHEM room TCS
attr TCS2FHEM set01Name triggerDoor
attr TCS2FHEM set01NoArg 1
attr TCS2FHEM set01URL http://servername/api_key/triggerdoor
attr TCS2FHEM set02Name triggerLight
attr TCS2FHEM set02NoArg 1
attr TCS2FHEM set02URL http://servername/api_key/triggerlight
attr TCS2FHEM set03Name togglePartyMode
attr TCS2FHEM set03NoArg 1
attr TCS2FHEM set03URL http://servername/api_key/togglepartymode
attr TCS2FHEM webCmd triggerDoor:triggerLight:togglePartyMode
```

### Example of Notify and Dummy device in FHEM to send a message to your smartphone

This dummy device is used to represent the state. The state 'idle' means, there is no action. The state 'ringed' is set if someone rings your doorbell and the TCS2FHEM device sets it. The notify device in FHEM is used to see the change from idle to ringed, and you can perform your wanted action in FHEM.  

```
define TCS_Door dummy
setuuid TCS_Door 63a1c02e-f33f-1b7d-29b2-21917943a9d12101
attr TCS_Door room TCS
attr TCS_Door setList idle ringed
```

```
define n_TCS_Door notify TCS_Door:ringed set Talk msg Jemand hat an der Wohnungstür angeläutet;; set TCS_Door idle
setuuid n_TCS_Door 63a1c0c2-f33f-1b7d-fe89-1e89dde293580eb1
attr n_TCS_Door disabledAfterTrigger 10
attr n_TCS_Door room TCS
```

For this devices, the FHEM API Url that you need to use in TCS2FHEM setting 'fhem_door_ringed' would be:  
```
http://fhem-server:8086/fhem?cmd=set%20TCS_Door%20ringed&XHR=1
```

This works exactly the same for the TCS2FHEM settings 'fhem_frontdoor_ringed'.

### Example of Notify and Dummy device in FHEM for Partymode

If you decide to not use the builtin Partymode in your TCS2FHEM device, you can set up a Partymode in FHEM. This may be useful, if you want to trigger more actions as it would be possible with just the TCS2FHEM device.  

```
coming soon...
``` 

## Legal remarks
I am not affiliated to TCSAG and/or any of their brands and/or trademarks, nor do I have any business information on the proprietary TCS:Bus. I just reverse engineered it, to include my intercom system into my home automation and shared my research here. All Rights to the possible Trademark TCS:Bus and all things connected, remain untouched by this open source project.
