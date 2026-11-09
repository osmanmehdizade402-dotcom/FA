"""Hovuz suyunu yaşıldan göyə çevirir (orig/ -> photos/). Yalnız çəkilmiş poliqon içində, yaşıl tonlara təsir edir."""
import cv2, numpy as np, sys
from pathlib import Path
D = Path(__file__).resolve().parent
POLYS = {
    "facade_pool":   [(140,1062),(520,1040),(980,1110),(1540,1215),(1540,2040),(-40,2040),(-40,1460)],
    "pool_palm":     [(-40,1120),(560,1050),(980,990),(1540,1040),(1540,2040),(-40,2040)],
    "facade_garden": [(0,1092),(470,1062),(560,1062),(560,1100),(0,1150)],
    "terrace_pool":  [(700,1052),(1340,1042),(1440,1135),(760,1172)],
}
for k, poly in POLYS.items():
    im = cv2.imread(str(D / "orig" / f"{k}.jpg"))
    h, w = im.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.array(poly, np.int32)], 255)
    m = cv2.GaussianBlur(m, (0, 0), 3).astype(np.float32) / 255
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # green/olive/teal hues (OpenCV 0..180): 25..95
    gw = np.clip((H - 15) / 10, 0, 1) * np.clip((105 - H) / 10, 0, 1) * np.clip(S / 30, 0, 1)
    wgt = (gw * m)
    newH = 101.0  # clear pool blue (~202 deg)
    hsv2 = hsv.copy()
    hsv2[..., 0] = H * (1 - wgt) + newH * wgt
    hsv2[..., 1] = np.clip(S * (1 + 0.25 * wgt), 0, 255)
    hsv2[..., 2] = np.clip(V * (1 + 0.30 * wgt) + 8 * wgt, 0, 255)
    out = cv2.cvtColor(hsv2.astype(np.uint8), cv2.COLOR_HSV2BGR)
    cv2.imwrite(str(D / "photos" / f"{k}.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if len(sys.argv) > 1:
        sm = lambda a: cv2.resize(a, (375, 500))
        cv2.imwrite(f"{sys.argv[1]}/pb_{k}.jpg", np.hstack([sm(im), sm(out)]))
print("ok")
