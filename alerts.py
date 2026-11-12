import logging

alert_logger = logging.getLogger("alerts")
alert_logger.setLevel(logging.INFO)
alert_logger.propagate = False  # keep alerts.log messages out of the main logger
_handler = logging.FileHandler("alerts.log")
_handler.setFormatter(logging.Formatter("%(asctime)s [ALERT] %(message)s"))
alert_logger.addHandler(_handler)


def send_alert(message: str) -> None:
    """Placeholder alert channel: log to console and alerts.log.
    Email/Slack can be added here later without changing monitor.py."""
    logging.warning("ALERT: %s", message)
    alert_logger.info(message)
