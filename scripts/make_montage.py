from PIL import Image,ImageDraw
from pathlib import Path
p=Path('output/imagegen/xianyu-ai-services-new-drafts-20261105')
files=sorted(p.glob('*.png'))
thumbs=[]
for f in files:
 im=Image.open(f).resize((320,320),Image.Resampling.LANCZOS); thumbs.append((f.name,im))
out=Image.new('RGB',(960,760),(236,244,255)); d=ImageDraw.Draw(out)
for i,(name,im) in enumerate(thumbs):
 x=(i%3)*320; y=(i//3)*380; out.paste(im,(x,y)); d.text((x+10,y+330),name,font=None,fill=(20,36,67))
out.save(p/'预览拼图.png')
print(out.size)
