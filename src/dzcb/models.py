"""
Data models for codeplug objects
"""
import enum
from typing import Optional, Tuple

import attr


class Timeslot(enum.IntEnum):
    """DMR Tier II uses 2x30ms timeslots"""
    ONE = 1
    TWO = 2


class ContactType(enum.Enum):
    """DMR Contact types"""
    GROUP = "Group"
    PRIVATE = "Private"


class Power(enum.Enum):
    """Transmit power levels"""
    LOW = "Low"
    MED = "Medium"
    HIGH = "High"
    TURBO = "Turbo"


class Bandwidth(enum.Enum):
    """Channel bandwidth"""
    _125 = "12.5"
    _20 = "20"
    _25 = "25"


@attr.s(frozen=True, auto_attribs=True)
class Contact:
    """A DMR Contact (talkgroup or private call)"""
    name: str
    dmrid: int
    kind: ContactType = ContactType.GROUP


@attr.s(frozen=True, auto_attribs=True)
class Talkgroup(Contact):
    """A DMR Talkgroup with timeslot"""
    timeslot: Timeslot = Timeslot.ONE

    @property
    def name_with_timeslot(self) -> str:
        """Get name with timeslot appended if not already present"""
        ts = str(self.timeslot.value)
        if self.name.endswith(ts) and not self.name.startswith("TAC"):
            return self.name
        return f"{self.name} {ts}"


@attr.s(frozen=True)
class Channel:
    """Base class for all channels"""
    name: str = attr.ib()
    frequency: float = attr.ib()  # MHz
    offset: float = attr.ib(default=0.0)  # MHz
    power: Power = attr.ib(default=Power.HIGH)
    rx_only: bool = attr.ib(default=False)
    code: Optional[str] = attr.ib(default=None)  # Short code for zone name
    dedup_key: int = attr.ib(default=0)  # For ensuring unique short names

    @property
    def short_name(self) -> str:
        """
        Generate short name for channel (max 16 chars for Anytone)
        """
        name = self.name[:16]
        if self.dedup_key > 0:
            suffix = f" {self.dedup_key}"
            name = name[:16 - len(suffix)] + suffix
        return name

    @property
    def tx_frequency(self) -> float:
        """Get transmit frequency"""
        return self.frequency + self.offset


@attr.s(frozen=True)
class AnalogChannel(Channel):
    """Analog FM channel"""
    bandwidth: Bandwidth = attr.ib(default=Bandwidth._25)
    tone_decode: Optional[str] = attr.ib(default=None)  # CTCSS/DCS decode
    tone_encode: Optional[str] = attr.ib(default=None)  # CTCSS/DCS encode
    scanlist: Optional['ScanList'] = attr.ib(default=None)  # Scanlist reference
    
    # APRS fields
    aprs_rx: str = attr.ib(default="Off")
    aprs_ptt_mode: str = attr.ib(default="Off")
    aprs_report_type: str = attr.ib(default="Off")
    aprs_report_channel: str = attr.ib(default="1")
    # 890-specific APRS (optional, default to "0")
    aprs_mute: str = attr.ib(default="0")
    aprs_tx_path: str = attr.ib(default="0")


@attr.s(frozen=True)
class DigitalChannel(Channel):
    """DMR digital channel"""
    color_code: int = attr.ib(default=1)
    talkgroup: Optional[Talkgroup] = attr.ib(default=None)
    static_talkgroups: Tuple[Talkgroup, ...] = attr.ib(default=())  # For repeaters with multiple TGs
    grouplist: Optional['GroupList'] = attr.ib(default=None)
    scanlist: Optional['ScanList'] = attr.ib(default=None)


@attr.s(frozen=True, auto_attribs=True)
class GroupList:
    """A group list of contacts for a digital channel"""
    name: str
    contacts: Tuple[Contact, ...]


@attr.s(frozen=True, auto_attribs=True)
class ScanList:
    """A scan list containing channels"""
    name: str
    channels: Tuple[Channel, ...]

    @property
    def unique_channels(self) -> Tuple[Channel, ...]:
        """Get unique channels by short name"""
        seen = set()
        unique = []
        for ch in self.channels:
            if ch.short_name not in seen:
                seen.add(ch.short_name)
                unique.append(ch)
        return tuple(unique)


@attr.s(frozen=True, auto_attribs=True)
class Zone:
    """A zone containing channels"""
    name: str
    channels_a: Tuple[Channel, ...]  # VFO A
    channels_b: Tuple[Channel, ...]  # VFO B

    @property
    def unique_channels(self) -> Tuple[Channel, ...]:
        """Get all unique channels in this zone"""
        all_channels = list(self.channels_a) + list(self.channels_b)
        seen = set()
        unique = []
        for ch in all_channels:
            if ch.short_name not in seen:
                seen.add(ch.short_name)
                unique.append(ch)
        return tuple(unique)


@attr.s(auto_attribs=True)
class Codeplug:
    """Complete codeplug with all objects"""
    contacts: Tuple[Contact, ...] = ()
    channels: Tuple[Channel, ...] = ()
    grouplists: Tuple[GroupList, ...] = ()
    scanlists: Tuple[ScanList, ...] = ()
    zones: Tuple[Zone, ...] = ()

    def filter_frequency_ranges(self, ranges: Tuple[Tuple[float, float], ...]) -> 'Codeplug':
        """
        Filter codeplug to only include channels in the specified frequency ranges
        """
        def in_range(freq):
            return any(low <= freq <= high for low, high in ranges)

        filtered_channels = tuple(ch for ch in self.channels if in_range(ch.frequency))
        filtered_channel_names = {ch.short_name for ch in filtered_channels}

        def filter_channels(channels):
            return tuple(ch for ch in channels if ch.short_name in filtered_channel_names)

        # Filter zones and scanlists to only include filtered channels
        filtered_zones = tuple(
            attr.evolve(
                zone,
                channels_a=filter_channels(zone.channels_a),
                channels_b=filter_channels(zone.channels_b),
            )
            for zone in self.zones
        )
        filtered_zones = tuple(z for z in filtered_zones if z.unique_channels)

        filtered_scanlists = tuple(
            attr.evolve(scanlist, channels=filter_channels(scanlist.channels))
            for scanlist in self.scanlists
        )
        filtered_scanlists = tuple(s for s in filtered_scanlists if s.unique_channels)

        return attr.evolve(
            self,
            channels=filtered_channels,
            zones=filtered_zones,
            scanlists=filtered_scanlists,
        )


def uniquify_contacts(contacts: Tuple[Contact, ...]) -> Tuple[Contact, ...]:
    """
    Return unique contacts by dmrid, keeping first occurrence
    """
    seen = set()
    unique = []
    for contact in contacts:
        if contact.dmrid not in seen:
            seen.add(contact.dmrid)
            unique.append(contact)
    return tuple(unique)
