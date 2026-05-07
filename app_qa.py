import time
import streamlit as st
import config_data as config
from rag import RagService, LegalCitationFormatter


st.set_page_config(
    page_title="法律助手",
    page_icon="⚖️",
    layout="wide"
)


if "legal_rag" not in st.session_state:
    st.session_state["legal_rag"] = RagService()

if "message" not in st.session_state:
    st.session_state["message"] = [
        {"role": "assistant", "content": "您好！我是法律助手，可以为您解答《民法典》相关法律问题。请问有什么可以帮助您的？"}
    ]

if "cited_articles" not in st.session_state:
    st.session_state["cited_articles"] = []

if "similar_cases" not in st.session_state:
    st.session_state["similar_cases"] = None

if "retrieval_mode" not in st.session_state:
    st.session_state["retrieval_mode"] = "hybrid"

if "enable_case_push" not in st.session_state:
    st.session_state["enable_case_push"] = False


st.title("⚖️ 法律助手")
st.caption("基于《民法典》的智能法律问答系统")

col1, col2, col3, col4 = st.columns(4)
with col1:
    mode = st.selectbox(
        "检索模式",
        options=["hybrid", "exact", "semantic", "chapter"],
        index=["hybrid", "exact", "semantic", "chapter"].index(st.session_state["retrieval_mode"]),
        format_func=lambda x: {"hybrid": "🔍 混合检索", "exact": "📌 精确检索", "semantic": "🌐 语义检索", "chapter": "📚 章节检索"}[x]
    )
    if mode != st.session_state["retrieval_mode"]:
        st.session_state["retrieval_mode"] = mode

with col2:
    case_push = st.checkbox("🔗 启用类案推送", value=st.session_state["enable_case_push"])
    if case_push != st.session_state["enable_case_push"]:
        st.session_state["enable_case_push"] = case_push
        st.rerun()

with col3:
    st.write("")
    st.write("")

with col4:
    if st.button("🗑️ 清空对话"):
        st.session_state["message"] = [
            {"role": "assistant", "content": "您好！我是法律助手，可以为您解答《民法典》相关法律问题。请问有什么可以帮助您的？"}
        ]
        st.session_state["cited_articles"] = []
        st.session_state["similar_cases"] = None
        st.session_state["legal_rag"].reset_conversation()
        st.rerun()

st.divider()


left_col, right_col = st.columns([3, 1])


with left_col:
    for message in st.session_state["message"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "article_cards" in message:
                for card in message["article_cards"]:
                    with st.container():
                        st.info(card)

    prompt = st.chat_input("请输入您的法律问题...")

    if prompt:
        st.chat_message("user").write(prompt)
        st.session_state["message"].append({"role": "user", "content": prompt})

        session_config = {
            "configurable": {
                "session_id": f"legal_session_{int(time.time())}",
            }
        }

        with st.spinner("🔍 检索相关法条中..."):
            try:
                result = st.session_state["legal_rag"].ask(
                    question=prompt,
                    retrieval_mode=st.session_state["retrieval_mode"],
                    enable_case_push=st.session_state["enable_case_push"],
                    session_config=session_config
                )

                ai_response = result.get("answer", "抱歉，暂时无法回答您的问题。")

                article_cards = []
                if "cited_articles" in result and result["cited_articles"]:
                    st.session_state["cited_articles"] = result["cited_articles"]

                    try:
                        docs = st.session_state["legal_rag"].vector_store.search_by_article_number(
                            result["cited_articles"][0]
                        )
                        for doc in docs[:3]:
                            formatter = LegalCitationFormatter()
                            card = formatter.format_article_citation(doc)
                            article_cards.append(card)
                    except:
                        pass

                if st.session_state["enable_case_push"] and "similar_cases" in result:
                    st.session_state["similar_cases"] = result["similar_cases"]

                response_msg = {"role": "assistant", "content": ai_response}
                if article_cards:
                    response_msg["article_cards"] = article_cards

                st.session_state["message"].append(response_msg)

                with st.chat_message("assistant"):
                    st.markdown(ai_response)
                    for card in article_cards:
                        with st.container():
                            st.info(card)

            except Exception as e:
                error_msg = f"处理您的问题时出现错误: {str(e)}"
                st.chat_message("assistant").error(error_msg)
                st.session_state["message"].append({"role": "assistant", "content": error_msg})


with right_col:
    st.subheader("📖 当前引用法条")
    if st.session_state["cited_articles"]:
        for article in st.session_state["cited_articles"]:
            with st.container():
                st.markdown(f"**第{article}条**")
                st.caption("点击查看详情 →")
                st.divider()
    else:
        st.info("暂无引用法条")

    st.subheader("🔗 类案推荐")
    if st.session_state["similar_cases"]:
        st.markdown(st.session_state["similar_cases"])
    else:
        st.info("开启类案推送后显示")

    st.subheader("💡 追问引导")
    st.caption("快速提问")

    suggested_questions = [
        "民法典关于合同的最新规定是什么？",
        "遇到纠纷如何选择管辖法院？",
        "如何申请财产保全？",
        "民事诉讼时效是多久？",
        "举证责任如何分配？",
    ]

    for q in suggested_questions:
        if st.button(f"👉 {q}", key=f"q_{q[:10]}"):
            st.session_state["message"].append({"role": "user", "content": q})
            st.rerun()