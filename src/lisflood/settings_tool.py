"""
LISFLOOD settings XML formatter and updater.
"""

from __future__ import absolute_import

import argparse
import re
import sys

import yaml
from lxml import etree

# Built-in path variables that LISFLOOD provides automatically.
_BUILTIN_VARS = frozenset({
    "SettingsPath", "SettingsDir", "ProjectPath", "ProjectDir",
})


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


_VAR_RE = re.compile(r"\$\(([^)]+)\)")


def _find_refs(value):
    """Return set of variable names referenced via $(Name) in *value*."""
    return set(_VAR_RE.findall(value))


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
        return _validate_refs(lfuser_elem, root)

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


def _validate_refs(lfuser_elem, root):
    """Check that every $(Var) reference resolves to a defined lfuser name or a builtin."""
    user_index = _index_textvars(lfuser_elem)
    defined = set(user_index.keys()) | _BUILTIN_VARS
    errors = []

    lfbinding_elem = root.find("lfbinding")
    if lfbinding_elem is None:
        lfbinding_elem = root.find("lfbindings")

    for section_tag, elem in [("lfuser", lfuser_elem), ("lfbinding", lfbinding_elem)]:
        if elem is None:
            continue
        for node in elem.findall(".//textvar"):
            name = node.get("name", "?")
            value = node.get("value", "")
            for ref in _find_refs(value):
                if ref not in defined:
                    errors.append(
                        "{}: '{}' references undefined variable '$({})'.".format(
                            section_tag, name, ref
                        )
                    )

    # Also scan lfoptions — they shouldn't contain $(refs) but flag if they do
    lfoptions_elem = root.find("lfoptions")
    if lfoptions_elem is not None:
        for node in lfoptions_elem.findall(".//setoption"):
            choice = node.get("choice", "")
            for ref in _find_refs(choice):
                errors.append(
                    "lfoptions: '{}' choice references variable '$({})'.".format(
                        node.get("name", "?"), ref
                    )
                )

    if errors:
        for err in errors:
            print("  " + err, file=sys.stderr)
        raise SettingsToolError("{} undefined variable reference(s) found.".format(len(errors)))
    return 0


def _parse_sections(path):
    """Parse an XML file and return (tree, root, lfoptions_elem, lfuser_elem, lfbinding_elem)."""
    parser = etree.XMLParser(remove_blank_text=True, remove_comments=False)
    tree = etree.parse(path, parser)
    root = tree.getroot()
    if root.tag != "lfsettings":
        raise SettingsToolError("Root element must be <lfsettings>, found <{}>.".format(root.tag))
    lfoptions_elem = _get_required_child(root, ("lfoptions",))
    lfuser_elem = _get_required_child(root, ("lfuser",))
    lfbinding_elem = _get_required_child(root, ("lfbinding", "lfbindings"))
    return tree, root, lfoptions_elem, lfuser_elem, lfbinding_elem


def _shell_quote(value):
    """Wrap *value* in single quotes so it is safe to paste into a shell command."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _copy_path(path):
    """Return *path* with '_copy' inserted before the extension."""
    import os
    base, ext = os.path.splitext(path)
    return base + "_copy" + ext


def run_diff(input_path, output_path):
    """Compare two LISFLOOD settings XMLs and print differences."""
    _, _, opts_a, user_a, _ = _parse_sections(input_path)
    _, _, opts_b, user_b, _ = _parse_sections(output_path)

    idx_opts_a = {n.get("name"): n.get("choice") for n in opts_a.findall(".//setoption") if n.get("name")}
    idx_opts_b = {n.get("name"): n.get("choice") for n in opts_b.findall(".//setoption") if n.get("name")}
    idx_user_a = {n.get("name"): n.get("value") for n in user_a.findall(".//textvar") if n.get("name")}
    idx_user_b = {n.get("name"): n.get("value") for n in user_b.findall(".//textvar") if n.get("name")}

    opt_diffs = []
    user_diffs = []

    all_opt_keys = sorted(set(idx_opts_a) | set(idx_opts_b))
    for key in all_opt_keys:
        va = idx_opts_a.get(key)
        vb = idx_opts_b.get(key)
        if va != vb:
            opt_diffs.append((key, va, vb))

    all_user_keys = sorted(set(idx_user_a) | set(idx_user_b))
    for key in all_user_keys:
        va = idx_user_a.get(key)
        vb = idx_user_b.get(key)
        if va != vb:
            user_diffs.append((key, va, vb))

    if not opt_diffs and not user_diffs:
        print("No differences found.")
        return 0

    if opt_diffs:
        print("lfoptions:")
        for name, va, vb in opt_diffs:
            la = "  (absent)" if va is None else va
            lb = "  (absent)" if vb is None else vb
            print("  {}: {} -> {}".format(name, la, lb))

    if user_diffs:
        print("lfuser:")
        for name, va, vb in user_diffs:
            la = "  (absent)" if va is None else va
            lb = "  (absent)" if vb is None else vb
            print("  {}: {} -> {}".format(name, la, lb))

    # Build the set command to go from input (-i) to output (-o)
    out_copy = _copy_path(output_path)
    cmd_parts = ["lisflood-settings set -i {} -o {}".format(
        _shell_quote(input_path), _shell_quote(out_copy)
    )]
    set_opt_parts = []
    set_user_parts = []
    for name, _va, vb in opt_diffs:
        if vb is not None:
            set_opt_parts.append(_shell_quote("{}={}".format(name, vb)))
    for name, _va, vb in user_diffs:
        if vb is not None:
            set_user_parts.append(_shell_quote("{}={}".format(name, vb)))
    if set_opt_parts:
        cmd_parts.append("--lfoptions " + " ".join(set_opt_parts))
    if set_user_parts:
        cmd_parts.append("--lfuser " + " ".join(set_user_parts))
    print("\nEquivalent command (-i -> -o):")
    print("  " + " ".join(cmd_parts))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Parse, validate, lint and update LISFLOOD settings XML files."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser(
        "check",
        help="Validate XML structure, sections, and variable references.",
    )
    check_parser.add_argument("-i", "--input", required=True, help="Input LISFLOOD settings XML file.")

    diff_parser = subparsers.add_parser(
        "diff",
        help="Show differences between two settings XMLs.",
    )
    diff_parser.add_argument("-i", "--input", required=True, help="First (base) LISFLOOD settings XML file.")
    diff_parser.add_argument("-o", "--output", required=True, help="Second (target) LISFLOOD settings XML file.")

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

        if args.command == "diff":
            run_diff(args.input, args.output)
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
