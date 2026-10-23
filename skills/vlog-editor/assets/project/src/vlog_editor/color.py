"""Local HLG BT.2020 to SDR BT.709 display transform for iPhone HDR sources."""
from pathlib import Path
import numpy as np


def display_lut(path):
    path=Path(path)
    if path.exists(): return path
    size=33
    values=np.linspace(0,1,size)
    with path.open('w') as stream:
        stream.write('TITLE "HLG1000 to SDR100 Reinhard BT709"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        # Cube order: red changes fastest.
        for b in values:
            for g in values:
                encoded=np.stack([values,np.full(size,g),np.full(size,b)],axis=1)
                scene=np.where(encoded<=.5,encoded**2/3,(np.exp((encoded-.55991073)/.17883277)+.28466892)/12)
                luminance=scene@np.array([.2627,.6780,.0593])
                display=scene*np.maximum(luminance[:,None],1e-8)**.2*10
                matrix=np.array([[1.660491,-.587641,-.07285],[-.12455,1.1329,-.008349],[-.018151,-.100579,1.11873]])
                rgb=np.maximum(display@matrix.T,0)
                y=rgb@np.array([.2126,.7152,.0722])
                mapped=y*(1+y/100)/(1+y)
                rgb=np.clip(rgb*(mapped/np.maximum(y,1e-8))[:,None],0,1)
                rgb=np.where(rgb<.018,4.5*rgb,1.099*rgb**.45-.099)
                for r,g0,b0 in rgb: stream.write(f'{r:.7f} {g0:.7f} {b0:.7f}\n')
    return path


def hdr_filter(lut):
    # Working path is generated under analysis/, never an original file.
    path=str(Path(lut).resolve()).replace('\\','\\\\').replace(':','\\:').replace("'","\\'")
    return f"format=gbrpf32le,lut3d=file='{path}':interp=tetrahedral,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"
