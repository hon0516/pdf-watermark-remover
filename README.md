# PDF 本地去水印工具

[English](README_EN.md)

一个在本机运行的 PDF 工具：导入 PDF，检查可识别的平铺 Pattern 水印候选，确认后导出新文件。PDF 内容在本机处理，不会上传到远程服务。原文件不会被覆盖。

![PDF 去水印工具演示](docs/images/app-demo.png)

> **当前版本范围**：0.1 版只自动移除页面内容流末尾、结构可识别的裁剪式 Pattern 平铺图层。扫描件水印、背景里融合的水印、普通文字/图片/透明组水印，以及结构不同的 Pattern 暂不支持。未识别到水印不代表 PDF 没有水印。

## 安装和启动

需要 Python 3.9 或更高版本。

```bash
git clone https://github.com/hon0516/pdf-watermark-remover.git
cd pdf-watermark-remover
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install .
python -m watermark_remover
```

在浏览器访问 <http://127.0.0.1:8765>，选择或拖入 PDF，检查候选水印，然后确认导出。

开发模式安装和测试：

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## 配置

```bash
python -m watermark_remover --host 127.0.0.1 --port 8765
```

| 设置 | 默认值 | 说明 |
| --- | --- | --- |
| `--host` | `127.0.0.1` | 监听地址。建议保留本机地址，避免把文档处理服务暴露到网络。 |
| `--port` | `8765` | 本地网页服务端口。 |
| `WM_MAX_BYTES` | `52428800` | 上传文件大小上限，单位字节。 |
| `WM_MAX_PAGES` | `100` | PDF 页数上限。 |
| `WM_TASK_TTL` | `3600` | 上传文件和输出文件保留秒数，过期自动清理。 |
| `WM_TEMP_DIR` | `.wm-tasks` | 临时任务目录。 |

## 隐私和安全

- 默认只监听 `127.0.0.1`，处理内容不发送到互联网。
- 上传文件只保存在配置的临时目录，任务过期后自动删除。
- 上传文件名会清理路径部分，避免将文件写出临时目录。
- 单文件默认上限 50 MiB，默认最多 100 页。
- 处理结果写入新 PDF；工具不会覆盖源文件。
- 请只处理你拥有或获授权修改的文件，并在使用前后检查输出。

## 已知限制

- 水印识别依赖 PDF 内部内容流的结构，不使用 OCR，也不修复扫描图像中的像素水印。
- 自动识别目前局限于页面末尾的裁剪式 Pattern 平铺绘制块；不同 PDF 软件可能采用其他结构。
- 如果导出后页面内容不完整或视觉异常，请不要使用该输出，并提交不含个人信息的最小复现样本。
- PDF 解析器存在固有风险。只处理可信来源的 PDF，并保持依赖更新。

## 贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。漏洞报告方式见 [SECURITY.md](SECURITY.md)。

## 许可证

本项目采用 MIT License，详见 [LICENSE](LICENSE)。

版本记录见 [CHANGELOG.md](CHANGELOG.md)。
