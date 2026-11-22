from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

ROOT=Path(r'D:\codex_workspace\projects\payForOthers')
base=ROOT/'output/imagegen/ChatGPT充值流程高清长图.png'
qr=Path(r'C:\Users\Ruby1114\AppData\Local\Temp\codex-clipboard-61b3b09c-b374-41ea-9537-cda6a95c95a8.png')
out=ROOT/'output/imagegen/ChatGPT充值流程高清长图-含客服二维码.png'
W=1800
old=Image.open(base).convert('RGB')
old_w,old_h=old.size
extra=850
H=old_h+extra
# Background continuation using a soft vertical gradient
im=Image.new('RGB',(W,H))
d=ImageDraw.Draw(im)
start=(235,243,255); end=(225,239,255)
for y in range(H):
    if y<old_h:
        # overwritten below, still fill
        t=y/max(1,H-1)
    else:
        t=(y-old_h)/max(1,extra-1)
    c=tuple(int(start[i]*(1-t)+end[i]*t) for i in range(3))
    d.line((0,y,W,y),fill=c)
im.paste(old,(0,0))
# subtle continuation ornaments
d=ImageDraw.Draw(im,'RGBA')
for x in [120,430,830,1200,1600]:
    d.line((x,old_h-30,x-30,H),fill=(78,139,240,22),width=3)
d.ellipse((80,old_h+140,590,old_h+650),fill=(73,180,226,22))
d.ellipse((1400,old_h+60,1970,old_h+620),fill=(109,128,250,20))

font_dir=Path(r'C:\Windows\Fonts')
regular=ImageFont.truetype(str(font_dir/'NotoSansSC-VF.ttf'),33)
regular26=ImageFont.truetype(str(font_dir/'NotoSansSC-VF.ttf'),29)
regular24=ImageFont.truetype(str(font_dir/'NotoSansSC-VF.ttf'),27)
bold=ImageFont.truetype(str(font_dir/'Dengb.ttf'),46)
bold32=ImageFont.truetype(str(font_dir/'Dengb.ttf'),35)
bold28=ImageFont.truetype(str(font_dir/'Dengb.ttf'),31)
navy=(17,38,77); blue=(43,104,255); ink=(20,36,67); muted=(56,76,110)

def rr(box,r,fill,outline=None,width=1):
    d.rounded_rectangle(box,r,fill=fill,outline=outline,width=width)
def txt(x,y,s,font,fill=ink,anchor=None):
    d.text((x,y),s,font=font,fill=fill,anchor=anchor)

# Contact card
card_y=old_h+65
card_h=610
rr((105,card_y,W-105,card_y+card_h),34,(255,255,255,255),outline=(210,225,246,255),width=2)
# left content
rr((150,card_y+55,700,card_y+135),22,(230,240,255,255))
txt(180,card_y+95,'需要帮助？联系客服',bold28,blue,anchor='lm')
txt(160,card_y+190,'微信客服',bold32,ink)
txt(160,card_y+255,'think-more-9',ImageFont.truetype(str(font_dir/'arialbd.ttf'),42),blue)
txt(160,card_y+340,'充值过程中遇到问题，欢迎添加客服微信。',regular26,muted)
txt(160,card_y+390,'请勿向他人发送卡密或账号 Session。',regular24,(169,112,39))
# QR panel
qr_im=Image.open(qr).convert('RGB')
qr_size=420
qr_im=qr_im.resize((qr_size,qr_size),Image.Resampling.LANCZOS)
# QR white panel with shadow
shadow=Image.new('RGBA',(qr_size+38,qr_size+38),(0,0,0,0)); sd=ImageDraw.Draw(shadow)
sd.rounded_rectangle((8,8,qr_size+30,qr_size+30),20,fill=(186,201,223,130))
shadow=shadow.filter(ImageFilter.GaussianBlur(8))
im.paste(shadow,(1135,card_y+92),shadow)
im.paste(qr_im,(1150,card_y+100))
txt(1360,card_y+535,'扫码添加客服微信',regular24,muted,anchor='mm')
# bottom footer bar
foot_y=card_y+card_h+42
rr((105,foot_y,W-105,foot_y+145),30,navy)
txt(150,foot_y+45,'完成后请关闭页面并妥善删除临时复制内容。',regular26,(224,240,255))
txt(150,foot_y+97,'GPTPAYNOW · 客服微信：think-more-9',regular24,(157,200,239))
txt(W-150,foot_y+72,'GPTPAYNOW',regular24,(121,170,226),anchor='rm')

im.save(out,format='PNG',optimize=True,dpi=(144,144))
print('saved',out,im.size,out.stat().st_size)
