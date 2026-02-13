"""
Parse K7ABD format CSV files

K7ABD format files:
- Analog__*.csv: Analog channels
- Digital-Repeaters__*.csv: Digital repeaters with talkgroup matrix
- Digital-Others__*.csv: Digital simplex/other channels
- Talkgroups__*.csv: Talkgroup definitions
"""
import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import attr

from dzcb.models import (
    AnalogChannel,
    Bandwidth,
    Codeplug,
    Contact,
    ContactType,
    DigitalChannel,
    GroupList,
    Power,
    ScanList,
    Talkgroup,
    Timeslot,
    Zone,
)

logger = logging.getLogger(__name__)


def parse_talkgroups(talkgroups_csv: List[str]) -> Dict[str, Contact]:
    """
    Parse Talkgroups CSV file (no header)
    Format: talkgroup_name,dmrid[P]
    Suffix 'P' indicates Private call
    """
    talkgroups = {}
    for line in csv.reader(talkgroups_csv):
        if not line or len(line) < 2:
            continue
        tg_name, tg_id = line[0].strip(), line[1].strip()
        
        # Check for Private call suffix
        ct_type = ContactType.GROUP
        if tg_id.upper().endswith('P'):
            tg_id = tg_id[:-1]
            ct_type = ContactType.PRIVATE
        
        try:
            talkgroups[tg_name] = Contact(
                name=tg_name,
                dmrid=int(tg_id),
                kind=ct_type,
            )
        except ValueError as e:
            logger.warning(f"Skipping invalid talkgroup {tg_name}: {e}")
    
    return talkgroups


def parse_analog_channels(analog_csv: List[str]) -> Dict[str, List[AnalogChannel]]:
    """
    Parse Analog__*.csv file
    Returns dict of zone_name -> list of AnalogChannel
    """
    zones = {}
    reader = csv.DictReader(analog_csv)
    
    for row in reader:
        try:
            # Parse zone name (may have code: "Zone Name;CODE")
            zone_full = row['Zone']
            zone_name, _, code = zone_full.partition(';')
            
            # Parse basic channel info
            name = row['Channel Name']
            rx_freq = float(row['RX Freq'])
            tx_freq = float(row['TX Freq'])
            offset = round(tx_freq - rx_freq, 1)
            
            # Parse settings
            power_str = row.get('Power', 'High')
            power = Power[power_str.upper()] if power_str.upper() in Power.__members__ else Power.HIGH
            
            bandwidth_str = row.get('Bandwidth', '25').rstrip('K')
            if bandwidth_str == '12.5':
                bandwidth = Bandwidth._125
            elif bandwidth_str == '20':
                bandwidth = Bandwidth._20
            else:
                bandwidth = Bandwidth._25
            
            # Parse tones
            tone_decode = row.get('CTCSS Decode', 'Off')
            tone_decode = None if tone_decode.lower() in ('off', '') else tone_decode
            
            tone_encode = row.get('CTCSS Encode', 'Off')
            tone_encode = None if tone_encode.lower() in ('off', '') else tone_encode
            
            # Parse TX prohibit
            tx_prohibit = row.get('TX Prohibit', 'Off').lower() in ('on', 'yes', 'true', '1')
            
            # Parse APRS fields (with defaults if not present)
            aprs_rx = row.get('APRS RX', 'Off')
            aprs_ptt_mode = row.get('APRS PTT Mode', 'Off')
            aprs_report_type = row.get('APRS Report Type', 'Off')
            aprs_report_channel = row.get('APRS Report Channel', '1')
            aprs_mute = row.get('APRS Mute', '0')
            aprs_tx_path = row.get('APRS TX Path', '0')
            
            channel = AnalogChannel(
                name=name,
                code=code or None,
                frequency=rx_freq,
                offset=offset,
                power=power,
                bandwidth=bandwidth,
                tone_decode=tone_decode,
                tone_encode=tone_encode,
                rx_only=tx_prohibit,
                aprs_rx=aprs_rx,
                aprs_ptt_mode=aprs_ptt_mode,
                aprs_report_type=aprs_report_type,
                aprs_report_channel=aprs_report_channel,
                aprs_mute=aprs_mute,
                aprs_tx_path=aprs_tx_path,
            )
            
            zones.setdefault(zone_name, []).append(channel)
            
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping analog channel {row.get('Channel Name', '?')}: {e}")
    
    return zones


def parse_digital_others(digital_csv: List[str], talkgroups: Dict[str, Contact]) -> Dict[str, List[DigitalChannel]]:
    """
    Parse Digital-Others__*.csv file
    Returns dict of zone_name -> list of DigitalChannel
    """
    zones = {}
    reader = csv.DictReader(digital_csv)
    
    for row in reader:
        try:
            # Parse zone name
            zone_full = row.get('Zone Name', row.get('Zone', ''))
            zone_name, _, code = zone_full.partition(';')
            
            # Parse channel info
            name = row['Channel Name']
            rx_freq = float(row['RX Freq'])
            tx_freq = float(row['TX Freq'])
            offset = round(tx_freq - rx_freq, 1)
            
            # Parse settings
            power_str = row.get('Power', 'High')
            power = Power[power_str.upper()] if power_str.upper() in Power.__members__ else Power.HIGH
            
            color_code = int(row.get('Color Code', 1))
            
            # Parse talkgroup
            tg_name = row['Talk Group']
            timeslot_str = row.get('TimeSlot', '1')
            timeslot = Timeslot(int(timeslot_str))
            
            if tg_name not in talkgroups:
                logger.warning(f"Channel '{name}' references unknown talkgroup '{tg_name}', skipping")
                continue
            
            talkgroup = Talkgroup(
                name=talkgroups[tg_name].name,
                dmrid=talkgroups[tg_name].dmrid,
                kind=talkgroups[tg_name].kind,
                timeslot=timeslot,
            )
            
            channel = DigitalChannel(
                name=name,
                code=code or None,
                frequency=rx_freq,
                offset=offset,
                power=power,
                color_code=color_code,
                talkgroup=talkgroup,
            )
            
            zones.setdefault(zone_name, []).append(channel)
            
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping digital channel {row.get('Channel Name', '?')}: {e}")
    
    return zones


def parse_digital_repeaters(repeater_csv: List[str], talkgroups: Dict[str, Contact], sort_mode: str = "alpha") -> Dict[str, List[DigitalChannel]]:
    """
    Parse Digital-Repeaters__*.csv file
    This creates one repeater "template" that will be expanded into
    multiple channels (one per talkgroup) during codeplug assembly
    
    Returns dict with zone_name -> list of DigitalChannel with static_talkgroups
    """
    reader = csv.DictReader(repeater_csv)
    repeaters = {}
    
    for row in reader:
        try:
            # Parse zone name
            zone_full = row.pop('Zone Name')
            zone_name, _, code = zone_full.partition(';')
            
            # Parse repeater info
            rx_freq = float(row.pop('RX Freq'))
            tx_freq = float(row.pop('TX Freq'))
            if not rx_freq:
                logger.info(f"Skipping repeater '{zone_name}' with no frequency")
                continue
            
            offset = round(tx_freq - rx_freq, 1)
            
            power_str = row.pop('Power', 'High')
            power = Power[power_str.upper()] if power_str.upper() in Power.__members__ else Power.HIGH
            
            color_code = int(row.pop('Color Code', 1))
            
            # Remove optional comment field
            row.pop('Comment', None)
            
            # Parse talkgroup matrix
            # Remaining columns are talkgroup names with values of "-", "1", or "2"
            static_tgs = []
            for tg_name, timeslot_str in row.items():
                if timeslot_str.strip() == '-':
                    continue
                
                if tg_name not in talkgroups:
                    logger.warning(f"Repeater '{zone_name}' references unknown talkgroup '{tg_name}'")
                    continue
                
                try:
                    timeslot = Timeslot(int(timeslot_str))
                    tg = Talkgroup(
                        name=talkgroups[tg_name].name,
                        dmrid=talkgroups[tg_name].dmrid,
                        kind=talkgroups[tg_name].kind,
                        timeslot=timeslot,
                    )
                    static_tgs.append(tg)
                except (ValueError, KeyError) as e:
                    logger.info(f"Skipping talkgroup {tg_name} on {zone_name}: {e}")
            
            # Create the repeater template
            repeater = DigitalChannel(
                name=zone_name,
                code=code or None,
                frequency=rx_freq,
                offset=offset,
                power=power,
                color_code=color_code,
                static_talkgroups=tuple(sorted(static_tgs, key=lambda tg: tg.name) if sort_mode == "alpha" else static_tgs),
            )
            
            repeaters[zone_name] = [repeater]
            
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping repeater: {e}")
    
    return repeaters


def codeplug_from_k7abd(input_dir: Path, sort_mode: str = "alpha") -> Codeplug:
    """
    Read K7ABD format CSV files from a directory and create a Codeplug
    """
    input_path = Path(input_dir)

    # Parse all talkgroups first
    all_talkgroups = {}
    for tg_file in sorted(input_path.glob('Talkgroups__*.csv')):
        logger.info(f"Reading {tg_file.name}")
        tgs = parse_talkgroups(tg_file.read_text().splitlines())
        all_talkgroups.update(tgs)
        logger.debug(f"Loaded {len(tgs)} talkgroups from {tg_file.name}")

    # Collect zones separately by source type
    other_zones = {}
    repeater_zones = {}

    # Parse analog channels
    for analog_file in sorted(input_path.glob('Analog__*.csv')):
        logger.info(f"Reading {analog_file.name}")
        zones = parse_analog_channels(analog_file.read_text().splitlines())
        for zone_name, channels in zones.items():
            other_zones.setdefault(zone_name, []).extend(channels)
        logger.debug(f"Loaded {sum(len(z) for z in zones.values())} analog channels")

    # Parse digital simplex/others
    for digital_file in sorted(input_path.glob('Digital-Others__*.csv')):
        logger.info(f"Reading {digital_file.name}")
        zones = parse_digital_others(digital_file.read_text().splitlines(), all_talkgroups)
        for zone_name, channels in zones.items():
            other_zones.setdefault(zone_name, []).extend(channels)
        logger.debug(f"Loaded {sum(len(z) for z in zones.values())} digital channels")

    # Parse digital repeaters
    for repeater_file in sorted(input_path.glob('Digital-Repeaters__*.csv')):
        logger.info(f"Reading {repeater_file.name}")
        zones = parse_digital_repeaters(repeater_file.read_text().splitlines(), all_talkgroups, sort_mode)
        for zone_name, channels in zones.items():
            repeater_zones.setdefault(zone_name, []).extend(channels)
        logger.debug(f"Loaded {len(zones)} repeaters")

    # Build codeplug objects
    return build_codeplug(repeater_zones, other_zones, sort_mode)


def build_codeplug(repeater_zones: Dict[str, List], other_zones: Dict[str, List], sort_mode: str = "alpha") -> Codeplug:
    """
    Convert zone->channels dicts into a complete Codeplug with all objects.

    sort_mode controls zone/channel ordering:
      - "alpha": merge all zones and sort alphabetically (original behavior)
      - "repeaters-first": repeater zones first, then other zones, preserving file order
      - "analog-first": other zones first, then repeater zones, preserving file order
    """
    all_contacts = set()
    all_channels = []
    all_grouplists = []
    all_scanlists = []
    all_zones = []

    # Track channel short names for deduplication
    channel_by_shortname = {}

    # Determine zone iteration order based on sort_mode
    if sort_mode == "alpha":
        merged = {}
        merged.update(other_zones)
        for zone_name, channels in repeater_zones.items():
            merged.setdefault(zone_name, []).extend(channels)
        ordered_zones = sorted(merged.items())
    elif sort_mode == "repeaters-first":
        ordered_zones = list(repeater_zones.items()) + list(other_zones.items())
    else:  # analog-first
        ordered_zones = list(other_zones.items()) + list(repeater_zones.items())

    for zone_name, channels in ordered_zones:
        zone_channels_list = []

        # Create scanlist for this zone
        scanlist = ScanList(name=zone_name, channels=())

        for ch in channels:
            # Handle digital repeaters with static talkgroups
            if isinstance(ch, DigitalChannel) and ch.static_talkgroups:
                # Create grouplist for this repeater
                all_contacts.update(ch.static_talkgroups)
                grouplist = GroupList(
                    name=f"{ch.code or ch.name[:5]} TGS",
                    contacts=ch.static_talkgroups,
                )
                all_grouplists.append(grouplist)

                # Expand into one channel per talkgroup
                for tg in ch.static_talkgroups:
                    expanded_ch = attr.evolve(
                        ch,
                        talkgroup=tg,
                        grouplist=grouplist,
                        static_talkgroups=(),
                        name=f"{ch.name} {tg.name}",
                    )
                    zone_channels_list.append(expanded_ch)
                    all_contacts.add(tg)
            else:
                # Regular channel
                if isinstance(ch, DigitalChannel) and ch.talkgroup:
                    all_contacts.add(ch.talkgroup)

                zone_channels_list.append(ch)

        # Deduplicate channels by short name
        final_channels = []
        for ch in zone_channels_list:
            # Check if we need to add dedup suffix
            while channel_by_shortname.get(ch.short_name) not in (ch, None):
                ch = attr.evolve(ch, dedup_key=ch.dedup_key + 1)

            channel_by_shortname[ch.short_name] = ch

            # Attach scanlist
            ch = attr.evolve(ch, scanlist=scanlist)
            final_channels.append(ch)

        # Update scanlist with final channels
        scanlist = attr.evolve(scanlist, channels=tuple(final_channels))
        all_scanlists.append(scanlist)

        # Create zone
        all_zones.append(Zone(
            name=zone_name,
            channels_a=tuple(final_channels),
            channels_b=tuple(final_channels),
        ))

        all_channels.extend(final_channels)

    # Contacts always sorted alphabetically (needed for clean TalkGroups.CSV)
    # Scanlists and zones: sort only in alpha mode, otherwise preserve insertion order
    if sort_mode == "alpha":
        sorted_scanlists = tuple(sorted(all_scanlists, key=lambda s: s.name))
        sorted_zones = tuple(sorted(all_zones, key=lambda z: z.name))
    else:
        sorted_scanlists = tuple(all_scanlists)
        sorted_zones = tuple(all_zones)

    return Codeplug(
        contacts=tuple(sorted(all_contacts, key=lambda c: c.name)),
        channels=tuple(all_channels),
        grouplists=tuple(all_grouplists),
        scanlists=sorted_scanlists,
        zones=sorted_zones,
    )
