# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['UNDevice', 'PPDevice', 'PPController', 'ID_CODE', 'REG_CODE', 'CMD_CODE', 'BUF_CLR']

# Cell
from sys import byteorder
import board
import microcontroller
from busio import I2C
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
ID_CODE  = bytearray([ord(c) for c in list('ppdd')])
"""identifier string used by RPi(s) running PP device daemon"""

REG_CODE = {
    'CLR': bytearray([ord('F')]), # request to Flush/clear transmit FIFO
    'IDF': bytearray([ord('I')]), # request to send [str]  ID_CODE
    'BOS': bytearray([ord('B')]), # request to send [bool] Bosmang status
    'TIM': bytearray([ord('T')]), # request to send [int]  dateTime
    'CMD': bytearray([ord('C')]), # request to send [int]  Command
    'HOS': bytearray([ord('H')]), # request to send [str]  Hostname
    'LOD': bytearray([ord('L')]), # request to send [int]  Load
    'TZO': bytearray([ord('Z')]), # request to send [int]  timeZone (sec offset from UTC)
    'PEN': bytearray([ord('P')]), # request to send [int]  MCU pin connected to RPi PEN
    'MSG': bytearray([ord('M')]), # request to receive [int+str] message for display
    'NAM': bytearray([ord('N')]), # request to receive [int+int+str] PPD name
    'ICS': bytearray([ord('S')]), # request to receive [int+str] PPC I2C_str
    'UID': bytearray([ord('U')]), # request to receive [int+bytearray] PPC microcontroller.cpu.uid
    'RPT': bytearray([ord('R')]), # request to receive [int] report data for N PPDs
    'PPD': bytearray([ord('D')]), # request to receive [int+int+str] individual PPD report
    'RBT': bytearray([252]),      # request to REBOOT
    'SDN': bytearray([253]),      # request to SHUTDOWN
    'ONN': bytearray([254]),      # request to POWERON
    'OFF': bytearray([255])}      # request to POWEROFF
"""I2C Register codes for PPDevices"""

CMD_CODE = (
    (  0, 'NOP',        0), # no command, not used
    ( 97, 'OFFLINE',    1), # confirm
    ( 98, 'ONLINE',     1), # confirm
    ( 99, 'DEREGISTER', 1), # confirm
    (100, 'HOSTNAME',   1), # confirm
    (101, 'MIBOSMANG',  1), # confirm

    (225, 'FLICKER',    1), # duration
    (226, 'ROUNDROBIN', 1), # duration
    (227, 'REPORT',     1), # number of PPDs

    (247, 'REBOOT',     1), # confirm
    (248, 'SHUTDOWN',   1), # confirm
    (249, 'POWERON',    1), # confirm
    (250, 'POWEROFF',   1)) # confirm
"""Command code int values, command NAME, number of bytes to expect
   from follow-on request. So as to avoid collisions with ASCII/UTF-8
   control characters & capital letters used by REG_CODE, purely to
   avoid confusion, valid ranges are: 97-122, 225-250. Reserved
   commands, in the higher range, can be used externally only by bosmang."""

BUF_CLR = 16
"""number of bytes to clear from the sender's TX buffer"""

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
        self.command    = None

        self.uart_rx    = None
        """MCU gpio rx for passthru from bosmang console TX"""
        self.uart_tx    = None
        """MCU gpio tx for passthru from bosmang console RX"""
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
        logger.info('%-6s %-27s %-9s %s' % (self.id_str, message+str(msg or ''), fname, self.controller.i2c_str))

    def dcd_cmd(cmd_code=None,cmd_name=None):
        "Decode command codes from cmd_code or cmd_name"
        if device_address:
            clist = list(filter(lambda ctuple: ctuple[0] == cmd_code, self.CMD_CODE))
            if clist:
                return clist[0]
        return None

    def get_hos(self):
        """Ask PPD for its hostname"""
        fname='get_hos'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUF_CLR)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(1)
            try:
                i2cdevice.write_then_readinto(REG_CODE['HOS'],msg)
                """Get the length in bytes of the hostname"""
                msg = bytearray(int.from_bytes(msg, byteorder))
                i2cdevice.readinto(msg)
                self.lastonline=datetime.now()
                self.log_txn(fname,"recvd hostname ",msg.decode())
                return msg.decode()
            except OSError:
                pass
        return None

    def get_tim(self):
        """Ask PPD for its datetime"""
        fname='get_tim'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUF_CLR)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(4)
            try:
                i2cdevice.write_then_readinto(REG_CODE['TIM'],msg)
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
            msg = bytearray(BUF_CLR)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(1)
            try:
                i2cdevice.write_then_readinto(REG_CODE['BOS'],msg)
                self.lastonline=datetime.now()
                self.log_txn(fname,"recvd bosmang status: ",bool(msg.decode()))
                return bool(int.from_bytes(bytes(msg),byteorder))
            except OSError:
                pass
        return None

    def get_cmd(self):
        """Ask PPD for a command (if any)"""
        fname='get_cmd'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUF_CLR)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(1)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CMD'],msg)
                """Get the command code or 0 for no command"""
                cmd_code = int.from_bytes(bytes(msg),byteorder)
                if cmd_code:
                    self.log_txn(fname,"recvd command",msg.decode())
                    #msg = self.dcd_cmd(cmd_code)
                    #i2cdevice.readinto(msg)
                    self.lastonline=datetime.now()
                    return cmd_code,msg.decode()
                else:
                    self.lastonline=datetime.now()
                    self.log_txn(fname,"recvd no command")
                    return 0
            except OSError:
                pass
        return None

    def get_tzn(self):
        """Ask PPD for its timezone (in seconds offset from utc)"""
        fname='get_tzn'
        #self.log_txn(fname,"querying device")
        with self.i2cdevice as i2cdevice:
            msg = bytearray(BUF_CLR)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(3)
            try:
                i2cdevice.write_then_readinto(REG_CODE['TZO'],msg)
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
            msg = bytearray(BUF_CLR)
            try:
                i2cdevice.write_then_readinto(REG_CODE['CLR'],msg)
                """Clear the i2c peripheral's transmit FIFO"""
            except OSError:
                pass
            msg = bytearray(4)
            try:
                i2cdevice.write_then_readinto(REG_CODE['LOD'],msg)
                self.lastonline=datetime.now()
                self.log_txn(fname,"recvd loadavg: ","{:04.2f}".format(float(msg.decode())))
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
        fname='__init__'
        self.scl       = kwargs.pop('scl', board.SCL)
        self.sda       = kwargs.pop('sda', board.SDA)
        self.frequency = kwargs.pop('frequency', 4800)
        self.timeout   = kwargs.pop('timeout', 10000)

        self.i2c       = I2C(scl=self.scl, sda=self.sda, frequency=self.frequency, timeout=self.timeout)

        self.bosmang   = kwargs.pop('bosmang', None)
        """type: int PPDevice device_address selected to recieve datetime & control
           instructions from, have UART connected for passthru, etc. If set, bosmang
           will be the first PPDevice contacted and MCU RTC will be set at the earliest
           possible time."""
        if kwargs:
            raise TypeError('Unepxected kwargs provided: %s' % list(kwargs.keys()))

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

        #TBD: impliment UID if system is not an MCU
        self.mcu_uid = '0x'+''.join(map(str, ['{:0>{w}}'.format( hex(x)[2:], w=2 ) for x in microcontroller.cpu.uid])) or None
        self.i2c_str = str(self.scl).strip('board.')+"/"+str(self.sda).strip('board.')

        self.log_txn(fname,"MCU UID: "+str(self.mcu_uid))
        self.log_txn(fname,"I2C freq/timeout "+str(self.frequency)+"/"+str(self.timeout))

        self.bosmang_lok = None
        if self.bosmang:
            self.ppds.append(PPDevice(controller=self,device_address=self.bosmang))
            self.ppds[0].i2cdevice=i2c_device.I2CDevice(self.i2c,device_address=self.bosmang,probe=False)
            self.ppds[0].bosmang = True
            self.bosmang_lok = True
            self.log_txn(fname,'>>>  BOSMANG set, lok  <<<',hex(self.bosmang))
            self.qry_ppds()

    def log_txn(self, fname, message, hexaddr=None, msg=None):
        """Wrapper for logger."""
        id_str = type(self).__name__[2]+" "+str(hexaddr or '    ')
        logger.info('%-6s %-27s %-9s %s' % (id_str, message+str(msg or ''), fname, self.i2c_str))

    def i2c_scan(self):
        """Scan the I2C bus and create I2CDevice objects for each peripheral."""
        fname='i2c_scan'
        while not self.i2c.try_lock():
            pass
        self.log_txn(fname,">>>  SCANNING I2C bus  <<<")

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
        index = 0
        while index < len(self.noident):
            addr = self.noident[index].device_address
            msg = bytearray(BUF_CLR)
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
                    self.ppds[-1].lastonline=datetime.now()
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
        """Wrapper for `i2c_scan` + `idf_ppds`."""
        fname='add_ppds'
        self.log_txn(fname,'Auto-adding PPDevices')
        self.i2c_scan()
        if self.noident:
            self.log_txn(fname,"found new peripherals: ",'',len(self.noident))
            self.idf_ppds()

    def qry_ppds(self,ppds=None):
        """Ask PPDs for their essential metadata & stats. Updates bosmang status
           if setting not locked on controller.
           Note that certain metadata, once set, can be changed only via command."""
        fname='qry_ppds'
        #self.log_txn(fname,'    function called')
        for ppd in ppds or self.ppds:
            #self.log_txn(fname,'current bosmang: ',None,hex(self.bosmang) if self.bosmang is not None else 'None')
            if not self.bosmang_lok:
                ppd.bosmang   = ppd.get_bos()
            ppd.datetime      = ppd.get_tim()
            if ppd.bosmang and ppd.datetime:
                self.set_rtc(ppd.datetime.timetuple())
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

    def png_ppds(self,ppds=None):
        """Ask PPDs for queued commands & essential stats."""
        fname='png_ppds'
        self.log_txn(fname,'pinging PPDevices')
        for ppd in ppds or self.ppds:
            ppd.command   = ppd.get_cmd()
            ppd.loadavg       = ppd.get_lod()

    def set_rtc(self,timetuple):
        """Set the MCU's realtime clock."""
        fname='set_rtc'
        self.clock.datetime = timetuple
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