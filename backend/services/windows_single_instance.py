"""Small Windows-only guard against duplicate historical collectors."""

import os


class HistoricalCollectorAlreadyRunningError(RuntimeError):
    """Raised when another collector owns the Windows named mutex."""


class WindowsSingleInstanceGuard:
    """Own a named Windows mutex for the lifetime of a collector process."""

    ERROR_ALREADY_EXISTS = 183

    def __init__(self, mutex_name):
        self.mutex_name = mutex_name
        self._handle = None
        self._kernel32 = None

    def __enter__(self):
        if os.name != "nt":
            return self

        import ctypes
        from ctypes import wintypes

        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.CreateMutexW.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        self._kernel32.CreateMutexW.restype = wintypes.HANDLE
        self._kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        self._kernel32.CloseHandle.restype = wintypes.BOOL

        self._handle = self._kernel32.CreateMutexW(
            None,
            False,
            self.mutex_name,
        )
        error_code = ctypes.get_last_error()

        if not self._handle:
            raise ctypes.WinError(error_code)

        if error_code == self.ERROR_ALREADY_EXISTS:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None
            raise HistoricalCollectorAlreadyRunningError(
                "Another historical GTFS collector instance is already running"
            )

        return self

    def __exit__(self, exception_type, exception, traceback):
        if self._handle is not None:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None
        return False
