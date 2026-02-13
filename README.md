# dzcb-simple

**D**MR **Z**one **C**hannel **B**uilder - Simplified for Anytone 878/890

A streamlined Python tool to generate Anytone radio codeplug CSV files from K7ABD format input files.

## Features

- ✅ Read K7ABD CSV format (Analog, Digital-Repeaters, Digital-Others, Talkgroups)
- ✅ Generate Anytone 878UVii CSV files
- ✅ Generate Anytone 890 CSV files
- ✅ Support APRS configuration on analog channels
- ✅ Simple command-line interface
- ✅ Modern Python packaging (Python 3.8+)

## Installation

```bash
# Install from source
git clone https://github.com/yourusername/dzcb-simple.git
cd dzcb-simple
pip install -e .
```

## Usage

### Basic Usage

```bash
# Generate for both radios
dzcb input_directory output_directory

# Generate for 890 only
dzcb input_directory output_directory --radio 890

# Generate for 878 only
dzcb input_directory output_directory --radio 878
```

### Sorting Options

Control zone and channel ordering with `--sort`:

```bash
# Alphabetical (default) - zones and channels sorted A-Z
dzcb input_directory output_directory --sort alpha

# Repeaters first - digital repeater zones first, then analog/others, preserving file order
dzcb input_directory output_directory --sort repeaters-first

# Analog first - analog/digital-others zones first, then repeaters, preserving file order
dzcb input_directory output_directory --sort analog-first
```

| Mode | Zone Order | Channel Order Within Zones |
|------|-----------|--------------------------|
| `alpha` | All zones sorted A-Z | Channels sorted alphabetically |
| `repeaters-first` | Repeater zones first, then analog/others | Preserves input file order |
| `analog-first` | Analog/others first, then repeater zones | Preserves input file order |

### Input File Format

Place your K7ABD format CSV files in a directory:

**Analog__YourName.csv:**
```csv
Zone,Channel Name,Bandwidth,Power,RX Freq,TX Freq,CTCSS Decode,CTCSS Encode,TX Prohibit,APRS RX,APRS PTT Mode,APRS Report Type
Simplex,146.520,25,High,146.520,146.520,Off,Off,Off,Off,Off,Off
```

**Digital-Repeaters__YourName.csv:**
```csv
Zone Name,Comment,Power,RX Freq,TX Freq,Color Code,TG1,TG2,TG3
K7ABD;K7ABD,Seattle,High,440.600,445.600,1,1,2,-
```

**Digital-Others__YourName.csv:**
```csv
Zone,Channel Name,Power,RX Freq,TX Freq,Color Code,Talk Group,TimeSlot,Call Type,TX Permit
Simplex,DMR Simplex 1,High,433.450,433.450,1,Local,1,Group Call,Always
```

**Talkgroups__YourName.csv:**
```
Local,9
Worldwide,91
North America,93
TAC 310,310
```

### Output

The tool generates four CSV files in the output directory for each radio:

- `Channel.CSV` - All channels
- `TalkGroups.CSV` - Contact list
- `Zone.CSV` - Zone assignments
- `ScanList.CSV` - Scan lists

Import these files into your Anytone CPS.

## APRS Support

Add APRS configuration to analog channels with these optional columns:

- `APRS RX` - Off or On
- `APRS PTT Mode` - Off, Start, End, or Both
- `APRS Report Type` - Off, Analog, or Digital

Example:
```csv
Zone,Channel Name,...,APRS RX,APRS PTT Mode,APRS Report Type
APRS,144.390,...,On,Both,Analog
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Format code
black src/

# Run tests
pytest
```

## Differences from Original dzcb

This is a simplified fork focused on:
- Local K7ABD CSV input only (no network fetching)
- Anytone 878/890 output only (no other radio formats)
- APRS support for analog channels
- Modern Python packaging
- Simpler codebase and maintenance

For the full-featured version with Repeaterbook integration, PNWDigital support, and multiple output formats, see the [original dzcb](https://github.com/mycodeplug/dzcb).

## Credits

Based on the original [dzcb](https://github.com/mycodeplug/dzcb) by Masen Furer.

Simplified and modernized by Joe (AF1E) for personal use with Anytone 878UVii and 890 radios.

## License

MIT License - see LICENSE file
