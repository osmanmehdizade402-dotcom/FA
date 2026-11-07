"""Ox düyməsi və səhifə nöqtələrini silmək (bir dəfəlik)."""
import cv2, numpy as np
S='/tmp/claude-0/-home-user-FA/579f83ba-99da-59c5-9b5f-c46d81367fec/scratchpad/'
im=cv2.imread('orijinal-2.jpg'); h,w=im.shape[:2]
o=im.copy()
# 1) dots: 10 evenly spaced translucent discs -> inpaint
fixd=np.zeros((h,w),np.uint8)
for i in range(10):
    cv2.circle(fixd,(454+i*30,821),12,255,-1)
# each dot: copy a nearby patch (left/right/above) whose border matches best, feathered
for i in range(10):
    dx,dy=454+i*30,821
    R=16; r=11
    yy,xx=np.mgrid[-R:R+1,-R:R+1]; dd=np.hypot(xx,yy)
    ring=(dd>r+1)&(dd<=R)
    tgt=o[dy-R:dy+R+1,dx-R:dx+R+1].astype(np.float32)
    best=None
    for oy in range(-60,1,3):
        for ox in range(-45,46,3):
            if abs(oy)<26 and abs(ox)<26: continue
            sy,sx=dy+oy,dx+ox
            p_=o[sy-R:sy+R+1,sx-R:sx+R+1].astype(np.float32)
            if p_.shape!=tgt.shape: continue
            fd=fixd[sy-R:sy+R+1,sx-R:sx+R+1]
            if fd.any(): continue
            e=np.abs(p_[ring]-tgt[ring]).mean()
            if best is None or e<best[0]: best=(e,sx,sy)
    _,sx,sy=best
    p_=o[sy-R:sy+R+1,sx-R:sx+R+1].astype(np.float32)
    m=np.clip((r+4-dd)/4,0,1)[...,None]
    o[dy-R:dy+R+1,dx-R:dx+R+1]=np.clip(tgt*(1-m)+p_*m,0,255).astype(np.uint8)
# 2) arrow button: fill disc with nearby tree texture (best-matching patch by border similarity), feathered
cx,cy,r=1110,434,36
R=r+6
yy,xx=np.mgrid[-R:R+1,-R:R+1]; dd=np.hypot(xx,yy)
ring=(dd>r+2)&(dd<=R)
tgt=o[cy-R:cy+R+1,cx-R:cx+R+1].astype(np.float32)
best=None
for sy in range(R,h-R,4):
    for sx in range(w-260,w-R,4):
        if abs(sy-cy)<2*R and abs(sx-cx)<2*R: continue
        p=o[sy-R:sy+R+1,sx-R:sx+R+1].astype(np.float32)
        e=np.abs(p[ring]-tgt[ring]).mean()
        if best is None or e<best[0]: best=(e,sx,sy)
_,sx,sy=best; print('patch from',sx,sy,round(best[0],1))
p=o[sy-R:sy+R+1,sx-R:sx+R+1].astype(np.float32)
m=np.clip((r+5-dd)/5,0,1)[...,None]
# match low-frequency color to the surroundings
blend=tgt*(1-m)+p*m
o[cy-R:cy+R+1,cx-R:cx+R+1]=np.clip(blend,0,255).astype(np.uint8)
cv2.imwrite('temiz-2.jpg',o,[cv2.IMWRITE_JPEG_QUALITY,95])
cv2.imwrite(S+'c3.jpg',np.hstack([cv2.resize(o[370:500,1030:1179],None,fx=2,fy=2),cv2.resize(im[370:500,1030:1179],None,fx=2,fy=2)]))
cv2.imwrite(S+'d3.jpg',np.vstack([o[795:850,420:760],im[795:850,420:760]]))
