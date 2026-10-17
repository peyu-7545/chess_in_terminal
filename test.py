import sys

class ANSI_SGR:

    _CODES = {
        "reset": "0",
        "bold": "1",

        "black": "30", "red": "31", "green": "32", "yellow": "33",
        "blue": "34", "magenta": "35", "cyan": "36", "white": "37",
    }

    def __init__(self):
        self.support_ansi = sys.stdout.isatty()

    def __getattr__(self, name):
        if not self.support_ansi:
            return ""

        if name not in self._CODES:
            return ""

        return "\033[" + self._CODES[name] + "m"