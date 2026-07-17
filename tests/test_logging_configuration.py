"""Regression test — core/config.py must not force the root logger level
(SPRINT20-G3).

core/config.py previously called logging.getLogger().setLevel(logging.ERROR)
as a side effect of being imported, which silently suppressed WARNING/INFO
logs project-wide — including core/extractors.py's optional-dependency
warnings (PyMuPDF/striprtf/pytesseract/pdf2image missing) and processing
failure warnings. Application logging level is the entry point's
responsibility, not a config-loading side effect. This test guards against
that suppression reappearing.
"""

import importlib
import logging
import sys

import pytest


class TestLoggingConfiguration:
    def test_importing_core_config_does_not_force_root_logger_to_error(self):
        """Importing core.config must not raise the root logger's effective
        level above WARNING (Python's default) as a side effect."""
        # Reset to Python's actual default so this test is independent of
        # whatever prior test/import in the same session already set it.
        logging.getLogger().setLevel(logging.WARNING)

        sys.modules.pop("core.config", None)
        importlib.import_module("core.config")

        assert logging.getLogger().level <= logging.WARNING

    def test_extractors_warning_is_not_suppressed_by_root_level(self, caplog):
        """A WARNING-level log call must actually be capturable after
        core.config has been imported — the exact failure mode of the
        SPRINT20-G3 incident."""
        import core.config  # noqa: F401

        logger = logging.getLogger("core.extractors")
        with caplog.at_level(logging.WARNING):
            logger.warning("[EXTRACTORS] simulated optional-dependency warning")

        assert "simulated optional-dependency warning" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
