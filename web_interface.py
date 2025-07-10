#!/usr/bin/env python3
"""
Gemini PDF Indexer Web Interface
简单的Web界面用于上传PDF文件并处理
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, session
import threading
import time
import uuid

# 导入主要处理模块
from gemini_extractor import GeminiTitleExtractor
from pdf_chunker import PDFChunker
from toc_merger import TOCMerger
from pdf_toc_writer import PDFTOCWriter

app = Flask(__name__)
app.secret_key = 'gemini-pdf-indexer-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# 全局处理状态
processing_status = {}

def get_api_key():
    """获取API Key，优先从session，然后从环境变量"""
    if 'custom_api_key' in session and session['custom_api_key']:
        return session['custom_api_key']
    
    # 从环境变量读取
    return os.getenv('GOOGLE_AI_API_KEY', '')

@app.route('/')
def index():
    """主页"""
    api_key = get_api_key()
    has_api_key = bool(api_key)
    return render_template('index.html', has_api_key=has_api_key)

@app.route('/settings')
def settings():
    """设置页面"""
    env_api_key = os.getenv('GOOGLE_AI_API_KEY', '')
    custom_api_key = session.get('custom_api_key', '')
    return render_template('settings.html', 
                         env_api_key=bool(env_api_key), 
                         custom_api_key=custom_api_key)

@app.route('/save_settings', methods=['POST'])
def save_settings():
    """保存设置"""
    custom_api_key = request.form.get('custom_api_key', '').strip()
    
    if custom_api_key:
        session['custom_api_key'] = custom_api_key
        flash('自定义API Key已保存', 'success')
    else:
        session.pop('custom_api_key', None)
        flash('已清除自定义API Key，将使用环境变量', 'info')
    
    return redirect(url_for('settings'))

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    if 'pdf_file' not in request.files:
        flash('请选择一个PDF文件', 'error')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    
    if file.filename == '':
        flash('请选择一个PDF文件', 'error')
        return redirect(url_for('index'))
    
    # 获取API Key
    api_key = get_api_key()
    if not api_key:
        flash('请先设置Gemini API Key', 'error')
        return redirect(url_for('settings'))
    
    if file and file.filename.lower().endswith('.pdf'):
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 保存上传的文件
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)
        
        # 设置输出路径
        output_filename = file.filename.replace('.pdf', '_with_bookmarks.pdf')
        output_path = os.path.join(temp_dir, output_filename)
        
        # 初始化处理状态
        processing_status[task_id] = {
            'status': 'starting',
            'progress': 0,
            'message': '准备开始处理...',
            'input_path': input_path,
            'output_path': output_path,
            'output_filename': output_filename,
            'temp_dir': temp_dir
        }
        
        # 启动后台处理线程
        thread = threading.Thread(
            target=process_pdf_background,
            args=(task_id, input_path, output_path, api_key)
        )
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('processing', task_id=task_id))
    
    flash('请上传有效的PDF文件', 'error')
    return redirect(url_for('index'))

@app.route('/processing/<task_id>')
def processing(task_id):
    """处理进度页面"""
    if task_id not in processing_status:
        flash('无效的任务ID')
        return redirect(url_for('index'))
    
    return render_template('processing.html', task_id=task_id)

@app.route('/status/<task_id>')
def get_status(task_id):
    """获取处理状态API"""
    if task_id in processing_status:
        return jsonify(processing_status[task_id])
    return jsonify({'status': 'not_found'}), 404

@app.route('/download/<task_id>')
def download_file(task_id):
    """下载处理后的文件"""
    if task_id not in processing_status:
        flash('无效的任务ID')
        return redirect(url_for('index'))
    
    status = processing_status[task_id]
    if status['status'] != 'completed':
        flash('文件还未处理完成')
        return redirect(url_for('processing', task_id=task_id))
    
    if not os.path.exists(status['output_path']):
        flash('输出文件不存在')
        return redirect(url_for('index'))
    
    return send_file(
        status['output_path'],
        as_attachment=True,
        download_name=status['output_filename']
    )

def process_pdf_background(task_id, input_path, output_path, api_key):
    """后台处理PDF文件"""
    try:
        # 更新状态
        processing_status[task_id].update({
            'status': 'analyzing',
            'progress': 10,
            'message': '分析PDF文件...'
        })
        
        # 分析PDF
        chunker = PDFChunker(max_pages=1000)
        total_pages, estimated_size = chunker.get_pdf_info(input_path)
        
        processing_status[task_id].update({
            'progress': 20,
            'message': f'文件信息: {total_pages}页, 预计{estimated_size:,}字符'
        })
        
        # 分块处理
        processing_status[task_id].update({
            'status': 'chunking',
            'progress': 30,
            'message': '分块读取PDF...'
        })
        
        chunks = chunker.chunk_pdf(input_path)
        
        # 初始化提取器
        processing_status[task_id].update({
            'status': 'extracting',
            'progress': 40,
            'message': '初始化Gemini AI...'
        })
        
        extractor = GeminiTitleExtractor(api_key=api_key)
        
        # 提取标题
        processing_status[task_id].update({
            'progress': 50,
            'message': '提取文档标题结构...'
        })
        
        all_toc_entries = []
        for i, (chunk_bytes, start_page, end_page) in enumerate(chunks):
            progress = 50 + (i + 1) / len(chunks) * 30  # 50%-80%
            processing_status[task_id].update({
                'progress': int(progress),
                'message': f'处理第 {start_page}-{end_page} 页...'
            })
            
            try:
                toc_entries = extractor.extract_titles_from_pdf_bytes(
                    chunk_bytes, start_page, end_page
                )
            except Exception as e:
                # 回退到文本提取
                text = chunker.extract_text_from_chunk(chunk_bytes)
                toc_entries = extractor.extract_titles_from_text(text, start_page, end_page)
            
            all_toc_entries.append(toc_entries)
        
        # 合并目录 - 使用与命令行版本相同的高级算法
        processing_status[task_id].update({
            'progress': 85,
            'message': '合并和排序目录...'
        })
        
        merger = TOCMerger()
        final_toc = merger.merge_toc_entries(all_toc_entries)
        
        if not final_toc:
            processing_status[task_id].update({
                'status': 'error',
                'message': '未提取到任何目录条目，请检查PDF文档是否包含标题结构'
            })
            return
        
        # 写入目录
        processing_status[task_id].update({
            'progress': 95,
            'message': f'写入目录书签({len(final_toc)}个条目)...'
        })
        
        writer = PDFTOCWriter()
        writer.write_toc_to_pdf(input_path, final_toc, output_path)
        
        # 完成
        processing_status[task_id].update({
            'status': 'completed',
            'progress': 100,
            'message': f'处理完成！提取了{len(final_toc)}个标题条目'
        })
        
    except Exception as e:
        processing_status[task_id].update({
            'status': 'error',
            'message': f'处理失败: {str(e)}'
        })

@app.route('/cleanup/<task_id>')
def cleanup_task(task_id):
    """清理任务文件"""
    if task_id in processing_status:
        temp_dir = processing_status[task_id].get('temp_dir')
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        del processing_status[task_id]
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    # 创建templates目录
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 启动Gemini PDF Indexer Web界面...")
    print("📱 访问地址: http://localhost:5000")
    print("🛑 按Ctrl+C停止服务")
    
    app.run(debug=True, host='0.0.0.0', port=5000)