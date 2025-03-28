import logging
import time

from isodate import Duration, parse_duration

logger = logging.getLogger(__name__)


class TimeUtil:
    """Utility class for time operations."""

    @staticmethod
    def get_timestamp_ms() -> int:
        """Get the current timestamp in milliseconds."""
        return int(time.time() * 1000)

    @staticmethod
    def parse_iso_duration(duration: str) -> int:
        """Parse the given time duration String and returns the corresponding number of milliseconds.

        Args:
            duration: The time duration to parse. (ISO 8601)

        Returns:
            The number of seconds.
        """

        # Parse the ISO 8601 duration string to a timedelta object
        duration_obj: Duration = parse_duration(duration, as_timedelta_if_possible=False)

        # Convert the duration object to milliseconds
        duration_seconds = int(duration_obj.total_seconds())
        return duration_seconds
