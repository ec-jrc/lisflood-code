import pytest
from lxml import etree

from lisflood.settings_tool import main


SAMPLE_XML = """\
<lfsettings>
  <!-- top-level comment -->
  <lfoptions>
    # option note
    <setoption choice="0" name="TemperatureInKelvin"/>
    <setoption choice="1" name="wateruse"/>
  </lfoptions>
  <lfuser>
    <group>
      <textvar name="PathRoot" value="/tmp/project"/>
      <textvar name="SharedVar" value="/tmp/project/shared">
        <comment>Keep me</comment>
      </textvar>
      <textvar name="SomeUserVar" value="abc"/>
    </group>
  </lfuser>
  <lfbinding>
    <group>
      <textvar name="SharedVar" value="$(PathRoot)/shared"/>
      <textvar name="MaskMap" value="$(PathRoot)/mask.nc"/>
    </group>
  </lfbinding>
</lfsettings>
"""


def _write(path, content):
    path.write_text(content, encoding="utf-8")


def _parse(path):
    return etree.parse(str(path))


class TestSettingsTool:
    def test_set_clean_rewrite_and_comment_propagation(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "clean.xml"
        _write(src, SAMPLE_XML)

        rc = main(["set", "-i", str(src), "-o", str(dst)])
        assert rc == 0
        assert dst.exists()

        output = dst.read_text(encoding="utf-8")
        assert "top-level comment" in output
        assert "Keep me" in output

        tree = _parse(dst)
        assert tree.getroot().tag == "lfsettings"

    def test_set_file_and_cli_updates_with_list_values(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "updated.xml"
        yml = tmp_path / "updates.yaml"
        _write(src, SAMPLE_XML)
        _write(
            yml,
            "lfoptions:\n  TemperatureInKelvin: 1\nlfuser:\n  SomeUserVar: from-yaml\n",
        )

        rc = main(
            [
                "set",
                "-i",
                str(src),
                "-o",
                str(dst),
                "--file",
                str(yml),
                "--lfoptions",
                "wateruse=0",
                "TemperatureInKelvin=1",
                "--lfuser",
                "SomeUserVar=from-cli",
                "PathRoot=/data/root",
            ]
        )
        assert rc == 0

        tree = _parse(dst)
        options = {n.get("name"): n.get("choice") for n in tree.findall(".//lfoptions//setoption")}
        users = {n.get("name"): n.get("value") for n in tree.findall(".//lfuser//textvar")}

        assert options["TemperatureInKelvin"] == "1"
        assert options["wateruse"] == "0"
        assert users["SomeUserVar"] == "from-cli"
        assert users["PathRoot"] == "/data/root"

    def test_set_allows_repeating_lfoptions_and_lfuser_flags(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "updated.xml"
        _write(src, SAMPLE_XML)

        rc = main(
            [
                "set",
                "-i",
                str(src),
                "-o",
                str(dst),
                "--lfoptions",
                "TemperatureInKelvin=1",
                "--lfoptions",
                "wateruse=0",
                "--lfuser",
                "SomeUserVar=from-cli",
                "--lfuser",
                "PathRoot=/alternate/root",
            ]
        )
        assert rc == 0

        tree = _parse(dst)
        options = {n.get("name"): n.get("choice") for n in tree.findall(".//lfoptions//setoption")}
        users = {n.get("name"): n.get("value") for n in tree.findall(".//lfuser//textvar")}
        assert options["TemperatureInKelvin"] == "1"
        assert options["wateruse"] == "0"
        assert users["SomeUserVar"] == "from-cli"
        assert users["PathRoot"] == "/alternate/root"

    def test_check_mode_no_output_written(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "check-output.xml"
        _write(src, SAMPLE_XML)

        rc = main(["check", "-i", str(src)])
        assert rc == 0
        assert not dst.exists()

    def test_rejects_binding_edits_from_file_inputs(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "updated.xml"
        yml = tmp_path / "updates.yaml"
        _write(src, SAMPLE_XML)
        _write(yml, "lfbinding:\n  MaskMap: /tmp/new-mask.nc\n")

        rc = main(["set", "-i", str(src), "-o", str(dst), "--file", str(yml)])
        assert rc == 0

        tree = _parse(dst)
        bindings = {n.get("name"): n.get("value") for n in tree.findall(".//lfbinding//textvar")}
        assert bindings["MaskMap"] == "$(PathRoot)/mask.nc"

    def test_removed_set_option_is_rejected(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "updated.xml"
        _write(src, SAMPLE_XML)

        with pytest.raises(SystemExit):
            main(["set", "-i", str(src), "-o", str(dst), "--set", "lfuser.SomeUserVar=abc"])

    def test_lfoptions_rejects_non_key_value_token(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "updated.xml"
        _write(src, SAMPLE_XML)

        with pytest.raises(SystemExit):
            main(["set", "-i", str(src), "-o", str(dst), "--lfoptions", "wateruse=1", "not-a-pair"])
