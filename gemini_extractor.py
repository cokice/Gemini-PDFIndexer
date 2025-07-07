from google import genai
from google.genai import types
import json
import io
import os
from typing import List, Dict, Optional
from dataclasses import asdict
from pdf_chunker import TOCEntry


class GeminiTitleExtractor:
    """使用 Gemini 2.5 Flash 进行标题抽取 - 简化版"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Gemini 客户端
        
        Args:
            api_key: Google AI API key，如果为 None 则从环境变量获取
        """
        if api_key is None:
            api_key = os.getenv('GOOGLE_AI_API_KEY')
        
        if not api_key:
            raise ValueError("需要提供 Google AI API key，请设置环境变量 GOOGLE_AI_API_KEY 或直接传入")
        
        # 创建客户端（新版API直接传入密钥）
        self.client = genai.Client(api_key=api_key)
        
        # 简洁有效的系统指令
        self.system_instruction = """
你是PDF目录提取专家。请只提取真正的章节标题，不要提取描述性文字。

标准：
- 只提取有明确编号的标题（如：1.、1.1、第一章）
- 最多3级标题
- 标题长度2-40字
- 忽略日期、描述、网址等内容

输出JSON格式：[{"title": "标题", "level": 层级, "page": 页码}]
"""
    
    def extract_titles_from_pdf_bytes(self, pdf_bytes: bytes, chunk_start_page: int, chunk_end_page: int) -> List[TOCEntry]:
        """
        直接从PDF字节流中提取标题
        
        Args:
            pdf_bytes: PDF文件字节流
            chunk_start_page: 块起始页码
            chunk_end_page: 块结束页码
            
        Returns:
            List[TOCEntry]: 提取的标题列表
        """
        try:
            # 修正的提示词 - 区分PDF页面序号和文档页码
            # 修正的提示词 - 区分PDF页面序号和文档页码
            prompt = f"""
分析第 {chunk_start_page}-{chunk_end_page} 页，提取章节标题。

重要说明：
- 这是PDF的第 {chunk_start_page}-{chunk_end_page} 页面
- 如果文档有封面等，实际内容页码可能不同
- 请根据标题在这个PDF页面范围内的位置，输出对应的PDF页面序号
- 比如：标题在传入的第1个页面，应输出 {chunk_start_page}；在第2个页面，应输出 {chunk_start_page + 1}

要求：
- 只要有编号的主要标题（1.、1.1、第一章等）  
- 最多3级，2-40字
- 不要描述文字、日期、网址
- 页码要对应PDF的实际页面序号，不是文档内容的页码编号

直接输出JSON：[{{"title": "标题", "level": 1, "page": {chunk_start_page}}}]
"""
            
            # 检查PDF大小，决定使用哪种方式
            pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
            
            if pdf_size_mb > 20:
                # 使用File API处理大文件
                return self._extract_with_file_api(pdf_bytes, prompt, chunk_start_page, chunk_end_page)
            else:
                # 直接处理小文件
                return self._extract_direct(pdf_bytes, prompt, chunk_start_page, chunk_end_page)
                
        except Exception as e:
            print(f"PDF标题提取过程中发生错误: {e}")
            # 如果失败，回退到文本提取方式
            return self._fallback_text_extraction(pdf_bytes, chunk_start_page)
    
    def _extract_direct(self, pdf_bytes: bytes, prompt: str, chunk_start_page: int, chunk_end_page: int) -> List[TOCEntry]:
        """直接处理小PDF文件"""
        try:
            # 使用新的API格式处理PDF
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type='application/pdf'
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json",
                    response_schema={"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "level": {"type": "integer"}, "page": {"type": "integer"}}, "required": ["title", "level", "page"]}}
                )
            )
            
            # 提取文本用于智能分析器
            try:
                from pdf_chunker import PDFChunker
                chunker = PDFChunker()
                original_text = chunker.extract_text_from_chunk(pdf_bytes)
            except:
                original_text = ""
            
            return self._parse_response(response.text, chunk_start_page, chunk_end_page, original_text)
            
        except Exception as e:
            print(f"直接处理PDF失败: {e}")
            raise
    
    def _extract_with_file_api(self, pdf_bytes: bytes, prompt: str, chunk_start_page: int, chunk_end_page: int) -> List[TOCEntry]:
        """使用File API处理大PDF文件"""
        try:
            # 上传PDF到File API
            pdf_io = io.BytesIO(pdf_bytes)
            uploaded_file = self.client.files.upload(
                file=pdf_io,
                config=dict(mime_type='application/pdf')
            )
            
            # 处理上传的文件
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json",
                    response_schema={"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "level": {"type": "integer"}, "page": {"type": "integer"}}, "required": ["title", "level", "page"]}}
                )
            )
            
            # 提取文本用于智能分析器
            try:
                from pdf_chunker import PDFChunker
                chunker = PDFChunker()
                original_text = chunker.extract_text_from_chunk(pdf_bytes)
            except:
                original_text = ""
            
            return self._parse_response(response.text, chunk_start_page, chunk_end_page, original_text)
            
        except Exception as e:
            print(f"File API处理失败: {e}")
            raise
    
    def _parse_response(self, response_text: str, chunk_start_page: int, chunk_end_page: int, original_text: str = "") -> List[TOCEntry]:
        """解析API响应"""
        try:
            if not response_text:
                return []
            
            # 解析AI返回的结果
            ai_results = json.loads(response_text)
            
            # 转换为TOCEntry对象
            titles = []
            for item in ai_results:
                if isinstance(item, dict) and all(key in item for key in ['title', 'level', 'page']):
                    title = item['title'].strip()
                    level = min(int(item['level']), 3)  # 限制到3级
                    
                    # 页码处理 - 验证和调试
                    raw_page = item['page']
                    
                    # 验证页码是否在合理范围内
                    if chunk_start_page <= raw_page <= chunk_end_page:
                        # 页码在预期范围内，直接使用
                        actual_page = raw_page
                    elif 1 <= raw_page <= (chunk_end_page - chunk_start_page + 1):
                        # 页码是相对的，需要转换为绝对页码
                        actual_page = raw_page + chunk_start_page - 1
                        print(f"🔧 页码调整: {title} 从相对页码 {raw_page} 调整为绝对页码 {actual_page}")
                    else:
                        # 页码异常，使用默认值
                        actual_page = chunk_start_page
                        print(f"⚠️  页码异常: {title} 原页码 {raw_page}，使用默认页码 {actual_page}")
                    
                    print(f"📍 标题: {title} → PDF第{actual_page}页")
                    
                    # 简单过滤：长度和基本格式检查
                    if 2 <= len(title) <= 40 and not any(word in title for word in ['具体而言', '根据', '.jp', '.com']):
                        titles.append(TOCEntry(
                            title=title,
                            level=level,
                            page=max(1, actual_page)
                        ))
            
            return titles
        
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return []
        except Exception as e:
            print(f"解析错误: {e}")
            return []
    
    def _fallback_text_extraction(self, pdf_bytes: bytes, chunk_start_page: int) -> List[TOCEntry]:
        """回退到文本提取方式"""
        try:
            from pdf_chunker import PDFChunker
            chunker = PDFChunker()
            text = chunker.extract_text_from_chunk(pdf_bytes)
            return self.extract_titles_from_text(text, chunk_start_page)
        except Exception as e:
            print(f"文本提取回退也失败: {e}")
            return []
    
    def extract_titles_from_text(self, text: str, chunk_start_page: int, chunk_end_page: int = None) -> List[TOCEntry]:
        """
        从文本中提取标题（回退方法）
        
        Args:
            text: PDF文本内容
            chunk_start_page: 当前块的起始页码
            
        Returns:
            List[TOCEntry]: 提取的标题列表
        """
        try:
            # 构建提示词
            prompt = f"""
请分析以下PDF文档文本，提取其中的标题结构。

文档文本：
{text}

注意：
1. 文本中的 "--- 第 X 页 ---" 标记了页码信息
2. 输出的 page 字段应该基于这些页码标记计算实际页码
3. 当前文档块从第 {chunk_start_page} 页开始
4. 严格按照JSON格式输出，不要添加任何解释性文字

输出格式：
[
  {{"title": "标题", "level": 层级, "page": 页码}},
  ...
]
"""
            
            # 使用文本处理
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type="application/json",
                    response_schema={"type": "array", "items": {"type": "object", "properties": {"title": {"type": "string"}, "level": {"type": "integer"}, "page": {"type": "integer"}}, "required": ["title", "level", "page"]}}
                )
            )
            
            return self._parse_response(response.text, chunk_start_page, chunk_end_page or chunk_start_page + 100, text)
            
        except Exception as e:
            print(f"文本标题提取过程中发生错误: {e}")
            return []