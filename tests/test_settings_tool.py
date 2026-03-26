import pytest
from lxml import etree

from lisflood.settings_tool import main, SettingsToolError


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

SAMPLE_BAD_REF_XML = """\
<lfsettings>
  <lfoptions>
    <setoption choice="0" name="wateruse"/>
  </lfoptions>
  <lfuser>
    <group>
      <textvar name="PathRoot" value="/data"/>
      <textvar name="MaskMap" value="$(UndefinedVar)/mask.nc"/>
    </group>
  </lfuser>
  <lfbinding>
    <group>
      <textvar name="MaskMap" value="$(MaskMap)"/>
    </group>
  </lfbinding>
</lfsettings>
"""

SAMPLE_BAD_BINDING_REF_XML = """\
<lfsettings>
  <lfoptions>
    <setoption choice="0" name="wateruse"/>
  </lfoptions>
  <lfuser>
    <group>
      <textvar name="PathRoot" value="/data"/>
    </group>
  </lfuser>
  <lfbinding>
    <group>
      <textvar name="MaskMap" value="$(NoSuchVar)/mask.nc"/>
    </group>
  </lfbinding>
</lfsettings>
"""

SAMPLE_XML_B = """\
<lfsettings>
  <lfoptions>
    <setoption choice="1" name="TemperatureInKelvin"/>
    <setoption choice="0" name="wateruse"/>
  </lfoptions>
  <lfuser>
    <group>
      <textvar name="PathRoot" value="/data/root"/>
      <textvar name="SharedVar" value="/tmp/project/shared"/>
      <textvar name="SomeUserVar" value="xyz"/>
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

    def test_check_validates_refs_ok(self, tmp_path):
        src = tmp_path / "settings.xml"
        _write(src, SAMPLE_XML)

        rc = main(["check", "-i", str(src)])
        assert rc == 0

    def test_check_catches_undefined_lfuser_ref(self, tmp_path):
        src = tmp_path / "bad.xml"
        _write(src, SAMPLE_BAD_REF_XML)

        rc = main(["check", "-i", str(src)])
        assert rc == 1

    def test_check_catches_undefined_lfbinding_ref(self, tmp_path):
        src = tmp_path / "bad.xml"
        _write(src, SAMPLE_BAD_BINDING_REF_XML)

        rc = main(["check", "-i", str(src)])
        assert rc == 1

    def test_check_allows_builtin_vars(self, tmp_path):
        xml = """\
<lfsettings>
  <lfoptions/>
  <lfuser>
    <group>
      <textvar name="PathRoot" value="$(SettingsPath)/../../root"/>
    </group>
  </lfuser>
  <lfbinding>
    <group>
      <textvar name="MaskMap" value="$(PathRoot)/mask.nc"/>
    </group>
  </lfbinding>
</lfsettings>
"""
        src = tmp_path / "builtin.xml"
        _write(src, xml)

        rc = main(["check", "-i", str(src)])
        assert rc == 0

    def test_diff_identical_files(self, tmp_path, capsys):
        src = tmp_path / "a.xml"
        _write(src, SAMPLE_XML)

        rc = main(["diff", "-i", str(src), "-o", str(src)])
        assert rc == 0
        assert "No differences" in capsys.readouterr().out

    def test_diff_shows_changes(self, tmp_path, capsys):
        a = tmp_path / "a.xml"
        b = tmp_path / "b.xml"
        _write(a, SAMPLE_XML)
        _write(b, SAMPLE_XML_B)

        rc = main(["diff", "-i", str(a), "-o", str(b)])
        assert rc == 0

        out = capsys.readouterr().out
        assert "TemperatureInKelvin" in out
        assert "wateruse" in out
        assert "PathRoot" in out
        assert "SomeUserVar" in out
        assert "Equivalent command" in out
        # Generated command uses real paths with _copy suffix
        assert str(a) in out
        assert "b_copy.xml" in out
        # Values are single-quoted for shell safety
        assert "'PathRoot=/data/root'" in out
