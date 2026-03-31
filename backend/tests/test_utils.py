"""Tests for utils module."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.utils.logging import get_logger, setup_logging


class TestLogging:
    """Tests for logging utilities."""

    def test_setup_logging_returns_logger(self):
        """Test setup_logging returns a logger."""
        logger = setup_logging(level=logging.INFO)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "pocket_studio"

    def test_setup_logging_with_custom_format(self):
        """Test setup_logging with custom format string."""
        format_str = "%(levelname)s: %(message)s"
        logger = setup_logging(level=logging.DEBUG, format_string=format_str)
        assert isinstance(logger, logging.Logger)

    def test_setup_logging_default_level(self):
        """Test setup_logging returns a logger."""
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "pocket_studio"

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom level."""
        logger = setup_logging(level=logging.DEBUG)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "pocket_studio"

    def test_get_logger_returns_child_logger(self):
        """Test get_logger returns a child logger."""
        logger = get_logger("test")
        assert logger.name == "pocket_studio.test"

    def test_get_logger_returns_correct_type(self):
        """Test get_logger returns a Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
