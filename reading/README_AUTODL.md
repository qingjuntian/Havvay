# AutoDL 部署说明

本项目把用户提供的 PDF、逐页图片和声音样本，转换成带配音和翻页效果的竖版 MP4。

完整流程：

```text
PDF + page images + voice sample + REF_TEXT
        |
        v
PDF 提取/文本归一化
        |
        v
参考音频去首尾静音
        |
        v
F5-TTS GPU 生成 chunk WAV
        |
        v
根据 PDF 页面和 chunk 文本计算翻页时间
        |
        v
720x1280 竖版 MP4
```

## 1. AutoDL 准备

建议选择带 NVIDIA GPU 的 AutoDL 实例，并使用工作目录，例如：

```bash
cd /root/autodl-tmp
# 将项目放在这里，最终目录假设为：
# /root/autodl-tmp/reading
cd /root/autodl-tmp/reading
```

确认 GPU 和 ffmpeg：

```bash
nvidia-smi
ffmpeg -version
```

`nvidia-smi` 应能看到 GPU。若没有 `ffmpeg`，按 AutoDL 镜像类型安装：

```bash
apt-get update
apt-get install -y ffmpeg
```

## 2. 创建两个 Python 环境

视频、PDF 和预处理依赖使用一个环境；F5-TTS 使用另一个环境，避免 PyTorch、Transformers 等版本冲突。

### 视频/预处理环境

```bash
python3 -m venv .venv-video
source .venv-video/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-video.txt
```

检查：

```bash
python -c "import moviepy, PIL, pypdf, numpy; print('video environment: ok')"
```

### F5-TTS GPU 环境

先退出视频环境：

```bash
deactivate
```

如果当前 shell 无法识别 `conda`，先初始化 Conda：

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate f5
```

已有 AutoDL `f5` Conda 环境时，直接使用上面两行命令激活它，并跳过下面的 venv 创建步骤。

创建 F5 环境：

```bash
python3 -m venv .venv-f5
source .venv-f5/bin/activate
python -m pip install --upgrade pip
```

安装 PyTorch 时，应使用与 AutoDL CUDA/驱动匹配的版本。若镜像已经预装了可用的 `torch` 和 `torchaudio`，不要重复安装；先检查：

```bash
python -c "import torch; print(torch.__version__); print('cuda:', torch.cuda.is_available()); print(torch.version.cuda)"
```

若没有 PyTorch，再按照 PyTorch 官方安装命令安装匹配版本。之后安装 F5-TTS 依赖：

```bash
python -m pip install -r requirements-f5-autodl.txt
```

检查：

```bash
python -c "import torch, f5_tts, soundfile; print('cuda:', torch.cuda.is_available()); print('f5 environment: ok')"
```

必须看到：

```text
cuda: True
```

## 3. 输入文件

一键流程需要四项输入：

```text
book.pdf                 书籍 PDF
page-images/             每页一张 PNG 图片
voice.wav 或 voice.mp3   声音样本
REF_TEXT                 声音样本的准确文字转写
```

例如：

```text
data/book.pdf
data/pages/page_01.png
data/pages/page_02.png
...
data/voice.wav
```

要求：

- PDF 页数必须等于 PNG 数量
- 图片按数字顺序命名，例如 `page_01.png`、`page_02.png`
- 声音样本建议包含一段连续、清晰的中文语音
- `REF_TEXT` 必须逐字匹配声音样本实际说出的内容
- 参考音频会自动去除首尾静音，最长不能超过 12 秒

## 4. 一键生成最终视频

先启用视频环境：

```bash
source .venv-video/bin/activate
```

运行：

```bash
python src/build_book_video.py \
  --pdf data/book.pdf \
  --images-dir data/pages \
  --voice data/voice.wav \
  --ref-text "这里填写声音样本实际说出的完整文字" \
  --f5-python .venv-f5/bin/python \
  --speed 1.2 \
  --output output/book.mp4
```

在 macOS 或 Linux 中，`--f5-python` 通常是：

```bash
--f5-python .venv-f5/bin/python
```

如果使用 Conda，则传入对应解释器：

```bash
--f5-python /root/miniconda3/envs/f5/bin/python
```

最终文件：

```text
output/book.mp4
```

默认视频规格：

```text
分辨率：720 x 1280
帧率：24 fps
翻页过渡：0.8 秒
语速：1.2
```

## 5. 中间文件

默认工作目录为 `output/book_build/`：

```text
output/book_build/
├── book.txt                       # PDF 提取并归一化后的全文
├── book_pages.json                # 逐页文本和匹配文本
├── book_checklist.json            # 疑似图表/表格人工检查清单
├── reference/
│   ├── reference.wav              # 去除首尾静音后的参考音频
│   └── reference.txt              # REF_TEXT
├── f5/
│   ├── chunks/
│   │   ├── chunk_00001.txt
│   │   ├── chunk_00001.wav
│   │   └── ...
│   └── audiobook.mp3
└── page_timings.json              # 页面到音频时间的映射
```

如果希望使用其他工作目录：

```bash
--work-dir output/my_book
```

## 6. 参数说明

### `build_book_video.py`

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `--pdf` | 必填 | 输入 PDF |
| `--images-dir` | 必填 | PNG 页面目录 |
| `--voice` | 必填 | 原始声音样本 |
| `--ref-text` | 必填 | 声音样本准确转写 |
| `--f5-python` | 当前 Python | F5-TTS 环境的 Python |
| `--work-dir` | `output/book_build` | 中间文件目录 |
| `--speed` | `1.2` | F5-TTS 语速，原速使用 `1.0` |
| `--nfe-step` | `32` | F5 推理步数，越高通常质量越好但越慢 |
| `--max-chars` | `100` | 单个 TTS chunk 最大字符数 |
| `--test-limit` | `0` | `0` 表示全书；例如 `10` 只生成前 10 个 chunk |
| `--width` | `720` | 视频宽度 |
| `--height` | `1280` | 视频高度 |
| `--fps` | `24` | 视频帧率 |
| `--transition` | `0.8` | 翻页过渡秒数 |
| `--output` | `output/book.mp4` | 最终 MP4 路径 |

## 7. 先做小规模测试

F5 生成全书可能需要较长时间。建议先生成前 10 个 chunk：

```bash
python src/build_book_video.py \
  --pdf data/book.pdf \
  --images-dir data/pages \
  --voice data/voice.wav \
  --ref-text "声音样本的准确转写" \
  --f5-python .venv-f5/bin/python \
  --test-limit 10 \
  --output output/test.mp4
```

注意：`--test-limit 10` 只适合测试 F5 音质和流程，不适合生成完整页时长视频，因为它不会覆盖整本 PDF。

正式运行时使用：

```bash
--test-limit 0
```

## 8. 选择性重读 chunk

如果某个 chunk 的发音、停顿或文本不理想，不需要重读全书。

创建覆盖文件，例如 `output/chunk_overrides.json`：

```json
{
  "chunks": {
    "22": "四、增进社会关系。"
  }
}
```

只重新生成第 22 个 chunk：

```bash
python src/build_book_video.py \
  --pdf data/book.pdf \
  --images-dir data/pages \
  --voice data/voice.wav \
  --ref-text "声音样本的准确转写" \
  --f5-python .venv-f5/bin/python \
  --chunk-overrides output/chunk_overrides.json \
  --rerender-chunks 22 \
  --output output/book-fixed.mp4
```

多个 chunk 或范围：

```bash
--rerender-chunks 22,41-43
```

`page_timings.json` 会列出每页使用的 chunk。要修复某一页，找到该页的 chunk 列表，把相关编号传给 `--rerender-chunks`。

## 9. 直接运行单个步骤

### 只提取和归一化 PDF

```bash
python src/prepare_book.py \
  --pdf data/book.pdf \
  --text-output output/book_build/book.txt \
  --pages-output output/book_build/book_pages.json
```

### 只处理参考音频

```bash
python src/prepare_reference.py \
  --input data/voice.wav \
  --output output/book_build/reference/reference.wav \
  --text-output output/book_build/reference/reference.txt \
  --ref-text "声音样本的准确转写"
```

### 只生成 F5 音频

```bash
.venv-f5/bin/python src/narrate_book_f5.py \
  --book output/book_build/book.txt \
  --reference-audio output/book_build/reference/reference.wav \
  --reference-text-file output/book_build/reference/reference.txt \
  --output-dir output/book_build/f5 \
  --speed 1.2 \
  --test-limit 0
```

### 只计算页面时间

```bash
python src/page_timings.py \
  --pdf data/book.pdf \
  --pages-json output/book_build/book_pages.json \
  --chunks-dir output/book_build/f5/chunks \
  --output output/book_build/page_timings.json
```

### 只生成视频

```bash
python src/book_video.py \
  --audio output/book_build/f5/audiobook.mp3 \
  --images-dir data/pages \
  --timings output/book_build/page_timings.json \
  --width 720 \
  --height 1280 \
  --transition 0.8 \
  --output output/book.mp4
```

## 10. 常见问题

### `torch.cuda.is_available()` 是 `False`

当前 F5 Python 环境没有识别 GPU。检查：

```bash
nvidia-smi
.venv-f5/bin/python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

确认 AutoDL 实例有 GPU，并重新安装与 CUDA/驱动匹配的 PyTorch。

### `No module named f5_tts`

说明 `--f5-python` 指向了错误环境：

```bash
.venv-f5/bin/python -c "import f5_tts; print('ok')"
```

### `PDF has N pages but images directory has M PNG files`

PDF 和页面图片不是一一对应。补齐或删除图片后再运行。

### `REF_TEXT` 不匹配

`REF_TEXT` 必须是声音样本实际说出的内容，不能填写书中其他句子，也不要遗漏开头或结尾的词。

### 任务中断

F5 chunk 会按文本和参数缓存。重新运行同一命令通常会复用已完成的 chunk，只继续生成缺失或设置已变化的部分。

### 输出视频播放异常

检查最终文件：

```bash
ffprobe -v error output/book.mp4
```

如果视频生成被中断，删除对应的 `.tmp.mp4` 后重新运行视频步骤即可。
