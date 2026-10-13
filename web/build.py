#!/usr/bin/env python3
"""Assemble web/channel-builder.html (the single-file page published as an Artifact) from web/src.
Usage: python3 web/build.py            -> web/channel-builder.html
       python3 web/build.py --test OUT -> a full HTML document (doctype/head/body) for local browser tests"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
css = open(os.path.join(HERE, "..", "static", "style.css")).read()
# adjustments for the single-page build
css = css.replace("main{max-width:1100px;margin:0 auto;padding:12px 12px calc","main{max-width:1100px;margin:0 auto;padding:12px 16px calc")
css = css.replace(".appbar{position:sticky;top:0;", ".appbar{position:sticky;top:env(safe-area-inset-top,0px);")
css = css.replace("top:calc(var(--ab-h) + 8px);z-index:4", "top:calc(var(--ab-h) + env(safe-area-inset-top,0px) + 8px);z-index:4")
css += """
@media (max-width:600px){main{padding-left:16px;padding-right:16px}}
.toggle button{padding:10px 18px;border:0;background:transparent;color:var(--ink);font:inherit;min-height:44px;cursor:pointer}.toggle button.on{background:var(--accent);color:var(--on-accent);font-weight:700}
button.linkbtn{border:0;background:transparent;color:var(--accent);font:inherit;text-decoration:underline;cursor:pointer;padding:0;min-height:32px}
.schip{display:inline-flex;align-items:center;min-height:30px;padding:0 10px;border-radius:999px;border:1px solid var(--line);color:var(--muted);font-size:.78rem;white-space:nowrap}
.schip.ok{border-color:var(--accent);color:var(--accent)}.schip.err{border-color:var(--over);color:var(--over);background:var(--over-soft)}
@media (min-width:700px){.schip{margin-left:auto}}
#toast{position:fixed;left:50%;transform:translateX(-50%) translateY(20px);bottom:calc(var(--bar-h) + 16px + env(safe-area-inset-bottom,0px));background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:999px;font-size:.9rem;opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:70;max-width:calc(100vw - 32px)}
#toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
#cfmBar{position:fixed;z-index:60;left:16px;right:16px;top:calc(var(--ab-h) + env(safe-area-inset-top,0px) + 8px);max-width:520px;margin:0 auto;padding:12px 14px;border:2px solid var(--attn);border-radius:10px;background:var(--card);color:var(--ink);box-shadow:0 8px 28px rgba(0,0,0,.25)}
#cfmBar p{margin:0 0 8px;font-weight:600}
#txtBox{position:fixed;inset:0;z-index:80;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;padding:16px}#txtBox[hidden]{display:none}
.txt-card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;width:min(640px,100%);max-height:90vh;overflow:auto}.txt-card textarea{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem}
@media (min-width:1000px){#toast{bottom:24px}}
"""
parts = sorted(glob.glob(os.path.join(HERE, "src", "*.js")))
js = "\n".join(open(p).read() for p in parts)
fragment = ('<title>Channel Builder</title>\n<style>\n' + css + '\n</style>\n'
            "<script>try{var t=localStorage.getItem('cb-theme');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>\n"
            '<div id="app"></div>\n<script>\n' + js + '\n</script>\n')
if "--test" in sys.argv:
    out = sys.argv[sys.argv.index("--test") + 1]
    doc = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
           '<style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
           'body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>'
           + fragment + '</body></html>')
    open(out, "w").write(doc)
else:
    open(os.path.join(HERE, "channel-builder.html"), "w").write(fragment)
print(len(fragment), "bytes")
