from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pathlib import Path
import textwrap, json

ROOT=Path(r'D:\codex_workspace\projects\payForOthers')
SRC=ROOT/'output/imagegen/xianyu-ai-services'
OUT=ROOT/'output/imagegen/vibe-coding-ai-templates-20261107'
OUT.mkdir(parents=True,exist_ok=True)
font_dir=Path(r'C:\Windows\Fonts')
REG=str(font_dir/'NotoSansSC-VF.ttf'); BOLD=str(font_dir/'Dengb.ttf'); ARIAL=str(font_dir/'arialbd.ttf')
def F(size,bold=False,latin=False): return ImageFont.truetype(ARIAL if latin else (BOLD if bold else REG),size)

def crop(path, focus=(0.5,0.5)):
    im=Image.open(path).convert('RGB'); w,h=im.size; S=1024
    scale=max(S/w,S/h); nw,nh=round(w*scale),round(h*scale); im=im.resize((nw,nh),Image.Resampling.LANCZOS)
    cx,cy=int(focus[0]*nw),int(focus[1]*nh); l=max(0,min(nw-S,cx-S//2)); t=max(0,min(nh-S,cy-S//2)); return im.crop((l,t,l+S,t+S))

def rr(d,box,r,fill,outline=None,width=1): d.rounded_rectangle(box,r,fill=fill,outline=outline,width=width)

def add_gradient(im, left, right):
    layer=Image.new('RGBA',im.size,(0,0,0,0)); d=ImageDraw.Draw(layer)
    for x in range(1024):
        t=x/1023; a=int(218*(1-t)**1.5); col=tuple(int(left[i]*(1-t)+right[i]*t) for i in range(3)); d.line((x,0,x,1024),fill=(*col,a))
    return Image.alpha_composite(im.convert('RGBA'),layer)

def cover():
    bg=crop(SRC/'ai-coding.png',(0.58,0.48)); bg=ImageEnhance.Contrast(bg).enhance(1.03); bg=ImageEnhance.Color(bg).enhance(0.96)
    bg=add_gradient(bg,(9,27,76),(40,122,180))
    d=ImageDraw.Draw(bg,'RGBA')
    # large glass panel
    rr(d,(52,52,640,590),38,(7,23,66,178),(141,238,255,210),3)
    rr(d,(86,86,286,136),25,(71,206,192,230))
    d.text((186,111),'AI 编程服务',font=F(24,True),fill='white',anchor='mm')
    d.text((575,110),'01',font=F(26,True),fill=(178,242,255,255),anchor='mm')
    d.text((86,181),'Vibe Coding',font=F(68,True,latin=True),fill='white')
    d.text((88,266),'AI编程模板',font=F(57,True),fill=(227,253,255,255))
    d.line((88,355,590,355),fill=(85,230,218,230),width=4)
    d.text((88,390),'让 AI 编程从灵感到落地',font=F(29,True),fill=(225,248,255,255))
    feats=['项目骨架','提示词工作流','快速上手']
    y=458
    for x,t in zip([88,245,442],feats):
        rr(d,(x,y,x+142,y+54),27,(255,255,255,38),(145,235,255,180),2)
        d.text((x+71,y+27),t,font=F(21,True),fill=(239,255,255,255),anchor='mm')
    # lower caption
    rr(d,(52,884,972,974),28,(8,20,57,210),(103,234,219,150),2)
    d.text((84,913),'模板即拿即用 · 适合个人开发者与小团队',font=F(24,True),fill=(234,255,255,255),anchor='lm')
    # accents
    for x,y,r in [(800,120,8),(882,196,5),(730,760,7),(938,720,4)]:
        d.ellipse((x-r,y-r,x+r,y+r),fill=(108,244,223,230)); d.ellipse((x-3*r,y-3*r,x+3*r,y+3*r),outline=(108,244,223,80),width=2)
    return bg.convert('RGB')

def detail():
    bg=crop(SRC/'ai-automation.png',(0.52,0.50)); bg=ImageEnhance.Contrast(bg).enhance(1.02); bg=ImageEnhance.Color(bg).enhance(0.94)
    # soft white veil for detail readability
    veil=Image.new('RGBA',(1024,1024),(255,255,255,0)); vd=ImageDraw.Draw(veil,'RGBA')
    for y in range(1024): vd.line((0,y,1024,y),fill=(250,253,255,int(100+80*(y/1024))))
    bg=Image.alpha_composite(bg.convert('RGBA'),veil)
    d=ImageDraw.Draw(bg,'RGBA')
    d.text((64,58),'Vibe Coding',font=F(62,True,latin=True),fill=(15,40,82,255))
    d.text((66,135),'AI编程模板 · 宝贝详情',font=F(36,True),fill=(43,102,174,255))
    d.text((68,194),'把常用编程步骤整理成可复用的模板',font=F(23),fill=(69,94,129,255))
    # four cards
    cards=[('项目骨架','从目录到基础文件，快速开始'),('代码规范','统一命名、注释与结构习惯'),('调试流程','按步骤定位问题与修复'),('提示词库','常用任务直接套用与改写')]
    positions=[(62,286),(534,286),(62,520),(534,520)]
    colors=[(102,154,247),(75,195,174),(238,151,125),(143,113,237)]
    for (title,desc),(x,y),ac in zip(cards,positions,colors):
        rr(d,(x,y,x+428,y+192),26,(255,255,255,228),(*ac,170),3)
        d.ellipse((x+24,y+26,x+76,y+78),fill=(*ac,235))
        d.text((x+50,y+52),'✦',font=F(24,True),fill='white',anchor='mm')
        d.text((x+96,y+30),title,font=F(29,True),fill=(18,46,87,255))
        d.text((x+96,y+88),desc,font=F(21),fill=(73,98,133,255))
        d.line((x+24,y+145,x+390,y+145),fill=(*ac,110),width=2)
        d.text((x+24,y+160),'可复制 · 可修改 · 可复用',font=F(18,True),fill=(*ac,255))
    rr(d,(62,772,962,930),28,(18,52,101,235),(89,224,202,220),3)
    d.text((92,808),'适合谁？',font=F(27,True),fill=(123,240,220,255))
    d.text((92,862),'个人开发者 · 独立创作者 · 小团队协作',font=F(27,True),fill='white')
    rr(d,(62,948,962,992),18,(229,248,247,255))
    d.text((512,970),'AI 编程模板：少走弯路，更快交付',font=F(20,True),fill=(25,103,103,255),anchor='mm')
    return bg.convert('RGB')

p1=OUT/'01-Vibe-Coding-AI编程模板-主图.png'; p2=OUT/'02-Vibe-Coding-AI编程模板-宝贝详情.png'
cover().save(p1,'PNG',optimize=True); detail().save(p2,'PNG',optimize=True)
manifest={'status':'local style draft because API returned 401 INVALID_API_KEY','style_reference':str(SRC),'model_requested':'image2','files':[p1.name,p2.name]}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(p1,p1.stat().st_size); print(p2,p2.stat().st_size)
