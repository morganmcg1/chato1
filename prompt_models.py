import os
import openai
import weave
from pydantic import BaseModel
from dotenv import load_dotenv
import instructor
import time

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

PROMPT_GEN_SYSTEM_PROMPT = """
You are an AI prompt engineer. You will be given a user prompt. \
Your job is to generate a prompt for a smaller, weak model that \
help the smaller model solve the task.

You are able to deliver concise, terse instructions that are high \
signal.
"""


PROMPT_GEN_PROMPT = """
Given the following <task>, write a detailed prompt for a smaller, weak model \
that will help guide it towards solving the task.

## Task
<task>
{{task}}
</task>

Providing your reasoning will also help guide the smaller model to solve the task.

## Style
Write your prompt as if directly instructing the smaller model itself.
"""

class PromptModel(BaseModel):
    original_input_user_prompt: str
    system_prompt: str
    user_prompt: str


client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client = instructor.from_openai(client)


@weave.op
def call_dummy_llm(
    system_prompt: str = "",
    user_prompt: str = "",
    model_name: str = "gpt-4o-mini",
    response_model: BaseModel = None,
    sleep_time: float = 0,
):
    if sleep_time > 0:
        logger.debug(f"Sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)
    return PromptModel(
        original_input_user_prompt=user_prompt,
        system_prompt=system_prompt,
        user_prompt=f"dummy_{model_name}_output_{system_prompt[:10]}_{user_prompt[:10]}",
    )


@weave.op
def call_llm(system_prompt: str = "",
              user_prompt: str = "",
              model_name: str = "gpt-4o-mini",
              response_model: BaseModel = None,
            #   temperature: float = None,
              ):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if "o1" in model_name:
        messages.pop(0)

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_model=response_model,
        # temperature=temperature,
    )
    if response_model is not None:
        return response
    else:
        return response.choices[0].message.content
