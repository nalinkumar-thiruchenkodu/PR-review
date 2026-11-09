"""Demo 1: send a PR diff to an LLM (GitHub Models) and write review.md.
"""Testing the pr.

No third-party packages needed. Auth uses the workflow's GITHUB_TOKEN
(the workflow must grant `models: read`).
"""
import json
import os
import urllib.error
import urllib.request

API_URL = "https://models.github.ai/inference/chat/completions"
MODEL = os.getenv("REVIEW_MODEL", "openai/gpt-4o-mini")
MAX_DIFF_CHARS = 12000  # guardrail: keep the prompt small and cheap

SYSTEM_PROMPT = (
    "You are a senior engineer reviewing a pull request diff. "
    "Report real problems only: bugs, security issues, missing error handling, "
    "unclear logic. Skip pure style nitpicks. "
    "Reply in Markdown: a one-line summary, then at most 6 bullets in the form "
    "'**[High|Medium|Low]** file: issue - suggested fix'. "
    "If the change looks fine, say so in one line."
)


def read_diff() -> str:
    with open("pr.diff", encoding="utf-8", errors="replace") as f:
        diff = f.read()
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated]"
    return diff


def ask_llm(diff: str) -> str:
    payload = {
        "model": MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Review this diff:\n\n{diff}"},
        ],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]


def main() -> None:
    diff = read_diff()
    if not diff.strip():
        body = "No code changes to review."
    else:
        try:
            body = ask_llm(diff)
        except urllib.error.HTTPError as e:
            body = f"AI review unavailable (HTTP {e.code}). Please review manually."
        except Exception as e:  # keep the demo alive, never block the PR
            body = f"AI review unavailable ({type(e).__name__}). Please review manually."

    footer = "\n\n---\n_Automated review by an LLM. Advisory only; a human decides._"
    with open("review.md", "w", encoding="utf-8") as f:
        f.write("### AI Review\n\n" + body + footer)
    print(body)


if __name__ == "__main__":
    main()
