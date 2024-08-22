# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import logging
from typing import Tuple, List, Dict, Any
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
AWS_REGION = os.environ.get("AWS_REGION")
AGENT_ID = os.environ.get("AGENT_ID")
AGENT_ALIAS_ID = os.environ.get("AGENT_ALIAS_ID")

# Validate required environment variables
if not all([AWS_REGION, AGENT_ID, AGENT_ALIAS_ID]):
    raise ValueError("Missing required environment variables: AWS_REGION, AGENT_ID, or AGENT_ALIAS_ID")

# Initialize Bedrock Agent Runtime client
client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

def ask_question(question: str, session_id: str, end_session: bool = False) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Ask a question to the Bedrock Agent and process the response.

    Args:
        question (str): The question to ask.
        session_id (str): The session ID.
        end_session (bool): Whether to end the session.

    Returns:
        Tuple[str, List[Dict[str, Any]]]: The response and trace.
    """
    logger.info(f"Asking question: {question}")

    try:
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            endSession=end_session,
            enableTrace=True,
            inputText=question
        )

        logger.debug(f"Raw response: {response}")

        return process_response(response)
    except ClientError as e:
        logger.error(f"ClientError in ask_question: {e}")
        return str(e), []
    except Exception as e:
        logger.error(f"Unexpected error in ask_question: {e}")
        return str(e), []

def process_response(response: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Process the response from the Bedrock Agent.

    Args:
        response (Dict[str, Any]): The raw response from the Bedrock Agent.

    Returns:
        Tuple[str, List[Dict[str, Any]]]: The processed response and trace.
    """
    steps = response.get('completion', [])
    trace = []
    final_response = ""

    for step in steps:
        if "trace" in step:
            current_trace = step['trace']['trace']
            process_trace(current_trace, trace)
        if "chunk" in step:
            chunk_data = step['chunk']['bytes'].decode('utf-8')
            final_response += chunk_data
            logger.info(f"Chunk: {chunk_data}")

    logger.info(f"Final response: {final_response}")
    return final_response, trace

def process_trace(current_trace: Dict[str, Any], trace: List[Dict[str, Any]]) -> None:
    """
    Process and append trace information.

    Args:
        current_trace (Dict[str, Any]): The current trace to process.
        trace (List[Dict[str, Any]]): The list to append processed traces.
    """
    for key in ['preProcessingTrace', 'orchestrationTrace']:
        if key in current_trace:
            current_trace[key].pop('modelInvocationInput', None)
            if current_trace[key]:
                trace.append({key: current_trace[key]})

def get_chat_response(prompt: str, session_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Get a chat response for the given prompt.

    Args:
        prompt (str): The chat prompt.
        session_id (str): The session ID.

    Returns:
        Tuple[str, List[Dict[str, Any]]]: The response and trace.
    """
    logger.info(f"Session: {session_id} asked question: {prompt}")

    return ask_question(prompt, session_id)
