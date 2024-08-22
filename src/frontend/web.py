# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import streamlit as st
import chatbot as agent
import os
import re
import uuid
import json
from typing import List, Dict
from streamlit_card import card
from botocore.exceptions import ClientError

WORKLOAD_PREFIX = "Parts Catalog"

def render_sidebar():
    with st.sidebar:
        with st.container():
            st.sidebar.markdown(f"<h2> Welcome to {WORKLOAD_PREFIX}</h2>", unsafe_allow_html=True)
        st.divider()
        st.markdown('**Session:** :blue[{}]'.format(st.session_state.id))
        with st.container():
            st.button("Clear Chat 🗑️", "clear_chat", on_click=clear_session)

def clear_session():
    print("Clearing session...")
    st.session_state.messages = []

def render_structured_data(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            st.error("Failed to parse structured data")
            return

    all_parts = []
    if isinstance(data, dict) and 'parts' in data:
        all_parts = data['parts']
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if 'parts' in item:
                    all_parts.extend(item['parts'])
                else:
                    all_parts.append(item)
            else:
                st.error(f"Unexpected data format: {item}")
    else:
        st.error(f"Unexpected data format: {data}")

    # Display parts in rows of 4
    for i in range(0, len(all_parts), 4):
        cols = st.columns(4, gap="small")
        for j in range(4):
            if i + j < len(all_parts):
                with cols[j]:
                    render_card(all_parts[i + j], i + j)

def extract_structured_data(response: str) -> tuple:
    
    def replace_tags(match):
        tag = match.group(1)
        content = match.group(2)
        return f"**{tag.capitalize()}:** {content}"
    
    parts = response.split("<structured_data>")
    markdown_response = parts[0].strip()
    structured_data_str = parts[1].split("</structured_data>")[0].strip() if len(parts) > 1 else None
    
    markdown_response = re.sub(r'<(question|sources)>(.*?)</\1>', replace_tags, markdown_response, flags=re.DOTALL)
    
    structured_data = None
    if structured_data_str:
        try:
            # Remove any leading/trailing whitespace and newlines
            structured_data_str = structured_data_str.strip()
            # Parse the JSON data
            parsed_data = json.loads(structured_data_str)
            
            # Check if the data is in the '_source' format or the 'parts' format
            if isinstance(parsed_data, list) and all('_source' in item for item in parsed_data):
                print("Response uses _source format")
                structured_data = [item['_source'] for item in parsed_data]
            elif isinstance(parsed_data, list) and all('parts' in item for item in parsed_data):
                print("Response uses parts format")
                structured_data = {'parts': [part for item in parsed_data for part in item['parts']]}
            else:
                print("Response uses no format")
                structured_data = parsed_data
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            structured_data = structured_data_str  # Keep the original string if parsing fails
    
    return markdown_response, structured_data

def render_card(part: Dict, index: int):
    colors = [
        "#E8F0FE", "#F0F4F8", "#E6F3FF", "#F5F5F5",
        "#FFF8E1", "#F1F8E9", "#FAFAFA", "#E0F2F1",
    ]
    
    bg_color = colors[index % len(colors)]
    
    text_content = [
        f"Part #: {part.get('part_number', 'N/A')}",
        part.get('description', 'No description')[:40] + "..." if len(part.get('description', '')) > 40 else part.get('description', 'No description'),
    ]

    if 'price' in part:
        text_content.append(f"${part['price']} {part.get('currency', 'USD')}")

    if 'in_stock' in part:
        text_content.append("In Stock" if part['in_stock'] else "Out of Stock")

    if 'rating' in part:
        text_content.append(f"Rating: {part['rating']}")

    card(
        title=part.get("part_name", "Unknown Part"),
        text=text_content,
        styles={
            "card": {
                "width": "100%",
                "height": "250px",
                "border-radius": "8px",
                "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
                "transition": "all 0.3s ease",
                "margin-bottom": "10px",
                "background-color": bg_color,
            },
            "title": {
                "font-size": "18px",
                "font-weight": "bold",
                "color": "white",
                "text-shadow": "1px 1px 2px rgba(0,0,0,0.8)",
            },
            "text": {
                "font-size": "14px",
                "color": "white",
                "text-shadow": "1px 1px 2px rgba(0,0,0,0.8)",
            },
        }
    )

def get_agent_response(prompt: str):
    try:
        response, trace = agent.get_chat_response(prompt, st.session_state.id)
        if not trace:
            trace = dict()
        markdown_response, structured_data = extract_structured_data(response)
        print("Structured data: ", structured_data)
    except Exception as e:
        print(f"Unexpected error in get_agent_response: {e}")
        markdown_response = f"An unexpected error occurred: {e}"
        structured_data = None
        trace = dict()

    return {
        "role": "assistant",
        "content": markdown_response,
        "structured_data": structured_data,
        "trace": trace
    }

st.set_page_config(
    page_title=f"{WORKLOAD_PREFIX} Assistant",
    page_icon="🔧",
    layout="wide"
)

st.header(f"Parts Catalog Agent", divider='blue')

if "id" not in st.session_state:
    st.session_state.id = str(uuid.uuid4())[1:8]

if "messages" not in st.session_state:
    st.session_state.messages = []

render_sidebar()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "structured_data" in message and message["structured_data"]:
            render_structured_data(message["structured_data"])
        if "trace" in message and message["role"] == "assistant":
            with st.expander("Trace", expanded=False):
                st.json(message["trace"], expanded=True)

if prompt := st.chat_input("How can I help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        response = get_agent_response(prompt)

        st.session_state.messages.append(response)
        with st.chat_message("assistant"):
            st.markdown(response["content"])
            if response["structured_data"]:
                render_structured_data(response["structured_data"])
            with st.expander("Trace", expanded=False):
                st.json(response["trace"], expanded=True)

    st.rerun()