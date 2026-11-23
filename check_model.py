import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

model = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    extra_body={"thinking": {"type": "disabled"}},
)

response = model.invoke("你好，只回复 OK")

print(type(response))
print(response.content)
print(response.usage_metadata)
