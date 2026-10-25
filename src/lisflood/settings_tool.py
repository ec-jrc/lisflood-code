"""
LISFLOOD settings XML formatter and updater.
"""

from __future__ import absolute_import

import argparse
import sys

import yaml
from lxml import etree


class SettingsToolError(Exception):
    """Raised when the settings tool cannot complete requested operations."""


def _parse_bool(value):
    if isinstance(value, bool):
        return 1 if value else 0
    sval = str(value).strip().lower()
    if sval in ("1", "true", "yes", "on"):
        return 1
    if sval in ("0", "false", "no", "off"):
        return 0
    raise SettingsToolError("Invalid lfoptions value '{}'. Use 0/1 or true/false.".format(value))


def _get_required_child(root, names):
    for name in names:
        node = root.find(name)
        if node is not None:
            return node
    raise SettingsToolError("Missing XML section(s): {}".format(", ".join(names)))


def _index_options(lfoptions_elem):
    indexed = {}
    for node in lfoptions_elem.findall(".//setoption"):
        name = node.get("name")
        if name:
            indexed[name] = node
    return indexed


def _index_textvars(section_elem):
    indexed = {}
    for node in section_elem.findall(".//textvar"):
        name = node.get("name")
        if name:
            indexed[name] = node
    return indexed


def _key_value_arg(expression):
    if "=" not in expression:
        raise argparse.ArgumentTypeError(
            "Invalid entry '{}' (expected KEY=VALUE).".format(expression)
        )
    name, value = expression.split("=", 1)
    if not name.strip():
        raise argparse.ArgumentTypeError(
            "Invalid entry '{}' (empty key in KEY=VALUE).".format(expression)
        )
    return name.strip(), value


def _flatten_pairs(raw_values):
    if not raw_values:
        return []
    # raw_values shape with nargs='+' and action='append': [[(k,v), ...], ...]
    flattened = []
    for values in raw_values:
        flattened.extend(values)
    return flattened


def run_tool(input_path, output_path=None, file_path=None, lfoptions_values=None, lfuser_values=None, check=False):
    parser = etree.XMLParser(remove_blank_text=True, remove_comments=False)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()
    if root.tag != "lfsettings":
        raise SettingsToolError("Root element must be <lfsettings>, found <{}>.".format(root.tag))

    lfoptions_elem = _get_required_child(root, ("lfoptions",))
    lfuser_elem = _get_required_child(root, ("lfuser",))
    _ = _get_required_child(root, ("lfbinding", "lfbindings"))

    if check:
        return 0

    if not output_path:
        raise SettingsToolError("Output path is required for the 'set' subcommand.")

    options_index = _index_options(lfoptions_elem)
    user_index = _index_textvars(lfuser_elem)

    merged_lfoptions = {}
    merged_lfuser = {}

    if file_path:
        with open(file_path, "r") as stream:
            payload = yaml.safe_load(stream) or {}
        yaml_options = payload.get("lfoptions") or payload.get("options") or {}
        yaml_user = payload.get("lfuser") or payload.get("user") or {}
        if not isinstance(yaml_options, dict) or not isinstance(yaml_user, dict):
            raise SettingsToolError("Update file must use mapping values for lfoptions/lfuser.")
        merged_lfoptions.update(yaml_options)
        merged_lfuser.update(yaml_user)

    for name, value in lfoptions_values or []:
        merged_lfoptions[name] = value
    for name, value in lfuser_values or []:
        merged_lfuser[name] = value

    for name, value in merged_lfoptions.items():
        node = options_index.get(name)
        if node is None:
            raise SettingsToolError("lfoptions variable '{}' not found in XML.".format(name))
        node.set("choice", str(_parse_bool(value)))

    for name, value in merged_lfuser.items():
        node = user_index.get(name)
        if node is None:
            raise SettingsToolError("lfuser variable '{}' not found in XML.".format(name))
        node.set("value", str(value))

    tree.write(output_path, encoding="utf-8", pretty_print=True)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Parse, validate, lint and update LISFLOOD settings XML files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser(
        "check",
        help="Validate XML structure/sections without writing output.",
    )
    check_parser.add_argument("-i", "--input", required=True, help="Input LISFLOOD settings XML file.")

    set_parser = subparsers.add_parser(
        "set",
        help="Apply updates and write output XML.",
    )
    set_parser.add_argument("-i", "--input", required=True, help="Input LISFLOOD settings XML file.")
    set_parser.add_argument("-o", "--output", required=True, help="Output XML path.")
    set_parser.add_argument(
        "-f",
        "--file",
        dest="file",
        help="YAML file with updates. Format: {lfoptions: {name: 0/1}, lfuser: {name: value}}.",
    )
    set_parser.add_argument(
        "--lfoptions",
        action="append",
        nargs="+",
        type=_key_value_arg,
        metavar="KEY=VALUE",
        help="One or more lfoptions updates. Example: --lfoptions TemperatureInKelvin=1 wateruse=0",
    )
    set_parser.add_argument(
        "--lfuser",
        action="append",
        nargs="+",
        type=_key_value_arg,
        metavar="KEY=VALUE",
        help="One or more lfuser updates. Example: --lfuser PathRoot=/data NetCDFTimeChunks=10",
    )

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "check":
            run_tool(input_path=args.input, check=True)
            return 0

        lfoptions_values = _flatten_pairs(args.lfoptions)
        lfuser_values = _flatten_pairs(args.lfuser)
        run_tool(
            input_path=args.input,
            output_path=args.output,
            file_path=args.file,
            lfoptions_values=lfoptions_values,
            lfuser_values=lfuser_values,
            check=False,
        )
    except (SettingsToolError, etree.XMLSyntaxError, OSError, yaml.YAMLError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
