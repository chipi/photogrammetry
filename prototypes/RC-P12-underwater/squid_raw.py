"""Bring a SQUID NEF into the geometry of its resizedUndistort TIF.

SQUID's TIFs clip red to zero on most underwater pixels, so colour work needs the RAW. The
chart annotations and range maps are in the undistorted TIF's pixel grid, and the undistortion
model (a MATLAB stereoParameters object) cannot be read outside MATLAB. Instead the linear RAW
decode is registered to the TIF: green channels are phase-correlated tile by tile, a cubic
polynomial maps TIF pixels to RAW pixels, and the RAW is sampled on the TIF grid.
"""

import numpy as np
import rawpy
import scipy.ndimage as ndi

TILE = 256
STEP = 128
MIN_PEAK = 8.0
MAX_RESID_PX = 1.5


def decode_linear(nef_path):
    """Camera RGB, linear, black subtracted, scaled to [0, 1]; no white balance."""
    with rawpy.imread(str(nef_path)) as r:
        rgb = r.postprocess(
            half_size=True,
            gamma=(1, 1),
            no_auto_bright=True,
            output_bps=16,
            use_camera_wb=False,
            user_wb=[1, 1, 1, 1],
            output_color=rawpy.ColorSpace.raw,
        )
        wb = np.array(r.camera_whitebalance[:3]) / r.camera_whitebalance[1]
    return rgb.astype(np.float64) / 65535, wb


def _poly_terms(x, y):
    return np.stack(
        [np.ones_like(x), x, y, x * x, x * y, y * y, x**3, x * x * y, x * y * y, y**3], -1
    )


def register(raw_rgb, tif_green):
    """Fit TIF (x, y) -> RAW (x, y); returns coefficients, normalisation, fit statistics."""
    h, w = tif_green.shape
    sy, sx = raw_rgb.shape[0] / h, raw_rgb.shape[1] / w
    g0 = ndi.zoom(raw_rgb[..., 1], (1 / sy, 1 / sx), order=1)[:h, :w]
    a_img, b_img = np.log(g0 + 1e-4), np.log(tif_green + 1e-4)
    src, dst = [], []
    for y0 in range(0, h - TILE + 1, STEP):
        for x0 in range(0, w - TILE + 1, STEP):
            tb = tif_green[y0 : y0 + TILE, x0 : x0 + TILE]
            if (tb <= 0).any() or tb.std() < 1e-3:
                continue
            a = a_img[y0 : y0 + TILE, x0 : x0 + TILE]
            b = b_img[y0 : y0 + TILE, x0 : x0 + TILE]
            a, b = a - a.mean(), b - b.mean()
            fa, fb = np.fft.fft2(a), np.fft.fft2(b)
            cross = fb * np.conj(fa)
            xc = np.abs(np.fft.ifft2(cross / (np.abs(cross) + 1e-12)))
            py, px = np.unravel_index(xc.argmax(), xc.shape)
            if xc.max() / np.median(xc) < MIN_PEAK:
                continue
            dy = py if py < TILE // 2 else py - TILE
            dx = px if px < TILE // 2 else px - TILE
            # b(p) = a(p - s): the TIF pixel p sits at p - s in the zoomed RAW
            cy, cx = y0 + TILE / 2, x0 + TILE / 2
            src.append((cx, cy))
            dst.append(((cx - dx) * sx, (cy - dy) * sy))
    src, dst = np.array(src), np.array(dst)
    norm = np.array([w / 2, h / 2])
    s = (src - norm) / norm
    keep = np.ones(len(src), bool)
    for _ in range(5):
        terms = _poly_terms(s[keep, 0], s[keep, 1])
        coef = np.linalg.lstsq(terms, dst[keep], rcond=None)[0]
        resid = np.linalg.norm(_poly_terms(s[:, 0], s[:, 1]) @ coef - dst, axis=1) / sx
        keep = resid < max(MAX_RESID_PX, 3 * np.median(resid))
    stats = {
        "tiles": len(src),
        "kept": int(keep.sum()),
        "rms_resid_tif_px": float(np.sqrt((resid[keep] ** 2).mean())),
    }
    return coef, norm, stats


def warp_to_tif(raw_rgb, coef, norm, shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    terms = _poly_terms((xx.ravel() - norm[0]) / norm[0], (yy.ravel() - norm[1]) / norm[1])
    rx, ry = (terms @ coef).T
    out = np.stack(
        [
            ndi.map_coordinates(raw_rgb[..., c], [ry, rx], order=1, mode="constant", cval=np.nan)
            for c in range(3)
        ],
        -1,
    )
    return out.reshape(h, w, 3)
