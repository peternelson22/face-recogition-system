from datetime import datetime

def get_relative_time(timestamp):
    """
    Convert a timestamp to a human-readable relative time.

    :param timestamp: ISO format timestamp
    :return: Relative time string
    """
    try:
        # Parse the timestamp
        attendance_time = datetime.fromisoformat(timestamp)

        # Calculate time difference
        now = datetime.now()
        diff = now - attendance_time

        # Convert to total seconds
        total_seconds = diff.total_seconds()

        # Define time intervals
        if total_seconds < 60:
            return f"{int(total_seconds)} second{'s' if total_seconds != 1 else ''} ago"

        minutes = total_seconds / 60
        if minutes < 60:
            return f"{int(minutes)} minute{'s' if minutes != 1 else ''} ago"

        hours = minutes / 60
        if hours < 24:
            return f"{int(hours)} hour{'s' if hours != 1 else ''} ago"

        days = hours / 24
        if days < 30:
            return f"{int(days)} day ago"

        days = hours / 24
        if days < 30:
            return f"{int(days)} day{'s' if days > 1 else ''} ago"

        months = days / 30
        if months < 12:
            return f"{int(months)} month{'s' if months != 1 else ''} ago"

        years = months / 12
        return f"{int(years)} year{'s' if years != 1 else ''} ago"

    except (ValueError, TypeError):
        return "Never"