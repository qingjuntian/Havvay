from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor


OUT = "/Users/qingjun/workspace/Havvay/agent-starter/docs/unified_model_gateway_presentation.pptx"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

BLUE = RGBColor(17, 54, 95)
BLUE2 = RGBColor(33, 89, 143)
ORANGE = RGBColor(245, 144, 58)
SOFT = RGBColor(240, 244, 248)
TEXT = RGBColor(30, 41, 59)
GRAY = RGBColor(96, 108, 120)
WHITE = RGBColor(255, 255, 255)
GREEN = RGBColor(57, 140, 92)
RED = RGBColor(189, 67, 67)


def set_bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title(slide, title, subtitle=None):
    title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.0), Inches(0.7))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.LEFT
    run = p.runs[0]
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.color.rgb = BLUE
    if subtitle:
        sub = slide.shapes.add_textbox(Inches(0.6), Inches(1.0), Inches(11.5), Inches(0.4))
        tf2 = sub.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = subtitle
        p2.alignment = PP_ALIGN.LEFT
        r2 = p2.runs[0]
        r2.font.size = Pt(11)
        r2.font.color.rgb = GRAY


def add_bullets(slide, bullets, left=0.9, top=1.5, width=11.3, height=4.5, font_size=20, color=TEXT):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = b
        p.level = 0
        p.bullet = True
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(10)
        run = p.runs[0]
        run.font.size = Pt(font_size)
        run.font.color.rgb = color
        run.font.name = 'Microsoft YaHei'


def add_highlight_box(slide, text, x, y, w, h, fill_color=ORANGE, text_color=WHITE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = fill_color
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.CENTER
    r = p.runs[0]
    r.font.size = Pt(18)
    r.font.bold = True
    r.font.color.rgb = text_color
    r.font.name = 'Microsoft YaHei'
    return shape


def add_box(slide, text, x, y, w, h, fill_color=SOFT, text_color=TEXT):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = BLUE2
    tf = shape.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = PP_ALIGN.CENTER
    r = p.runs[0]
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = text_color
    r.font.name = 'Microsoft YaHei'
    return shape


def add_arrow(slide, x1, y1, x2, y2):
    shape = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x1), Inches(y1), Inches(x2 - x1), Inches(y2 - y1))
    shape.fill.solid()
    shape.fill.fore_color.rgb = BLUE2
    shape.line.color.rgb = BLUE2
    return shape


# Slide 1
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
# title block
bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.55))
bar.fill.solid(); bar.fill.fore_color.rgb = BLUE
bar.line.color.rgb = BLUE

header = slide.shapes.add_textbox(Inches(0.6), Inches(0.9), Inches(10), Inches(0.8))
tf = header.text_frame
p = tf.paragraphs[0]
p.text = '统一模型网关平台'
p.alignment = PP_ALIGN.LEFT
r = p.runs[0]
r.font.size = Pt(32)
r.font.bold = True
r.font.color.rgb = BLUE
r.font.name = 'Microsoft YaHei'

sub = slide.shapes.add_textbox(Inches(0.6), Inches(1.7), Inches(11.5), Inches(0.6))
tf2 = sub.text_frame
p2 = tf2.paragraphs[0]
p2.text = 'SaaS 优先 · 多租户 · 统一接入 · 成本治理 · 可扩展企业能力'
p2.alignment = PP_ALIGN.LEFT
r2 = p2.runs[0]
r2.font.size = Pt(17)
r2.font.color.rgb = GRAY
r2.font.name = 'Microsoft YaHei'

# right side summary box
box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.1), Inches(2.2), Inches(3.5), Inches(3.1))
box.fill.solid(); box.fill.fore_color.rgb = BLUE
box.line.color.rgb = BLUE
fb = box.text_frame
fb.clear()
for idx, txt in enumerate(['SaaS优先', '统一 API', '多租户治理', '成本控制']):
    p = fb.paragraphs[0] if idx == 0 else fb.add_paragraph()
    p.text = txt
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(16)
    run = p.runs[0]
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = 'Microsoft YaHei'

# bottom features
features = [
    ('统一接入', 'OpenAI/Moonshot/Anthropic等多模型'),
    ('统一治理', '租户、API Key、限流、配额'),
    ('统一成本', '预算、token计量、告警'),
    ('统一审计', '日志、追踪、运营洞察'),
]
for i, (title, desc) in enumerate(features):
    x = Inches(0.6 + i * 3.15)
    y = Inches(5.0)
    w = Inches(2.8)
    h = Inches(1.35)
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = SOFT
    sh.line.color.rgb = BLUE2
    tf3 = sh.text_frame
    tf3.clear()
    p3 = tf3.paragraphs[0]
    p3.text = title
    p3.alignment = PP_ALIGN.CENTER
    r3 = p3.runs[0]
    r3.font.size = Pt(17)
    r3.font.bold = True
    r3.font.color.rgb = BLUE
    r3.font.name = 'Microsoft YaHei'
    p4 = tf3.add_paragraph()
    p4.text = desc
    p4.alignment = PP_ALIGN.CENTER
    r4 = p4.runs[0]
    r4.font.size = Pt(9)
    r4.font.color.rgb = GRAY
    r4.font.name = 'Microsoft YaHei'

# Slide 2: why now
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '为什么需要统一模型网关', '企业在多模型时代面临统一接入与治理难题')

bullets = [
    '不同模型厂商 API 形式、定价和能力存在明显差异，应用层被迫适配多个 SDK 和协议。',
    '企业缺少统一的租户权限控制、API Key 管理、限流和配额能力，导致安全和成本控制困难。',
    '模型稳定性不一致，单独接入会带来超时、失败、降级和研发成本高的问题。',
    '上游 provider 变化快，业务需要有统一抽象层，避免被供应商绑定。',
    '平台若不具备审计、预算和观测能力，很难进入规模化运营阶段。',
]
add_bullets(slide, bullets, left=0.8, top=1.5, width=11.6, height=4.8, font_size=19)

# Slide 3: solution summary
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '方案概览', '从“多模型接入”升级为“统一平台能力”')

add_highlight_box(slide, '统一模型入口', 0.8, 1.9, 2.4, 1.0)
add_highlight_box(slide, '统一鉴权', 3.5, 1.9, 2.2, 1.0)
add_highlight_box(slide, '统一预算', 6.0, 1.9, 2.2, 1.0)
add_highlight_box(slide, '统一审计', 8.5, 1.9, 2.2, 1.0)

add_box(slide, 'OpenAI\nMoonshot\nAnthropic\nAzure', 0.9, 3.2, 2.2, 1.7, fill_color=SOFT)
add_box(slide, 'API Key\n租户隔离\n角色权限\n限流配额', 3.4, 3.2, 2.3, 1.7, fill_color=SOFT)
add_box(slide, 'token 计量\n成本估算\n预算报警\ncost guard', 5.9, 3.2, 2.5, 1.7, fill_color=SOFT)
add_box(slide, '调用日志\n链路追踪\n指标告警\n运营视图', 8.6, 3.2, 2.8, 1.7, fill_color=SOFT)

boxes = [
    ('A. API Gateway', '统一对外接入'),
    ('B. Routing Engine', '按策略选 provider'),
    ('C. Provider Adapter', '抽象不同模型差异'),
    ('D. FinOps', '管理成本与预算'),
]
for i, (t, d) in enumerate(boxes):
    x = 0.8 + i * 3.1
    y = 5.7
    w = 2.7
    h = 0.9
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = BLUE2
    sh.line.color.rgb = BLUE2
    tf = sh.text_frame
    p = tf.paragraphs[0]
    p.text = t
    p.alignment = PP_ALIGN.CENTER
    r = p.runs[0]
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = WHITE
    r.font.name = 'Microsoft YaHei'
    p2 = tf.add_paragraph()
    p2.text = d
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.runs[0]
    r2.font.size = Pt(9)
    r2.font.color.rgb = WHITE
    r2.font.name = 'Microsoft YaHei'

# Slide 4: architecture with boxes and arrows
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '核心架构图', 'MVP 版：统一接入 + 多租户 + 成本治理')

# Column layout
positions = [
    ('Client', 0.8, 3.0, 1.5, 1.0),
    ('API Gateway', 2.7, 2.5, 2.0, 1.5),
    ('Auth / Tenant', 5.1, 2.1, 2.0, 2.0),
    ('Routing Engine', 7.6, 2.1, 2.0, 2.0),
    ('Provider Adapter', 10.2, 2.1, 2.0, 2.0),
    ('Usage / Cost / Audit', 5.1, 5.0, 7.0, 1.4),
]
for label, x, y, w, h in positions:
    if label == 'Client':
        sh = add_box(slide, label, x, y, w, h, fill_color=BLUE, text_color=WHITE)
    elif label == 'Usage / Cost / Audit':
        sh = add_box(slide, label, x, y, w, h, fill_color=ORANGE, text_color=WHITE)
    else:
        sh = add_box(slide, label, x, y, w, h, fill_color=SOFT, text_color=TEXT)

# arrows between boxes and row below
for i in range(4):
    x1 = 2.3 + i*2.4
    y1 = 3.1
    x2 = 2.95 + i*2.4
    y2 = 3.1
    arr = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    arr.line.color.rgb = BLUE2
    arr.line.width = Pt(2)

# bottom row arrow to usage
line = slide.shapes.add_connector(1, Inches(8.6), Inches(4.2), Inches(8.6), Inches(5.0))
line.line.color.rgb = BLUE2
line.line.width = Pt(2)

# slide 5: technical stack
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '技术选型方案', '低风险、可商用、适合中国团队落地')

left = [
    'FastAPI（MIT）',
    'PostgreSQL（PostgreSQL License）',
    'Redis（BSD 风格）',
    'RabbitMQ / Kafka',
]
right = [
    'Prometheus + OpenTelemetry',
    'Docker + Kubernetes + Helm',
    '云 KMS / Vault',
    'OpenAI 兼容接口层',
]
for i, item in enumerate(left):
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.7 + i * 1.15), Inches(5.1), Inches(0.7))
    box.fill.solid(); box.fill.fore_color.rgb = SOFT
    box.line.color.rgb = BLUE2
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = item
    p.alignment = PP_ALIGN.LEFT
    r = p.runs[0]
    r.font.size = Pt(19)
    r.font.bold = True
    r.font.color.rgb = TEXT
    r.font.name = 'Microsoft YaHei'

for i, item in enumerate(right):
    box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7.1), Inches(1.7 + i * 1.15), Inches(5.1), Inches(0.7))
    box.fill.solid(); box.fill.fore_color.rgb = BLUE2
    box.line.color.rgb = BLUE2
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.text = item
    p.alignment = PP_ALIGN.LEFT
    r = p.runs[0]
    r.font.size = Pt(19)
    r.font.bold = True
    r.font.color.rgb = WHITE
    r.font.name = 'Microsoft YaHei'

# slide 6: license and compliance notes
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, 'License 与合规考虑', '优先采用商用友好技术栈')

add_box(slide, '优先选：\nApache 2.0\nMIT\nBSD\nPostgreSQL License', 0.8, 1.8, 4.8, 2.0, fill_color=GREEN, text_color=WHITE)
add_box(slide, '注意：\nAGPL / GPL / SSPL\n可能带来源码公开风险\n或企业法务阻力', 5.9, 1.8, 4.8, 2.0, fill_color=RED, text_color=WHITE)

bullets = [
    '推荐优先使用 Apache 2.0 / MIT / BSD / PostgreSQL License 组件。',
    '在 SaaS 场景中，AGPL 可能带来源码公开义务，企业客户通常不接受。',
    '避免把 Grafana OSS / Elastic 等复杂许可组件直接嵌入核心产品代码中。',
    '法务层面建议在组件选型阶段进行 license review，并保留最终审查步骤。',
]
add_bullets(slide, bullets, left=0.8, top=4.4, width=11.4, height=2.2, font_size=17)

# slide 7: budget
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '2 个月 MVP 成本预算（中国团队）', '4 人团队，稳妥方案')

budget = [
    ('人员成本', '¥218,000 – ¥302,000'),
    ('基础 infra / tools', '¥18,000 – ¥60,000'),
    ('LLM 调用测试成本', '¥2,200 – ¥21,600'),
    ('合计预算', '¥260,000 – ¥400,000'),
]
for i, (k, v) in enumerate(budget):
    x = 1.2
    y = 1.8 + i * 1.1
    w = 4.3
    h = 0.8
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = SOFT
    sh.line.color.rgb = BLUE2
    tf = sh.text_frame
    p = tf.paragraphs[0]
    p.text = k
    p.alignment = PP_ALIGN.LEFT
    r = p.runs[0]
    r.font.size = Pt(18)
    r.font.bold = True
    r.font.color.rgb = TEXT
    r.font.name = 'Microsoft YaHei'
    p2 = tf.paragraphs[0] if False else None
    # value on right
    sh2 = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(6.1), Inches(y), Inches(5.8), Inches(h))
    sh2.fill.solid(); sh2.fill.fore_color.rgb = BLUE2
    sh2.line.color.rgb = BLUE2
    tf2 = sh2.text_frame
    p3 = tf2.paragraphs[0]
    p3.text = v
    p3.alignment = PP_ALIGN.CENTER
    r2 = p3.runs[0]
    r2.font.size = Pt(20)
    r2.font.bold = True
    r2.font.color.rgb = WHITE
    r2.font.name = 'Microsoft YaHei'

# slide 8 risk matrix
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '关键风险与应对', '把工程和经营风险提前识别')

risks = [
    ('上游 provider 稳定性', 'retry / fallback / circuit breaker / provider health watch'),
    ('流量冲击', '租户限流 / quota / queue / token bucket'),
    ('成本失控', '请求前成本估算 / budget cap / cost alert'),
    ('合规隐私', '最小化日志 / BYOK / self-hosted / 审计导出'),
]
for i, (r, a) in enumerate(risks):
    y = 1.7 + i * 1.5
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(y), Inches(3.5), Inches(1.0))
    sh.fill.solid(); sh.fill.fore_color.rgb = BLUE2
    sh.line.color.rgb = BLUE2
    tf = sh.text_frame
    p = tf.paragraphs[0]
    p.text = r
    p.alignment = PP_ALIGN.CENTER
    run = p.runs[0]
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = 'Microsoft YaHei'

    sh2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.8), Inches(y), Inches(7.3), Inches(1.0))
    sh2.fill.solid(); sh2.fill.fore_color.rgb = SOFT
    sh2.line.color.rgb = BLUE2
    tf2 = sh2.text_frame
    p2 = tf2.paragraphs[0]
    p2.text = a
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.runs[0]
    run2.font.size = Pt(14)
    run2.font.color.rgb = TEXT
    run2.font.name = 'Microsoft YaHei'

# slide 9 timeline
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, WHITE)
add_title(slide, '实施里程碑', '建议 2 个月实现 MVP')

weeks = [
    ('1-2周', '需求确认、API 设计、基础环境奠定'),
    ('3-5周', '网关与路由构建、租户认证、限流、日志'),
    ('6-7周', 'OpenAI + Moonshot adapter、降级和重试'),
    ('8周', '成本控制、演示、文档、风险复盘'),
]
for i, (w, d) in enumerate(weeks):
    x = Inches(0.8 + i * 3.0)
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Inches(2.2), Inches(2.5), Inches(2.5))
    sh.fill.solid(); sh.fill.fore_color.rgb = BLUE2 if i % 2 == 0 else ORANGE
    sh.line.color.rgb = BLUE2
    tf = sh.text_frame
    p = tf.paragraphs[0]
    p.text = w
    p.alignment = PP_ALIGN.CENTER
    run = p.runs[0]
    run.font.size = Pt(17)
    run.font.bold = True
    run.font.color.rgb = WHITE
    run.font.name = 'Microsoft YaHei'
    p2 = tf.add_paragraph()
    p2.text = d
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.runs[0]
    run2.font.size = Pt(11)
    run2.font.color.rgb = WHITE
    run2.font.name = 'Microsoft YaHei'

# slide 10 final summary
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide, BLUE)

big = slide.shapes.add_textbox(Inches(0.7), Inches(1.1), Inches(11.5), Inches(1.0))
tf = big.text_frame
p = tf.paragraphs[0]
p.text = '结论：先做统一模型网关，再扩展企业级 AI 能力'
p.alignment = PP_ALIGN.LEFT
r = p.runs[0]
r.font.size = Pt(28)
r.font.bold = True
r.font.color.rgb = WHITE
r.font.name = 'Microsoft YaHei'

sum_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(11.5), Inches(2.6))
tf2 = sum_box.text_frame
msgs = [
    '1. 4 人中国团队、2 个月交付 MVP 是稳妥方案。',
    '2. 统一模型网关是最有价值的底座，可支撑多租户和成本治理。',
    '3. 选型优先考虑 Apache/MIT/BSD/PostgreSQL 这类商用友好组件。',
    '4. 后续可顺势扩展到知识库、RAG、Agent 与企业 AI 助手。',
]
for idx, msg in enumerate(msgs):
    p2 = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
    p2.text = msg
    p2.alignment = PP_ALIGN.LEFT
    run2 = p2.runs[0]
    run2.font.size = Pt(18)
    run2.font.color.rgb = WHITE
    run2.font.name = 'Microsoft YaHei'

# footer
foot = slide.shapes.add_textbox(Inches(0.8), Inches(6.2), Inches(6), Inches(0.5))
ft = foot.text_frame
p3 = ft.paragraphs[0]
p3.text = '统一模型网关平台 | 版本：MVP 路线图'
p3.alignment = PP_ALIGN.LEFT
r3 = p3.runs[0]
r3.font.size = Pt(12)
r3.font.color.rgb = WHITE
r3.font.name = 'Microsoft YaHei'

prs.save(OUT)
print(f'PowerPoint saved to {OUT}')
