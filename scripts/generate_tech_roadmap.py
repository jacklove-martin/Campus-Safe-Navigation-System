from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 2400, 1700
BG = (248, 249, 252)
BLACK = (35, 35, 35)
WHITE = (255, 255, 255)

GREEN = (208, 232, 192)
GREEN_BORDER = (91, 137, 68)
BLUE = (219, 231, 248)
BLUE_BORDER = (75, 121, 191)
YELLOW = (251, 236, 176)
YELLOW_BORDER = (198, 157, 43)
ORANGE = (250, 221, 199)
ORANGE_BORDER = (207, 129, 71)

FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/simhei.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)


def rounded(box, fill, outline, radius=18, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_center(box, text, size=24, bold=False, fill=BLACK, spacing=6):
    fnt = font(size, bold)
    bb = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=spacing, align="center")
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    x1, y1, x2, y2 = box
    x = x1 + (x2 - x1 - tw) / 2
    y = y1 + (y2 - y1 - th) / 2 - 1
    draw.multiline_text((x, y), text, font=fnt, fill=fill, spacing=spacing, align="center")


def node(x, y, w, h, text, fill, outline, size=24):
    rounded((x, y, x + w, y + h), fill, outline, radius=18, width=3)
    text_center((x, y, x + w, y + h), text, size=size, bold=True)


def panel(x, y, w, h, title, fill, outline):
    rounded((x, y, x + w, y + h), WHITE, outline, radius=16, width=3)
    rounded((x, y, x + w, y + 72), fill, outline, radius=16, width=3)
    draw.rectangle((x + 2, y + 38, x + w - 2, y + 72), fill=fill)
    text_center((x, y + 4, x + w, y + 64), title, size=30, bold=True)


def arrow_down(x, y1, y2, width=6, head=18):
    draw.line((x, y1, x, y2), fill=BLACK, width=width)
    draw.polygon([(x, y2), (x - head, y2 - head), (x + head, y2 - head)], fill=BLACK)


def arrow_up(x, y1, y2, width=6, head=18):
    draw.line((x, y1, x, y2), fill=BLACK, width=width)
    draw.polygon([(x, y2), (x - head, y2 + head), (x + head, y2 + head)], fill=BLACK)


def arrow_right(x1, y, x2, width=6, head=18):
    draw.line((x1, y, x2, y), fill=BLACK, width=width)
    draw.polygon([(x2, y), (x2 - head, y - head), (x2 - head, y + head)], fill=BLACK)


def arrow_left(x1, y, x2, width=6, head=18):
    draw.line((x1, y, x2, y), fill=BLACK, width=width)
    draw.polygon([(x2, y), (x2 + head, y - head), (x2 + head, y + head)], fill=BLACK)


def join_to_bar(xs, top_y, bar_y, width=5):
    for x in xs:
        draw.line((x, top_y, x, bar_y), fill=BLACK, width=width)
    draw.line((min(xs), bar_y, max(xs), bar_y), fill=BLACK, width=width)


# Title and top container
rounded((22, 12, W - 22, 82), GREEN, GREEN_BORDER, radius=26, width=3)
text_center((22, 12, W - 22, 82), "数据处理", size=38, bold=True)
draw.rectangle((22, 90, W - 22, 515), outline=(118, 177, 78), width=3)

# Left top block
draw.rectangle((92, 112, 760, 336), outline=(63, 94, 142), width=3)
node(190, 124, 210, 66, "基础空间数据", GREEN, GREEN_BORDER, 26)
node(430, 124, 210, 66, "服务设施数据", GREEN, GREEN_BORDER, 26)
node(108, 236, 190, 66, "GPS控制点", GREEN, GREEN_BORDER, 24)
node(318, 236, 190, 66, "遥感影像", GREEN, GREEN_BORDER, 24)
node(528, 236, 200, 66, "道路/建筑/绿地", GREEN, GREEN_BORDER, 24)
node(300, 385, 270, 74, "基础地理要素", GREEN, GREEN_BORDER, 28)
arrow_down(430, 336, 385, width=6, head=16)

# Middle top block
node(1015, 124, 180, 66, "安全专题数据", GREEN, GREEN_BORDER, 26)
node(935, 242, 150, 68, "路灯点", GREEN, GREEN_BORDER, 24)
node(1165, 242, 150, 68, "台阶/坡道", GREEN, GREEN_BORDER, 24)
node(1040, 382, 180, 72, "安全评价因子", GREEN, GREEN_BORDER, 26)
arrow_down(1015, 190, 242, width=5, head=14)
arrow_down(1240, 190, 242, width=5, head=14)
join_to_bar([1010, 1240], 310, 346, width=5)
arrow_down(1125, 346, 382, width=5, head=14)

# Right top block
node(1610, 124, 190, 66, "语义与业务数据", GREEN, GREEN_BORDER, 26)
node(1910, 124, 260, 66, "业务规则与样例", GREEN, GREEN_BORDER, 26)
node(1700, 264, 220, 72, "设施别名/口语地标", GREEN, GREEN_BORDER, 24)
node(1970, 264, 180, 72, "查询条件抽取", GREEN, GREEN_BORDER, 24)
node(1815, 404, 200, 72, "问答语义规则库", GREEN, GREEN_BORDER, 26)
join_to_bar([1705, 2040], 190, 228, width=5)
draw.line((1872, 228, 1872, 264), fill=BLACK, width=5)
join_to_bar([1810, 2060], 336, 372, width=5)
arrow_down(1910, 372, 404, width=5, head=14)

# Main panels
panel(44, 572, 960, 700, "基于 GIS 的校园安全服务分析建模", BLUE, BLUE_BORDER)
panel(1120, 572, 1236, 700, "基于 LLM + GIS 的智能导览任务识别与系统实现", BLUE, BLUE_BORDER)

arrow_down(1125, 515, 572, width=10, head=22)
arrow_down(1915, 515, 572, width=10, head=22)

# Left panel nodes
left_top_y = 704
left_top = [
    (84, left_top_y, 180, 96, "基础地理要素"),
    (314, left_top_y, 210, 96, "设施分类与\n属性建模"),
    (574, left_top_y, 180, 96, "安全评价因子"),
    (804, left_top_y, 140, 96, "路网构建"),
]
for x, y, w, h, t in left_top:
    node(x, y, w, h, t, BLUE, BLUE_BORDER, 22)

node(370, 880, 170, 94, "设施筛选与\n空间匹配", BLUE, BLUE_BORDER, 21)
node(590, 880, 160, 94, "路灯缓冲区\n分析", BLUE, BLUE_BORDER, 21)
node(800, 880, 160, 94, "路段评分\n入库", BLUE, BLUE_BORDER, 21)

left_bottom_y = 1072
node(135, left_bottom_y, 190, 98, "夜间安全\n路径模型", BLUE, BLUE_BORDER, 22)
node(395, left_bottom_y, 190, 98, "无障碍\n路径模型", BLUE, BLUE_BORDER, 22)
node(655, left_bottom_y, 190, 98, "应急撤离\n路径模型", BLUE, BLUE_BORDER, 22)
node(300, 1218, 380, 64, "服务设施分布与多目标候选路径集", BLUE, BLUE_BORDER, 22)

# Left arrows, all center aligned
arrow_down(174, 800, left_bottom_y, width=5, head=15)
arrow_down(419, 800, 880, width=5, head=15)
arrow_down(664, 800, 880, width=5, head=15)
arrow_down(874, 800, 880, width=5, head=15)
join_to_bar([455, 670, 880], 974, 1018, width=5)
arrow_down(490, 1018, left_bottom_y, width=5, head=15)
arrow_down(750, 1018, left_bottom_y, width=5, head=15)
arrow_down(490, 1170, 1218, width=5, head=15)

# Middle connector
arrow_right(1004, 905, 1096, width=12, head=28)

# Right panel nodes
right_top_y = 704
right_top = [
    (1170, right_top_y, 190, 96, "问答语义\n规则库"),
    (1416, right_top_y, 190, 96, "DeepSeek\n意图识别"),
    (1662, right_top_y, 190, 96, "起终点/途经点\n抽取"),
    (1908, right_top_y, 190, 96, "时间约束/服务\n约束抽取"),
]
for x, y, w, h, t in right_top:
    node(x, y, w, h, t, BLUE, BLUE_BORDER, 22 if "时间约束" not in t else 20)

task_x, task_y, task_w, task_h = 1458, 900, 240, 92
node(task_x, task_y, task_w, task_h, "任务类型判定", BLUE, BLUE_BORDER, 24)
task_cx = task_x + task_w // 2

right_bottom = [
    (1180, 1082, 210, 100, "设施查询任务"),
    (1450, 1082, 210, 100, "安全路径规划任务"),
    (1720, 1082, 210, 100, "多目标导航任务"),
    (1990, 1082, 240, 100, "结果解释与\n推荐理由生成"),
]
for x, y, w, h, t in right_bottom:
    node(x, y, w, h, t, BLUE, BLUE_BORDER, 22)

# Right arrows, fully aligned
top_centers = [1265, 1511, 1757, 2003]
join_to_bar(top_centers, 800, 904, width=5)
arrow_down(task_cx, 904, 900, width=5, head=15)

bottom_centers = [1285, 1555, 1825, 2110]
arrow_down(task_cx, 992, 1036, width=5, head=15)
draw.line((task_cx, 1036, task_cx, 1036), fill=BLACK, width=5)
draw.line((min(bottom_centers), 1036, max(bottom_centers), 1036), fill=BLACK, width=5)
for xc in bottom_centers:
    arrow_down(xc, 1036, 1082, width=5, head=15)

# To outputs
arrow_down(task_cx, 1272, 1360, width=10, head=22)

# Bottom panels
panel(60, 1360, 940, 286, "系统应用价值", YELLOW, YELLOW_BORDER)
panel(1120, 1360, 1236, 286, "成果输出", ORANGE, ORANGE_BORDER)

node(120, 1478, 320, 130, "提升校园夜间出行\n安全保障能力", YELLOW, YELLOW_BORDER, 24)
node(520, 1478, 360, 130, "为无障碍通行与应急撤离\n提供科学决策支持", YELLOW, YELLOW_BORDER, 24)

out_nodes = [
    (1200, 1478, 220, 100, "MDB 数据库"),
    (1470, 1478, 220, 100, "专题图成果"),
    (1740, 1478, 220, 100, "Web 演示系统"),
    (2010, 1478, 180, 100, "答辩材料"),
]
for x, y, w, h, t in out_nodes:
    node(x, y, w, h, t, ORANGE, ORANGE_BORDER, 24)
node(1520, 1580, 300, 42, "项目设计文档", ORANGE, ORANGE_BORDER, 20)

# Output arrows, centered and level
output_centers = [1310, 1580, 1850, 2100]
join_to_bar(output_centers, 1578, 1632, width=5)
arrow_up(1670, 1632, 1580, width=5, head=12)

# Value link
arrow_left(1120, 1508, 980, width=10, head=24)

out = Path("E:/Campus-Safe-Navigation-System/outputs/技术路线图.png")
img.save(out, quality=95)
print(out)
