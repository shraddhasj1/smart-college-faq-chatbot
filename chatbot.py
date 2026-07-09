from pathlib import Path

import streamlit as st

try:
    import ollama
except ModuleNotFoundError:
    ollama = None

st.set_page_config(page_title="FAQ Chatbot", page_icon="🤖", layout="centered")
st.title("FAQ Chatbot")


def load_context() -> str:
    syllabus_path = Path(__file__).with_name("syllabus.txt")
    with syllabus_path.open("r", encoding="utf-8") as file:
        return file.read()


def build_prompt(question: str, context: str) -> str:
    return f"""
You are a helpful college FAQ chatbot.

Answer only based on the given information.
If the answer is not available, say:
"Sorry, I don’t have that information."

Information:
{context}

Question:
{question}

Give a simple and clear answer.
"""


if "messages" not in st.session_state:
    st.session_state.messages = []

context = load_context()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if ollama is None:
    st.error("The 'ollama' Python package is not installed in this environment.")
    st.code("python -m pip install ollama")
    st.info("Install Ollama on your machine and start it with 'ollama serve' before chatting.")
    st.stop()

user_input = st.chat_input("Ask your question")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Thinking..."):
        try:
            response = ollama.chat(
                model="llama3",
                messages=[{"role": "user", "content": build_prompt(user_input, context)}],
            )
            answer = response["message"]["content"]
        except Exception as exc:
            answer = f"Error: {exc}"

    st.session_state.messages.append({"role": "assistant", "content": answer})

    with st.chat_message("assistant"):
        st.markdown(answer)

    st.rerun()
