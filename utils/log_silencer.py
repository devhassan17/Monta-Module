# -*- coding: utf-8 -*-
import logging
import threading
from contextlib import contextmanager

# Thread-local flag so concurrent requests don’t affect each other
_MONTA_SILENCE = threading.local()
_MONTA_SILENCE.enabled = False

class _MontaSilenceFilter(logging.Filter):
    """Drops Monta module logs when the silence flag is enabled."""
    def filter(self, record):
        try:
            if getattr(_MONTA_SILENCE, "enabled", False):
                # Drop EVERY log from this module while silenced
                return False
        except Exception:
            pass
        return True

# Attach the filter to the whole Monta module logger hierarchy once on import
_module_logger = logging.getLogger("odoo.addons.Monta-Module")
_module_logger.addFilter(_MontaSilenceFilter())

# Also attach to likely children (models/services) just in case
logging.getLogger("odoo.addons.Monta-Module.models").addFilter(_MontaSilenceFilter())
logging.getLogger("odoo.addons.Monta-Module.services").addFilter(_MontaSilenceFilter())

@contextmanager
def silence_monta_logs():
    """Context manager: silence Monta logs for the duration of the block."""
    prev = getattr(_MONTA_SILENCE, "enabled", False)
    _MONTA_SILENCE.enabled = True
    try:
        yield
    finally:
        _MONTA_SILENCE.enabled = prev
