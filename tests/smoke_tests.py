import os

from lisflood.global_modules.globals import binding
from lisflood.lisf1 import Lisfloodexe, get_optionxml_path

from tests import listest, reference_files


current_dir = os.path.dirname(os.path.abspath(__file__))


class TestDrina(object):
    settings_path = os.path.join(current_dir, 'data/Drina/settings/lisfloodSettings_cold_day_base.xml')

    @classmethod
    def setup_class(cls):
        optionxml = get_optionxml_path()
        Lisfloodexe(cls.settings_path, optionxml)

    @classmethod
    def teardown_class(cls):
        for var, obj in reference_files.items():
            output_nc = binding[reference_files[var]['report_map']]
            output_nc = output_nc + '.nc'
            if os.path.exists(output_nc):
                os.remove(output_nc)
            output_tss = binding[reference_files[var]['report_tss']]
            if os.path.exists(output_tss):
                os.remove(output_tss)

    @listest('dis')
    def test_dis(self):
        pass
