import os
import re
import time

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig


st.set_page_config(page_title="VCET BOT", layout="wide")

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

load_dotenv()

MODEL_ID = "gemini-2.5-flash-lite"
WEBSITE_URL = "https://vcetputtur.ac.in/"
MAX_OUTPUT_TOKENS = 420
MAX_CALLS_PER_MINUTE = 6
NO_INFO_TEXT = "No relevant info found."
SITEMAP_URLS = [
    "https://vcetputtur.ac.in/post-sitemap1.xml",
    "https://vcetputtur.ac.in/page-sitemap1.xml",
    "https://vcetputtur.ac.in/elementor_library-sitemap1.xml",
    "https://vcetputtur.ac.in/gallery-sitemap1.xml",
    "https://vcetputtur.ac.in/faculty-sitemap1.xml",
    "https://vcetputtur.ac.in/achievements-sitemap1.xml",
    "https://vcetputtur.ac.in/academics-sitemap1.xml",
    "https://vcetputtur.ac.in/newsletter-sitemap1.xml",
    "https://vcetputtur.ac.in/projects-sitemap1.xml",
    "https://vcetputtur.ac.in/achievers-sitemap1.xml",
    "https://vcetputtur.ac.in/category-sitemap1.xml",
    "https://vcetputtur.ac.in/departments-sitemap1.xml",
    "https://vcetputtur.ac.in/faculty_type-sitemap1.xml",
    "https://vcetputtur.ac.in/achievements_type-sitemap1.xml",
    "https://vcetputtur.ac.in/achiver-type-sitemap1.xml",
]

api_key = "AIzaSyCkd4IlvJnxS7ml1AwYNPjQa_2uw-jKtGs"
client = genai.Client(api_key=api_key) if api_key else None
tools = [{"google_search": {}}]


def normalize_question(text: str) -> str:
    lowered = text.strip().lower()
    alnum_space = re.sub(r"[^a-z0-9\s]", " ", lowered)
    collapsed = re.sub(r"\s+", " ", alnum_space)
    return collapsed


def local_reply_for_smalltalk(text: str) -> str | None:
    normalized = normalize_question(text)
    if normalized in {"hi", "hello", "hey", "yo", "hola"}:
        return "Hello! Ask me anything about VCET Puttur."
    if normalized in {"thanks", "thank you", "ok thanks", "thx"}:
        return "You're welcome."
    if normalized in {"who are you", "what are you", "help"}:
        return "I can answer questions about VCET Puttur using website-grounded responses."
    return None


def is_no_info_reply(text: str) -> bool:
    normalized = normalize_question(text)
    return normalized in {"no relevant info found", "no relevant information found"}


def build_prompt(question: str, second_pass: bool = False) -> str:
    sitemap_text = "\n".join(SITEMAP_URLS)
    if not second_pass:
        return (
            "You are a VCET Puttur information assistant. "
            f"Primary website: {WEBSITE_URL}\n"
            "Prefer pages from the above domain and these sitemaps:\n"
            f"{sitemap_text}\n"
            f"Question: {question}\n"
            "Instructions:\n"
            "1) Use grounded web search and prioritize vcetputtur.ac.in pages.\n"
            "2) Return a concise factual answer.\n"
            "3) If truly unavailable, reply exactly: No relevant info found."
        )

    return (
        "Re-check carefully using broader search terms but still prioritize vcetputtur.ac.in.\n"
        f"Search hint: site:vcetputtur.ac.in {question}\n"
        f"Question: {question}\n"
        "Return the best available factual answer. "
        "Only if nothing reliable exists, reply exactly: No relevant info found."
    )


def query_model(prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=GenerateContentConfig(
            tools=tools,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.2,
        ),
    )
    return response.text if response.text else "No response generated."

st.title("ASK-VCET")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "qa_cache" not in st.session_state:
    st.session_state.qa_cache = {}

if "llm_calls" not in st.session_state:
    st.session_state.llm_calls = []

if "last_question" not in st.session_state:
    st.session_state.last_question = None

if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    normalized_question = normalize_question(user_input)
    cached_reply = st.session_state.qa_cache.get(normalized_question)
    local_reply = local_reply_for_smalltalk(user_input)

    current_time = time.time()
    st.session_state.llm_calls = [
        ts for ts in st.session_state.llm_calls if current_time - ts < 60
    ]

    if local_reply:
        reply = local_reply
    elif cached_reply:
        reply = cached_reply
    elif normalized_question == st.session_state.last_question and st.session_state.last_answer:
        reply = st.session_state.last_answer
    elif not client:
        reply = "Missing GEMINI_API_KEY in environment. Add it to your .env file and try again."
    elif len(st.session_state.llm_calls) >= MAX_CALLS_PER_MINUTE:
        reply = "Too many requests right now. Please wait a few seconds and try again."
    else:
        try:
            first_prompt = build_prompt(user_input, second_pass=False)
            reply = query_model(first_prompt)
            st.session_state.llm_calls.append(current_time)

            if is_no_info_reply(reply):
                retry_time = time.time()
                st.session_state.llm_calls = [
                    ts for ts in st.session_state.llm_calls if retry_time - ts < 60
                ]
                if len(st.session_state.llm_calls) < MAX_CALLS_PER_MINUTE:
                    second_prompt = build_prompt(user_input, second_pass=True)
                    reply = query_model(second_prompt)
                    st.session_state.llm_calls.append(retry_time)

            if not is_no_info_reply(reply) and not reply.startswith("Error:"):
                st.session_state.qa_cache[normalized_question] = reply
        except Exception as exc:
            reply = f"Error: {exc}"

    st.session_state.last_question = normalized_question
    st.session_state.last_answer = reply

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})