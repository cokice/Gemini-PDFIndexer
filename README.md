# Gemini PDF Indexer

基于 Gemini 2.5 Flash Developer API 的 PDF 文档标题结构抽取工具，能够自动分析PDF文档的标题层级并将目录信息写回PDF文件。支持单文件处理和批量处理文件夹。

## 功能特点

- 🤖 **智能提取**: 使用 Gemini 2.5 Flash 模型自动识别文档标题结构
- 📦 **分块处理**: 自动将大型PDF分块处理，避免API限制
- 🔄 **智能合并**: 自动合并多个块的结果并优化层级关系
- 💾 **增量保存**: 使用PyMuPDF增量保存，保持原文件完整性
- 🎯 **高精度**: 支持多种文档格式，准确识别标题层级
- 🔧 **灵活配置**: 支持多种参数调整和输出格式
- 📁 **批量处理**: 支持文件夹批量处理，自动处理多个PDF文件
- 🔄 **递归搜索**: 支持递归搜索子文件夹中的PDF文件

## 系统要求

- Python 3.7+
- Google AI API密钥

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制环境变量模板:
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，设置你的 Google AI API 密钥:
```
GOOGLE_AI_API_KEY=your_google_ai_api_key_here
```

或者在运行时通过参数指定:
```bash
python main.py input.pdf --api-key your_google_ai_api_key
```

## 🆕 增强的分级标题识别功能

### 智能标题格式识别
- **多格式支持**: 自动识别中英文、数字、字母等各种编号格式
- **层级智能判断**: 基于标题格式和上下文智能确定层级关系
- **混合AI+规则**: 结合Gemini AI和规则引擎的双重识别机制

### 支持的标题格式

#### 一级标题
- 章节标题：`第一章 概述`、`Chapter 1 Introduction`
- 部分标题：`第一部分 基础理论`、`Part 1 Overview`
- 中文数字：`一、引言`、`二、方法论`
- 阿拉伯数字：`1. 背景介绍`、`2. 研究方法`

#### 二级标题
- 小节编号：`1.1 研究现状`、`2.1 理论基础`
- 括号编号：`(1) 国内研究`、`(一) 基本概念`
- 圆圈数字：`① 第一点`、`② 第二点`
- 中文小节：`一.一 具体内容`

#### 三级标题
- 三级编号：`1.1.1 具体问题`、`2.1.1 详细分析`
- 字母编号：`a) 方法一`、`A) 主要特点`
- 罗马数字：`ⅰ 第一项`、`ⅱ 第二项`

#### 四级标题
- 四级编号：`1.1.1.1 子问题`
- 小写字母：`a. 具体步骤`、`b. 实施方案`

### 高级算法特性

#### 智能层级修正
- **上下文感知**: 根据前后标题调整层级关系
- **跳级处理**: 自动修正层级跳跃问题
- **一致性保证**: 确保整体层级结构的逻辑性

#### 高级去重算法
- **相似性检测**: 基于内容相似性识别重复标题
- **智能选择**: 自动选择最佳版本的重复标题
- **页码容错**: 处理页码轻微偏差的重复项

#### 质量过滤系统
- **格式验证**: 过滤非标题内容（图表标题、页码等）
- **长度检查**: 排除过短或过长的无效标题
- **关键词过滤**: 自动排除页眉页脚等干扰内容

## 使用方法

### 单文件处理

```bash
# 基本用法（覆盖原文件，自动备份）
python main.py document.pdf

# 指定输出文件
python main.py input.pdf --output output_with_toc.pdf

# 指定API密钥
python main.py input.pdf --api-key your_google_ai_api_key

# 仅预览目录结构，不修改PDF
python main.py input.pdf --preview-only
```

### 批量处理文件夹

```bash
# 批量处理文件夹中的所有PDF（原地处理）
python main.py /path/to/pdf/folder --batch

# 批量处理并输出到新文件夹
python main.py pdf_folder --batch --output output_folder

# 递归处理子文件夹
python main.py pdf_folder --batch --recursive

# 保存所有目录为JSON文件
python main.py pdf_folder --batch --save-json

# 设置文件间处理延迟（避免API限制）
python main.py pdf_folder --batch --delay 2

# 不跳过已处理的文件
python main.py pdf_folder --batch --no-skip
```

### 智能模式检测

程序会自动检测输入类型：

```bash
# 如果输入是文件，自动使用单文件模式
python main.py document.pdf

# 如果输入是文件夹，提示使用批量模式
python main.py pdf_folder
# 输出: 错误: 检测到文件夹路径，请使用 --batch 参数启用批量模式

# 正确的批量处理方式
python main.py pdf_folder --batch
```

### 高级选项

```bash
# 调整分块大小（每块最大页数）
python main.py input.pdf --max-pages 500

# 不创建备份文件
python main.py input.pdf --no-backup

# 保存提取的目录为JSON文件
python main.py input.pdf --save-json extracted_toc.json

# 显示详细信息
python main.py input.pdf --verbose
```

### 完整参数列表

```
positional arguments:
  input                 输入PDF文件路径或文件夹路径

options:
  -h, --help            显示帮助信息
  --output, -o          输出PDF文件路径或文件夹（默认覆盖原文件）
  --api-key             Google AI API密钥
  --max-pages           每个处理块的最大页数（默认1000）
  --no-backup           不创建备份文件
  --save-json           将提取的目录保存为JSON文件
  --preview-only        仅预览提取的目录，不写入PDF（仅单文件模式）
  --verbose, -v         显示详细信息

批量处理选项:
  --batch               批量处理模式（处理文件夹中的所有PDF）
  --recursive, -r       递归处理子文件夹
  --no-skip             不跳过已处理的文件
  --delay               文件间处理延迟秒数（默认1秒）
```

## 批量处理特性

### 智能文件发现
- 自动扫描文件夹中的所有PDF文件
- 支持递归搜索子文件夹
- 按文件名排序处理

### 处理进度跟踪
- 实时显示处理进度条
- 显示当前处理的文件名
- 统计成功/失败文件数量

### 错误处理
- 单个文件失败不影响其他文件处理
- 详细的错误日志记录
- 处理结果统计报告

### 性能优化
- 可配置的文件间处理延迟
- 智能跳过已处理文件
- 内存友好的流式处理

## 工作流程

### 单文件处理
1. **文件分析**: 分析PDF文件结构，获取总页数和估算大小
2. **分块处理**: 将大型PDF分为不超过指定页数的块
3. **AI提取**: 使用Gemini 2.5 Flash逐块提取标题结构
4. **结果合并**: 智能合并多个块的结果，去重和层级优化
5. **目录写入**: 使用PyMuPDF将目录结构写回PDF文件

### 批量处理
1. **文件夹扫描**: 递归搜索所有PDF文件
2. **处理队列**: 按文件名排序创建处理队列
3. **逐文件处理**: 对每个PDF执行完整的单文件流程
4. **进度跟踪**: 实时显示处理进度和统计信息
5. **结果汇总**: 生成批量处理报告

## 输出格式

提取的目录采用标准JSON格式:

```json
[
  {"title": "第一章 概述", "level": 1, "page": 1},
  {"title": "1.1 背景介绍", "level": 2, "page": 2},
  {"title": "1.2 研究目标", "level": 2, "page": 5},
  {"title": "第二章 方法论", "level": 1, "page": 10}
]
```

- `title`: 标题文本
- `level`: 层级（1为最高级）
- `page`: 页码（从1开始）

## 批量处理示例

### 基本批量处理
```bash
# 处理当前文件夹中的所有PDF
python main.py . --batch

# 处理指定文件夹
python main.py /home/user/documents/pdfs --batch
```

### 高级批量处理
```bash
# 递归处理所有子文件夹，输出到新位置，保存JSON
python main.py source_folder --batch \
  --output processed_folder \
  --recursive \
  --save-json \
  --delay 1.5 \
  --verbose
```

### 批量处理结果示例
```
🚀 批量PDF处理器启动
📂 输入文件夹: /path/to/pdfs
📁 输出文件夹: /path/to/output

🔍 扫描文件夹: /path/to/pdfs
📁 找到 15 个PDF文件
   (包含子文件夹)

处理进度: 100%|██████████| 15/15 [03:25<00:00,  1.23文件/秒]
✅ 完成: document1.pdf
✅ 完成: document2.pdf
❌ 失败: corrupted.pdf
...

==================================================
📊 批量处理结果摘要
==================================================
📁 总文件数: 15
✅ 成功处理: 14
❌ 处理失败: 1
📋 总目录条目: 287
⏱️  总耗时: 205.3 秒
📈 平均处理时间: 14.7 秒/文件
==================================================

🎉 批量处理完成！
```

## 性能优化

### API成本控制
- 使用最新的 Gemini 2.5 Flash API
- 自动选择最优的处理方式（直接处理 vs File API）
- 设置合理的处理延迟避免API限制

### 处理大文件
- 默认每块1000页，可根据文档复杂度调整
- 支持最大50MB的PDF文件
- 内存友好的流式处理

### 批量处理优化
- 智能跳过已处理文件
- 可配置的错误处理策略
- 进度保存和恢复能力

## 常见问题

### Q: 如何批量处理大量PDF文件？
A: 使用 `--batch` 参数：
```bash
python main.py pdf_folder --batch --delay 2 --verbose
```

### Q: 处理中断后如何继续？
A: 程序默认会跳过已处理的文件，如需重新处理使用 `--no-skip`：
```bash
python main.py pdf_folder --batch --no-skip
```

### Q: 如何处理子文件夹中的PDF？
A: 使用 `--recursive` 参数：
```bash
python main.py pdf_folder --batch --recursive
```

### Q: 无法提取到目录怎么办？
A: 
- 检查PDF是否包含明确的标题结构
- 尝试调整 `--max-pages` 参数
- 使用 `--verbose` 查看详细信息
- 使用 `--preview-only` 预览提取结果

### Q: API调用失败怎么办？
A:
- 确认API密钥设置正确
- 检查网络连接
- 确认API配额充足
- 增加 `--delay` 参数避免速率限制

## 🧪 测试和验证

### 功能测试
```bash
# 运行增强功能测试
python test_advanced_features.py
```

测试内容包括：
- 标题格式识别准确性测试
- AI结果增强功能验证
- 目录合并算法测试
- 完整工作流程验证

### API配置验证
```bash
# 验证API密钥配置
python test_api_key.py
```

## 技术架构

### 核心模块
- `main.py`: 主程序入口，支持单文件和批量处理
- `batch_processor.py`: 批量处理器，专门处理文件夹
- `pdf_chunker.py`: PDF文件分块处理
- `gemini_extractor.py`: Gemini API集成和标题提取（🆕 增强版）
- `advanced_title_analyzer.py`: 🆕 高级标题分析器和智能提取器
- `toc_merger.py`: 目录合并和层级优化（🆕 增强版）
- `pdf_toc_writer.py`: PDF目录写入

### 🆕 新增组件
- **AdvancedTitleAnalyzer**: 专业的标题格式识别引擎
- **SmartTitleExtractor**: AI与规则结合的智能提取器
- **AdvancedTOCMerger**: 高级目录合并和优化算法

### API配置
使用最新的Gemini 2.5 Flash API，配置:
- 自动文件大小检测（<20MB直接处理，>20MB使用File API）
- JSON结构化输出
- 成本优化设置

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

### v1.2.0 - 🆕 增强的分级标题识别
- ✨ 全新的智能标题格式识别系统
- 🧠 AI+规则混合识别机制
- 📊 支持多达20+种标题格式
- 🔧 智能层级修正和上下文感知
- 🚀 高级去重和质量过滤算法
- 🧪 完整的测试验证套件

### v1.1.0
- ✨ 新增批量处理功能
- 🔄 支持文件夹递归搜索
- 📊 增强的进度跟踪和统计
- 🛡️ 改进的错误处理机制
- 🎯 智能模式检测

### v1.0.0
- 初始版本发布
- 支持基本的标题提取和目录生成
- 集成Gemini 2.5 Flash API
- 支持大文件分块处理