"""
dzcb-simple: Simplified DMR Zone Channel Builder for Anytone 878/890
"""

__version__ = "2.0.0"
__author__ = "Joe (AF1E)"

# Frequency ranges (in MHz)
# VHF Commercial: 136-174 MHz
# UHF Commercial: 400-480 MHz (sometimes 400-520)
# Amateur 220: 219-225 MHz (not common, but some radios support it)

FREQUENCY_RANGES = {
    "VHF_COMMERCIAL": (136.0, 174.0),
    "UHF_COMMERCIAL": (400.0, 480.0),
    "AMATEUR_220": (219.0, 225.0),
}


def is_frequency_in_range(freq_mhz, range_name):
    """Check if frequency is within a named range."""
    if range_name not in FREQUENCY_RANGES:
        return False
    low, high = FREQUENCY_RANGES[range_name]
    return low <= freq_mhz <= high
