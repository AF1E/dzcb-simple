# dzcb-simple Usage Guide

## Quick Start

```bash
# 1. Prepare your input directory with K7ABD CSV files
mkdir ~/my-codeplug
# Add your Analog__*.csv, Digital-Repeaters__*.csv, etc.

# 2. Run dzcb-simple
dzcb ~/my-codeplug ~/output

# 3. Import the generated CSV files into Anytone CPS
# Files will be in ~/output/878/ and ~/output/890/
```

## Installation

### From Source
```bash
git clone https://github.com/yourusername/dzcb-simple.git
cd dzcb-simple
pip install -e .
```

### Running Without Installation
```bash
PYTHONPATH=/path/to/dzcb-simple/src python3 -m dzcb input_dir output_dir
```

## Input File Format

### Required Files

Place these files in your input directory:

#### 1. Talkgroups__YourName.csv (no header)
```
Local,9
Worldwide,91
North America,93
TAC 310,310
Parrot Private,9990P
```

**Format:** `talkgroup_name,dmrid[P]`
- Add 'P' suffix for Private Call (e.g., `9990P`)
- No 'P' or Group Call by default

#### 2. Analog__YourName.csv
```csv
Zone,Channel Name,Bandwidth,Power,RX Freq,TX Freq,CTCSS Decode,CTCSS Encode,TX Prohibit,APRS RX,APRS PTT Mode,APRS Report Type
Simplex,146.520,25,High,146.520,146.520,Off,Off,Off,Off,Off,Off
Repeaters;RPTR,W7AW Cougar,25,High,146.760,146.160,103.5,103.5,Off,Off,Off,Off
APRS,APRS 144.390,25,High,144.390,144.390,Off,Off,Off,On,Both,Analog
```

**Columns:**
- `Zone` - Zone name, optionally with code: "Zone Name;CODE"
- `Channel Name` - Channel name (max 16 chars)
- `Bandwidth` - 12.5, 20, or 25 (kHz)
- `Power` - Low, Medium, High, or Turbo
- `RX Freq` - Receive frequency in MHz
- `TX Freq` - Transmit frequency in MHz
- `CTCSS Decode` - CTCSS/DCS tone or "Off"
- `CTCSS Encode` - CTCSS/DCS tone or "Off"
- `TX Prohibit` - "Off" or "On" (RX only)

**APRS Columns (optional, defaults to Off):**
- `APRS RX` - "Off" or "On"
- `APRS PTT Mode` - "Off", "Start", "End", or "Both"
- `APRS Report Type` - "Off", "Analog", or "Digital"

#### 3. Digital-Repeaters__YourName.csv
```csv
Zone Name,Comment,Power,RX Freq,TX Freq,Color Code,Worldwide,North America,Local,TAC 310
K7ABD;K7ABD,Seattle,High,440.600,445.600,1,-,1,2,-
```

**Columns:**
- `Zone Name` - Zone name with optional code: "Zone Name;CODE"
- `Comment` - Optional description
- `Power` - Low, Medium, High, or Turbo
- `RX Freq` - Receive frequency in MHz
- `TX Freq` - Transmit frequency in MHz
- `Color Code` - DMR color code (1-15)
- Remaining columns are talkgroup names with values:
  - `-` = Not included
  - `1` = Timeslot 1
  - `2` = Timeslot 2

**Result:** Creates one channel per talkgroup with automatic naming.
- Example: "K7ABD Worldwide 1", "K7ABD Local 2"

#### 4. Digital-Others__YourName.csv
```csv
Zone,Channel Name,Power,RX Freq,TX Freq,Color Code,Talk Group,TimeSlot,Call Type,TX Permit
Simplex,DMR Simplex 1,High,433.450,433.450,1,Local,1,Group Call,Always
```

**Columns:**
- `Zone` - Zone name with optional code
- `Channel Name` - Channel name
- `Power` - Low, Medium, High, or Turbo
- `RX Freq` - Receive frequency in MHz
- `TX Freq` - Transmit frequency in MHz
- `Color Code` - DMR color code (1-15)
- `Talk Group` - Talkgroup name (must be in Talkgroups file)
- `TimeSlot` - 1 or 2
- `Call Type` - "Group Call" or "Private Call"
- `TX Permit` - "Always" or "Same Color Code"

## Command-Line Options

```bash
dzcb [OPTIONS] INPUT_DIR OUTPUT_DIR
```

### Arguments
- `INPUT_DIR` - Directory containing K7ABD CSV files
- `OUTPUT_DIR` - Where to write output CSV files

### Options
- `--radio {878,890,both}` - Which radio(s) to generate (default: both)
- `--sort {alpha,repeaters-first,analog-first}` - Zone/channel sort order (default: alpha)
- `-v, --verbose` - Enable detailed logging
- `--version` - Show version and exit
- `-h, --help` - Show help message

### Sort Modes

The `--sort` option controls how zones and channels are ordered in the output:

- **`alpha`** (default) - Alphabetize everything. Zones sorted A-Z, channels within each zone sorted alphabetically by name.

- **`repeaters-first`** - Digital repeater zones appear first (preserving row order from `Digital-Repeaters__*.csv`), followed by Analog and Digital-Others zones (preserving their file order). Channels within each zone preserve input file order.

- **`analog-first`** - Analog/Digital-Others zones appear first (preserving file order), followed by digital repeater zones (preserving their file order). Channels within each zone preserve input file order.

Contacts (TalkGroups.CSV) are always sorted alphabetically regardless of sort mode.

### Examples

```bash
# Generate for both radios (default)
dzcb ~/my-codeplug ~/output

# Generate for 890 only
dzcb ~/my-codeplug ~/output --radio 890

# Generate for 878 only
dzcb ~/my-codeplug ~/output --radio 878

# Verbose output for debugging
dzcb ~/my-codeplug ~/output -v

# Analog/others zones first, then repeaters
dzcb ~/my-codeplug ~/output --sort analog-first

# Repeater zones first, then analog/others
dzcb ~/my-codeplug ~/output --sort repeaters-first
```

## Output Files

The tool generates 4 CSV files for each radio in separate directories:

```
output/
├── 878/
│   ├── Channel.CSV      # All channels
│   ├── TalkGroups.CSV   # Contact list
│   ├── Zone.CSV         # Zone assignments
│   └── ScanList.CSV     # Scan lists
└── 890/
    ├── Channel.CSV
    ├── TalkGroups.CSV
    ├── Zone.CSV
    └── ScanList.CSV
```

### Importing into CPS

**For Anytone 878:**
1. Open Anytone CPS 1.21+
2. File → Import → Select `878/Channel.CSV`
3. File → Import → Select `878/TalkGroups.CSV`
4. File → Import → Select `878/Zone.CSV`
5. File → Import → Select `878/ScanList.CSV`

**For Anytone 890:**
1. Open Anytone 890 CPS
2. Follow same import procedure with `890/` files

## Tips & Tricks

### Zone Organization

Use zone codes for better organization:
```csv
Zone,Channel Name,...
Repeaters;RPTR,W7AW,...
Simplex;SMPLX,146.520,...
APRS;APRS,144.390,...
```

The code after `;` is used for grouplist names and identification.

### Talkgroup Naming

Name your talkgroups descriptively:
```
Local 9,9
WW 91,91
NA 93,93
```

Repeater channels will be named: "K7ABD Local 9 2"

### Frequency Filtering

The tool automatically filters channels by radio capability:
- 878/890: VHF (136-174 MHz) and UHF (400-480 MHz)
- Out-of-band channels are automatically excluded

### Scan Lists

Each zone automatically gets a scan list with the same name containing all channels in that zone.

### APRS Configuration

To enable APRS on analog channels:
```csv
Zone,Channel Name,...,APRS RX,APRS PTT Mode,APRS Report Type
APRS,APRS 144.390,...,On,Both,Analog
APRS,APRS 144.390 RX,...,On,Off,Analog
```

Common settings:
- **APRS RX**: "On" to receive APRS
- **APRS PTT Mode**: "Both" to beacon on PTT press/release
- **APRS Report Type**: "Analog" for analog APRS

## Troubleshooting

### "Unknown talkgroup" warning
Your Digital channels reference a talkgroup that isn't in your Talkgroups file.
**Fix:** Add the talkgroup to Talkgroups__*.csv

### Empty output
Check that your input files follow the naming pattern:
- `Analog__*.csv`
- `Digital-Repeaters__*.csv`
- `Digital-Others__*.csv`
- `Talkgroups__*.csv`

### Channels not appearing
Verify frequencies are in range:
- VHF: 136-174 MHz
- UHF: 400-480 MHz

### APRS not working
Make sure APRS columns are present in your Analog CSV.
If columns are missing, they default to "Off".

## Examples

See the `examples/` directory for sample input files:
- `Analog__Example.csv` - Example analog channels with APRS
- `Digital-Repeaters__Example.csv` - Example DMR repeater
- `Digital-Others__Example.csv` - Example DMR simplex
- `Talkgroups__Example.csv` - Example talkgroups

Run the examples:
```bash
dzcb examples /tmp/output -v
```

## Getting Help

- Documentation: https://github.com/yourusername/dzcb-simple
- Issues: https://github.com/yourusername/dzcb-simple/issues
- Original dzcb: https://github.com/mycodeplug/dzcb
