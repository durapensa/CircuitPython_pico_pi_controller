# AUTOGENERATED! DO NOT EDIT! File to edit: 20_reports.ipynb (unless otherwise specified).

__all__ = ['ReportData', 'stats_struct']

# Cell

# export
try:
    from adafruit_datetime import datetime
except ModuleNotFoundError:
    from datetime import datetime
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

from CircuitPython_pico_pi_common.codes import *

# Cell
stats_struct = { }

for property_name, common_name in REP_CLI_CATALOG:
    stats_struct[property_name]=None

class ReportData():
    """Instances hold report data for PPDevices. Using this class,
       reports can be generated at any time without querrying PPDevices,
       limited only by available memory.
       Note that hosthame, mcu_uid & ppc_i2c_str are sent to bosmang separately
       as they have variable lengths, and thus are omitted from the stats_struct
       when sent but re-incorporated after the truncated stats_struct is
       received."""
    def __init__(self, ppds):
        self.ppds  = ppds
        self.stats = []

    def log_txn(self, fname, message, hexaddr=None, msg=None, i2c_str=None):
        """Wrapper for logger."""
        id_str = type(self).__name__[0]+" "+str(hexaddr or '    ')
        logger.info('%-6s %-27s %-9s %s' % (id_str, message+str(msg or ''), fname, i2c_str))

    def get_stat(self):
        fname='get_stat'
        for ppd in self.ppds:
            if not any(d.device_address == ppd.device_address for d in self.stats):
                dstats = stats_struct
                dstats['ppc_i2c_str']    = ppd.controller.i2c_str
                dstats['device_address'] = ppd.device_address
                dstats['hostname']       = ppd.hostname
                dstats['lastonline']     = ppd.lastonline
                dstats['loadavg']        = ppd.loadavg
                dstats['uptime']         = ppd.uptime
                dstats['bosmang']        = ppd.bosmang
                dstats['utcoffset']      = ppd.utcoffset
                self.stats.append(dstats)
                self.log_txn(fname,"gathered stats",hex(ppd.device_address),'',ppd.controller.i2c_str)