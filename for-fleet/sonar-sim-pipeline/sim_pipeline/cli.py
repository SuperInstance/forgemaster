"""Pipeline CLI.

Usage::

    python -m sim_pipeline survey --type lawnmower --area 500x500 --depth 50
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from .physics import JerlovWaterType
from .mission_planner import SurveyType
from .pipeline import Pipeline


def _setup_logging(verbose: bool = False) -> None:
    """Configure root logging."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stderr)


def _parse_area(area_str: str) -> tuple[float, float]:
    """Parse '500x500' into (width, height)."""
    parts = area_str.lower().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"Area must be WxH, got: {area_str}")
    try:
        w = float(parts[0])
        h = float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid area dimensions: {area_str}") from exc
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError(f"Area dimensions must be positive: {area_str}")
    return w, h


def _parse_jerlov(value: str) -> JerlovWaterType:
    """Parse Jerlov water type string."""
    try:
        return JerlovWaterType(value.upper())
    except ValueError as exc:
        valid = ", ".join(j.value for j in JerlovWaterType)
        raise argparse.ArgumentTypeError(
            f"Invalid water type '{value}'. Choose from: {valid}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sim_pipeline",
        description="Sonar simulation pipeline: mission → physics → ray trace → display",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # survey subcommand
    survey_parser = subparsers.add_parser("survey", help="Run a survey simulation")
    survey_parser.add_argument(
        "--type",
        choices=[t.value for t in SurveyType],
        default="lawnmower",
        help="Survey pattern type (default: lawnmower)",
    )
    survey_parser.add_argument(
        "--area",
        type=_parse_area,
        default=(500.0, 500.0),
        help="Survey area as WxH in meters (default: 500x500)",
    )
    survey_parser.add_argument(
        "--depth",
        type=float,
        default=50.0,
        help="Water depth in meters (default: 50)",
    )
    survey_parser.add_argument(
        "--line-spacing",
        type=float,
        default=None,
        help="Track spacing in meters (default: auto)",
    )
    survey_parser.add_argument(
        "--speed",
        type=float,
        default=2.5,
        help="AUV speed in m/s (default: 2.5)",
    )
    survey_parser.add_argument(
        "--water-type",
        type=_parse_jerlov,
        default=JerlovWaterType.IA,
        help="Jerlov water type (default: IA)",
    )
    survey_parser.add_argument(
        "--surface-temp",
        type=float,
        default=20.0,
        help="Surface temperature in °C (default: 20)",
    )
    survey_parser.add_argument(
        "--deep-temp",
        type=float,
        default=4.0,
        help="Deep water temperature in °C (default: 4)",
    )
    survey_parser.add_argument(
        "--salinity",
        type=float,
        default=35.0,
        help="Salinity in psu (default: 35)",
    )
    survey_parser.add_argument(
        "--thermocline",
        type=float,
        default=100.0,
        help="Thermocline characteristic depth in meters (default: 100)",
    )
    survey_parser.add_argument(
        "--freq",
        type=float,
        default=50.0,
        help="Sonar frequency in kHz (default: 50)",
    )
    survey_parser.add_argument(
        "--max-range",
        type=float,
        default=500.0,
        help="Max ray trace range in meters (default: 500)",
    )
    survey_parser.add_argument(
        "--ray-step",
        type=float,
        default=1.0,
        help="Ray trace step size in meters (default: 1)",
    )
    survey_parser.add_argument(
        "--n-beams",
        type=int,
        default=101,
        help="Number of beams for multi-beam (default: 101)",
    )
    survey_parser.add_argument(
        "--aperture",
        type=float,
        default=120.0,
        help="Beam aperture in degrees (default: 120)",
    )
    survey_parser.add_argument(
        "--single-beam",
        action="store_true",
        help="Use single-beam instead of multi-beam",
    )
    survey_parser.add_argument(
        "--save-csv",
        action="store_true",
        help="Also save CSV output",
    )
    survey_parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for JSON/CSV (default: output)",
    )

    # info subcommand
    info_parser = subparsers.add_parser("info", help="Show physics constants and formulas")

    return parser


def cmd_survey(args: argparse.Namespace) -> int:
    """Execute the survey command."""
    width, height = args.area
    pipeline = Pipeline(
        survey_type=SurveyType(args.type),
        width=width,
        height=height,
        depth=args.depth,
        line_spacing=args.line_spacing,
        speed=args.speed,
        water_type=args.water_type,
        surface_temp=args.surface_temp,
        deep_temp=args.deep_temp,
        salinity=args.salinity,
        thermocline_depth=args.thermocline,
        freq=args.freq,
        max_range=args.max_range,
        ray_step=args.ray_step,
        n_beams=args.n_beams,
        aperture=args.aperture,
        output_dir=args.output_dir,
    )

    result = pipeline.run(
        multi_beam=not args.single_beam,
        save_csv=args.save_csv,
    )

    print("=" * 60)
    print("SONAR SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Survey type     : {result.mission.survey_type.value}")
    print(f"Area            : {width:.0f} x {height:.0f} m")
    print(f"Depth           : {args.depth:.1f} m")
    print(f"Waypoints       : {len(result.mission.waypoints)}")
    print(f"Pings simulated : {len(result.pings)}")
    print(f"Duration est.   : {result.mission.duration_estimate_s:.0f} s")
    print(f"JSON output     : {result.json_path}")
    print("-" * 60)
    print(result.ascii_plot)
    print("-" * 60)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show physics info."""
    print("=" * 60)
    print("SONAR SIMULATION PIPELINE — PHYSICS REFERENCE")
    print("=" * 60)
    print("\nSound Speed: Mackenzie (1981)")
    print("  c = 1448.96 + 4.591*T - 5.304e-2*T^2 + 2.374e-4*T^3")
    print("      + 1.340*(S-35) + 1.630e-2*D + 1.675e-7*D^2")
    print("      - 1.025e-2*T*(S-35) - 7.139e-13*T*D^3")
    print("\nAbsorption: Francois-Garrison (1982)")
    print("  alpha = alpha_boric + alpha_magnesium + alpha_water")
    print("  alpha_boric  = 0.106 * f1*f^2/(f1^2+f^2) * exp((pH-8)/0.56)")
    print("  alpha_mg     = 0.52*(1+T/43)*(S/35)*f2*f^2/(f2^2+f^2)*exp(-D/6000)")
    print("  alpha_water  = 0.00049*f^2*exp(-(T/27 + D/17000))")
    print("\nRefraction: Snell's Law")
    print("  sin(theta2)/sin(theta1) = c2/c1")
    print("\nThermocline: Exponential decay")
    print("  T(z) = T_deep + (T_surface - T_deep) * exp(-z / z_thermo)")
    print("\nJerlov Water Types (Kd in m^-1):")
    for wt in JerlovWaterType:
        print(f"  {wt.value:>8} : Kd = {FluxPhysics.JERLOV_KD.get(wt, 0.0):.3f}")
    print("=" * 60)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(verbose=args.verbose)

    if args.command == "survey":
        return cmd_survey(args)
    elif args.command == "info":
        return cmd_info(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
