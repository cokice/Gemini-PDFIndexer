#!/usr/bin/env python3
"""
批量PDF处理器 - 处理文件夹中的多个PDF文件
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm
import json

from pdf_chunker import PDFChunker
from gemini_extractor import GeminiTitleExtractor
from toc_merger import TOCMerger
from pdf_toc_writer import PDFTOCWriter


class BatchPDFProcessor:
    """批量PDF处理器"""
    
    def __init__(self, api_key: Optional[str] = None, max_pages: int = 1000):
        """
        初始化批量处理器
        
        Args:
            api_key: Google AI API密钥
            max_pages: 每个处理块的最大页数
        """
        self.chunker = PDFChunker(max_pages=max_pages)
        self.extractor = GeminiTitleExtractor(api_key=api_key)
        self.merger = TOCMerger()
        self.writer = PDFTOCWriter()
        self.max_pages = max_pages
        
        # 处理统计
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_toc_entries': 0,
            'processing_time': 0
        }
        
        # 失败文件记录
        self.failed_files = []
    
    def find_pdf_files(self, folder_path: str, recursive: bool = True) -> List[Path]:
        """
        查找文件夹中的PDF文件
        
        Args:
            folder_path: 文件夹路径
            recursive: 是否递归查找子文件夹
            
        Returns:
            List[Path]: PDF文件路径列表
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise ValueError(f"文件夹不存在: {folder_path}")
        
        if not folder.is_dir():
            raise ValueError(f"路径不是文件夹: {folder_path}")
        
        # 查找PDF文件
        if recursive:
            pdf_files = list(folder.rglob("*.pdf"))
        else:
            pdf_files = list(folder.glob("*.pdf"))
        
        # 按文件名排序
        pdf_files.sort(key=lambda x: x.name.lower())
        
        return pdf_files
    
    def process_folder(self, 
                      input_folder: str, 
                      output_folder: Optional[str] = None,
                      recursive: bool = True,
                      backup: bool = True,
                      save_json: bool = False,
                      skip_existing: bool = True,
                      delay_between_files: float = 1.0) -> Dict:
        """
        批量处理文件夹中的PDF文件
        
        Args:
            input_folder: 输入文件夹路径
            output_folder: 输出文件夹路径（None则原地处理）
            recursive: 是否递归处理子文件夹
            backup: 是否创建备份
            save_json: 是否保存JSON格式的目录
            skip_existing: 是否跳过已处理的文件
            delay_between_files: 文件间处理延迟（秒）
            
        Returns:
            Dict: 处理结果统计
        """
        start_time = time.time()
        
        # 查找PDF文件
        print(f"🔍 扫描文件夹: {input_folder}")
        pdf_files = self.find_pdf_files(input_folder, recursive)
        
        if not pdf_files:
            print("❌ 未找到PDF文件")
            return self.stats
        
        print(f"📁 找到 {len(pdf_files)} 个PDF文件")
        if recursive:
            print("   (包含子文件夹)")
        print()
        
        # 准备输出文件夹
        if output_folder:
            output_path = Path(output_folder)
            output_path.mkdir(parents=True, exist_ok=True)
        
        # 重置统计
        self.stats['total_files'] = len(pdf_files)
        self.failed_files = []
        
        # 处理每个PDF文件
        with tqdm(total=len(pdf_files), desc="处理进度", unit="文件") as pbar:
            for pdf_file in pdf_files:
                try:
                    # 更新进度条描述
                    pbar.set_description(f"处理: {pdf_file.name}")
                    
                    # 检查是否跳过已处理的文件
                    if skip_existing and self._is_already_processed(pdf_file, output_folder):
                        pbar.write(f"⏭️  跳过已处理文件: {pdf_file.name}")
                        pbar.update(1)
                        continue
                    
                    # 处理单个文件
                    success = self._process_single_file(
                        pdf_file, 
                        output_folder, 
                        backup, 
                        save_json
                    )
                    
                    if success:
                        self.stats['processed_files'] += 1
                        pbar.write(f"✅ 完成: {pdf_file.name}")
                    else:
                        self.stats['failed_files'] += 1
                        self.failed_files.append(str(pdf_file))
                        pbar.write(f"❌ 失败: {pdf_file.name}")
                    
                    # 文件间延迟（避免API限制）
                    if delay_between_files > 0:
                        time.sleep(delay_between_files)
                
                except KeyboardInterrupt:
                    pbar.write("\n⚠️  用户中断处理")
                    break
                except Exception as e:
                    self.stats['failed_files'] += 1
                    self.failed_files.append(str(pdf_file))
                    pbar.write(f"❌ 处理 {pdf_file.name} 时发生错误: {e}")
                
                pbar.update(1)
        
        # 计算处理时间
        self.stats['processing_time'] = time.time() - start_time
        
        # 显示处理结果
        self._print_summary()
        
        return self.stats
    
    def _process_single_file(self, 
                           pdf_file: Path, 
                           output_folder: Optional[str], 
                           backup: bool, 
                           save_json: bool) -> bool:
        """
        处理单个PDF文件
        
        Args:
            pdf_file: PDF文件路径
            output_folder: 输出文件夹
            backup: 是否备份
            save_json: 是否保存JSON
            
        Returns:
            bool: 是否处理成功
        """
        try:
            # 确定输出路径
            if output_folder:
                output_path = Path(output_folder) / pdf_file.name
            else:
                output_path = pdf_file
            
            # 步骤1: 分块处理PDF
            chunks = self.chunker.chunk_pdf(str(pdf_file))
            
            # 步骤2: 提取标题
            all_toc_entries = []
            
            for chunk_bytes, start_page, end_page in chunks:
                try:
                    toc_entries = self.extractor.extract_titles_from_pdf_bytes(
                        chunk_bytes, start_page, end_page
                    )
                    all_toc_entries.append(toc_entries)
                except Exception as e:
                    print(f"   块 {start_page}-{end_page} 处理失败: {e}")
                    # 继续处理其他块
                    all_toc_entries.append([])
            
            # 步骤3: 合并结果
            final_toc = self.merger.merge_toc_entries(all_toc_entries)
            
            if not final_toc:
                print(f"   警告: {pdf_file.name} 未提取到任何目录条目")
                return False
            
            # 更新统计
            self.stats['total_toc_entries'] += len(final_toc)
            
            # 步骤4: 保存JSON（如果需要）
            if save_json:
                json_path = output_path.with_suffix('.json')
                self.merger.save_toc_to_json(final_toc, str(json_path))
            
            # 步骤5: 写入PDF目录
            self.writer.write_toc_to_pdf(
                str(pdf_file),
                final_toc,
                str(output_path) if output_path != pdf_file else None,
                backup=backup
            )
            
            return True
            
        except Exception as e:
            print(f"   处理 {pdf_file.name} 时发生错误: {e}")
            return False
    
    def _is_already_processed(self, pdf_file: Path, output_folder: Optional[str]) -> bool:
        """
        检查文件是否已经处理过（简单检查是否有备份文件）
        
        Args:
            pdf_file: PDF文件路径
            output_folder: 输出文件夹
            
        Returns:
            bool: 是否已处理
        """
        try:
            if output_folder:
                # 检查输出文件夹中是否有对应文件
                output_file = Path(output_folder) / pdf_file.name
                return output_file.exists()
            else:
                # 检查是否有备份文件
                backup_file = pdf_file.with_name(f"{pdf_file.stem}_backup.pdf")
                return backup_file.exists()
        except:
            return False
    
    def _print_summary(self):
        """打印处理结果摘要"""
        print("\n" + "="*50)
        print("📊 批量处理结果摘要")
        print("="*50)
        print(f"📁 总文件数: {self.stats['total_files']}")
        print(f"✅ 成功处理: {self.stats['processed_files']}")
        print(f"❌ 处理失败: {self.stats['failed_files']}")
        print(f"📋 总目录条目: {self.stats['total_toc_entries']}")
        print(f"⏱️  总耗时: {self.stats['processing_time']:.1f} 秒")
        
        if self.stats['processed_files'] > 0:
            avg_time = self.stats['processing_time'] / self.stats['processed_files']
            print(f"📈 平均处理时间: {avg_time:.1f} 秒/文件")
        
        # 显示失败文件
        if self.failed_files:
            print(f"\n❌ 失败文件列表:")
            for failed_file in self.failed_files:
                print(f"   - {failed_file}")
        
        print("="*50)
    
    def save_processing_log(self, log_path: str):
        """
        保存处理日志
        
        Args:
            log_path: 日志文件路径
        """
        log_data = {
            'stats': self.stats,
            'failed_files': self.failed_files,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'settings': {
                'max_pages': self.max_pages
            }
        }
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        print(f"📄 处理日志已保存到: {log_path}")


def main():
    """批量处理命令行入口"""
    import argparse
    from dotenv import load_dotenv
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description='批量处理文件夹中的PDF文件，为每个PDF添加目录',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
    python batch_processor.py /path/to/pdf/folder
    python batch_processor.py input_folder --output output_folder
    python batch_processor.py folder --recursive --save-json --delay 2
        """
    )
    
    parser.add_argument('input_folder', help='输入文件夹路径')
    parser.add_argument('--output', '-o', help='输出文件夹路径（默认原地处理）')
    parser.add_argument('--api-key', help='Google AI API密钥')
    parser.add_argument('--max-pages', type=int, default=1000, help='每个处理块的最大页数')
    parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子文件夹')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份文件')
    parser.add_argument('--save-json', action='store_true', help='保存目录为JSON文件')
    parser.add_argument('--no-skip', action='store_true', help='不跳过已处理的文件')
    parser.add_argument('--delay', type=float, default=1.0, help='文件间处理延迟（秒）')
    parser.add_argument('--log', help='保存处理日志的文件路径')
    
    args = parser.parse_args()
    
    try:
        print("🚀 批量PDF处理器启动")
        print(f"📂 输入文件夹: {args.input_folder}")
        
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
            input_folder=args.input_folder,
            output_folder=args.output,
            recursive=args.recursive,
            backup=not args.no_backup,
            save_json=args.save_json,
            skip_existing=not args.no_skip,
            delay_between_files=args.delay
        )
        
        # 保存日志
        if args.log:
            processor.save_processing_log(args.log)
        
        print("\n🎉 批量处理完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
    except Exception as e:
        print(f"\n❌ 批量处理过程中发生错误: {e}")


if __name__ == "__main__":
    main()