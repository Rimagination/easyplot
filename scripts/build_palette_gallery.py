"""Build a self-contained, searchable local palette catalogue and full HEX CSV.

No hosting, external scripts, telemetry, package installation or network access.
The static HTML preserves all swatches; iTerm extensions are initially hidden.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIND = dict(qualitative="分类", sequential="顺序", diverging="发散", cyclic="循环", multisequential="多段")
CVD = dict(reported="色觉友好设计有来源", conditional="色觉适用有条件", not_assessed="色觉表现未评估", not_recommended="慎用于色觉友好任务")
FAMILY = dict(ggsci="ggsci", brewer="Brewer", viridis="viridis", matplotlib="MPL",
              cud="CUD", tol="Tol", scico="SCM", cmocean="cmocean",
              cetcolor="CET", colorspace="HCL", china="东方原色", dongfang="东方衍生")


def text_colour(colour):
    values = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    lum = sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
    return "#000000" if (lum + .05) / .05 >= 1.05 / (lum + .05) else "#FFFFFF"


def palette_card(p, colour_aliases):
    esc = html.escape
    colours = p["colours"]
    names = p.get("colour_names", [])
    if p["kind"] == "qualitative" or len(colours) <= 60:
        swatches = "".join(
            f'<div class="swatch" style="background:{c};color:{text_colour(c)}" title="{esc(names[i] if i < len(names) else str(i+1))}">'
            + (f'<span>{esc(names[i])}</span>' if p["family"] == "china" and i < len(names) else "")
            + f'<code>{c}</code></div>' for i, c in enumerate(colours))
        swatches = '<div class="swatches">' + swatches + '</div>'
    else:
        stops = ",".join(f"{c} {100*i/len(colours):.5f}% {100*(i+1)/len(colours):.5f}%" for i,c in enumerate(colours))
        swatches = f'<div role="img" aria-label="{esc(p["id"])}: {len(colours)} 个固定色阶" class="ramp" style="background:linear-gradient(to right,{stops})"></div>'
        samples = [colours[round(i * (len(colours)-1)/4)] for i in range(5)]
        swatches += '<div class="stops">' + ''.join(f'<code>{c}</code>' for c in samples) + '</div>'
    count = f'{len(colours)} 色' if p["kind"] == "qualitative" else f'{len(colours)} 级'
    n = min(6, len(colours)) if p["kind"] == "qualitative" else min(256, len(colours))
    call = f'easyplot_palette("{p["id"]}", n = {n})'
    status = p["cvd"]["status"]
    cvd = p["cvd"]
    targets = cvd.get("targets") or []
    target_labels = {"protan": "Protan", "deutan": "Deutan", "tritan": "Tritan"}
    target_line = "" if not targets else "<p>设计目标：" + esc(" / ".join(target_labels.get(v, v) for v in targets)) + "</p>"
    by_n = cvd.get("by_n", {})
    status_labels = {"reported": "有来源支持", "conditional": "有条件", "not_recommended": "谨慎使用", "not_assessed": "未评估"}
    by_n_line = "" if not by_n else "<p>按类别数评价：" + esc("；".join(f"{n} 色：{status_labels.get(flag, flag)}" for n, flag in by_n.items())) + "</p>"
    source_name_line = "" if not p.get("source_map_name") else "<p>原始色表名：" + esc(p["source_map_name"]) + "</p>"
    full_label_line = "" if not p.get("label_full") else "<p>完整标签：" + esc(p["label_full"]) + "</p>"
    extension = "extension" in p.get("tags", [])
    shortlist = "cvd-shortlist" in p.get("tags", [])
    url = p["source"]["url"]
    aliases = [alias for name in names for alias in colour_aliases.get(name, [])] if p["family"] == "china" else []
    search = " ".join([p["id"], p["label"], p.get("label_full", ""), p["family"], p.get("source_map_name", ""),
                       *names, *aliases, *p.get("tags", []), *targets, *by_n.keys(), *by_n.values()]).lower()
    return f'''<article class="card" data-id="{esc(p['id'])}" data-family="{esc(p['family'])}" data-kind="{esc(p['kind'])}" data-cvd="{esc(status)}" data-cvd-shortlist="{str(shortlist).lower()}" data-extension="{str(extension).lower()}" data-search="{esc(search)}" {'hidden' if extension else ''}>
<div class="cardhead"><h2>{esc(p['label'])}</h2><span>{KIND[p['kind']]} · {count}</span></div>
<div class="idrow"><code class="palette-id">{esc(p['id'])}</code><button type="button" class="copy" data-copy="{esc(p['id'])}" aria-label="复制 {esc(p['id'])}">复制 ID</button></div>
{swatches}
<div class="badge {status}">{CVD[status]}</div>
<details><summary>来源、限制与调用</summary>
<p>{esc(p.get('notes',''))}</p>{full_label_line}<p>{esc(cvd.get('note',''))}</p>{target_line}{by_n_line}{source_name_line}
<p>来源：<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(url)}</a><br>版本：{esc(str(p['source'].get('version','')))}<br>许可：{esc(p['source'].get('license',''))}</p>
<p>载入 EasyPlot 模块后，R / Python 都使用以下唯一 ID：</p><pre>{esc(call)}</pre>
<button type="button" class="copy" data-copy="{esc(call)}">复制调用</button>
<p>反向：R 用 reverse = TRUE；Python 用 reverse=True。分类色不自动循环，ColorBrewer 按 n 取原生分级方案。</p>
</details></article>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--registry", type=Path, default=ROOT / "assets/palettes.json")
    parser.add_argument("--overwrite", action="store_true", help="explicitly replace generated catalogue files")
    args = parser.parse_args()
    data = json.loads(args.registry.read_text(encoding="utf-8"))
    palettes = data["palettes"]
    targets = [args.output_dir / name for name in ("index.html", "all-colours.csv", "catalogue-summary.json")]
    if any(p.exists() for p in targets) and not args.overwrite:
        raise FileExistsError("Catalogue outputs already exist; choose a new directory")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    core = [p for p in palettes if "extension" not in p.get("tags", [])]
    extensions = len(palettes) - len(core)
    counts = Counter(p["family"] for p in palettes)
    # Explicit priority does not reorder a palette's internal colours.
    family_order = ["china", "cud", "tol", "cetcolor", "brewer", "viridis", "colorspace", "scico", "cmocean", "ggsci", "matplotlib", "dongfang"]
    order = {f:i for i,f in enumerate(family_order)}
    palettes = sorted(palettes, key=lambda p: ("extension" in p.get("tags", []), order.get(p["family"], 99)))
    options = ''.join(f'<option value="{html.escape(f)}">{html.escape(FAMILY.get(f,f))} ({counts[f]})</option>' for f in family_order if f in counts)
    dongfang = json.loads((ROOT / 'assets/dongfang.json').read_text(encoding='utf-8'))
    aliases = {c['name']:c.get('aliases',[]) for c in dongfang['source_colours']}
    cards = '\n'.join(palette_card(p, aliases) for p in palettes)
    sources = ''.join(f'<li>{html.escape(str(s.get("name",s.get("id","Source"))))} — {html.escape(str(s.get("attribution",s.get("license",""))))}</li>' for s in data["sources"])
    page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EasyPlot 色带库</title><style>
:root{color-scheme:light;font-family:Arial,"Microsoft YaHei",sans-serif;color:#253039;background:#f6f7f8}
*{box-sizing:border-box}body{margin:0}header,main,footer{max-width:1440px;margin:auto;padding:28px 32px}header{padding-bottom:8px}
.eyebrow{font-size:12px;letter-spacing:.14em;color:#697881}h1{font-size:34px;margin:12px 0}header p{max-width:1020px;line-height:1.8;color:#52616a}
a{color:#225c78}button,select,input{font:inherit}button{cursor:pointer}.filters{display:flex;gap:12px;flex-wrap:wrap;padding:18px 0;align-items:end}
.filters label{display:flex;flex-direction:column;gap:6px;font-size:12px;color:#52616a}.filters .check{flex-direction:row;align-items:center;max-width:230px;line-height:1.5;padding:8px}
select,input[type=search]{padding:10px 12px;border:1px solid #c8d1d7;border-radius:6px;background:white;color:#253039}input[type=search]{width:300px;max-width:80vw}
button{border:1px solid #c8d1d7;border-radius:5px;background:white;color:#354650;padding:6px 10px}button:hover{background:#eef3f6}button:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #2d789e;outline-offset:3px}
#status{min-height:20px;font-size:13px;color:#63717a;margin:8px 0 20px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;align-items:start}
.card{padding:20px;background:white;border:1px solid #e0e5e8;border-radius:9px;min-width:0;break-inside:avoid}.cardhead{display:flex;justify-content:space-between;gap:10px;align-items:start}.cardhead h2{font-size:17px;font-weight:600;line-height:1.4;margin:0 0 10px;overflow-wrap:anywhere}.cardhead>span{font-size:11px;color:#707f88;white-space:nowrap;margin-top:4px}
.idrow{display:flex;align-items:center;gap:10px;justify-content:space-between;margin:0 0 18px}.palette-id{font-size:11px;overflow-wrap:anywhere;color:#54636d}.copy{font-size:11px;flex-shrink:0}
.swatches{display:grid;grid-template-columns:repeat(auto-fit,minmax(60px,1fr));gap:3px}.swatch{min-height:60px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;padding:6px 1px}.swatch code{font:10px Arial,sans-serif}.swatch span{font-size:11px;text-align:center;line-height:1.4}
.ramp{height:56px;border:1px solid #e0e5e8}.stops{display:flex;justify-content:space-between;margin-top:8px;font-size:9px;color:#53616a}.badge{display:inline-block;font-size:10px;padding:5px 7px;margin-top:14px;background:#f1f3f5;border-radius:3px;color:#677680}.reported{background:#e9f1f6;color:#2c5b76}.conditional{background:#fbf3de;color:#7b622d}.not_recommended{background:#f9ebe7;color:#8b4f43}
details{margin-top:13px;font-size:12px;line-height:1.7;color:#56656e}summary{cursor:pointer;color:#46565f}details a{overflow-wrap:anywhere}pre{background:#f6f7f8;padding:10px;font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere}
[hidden]{display:none!important}footer{color:#697780;font-size:12px;line-height:1.8;border-top:1px solid #dce3e7}#empty{padding:40px 0;color:#63717a}
@media(max-width:1000px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.grid{grid-template-columns:1fr}header,main,footer{padding:20px}h1{font-size:28px}}
@media print{.filters,.copy{display:none}body{background:white}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card{box-shadow:none}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head><body>
<header><div class="eyebrow">EASYPLOT / PALETTE LIBRARY / OFFLINE</div><h1>按名字选色，让配色可复现。</h1>
<p>__CORE__ 套核心色带 + __EXT__ 套 ggsci iTerm 扩展。原版、东方原色与微调候选分开管理。每套色带有唯一 ID，R 和 Python 使用相同色值。东方组合由 EasyPlot 策划，每个 HEX 保留 2kil 原值。</p>
<p>“色觉友好设计有来源”表示设计依据，仍需结合点形、线型、标签、背景与最终尺寸检查。期刊名称是配色灵感标签；ggsci 的生成式 Gephi 不属于本次固定色表快照。</p></header>
<main><section class="filters" aria-label="筛选色带">
<label>搜索 ID、名称、原色名<input id="search" type="search" placeholder="例如 npg、china、朱砂、viridis"></label>
<label>来源<select id="family"><option value="">全部来源</option>__OPTIONS__</select></label>
<label>数据类型<select id="kind"><option value="">全部类型</option><option value="qualitative">分类</option><option value="sequential">顺序</option><option value="diverging">发散</option><option value="cyclic">循环</option><option value="multisequential">多段</option></select></label>
<label>色觉依据<select id="cvd"><option value="">全部状态</option><option value="reported">有友好设计来源</option><option value="conditional">有条件</option><option value="not_assessed">未评估</option><option value="not_recommended">慎用</option></select></label>
<label class="check"><input id="shortlist" type="checkbox">显示有色觉依据或明确限制的色带</label>
<label class="check"><input id="extensions" type="checkbox">显示 __EXT__ 套 iTerm 扩展主题</label><button id="reset" type="button">重置</button>
</section><p id="status" aria-live="polite"></p><section class="grid" id="cards" aria-label="色带卡片">__CARDS__</section><p id="empty" hidden>没有匹配的色带，请调整筛选。</p></main>
<footer><p><a href="all-colours.csv">下载完整 HEX 表（包含原生 n 色变体）</a> · 本地静态页面，无外部请求。分类色超出容量会报错；分级东方原色色带不生成新颜色。连续色带有固定采样精度，反向通过参数指定。</p><p>原始来源及许可见每张卡片与资产目录。2kil 原色目录的公开再分发许可尚待确认；此版本用于本地选色。</p><ul>__SOURCES__</ul><div id="copy-status" role="status" aria-live="polite"></div></footer>
<script>
'use strict';
const cards=Array.from(document.querySelectorAll('.card'));
const fields=['search','family','kind','cvd','extensions','shortlist'].map(id=>document.getElementById(id));
function filterCards(){const [q,f,k,c,e,s]=fields;const needle=q.value.trim().toLowerCase();let n=0;
for(const card of cards){const d=card.dataset;const visible=(!needle||d.search.includes(needle))&&(!f.value||d.family===f.value)&&(!k.value||d.kind===k.value)&&(!c.value||d.cvd===c.value)&&(e.checked||d.extension!=='true')&&(!s.checked||d.cvdShortlist==='true');card.hidden=!visible;if(visible)n++;}
document.getElementById('status').textContent=`显示 ${n} / ${cards.length} 套色带；点击“复制 ID”即可唯一指定。`;
document.getElementById('empty').hidden=n!==0;}
for(const field of fields)field.addEventListener('input',filterCards);
document.getElementById('reset').addEventListener('click',()=>{for(const field of fields){if(field.type==='checkbox')field.checked=false;else field.value='';}filterCards();});
document.getElementById('cards').addEventListener('click',async event=>{const button=event.target.closest('button[data-copy]');if(!button)return;const value=button.dataset.copy;let copied=false;
try{await navigator.clipboard.writeText(value);copied=true;}catch(error){const area=document.createElement('textarea');area.value=value;area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();copied=document.execCommand('copy');area.remove();}
document.getElementById('copy-status').textContent=copied?'已复制：'+value:'请选中并手动复制：'+value;});
if(new URLSearchParams(location.search).get('cvd')==='shortlist')document.getElementById('shortlist').checked=true;
filterCards();
</script></body></html>'''
    page = page.replace('__CORE__',str(len(core))).replace('__EXT__',str(extensions)).replace('__OPTIONS__',options).replace('__CARDS__',cards).replace('__SOURCES__',sources)
    mode = 'w' if args.overwrite else 'x'
    with targets[0].open(mode,encoding='utf-8') as stream:
        stream.write(page)
    with targets[1].open(mode,encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['id','label','label_full','family','kind','variant_n','index','hex','colour_name','source_map_name','cvd_status','cvd_targets','cvd_by_n','source_url','source_version'])
        for p in palettes:
            schemes = {'default':p['colours'], **p.get('native_sizes',{})}
            if p.get('anchors'):
                schemes['source_anchors'] = p['anchors']
            for n,values in schemes.items():
                for i,colour in enumerate(values):
                    names=p.get('colour_names',[]) if n=='default' else []
                    writer.writerow([p['id'],p['label'],p.get('label_full',''),p['family'],p['kind'],n,i+1,colour,names[i] if i<len(names) else '',p.get('source_map_name',''),p['cvd']['status'],"|".join(p['cvd'].get('targets') or []),json.dumps(p['cvd'].get('by_n',{}),ensure_ascii=False,separators=(',',':')),p['source']['url'],p['source'].get('version','')])
    with targets[2].open(mode,encoding='utf-8') as stream:
        json.dump({'registry_version':data['version'],'total':len(palettes),'core':len(core),'extensions':extensions,'families':dict(counts),'omissions':data['omissions']},stream,ensure_ascii=False,indent=2)
    print(f'Built {len(palettes)} cards ({len(core)} core) in {targets[0]}')


if __name__=='__main__':
    main()
