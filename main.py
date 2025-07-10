#!/usr/bin/env python3
"""
Gemini PDF Indexer - 使用 Gemini 2.5 Flash 自动提取PDF标题并创建目录

主要功能：
1. 自动分析PDF文档结构
2. 使用Gemini AI提取标题层级
3. 将目录信息写回PDF文件
4. 支持单文件和批量处理

使用方法：
    # 单文件处理
    python main.py input.pdf [--output output.pdf] [--api-key YOUR_API_KEY]
    
    # 批量处理文件夹
    python main.py folder_path --batch [--output output_folder]

环境变量：
    GOOGLE_AI_API_KEY: Google AI API密钥
"""

import argparse
import os
import sys
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

from pdf_chunker import PDFChunker
from gemini_extractor import GeminiTitleExtractor
from toc_merger import TOCMerger
from pdf_toc_writer import PDFTOCWriter


def process_single_file(args):
    """处理单个PDF文件"""
    # 验证输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.pdf':
        print(f"错误: 输入文件不是PDF格式: {input_path}")
        sys.exit(1)
    
    # 确定输出路径
    output_path = args.output if args.output else str(input_path)
    
    try:
        print("🚀 Gemini PDF Indexer 开始运行")
        print(f"📄 输入文件: {input_path}")
        print(f"📝 输出文件: {output_path}")
        print()
        
        # 步骤1: 分析PDF文件
        print("📊 分析PDF文件...")
        chunker = PDFChunker(max_pages=args.max_pages)
        total_pages, estimated_size = chunker.get_pdf_info(str(input_path))
        
        print(f"   总页数: {total_pages}")
        print(f"   估算大小: {estimated_size:,} 字符")
        print(f"   将分为 {(total_pages + args.max_pages - 1) // args.max_pages} 个处理块")
        print()
        
        # 步骤2: 分块处理
        print("📦 分块读取PDF...")
        chunks = chunker.chunk_pdf(str(input_path))
        print(f"   已创建 {len(chunks)} 个处理块")
        print()
        
        # 步骤3: 初始化Gemini提取器
        print("🤖 初始化Gemini AI...")
        try:
            extractor = GeminiTitleExtractor(api_key=args.api_key)
            print("   Gemini 2.5 Flash 已就绪")
        except ValueError as e:
            print(f"   错误: {e}")
            print("   请设置环境变量 GOOGLE_AI_API_KEY 或使用 --api-key 参数")
            sys.exit(1)
        print()
        
        # 步骤4: 提取标题
        print("🔍 提取文档标题结构...")
        all_toc_entries = []
        
        with tqdm(total=len(chunks), desc="处理进度") as pbar:
            for i, (chunk_bytes, start_page, end_page) in enumerate(chunks):
                pbar.set_description(f"处理第 {start_page}-{end_page} 页")
                
                if args.verbose:
                    print(f"\n   块 {i+1}/{len(chunks)}: 第 {start_page}-{end_page} 页")
                
                # 尝试直接处理PDF字节流，如果失败则回退到文本提取
                try:
                    toc_entries = extractor.extract_titles_from_pdf_bytes(
                        chunk_bytes, start_page, end_page
                    )
                except Exception as e:
                    if args.verbose:
                        print(f"   PDF直接处理失败，回退到文本提取: {e}")
                    
                    # 回退到文本提取
                    text = chunker.extract_text_from_chunk(chunk_bytes)
                    toc_entries = extractor.extract_titles_from_text(text, start_page, end_page)
                
                all_toc_entries.append(toc_entries)
                
                if args.verbose and toc_entries:
                    print(f"   提取到 {len(toc_entries)} 个标题")
                
                pbar.update(1)
        
        print()
        
        # 步骤5: 合并和排序
        print("🔄 合并和排序目录...")
        merger = TOCMerger()
        final_toc = merger.merge_toc_entries(all_toc_entries)
        
        if not final_toc:
            print("   警告: 未提取到任何目录条目")
            print("   可能的原因:")
            print("   - PDF文档没有明确的标题结构")
            print("   - 文档格式不适合自动提取")
            print("   - 需要调整提取参数")
            return
        
        print(f"   合并后共 {len(final_toc)} 个目录条目")
        print()
        
        # 显示目录预览
        merger.print_toc_preview(final_toc)
        
        # 保存JSON格式（如果需要）
        if args.save_json:
            merger.save_toc_to_json(final_toc, args.save_json)
        
        # 如果只是预览模式，到此结束
        if args.preview_only:
            print("\n✅ 预览模式完成，未修改PDF文件")
            return
        
        # 步骤6: 写入PDF目录
        print("💾 写入PDF目录...")
        writer = PDFTOCWriter()
        
        # 预览现有目录
        if args.verbose:
            existing_toc = writer.preview_existing_toc(str(input_path))
            writer.compare_toc(existing_toc, final_toc)
        
        # 写入目录
        result_path = writer.write_toc_to_pdf(
            str(input_path),
            final_toc,
            output_path if output_path != str(input_path) else None,
            backup=not args.no_backup
        )
        
        print()
        print("✅ 目录生成完成！")
        print(f"📁 输出文件: {result_path}")
        print(f"📋 目录条目: {len(final_toc)} 个")
        print()
        print("🎉 现在可以在PDF阅读器中查看自动生成的目录了！")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 运行时发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def process_batch(args):
    """批量处理文件夹"""
    from batch_processor import BatchPDFProcessor
    
    try:
        print("🚀 批量PDF处理器启动")
        print(f"📂 输入文件夹: {args.input}")
        
        if args.output:
            print(f"📁 输出文件夹: {args.output}")
        else:
            print("📁 输出方式: 原地处理（覆盖原文件）")
        
        print()
        
        # 创建处理器
        processor = BatchPDFProcessor(
            api_key=args.api_key,
            max_pages=args.max_pages
        )
        
        # 开始批量处理
        stats = processor.process_folder(
            input_folder=args.input,
            output_folder=args.output,
            recursive=args.recursive,
            backup=not args.no_backup,
            save_json=bool(args.save_json),
            skip_existing=not args.no_skip,
            delay_between_files=args.delay if hasattr(args, 'delay') else 1.0
        )
        
        print("\n🎉 批量处理完成！")
        
    except Exception as e:
        print(f"\n❌ 批量处理过程中发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """主程序入口"""
    # 加载环境变量
    load_dotenv()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='使用 Gemini 2.5 Flash 自动提取PDF标题并创建目录',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  单文件处理:
    python main.py document.pdf
    python main.py input.pdf --output output_with_toc.pdf
    python main.py input.pdf --api-key your_google_ai_api_key
    
  批量处理:
    python main.py /path/to/pdf/folder --batch
    python main.py folder --batch --output output_folder --recursive
    python main.py folder --batch --save-json --delay 2
        """
    )
    
    parser.add_argument('input', help='输入PDF文件路径或文件夹路径')
    parser.add_argument('--output', '-o', help='输出PDF文件路径或文件夹（默认覆盖原文件）')
    parser.add_argument('--api-key', help='Google AI API密钥（也可通过环境变量GOOGLE_AI_API_KEY设置）')
    parser.add_argument('--max-pages', type=int, default=1000, help='每个处理块的最大页数（默认1000）')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份文件')
    parser.add_argument('--save-json', help='将提取的目录保存为JSON文件')
    parser.add_argument('--preview-only', action='store_true', help='仅预览提取的目录，不写入PDF（仅单文件模式）')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    # 批量处理相关参数
    parser.add_argument('--batch', action='store_true', help='批量处理模式（处理文件夹中的所有PDF）')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子文件夹（批量模式）')
    parser.add_argument('--no-skip', action='store_true', help='不跳过已处理的文件（批量模式）')
    parser.add_argument('--delay', type=float, default=1.0, help='文件间处理延迟秒数（批量模式，默认1秒）')
    
    args = parser.parse_args()
    
    # 检查输入路径
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入路径不存在: {input_path}")
        sys.exit(1)
    
    # 根据输入类型和批量模式标志决定处理方式
    if args.batch or input_path.is_dir():
        # 批量处理模式
        if not input_path.is_dir():
            print(f"错误: 批量模式需要文件夹路径: {input_path}")
            sys.exit(1)
        process_batch(args)
    else:
        # 单文件处理模式
        if input_path.is_dir():
            print(f"错误: 检测到文件夹路径，请使用 --batch 参数启用批量模式")
            print(f"示例: python main.py {args.input} --batch")
            sys.exit(1)
        process_single_file(args)


if __name__ == "__main__":
    main()