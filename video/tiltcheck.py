"""Before/after straightening check: prints vertical lean per photo and saves a sheet with red guides.

Usage: python3 tiltcheck.py listings/<slug> <out.jpg>
"""
import sys, glob, math
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
from straighten import straighten, _segments
def resid(im):
    # weighted mean |lean| of near-vertical segments: 0 = perfectly straight verticals
    segs,_=_segments(im)
    if not segs: return 0
    l=[abs(math.degrees(math.atan2(s[2]-s[0], abs(s[3]-s[1])+1e-9))) for s in segs]
    return np.average(l,weights=[s[4] for s in segs])
d=sys.argv[1]; out=[]
for p in sorted(glob.glob(d+'/photos/*.jpg')):
    im=Image.open(p).convert('RGB'); fx,s=straighten(im)
    print(f"{p.split('/')[-1]:20s} before {resid(im):5.2f}  after {resid(fx):5.2f}  shift {s:4.1f}%")
    for x in (im,fx):
        x=x.resize((240,320)); dr=ImageDraw.Draw(x)
        for gx in range(24,240,24): dr.line([(gx,0),(gx,320)],fill=(255,0,0))
        out.append(x)
cols=8; rows=math.ceil(len(out)/cols)
m=Image.new('RGB',(cols*245,rows*325),'white')
for i,x in enumerate(out): m.paste(x,((i%cols)*245,(i//cols)*325))
m.save(sys.argv[2])
