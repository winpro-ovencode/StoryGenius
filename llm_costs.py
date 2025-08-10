import os
import math

# 간단한 문자수→토큰 근사치. 필요 시 환경변수로 조정
CHARS_PER_TOKEN = 3
try:
    CHARS_PER_TOKEN = int(os.environ.get("CHARS_PER_TOKEN", "3"))
except ValueError:
    CHARS_PER_TOKEN = 3


def estimate_tokens_from_text(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / max(1, CHARS_PER_TOKEN)))


def estimate_tokens_from_messages(messages) -> int:
    if not messages:
        return 0
    contents = []
    for m in messages:
        c = m.get("content", "")
        if isinstance(c, str):
            contents.append(c)
    return estimate_tokens_from_text("\n".join(contents))


def _get_rate(env_key: str, default_value: float) -> float:
    try:
        return float(os.environ.get(env_key, str(default_value)))
    except ValueError:
        return default_value


# 모델별 1K 토큰당 비용(USD). 환경변수로 오버라이드 가능
DEFAULT_RATES = {
    # 합리적인 기본값(예: gpt-4o 기준). 실제와 다를 수 있으므로 필요 시 ENV로 조정
    "gpt-4o": {
        "prompt_per_1k": _get_rate("G4O_PROMPT_PER_1K", 0.005),
        "completion_per_1k": _get_rate("G4O_COMPLETION_PER_1K", 0.015),
    },
    # 프로젝트 기본 모델로 사용 중. ENV로 손쉽게 세팅 가능
    "gpt-5": {
        "prompt_per_1k": _get_rate("GPT5_PROMPT_PER_1K", 0.005),
        "completion_per_1k": _get_rate("GPT5_COMPLETION_PER_1K", 0.015),
    },
}

# 임베딩 모델(입력만 과금) 1K 토큰당 비용
EMBED_RATES = {
    "text-embedding-3-small": _get_rate("EMBED_TEXT_EMBEDDING_3_SMALL_PER_1K", 0.00002),
}


def estimate_chat_cost(model: str, prompt_tokens: int, completion_tokens: int):
    rates = DEFAULT_RATES.get(model) or DEFAULT_RATES.get("gpt-4o")
    prompt_rate = float(rates["prompt_per_1k"]) if rates else 0.0
    completion_rate = float(rates["completion_per_1k"]) if rates else 0.0

    prompt_cost = (prompt_tokens / 1000.0) * prompt_rate
    completion_cost = (completion_tokens / 1000.0) * completion_rate
    total_cost = prompt_cost + completion_cost
    return {
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost,
        "total_cost": total_cost,
    }


def estimate_embedding_cost(model: str, tokens: int) -> float:
    rate = float(EMBED_RATES.get(model, 0.0))
    return (tokens / 1000.0) * rate


def should_show_cost_info() -> bool:
    return os.environ.get("SHOW_COST_INFO", "1") == "1"


