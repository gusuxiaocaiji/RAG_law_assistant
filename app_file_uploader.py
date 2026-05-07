import time
import os

import streamlit as st
from knowledge_base import KnowledgeBaseService
from legal_entities import DocumentType

st.title("知识库更新服务")

st.divider()

doc_type = st.selectbox(
    "选择文档类型",
    ["通用文档", "《民法典》原文", "判决文书"]
)

st.divider()

uploader_file = st.file_uploader(
    "请上传文件",
    type=['txt', 'pdf', 'doc', 'docx'],
    accept_multiple_files=False,
)

if "service" not in st.session_state:
    st.session_state["service"] = KnowledgeBaseService()

if uploader_file is not None:
    file_name = uploader_file.name
    file_type = uploader_file.type
    file_size = uploader_file.size / 1024

    st.subheader(f"文件名：{file_name}")
    st.write(f"格式：{file_type}|大小：{file_size:.2f}KB")
    st.write(f"文档类型：{doc_type}")

    with st.spinner("载入知识库中..."):
        time.sleep(0.5)
        
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
            st.success(result)
        else:
            st.error(result)
