import os
import json
import anthropic

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def clean_stanzas(stanzas: list[dict], title: str = "") -> list[dict]:
    """
    Use Claude to clean and organize raw scraped song/hymn stanzas.
    Returns a list of stanzas in the format: [{"number": N, "lines": [...]}]
    Falls back to the original stanzas if the API call fails or key is not set.
    """
    try:
        client = _get_client()
    except RuntimeError:
        return stanzas

    raw_json = json.dumps(stanzas, indent=2)
    prompt = f"""You are cleaning up song/hymn lyrics that were scraped from the web.
The song title is: "{title}"

Here are the raw scraped stanzas (JSON):
{raw_json}

Please clean and organize them:
- Remove any web artifacts, navigation text, copyright notices, or non-lyric content
- Fix line breaks so each line is a single meaningful lyric line
- Correctly identify and label each section as one of: "verse", "chorus", "refrain", or "bridge"
- A chorus or refrain that repeats should appear ONCE in the output with type "chorus" or "refrain"
- Verses are numbered sequentially (1, 2, 3…); chorus/refrain/bridge use their own counter starting at 1
- Remove duplicate stanzas (same lines appearing more than once)
- Each stanza should have 2–6 lines

Return ONLY a JSON array with this exact schema, no explanation:
[{{"number": 1, "type": "verse", "lines": ["line 1", "line 2", "..."]}}]

Where "type" is one of: "verse", "chorus", "refrain", "bridge"."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract the text block (skip thinking blocks)
    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text.strip()
            break

    # Parse the JSON response
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        return stanzas

    cleaned = json.loads(text[start:end])
    if not isinstance(cleaned, list) or not cleaned:
        return stanzas

    return cleaned
