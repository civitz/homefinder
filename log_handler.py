import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes log records to the database.

    This handler respects the Python logging module's specification and
    integrates with the DatabaseManager to store log entries.

    Usage:
        from database import DatabaseManager
        from log_handler import DatabaseLogHandler

        db_manager = DatabaseManager()
        handler = DatabaseLogHandler(db_manager)
        logging.getLogger().addHandler(handler)
    """

    def __init__(self, db_manager, level: int = logging.NOTSET):
        """Initialize the handler with a database manager.

        Args:
            db_manager: DatabaseManager instance for storing logs
            level: The logging level threshold (default: NOTSET)
        """
        super().__init__(level)
        self.db_manager = db_manager
        self._initialized = False

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the database.

        Args:
            record: The LogRecord to emit
        """
        try:
            level_name = record.levelname
            source = record.name
            message = self.format(record)
            details = self._get_details(record)

            self.db_manager.add_log(level_name, source, message, details)
        except Exception:
            self.handleError(record)

    def _get_details(self, record: logging.LogRecord) -> Optional[Dict[str, Any]]:
        """Extract additional details from a log record.

        Args:
            record: The LogRecord to extract details from

        Returns:
            Dictionary with additional context or None
        """
        details = {}

        if hasattr(record, "exc_info") and record.exc_info:
            details["exc_info"] = self.formatException(record.exc_info)

        if hasattr(record, "args") and record.args:
            details["args"] = record.args

        if hasattr(record, "funcName"):
            details["funcName"] = record.funcName

        if hasattr(record, "lineno"):
            details["lineno"] = record.lineno

        if hasattr(record, "module"):
            details["module"] = record.module

        if hasattr(record, "thread"):
            details["thread"] = record.thread

        if hasattr(record, "threadName"):
            details["threadName"] = record.threadName

        if hasattr(record, "process"):
            details["process"] = record.process

        if hasattr(record, "processName"):
            details["processName"] = record.processName

        return details if details else None

    def formatException(self, exc_info) -> str:
        """Format exception information for storage.

        Args:
            exc_info: Exception info tuple (type, value, traceback)

        Returns:
            Formatted exception string
        """
        import traceback

        if exc_info:
            return "".join(traceback.format_exception(*exc_info))
        return ""

    def flush(self) -> None:
        """Flush any pending log entries.

        Currently a no-op since database writes are synchronous.
        """
        pass
