# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['UNDevice', 'PPDevice', 'PPController', 'IDENTITY', 'BUFCLR', 'CLR', 'IDF', 'HOS', 'TIM', 'BOS', 'LOD',
           'TZO', 'PEN']

# Cell
from sys import byteorder, modules
import board
from adafruit_bus_device import i2c_device
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
IDENTITY = bytearray(([ord(c) for c in list('ppdd')]))
"""identifier string used by RPi(s) running PP device daemon"""

BUFCLR = 16
"""number of bytes to clear from the sender's TX buffer"""

CLR = bytearray([ord('C')]) # request clear transmit FIFO
IDF = bytearray([ord('I')]) # request to send [str] identification
HOS = bytearray([ord('H')]) # request to send [str] hostname
TIM = bytearray([ord('T')]) # request to send [int] datetime
BOS = bytearray([ord('B')]) # request to send [bool] bosmang status
LOD = bytearray([ord('L')]) # request to send [int] load
TZO = bytearray([ord('Z')]) # request to send [int] timezone (sec offset from UTC)
PEN = bytearray([ord('P')]) # request to send [int] MCU pin connected to RPi PEN

class UNDevice():
    """Represents an I2C peripheral device unidentified to a `PPController`"""
    def __init__(self, controller, device_address, *argv, **kwargs):
        self.controller  = controller
        self.device_address = device_address
        self.i2cdevice      = None
        """The I2CDevice created by a PPController."""

        self.retries     = 0
        self.retries_max = 4
        """retry count before I2CDevice is considered 'other', i.e. not a PPC device."""

class PPDevice():
    """Represents an I2C peripheral device identified as a `PPDevice`
    and stores data from those hosts."""
    def __init__(self, controller, device_address, *argv, **kwargs):
        self.controller     = controller
        self.device_address = device_address
        self.i2cdevice      = None
        """The I2CDevice created by a PPController."""

        self.lastonline  = None
        """type: datetime A controller time-stamp updated with each successful receive.
           reports & bosmang can decide what to do with this info."""

        """All data below are received *from* the PPC device:"""

        self.bosmang    = None
        """Declaration that device will send datetime & control instructions to controller.
           Only one bosmang per controller please, unless you wanya chaos."""
        self.uart_rx    = None
        """MCU gpio rx for passthru from bosmang console tx"""
        self.uart_tx    = None
        """MCU gpio tx for passthru from bosmang console rx"""
        self.pen        = None
        """MCU gpio connected to RPi pen pin"""

        self.hostname   = None
        self.datetime   = None
        """type: datetime Converted from timestamp, used to send datetime as bosmang &
           to check for datetime skew on other devices."""
        self.utcoffset  = None
        self.loadavg    = None

        self.id_str = type(self).__name__[2]+" "+str(hex(self.device_address))

    def log_txn(self, fname, message, msg=None):
        """Wrapper for logger."""
        logger.info('%-6s %-26s %-9s %s' % (self.id_str, message+str(msg or ''), fname, self.controller.i2c_str))

    def get_hos(self):
        """Ask PPD for its hostname"""
        fname='get_hos'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUFCLR)
            try:
                i2cdevice.write_then_readinto(CLR,msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(1)
            try:
                i2cdevice.write_then_readinto(HOS,msg)
                """Get the length in bytes of the hostname"""
                msg = bytearray(int.from_bytes(msg, byteorder))
                i2cdevice.readinto(msg)
                self.lastonline=datetime.now()
                self.log_txn(fname,"recvd hostname ",msg.decode())
            except OSError:
                pass
        return msg.decode()

    def get_tim(self):
        """Ask PPD for its datetime"""
        fname='get_tim'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUFCLR)
            try:
                i2cdevice.write_then_readinto(CLR,msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(4)
            try:
                i2cdevice.write_then_readinto(TIM,msg)
                self.lastonline=datetime.now()
                self.log_txn(fname,"recvd datetime: ",int.from_bytes(bytes(msg),byteorder))
                return datetime.fromtimestamp((int.from_bytes(bytes(msg),byteorder)))
            except OSError:
                pass
        return None

    def get_bos(self):
        """Ask PPD for its bosmang status (bool)"""
        fname='get_bos'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUFCLR)
            try:
                i2cdevice.write_then_readinto(CLR,msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(1)
            try:
                i2cdevice.write_then_readinto(BOS,msg)
                self.lastonline=datetime.now()
                self.controller.bosmang = self.device_address
                self.log_txn(fname,"recvd bosmang status: ",bool(msg.decode()))
                return bool(int.from_bytes(bytes(msg),byteorder))
            except OSError:
                pass
        return None

    def get_tzn(self):
        """Ask PPD for its timezone (in seconds offset from utc)"""
        fname='get_tzn'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUFCLR)
            try:
                i2cdevice.write_then_readinto(CLR,msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(3)
            try:
                i2cdevice.write_then_readinto(TZO,msg)
                self.lastonline=datetime.now()
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
            msg = bytearray(BUFCLR)
            try:
                i2cdevice.write_then_readinto(CLR,msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(4)
            try:
                i2cdevice.write_then_readinto(LOD,msg)
                self.lastonline=datetime.now()
                self.log_txn(fname,"recvd loadavg: ",msg.decode())
                return msg.decode()
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

class PPController():
    """Represents one of the system's I2C busses and tracks which I2C
    peripherals are `PPDevice`s."""
    def __init__(self, **kwargs):
        self.i2c       = None
        self.scl       = kwargs.pop('scl', board.SCL)
        self.sda       = kwargs.pop('sda', board.SDA)
        self.frequency = kwargs.pop('frequency', 4800)
        self.timeout   = kwargs.pop('timeout', 10000)

        self.bosmang   = kwargs.pop('bosmang', None)
        """type: int PPDevice device_address selected to recieve datetime & control
           instructions from, have UART connected for passthru, etc. If set, bosmang
           will be the first PPDevice contacted and MCU RTC will be set at the earliest
           possible time."""

        self.datetime  = None
        """to receive datetime from bosmang & to check for datetime skew on other devices."""
        self.utcoffset = None
        self.clock     = RTC()

        self.ppds      = []
        """PPDevice objects belonging to a PPController object."""
        self.noident   = []
        """UNDevice objects belonging to a PPController object."""
        self.othrdev   = []
        """UNDevice objects without I2CDevices (address record only)
           recognized as 'other' peripherals"""

        if self.bosmang:
            self.ppds.append(PPDevice(controller=self,device_address=bosmang))
            self.ppds[0].i2cdevice=i2c_device.I2CDevice(self.i2c,device_address=bosmang,probe=False)
            self.bosmang_lok = True
            qry_ppds()

        self.i2c_str = str(self.scl).strip('board.')+"/"+str(self.sda).strip('board.')

    def log_txn(self, fname, message, hexaddr=None, msg=None):
        """Wrapper for logger."""
        id_str = type(self).__name__[2]+" "+str(hexaddr or '    ')
        logger.info('%-6s %-26s %-9s %s' % (id_str, message+str(msg or ''), fname, self.i2c_str))

    def i2c_scan(self):
        """Scan the I2C bus and create I2CDevice objects for each peripheral."""
        fname='i2c_scan'
        while not self.i2c.try_lock():
            pass
        self.log_txn(fname,">>> SCANNING I2C bus <<<")

        for addr in self.i2c.scan():
            if not any(d.device_address == addr for d in chain(self.ppds,self.noident,self.othrdev)):
                self.noident.append(UNDevice(controller=self,device_address=addr))
                self.noident[-1].i2cdevice=i2c_device.I2CDevice(self.i2c,device_address=addr,probe=False)
                self.log_txn(fname,"added I2C peripheral",hex(addr))
        self.i2c.unlock()
        return True

    def idf_ppds(self):
        """Identify PPDs from among all unidentified I2CDevices"""
        fname='idf_ppds'
        i = 0
        while i < len(self.noident):
            addr = self.noident[i].device_address
            self.log_txn(fname,"querying I2C peripheral",hex(addr))
            with self.noident[i].i2cdevice as unident:
                msg = bytearray(BUFCLR)
                try:
                    unident.write_then_readinto(CLR,msg)
                    """Clear the i2c peripheral's TX FIFO"""
                except OSError:
                    pass
                msg = bytearray(len(IDENTITY))
                try:
                    unident.write_then_readinto(IDF,msg)
                except OSError:
                    self.log_txn(fname,"WRITE FAILED",hex(addr))
                if msg == IDENTITY:
                    self.ppds.append(PPDevice(controller=self,device_address=addr))
                    self.ppds[-1].i2cdevice = unident
                    self.ppds[-1].lastonline=datetime.now()
                    del self.noident[i]
                    self.log_txn(fname,">>>  added PPDevice  <<<",hex(addr))
                else:
                    self.noident[i].retries += 1
                    self.log_txn(fname,"ID FAILED on try ",hex(addr),self.noident[i].retries)
                    if self.noident[i].retries >= self.noident[i].retries_max:
                        self.log_txn(fname,"max retries; releasing",hex(addr))
                        self.othrdev.append(self.noident.pop(i))
                        del self.othrdev[-1].i2cdevice
                    else:
                        i += 1

    def add_ppds(self):
        """Wrapper for `i2c_scan` + `idf_ppds`."""
        fname='add_ppds'
        self.log_txn(fname,'    function called')
        self.i2c_scan()
        if self.noident:
            self.log_txn(fname,"found new peripherals: ",'',len(self.noident))
            self.idf_ppds()

    def qry_ppds(self):
        """Ask all PPDs for all of their metadata & stats.
           Note that certain metadata, once set, can be changed only via command."""
        fname='qry_ppds'
        self.log_txn(fname,'    function called')
        for ppd in self.ppds:
            if not ppd.bosmang and not ppd.bosmang_lok:
                ppd.bosmang   = ppd.get_bos()
            ppd.datetime      = ppd.get_tim()
            if ppd.bosmang:
                self.set_rtc(ppd.datetime.timetuple())
            if not ppd.uart_rx:
                ppd.uart_rx   = ppd.get_urx()
            if not ppd.uart_tx:
                ppd.uart_tx   = ppd.get_utx()
            if not ppd.pen:
                ppd.PEN       = ppd.get_pen()
            if not ppd.hostname:
                ppd.hostname  = ppd.get_hos()
            if not ppd.utcoffset:
                ppd.utcoffset = ppd.get_tzn()
            ppd.loadavg       = ppd.get_lod()

    def png_ppds(self):
        """Ask all PPDs for their essential stats."""
        fname='png_ppds'
        self.log_txn(fname,'    function called')
        for ppd in self.ppds:
            ppd.loadavg   = ppd.get_lod()

    def png_bos(self):
        """Ask bosmang for commands."""
        fname='png_bos'
        self.log_txn(fname,'pinging bosmang',hex(self.bosmang))
        cmd = self.get_ppd(device_aaddress=bosmang).get_cmd()

    def set_rtc(self,timetuple):
        """Set the MCU's realtime clock."""
        fname='set_rtc'
        self.clock.datetime = timetuple
        self.log_txn(fname,str(datetime.now()))

    def get_ppd(self, device_address=None, hostname=None):
        """"""
        if device_address:
            dlist = list(filter(lambda d: d.device_address == device_address, self.ppds))
            if dlist:
                return dlist[0]
        if hostname:
            dlist = list(filter(lambda d: d.hostname == hostname, self.ppds))
            if dlist:
                return dlist[0]
        return None