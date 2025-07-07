from typing import List
from pdf_chunker import TOCEntry
import re


class AdvancedTOCMerger:
    """高级目录合并和层级优化处理器"""
    
    def __init__(self):
        pass
    
    def merge_toc_entries(self, all_entries: List[List[TOCEntry]]) -> List[TOCEntry]:
        """
        合并多个块的目录条目，使用高级算法
        
        Args:
            all_entries: 所有块的目录条目列表
            
        Returns:
            List[TOCEntry]: 合并后的目录条目
        """
        merged = []
        
        # 展开所有条目
        for chunk_entries in all_entries:
            merged.extend(chunk_entries)
        
        if not merged:
            return []
        
        # 按页码排序
        merged.sort(key=lambda x: (x.page, x.level))
        
        # 去重和清理
        cleaned = self._remove_duplicates_advanced(merged)
        
        # 智能层级修正
        validated = self._validate_and_fix_levels_advanced(cleaned)
        
        # 最终质量检查
        final_result = self._final_quality_check(validated)
        
        return final_result
    
    def _remove_duplicates_advanced(self, entries: List[TOCEntry]) -> List[TOCEntry]:
        """
        高级去重算法 - 考虑相似性和上下文
        
        Args:
            entries: 原始目录条目列表
            
        Returns:
            List[TOCEntry]: 去重后的目录条目
        """
        if not entries:
            return []
        
        unique_entries = []
        
        for current in entries:
            is_duplicate = False
            
            for i, existing in enumerate(unique_entries):
                # 检查是否为重复项
                if self._is_duplicate_entry(current, existing):
                    # 选择更好的版本
                    better_entry = self._choose_better_entry(current, existing)
                    unique_entries[i] = better_entry
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_entries.append(current)
        
        return unique_entries
    
    def _is_duplicate_entry(self, entry1: TOCEntry, entry2: TOCEntry) -> bool:
        """判断两个条目是否为重复"""
        # 页码相近（±2页内）
        page_close = abs(entry1.page - entry2.page) <= 2
        
        # 标题相似性检查
        title_similar = self._calculate_title_similarity(entry1.title, entry2.title) > 0.8
        
        # 层级相同或相近
        level_close = abs(entry1.level - entry2.level) <= 1
        
        return page_close and title_similar and level_close
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似性（0-1）"""
        # 标准化标题
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)
        
        if t1 == t2:
            return 1.0
        
        # 计算编辑距离相似性
        max_len = max(len(t1), len(t2))
        if max_len == 0:
            return 1.0
        
        # 简单的相似性计算
        common_chars = sum(1 for a, b in zip(t1, t2) if a == b)
        return common_chars / max_len
    
    def _normalize_title(self, title: str) -> str:
        """标准化标题以便比较"""
        # 移除编号
        title = re.sub(r'^[\d\.\s\(\)①②③④⑤⑥⑦⑧⑨⑩一二三四五六七八九十]+', '', title)
        # 移除特殊字符和多余空格
        title = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
        return title.lower().strip()
    
    def _choose_better_entry(self, entry1: TOCEntry, entry2: TOCEntry) -> TOCEntry:
        """在重复条目中选择更好的版本"""
        # 优先选择标题更完整的
        if len(entry1.title) > len(entry2.title):
            return entry1
        elif len(entry2.title) > len(entry1.title):
            return entry2
        
        # 优先选择层级更合理的
        if entry1.level < entry2.level:
            return entry1
        elif entry2.level < entry1.level:
            return entry2
        
        # 优先选择页码更靠前的
        if entry1.page < entry2.page:
            return entry1
        
        return entry2
    
    def _validate_and_fix_levels_advanced(self, entries: List[TOCEntry]) -> List[TOCEntry]:
        """
        高级层级验证和修正算法
        
        Args:
            entries: 目录条目列表
            
        Returns:
            List[TOCEntry]: 层级修正后的目录条目
        """
        if not entries:
            return entries
        
        validated = []
        level_stack = []  # 跟踪层级栈
        
        for entry in entries:
            # 分析标题格式以确定正确层级
            predicted_level = self._predict_level_from_format(entry.title)
            
            # 结合上下文调整层级
            adjusted_level = self._adjust_level_with_context(
                entry.level, predicted_level, level_stack
            )
            
            # 创建新的条目
            new_entry = TOCEntry(
                title=entry.title,
                level=adjusted_level,
                page=entry.page
            )
            
            # 更新层级栈
            self._update_level_stack(level_stack, adjusted_level)
            
            validated.append(new_entry)
        
        # 后处理：确保层级的连续性
        return self._ensure_level_continuity(validated)
    
    def _predict_level_from_format(self, title: str) -> int:
        """基于标题格式预测层级"""
        title = title.strip()
        
        # 一级标题模式
        if re.match(r'^第[一二三四五六七八九十\d]+章', title):
            return 1
        if re.match(r'^[一二三四五六七八九十]\s*[、.]', title):
            return 1
        if re.match(r'^\d+\s*[、.](?!\d)', title):
            return 1
        
        # 二级标题模式
        if re.match(r'^\d+\.\d+\s', title):
            return 2
        if re.match(r'^\([一二三四五六七八九十\d]+\)', title):
            return 2
        if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', title):
            return 2
        
        # 三级标题模式
        if re.match(r'^\d+\.\d+\.\d+\s', title):
            return 3
        if re.match(r'^[a-zA-Z]\)', title):
            return 3
        if re.match(r'^[ⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]', title):
            return 3
        
        # 四级标题模式
        if re.match(r'^\d+\.\d+\.\d+\.\d+\s', title):
            return 4
        if re.match(r'^[a-z]\.\s', title):
            return 4
        
        # 默认返回2级
        return 2
    
    def _adjust_level_with_context(self, original_level: int, predicted_level: int, level_stack: List[int]) -> int:
        """结合上下文调整层级"""
        # 如果预测层级很明确，使用预测层级
        if predicted_level > 0:
            base_level = predicted_level
        else:
            base_level = original_level
        
        # 确保层级不会跳跃太大
        if level_stack:
            last_level = level_stack[-1]
            if base_level > last_level + 1:
                base_level = last_level + 1
        
        # 确保层级至少为1
        return max(1, base_level)
    
    def _update_level_stack(self, level_stack: List[int], current_level: int):
        """更新层级栈"""
        # 移除比当前层级更深的层级
        while level_stack and level_stack[-1] >= current_level:
            level_stack.pop()
        
        # 添加当前层级
        level_stack.append(current_level)
    
    def _ensure_level_continuity(self, entries: List[TOCEntry]) -> List[TOCEntry]:
        """确保层级的连续性"""
        if not entries:
            return entries
        
        result = []
        last_level = 0
        
        for entry in entries:
            current_level = entry.level
            
            # 确保层级不会跳跃太大
            if current_level > last_level + 1:
                current_level = last_level + 1
            
            # 确保层级至少为1
            current_level = max(1, current_level)
            
            result.append(TOCEntry(
                title=entry.title,
                level=current_level,
                page=entry.page
            ))
            
            last_level = current_level
        
        return result
    
    def _final_quality_check(self, entries: List[TOCEntry]) -> List[TOCEntry]:
        """最终质量检查和过滤"""
        if not entries:
            return entries
        
        filtered = []
        
        for entry in entries:
            # 过滤明显不是标题的条目
            if self._is_valid_title(entry.title):
                filtered.append(entry)
        
        return filtered
    
    def _is_valid_title(self, title: str) -> bool:
        """判断是否为有效标题（更严格的标准）"""
        title = title.strip()
        
        # 基本长度检查
        if len(title) < 3 or len(title) > 50:
            return False
        
        # 纯数字、日期或符号
        if re.match(r'^[\d\s\.\-_年月日]+$', title):
            return False
        
        # 以句号、感叹号、问号结尾的（可能是句子而非标题）
        if re.search(r'[。！？]$', title):
            return False
        
        # 包含过多标点符号的（可能是句子片段）
        punctuation_count = len(re.findall(r'[，。；：！？""''（）]', title))
        if punctuation_count > 2:
            return False
        
        # 明显的排除模式
        exclude_patterns = [
            r'^图\s*\d+',
            r'^表\s*\d+',
            r'^Figure\s*\d+',
            r'^Table\s*\d+',
            r'第\s*\d+\s*页',
            r'Page\s*\d+',
            r'^参考文献',
            r'^致谢',
            r'^附录[A-Z]?$',
            r'^\d{4}年',  # 纯年份
            r'具体而言',   # 句子开头
            r'根据.*',    # 句子开头
            r'.*。.*',    # 包含句号的句子
            r'^[a-z]+\.[a-z]+',  # 网址片段
            r'双语优势',   # 描述性内容
            r'语言考试替代', # 描述性内容
            r'课程环境',   # 描述性内容
            r'能力.*的.*', # 描述性句子模式
            r'项目.*允许', # 描述性句子模式
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return False
        
        # 检查是否有明确的标题格式
        title_patterns = [
            r'^第[一二三四五六七八九十\d]+章',
            r'^第[一二三四五六七八九十\d]+节',
            r'^[一二三四五六七八九十]\s*[、.]',
            r'^\d+\s*[、.]',
            r'^\d+\.\d+',
            r'^\([一二三四五六七八九十\d]+\)',
            r'^[①②③④⑤⑥⑦⑧⑨⑩]',
        ]
        
        # 如果有明确的标题格式，直接通过
        for pattern in title_patterns:
            if re.match(pattern, title):
                return True
        
        # 否则需要更严格的检查
        # 不能包含太多的描述性词汇
        descriptive_words = ['能力', '环境', '课程', '项目', '院校', '成绩', '证明', '具备', '允许', '作为', '同时', '发展', '状况', '情况', '内容', '方面']
        descriptive_count = sum(1 for word in descriptive_words if word in title)
        if descriptive_count > 1:
            return False
        
        return True
    
    def format_for_pymupdf(self, entries: List[TOCEntry]) -> List[List]:
        """
        将目录条目格式化为PyMuPDF需要的格式
        
        Args:
            entries: 目录条目列表
            
        Returns:
            List[List]: PyMuPDF格式的目录列表
        """
        toc_list = []
        
        for entry in entries:
            # PyMuPDF的目录格式：[level, title, page, zoom_info]
            toc_item = [
                entry.level,
                entry.title,
                entry.page
            ]
            toc_list.append(toc_item)
        
        return toc_list
    
    def print_toc_preview(self, entries: List[TOCEntry]) -> None:
        """
        打印目录预览（增强版）
        
        Args:
            entries: 目录条目列表
        """
        print("\n=== 提取的目录结构 ===")
        
        if not entries:
            print("未找到任何目录条目")
            return
        
        # 按层级统计
        level_counts = {}
        for entry in entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
        
        print(f"层级统计: {dict(sorted(level_counts.items()))}")
        print()
        
        for entry in entries:
            indent = "  " * (entry.level - 1)
            level_indicator = "►" if entry.level == 1 else "▪"
            print(f"{indent}{level_indicator} {entry.title} (第{entry.page}页)")
        
        print(f"\n总计 {len(entries)} 个目录条目")
    
    def save_toc_to_json(self, entries: List[TOCEntry], output_path: str) -> None:
        """
        将目录保存为JSON文件（增强版）
        
        Args:
            entries: 目录条目列表
            output_path: 输出文件路径
        """
        import json
        from dataclasses import asdict
        import time
        
        # 构建详细的元数据
        toc_data = {
            'metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_entries': len(entries),
                'level_distribution': {},
                'page_range': {
                    'first': min(entry.page for entry in entries) if entries else 0,
                    'last': max(entry.page for entry in entries) if entries else 0
                }
            },
            'toc_entries': [asdict(entry) for entry in entries]
        }
        
        # 统计层级分布
        for entry in entries:
            level = entry.level
            toc_data['metadata']['level_distribution'][level] = \
                toc_data['metadata']['level_distribution'].get(level, 0) + 1
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(toc_data, f, ensure_ascii=False, indent=2)
        
        print(f"📄 增强目录已保存到: {output_path}")


# 为了向后兼容，保留原有的类名
class TOCMerger(AdvancedTOCMerger):
    """向后兼容的TOCMerger类"""
    pass