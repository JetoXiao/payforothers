from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pathlib import Path
import textwrap, json, shutil
ROOT=Path(r'D:\codex_workspace\projects\payForOthers')
OUT=ROOT/'output/imagegen/recharge-guide-20261116'; OUT.mkdir(parents=True,exist_ok=True)
BG=OUT/'ai-background.png'
IMG1=Path(r'C:\Users\Ruby1114\AppData\Local\Temp\codex-clipboard-722ba256-af8a-407a-b3f5-b84f87b2afbe.png')
IMG2=Path(r'C:\Users\Ruby1114\AppData\Local\Temp\codex-clipboard-b976e9f2-f6e1-4a07-a039-cd8dd8796141.png')
QR=Path(r'C:\Users\Ruby1114\AppData\Local\Temp\codex-clipboard-7d264b0e-40ad-4a30-88c2-e5d16a4438bd.png')
W,H=1800,7600
navy=(18,43,88); blue=(35,106,246); cyan=(34,189,207); ink=(20,37,70); muted=(58,79,115); soft=(241,247,255); card=(255,255,255)
fd=Path(r'C:\Windows\Fonts'); reg=str(fd/'NotoSansSC-VF.ttf'); bold=str(fd/'Dengb.ttf'); arial=str(fd/'arialbd.ttf')
def F(n,b=False,lat=False): return ImageFont.truetype(arial if lat else (bold if b else reg),n)
def rr(d,b,r,fill,outline=None,width=1): d.rounded_rectangle(b,r,fill=fill,outline=outline,width=width)
def fit(im, size):
 im=im.convert('RGB'); w,h=im.size; tw,th=size; scale=max(tw/w,th/h); nw,nh=round(w*scale),round(h*scale); im=im.resize((nw,nh),Image.Resampling.LANCZOS); l=(nw-tw)//2; t=(nh-th)//2; return im.crop((l,t,l+tw,t+th))
def paste_card(base, src, x,y,w, maxh=None, blur=False):
 # Preserve the supplied screenshot in full: proportional resize only.
 source=Image.open(src).convert('RGB')
 im=source.resize((w,round(w*source.height/source.width)),Image.Resampling.LANCZOS)
 # shadow
 sd=Image.new('RGBA',(im.width+34,im.height+34),(0,0,0,0)); sdd=ImageDraw.Draw(sd);sdd.rounded_rectangle((9,9,im.width+24,im.height+24),22,fill=(30,50,88,60));sd=sd.filter(ImageFilter.GaussianBlur(9));base.alpha_composite(sd,(x-17,y-17));base.alpha_composite(im.convert('RGBA'),(x,y)); return im.height

def make(include_wechat):
 bg=fit(Image.open(BG),(W,H)).convert('RGBA'); bg=ImageEnhance.Brightness(bg).enhance(1.08); bg=ImageEnhance.Contrast(bg).enhance(.94)
 # white overlay for readability
 veil=Image.new('RGBA',(W,H),(255,255,255,0)); vd=ImageDraw.Draw(veil,'RGBA')
 for y in range(H): vd.line((0,y,W,y),fill=(255,255,255,95 if y<1000 else 170))
 bg=Image.alpha_composite(bg,veil); d=ImageDraw.Draw(bg,'RGBA')
 # top hero
 rr(d,(92,78,W-92,740),42,(255,255,255,215),(198,220,252,255),2)
 rr(d,(152,128,514,190),30,(225,239,255,255))
 d.text((333,159),'GPTPAYNOW · 充值指南',font=F(29,True),fill=blue,anchor='mm')
 d.text((150,245),'Free 账号充值',font=F(72,True),fill=navy)
 d.text((150,340),'自动发卡 · 自助兑换 · 清晰可查',font=F(38,True),fill=blue)
 d.text((150,423),'请先确认账号当前处于 Free 状态。非 Free 状态的充值路径不同。',font=F(27),fill=muted)
 rr(d,(150,532,W-150,640),28,(235,250,255,255),(147,221,247,255),2)
 d.ellipse((183,567,215,599),fill=(50,205,172,255)); d.text((246,583),'卡密仅限本人使用，切勿泄露给他人。',font=F(28,True),fill=ink,anchor='lm')
 # step 1 card
 y=820; h=1900; rr(d,(92,y,W-92,y+h),42,(255,255,255,235),(199,219,247,255),2)
 rr(d,(146,y+56,300,y+170),30,blue); d.text((223,y+113),'01',font=F(54,True),fill='white',anchor='mm')
 d.text((346,y+76),'获取卡密',font=F(46,True),fill=ink); d.text((346,y+136),'从充值网站下单，系统会自动发卡。',font=F(27),fill=muted)
 d.text((150,y+240),'充值网站',font=F(27,True),fill=muted); d.text((150,y+292),'https://www.gptpaynow.com/',font=F(35,True,True),fill=blue)
 d.text((150,y+390),'自动交付的卡密一般以 GPTPAYNOW- 开头。',font=F(28,True),fill=ink)
 d.text((150,y+452),'请复制完整卡密，不要加空格、不要截图发给他人。',font=F(27),fill=muted)
 rr(d,(150,y+548,W-150,y+640),24,(255,248,226,255),(241,194,77,255),2)
 d.text((180,y+594),'安全提示：卡密属于一次性兑换凭证，请勿公开或转发。',font=F(25,True),fill=(148,92,18),anchor='lm')
 d.text((150,y+748),'兑换网址',font=F(27,True),fill=muted); d.text((150,y+800),'https://redeem.gptpaynow.com/',font=F(35,True,True),fill=blue)
 d.text((150,y+910),'在第一个输入框粘贴卡密，然后点击“验证卡密”。',font=F(30,True),fill=ink)
 h1=paste_card(bg,IMG1,150,y+1000,1500)
 d=ImageDraw.Draw(bg,'RGBA'); d.text((150,y+1000+h1+32),'图 1｜输入卡密并验证（完整截图）',font=F(25,True),fill=muted)
 # step 2
 y2=y+h+80; h2=2200; rr(d,(92,y2,W-92,y2+h2),42,(255,255,255,235),(199,219,247,255),2)
 rr(d,(146,y2+56,300,y2+170),30,blue); d.text((223,y2+113),'02',font=F(54,True),fill='white',anchor='mm')
 d.text((346,y2+76),'提供账号 Session',font=F(46,True),fill=ink); d.text((346,y2+136),'按页面指引获取完整 Session 内容。',font=F(27),fill=muted)
 d.text((150,y2+245),'方式一',font=F(29,True),fill=blue); d.text((150,y2+300),'按兑换网站指引找到账号 Session。',font=F(29),fill=ink)
 d.text((150,y2+395),'方式二',font=F(29,True),fill=blue); d.text((150,y2+450),'直接打开 ChatGPT Session 页面：',font=F(29),fill=ink)
 rr(d,(150,y2+520,W-150,y2+610),20,(234,242,255,255),(184,211,249,255),2); d.text((180,y2+565),'https://chatgpt.com/api/auth/session',font=F(27,True,True),fill=blue,anchor='lm')
 d.text((150,y2+700),'打开后使用“全选 → 复制”，复制网页返回的全部 JSON 内容。',font=F(29,True),fill=ink)
 d.text((150,y2+758),'不要只复制其中一部分，也不要在聊天中发送 Session。',font=F(27),fill=(145,91,23))
 h2img=paste_card(bg,IMG2,150,y2+860,1500)
 d=ImageDraw.Draw(bg,'RGBA'); d.text((150,y2+860+h2img+32),'图 2｜获取完整 Session（完整截图）',font=F(25,True),fill=muted)
 d.text((150,y2+860+h2img+110),'将完整内容粘贴到兑换页面的账号信息输入框。',font=F(29,True),fill=ink)
 # step 3
 y3=y2+h2+80; h3=690 if not include_wechat else 880; rr(d,(92,y3,W-92,y3+h3),42,(255,255,255,235),(199,219,247,255),2)
 rr(d,(146,y3+56,300,y3+170),30,blue); d.text((223,y3+113),'03',font=F(54,True),fill='white',anchor='mm')
 d.text((346,y3+76),'开始兑换',font=F(46,True),fill=ink); d.text((346,y3+136),'校验卡密和账号后，提交兑换任务。',font=F(27),fill=muted)
 d.text((150,y3+260),'① 确认卡密校验通过',font=F(30,True),fill=ink)
 d.text((150,y3+330),'② 确认账号 Session 已完整粘贴',font=F(30,True),fill=ink)
 d.text((150,y3+400),'③ 点击“开始兑换”，等待任务完成',font=F(30,True),fill=ink)
 d.text((150,y3+505),'完成后请到 ChatGPT 账号内确认权益状态。',font=F(27),fill=muted)
 # footer contact optional
 if include_wechat:
  y4=y3+h3+80; h4=850; rr(d,(92,y4,W-92,y4+h4),42,(255,255,255,240),(199,219,247,255),2)
  d.text((150,y4+68),'需要帮助？联系客服',font=F(40,True),fill=blue)
  d.text((150,y4+170),'微信：think-more-9',font=F(36,True),fill=ink)
  d.text((150,y4+238),'请勿发送密码、验证码或完整 Session。',font=F(25),fill=muted)
  qr=fit(Image.open(QR),(430,430)); bg.alpha_composite(qr.convert('RGBA'),(1160,y4+110)); d=ImageDraw.Draw(bg,'RGBA'); d.text((1375,y4+580),'扫码添加客服微信',font=F(24,True),fill=muted,anchor='mm')
  footer_y=y4+h4+70
 else: footer_y=y3+h3+70
 rr(d,(92,footer_y,W-92,footer_y+150),30,navy); d.text((150,footer_y+75),'请妥善保管卡密，完成兑换后删除临时复制内容。',font=F(27,True),fill=(236,247,255),anchor='lm')
 return bg.convert('RGB')

for flag,name in [(False,'充值流程长图-无微信.png'),(True,'充值流程长图-含微信二维码.png')]:
 im=make(flag); im.save(OUT/name,format='PNG',optimize=True,dpi=(144,144)); print(name,im.size,im.getbbox())
(OUT/'README.md').write_text('两版充值流程长图：无微信版与含微信二维码版。Session 截图已脱敏，仅作为操作位置示意。',encoding='utf-8')
