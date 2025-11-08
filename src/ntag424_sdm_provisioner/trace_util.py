"""
Tracing utilities for debugging NFC operations and crypto.

Usage:
    from ntag424_sdm_provisioner.trace_util import trace_calls, trace_block
    
    # Trace function calls
    @trace_calls
    def my_function(arg1, arg2):
        return result
    
    # Trace code blocks
    with trace_block("Description"):
        # code here
"""

import logging
import functools
import time
from typing import Any, Callable
from contextlib import contextmanager

log = logging.getLogger(__name__)


def trace_calls(func: Callable) -> Callable:
    """
    Decorator to trace function calls with arguments and return values.
    
    Usage:
        @trace_calls
        def my_function(arg1, arg2):
            return result
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__qualname__}"
        
        # Format arguments
        args_repr = [_format_value(a) for a in args]
        kwargs_repr = [f"{k}={_format_value(v)}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        
        log.debug(f"[TRACE] → {func_name}({signature})")
        
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start_time) * 1000  # ms
            
            result_repr = _format_value(result)
            log.debug(f"[TRACE] ← {func_name} returned {result_repr} ({elapsed:.2f}ms)")
            
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            log.error(f"[TRACE] ✗ {func_name} raised {type(e).__name__}: {e} ({elapsed:.2f}ms)")
            raise
    
    return wrapper


@contextmanager
def trace_block(description: str):
    """
    Context manager to trace a block of code.
    
    Usage:
        with trace_block("Building APDU"):
            apdu = [0x90, 0xC4, ...]
    """
    log.debug(f"[TRACE] >>> {description}")
    start_time = time.perf_counter()
    
    try:
        yield
        elapsed = (time.perf_counter() - start_time) * 1000
        log.debug(f"[TRACE] <<< {description} completed ({elapsed:.2f}ms)")
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        log.error(f"[TRACE] <<< {description} failed: {type(e).__name__}: {e} ({elapsed:.2f}ms)")
        raise


def _format_value(value: Any, max_bytes: int = 32) -> str:
    """Format a value for logging, with special handling for bytes."""
    if isinstance(value, bytes):
        if len(value) <= max_bytes:
            return f"bytes({value.hex()})"
        else:
            return f"bytes({value[:max_bytes].hex()}... {len(value)} bytes)"
    elif isinstance(value, bytearray):
        if len(value) <= max_bytes:
            return f"bytearray({bytes(value).hex()})"
        else:
            return f"bytearray({bytes(value[:max_bytes]).hex()}... {len(value)} bytes)"
    elif isinstance(value, list) and value and isinstance(value[0], int):
        # Looks like APDU data
        if len(value) <= max_bytes:
            return f"[{' '.join(f'{b:02X}' for b in value)}]"
        else:
            return f"[{' '.join(f'{b:02X}' for b in value[:max_bytes])}... {len(value)} bytes]"
    elif hasattr(value, '__class__') and hasattr(value, '__dict__'):
        # Object with attributes
        return f"{value.__class__.__name__}(...)"
    else:
        return repr(value)


def trace_apdu(apdu: list, direction: str = ">>", label: str = ""):
    """
    Log an APDU with nice formatting.
    
    Args:
        apdu: APDU bytes as list
        direction: ">>" for command, "<<" for response
        label: Optional label
    """
    if label:
        log.debug(f"[APDU] {direction} {label}")
    
    # Format as hex string
    hex_str = ' '.join(f'{b:02X}' for b in apdu)
    
    # Break into lines if too long
    if len(hex_str) > 80:
        lines = []
        words = hex_str.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 80:
                lines.append(line)
                line = "       " + word  # Indent continuation
            else:
                line += (" " if line and not line.endswith("       ") else "") + word
        if line:
            lines.append(line)
        
        log.debug(f"[APDU] {direction} {lines[0]}")
        for line in lines[1:]:
            log.debug(f"[APDU]    {line}")
    else:
        log.debug(f"[APDU] {direction} {hex_str}")


def trace_crypto(operation: str, **kwargs):
    """
    Log cryptographic operation details.
    
    Usage:
        trace_crypto("CMAC", 
                    input=data,
                    key=session_mac_key,
                    output=mac)
    """
    log.debug(f"[CRYPTO] {operation}")
    for key, value in kwargs.items():
        formatted = _format_value(value)
        log.debug(f"[CRYPTO]   {key}: {formatted}")


def enable_trace_logging():
    """Enable TRACE level logging for all trace utilities."""
    logging.getLogger(__name__).setLevel(logging.DEBUG)


def disable_trace_logging():
    """Disable TRACE level logging."""
    logging.getLogger(__name__).setLevel(logging.INFO)

