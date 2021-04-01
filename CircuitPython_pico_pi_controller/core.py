# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['UNDevice', 'PPDevice', 'PPController']

# Cell

from CircuitPython_pico_pi_common.codes import *
from sys import byteorder
import board
import microcontroller
from busio import I2C
from adafruit_bus_device.i2c_device import I2CDevice
try:
    from rtc import RTC
except ModuleNotFoundError:
    pass
try:
    from adafruit_datetime import datetime
except ModuleNotFoundError:
    from datetime import datetime
try:
    from adafruit_itertools.adafruit_itertools import chain
except ModuleNotFoundError:
    from itertools import chain

try:
    import adafruit_logging as logging
    logger = logging.getLogger('PPC')
    logger.setLevel(logging.DEBUG)
    # Monkey patch the logger's timestamp
    def format(self, level, msg):
        return "{0}: {1} - {2}".format(datetime.now().isoformat(), logging.level_for(level), msg)
    logging.LoggingHandler.format = format
except ModuleNotFoundError:
    import logging
    logger = logging.getLogger()
    logging.basicConfig(level = logging.DEBUG)

# Cell

class UNDevice():
    """Represents an I2C peripheral device unidentified to a `PPController`"""
    def __init__(self, controller, device_address):
        self.controller  = controller
        """type: PPController Creator/owner of the UNDevice instance."""
        self.i2cdevice      = None
        """type: I2CDevice Created by a PPController."""
        self.device_address = device_address
        """type: int The I2C address of the UNDevice"""

        self.retries     = 0
        self.retries_max = 4
        """retry count before I2CDevice is considered 'other', i.e. not a PPC device."""

class PPDevice():
    """Represents an I2C peripheral device identified as a `PPDevice`
    and stores data from those hosts."""
    def __init__(self, controller, device_address):
        self.controller     = controller
        """type: PPController Creator/owner of the PPDevice instance."""
        self.i2cdevice      = None
        """type: I2CDevice Created by a PPController."""
        self.device_address = device_address
        """type: int The I2C address of the PPDevice"""

        self.lastonline  = None
        """type: int A controller timestamp updated with each successful receive.
           reports & bosmang can decide what to do with this info."""

        """All data below are received via I2C *from* the PPC device:"""

        self.bosmang    = None
        """type: bool Declaration that device can send datetime & commands to controller.
           Only one bosmang per controller please, unless you wanya chaos."""
        self.command    = None
        """type: bytes Ref: CMD_CODES The latest command received from a PPC device."""

        self.hostname   = None
        """type: str"""
        self.timestamp   = None
        """type: int Used to send datetime as bosmang &  to check for datetime skew on other devices."""
        self.utcoffset  = None
        """type: int"""
        self.loadavg    = None
        """type: str"""
        self.uptime     = None
        """type: int"""

        self.uart_rx    = None
        """type: int MCU gpio rx for passthru from bosmang console TX"""
        self.uart_tx    = None
        """type: int MCU gpio tx for passthru from bosmang console RX"""
        self.pen        = None
        """type: int MCU gpio connected to RPi pen pin"""

        self.id_str = type(self).__name__[2]+" "+str(hex(self.device_address))

    def log_txn(self, fname, message, msg=None):
        """Wrapper for logger."""
        logger.info('%-6s %-27s %-9s %s' % (self.id_str, message+str(msg or ''), fname, self.controller.i2c_str))

    @staticmethod
    def conv_sec(seconds):
        """Convert seconds into a tuple: days, hours, minutes, seconds"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        return days, hours, minutes, seconds

    @staticmethod
    def clr_fifo(i2cdevice):
        """Clear the i2c peripheral's transmit FIFO"""
        msg = bytearray(REG_VAL_LEN['CLR'])
        try:
            i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
        except OSError:
            pass

    def get_hos(self):
        """Ask PPD for its hostname"""
        fname='get_hos'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = bytearray(REG_VAL_LEN['HOS'])
            try:
                i2cdevice.write_then_readinto(REG_CODE['HOS'],msg)
                """Get the length in bytes of the hostname"""
                msg = bytearray(int.from_bytes(msg, byteorder))
                i2cdevice.readinto(msg)
                self.lastonline=int(datetime.now().timestamp())
                self.log_txn(fname,"recvd hostname ",msg.decode())
                return msg.decode()
            except OSError:
                pass
        return None

    def get_tim(self):
        """Ask PPD for its datetime in seconds since epoch, returns timestamp int"""
        fname='get_tim'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = bytearray(REG_VAL_LEN['TIM'])
            try:
                i2cdevice.write_then_readinto(REG_CODE['TIM'],msg)
                self.lastonline=int(datetime.now().timestamp())
                self.log_txn(fname,"recvd timestamp: ",int.from_bytes(bytes(msg),byteorder))
                return int.from_bytes(bytes(msg),byteorder)
            except OSError:
                pass
        return None

    def get_bos(self):
        """Ask PPD for its bosmang status (bool)"""
        fname='get_bos'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = bytearray(REG_VAL_LEN['BOS'])
            try:
                i2cdevice.write_then_readinto(REG_CODE['BOS'],msg)
                self.lastonline=int(datetime.now().timestamp())
                self.log_txn(fname,"recvd bosmang status: ", str(bool(int.from_bytes(bytes(msg), byteorder))))
                return bool(int.from_bytes(bytes(msg), byteorder))
            except OSError:
                pass
        return None

    def get_cmd(self):
        """Ask PPD for a command (if any)"""
        fname='get_cmd'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            cmd = bytearray(REG_VAL_LEN['CMD'])
            try:
                i2cdevice.write_then_readinto(REG_CODE['CMD'],cmd)
                """Get the command code or 0 for no command"""
                cmd_code = int.from_bytes(bytes(cmd),byteorder)
                if cmd_code:
                    #cmd_tup  = self.dcd_cmd(cmd_code)
                    cmda = bytearray(CMD_VAL_LEN[cmd_code])
                    i2cdevice.readinto(cmda)
                    self.log_txn(fname,"recvd command ",CMD_NAME[cmd_code]+' '+str(hex(cmda[0])))
                    self.lastonline=int(datetime.now().timestamp())
                    return cmd+cmda
                else:
                    self.lastonline=int(datetime.now().timestamp())
                    self.log_txn(fname,"recvd no command")
                    return None
            except OSError:
                pass
        return None

    def get_tzn(self):
        """Ask PPD for its timezone (in seconds offset from utc)"""
        fname='get_tzn'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = bytearray(REG_VAL_LEN['TZN'])
            try:
                i2cdevice.write_then_readinto(REG_CODE['TZN'],msg)
                self.lastonline=int(datetime.now().timestamp())
                self.log_txn(fname,"recvd utcoffset: ",int.from_bytes(bytes(msg),byteorder))
                return int.from_bytes(bytes(msg),byteorder)
            except OSError:
                pass
        return None

    def get_lod(self):
        """Ask PPD for its load average"""
        fname='get_lod'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = bytearray(REG_VAL_LEN['LOD'])
            try:
                i2cdevice.write_then_readinto(REG_CODE['LOD'],msg)
                self.lastonline=int(datetime.now().timestamp())
                self.log_txn(fname,"recvd loadavg: ","{:04.2f}".format(float(msg.decode())))
                return msg.decode()
            except OSError:
                pass
        return None

    def get_upt(self):
        """Ask PPD for its uptime in seconds"""
        fname='get_upt'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = bytearray(1)
            try:
                i2cdevice.write_then_readinto(REG_CODE['UPT'],msg)
                """Read one byte so we can pause for PPD to get uptime"""
                msg = bytearray(REG_VAL_LEN['UPT'])
                i2cdevice.readinto(msg)
                self.lastonline=int(datetime.now().timestamp())
                self.log_txn(fname,"recvd uptime: ",int.from_bytes(bytes(msg),byteorder))
                self.log_txn(fname,"uptime %d d %02d:%02d" % self.conv_sec(int.from_bytes(bytes(msg),byteorder))[:3])
                return int.from_bytes(bytes(msg),byteorder)
            except OSError:
                pass
        return None

    def get_urx(self):
        """Ask PPD for the MCU board pin where its UART RX is connected"""
        return self.uart_rx

    def get_utx(self):
        """Ask PPD for the MCU board pin where its UART TX is connected"""
        return self.uart_tx

    def get_pen(self):
        """Ask PPD for the MCU board pin where its PEN is connected"""
        return self.pen

    def set_flkr(self, duration):
        """Tell PPD to flicker its power LED for duration (seconds)"""
        fname='set_flkr'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            self.clr_fifo(i2cdevice)
            msg = REG_CODE['FLK'] + bytearray([duration])
            try:
                i2cdevice.write(msg)
                self.log_txn(fname,'sent FLICKER: '+str(duration)+' seconds')
                return True
            except OSError:
                pass
        return None

class PPController():
    """Represents one of the system's I2C busses and tracks which I2C
       peripherals are `PPDevice`s."""
    def __init__(self, **kwargs):
        fname='__init__'
        self.scl       = kwargs.pop('scl', board.SCL)
        self.sda       = kwargs.pop('sda', board.SDA)
        self.frequency = kwargs.pop('frequency', 4800)
        self.timeout   = kwargs.pop('timeout', 10000)

        self.i2c       = I2C(scl=self.scl, sda=self.sda, frequency=self.frequency, timeout=self.timeout)

        self.bosmang   = kwargs.pop('bosmang', None)
        """type: int PPDevice device_address selected to recieve datetime & control
           instructions from, have UART connected for passthru, etc. If set, bosmang
           will be the first PPDevice contacted & MCU RTC will be set at the earliest
           possible time."""
        if kwargs:
            raise TypeError('Unepxected kwargs provided: %s' % list(kwargs.keys()))

        self.utcoffset = None
        self.clock     = RTC()

        self.ppds      = []
        """PPDevice objects belonging to a PPController object."""
        self.noident   = []
        """UNDevice objects belonging to a PPController object."""
        self.othrdev   = []
        """UNDevice objects without I2CDevices (address record only)
           recognized as 'other' peripherals"""

        #TBD: impliment UID if system is not an MCU
        self.mcu_uid = '0x'+''.join(map(str, ['{:0>{w}}'.format( hex(x)[2:], w=2 ) for x in microcontroller.cpu.uid])) or None
        self.i2c_str = str(self.scl).strip('board.')+"/"+str(self.sda).strip('board.')

        self.log_txn(fname,"MCU UID: "+str(self.mcu_uid))
        self.log_txn(fname,"I2C freq/timeout "+str(self.frequency)+"/"+str(self.timeout))

        self.bosmang_lok = None
        if self.bosmang:
            self.add_ppd(self.bosmang)
            self.ppds[0].bosmang = True
            self.bosmang_lok = True
            self.log_txn(fname,'>>>  BOSMANG set, lok  <<<',hex(self.bosmang))
            self.qry_ppds()

    def log_txn(self, fname, message, hexaddr=None, msg=None):
        """Wrapper for logger."""
        id_str = type(self).__name__[2]+" "+str(hexaddr or '    ')
        logger.info('%-6s %-27s %-9s %s' % (id_str, message+str(msg or ''), fname, self.i2c_str))

    def add_ppd(self,device_address):
        self.ppds.append(PPDevice(controller=self,device_address=device_address))
        self.ppds[0].i2cdevice=I2CDevice(self.i2c,device_address=device_address,probe=False)

    def i2c_scan(self):
        """Scans the I2C bus and creates I2CDevice objects for each I2C peripheral."""
        fname='i2c_scan'
        while not self.i2c.try_lock():
            pass
        self.log_txn(fname,">>>  SCANNING I2C bus  <<<")

        for addr in self.i2c.scan():
            if not any(d.device_address == addr for d in chain(self.ppds,self.noident,self.othrdev)):
                self.noident.append(UNDevice(controller=self,device_address=addr))
                self.noident[-1].i2cdevice=I2CDevice(self.i2c,device_address=addr,probe=False)
                self.log_txn(fname,"added I2C peripheral",hex(addr))
        self.i2c.unlock()
        return True

    def idf_ppds(self):
        """Identifies PPDs from among all unidentified I2C peripherals.
        I2CDevice objects for non-PPD I2C peripherals are eventually discared."""
        fname='idf_ppds'
        index = 0
        while index < len(self.noident):
            addr = self.noident[index].device_address
            msg = bytearray(REG_VAL_LEN['CLR'])
            self.log_txn(fname,"querying I2C peripheral",hex(addr))
            with self.noident[index].i2cdevice as i2cd_unident:
                try:
                    i2cd_unident.write_then_readinto(REG_CODE['CLR'],msg)
                    """Clear the i2c peripheral's TX FIFO"""
                except OSError:
                    pass
                msg = bytearray(len(ID_CODE))
                try:
                    i2cd_unident.write_then_readinto(REG_CODE['IDF'],msg)
                except OSError:
                    self.log_txn(fname,"WRITE FAILED",hex(addr))
                if msg == ID_CODE:
                    self.ppds.append(PPDevice(controller=self,device_address=addr))
                    self.ppds[-1].i2cdevice = i2cd_unident
                    self.ppds[-1].lastonline=int(datetime.now().timestamp())
                    del self.noident[index]
                    self.log_txn(fname,">>>   ADDED PPDevice   <<<",hex(addr))
                else:
                    self.noident[index].retries += 1
                    self.log_txn(fname,"ID FAILED on try ",hex(addr),self.noident[index].retries)
                    if self.noident[index].retries >= self.noident[index].retries_max:
                        self.log_txn(fname,"max retries; releasing",hex(addr))
                        self.othrdev.append(self.noident.pop(index))
                        del self.othrdev[-1].i2cdevice
                    else:
                        index += 1
            if msg == ID_CODE:
                self.qry_ppds([self.ppds[-1]])

    def add_ppds(self):
        """This class is a wrapper for `i2c_scan` + `idf_ppds`."""
        fname='add_ppds'
        self.log_txn(fname,'Auto-adding PPDevices')
        self.i2c_scan()
        if self.noident:
            self.log_txn(fname,"found new peripherals: ",'',len(self.noident))
            self.idf_ppds()

    def qry_ppds(self,ppds=None):
        """Queries PPDs for their essential metadata & stats; queries all by default.
           Updates bosmang status if setting not locked on controller.
           Note that certain PPD metadata, once set, can be changed only via command."""
        fname='qry_ppds'
        #self.log_txn(fname,'    function called')
        for ppd in ppds or self.ppds:
            #self.log_txn(fname,'current bosmang: ',None,hex(self.bosmang) if self.bosmang is not None else 'None')
            if not self.bosmang_lok:
                ppd.bosmang   = ppd.get_bos()
            ppd.timestamp = ppd.get_tim()
            if ppd.bosmang and ppd.timestamp:
                self.set_rtc(ppd.timestamp)
                if not self.bosmang:
                    self.bosmang  = ppd.device_address
                    self.log_txn(fname,'>>>  BOSMANG assigned  <<<',hex(self.bosmang))
                elif self.bosmang != ppd.device_address:
                    self.bosmang  = ppd.device_address
                    self.log_txn(fname,'>>>  BOSMANG changed!  <<<',hex(self.bosmang))
            if not ppd.uart_rx:
                ppd.uart_rx   = ppd.get_urx()
            if not ppd.uart_tx:
                ppd.uart_tx   = ppd.get_utx()
            if not ppd.pen:
                ppd.PEN       = ppd.get_pen()
            if not ppd.hostname:
                hos = ppd.get_hos()
                if hos:
                    ppd.hostname = hos
            if not ppd.utcoffset:
                ppd.utcoffset = ppd.get_tzn()
            ppd.loadavg       = ppd.get_lod()
            ppd.uptime        = ppd.get_upt()

    def png_ppds(self,  ppds=[] , register_names=None):
        """Pings PPDs for queued commands, register values; pings all PPDs by default,
           or a list of ppds, in both cases starting with bosmang."""
        fname='png_ppds'
        if self.bosmang and self.ppds:
            if self.ppds[0] != self.get_ppd(device_address=self.bosmang):
                self.ppds.insert(0, self.ppds.pop(self.ppds.index(self.get_ppd(device_address=self.bosmang))))

        if self.bosmang and not self.get_ppd(device_address=self.bosmang) in ppds:
            ppds = [self.get_ppd(device_address=self.bosmang)] + ppds

        self.log_txn(fname,'>>> Pinging PPDevices <<<')
        for ppd in ppds[1:] or self.ppds:
            ppd.command   = ppd.get_cmd()
            if isinstance(ppd.command, bytearray):
                self.cmd_hndlr(ppd)

    def set_rtc(self,timestamp):
        """Set the MCU's realtime clock."""
        fname='set_rtc'
        self.clock.datetime = datetime.fromtimestamp(timestamp).timetuple()
        self.log_txn(fname,str(datetime.now()))

    def get_ppd(self, device_address=None, hostname=None):
        """Get a PPDevice object by device_address or hostname."""
        if device_address:
            dlist = list(filter(lambda d: d.device_address == device_address, self.ppds))
            if dlist:
                return dlist[0]
        if hostname:
            dlist = list(filter(lambda d: d.hostname == hostname, self.ppds))
            if dlist:
                return dlist[0]
        return None

    def cmd_hndlr(self, ppd):
        fname='cmd_hndlr'
        """Handle a command sent by a PPDevice."""
        if self.get_ppd(device_address=ppd.command[1]):
            if ppd.command[0] == CMD_CODE['FLICKER']:
                #self.log_txn(fname,str(ppd.command),hex(ppd.command[1]))
                self.get_ppd(device_address=ppd.command[1]).set_flkr(ppd.command[2])
        else:
            self.log_txn(fname,"No device "+hex(ppd.command[1]))
        ppd.command = None