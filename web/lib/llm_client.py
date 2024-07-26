from openai import OpenAI
from codec import settings

from langsmith.wrappers import wrap_openai


# Use Braintrust proxy for OpenAI API
llm_client = wrap_openai(
    OpenAI(
        base_url="https://braintrustproxy.com/v1",
        api_key=settings.BRAINTRUST_API_KEY,
        default_headers={"x-bt-use-cache": "always" if settings.DEBUG else "never"},
    )
)
