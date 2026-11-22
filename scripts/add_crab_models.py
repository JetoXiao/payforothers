from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

root=Path(r'D:\codex_workspace\projects\payForOthers\output\imagegen\crab-gift-cards-20261117')
src=root/'03-xieli-zhenxuan.png'
im=Image.open(src).convert('RGB')
models=['PLUS型','5X型','10X型','25X型']
font_candidates=[r'C:\Windows\Fonts\Dengb.ttf',r'C:\Windows\Fonts\NotoSansSC-VF.ttf',r'C:\Windows\Fonts\arialbd.ttf']
font_path=next(p for p in font_candidates if Path(p).exists())
font=ImageFont.truetype(font_path,38)
# Coordinates correspond to the cream model plate in the generated third card.
plate=(720,872,977,965)
for model in models:
    out=im.copy(); d=ImageDraw.Draw(out)
    # Add a subtle warm translucent center behind the model text while preserving the original plate.
    d.rounded_rectangle((plate[0]+16,plate[1]+16,plate[2]-16,plate[3]-16),18,fill=(255,248,226),outline=(190,132,54),width=2)
    bbox=d.textbbox((0,0),model,font=font)
    tw,th=bbox[2]-bbox[0],bbox[3]-bbox[1]
    cx=(plate[0]+plate[2])//2; cy=(plate[1]+plate[3])//2
    d.text((cx-tw/2,cy-th/2-3),model,font=font,fill=(52,38,29),stroke_width=1,stroke_fill=(130,85,32))
    safe=model.replace('型','')
    path=root/f'03-xieli-zhenxuan-{safe}.png'
    out.save(path,format='PNG',optimize=True,dpi=(144,144))
    print(path.name,out.size,path.stat().st_size)
