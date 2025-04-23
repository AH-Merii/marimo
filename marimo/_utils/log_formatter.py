# Copyright 2024 Marimo. All rights reserved.
# Adapted from tornado.log (Apache 2.0 License)
from __future__ import annotations

import logging
import sys
import inspect
from typing import Any, cast

try:
    import curses
except ImportError:
    curses = None  # type: ignore


def _stderr_supports_color() -> bool:
    try:
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            if curses:
                curses.setupterm()
                if curses.tigetnum("colors") > 0:
                    return True
    except Exception:
        pass
    return False


class LogFormatter(logging.Formatter):
    DEFAULT_FORMAT = (
        "%(color)s[%(levelname)1.1s %(asctime)s]"
        "%(filename_color)s %(filename)s:%(lineno)d%(reset_color)s "
        "%(class_color)s%(classname)s%(reset_color)s"
        "%(function_color)s%(funcName)s()%(reset_color)s - "
        "%(end_color)s%(message)s"
    )
    DEFAULT_DATE_FORMAT = "%y%m%d %H:%M:%S"
    DEFAULT_COLORS = {
        logging.DEBUG: 4,  # Blue
        logging.INFO: 2,  # Green
        logging.WARNING: 3,  # Yellow
        logging.ERROR: 1,  # Red
        logging.CRITICAL: 5,  # Magenta
    }

    def __init__(
        self,
        fmt: str = DEFAULT_FORMAT,
        datefmt: str = DEFAULT_DATE_FORMAT,
        style: str = "%",
        color: bool = True,
        colors: dict[int, int] = DEFAULT_COLORS,
    ) -> None:
        super().__init__(datefmt=datefmt)
        self._fmt = fmt
        self._colors: dict[int, str] = {}
        self._filename_color = "\033[36m"  # Cyan
        self._function_color = "\033[34m"  # Blue
        self._class_color = "\033[35m"  # Magenta
        self._normal = "\033[0m"

        if color and _stderr_supports_color():
            if curses:
                curses.setupterm()
                fg_color = (
                    curses.tigetstr("setaf") or curses.tigetstr("setf") or b""
                )
                for levelno, code in colors.items():
                    self._colors[levelno] = str(
                        curses.tparm(fg_color, code), "ascii"
                    )
                self._normal = str(curses.tigetstr("sgr0") or b"", "ascii")
        else:
            for levelno, code in colors.items():
                self._colors[levelno] = f"\033[2;3{code}m"

    def format(self, record: Any) -> str:
        try:
            record.message = record.getMessage()
        except Exception as e:
            record.message = f"Bad message ({e!r}): {record.__dict__!r}"

        record.asctime = self.formatTime(record, self.datefmt)
        record.color = self._colors.get(record.levelno, "")
        record.end_color = self._normal

        record.filename_color = self._filename_color
        record.function_color = self._function_color
        record.class_color = self._class_color
        record.reset_color = self._normal

        record.classname = self._get_class_name_from_stack(record)

        formatted = self._fmt % record.__dict__

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            lines = [formatted.rstrip()]
            lines.extend(str(ln) for ln in record.exc_text.split("\n"))
            formatted = "\n".join(lines)
        return formatted.replace("\n", "\n    ")

    def _get_class_name_from_stack(self, record: Any) -> str:
        """
        Inspect the call stack to find the class name if possible.
        """
        frame = inspect.currentframe()
        if not frame:
            return ""

        try:
            # Walk back through the frames until we find one matching the logger call
            while frame:
                code = frame.f_code
                if code.co_name == record.funcName:
                    local_self = frame.f_locals.get("self", None)
                    if local_self:
                        return f"{local_self.__class__.__name__} "
                frame = frame.f_back
        except Exception:
            pass
        return ""
