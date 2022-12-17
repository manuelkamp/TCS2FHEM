# TCS2FHEM

If you have a TCS door intercom system and want to integrate it into your FHEM instance, this is a project for you. The goal of this project is to have a device, that connects the TCS intercom to FHEM. It should allow to trigger the dooropener and other functions (such as switching on the light) in FHEM. Also it should send events (like someone ringed de bell at the front door, or someone ringed the bell at the main door) to FHEM, so you can automate it (send notifications, interact...)  

## Hardware  
* Raspberry Pico W  
* Waveshare 2,23" OLED Display  
* 4-Button Keypad  
* 3D-printed Custom Case for Pico and Button Keypad and power circuit

## Instructions/Setup
In the file configs.py set your configurations:  
country: your countrycode (AT=Austria, DE=Germany...) (2-digit string)  
ntp_host: set a ntp server (string url)  
gmt_offset: offset to gmt for your timezone in hours (int)  
auto_summertime: Enables changing to summertime (and back) automatically (True/False)  
disable_wifi_powersavingmode: Wifi powersavingmode is enabled per default. Set to true to disable powersavingmode for Wifi (True/False)  
api_port: Port on which the API is available (int)  

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
todo

## Power circuit
todo

## Networking
Be sure that you give your Pico a static IP address on your router, so you know where the webservice is availabel and can set it up in FHEM.

## FHEM API
todo