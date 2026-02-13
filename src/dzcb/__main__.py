"""
dzcb-simple command-line interface
"""
import argparse
import logging
import sys
from pathlib import Path

from dzcb import __version__
from dzcb.k7abd import codeplug_from_k7abd
from dzcb.anytone import generate_all_radios, SUPPORTED_RADIOS


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="dzcb-simple: DMR Zone Channel Builder for Anytone 878/890",
        epilog="For more information, see: https://github.com/mycodeplug/dzcb-simple",
    )
    
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing K7ABD format CSV files",
    )
    
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Output directory for Anytone CSV files",
    )
    
    parser.add_argument(
        "--radio",
        choices=["878", "890", "both"],
        default="both",
        help="Which radio(s) to generate files for (default: both)",
    )
    
    parser.add_argument(
        "--sort",
        choices=["alpha", "repeaters-first", "analog-first"],
        default="alpha",
        help=(
            "Zone/channel sort order: "
            "'alpha' (default) sorts everything A-Z; "
            "'repeaters-first' preserves file order with digital repeater zones first; "
            "'analog-first' uses your sorting with Analog/Digital-Others zones first, "
            "DMR repeater zones follow behind preserving file order"
        ),
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"dzcb-simple {__version__}",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Validate input directory
    if not args.input_dir.exists():
        logger.error(f"Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    if not args.input_dir.is_dir():
        logger.error(f"Input path is not a directory: {args.input_dir}")
        sys.exit(1)
    
    # Determine which radios to generate
    if args.radio == "both":
        radio_ids = ["878", "890"]
    else:
        radio_ids = [args.radio]
    
    # Show configuration
    logger.info(f"dzcb-simple v{__version__}")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Generating for: {', '.join(SUPPORTED_RADIOS[r]['name'] for r in radio_ids)}")
    logger.info(f"Sort order: {args.sort}")
    logger.info("")
    
    try:
        # Parse input files
        logger.info("Reading K7ABD CSV files...")
        codeplug = codeplug_from_k7abd(args.input_dir, sort_mode=args.sort)
        
        logger.info(f"Loaded codeplug:")
        logger.info(f"  {len(codeplug.contacts)} contacts")
        logger.info(f"  {len(codeplug.channels)} channels")
        logger.info(f"  {len(codeplug.zones)} zones")
        logger.info(f"  {len(codeplug.scanlists)} scanlists")
        logger.info("")
        
        # Generate output files
        logger.info("Generating Anytone CSV files...")
        generate_all_radios(codeplug, args.output_dir, radio_ids)
        
        logger.info("")
        logger.info("✓ Done! Import the CSV files into your Anytone CPS.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
