import numpy as np
from matplotlib.ticker import ScalarFormatter


def eng_format(number, significance):
    if number == 0:
        return '0'
    elif number < 0:
        sign = '-'
    else:
        sign = ''

    exp = int(np.floor(np.log10(abs(number))))
    exp3 = exp - (exp % 3)

    x3 = abs(number) / (10**exp3)

    if exp3 == 0:
        exp3_text = ''
    else:
        exp3_text = 'e%s' % exp3

    format = '%.' + str(significance) + 'f'

    return ('%s' + format + '%s') % (sign, x3, exp3_text)


class FixedOrderFormatter(ScalarFormatter):
    """Format numbers using engineering notation."""
    def __init__(self, format='%.0f', division=1e0):
        ScalarFormatter.__init__(self, useOffset=False, useMathText=True)
        self.format = format
        self.division = division

    def __call__(self, x, pos=None):
        exp = self.orderOfMagnitude
        format = self.format
        if format.endswith('e'):
            format = format[:-1]+'f'
        return format % ((x / self.division) / (10 ** exp))

    def _set_format(self, vmin, vmax):
        pass

    def _set_orderOfMagnitude(self, range):
        exp_r = np.floor(np.log10(range / self.division)) if range!=0 else 0
        locs = np.abs(self.locs)
        val = max(locs[0],locs[-1])
        exp_max = np.floor(np.log10(val / self.division)) if val!=0 else 0
        exp = exp_r if self.offset else exp_max
        if self.format.endswith('f'):
            self.orderOfMagnitude = exp - (exp % 3)
        elif self.format.endswith('e'):
            self.orderOfMagnitude = exp_max
        else:
            self.orderOfMagnitude = 0
