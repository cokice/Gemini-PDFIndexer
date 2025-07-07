import fitz  # PyMuPDF
import os
import shutil
from typing import List
from pdf_chunker import TOCEntry


class PDFTOCWriter:
    """PDF目录写入器"""
    
    def __init__(self):
        pass
    
    def write_toc_to_pdf(self, pdf_path: str, toc_entries: List[TOCEntry], output_path: str = None, backup: bool = True) -> str:
        """
        将目录写入PDF文件
        
        Args:
            pdf_path: 源PDF文件路径
            toc_entries: 目录条目列表
            output_path: 输出文件路径，如果为None则覆盖原文件
            backup: 是否备份原文件
            
        Returns:
            str: 输出文件路径
        """
        # 确定输出路径
        if output_path is None:
            output_path = pdf_path
        
        # 备份原文件
        if backup and output_path == pdf_path:
            backup_path = self._create_backup(pdf_path)
            print(f"原文件已备份到: {backup_path}")
        
        try:
            # 打开PDF文档
            doc = fitz.open(pdf_path)
            
            # 转换目录格式
            toc_list = self._convert_to_pymupdf_format(toc_entries)
            
            # 验证目录格式
            if not self._validate_toc_format(toc_list, len(doc)):
                raise ValueError("目录格式验证失败")
            
            # 设置目录
            doc.set_toc(toc_list)
            
            # 保存文档（增量保存以保持原有内容）
            if output_path == pdf_path:
                # 原地保存
                doc.saveIncr()
            else:
                # 保存到新文件
                doc.save(output_path, garbage=3, deflate=True)
            
            doc.close()
            
            print(f"目录已成功写入PDF: {output_path}")
            print(f"共添加 {len(toc_entries)} 个目录条目")
            
            return output_path
            
        except Exception as e:
            print(f"写入目录时发生错误: {e}")
            raise
    
    def _create_backup(self, pdf_path: str) -> str:
        """
        创建文件备份
        
        Args:
            pdf_path: 原文件路径
            
        Returns:
            str: 备份文件路径
        """
        base_name = os.path.splitext(pdf_path)[0]
        backup_path = f"{base_name}_backup.pdf"
        
        # 如果备份文件已存在，添加数字后缀
        counter = 1
        while os.path.exists(backup_path):
            backup_path = f"{base_name}_backup_{counter}.pdf"
            counter += 1
        
        shutil.copy2(pdf_path, backup_path)
        return backup_path
    
    def _convert_to_pymupdf_format(self, toc_entries: List[TOCEntry]) -> List[List]:
        """
        转换为PyMuPDF需要的目录格式
        
        Args:
            toc_entries: 目录条目列表
            
        Returns:
            List[List]: PyMuPDF格式的目录
        """
        toc_list = []
        
        for entry in toc_entries:
            # PyMuPDF格式：[level, title, page]
            toc_item = [
                entry.level,
                entry.title,
                entry.page
            ]
            toc_list.append(toc_item)
        
        return toc_list
    
    def _validate_toc_format(self, toc_list: List[List], total_pages: int) -> bool:
        """
        验证目录格式是否正确
        
        Args:
            toc_list: PyMuPDF格式的目录
            total_pages: PDF总页数
            
        Returns:
            bool: 验证是否通过
        """
        for item in toc_list:
            # 检查格式
            if not isinstance(item, list) or len(item) < 3:
                print(f"目录项格式错误: {item}")
                return False
            
            level, title, page = item[:3]
            
            # 检查数据类型
            if not isinstance(level, int) or not isinstance(title, str) or not isinstance(page, int):
                print(f"目录项数据类型错误: level={type(level)}, title={type(title)}, page={type(page)}")
                return False
            
            # 检查层级范围
            if level < 1 or level > 10:  # PyMuPDF支持的最大层级
                print(f"目录层级超出范围: {level}")
                return False
            
            # 检查页码范围 - 修正页码验证
            if page < 1 or page > total_pages:
                print(f"⚠️  页码可能有问题: {page} (总页数: {total_pages}) - 标题: {title}")
                print(f"   将尝试修正页码...")
                # 不直接返回False，而是给出警告并尝试修正
                if page < 1:
                    item[2] = 1
                elif page > total_pages:
                    item[2] = total_pages
            
            # 检查标题不为空
            if not title.strip():
                print(f"标题为空: {item}")
                return False
        
        return True
    
    def preview_existing_toc(self, pdf_path: str) -> List[List]:
        """
        预览PDF文件中现有的目录
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            List[List]: 现有的目录结构
        """
        try:
            doc = fitz.open(pdf_path)
            existing_toc = doc.get_toc()
            doc.close()
            
            if existing_toc:
                print("=== 现有目录结构 ===")
                for item in existing_toc:
                    level, title, page = item[:3]
                    indent = "  " * (level - 1)
                    print(f"{indent}• {title} (第{page}页)")
                print(f"共 {len(existing_toc)} 个目录条目\n")
            else:
                print("PDF文件中没有现有目录\n")
            
            return existing_toc
            
        except Exception as e:
            print(f"读取现有目录时发生错误: {e}")
            return []
    
    def compare_toc(self, old_toc: List[List], new_toc: List[TOCEntry]) -> None:
        """
        比较新旧目录结构
        
        Args:
            old_toc: 原有目录结构
            new_toc: 新目录结构
        """
        print("=== 目录对比 ===")
        print(f"原有目录条目数: {len(old_toc)}")
        print(f"新目录条目数: {len(new_toc)}")
        
        if old_toc:
            print("\n将替换现有目录结构")
        else:
            print("\n将为PDF添加新的目录结构")
        
        print("\n新目录预览:")
        for entry in new_toc[:10]:  # 只显示前10个
            indent = "  " * (entry.level - 1)
            print(f"{indent}• {entry.title} (第{entry.page}页)")
        
        if len(new_toc) > 10:
            print(f"... 还有 {len(new_toc) - 10} 个条目")
        
        print()