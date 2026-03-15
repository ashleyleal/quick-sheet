import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "test"),
    base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
)

MODEL = "openai/gpt-oss-120b"


def chat(messages, max_tokens=500):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=max_tokens,
    )

    return resp.choices[0].message.content