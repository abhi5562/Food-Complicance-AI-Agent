from uuid import uuid4
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st
from langchain_core.messages import HumanMessage

from agents.workflows import create_rag_workflow, create_inspection_workflow
from schemas.schema import InspectionCategory


st.set_page_config(page_title="Food Compliance Assistant", page_icon="🍽️")


def conversation_page():
    st.title("Food Compliance Assistant")

    if "messages" not in st.session_state:
        st.session_state.workflow = create_rag_workflow
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid4())

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if query := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = st.session_state.workflow.invoke(
                    {"messages": [HumanMessage(content=query)]},
                    config={"configurable": {"thread_id": st.session_state.thread_id}},
                )
                answer = result["messages"][-1].content
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})


def image_inspection_page():
    def reset_inspection():
        st.session_state.inspection_category = InspectionCategory.FOOD_STORAGE
        st.session_state.inspection_upload_key = str(uuid4())
        st.session_state.pop("inspection_result", None)

    st.title("Image Inspection")
    if "inspection_upload_key" not in st.session_state:
        st.session_state.inspection_upload_key = str(uuid4())

    category = st.radio(
        "Category",
        list(InspectionCategory),
        format_func=lambda option: option.value,
        key="inspection_category",
    )
    image = st.file_uploader(
        "Upload an image",
        type=["jpg", "jpeg", "png", "webp"],
        key=st.session_state.inspection_upload_key,
    )
    if st.button("Submit", disabled=image is None):
        if "inspection_workflow" not in st.session_state:
            st.session_state.inspection_workflow = create_inspection_workflow()

        with st.spinner("Inspecting image..."):
            with TemporaryDirectory() as directory:
                image_path = Path(directory) / "inspection_image"
                image_path.write_bytes(image.getvalue())
                result = st.session_state.inspection_workflow.invoke({
                    "image_path": str(image_path),
                    "category": category,
                    "mime_type": image.type,
                })

        st.session_state.inspection_result = result["formatted_analysis"]

    st.button("Reset", on_click=reset_inspection)

    if "inspection_result" in st.session_state:
        st.markdown(st.session_state.inspection_result)


page = st.navigation([
    st.Page(conversation_page, title="Conversation", default=True),
    st.Page(image_inspection_page, title="Image Inspection"),
])
page.run()
