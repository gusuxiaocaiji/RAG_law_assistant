import time
import os

import streamlit as st
from knowledge_base import KnowledgeBaseService
from legal_entities import DocumentType

st.title("📚 知识库更新服务")

st.divider()

doc_type = st.selectbox(
    "选择文档类型",
    ["通用文档", "《民法典》原文", "判决文书"]
)

st.divider()

uploader_files = st.file_uploader(
    "请上传文件（支持批量上传）",
    type=['txt', 'pdf', 'doc', 'docx'],
    accept_multiple_files=True,
)

if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

if uploader_files is not None and len(uploader_files) > 0:
    total_files = len(uploader_files)
    
    st.divider()
    st.subheader(f"📁 待上传文件（共 {total_files} 个）")
    
    if total_files == 1:
        st.info(f"文件：{uploader_files[0].name}")
    else:
        for i, f in enumerate(uploader_files):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(f"{i+1}. {f.name}")
            with col2:
                st.text(f"{f.type}")
            with col3:
                st.text(f"{f.size / 1024:.2f} KB")
    
    st.divider()
    
    if st.button("🚀 开始批量上传", type="primary", use_container_width=True):
        results = {"success": [], "failed": []}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploader_file in enumerate(uploader_files):
            status_text.text(f"正在处理 {idx+1}/{total_files}: {uploader_file.name}")
            progress_bar.progress((idx + 1) / total_files)
            
            try:
                file_name = uploader_file.name
                file_bytes = uploader_file.getvalue()
                ext = os.path.splitext(file_name)[1].lower()
                
                if doc_type == "《民法典》原文":
                    result = st.session_state["service"].upload_legal_document(
                        file_bytes, file_name, DocumentType.CIVIL_LAW
                    )
                elif doc_type == "判决文书":
                    result = st.session_state["service"].upload_legal_document(
                        file_bytes, file_name, DocumentType.JUDGMENT
                    )
                else:
                    if ext in ['.pdf', '.doc', '.docx']:
                        result = st.session_state["service"].upload_by_file_bytes(file_bytes, file_name)
                    else:
                        text = file_bytes.decode("utf-8")
                        result = st.session_state["service"].upload_by_str(text, file_name)
                
                if "成功" in result:
                    results["success"].append((file_name, result))
                else:
                    results["failed"].append((file_name, result))
                    
            except Exception as e:
                results["failed"].append((uploader_file.name, f"处理异常: {str(e)[:50]}"))
        
        status_text.text("处理完成！")
        progress_bar.empty()
        
        st.divider()
        st.subheader("📊 上传结果汇总")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ 成功", len(results["success"]))
        with col2:
            st.metric("❌ 失败", len(results["failed"]))
        
        if results["success"]:
            with st.expander(f"✅ 成功的文件 ({len(results['success'])})", expanded=True):
                for file_name, msg in results["success"]:
                    st.success(f"**{file_name}**: {msg}")
        
        if results["failed"]:
            with st.expander(f"❌ 失败的文件 ({len(results['failed'])})", expanded=True):
                for file_name, msg in results["failed"]:
                    st.error(f"**{file_name}**: {msg}")

with st.expander("ℹ️ 支持的文件格式"):
    st.markdown("""
    **当前支持的文件格式：**

    1. **文本文件 (.txt)**
       - 最简单直接的方式
       - 确保文件编码为 UTF-8

    2. **PDF 文件 (.pdf)**
       - 支持扫描版和文本版 PDF
       - 推荐使用文本版 PDF 以获得更好的解析效果

    3. **Word 文件 (.doc, .docx)**
       - .doc：Microsoft Word 97-2003 格式
       - .docx：Microsoft Word 2007 及以上格式
       - 请确保文档结构清晰

    **上传建议：**

    - 《民法典》原文：推荐使用 PDF 格式
    - 判决文书：支持 PDF 和 Word 格式
    - 通用文档：支持所有格式
    """)
