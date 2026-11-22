from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from pathlib import Path
import textwrap, json, math

ROOT=Path(r'D:\codex_workspace\projects\payForOthers')
SRC=ROOT/'output/imagegen/xianyu-ai-services'
OUT=ROOT/'output/imagegen/xianyu-ai-services-new-drafts-20261105'
OUT.mkdir(parents=True,exist_ok=True)
font_dir=Path(r'C:\Windows\Fonts')
font_regular=font_dir/'NotoSansSC-VF.ttf'
font_bold=font_dir/'Dengb.ttf'

def f(size,bold=False): return ImageFont.truetype(str(font_bold if bold else font_regular),size)

def fit_cover(img,size=(1024,1024),focus=(0.5,0.5)):
    img=img.convert('RGB')
    tw,th=size; w,h=img.size; scale=max(tw/w,th/h)
    nw,nh=round(w*scale),round(h*scale)
    img=img.resize((nw,nh),Image.Resampling.LANCZOS)
    cx=int(focus[0]*nw); cy=int(focus[1]*nh)
    left=max(0,min(nw-tw,cx-tw//2)); top=max(0,min(nh-th,cy-th//2))
    return img.crop((left,top,left+tw,top+th))

def rounded_mask(size,r=34):
    m=Image.new('L',size,0); d=ImageDraw.Draw(m); d.rounded_rectangle((0,0,size[0]-1,size[1]-1),r,fill=255); return m

def make_cover(item):
    bg=fit_cover(Image.open(SRC/item['source']),focus=item.get('focus',(0.5,0.5)))
    bg=ImageEnhance.Color(bg).enhance(0.93)
    bg=ImageEnhance.Contrast(bg).enhance(1.02)
    layer=Image.new('RGBA',bg.size,(0,0,0,0)); d=ImageDraw.Draw(layer,'RGBA')
    # soft left-to-right readability veil
    for x in range(1024):
        if item['dark']:
            a=int(205*(1-x/1024)**1.55)
            d.line((x,0,x,1024),fill=(8,25,70,a))
        else:
            a=int(225*(1-x/1024)**1.6)
            d.line((x,0,x,1024),fill=(255,255,255,a))
    # bottom vignette
    for y in range(1024):
        a=int(80*(y/1024)**2)
        d.line((0,y,1024,y),fill=(4,20,55,a))
    bg=Image.alpha_composite(bg.convert('RGBA'),layer)
    # glass card for title
    panel=Image.new('RGBA',(1024,1024),(0,0,0,0)); p=ImageDraw.Draw(panel,'RGBA')
    if item['dark']:
        fill=(8,25,70,154); edge=(134,224,255,180); title=(255,255,255,255); sub=(213,243,255,255); accent=item['accent']
    else:
        fill=(255,255,255,178); edge=(255,255,255,210); title=(16,39,80,255); sub=(54,82,122,255); accent=item['accent']
    p.rounded_rectangle((54,56,600,520),34,fill=fill,outline=edge,width=3)
    # brand ribbon
    p.rounded_rectangle((83,87,250,133),23,fill=(*item['accent'],230))
    p.text((166,110),'AI 服务定制',font=f(22,True),fill=(255,255,255,255),anchor='mm')
    # number mark
    p.text((548,111),item['number'],font=f(25,True),fill=(*item['accent'],255),anchor='mm')
    # title lines
    title_font=f(48,True)
    lines=textwrap.wrap(item['title'],width=9,break_long_words=False,break_on_hyphens=False)
    yy=182
    for line in lines[:2]:
        p.text((85,yy),line,font=title_font,fill=title)
        yy+=68
    p.text((85,yy+16),item['subtitle'],font=f(25),fill=sub)
    # divider
    p.line((85,yy+74,555,yy+74),fill=(*item['accent'],210),width=3)
    # three benefits
    by=yy+104
    for benefit in item['benefits']:
        p.ellipse((87,by+5,103,by+21),fill=(*item['accent'],255))
        p.text((121,by),benefit,font=f(24),fill=sub)
        by+=44
    bg=Image.alpha_composite(bg,panel)
    # bottom footer label
    footer=Image.new('RGBA',(1024,130),(0,0,0,0)); fd=ImageDraw.Draw(footer,'RGBA')
    if item['dark']:
        fd.rounded_rectangle((54,10,970,116),30,fill=(7,20,56,190),outline=(*item['accent'],150),width=2)
        fill=(225,245,255,255); small=(181,223,245,255)
    else:
        fd.rounded_rectangle((54,10,970,116),30,fill=(255,255,255,214),outline=(*item['accent'],160),width=2)
        fill=(20,48,90,255); small=(69,98,136,255)
    fd.text((86,43),item['footer'],font=f(24,True),fill=fill)
    fd.text((86,82),item['hint'],font=f(18),fill=small)
    bg.alpha_composite(footer,(0,894))
    # subtle sparkles / circles
    decor=Image.new('RGBA',(1024,1024),(0,0,0,0)); dd=ImageDraw.Draw(decor,'RGBA')
    for x,y,r in [(820,130,8),(900,220,4),(760,610,7),(935,730,5)]:
        dd.ellipse((x-r,y-r,x+r,y+r),fill=(*item['accent'],190))
        dd.ellipse((x-r*3,y-r*3,x+r*3,y+r*3),outline=(*item['accent'],60),width=2)
    bg=Image.alpha_composite(bg,decor)
    return bg.convert('RGB')

items=[
 {'number':'01','source':'ai-productivity.png','title':'AI PPT 美化设计','subtitle':'结构梳理 · 视觉统一 · 一键交付','benefits':['汇报型 / 宣传型 / 教学型','统一配色、字体与版式','交付可编辑文件与预览图'],'footer':'让内容更清楚，让表达更有重点','hint':'下单请提供原稿、页数、风格和使用场景','accent':(93,144,245),'dark':False,'focus':(0.48,0.48)},
 {'number':'02','source':'ai-automation.png','title':'AI 数据分析报告','subtitle':'表格清洗 · 图表解读 · 结论提炼','benefits':['支持 Excel / CSV / 表格截图','输出趋势、异常与关键指标','交付分析稿、图表与说明'],'footer':'把数据变成可以行动的结论','hint':'涉及敏感数据时，请先脱敏再提交','accent':(40,186,174),'dark':False,'focus':(0.52,0.5)},
 {'number':'03','source':'ai-comic.png','title':'AI 短视频脚本','subtitle':'选题策划 · 分镜设计 · 口播文案','benefits':['适合短视频、广告与种草内容','拆解开场、节奏与行动引导','交付脚本、镜头表和修改建议'],'footer':'从一个想法，到一条可执行的脚本','hint':'请说明平台、时长、受众和表达风格','accent':(141,113,240),'dark':False,'focus':(0.51,0.45)},
 {'number':'04','source':'ai-training.png','title':'AI 知识库搭建','subtitle':'资料整理 · 分类设计 · 问答流程','benefits':['适合个人资料与小团队文档','设计目录、标签和检索规则','交付结构方案与使用说明'],'footer':'让资料更好找，让经验能复用','hint':'不代保管账号密码、Cookie 或 Session','accent':(61,164,228),'dark':False,'focus':(0.5,0.47)},
 {'number':'05','source':'ai-one-on-one.png','title':'AI 简历与面试优化','subtitle':'经历梳理 · 简历改写 · 面试练习','benefits':['突出项目成果与岗位匹配度','优化表达、结构和关键词','提供模拟问答与改进建议'],'footer':'把经历讲清楚，把优势说出来','hint':'请提供目标岗位与可公开的经历信息','accent':(235,133,117),'dark':False,'focus':(0.48,0.5)},
 {'number':'06','source':'ai-coding.png','title':'AI 研究资料整理','subtitle':'资料归纳 · 摘要提炼 · 引用核对','benefits':['适合论文、行业报告与项目调研','按主题整理要点与待核实信息','交付摘要、结构稿和检索清单'],'footer':'减少整理时间，保留思考空间','hint':'事实、引用与专业结论需由委托方复核','accent':(85,202,221),'dark':True,'focus':(0.58,0.5)},
]
manifest={'generated_at':'2026-11-05','style_reference':'output/imagegen/xianyu-ai-services','image_status':'local style drafts; image2 API returned 401 INVALID_API_KEY','items':[]}
for item in items:
    out=OUT/(item['number']+'-'+item['title'].replace(' ','')+'.png')
    make_cover(item).save(out,format='PNG',optimize=True)
    item2={k:v for k,v in item.items() if k not in {'focus','accent','dark','source'}}
    item2['image']=out.name
    manifest['items'].append(item2)

md=['# 新增闲鱼 AI 服务商品（风格参考稿）','', '参考风格：`output/imagegen/xianyu-ai-services`，采用明亮柔和的 AI 插画、圆润角色、蓝紫/薄荷绿配色和场景化构图。', '', '> 图片目前为本地风格草稿：前面提供的 image2 key 当前返回 `401 INVALID_API_KEY`，待有效 key 后可按同一提示词替换为模型生成图。', '']
for i,item in enumerate(items,1):
    md += [f'## {i}. {item["title"]}', '', f'**建议标题：** {item["title"]}｜{item["subtitle"]}', '', '**商品介绍：**', item['description'] if 'description' in item else '', '', f'**图片：** `{item["number"]}-{item["title"].replace(" ","")}.png`', '']
# descriptions separately
texts={
'AI PPT 美化设计':'提供 AI 辅助的 PPT 结构与视觉优化服务，适合工作汇报、课程讲解、活动宣传和方案展示。请提交原始 PPT 或页面截图，并说明页数、使用场景、品牌色和期望风格；交付包括版式调整、配色建议、页面文案精简和可编辑文件。默认提供 1 个初稿方向和 1 次小范围修改，具体范围以下单前确认。',
'AI 数据分析报告':'提供表格清洗、指标梳理、趋势分析和报告表达优化服务，适合运营复盘、销售周报、项目分析和个人数据整理。请提供脱敏后的 Excel、CSV 或表格截图，并说明关注的问题和目标读者；交付包括关键发现、图表建议、结论结构和可编辑分析稿。数据和结论需由委托方自行核对。',
'AI 短视频脚本':'提供短视频选题、口播文案、镜头拆解和分镜表辅助服务，适合知识分享、产品介绍、门店宣传和内容种草。请说明平台、时长、目标受众、产品信息和表达语气；交付包括标题方向、开场设计、脚本正文、镜头建议和行动引导。不承诺平台审核、流量或成交效果。',
'AI 知识库搭建':'协助整理个人或小团队的文档资料，设计目录、标签、命名规则和问答使用流程，适合项目资料、课程笔记、产品文档和常见问题整理。请说明资料类型、使用工具、团队人数和检索习惯；交付包括结构方案、字段建议、示例模板和使用说明。不代为保管账号密码、Cookie、Session 或其他个人凭据。',
'AI 简历与面试优化':'提供简历结构梳理、经历改写、岗位匹配和面试问答练习服务。请提交目标岗位、现有简历和可公开的项目经历；交付包括简历优化稿、关键词建议、常见问题清单和模拟回答方向。服务用于表达优化与准备，不承诺录用、薪资或招聘结果。',
'AI 研究资料整理':'提供公开资料的主题归纳、摘要提炼、研究框架和引用清单整理服务，适合论文前期、行业调研、竞品分析和项目资料汇总。请说明研究问题、资料范围、时间要求和输出格式；交付包括资料目录、摘要、要点结构和待核实清单。事实、引用、专业结论与版权使用需由委托方复核。',
}
# patch descriptions into md
md=[]
md += ['# 新增闲鱼 AI 服务商品（风格参考稿）','', '参考风格：`output/imagegen/xianyu-ai-services`，采用明亮柔和的 AI 插画、圆润角色、蓝紫/薄荷绿配色和场景化构图。', '', '> 图片目前为本地风格草稿：前面提供的 image2 key 当前返回 `401 INVALID_API_KEY`，待有效 key 后可按同一提示词替换为模型生成图。', '']
for i,item in enumerate(items,1):
    md += [f'## {i}. {item["title"]}', '', f'**建议标题：** {item["title"]}｜{item["subtitle"]}', '', '**商品介绍：**', texts[item['title']], '', f'**图片：** `{item["number"]}-{item["title"].replace(" ","")}.png`', '']
md += ['## 统一发布说明','', '- 标题和详情应与实际交付范围、交付时间和售后规则一致。','- 不使用“官方”“永久”“内部渠道”“稳定不封”等无法证明的表述。','- 不索取密码、验证码、Cookie、Session、Token 或恢复码。','- 图片仅作为服务主题示意图，不代表任何第三方品牌授权。']
(OUT/'商品文案清单.md').write_text('\n'.join(md),encoding='utf-8')
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('saved',len(items),'covers to',OUT)
for p in sorted(OUT.glob('*.png')): print(p.name,p.stat().st_size)
