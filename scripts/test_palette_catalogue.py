"""Source-identity and generated catalogue checks; optional delivered-file audit."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from build_palettes import parse_ggsci
from build_palette_gallery import text_colour
from easyplot_palettes import easyplot_palette, easyplot_palette_info

ROOT = Path(__file__).resolve().parents[1]


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.copies, self.fields = [], [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.fields.add(attrs['id'])
        if tag == 'button' and 'data-copy' in attrs:
            self.copies.append(attrs['data-copy'])
        if tag == 'article' and attrs.get('class') == 'card':
            self.ids.append(attrs['data-id'])


def lightness(colour):
    rgb = [int(colour[p:p + 2], 16) / 255 for p in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    y = sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
    return 116 * y ** (1 / 3) - 16 if y > (6 / 29) ** 3 else y * (29 / 3) ** 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gallery', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    registry = json.loads((ROOT / 'assets/palettes.json').read_text(encoding='utf-8'))
    palettes = {p['id']:p for p in registry['palettes']}
    assert len(palettes) == len(registry['palettes'])
    assert registry['coverage']['families'] == dict(Counter(p['family'] for p in palettes.values()))
    source_root = ROOT / 'assets/palette-sources'
    upstream = parse_ggsci((source_root / 'ggsci-palettes.R').read_text(encoding='utf-8'))
    upstream += parse_ggsci((source_root / 'ggsci-palettes-iterm.R').read_text(encoding='utf-8'), iterm=True)
    for original in upstream:
        stored = palettes[original['id']]
        assert original['colours'] == stored.get('anchors', stored['colours']), original['id']
        if original['kind'] == 'qualitative':
            assert original['colour_names'] == stored['colour_names'], original['id']
    assert len(upstream) == registry['coverage']['families']['ggsci']
    assert easyplot_palette('ggsci.npg.nrc', 3) == ['#E64B35','#4DBBD5','#00A087']

    dongfang = json.loads((ROOT / 'assets/dongfang.json').read_text(encoding='utf-8'))
    original_hex = {c['name']:c['hex'] for c in dongfang['source_colours']}
    recipes = json.loads((ROOT / 'assets/china-palette-recipes.json').read_text(encoding='utf-8'))
    for recipe in recipes['palettes']:
        p = palettes[recipe['id']]
        assert p['colour_names'] == recipe['names']
        assert p['colours'] == [original_hex[name] for name in recipe['names']]
        assert easyplot_palette(p['id']) == p['colours']
        if p['kind'] == 'sequential':
            ls = list(map(lightness,p['colours']))
            assert all(a > b for a,b in zip(ls,ls[1:])), (p['id'],ls)
    for key,spec in dongfang['palettes'].items():
        assert easyplot_palette('dongfang.' + key) == spec['fill']

    catalogue = ROOT / 'assets/palette-gallery'
    cards = Cards()
    cards.feed((catalogue / 'index.html').read_text(encoding='utf-8'))
    assert len(cards.ids) == len(palettes) == len(set(cards.ids))
    assert set(palettes) == set(cards.ids)
    assert set(palettes) <= set(cards.copies)
    assert {'search','family','kind','cvd','extensions','reset'} <= cards.fields
    calls = [s for s in cards.copies if s.startswith('easyplot_palette(')]
    assert len(calls) == len(palettes)
    for call in calls:
        match = re.fullmatch(r'easyplot_palette\("([^"]+)", n = (\d+)\)',call)
        assert match, call
        assert len(easyplot_palette(match[1],int(match[2]))) == int(match[2]), call
    # Every colour in every exported default/native/anchor table is attributable.
    csv_count = 0
    with (catalogue / 'all-colours.csv').open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            p = palettes[row['id']]
            scheme = p['colours'] if row['variant_n'] == 'default' else p['anchors'] if row['variant_n'] == 'source_anchors' else p['native_sizes'][row['variant_n']]
            assert scheme[int(row['index'])-1] == row['hex']
            csv_count += 1
    assert text_colour('#FFFFFF') == '#000000' and text_colour('#000000') == '#FFFFFF'
    checks = dict(status='passed', palettes=len(palettes), original_ggsci_tables=len(upstream),
                  china_source_schemes=len(recipes['palettes']), catalogue_cards=len(cards.ids),
                  executable_copy_snippets=len(calls), csv_rows=csv_count)
    if args.gallery:
        from easyplot_metadata import inspect_file
        reports = []
        for path in sorted(args.gallery.glob('*.png')):
            height = 177.8 if path.stem == '06-cvd-simulation' else 254
            report = inspect_file(path, min_dpi=300, target_width_mm=304.8,
                                  target_height_mm=height, alpha_policy='forbid')
            assert not report['warnings'] and not report['errors'], report
            reports.append(report)
        report = inspect_file(args.gallery / 'palette-atlas.pdf', target_width_mm=304.8,
                              target_height_mm=254, require_embedded_fonts=True)
        assert not report['warnings'] and not report['errors'], report
        atlas = json.loads((args.gallery / 'palette-atlas.manifest.json').read_text(encoding='utf-8'))
        represented = [id for page in atlas['pages'] for id in page['ids']]
        core = [p['id'] for p in palettes.values() if 'extension' not in p.get('tags',[])]
        assert Counter(represented) == Counter(core)
        assert report['properties']['pages'] == len(atlas['pages'])
        reports.append(report)
        checks['artifacts'] = reports
        checks['atlas_pages'] = len(atlas['pages'])
        checks['atlas_core_palettes'] = len(core)
    if args.report:
        with args.report.open('x',encoding='utf-8') as stream:
            json.dump(checks,stream,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in checks.items() if k != 'artifacts'},ensure_ascii=False))


if __name__ == '__main__':
    main()
