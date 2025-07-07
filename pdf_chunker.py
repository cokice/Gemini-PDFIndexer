import fitz  # PyMuPDF
import math
import io
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TOCEntry:
    """目录条目数据类"""
    title: str
    level: int
    page: int


class PDFChunker:
    """PDF 文件分块处理器"""
    
    def __init__(self, max_pages: int = 1000):
        self.max_pages = max_pages
    
    def get_pdf_info(self, pdf_path: str) -> Tuple[int, int]:
        """获取PDF文件信息：页数和总大小"""
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # 估算总大小（基于前几页的字符数）
        sample_pages = min(5, total_pages)
        sample_size = 0
        
        for i in range(sample_pages):
            page = doc.load_page(i)
            text = page.get_text()
            sample_size += len(text)
        
        doc.close()
        
        # 估算总字符数
        estimated_total_size = (sample_size // sample_pages) * total_pages if sample_pages > 0 else 0
        
        return total_pages, estimated_total_size
    
    def chunk_pdf(self, pdf_path: str) -> List[Tuple[bytes, int, int]]:
        """
        将PDF文件分块
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            List of tuples: (pdf_bytes, start_page, end_page)
        """
        total_pages, _ = self.get_pdf_info(pdf_path)
        chunks = []
        
        # 计算需要的块数
        num_chunks = math.ceil(total_pages / self.max_pages)
        
        doc = fitz.open(pdf_path)
        
        for i in range(num_chunks):
            start_page = i * self.max_pages
            end_page = min((i + 1) * self.max_pages, total_pages)
            
            # 创建新文档包含指定页面范围
            chunk_doc = fitz.open()
            chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
            
            # 转换为字节流
            chunk_bytes = chunk_doc.tobytes()
            chunks.append((chunk_bytes, start_page + 1, end_page))  # 页码从1开始
            
            chunk_doc.close()
        
        doc.close()
        return chunks
    
    def extract_text_from_chunk(self, chunk_bytes: bytes) -> str:
        """从PDF块中提取文本"""
        doc = fitz.open(stream=chunk_bytes, filetype="pdf")
        text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += f"\n--- 第 {page_num + 1} 页 ---\n"
            text += page.get_text()
        
        doc.close()
        return text