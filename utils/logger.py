
# Minimal logging helpers for chatter + server logs
import logging
_logger = logging.getLogger(__name__)

def chatter(record, msg, level='info'):
    try:
        record.message_post(body=msg)
    except Exception:
        pass
    getattr(_logger, level, _logger.info)(msg)
