"""
Generate Anytone CPS CSV files

Supported radios:
- Anytone 878UVii (CPS 1.21)
- Anytone 890 (Latest CPS)
"""
import csv
import enum
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from dzcb import FREQUENCY_RANGES
from dzcb.models import (
    AnalogChannel,
    Bandwidth,
    Channel,
    Codeplug,
    DigitalChannel,
    Power,
    uniquify_contacts,
)

logger = logging.getLogger(__name__)

# Constants
NAME_MAX = 16
SCANLIST_MAX = 50
OFF = "Off"
ON = "On"
NONE = "None"


class DMRMode(enum.IntEnum):
    """DMR Mode values"""
    SIMPLEX = 0
    REPEATER = 1


class TXPermit(enum.Enum):
    """TX Permit values"""
    ALWAYS = "Always"
    SAME_COLOR = "Same Color Code"


def format_frequency(freq: float) -> str:
    """Format frequency to 5 decimal places"""
    return f"{freq:.5f}"


def get_dmr_mode(channel: DigitalChannel) -> str:
    """Determine DMR mode based on offset"""
    return str(DMRMode.REPEATER.value if abs(channel.offset) > 0 else DMRMode.SIMPLEX.value)


def get_tx_permit(channel: DigitalChannel) -> str:
    """Determine TX permit based on offset"""
    return TXPermit.SAME_COLOR.value if abs(channel.offset) > 0 else TXPermit.ALWAYS.value


# ============================================================================
# Anytone 878 UVii Field Definitions (CPS 1.21)
# ============================================================================

CHANNEL_FIELDS_878 = {
    "No.": None,
    "Channel Name": None,
    "Receive Frequency": None,
    "Transmit Frequency": None,
    "Channel Type": None,
    "Transmit Power": "High",
    "Band Width": "25K",
    "CTCSS/DCS Decode": OFF,
    "CTCSS/DCS Encode": OFF,
    "Contact": "",
    "Contact Call Type": "Group Call",
    "Contact TG/DMR ID": "0",
    "Radio ID": "",
    "Busy Lock/TX Permit": "Always",
    "Squelch Mode": "Carrier",
    "Optional Signal": OFF,
    "DTMF ID": "1",
    "2Tone ID": "1",
    "5Tone ID": "1",
    "PTT ID": OFF,
    "Color Code": "1",
    "Slot": "1",
    "Scan List": NONE,
    "Receive Group List": NONE,
    "PTT Prohibit": OFF,
    "Reverse": OFF,
    "Simplex TDMA": OFF,
    "Slot Suit": OFF,
    "AES Digital Encryption": "Normal Encryption",
    "Digital Encryption": OFF,
    "Call Confirmation": OFF,
    "Talk Around(Simplex)": OFF,
    "Work Alone": OFF,
    "Custom CTCSS": "251.1",
    "2TONE Decode": "0",
    "Ranging": OFF,
    "Through Mode": OFF,
    "Digi APRS RX": OFF,
    "Analog APRS PTT Mode": OFF,
    "Digital APRS PTT Mode": OFF,
    "APRS Report Type": OFF,
    "Digital APRS Report Channel": "1",
    "Correct Frequency[Hz]": "0",
    "SMS Confirmation": OFF,
    "Exclude Channel From Roaming": "0",
    "DMR MODE": "0",
    "DataACK Disable": "0",
    "R5toneBot": "0",
    "R5ToneEot": "0",
}

ZONE_FIELDS_878 = {
    "No.": None,
    "Zone Name": None,
    "Zone Channel Member": None,
    "Zone Channel Member RX Frequency": None,
    "Zone Channel Member TX Frequency": None,
    "A Channel": None,
    "A Channel RX Frequency": None,
    "A Channel TX Frequency": None,
    "B Channel": None,
    "B Channel RX Frequency": None,
    "B Channel TX Frequency": None,
}

SCANLIST_FIELDS_878 = {
    "No.": None,
    "Scan List Name": None,
    "Scan Channel Member": None,
    "Scan Channel Member RX Frequency": None,
    "Scan Channel Member TX Frequency": None,
    "Scan Mode": OFF,
    "Priority Channel Select": "Priority Channel Select1",
    "Priority Channel 1": "Current Channel",
    "Priority Channel 1 RX Frequency": "",
    "Priority Channel 1 TX Frequency": "",
    "Priority Channel 2": OFF,
    "Priority Channel 2 RX Frequency": "",
    "Priority Channel 2 TX Frequency": "",
    "Revert Channel": "Selected",
    "Look Back Time A[s]": "2.0",
    "Look Back Time B[s]": "3.0",
    "Dropout Delay Time[s]": "3.1",
    "Dwell Time[s]": "3.1",
}

# ============================================================================
# Anytone 890 Field Definitions (Latest CPS)
# ============================================================================

CHANNEL_FIELDS_890 = {
    # Core fields (1-5)
    "No.": None,
    "Channel Name": None,
    "Receive Frequency": None,
    "Transmit Frequency": None,
    "Channel Type": None,
    
    # Basic settings (6-9)
    "Transmit Power": "High",
    "Bandwidth": "25K",
    "CTCSS/DCS Decode": OFF,
    "CTCSS/DCS Encode": OFF,
    
    # Contact/Talkgroup (10-13) - Note renamed fields
    "Contact/TG": "",
    "Contact/TG Call Type": "Group Call",
    "Contact/TG TG/DMR ID": "0",
    "Radio ID": "",
    
    # DMR settings (14-24)
    "Busy Lock/TX Permit": "Always",
    "Squelch Mode": "Carrier",
    "Optional Signal": OFF,
    "DTMF ID": "1",
    "2Tone ID": "1",
    "5Tone ID": "1",
    "PTT ID": OFF,
    "RX Color Code": "1",  # Renamed from "Color Code"
    "Slot": "1",
    "Scan List": NONE,
    "Receive Group List": NONE,
    
    # Channel behavior (25-33)
    "PTT Prohibit": OFF,
    "Reverse": OFF,
    "Digital Duplex": OFF,  # Renamed from "Simplex TDMA"
    "Slot Suit": OFF,
    "AES Encryption Key": "Normal Encryption",  # Renamed
    "Digital Encryption": OFF,
    "Call Confirmation": OFF,
    "Talk Around(Simplex)": OFF,
    "Work Alone": OFF,
    
    # Tone/Signal (34-36)
    "Custom CTCSS": "251.1",
    "2Tone Decode": "0",
    "Ranging": OFF,
    
    # APRS (37-42)
    "Idle TX": OFF,
    "APRS RX": OFF,
    "Analog APRS PTT Mode": OFF,
    "Digital APRS PTT Mode": OFF,
    "APRS Report Type": OFF,
    "Digital APRS Report Channel": "1",
    
    # Advanced (43-52)
    "Correct Frequency[Hz]": "0",
    "SMS Confirmation": OFF,
    "Exclude channel from roaming": "0",
    "DMR Mode": "0",
    "DataACK Disable": "0",
    "5Tone BOT ID": "0",
    "5Tone EOT ID": "0",
    "Auto Scan": "0",
    "Ana APRS Mute": "0",
    "Send Talker Alias": "0",
    
    # 890-specific (53-65)
    "AnaAprsTxPath": "0",
    "ARC4": "0",
    "ex_emg_kind": "0",
    "Rpga_Mdc": "0",
    "DisturEn": "0",
    "DisturFreq": "0",
    "dmr_crc_ignore": "0",
    "compand": "0",
    "tx_talkalaes": "0",
    "dup_call": "0",
    "tx_int": "0",
    "BtRxState": "0",
    "idle_tx": "0",
    
    # NXDN (66-77) - All defaults for DMR operation
    "nxdn_wn": "0",
    "NxdnRpga": "0",
    "nxdnSqCon": "0",
    "NxdnTxBusy": "0",
    "NxDnPttId": "0",
    "EnRan": "0",
    "DeRan": "0",
    "NxdnEncry": "0",
    "NxdnGroupId": "0",
    "NxdnIdNum": "0",
    "NxdnStateNum": "0",
    "txcc": "1",
}

ZONE_FIELDS_890 = {
    "No.": None,
    "Zone Name": None,
    "Zone Channel Member": None,
    "Zone Channel Member RX Frequency": None,
    "Zone Channel Member TX Frequency": None,
    "A Channel": None,
    "A Channel RX Frequency": None,
    "A Channel TX Frequency": None,
    "B Channel": None,
    "B Channel RX Frequency": None,
    "B Channel TX Frequency": None,
    "Zone Hide ": "0",  # NEW in 890 (note trailing space!)
}

SCANLIST_FIELDS_890 = SCANLIST_FIELDS_878  # Same as 878

# TalkGroups format (same for both radios)
TALKGROUP_FIELDS = ("No.", "Radio ID", "Name", "Call Type", "Call Alert")

# ============================================================================
# Radio Configurations
# ============================================================================

SUPPORTED_RADIOS = {
    "878": {
        "name": "Anytone 878UVii",
        "version": "CPS 1.21",
        "expand_members": True,
        "frequency_ranges": (
            FREQUENCY_RANGES["VHF_COMMERCIAL"],
            FREQUENCY_RANGES["UHF_COMMERCIAL"],
        ),
        "channel_fields": CHANNEL_FIELDS_878,
        "zone_fields": ZONE_FIELDS_878,
        "scanlist_fields": SCANLIST_FIELDS_878,
        "talkgroup_fields": TALKGROUP_FIELDS,
    },
    "890": {
        "name": "Anytone 890",
        "version": "Latest",
        "expand_members": True,
        "frequency_ranges": (
            FREQUENCY_RANGES["VHF_COMMERCIAL"],
            FREQUENCY_RANGES["UHF_COMMERCIAL"],
        ),
        "channel_fields": CHANNEL_FIELDS_890,
        "zone_fields": ZONE_FIELDS_890,
        "scanlist_fields": SCANLIST_FIELDS_890,
        "talkgroup_fields": TALKGROUP_FIELDS,
    },
}


# ============================================================================
# Conversion Functions
# ============================================================================

def format_member_list(members: Tuple[Channel, ...], list_name: str, expand: bool = False) -> Dict[str, str]:
    """Format a list of channel members for zone or scanlist"""
    result = {
        list_name: "|".join(m.short_name for m in members)
    }
    
    if expand:
        result.update({
            f"{list_name} RX Frequency": "|".join(
                format_frequency(m.frequency) for m in members
            ),
            f"{list_name} TX Frequency": "|".join(
                format_frequency(m.tx_frequency) for m in members
            ),
        })
    
    return result


def contact_to_dict(index: int, contact) -> Dict[str, str]:
    """Convert Contact to TalkGroups CSV row"""
    return {
        "No.": str(index + 1),
        "Radio ID": str(contact.dmrid),
        "Name": contact.name,
        "Call Type": f"{contact.kind.value} Call",
        "Call Alert": NONE,
    }


def analog_channel_to_dict(channel: AnalogChannel, radio_id: str = "878") -> Dict[str, str]:
    """Convert AnalogChannel to partial dict (radio-independent)"""
    # Field name differs between radios
    aprs_rx_field = "Digi APRS RX" if radio_id == "878" else "APRS RX"
    
    d = {
        "CTCSS/DCS Decode": channel.tone_decode or OFF,
        "CTCSS/DCS Encode": channel.tone_encode or OFF,
        "Squelch Mode": "CTCSS/DCS" if channel.tone_decode else "Carrier",
        "Busy Lock/TX Permit": OFF,
        
        # APRS fields (common to both radios)
        aprs_rx_field: channel.aprs_rx,
        "Analog APRS PTT Mode": channel.aprs_ptt_mode,
        "APRS Report Type": channel.aprs_report_type,
        "Digital APRS Report Channel": channel.aprs_report_channel,
    }
    
    # Add 890-specific APRS fields
    if radio_id == "890":
        d["Ana APRS Mute"] = channel.aprs_mute
        d["AnaAprsTxPath"] = channel.aprs_tx_path
        d["Digital APRS PTT Mode"] = OFF  # 890 has this field, 878 has it elsewhere
    else:
        # 878 has "Digital APRS PTT Mode" in main fields
        d["Digital APRS PTT Mode"] = OFF
    
    return d


def digital_channel_to_dict(channel: DigitalChannel, radio_id: str = "878") -> Dict[str, str]:
    """Convert DigitalChannel to partial dict"""
    # Field names differ between 878 and 890
    if radio_id == "890":
        color_field = "RX Color Code"
        contact_field = "Contact/TG"
        contact_type_field = "Contact/TG Call Type"
        contact_id_field = "Contact/TG TG/DMR ID"
        duplex_field = "Digital Duplex"
    else:
        color_field = "Color Code"
        contact_field = "Contact"
        contact_type_field = "Contact Call Type"
        contact_id_field = "Contact TG/DMR ID"
        duplex_field = "Simplex TDMA"
    
    d = {
        color_field: str(channel.color_code),
        "Busy Lock/TX Permit": get_tx_permit(channel),
        "DMR MODE" if radio_id == "878" else "DMR Mode": get_dmr_mode(channel),
        duplex_field: OFF if abs(channel.offset) > 0 else ON,
    }
    
    # Add "Through Mode" for 878 only
    if radio_id == "878":
        d["Through Mode"] = OFF if abs(channel.offset) > 0 else ON
    
    # Add talkgroup info if present
    if channel.talkgroup:
        d.update({
            contact_field: channel.talkgroup.name,
            contact_type_field: f"{channel.talkgroup.kind.value} Call",
            contact_id_field: str(channel.talkgroup.dmrid),
            "Slot": str(channel.talkgroup.timeslot.value),
        })
    
    # Add grouplist if present
    if channel.grouplist:
        d["Receive Group List"] = channel.grouplist.name
    
    return d


def channel_to_dict(index: int, channel: Channel, codeplug: Codeplug, radio_id: str = "878") -> Dict[str, str]:
    """Convert any Channel to full CSV row dict"""
    # Start with common fields
    d = {
        "No.": str(index + 1),
        "Channel Name": channel.short_name,
        "Receive Frequency": format_frequency(channel.frequency),
        "Transmit Frequency": format_frequency(channel.tx_frequency),
        "Channel Type": "A-Analog" if isinstance(channel, AnalogChannel) else "D-Digital",
        "Transmit Power": channel.power.value,
        "PTT Prohibit": ON if channel.rx_only else OFF,
    }
    
    # Add bandwidth
    bw_value = channel.bandwidth.value if isinstance(channel, AnalogChannel) else "12.5"
    if radio_id == "878":
        d["Band Width"] = f"{bw_value}K"
    else:  # 890
        d["Bandwidth"] = f"{bw_value}K"
    
    # Add scanlist
    scanlist_field = "Scan List"
    if channel.scanlist:
        d[scanlist_field] = channel.scanlist.name
    else:
        d[scanlist_field] = NONE
    
    # Add type-specific fields
    if isinstance(channel, AnalogChannel):
        d.update(analog_channel_to_dict(channel, radio_id))
    else:
        d.update(digital_channel_to_dict(channel, radio_id))
    
    return d


def zone_to_dict(index: int, zone, expand: bool = False) -> Dict[str, str]:
    """Convert Zone to CSV row"""
    d = {
        "No.": str(index + 1),
        "Zone Name": zone.name,
    }
    
    # Add channel members
    d.update(format_member_list(
        zone.unique_channels,
        "Zone Channel Member",
        expand,
    ))
    
    # Add A and B channel (first channel in zone)
    if zone.unique_channels:
        for channel_name in ("A Channel", "B Channel"):
            d.update(format_member_list(
                (zone.unique_channels[0],),
                channel_name,
                expand,
            ))
    
    return d


def scanlist_to_dict(index: int, scanlist, expand: bool = False) -> Dict[str, str]:
    """Convert ScanList to CSV row"""
    d = {
        "No.": str(index + 1),
        "Scan List Name": scanlist.name,
    }
    
    # Limit to SCANLIST_MAX channels
    channels = scanlist.unique_channels[:SCANLIST_MAX]
    
    d.update(format_member_list(
        channels,
        "Scan Channel Member",
        expand,
    ))
    
    return d


# ============================================================================
# Output Generation
# ============================================================================

def generate_codeplug(codeplug: Codeplug, output_dir: Path, radio_id: str = "878"):
    """
    Generate Anytone CSV files for the specified radio
    
    Args:
        codeplug: Codeplug object with all data
        output_dir: Directory to write CSV files
        radio_id: Radio identifier ("878" or "890")
    """
    if radio_id not in SUPPORTED_RADIOS:
        raise ValueError(f"Unknown radio: {radio_id}. Supported: {list(SUPPORTED_RADIOS.keys())}")
    
    radio_config = SUPPORTED_RADIOS[radio_id]
    radio_name = radio_config["name"]
    
    logger.info(f"Generating {radio_name} codeplug...")
    
    # Filter channels by frequency range
    filtered_cp = codeplug.filter_frequency_ranges(radio_config["frequency_ranges"])
    
    # Create output directory
    radio_dir = Path(output_dir) / radio_id
    radio_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate TalkGroups.CSV
    tg_file = radio_dir / "TalkGroups.CSV"
    with tg_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=radio_config["talkgroup_fields"])
        writer.writeheader()
        for idx, contact in enumerate(uniquify_contacts(filtered_cp.contacts)):
            writer.writerow(contact_to_dict(idx, contact))
    
    logger.info(f"  Wrote {len(filtered_cp.contacts)} contacts to {tg_file.name}")
    
    # Generate Channel.CSV
    channel_file = radio_dir / "Channel.CSV"
    with channel_file.open("w", newline="", encoding="utf-8") as f:
        # Get all field names from the radio config
        all_fields = list(radio_config["channel_fields"].keys())
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        
        for idx, channel in enumerate(filtered_cp.channels):
            # Start with defaults
            row = radio_config["channel_fields"].copy()
            # Update with channel data
            row.update(channel_to_dict(idx, channel, filtered_cp, radio_id))
            writer.writerow(row)
    
    logger.info(f"  Wrote {len(filtered_cp.channels)} channels to {channel_file.name}")
    
    # Generate Zone.CSV
    zone_file = radio_dir / "Zone.CSV"
    with zone_file.open("w", newline="", encoding="utf-8") as f:
        all_fields = list(radio_config["zone_fields"].keys())
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        
        for idx, zone in enumerate(filtered_cp.zones):
            row = radio_config["zone_fields"].copy()
            row.update(zone_to_dict(idx, zone, radio_config["expand_members"]))
            writer.writerow(row)
    
    logger.info(f"  Wrote {len(filtered_cp.zones)} zones to {zone_file.name}")
    
    # Generate ScanList.CSV
    scanlist_file = radio_dir / "ScanList.CSV"
    with scanlist_file.open("w", newline="", encoding="utf-8") as f:
        all_fields = list(radio_config["scanlist_fields"].keys())
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        
        for idx, scanlist in enumerate(filtered_cp.scanlists):
            row = radio_config["scanlist_fields"].copy()
            row.update(scanlist_to_dict(idx, scanlist, radio_config["expand_members"]))
            writer.writerow(row)
    
    logger.info(f"  Wrote {len(filtered_cp.scanlists)} scanlists to {scanlist_file.name}")
    logger.info(f"✓ {radio_name} codeplug generated in {radio_dir}")


def generate_all_radios(codeplug: Codeplug, output_dir: Path, radio_ids: List[str] = None):
    """Generate codeplugs for multiple radios"""
    if radio_ids is None:
        radio_ids = ["878", "890"]
    
    for radio_id in radio_ids:
        generate_codeplug(codeplug, output_dir, radio_id)
