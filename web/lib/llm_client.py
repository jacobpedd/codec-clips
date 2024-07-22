from openai import OpenAI
from codec import settings

# Use Braintrust proxy for OpenAI API
llm_client = OpenAI(
    base_url="https://braintrustproxy.com/v1",
    api_key=settings.BRAINTRUST_API_KEY,
    default_headers={"x-bt-use-cache": "always"},
)
