from datetime import time

def get_intersection(time_ranges):
    """
    time_ranges = [(start_time, end_time), (start_time, end_time), ...]
    回傳所有人的共同可上班區間
    """

    if not time_ranges:
        return None, None

    latest_start = max(s for s, _ in time_ranges)
    earliest_end = min(e for _, e in time_ranges)

    # 無交集
    if latest_start >= earliest_end:
        return None, None

    return latest_start, earliest_end

def intersection_time(ranges):
    latest_start = max(r[0] for r in ranges)
    earliest_end = min(r[1] for r in ranges)

    if latest_start >= earliest_end:
        return None, None
    return latest_start, earliest_end
