"""Small executable contract test for the opt-in Dongfang palette family."""
import argparse
import json
from pathlib import Path
import numpy as np
from easyplot_dongfang import dongfang_color, dongfang_palette, dongfang_cmap, registry
from easyplot_palette_audit import cie_lstar, parse_hex, contrast_ratio


def main(r_fixture=None):
    data = registry()
    assert len(data["source_colours"]) == 320
    assert dongfang_color("朱砂") == dongfang_color("硃砂") == "#B84B48"
    assert dongfang_color("奶绿") == "#AFC8BA"
    assert data['palettes']['moyun']['fill'] == data['palettes']['moyun']['classic']['fill']
    assert data['palettes']['moyun']['derived'] is False
    for name, spec in data["palettes"].items():
        assert spec['classic']['name']
        assert len(spec['classic']['fill']) == len(spec['fill'])
        assert spec['fill_derivation']['max_delta_Lstar'] <= .3
        assert spec['fill_derivation']['max_delta_E00'] <= 5
        if spec["type"] == "qualitative":
            fill = dongfang_palette(name)
            line = dongfang_palette(name, role="line")
            assert fill[:3] == dongfang_palette(name, n=3)
            assert len(fill) == spec["max_n"] == len(line)
            assert all(contrast_ratio(parse_hex(x), (1, 1, 1)) >= 4.5 for x in line)
            try:
                dongfang_palette(name, n=len(fill) + 1)
            except ValueError:
                pass
            else:
                raise AssertionError("Qualitative palettes must not recycle colours")
            try:
                dongfang_cmap(name)
            except ValueError:
                pass
            else:
                raise AssertionError("Category colours must not silently become a continuous ramp")
        else:
            ramp = dongfang_palette(name)
            assert len(ramp) == 257
            light = np.array([cie_lstar(parse_hex(x)) for x in ramp])
            if spec["type"] == "sequential":
                assert np.max(np.diff(light)) <= 0.12  # 8-bit rounding only
                assert np.ptp(light) > 65  # don't compress the classic range into a greyish band
            else:
                assert np.min(np.diff(light[:129])) >= -0.12
                assert np.max(np.diff(light[128:])) <= 0.12
                assert abs(light[0] - light[-1]) < 3
            assert dongfang_cmap(name).N == 257
    for bad in (0, -1, 1.5, True):
        try:
            dongfang_palette("danqing", n=bad)
        except ValueError:
            pass
        else:
            raise AssertionError("n must be a positive integer")
    for bad in (0, 1, 'false', None):
        try:
            dongfang_palette('qingya', reverse=bad)
        except ValueError:
            pass
        else:
            raise AssertionError('reverse must be a boolean, consistently with the R interface')
    # Returning a fresh registry prevents a caller from changing global colours.
    data["palettes"]["danqing"]["fill"][0] = "#FFFFFF"
    assert dongfang_palette("danqing")[0] != "#FFFFFF"
    if r_fixture is not None:
        fixture = json.loads(r_fixture.read_text(encoding='utf-8-sig'))
        assert fixture['registry_version'] == registry()['version']
        assert set(fixture['palettes']) == set(data['palettes'])
        for name, spec in fixture['palettes'].items():
            for role in ('fill', 'line'):
                if role in spec:
                    assert dongfang_palette(name, role=role) == spec[role], (name, role)
            for n, colours in spec.get('samples', {}).items():
                assert dongfang_palette(name, n=int(n)) == colours, (name, n)
        print('R/Python parity passed: all seven palettes, fill/line roles and stored resampling cases.')
    print("Dongfang contracts passed: source names, capacities, roles, ramps and isolation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r-fixture', type=Path)
    main(parser.parse_args().r_fixture)
