from machine import Pin
import utime as time

debounce_time = 0

class Keypad():
    def __init__(self):
        self.taste1 = Pin(20, Pin.IN, Pin.PULL_UP)
        self.taste2 = Pin(21, Pin.IN, Pin.PULL_UP)
        self.taste3 = Pin(18, Pin.IN, Pin.PULL_UP)
        self.taste4 = Pin(19, Pin.IN, Pin.PULL_UP)
        
        self.taste1.irq(trigger=Pin.IRQ_FALLING, handler=self.callback)
        self.taste2.irq(trigger=Pin.IRQ_FALLING, handler=self.callback)
        self.taste3.irq(trigger=Pin.IRQ_FALLING, handler=self.callback)
        self.taste4.irq(trigger=Pin.IRQ_FALLING, handler=self.callback)
        
        self.interrupt_flag = 0
        self.tastePressed = self.taste1
    
    # Keypress and debouncing
    def callback(self, pin):
        global debounce_time
        if (time.ticks_ms() - debounce_time) > 300:
            self.interrupt_flag = 1
            debounce_time = time.ticks_ms()
            self.tastePressed = pin