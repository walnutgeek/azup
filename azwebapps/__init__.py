import re


def guess_location_from_display_name(display_name):
    """
    >>> guess_location_from_display_name("UAE Central")
    'uaecentral'
    >>> guess_location_from_display_name("Southeast Asia (Stage)")
    'southeastasiastage'
    """
    return re.sub(r"[\s()]+", "", display_name).lower()
