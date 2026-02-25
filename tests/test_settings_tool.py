from pathlib import Path

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
    def test_clean_rewrite_and_comment_propagation(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "clean.xml"
        _write(src, SAMPLE_XML)

        rc = main([str(src), str(dst)])
        assert rc == 0
        assert dst.exists()

        output = dst.read_text(encoding="utf-8")
        assert "top-level comment" in output
        assert "Keep me" in output

        tree = _parse(dst)
        assert tree.getroot().tag == "lfsettings"

    def test_yaml_and_cli_updates(self, tmp_path):
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
                str(src),
                str(dst),
                "--yaml",
                str(yml),
                "--option",
                "wateruse=0",
                "--user",
                "SomeUserVar=from-cli",
            ]
        )
        assert rc == 0

        tree = _parse(dst)
        options = {n.get("name"): n.get("choice") for n in tree.findall(".//lfoptions//setoption")}
        users = {n.get("name"): n.get("value") for n in tree.findall(".//lfuser//textvar")}

        assert options["TemperatureInKelvin"] == "1"
        assert options["wateruse"] == "0"
        assert users["SomeUserVar"] == "from-cli"

    def test_check_mode_no_output_written(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "check-output.xml"
        _write(src, SAMPLE_XML)

        rc = main([str(src), str(dst), "--check"])
        assert rc == 0
        assert not dst.exists()

    def test_check_allows_unresolved_binding_reference(self, tmp_path):
        src = tmp_path / "settings.xml"
        bad_xml = SAMPLE_XML.replace(
            'name="MaskMap" value="$(PathRoot)/mask.nc"',
            'name="MaskMap" value="$(MissingRoot)/mask.nc"',
        )
        _write(src, bad_xml)

        rc = main([str(src), "--check"])
        assert rc == 0

    def test_rejects_binding_edits_from_inputs(self, tmp_path):
        src = tmp_path / "settings.xml"
        dst = tmp_path / "updated.xml"
        yml = tmp_path / "updates.yaml"
        _write(src, SAMPLE_XML)
        _write(yml, "lfbinding:\n  MaskMap: /tmp/new-mask.nc\n")

        rc = main([str(src), str(dst), "--yaml", str(yml)])
        assert rc == 0

        tree = _parse(dst)
        bindings = {n.get("name"): n.get("value") for n in tree.findall(".//lfbinding//textvar")}
        assert bindings["MaskMap"] == "$(PathRoot)/mask.nc"
