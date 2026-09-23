"""Render the Dongfang candidate gallery and reproducible synthetic science plots."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import Normalize, TwoSlopeNorm, ListedColormap
from matplotlib.patches import Rectangle

from easyplot_py import (publication_context, make_scientific_plate, plot_bar_pastel,
                         plot_box_jitter, plot_timecourse, format_axes, add_panel_tag,
                         export_figure, write_manifest)
import matplotlib.pyplot as plt
from easyplot_dongfang import registry, dongfang_palette, dongfang_cmap
from easyplot_palette_audit import audit_palette, grayscale_hex, cie_lstar, parse_hex
from easyplot_metadata import inspect_file

GROUPS = ['A', 'B', 'C', 'D']
MARKERS = dict(zip(GROUPS, ['o', '^', 's', 'D']))
LINES = dict(zip(GROUPS, ['-', '--', '-.', ':']))
SEED = 230926


def data_files(output):
    paths = [output / name for name in ('observations.csv', 'trajectories.csv', 'magnitude.csv')]
    if any(p.exists() for p in paths) and not all(p.exists() for p in paths):
        raise FileExistsError('Partial source-data bundle: use a new output directory or restore all three CSVs')
    if not all(p.exists() for p in paths):
        rng = np.random.default_rng(SEED)
        observations = []
        for i, group in enumerate(GROUPS):
            x = rng.normal(1.4 + 0.35 * i, 0.43, 24)
            response = rng.normal([3.3, 4.5, 6.0, 5.2][i], [0.55, 0.8, 0.72, 0.88][i], 24)
            y = 0.55 * x + 0.2 * i + rng.normal(0, 0.18, 24)
            observations.extend({'group': group, 'replicate': j + 1, 'response': response[j], 'x': x[j], 'y': y[j]}
                                for j in range(24))
        raw = pd.DataFrame(observations)
        values = [[1.1, 1.4, 1.6, 2.3, 2.0, 2.7, 2.9], [1.0, 1.9, 2.1, 2.7, 3.4, 3.1, 4.0],
                  [1.4, 2.0, 2.8, 2.5, 3.2, 3.7, 3.5], [0.9, 1.5, 2.4, 2.0, 2.9, 3.1, 4.5]]
        trajectories = pd.DataFrame([{'group': group, 'time': t, 'estimate': v}
                                     for group, ys in zip(GROUPS, values) for t, v in zip(range(0, 73, 12), ys)])
        x, y = np.meshgrid(np.linspace(-2, 2, 8), np.linspace(-2, 2, 8))
        matrix = np.exp(-((x - .7) ** 2 + (y + .5) ** 2) / 2) + .3 * np.exp(-((x + 1.1) ** 2 + (y - 1) ** 2))
        matrix = (matrix - matrix.min()) / (matrix.max() - matrix.min())
        matrix[2, 4] = np.nan
        raw.to_csv(paths[0], index=False, mode='x')
        trajectories.to_csv(paths[1], index=False, mode='x')
        pd.DataFrame(matrix).to_csv(paths[2], index=False, mode='x')
    return pd.read_csv(paths[0]), pd.read_csv(paths[1]), pd.read_csv(paths[2]).to_numpy()


def summary(raw):
    table = raw.groupby('group', observed=True)['response'].agg(['mean', 'std']).reindex(GROUPS).reset_index()
    return table.assign(estimate=table['mean'], lower=table['mean'] - table['std'], upper=table['mean'] + table['std'])


def mappings(name):
    return dict(zip(GROUPS, dongfang_palette(name, 4))), dict(zip(GROUPS, dongfang_palette(name, 4, role='line')))


def draw_bar(ax, name, raw, classic=False):
    fills, _ = mappings(name)
    if classic:
        fills = dict(zip(GROUPS, registry()['palettes'][name]['classic']['fill'][:4]))
    plot_bar_pastel(ax, summary(raw), condition='group', lower='lower', upper='upper',
                    raw=raw, raw_value='response', palette=fills, order=GROUPS, seed=SEED)
    ax.set(ylim=(0, 8.3), ylabel='Response (a.u.)')
    ax.set_yticks([0, 2, 4, 6, 8])


def four_panel(name, raw, trajectories):
    fills, strokes = mappings(name)
    fig, axes = make_scientific_plate(width_mm=180, height_mm=135, dpi=300)
    draw_bar(axes[0, 0], name, raw)
    plot_box_jitter(axes[0, 1], raw, condition='group', value='response', order=GROUPS, palette=fills, seed=SEED)
    axes[0, 1].set(ylim=(0, 8.3), ylabel='Response (a.u.)')
    axes[0, 1].set_yticks([0, 2, 4, 6, 8])
    plot_timecourse(axes[1, 0], trajectories, series='group', palette=strokes, markers=MARKERS, linestyles=LINES)
    axes[1, 0].set(xlim=(-3, 86), ylim=(.5, 5.1), xlabel='Time (h)', ylabel='Response (a.u.)')
    axes[1, 0].set_xticks([0, 24, 48, 72])
    for group in GROUPS:
        final = trajectories[trajectories.group == group].iloc[-1]
        axes[1, 0].annotate(group, (72, final['estimate']), (78, final['estimate']),
                             va='center', fontsize=7, color='#303030',
                             arrowprops={'arrowstyle': '-', 'color': strokes[group], 'lw': .6})
        points = raw[raw.group == group]
        axes[1, 1].scatter(points.x, points.y, s=13, marker=MARKERS[group], color=strokes[group],
                           edgecolor='white', linewidth=.3, alpha=.88, label=group)
    axes[1, 1].set(xlim=(0, 3.5), ylim=(0, 2.6), xlabel='Feature 1 (a.u.)', ylabel='Feature 2 (a.u.)')
    axes[1, 1].legend(frameon=False, ncol=4, loc='upper left', handletextpad=.25, columnspacing=.7)
    format_axes(axes[1, 1])
    for tag, ax in zip('abcd', axes.flat):
        add_panel_tag(ax, tag, x=-.12, y=1.04, fontsize=9)
    fig.canvas.draw()
    boxes = [ax.get_position() for ax in axes.flat]
    assert abs(boxes[0].x0 - boxes[2].x0) < 1e-6 and abs(boxes[1].x0 - boxes[3].x0) < 1e-6
    assert abs(boxes[0].y1 - boxes[1].y1) < 1e-6 and abs(boxes[2].y1 - boxes[3].y1) < 1e-6
    return fig


def palette_atlas(cjk):
    data = registry()
    fig, axes = plt.subplots(3, 2, figsize=(230 / 25.4, 161 / 25.4))
    fig.subplots_adjust(left=.04, right=.96, bottom=.09, top=.97, wspace=.18, hspace=.2)
    for column, names in enumerate([['danqing', 'qingya', 'qiushan'], ['qingci', 'qinglan', 'qingzhu']]):
        for row, name in enumerate(names):
            ax = axes[row, column]
            ax.axis('off')
            ax.set(xlim=(0, 1), ylim=(0, 1))
            spec = data['palettes'][name]
            ax.text(0, .94, spec['label'], fontproperties=cjk, fontsize=12, va='top', color='#303030')
            ax.text(.19, .90, name, fontsize=8.5, color='#6B7278')
            descriptor = {'danqing': '冷暖对照 · 通用分组', 'qingya': '柔和填色 · 分布与汇总',
                          'qiushan': '暖橙与金黄 · 青绿对照', 'qingci': '青绿递进 · 强度与丰度',
                          'qinglan': '浅黄—青绿—深蓝', 'qingzhu': '青朱两端 · 基准居中'}[name]
            ax.text(0, .69, descriptor, fontproperties=cjk, fontsize=8, color='#575A5D')
            if spec['type'] == 'qualitative':
                n = spec['max_n']
                for i, (fill, line, source_name) in enumerate(zip(spec['fill'], spec['line'], spec['source_names'])):
                    x, width = i / n, .92 / n
                    ax.add_patch(Rectangle((x, .37), width, .22, facecolor=fill, edgecolor='none'))
                    ax.add_patch(Rectangle((x, .28), width, .05, facecolor=line, edgecolor='none'))
                    record = next(item for item in data['source_colours'] if item['name'] == source_name)
                    label = record['aliases'][0] if record['aliases'] else source_name
                    ax.text(x + width / 2, .16, '偏' + label, fontproperties=cjk, fontsize=6.4, ha='center')
                    ax.text(x + width / 2, .045, fill, fontsize=5.8, ha='center', color='#626A70')
            else:
                ax.imshow(np.linspace(0, 1, 257)[None, :], cmap=dongfang_cmap(name), aspect='auto',
                          extent=(0, .97, .31, .58), interpolation='nearest', vmin=0, vmax=1)
                names = ['低', '高'] if spec['type'] == 'sequential' else ['负向', '基准', '正向']
                for x, label in zip(np.linspace(0, .97, len(names)), names):
                    ax.text(x, .15, label, fontproperties=cjk, fontsize=7.5,
                            ha='left' if x == 0 else 'right' if x == .97 else 'center', color='#575A5D')
                ax.text(0, .035, '257 阶 · 基底 ' + spec['classic']['name'],
                        fontproperties=cjk, fontsize=7, color='#6B7278')
    fig.text(.04, .035, '经典底稿微调版  /  填色均为派生色，传统色名表示微调方向；保留经典亮度结构，细条为较深线色。',
             fontproperties=cjk, fontsize=8, color='#626A70')
    return fig


def category_comparison(raw, cjk):
    fig, axes = plt.subplots(1, 3, figsize=(230 / 25.4, 85 / 25.4))
    fig.subplots_adjust(left=.065, right=.98, top=.79, bottom=.16, wspace=.38)
    for ax, name in zip(axes, ['danqing', 'qingya', 'qiushan']):
        draw_bar(ax, name, raw)
        ax.text(0, 1.15, registry()['palettes'][name]['label'], transform=ax.transAxes,
                fontproperties=cjk, fontsize=11, color='#303030')
    assert all(np.array_equal([p.get_height() for p in axes[0].patches], [p.get_height() for p in ax.patches]) for ax in axes[1:])
    return fig


def continuous_examples(matrix, cjk):
    fig = plt.figure(figsize=(210 / 25.4, 91 / 25.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, .065], left=.065, right=.975, bottom=.19, top=.85,
                         hspace=.28, wspace=.34)
    axes = []
    for col, name in enumerate(['qingci', 'qinglan', 'qingzhu']):
        ax, cax = fig.add_subplot(gs[0, col]), fig.add_subplot(gs[1, col])
        values = matrix if col < 2 else 2 * matrix - 1
        norm = Normalize(0, 1) if col < 2 else TwoSlopeNorm(0, vmin=-1, vmax=1)
        img = ax.imshow(values, cmap=dongfang_cmap(name), norm=norm, aspect='auto', interpolation='nearest')
        missing_y, missing_x = np.where(~np.isfinite(values))
        ax.scatter(missing_x, missing_y, marker='x', s=13, color='#575A5D', linewidths=.7)
        ax.set_xticks([0, 3, 7], ['M1', 'M4', 'M8'])
        ax.set_yticks([0, 3, 7], ['S1', 'S4', 'S8'])
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.text(0, 1.13, registry()['palettes'][name]['label'], transform=ax.transAxes, fontproperties=cjk, fontsize=10.5)
        cb = fig.colorbar(img, cax=cax, orientation='horizontal', ticks=[0, .5, 1] if col < 2 else [-1, 0, 1])
        cb.set_label('Normalized magnitude' if col < 2 else 'Centered score', fontsize=7.2)
        cb.outline.set_linewidth(.5)
        axes.append(ax)
    fig.text(.975, .94, '\u00d7 Missing', ha='right', fontsize=7, color='#575A5D')
    assert np.array_equal(axes[0].images[0].get_array().filled(np.nan), axes[1].images[0].get_array().filled(np.nan), equal_nan=True)
    return fig


def classic_continuous(matrix, cjk):
    """Same values, positions and limits; classic reference above its small edit."""
    fig = plt.figure(figsize=(230 / 25.4, 172 / 25.4))
    gs = fig.add_gridspec(4, 3, height_ratios=[1, .06, 1, .06],
                         left=.10, right=.975, bottom=.095, top=.87, hspace=.40, wspace=.28)
    for col, name in enumerate(['qingci', 'qinglan', 'qingzhu']):
        spec = registry()['palettes'][name]
        values = matrix if col < 2 else 2 * matrix - 1
        norm = Normalize(0, 1) if col < 2 else TwoSlopeNorm(0, vmin=-1, vmax=1)
        for row in range(2):
            ax, cax = fig.add_subplot(gs[row * 2, col]), fig.add_subplot(gs[row * 2 + 1, col])
            cmap = ListedColormap(spec['classic']['fill']) if row == 0 else dongfang_cmap(name)
            cmap.set_bad(registry()['neutrals']['missing'])
            image = ax.imshow(values, cmap=cmap, norm=norm, aspect='auto', interpolation='nearest')
            missing_y, missing_x = np.where(~np.isfinite(values))
            ax.scatter(missing_x, missing_y, marker='x', s=15, color='#575A5D', linewidths=.8)
            ax.set_xticks([0, 3, 7], ['M1', 'M4', 'M8'])
            ax.set_yticks([0, 3, 7], ['S1', 'S4', 'S8'])
            ax.tick_params(length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)
            cb = fig.colorbar(image, cax=cax, orientation='horizontal', ticks=[0, .5, 1] if col < 2 else [-1, 0, 1])
            cb.outline.set_linewidth(.5)
            if row == 0:
                box = ax.get_position()
                fig.text(box.x0, .945, f"{spec['classic']['name']}  →  {spec['label']}",
                         fontproperties=cjk, fontsize=10.5, va='top')
            else:
                cb.set_label('Normalized magnitude' if col < 2 else 'Centered score', fontsize=7)
    fig.text(.025, .725, '经典\n原版', fontproperties=cjk, fontsize=9.5, va='center', linespacing=1.6)
    fig.text(.025, .29, '中国风\n微调', fontproperties=cjk, fontsize=9.5, va='center', linespacing=1.6)
    fig.text(.10, .025, '同一模拟矩阵、同一数值范围；保留经典明暗层次，仅小幅调整色相和彩度。',
             fontproperties=cjk, fontsize=7.5, color='#575A5D')
    fig.text(.975, .025, '\u00d7 Missing', fontsize=7, color='#575A5D', ha='right')
    return fig


def classic_categories(raw, cjk):
    fig, axes = plt.subplots(2, 3, figsize=(230 / 25.4, 156 / 25.4))
    fig.subplots_adjust(left=.13, right=.98, bottom=.08, top=.88, hspace=.27, wspace=.34)
    for col, name in enumerate(['danqing', 'qingya', 'qiushan']):
        spec = registry()['palettes'][name]
        for row in range(2):
            draw_bar(axes[row, col], name, raw, classic=row == 0)
        ax = axes[0, col]
        ax.text(0, 1.16, f"{spec['classic']['name']}  →  {spec['label']}", transform=ax.transAxes,
                fontproperties=cjk, fontsize=10.5)
        assert [p.get_height() for p in axes[0, col].patches] == [p.get_height() for p in axes[1, col].patches]
    fig.text(.025, .705, '经典\n原版', fontproperties=cjk, fontsize=9.5, va='center', linespacing=1.6)
    fig.text(.025, .27, '中国风\n微调', fontproperties=cjk, fontsize=9.5, va='center', linespacing=1.6)
    fig.text(.13, .025, '相同组序、均值、样本标准差与原始点；经典色序按图示重排，底稿和微调版顺序一致。',
             fontproperties=cjk, fontsize=7.3, color='#575A5D')
    return fig


def cvd_preview(path, cjk):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    # The R test writes the actual colorspace simulations, not hand-picked replacements.
    fig, axes = plt.subplots(3, 5, figsize=(230 / 25.4, 86 / 25.4))
    fig.subplots_adjust(left=.09, right=.98, bottom=.13, top=.84, wspace=.24, hspace=.4)
    modes = ['original', 'grayscale', 'protan', 'deutan', 'tritan']
    titles = ['原始', '灰度', '红色觉模拟', '绿色觉模拟', '蓝色觉模拟']
    for row, name in enumerate(['danqing', 'qingya', 'qiushan']):
        fills = dongfang_palette(name)
        for col, mode in enumerate(modes):
            ax = axes[row, col]
            colours = fills if mode == 'original' else [grayscale_hex(x) for x in fills] if mode == 'grayscale' else data['palettes'][name]['fill'][mode]
            ax.set(xlim=(0, len(colours)), ylim=(0, 1))
            ax.axis('off')
            for i, colour in enumerate(colours):
                ax.add_patch(Rectangle((i, .12), .92, .66, color=colour, linewidth=0))
            if row == 0:
                ax.text(.5, 1.3, titles[col], transform=ax.transAxes, fontproperties=cjk, fontsize=8, ha='center')
            if col == 0:
                ax.text(-.12, .45, registry()['palettes'][name]['label'], transform=ax.transAxes,
                        fontproperties=cjk, fontsize=8.5, ha='right', va='center')
    fig.text(.09, .035, '模拟采用 colorspace，severity=1；用于发现潜在混淆，仍需结合最终图形、点形、线型与标签。',
             fontproperties=cjk, fontsize=7.4, color='#626A70')
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--stage', choices=['data', 'all', 'continuous', 'classic', 'cvd'], default='all')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw, trajectories, matrix = data_files(args.output_dir)
    if args.stage == 'data':
        print(f'Synthetic source data ready: {args.output_dir}')
        return
    cjk = font_manager.FontProperties(fname=font_manager.findfont('Microsoft YaHei', fallback_to_default=False))
    with publication_context(base_size=8, font_family='Arial') as font_info:
        if args.stage == 'cvd':
            figures = [('dongfang_cvd_screen', cvd_preview(args.output_dir / 'cvd_simulations.json', cjk))]
        elif args.stage == 'continuous':
            figures = [('dongfang_continuous_examples', continuous_examples(matrix, cjk))]
        elif args.stage == 'classic':
            figures = [('dongfang_classic_continuous', classic_continuous(matrix, cjk)),
                       ('dongfang_classic_categories', classic_categories(raw, cjk))]
        else:
            figures = [('dongfang_palette_atlas', palette_atlas(cjk)),
                       ('dongfang_same_data_bars', category_comparison(raw, cjk)),
                       ('dongfang_continuous_examples', continuous_examples(matrix, cjk))]
            figures.extend((f'{name}_four_panel_Python', four_panel(name, raw, trajectories))
                           for name in ['danqing', 'qingya', 'qiushan'])
            figures.extend([('dongfang_classic_continuous', classic_continuous(matrix, cjk)),
                            ('dongfang_classic_categories', classic_categories(raw, cjk))])
        qa = []
        for name, fig in figures:
            provenance = {'synthetic': True, 'seed': SEED, 'sources': ['observations.csv', 'trajectories.csv', 'magnitude.csv'],
                          'uncertainty': 'bar: sample mean +/- sample SD, n=24/group; curves: illustrative values, no CI',
                          'palette_registry_version': registry()['version'], 'palette_source': registry()['source'],
                          'palette_classic_sources': registry()['classic_sources'],
                          'palette_status': 'classic-based candidates; fills are derived, source-colour lookups remain original',
                          'fonts': {**font_info, 'CJK': 'Microsoft YaHei'},
                          'canvas_text': 'comparison/atlas/heatmap descriptors are teaching labels; four-panel exports have tags/axes only',
                          'missing': 'one synthetic missing matrix cell at S3/M5; neutral grey with X and a Missing key',
                          'diverging_transform': 'centered_score = 2*normalized_magnitude - 1; vmin=-1, center=0, vmax=1'}
            bundle = export_figure(fig, args.output_dir / name, formats=('png', 'pdf'), dpi=300,
                                   overwrite=args.overwrite, provenance=provenance)
            qa.extend(inspect_file(p, min_dpi=300, target_width_mm=fig.get_figwidth() * 25.4, alpha_policy='forbid')
                      for p in bundle['outputs'])
            plt.close(fig)
        write_manifest(args.output_dir / f'{args.stage}_artifact_audits.json', overwrite=args.overwrite, reports=qa)
        assert all(not q['errors'] and not q['warnings'] for q in qa), 'Review artifact audit JSON'
    if args.stage == 'all':
        audits = {}
        for name in ['danqing', 'qingya', 'qiushan']:
            spec = registry()['palettes'][name]
            fill = dict(zip(spec['source_names'], spec['fill']))
            line = dict(zip(spec['source_names'], spec['line']))
            audits[name] = {'fill': audit_palette(fill, geometry='bar', cues=('position-labels', 'outline')),
                            'line': audit_palette(line, geometry='line', cues=('markers', 'linestyles', 'direct-labels'),
                                                  foreground_placement='outside-marks')}
        write_manifest(args.output_dir / 'palette_audits.json', overwrite=args.overwrite, palettes=audits)
    print(f'Rendered {len(figures)} PNG/PDF pairs; same-data and metadata checks passed: {args.output_dir}')


if __name__ == '__main__':
    main()
