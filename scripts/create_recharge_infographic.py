from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pathlib import Path
import math, textwrap, random

ROOT = Path(r'D:\codex_workspace\projects\payForOthers')
OUT = ROOT / 'output' / 'imagegen'
OUT.mkdir(parents=True, exist_ok=True)
IMG1 = Path(r'C:\Users\Ruby1114\AppData\Local\Temp\codex-clipboard-db4bd511-e351-426e-aec8-7a378de708c5.png')
IMG2 = Path(r'C:\Users\Ruby1114\AppData\Local\Temp\codex-clipboard-2bb37c22-7970-44df-b3ab-2711511af422.png')

W, H = 1800, 5600
# Palette
navy=(17, 38, 77)
blue=(43, 104, 255)
cyan=(59, 197, 221)
ink=(20, 36, 67)
muted=(56, 76, 110)
line=(216, 228, 247)
card=(255,255,255)
soft=(241,247,255)
lightblue=(230,240,255)
warn=(255, 245, 222)
warnline=(244, 197, 92)

# Fonts
font_dir = Path(r'C:\Windows\Fonts')
font_regular = str(font_dir/'NotoSansSC-VF.ttf')
font_bold = str(font_dir/'Dengb.ttf')
font_serif = str(font_dir/'NotoSerifSC-VF.ttf')
def F(size, bold=False):
    return ImageFont.truetype(font_bold if bold else font_regular, size)

im = Image.new('RGB', (W,H), soft)
d = ImageDraw.Draw(im)

# Background gradient
top=(248,251,255); bottom=(235,243,255)
for y in range(H):
    t=y/(H-1)
    col=tuple(int(top[i]*(1-t)+bottom[i]*t) for i in range(3))
    d.line((0,y,W,y), fill=col)

# Abstract generated-style background ornaments (local deterministic)
def blob(cx,cy,r,fill,alpha=80):
    layer=Image.new('RGBA',(W,H),(0,0,0,0)); ld=ImageDraw.Draw(layer)
    ld.ellipse((cx-r,cy-r,cx+r,cy+r), fill=(*fill,alpha))
    layer=layer.filter(ImageFilter.GaussianBlur(max(20,r//6)))
    im.paste(layer,(0,0),layer)

blob(1520,220,480,(87,156,255),80)
blob(200,1220,420,(72,178,223),42)
blob(1650,3550,520,(125,141,255),35)
blob(180,5080,450,(38,177,220),36)
# fine connection lines
ld = ImageDraw.Draw(im, 'RGBA')
for i in range(10):
    x0=110+i*178
    pts=[]
    for y in range(0,H,80):
        x=x0 + int(35*math.sin(y/280+i))
        pts.append((x,y))
    ld.line(pts, fill=(83,137,240,18), width=3)
for x,y,r in [(1550,430,13),(310,740,9),(1460,2900,9),(350,4570,12),(1680,5000,7)]:
    ld.ellipse((x-r,y-r,x+r,y+r), fill=(62,144,255,100))
    ld.ellipse((x-r*2,y-r*2,x+r*2,y+r*2), outline=(62,144,255,45), width=2)

# helpers
def rr(box, radius, fill, outline=None, width=1):
    d.rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)

def txt(x,y,s,size,fill=ink,bold=False,anchor=None,spacing=8):
    # Slightly larger type with stronger contrast for mobile viewing.
    d.multiline_text((x,y),s,font=F(max(1, int(round(size*1.08))),bold),fill=fill,anchor=anchor,spacing=spacing)

def wrap_text(s, width_chars):
    return '\n'.join(textwrap.wrap(s, width=width_chars, break_long_words=False, break_on_hyphens=False))

def card_box(y,h,fill=card):
    rr((105,y,W-105,y+h), 34, fill, outline=(218,229,247), width=2)

def step_header(y,num,title,kicker):
    rr((150,y,272,y+122), 30, blue)
    txt(211,y+61,num,53,(255,255,255),True,anchor='mm')
    txt(315,y+18,title,38,ink,True)
    txt(315,y+73,kicker,22,muted)

def pill(x,y,label,fill=lightblue,color=blue,w=None):
    if w is None:
        w = int(d.textlength(label,font=F(24,True)))+46
    rr((x,y,x+w,y+50),25,fill)
    txt(x+w/2,y+25,label,22,color,True,anchor='mm')
    return w

def link_line(x,y,label,link):
    txt(x,y,label,23,muted,True)
    txt(x,y+38,link,28,blue,True)

# Header panel
rr((0,0,W,770), 0, navy)
# decorative top arcs
ld=ImageDraw.Draw(im,'RGBA')
ld.ellipse((1160,-300,2100,650), outline=(96,174,255,80), width=4)
ld.ellipse((1300,-180,1980,500), outline=(91,225,240,80), width=3)
ld.line((1320,590,1670,310,1800,390), fill=(102,199,255,100), width=4)
# brand mark
rr((126,110,240,224), 32, (51,116,255))
txt(183,167,'↗',54,(255,255,255),True,anchor='mm')
txt(280,112,'GPTPAYNOW',26,(156,208,255),True)
txt(280,162,'充值流程指南',54,(255,255,255),True)
txt(128,302,'ChatGPT 账号充值',78,(255,255,255),True)
txt(130,410,'Free 状态用户专属｜几分钟完成自助兑换',30,(188,218,255))
# status pill
rr((130,535,700,610), 37, (35,67,121))
d.ellipse((160,559,184,583), fill=(73,225,178))
txt(208,572,'开始前请先确认：账号当前为 Free 状态',25,(231,243,255),True,anchor='lm')
txt(130,668,'请按顺序操作，卡密与 Session 仅限本人使用。',24,(156,192,234))

# intro note
card_box(830,270,fill=(247,250,255))
txt(155,875,'先看懂两条规则',28,blue,True)
txt(155,932,'① Free 与非 Free 状态的充值路径不同；本指南适用于当前为 Free 的账号。\n② 兑换过程中需要卡密和账号 Session，请全程在官方/指定页面操作，勿向他人透露。',28,ink,False,spacing=14)

# Step 1
card_box(1150,735)
step_header(1205,'01','先下单，获取兑换信息','选择购买渠道后，拿到卡密与兑换网址')
# two columns
rr((150,1370,850,1715),25,(243,248,255),outline=(215,227,246),width=2)
pill(185,1405,'渠道 A · 闲鱼',fill=(230,239,255),color=blue,w=180)
txt(185,1485,'下单后由我手动发送：',25,ink,True)
txt(185,1535,'• 卡密（CDK 兑换码）\n• 兑换网址\n• 后续自助操作指引',26,muted,spacing=12)
rr((900,1370,1650,1715),25,(241,252,252),outline=(204,235,231),width=2)
pill(935,1405,'渠道 B · 自助网站',fill=(222,250,247),color=(15,150,139),w=220)
txt(935,1485,'打开充值网站下单：',25,ink,True)
txt(935,1535,'系统自动发卡，获取卡密后\n进入兑换页面完成后续操作。',26,muted,spacing=12)
# URLs
link_line(185,1778,'自助充值网站','www.gptpaynow.com')
link_line(935,1778,'兑换网址','https://966qjy.xyz/')
# security bar
rr((150,1925,1650,2015),22,warn,outline=warnline,width=2)
txt(180,1970,'安全提示',23,(177,111,18),True,anchor='lm')
txt(335,1970,'卡密一般以 GPTPAYNOW- 或 QIUJIUYI- 开头，请勿泄露、转发或重复提交。',23,(132,99,40),False,anchor='lm')

# Step 2
card_box(2095,1110)
step_header(2150,'02','打开兑换页，填写 CDK','先输入卡密，系统会自动校验有效性与套餐类型')
rr((150,2325,1650,2405),22,(230,241,255),outline=(191,213,247),width=2)
txt(185,2365,'兑换页面',22,muted,True,anchor='lm')
txt(370,2365,'https://966qjy.xyz/',28,blue,True,anchor='lm')
# screenshot 1
src1=Image.open(IMG1).convert('RGB')
maxw=1420; newh=int(src1.height*maxw/src1.width)
img1=src1.resize((maxw,newh),Image.Resampling.LANCZOS)
# shadow
rr((180,2455,1620,2455+newh+34),25,(222,230,242))
im.paste(img1,(190,2465))
# caption
cap_y=2465+newh+54
txt(190,cap_y,'图 1｜在第一个输入框粘贴 CDK 兑换码',23,muted,True)
# highlight strip
rr((150,cap_y+60,1650,cap_y+148),22,(247,250,255),outline=(214,226,245),width=2)
txt(180,cap_y+104,'输入完成后，点击页面中的校验/继续按钮，等待系统识别卡密。',24,ink,False,anchor='lm')

# Step 3
step3_y=3370
card_box(step3_y,1160)
step_header(step3_y+55,'03','获取并粘贴完整 Session','卡密校验通过后，按页面指引提供账号凭证')
# warning panel
rr((150,step3_y+220,1650,step3_y+400),24,(255,247,236),outline=(244,202,127),width=2)
txt(185,step3_y+258,'重要：Session 等同于账号密码',26,(170,94,18),True)
txt(185,step3_y+310,'只在本人设备和指定兑换页面使用，绝对不要发给任何人或发布到群聊。',24,(128,96,54))
# instructions
text_y=step3_y+475
txt(180,text_y,'方式一：按照兑换网站指引找到账号 Session。',26,ink,True)
txt(180,text_y+58,'方式二：直接打开 ChatGPT Session 页面，复制整个网页内容：',26,muted)
rr((180,text_y+125,1620,text_y+200),18,(235,241,252),outline=(204,217,238),width=2)
txt(205,text_y+162,'https://chatgpt.com/api/auth/session',25,blue,True,anchor='lm')
# redacted screenshot 2
src2=Image.open(IMG2).convert('RGB')
# scale to width 1420 then blur + dark privacy layer
maxw2=1420; h2=int(src2.height*maxw2/src2.width)
red=src2.resize((maxw2,h2),Image.Resampling.LANCZOS)
red=red.filter(ImageFilter.GaussianBlur(8))
# reduce contrast and tint
red=ImageEnhance.Contrast(red).enhance(0.55)
red=ImageEnhance.Brightness(red).enhance(0.92)
red_rgba=red.convert('RGBA')
rd=ImageDraw.Draw(red_rgba,'RGBA')
rd.rectangle((0,0,maxw2,h2),fill=(16,30,58,95))
rd.rounded_rectangle((40,40,maxw2-40,h2-40),20,outline=(255,255,255,95),width=3)
rd.rectangle((40,h2//2-36,maxw2-40,h2//2+36),fill=(8,19,43,210))
rd.text((maxw2//2,h2//2),'完整 Session 内容已脱敏，仅展示粘贴位置示意',font=F(30,True),fill=(255,255,255),anchor='mm')
# card shadow and paste
ry=text_y+245
rr((180,ry,1620,ry+h2+34),25,(222,230,242))
im.paste(red_rgba,(190,ry+10),red_rgba)
txt(190,ry+h2+58,'图 2｜完整 Session 页面示意（已脱敏）',23,muted,True)
# paste note
rr((150,ry+h2+105,1650,ry+h2+193),22,(247,250,255),outline=(214,226,245),width=2)
txt(180,ry+h2+149,'将网页中显示的全部内容复制后，粘贴到兑换页面的账号验证输入框。',24,ink,False,anchor='lm')

# Step 4
step4_y=4680
card_box(step4_y,585)
step_header(step4_y+55,'04','校验并确认兑换','完成两项校验后，提交充值')
# checklist
checks=[('01','校验 CDK 卡密','确认卡密有效且对应正确套餐'),('02','校验账号 Session','确认账号信息已正确识别'),('03','确认 CDK 兑换','点击确认按钮，等待充值完成')]
cy=step4_y+235
for i,(n,t,s) in enumerate(checks):
    x=180+i*485
    d.ellipse((x,cy,x+52,cy+52),fill=blue)
    txt(x+26,cy+26,'✓',28,(255,255,255),True,anchor='mm')
    txt(x,cy+75,t,25,ink,True)
    txt(x,cy+120,wrap_text(s,18),20,muted,spacing=5)

# footer safety
foot_y=5385
rr((105,foot_y,W-105,foot_y+160),30,navy)
txt(150,foot_y+38,'完成后请关闭页面并妥善删除临时复制内容。',25,(224,240,255),True)
txt(150,foot_y+92,'需要帮助？请通过下单渠道联系售后。',23,(157,200,239))

# Add tiny footer mark
txt(W-150,foot_y+80,'GPTPAYNOW',20,(121,170,226),True,anchor='rm')

# output
out=OUT/'ChatGPT充值流程高清长图.png'
im.save(out,format='PNG',optimize=True,dpi=(144,144))
# redacted source for audit/reuse
redout=OUT/'ChatGPT充值流程-图2脱敏.png'
red_rgba.convert('RGB').save(redout,format='PNG',optimize=True)
print('saved',out,im.size,out.stat().st_size)
print('saved',redout,red_rgba.size,redout.stat().st_size)
