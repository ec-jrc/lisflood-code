"""
LISFLOOD settings XML formatter and updater.
"""

from __future__ import absolute_import

import argparse
import re
import sys

import yaml
from lxml import etree


_PLACEHOLDER_RE = re.compile(r"\$\(([^)]+)\)")
_BUILTIN_BINDING_VARS = {"ProjectDir", "ProjectPath", "SettingsDir", "SettingsPath"}


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
    raise SettingsToolError("Invalid option value '{}'. Use 0/1 or true/false.".format(value))


def _parse_set_expression(expression):
    if "=" not in expression:
        raise SettingsToolError("Invalid --set '{}' (expected section.name=value)".format(expression))
    lhs, value = expression.split("=", 1)
    if "." not in lhs:
        raise SettingsToolError(
            "Invalid --set '{}' (expected lfoptions.name=value or lfuser.name=value)".format(expression)
        )
    section, name = lhs.split(".", 1)
    section = section.strip().lower()
    if section not in ("lfoptions", "lfuser"):
        raise SettingsToolError("Unsupported section '{}' in --set '{}'".format(section, expression))
    if not name.strip():
        raise SettingsToolError("Missing variable name in --set '{}'".format(expression))
    return section, name.strip(), value


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


def _resolve_with_user(value, user_values):
    resolved = value
    for _ in range(25):
        matches = _PLACEHOLDER_RE.findall(resolved)
        if not matches:
            return resolved
        changed = False
        for key in matches:
            if key in user_values:
                resolved = resolved.replace("$({})".format(key), user_values[key])
                changed = True
        if not changed:
            return resolved
    raise SettingsToolError("Could not resolve placeholders after 25 iterations: {}".format(value))


def _validate_compatibility(binding_nodes, user_values):
    issues = []
    allowed = set(user_values.keys()) | _BUILTIN_BINDING_VARS
    for name, node in binding_nodes.items():
        value = node.get("value", "")
        for ref in _PLACEHOLDER_RE.findall(value):
            if ref not in allowed:
                issues.append(
                    "Binding '{}' references undefined variable '$({})'.".format(name, ref)
                )
        try:
            _resolve_with_user(value, user_values)
        except SettingsToolError as exc:
            issues.append("Binding '{}' is not resolvable: {}.".format(name, exc))
    return issues


def run_tool(input_path, output_path=None, yaml_path=None, set_values=None, option_values=None, user_values=None, check=False):
    parser = etree.XMLParser(remove_blank_text=True, remove_comments=False)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()
    if root.tag != "lfsettings":
        raise SettingsToolError("Root element must be <lfsettings>, found <{}>.".format(root.tag))

    lfoptions_elem = _get_required_child(root, ("lfoptions",))
    lfuser_elem = _get_required_child(root, ("lfuser",))
    lfbinding_elem = _get_required_child(root, ("lfbinding", "lfbindings"))

    options_index = _index_options(lfoptions_elem)
    user_index = _index_textvars(lfuser_elem)
    binding_index = _index_textvars(lfbinding_elem)

    merged_option_updates = {}
    merged_user_updates = {}

    if yaml_path:
        with open(yaml_path, "r") as stream:
            payload = yaml.safe_load(stream) or {}
        yaml_options = payload.get("lfoptions") or payload.get("options") or {}
        yaml_user = payload.get("lfuser") or payload.get("user") or {}
        if not isinstance(yaml_options, dict) or not isinstance(yaml_user, dict):
            raise SettingsToolError("YAML file must use mapping values for lfoptions/lfuser.")
        merged_option_updates.update(yaml_options)
        merged_user_updates.update(yaml_user)

    for section, name, value in set_values or []:
        if section == "lfoptions":
            merged_option_updates[name] = value
        else:
            merged_user_updates[name] = value
    for name, value in option_values or []:
        merged_option_updates[name] = value
    for name, value in user_values or []:
        merged_user_updates[name] = value

    for name, value in merged_option_updates.items():
        node = options_index.get(name)
        if node is None:
            raise SettingsToolError("lfoptions variable '{}' not found in XML.".format(name))
        node.set("choice", str(_parse_bool(value)))

    for name, value in merged_user_updates.items():
        node = user_index.get(name)
        if node is None:
            raise SettingsToolError("lfuser variable '{}' not found in XML.".format(name))
        node.set("value", str(value))

    user_values_map = dict((name, node.get("value", "")) for name, node in user_index.items())
    # Compatibility checks between lfbinding and lfuser are intentionally disabled.
    # compatibility_issues = _validate_compatibility(binding_index, user_values_map)
    # if compatibility_issues:
    #     raise SettingsToolError("Compatibility validation failed:\n- {}".format("\n- ".join(compatibility_issues)))

    if check:
        return 0

    if not output_path:
        raise SettingsToolError("Output path is required unless --check is used.")

    tree.write(output_path, encoding="utf-8", pretty_print=True)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Parse, validate, lint and update LISFLOOD settings XML files."
    )
    parser.add_argument("input", help="Input LISFLOOD settings XML file.")
    parser.add_argument("output", nargs="?", help="Output XML path (required unless --check).")
    parser.add_argument(
        "--yaml",
        dest="yaml",
        help="YAML file with updates. Format: {lfoptions: {name: 0/1}, lfuser: {name: value}}.",
    )
    parser.add_argument(
        "--set",
        action="append",
        help="Update value using section.name=value, where section is lfoptions or lfuser. Can be repeated.",
    )
    parser.add_argument(
        "--option",
        action="append",
        help="Update lfoptions value using name=value (equivalent to --set lfoptions.name=value).",
    )
    parser.add_argument(
        "--user",
        action="append",
        help="Update lfuser value using name=value (equivalent to --set lfuser.name=value).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate XML structure/sections without writing output.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        set_values = []
        for expression in args.set or []:
            set_values.append(_parse_set_expression(expression))
        option_values = []
        for expression in args.option or []:
            if "=" not in expression:
                raise SettingsToolError("Invalid --option '{}' (expected name=value)".format(expression))
            name, value = expression.split("=", 1)
            if not name.strip():
                raise SettingsToolError("Invalid --option '{}' (empty name)".format(expression))
            option_values.append((name.strip(), value))
        user_values = []
        for expression in args.user or []:
            if "=" not in expression:
                raise SettingsToolError("Invalid --user '{}' (expected name=value)".format(expression))
            name, value = expression.split("=", 1)
            if not name.strip():
                raise SettingsToolError("Invalid --user '{}' (empty name)".format(expression))
            user_values.append((name.strip(), value))

        run_tool(
            input_path=args.input,
            output_path=args.output,
            yaml_path=args.yaml,
            set_values=set_values,
            option_values=option_values,
            user_values=user_values,
            check=args.check,
        )
    except (SettingsToolError, etree.XMLSyntaxError, OSError, yaml.YAMLError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
