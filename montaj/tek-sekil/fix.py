"""arenda.az su nişanı və ox düymələrini təmizləmək (bir dəfəlik)."""
import cv2, numpy as np, sys
S=sys.argv[1]
im=cv2.imread('orijinal.jpg'); imf=im.astype(np.float32); h,w=im.shape[:2]
yy,xx=np.mgrid[0:h,0:w]
o=imf.copy(); fix=np.zeros((h,w),np.uint8)
# 1) dark translucent discs: obs = orig*(1-a)  -> per-channel gain fitted on the rim
for cx,cy,r in [(170,773,82),(1008,785,76)]:
    d=np.hypot(xx-cx,yy-cy)
    inn=(d>r-9)&(d<r-3); ou=(d>r+3)&(d<r+9)
    disc=d<=r+3
    a_, c_ = 0.33, 85.0  # gray translucent disc (fitted visually), anti-aliased edge
    best=None
    for rr in np.arange(r-3,r+3.5,0.5):
        for wd in (1.5,2.5,3.5):
            al=(a_*np.clip((rr-d)/wd+0.5,0,1))[...,None]
            rec=(imf-al*c_)/(1-al)
            band=(d>r-10)&(d<r+10)
            gx=cv2.Sobel(cv2.cvtColor(np.clip(rec,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY),cv2.CV_32F,1,0)
            gy=cv2.Sobel(cv2.cvtColor(np.clip(rec,0,255).astype(np.uint8),cv2.COLOR_BGR2GRAY),cv2.CV_32F,0,1)
            nx,ny=(xx-cx)/np.maximum(d,1),(yy-cy)/np.maximum(d,1)
            e=np.abs((gx*nx+gy*ny)[band]).mean()
            if best is None or e<best[0]: best=(e,rr,wd)
    _,rr,wd=best; print('edge',cx,rr,wd)
    al=(a_*np.clip((rr-d)/wd+0.5,0,1))[...,None]
    o=np.where(disc[...,None],(imf-al*c_)/(1-al),o)
    fix|=cv2.dilate((disc&(imf.min(2)>205)).astype(np.uint8)*255,np.ones((11,11),np.uint8))
# 2) white translucent text: obs = orig*(1-a) + a*C, glyph mask fitted per letter
A=np.load(S+'A.npy')
Ad=cv2.GaussianBlur(cv2.dilate(A,np.ones((3,3),np.uint8)),(3,3),0)
a=0.41; C=np.array([215.,215.,215.])
aa=(Ad*a)[...,None]
o=np.where(Ad[...,None]>0.01,(o-aa*C)/(1-aa),o)
b=(A>0.35).astype(np.uint8)
fix|=(cv2.dilate(b,np.ones((5,5),np.uint8))-cv2.erode(b,np.ones((3,3),np.uint8)))*255
o=cv2.inpaint(np.clip(o,0,255).astype(np.uint8),fix,6,cv2.INPAINT_TELEA).astype(np.float32)
Ab=(A>0.3).astype(np.float32)
for _ in range(2):
    num=cv2.GaussianBlur(o*(1-Ab)[...,None],(0,0),9); den=cv2.GaussianBlur(1-Ab,(0,0),9)[...,None]
    sur=num/np.maximum(den,1e-3)
    num=cv2.GaussianBlur(o*Ab[...,None],(0,0),4); den=cv2.GaussianBlur(Ab,(0,0),4)[...,None]
    o=o+cv2.GaussianBlur((sur-num/np.maximum(den,1e-3))*Ab[...,None],(0,0),1.5)
o8=np.clip(o,0,255).astype(np.uint8)
cv2.imwrite('temiz.jpg',o8,[cv2.IMWRITE_JPEG_QUALITY,95])
cv2.imwrite(S+'wm.jpg',np.vstack([im[680:880,60:1120],o8[680:880,60:1120]]))
cv2.imwrite(S+'full.jpg',cv2.resize(o8,(590,752)))
