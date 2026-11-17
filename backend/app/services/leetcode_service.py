import html
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("leetcode_service")

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://leetcode.com/",
}


def clean_leetcode_html(raw_html: str) -> str:
    """Converts LeetCode problem HTML description to clean formatted Markdown text."""
    if not raw_html:
        return ""
    text = raw_html

    # Replace <pre> blocks with code fences
    text = re.sub(r"<pre>\s*", "\n```\n", text)
    text = re.sub(r"\s*</pre>", "\n```\n", text)

    # Inline code <code>...</code> -> `...`
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)

    # Bold and strong
    text = re.sub(r"<(?:strong|b)>(.*?)</(?:strong|b)>", r"**\1**", text, flags=re.DOTALL)

    # Italics
    text = re.sub(r"<(?:em|i)>(.*?)</(?:em|i)>", r"*\1*", text, flags=re.DOTALL)

    # List items
    text = re.sub(r"<li>\s*", "- ", text)
    text = re.sub(r"\s*</li>", "\n", text)

    # Paragraphs
    text = re.sub(r"<p>\s*", "\n", text)
    text = re.sub(r"\s*</p>", "\n", text)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Unescape HTML entities
    text = html.unescape(text)

    # Consolidate consecutive empty lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


class LeetCodeService:
    def __init__(self, base_url: str = LEETCODE_GRAPHQL_URL, timeout: float = 12.0):
        self.base_url = base_url
        self.timeout = timeout

    async def fetch_problem(self, id_or_slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetches problem details from LeetCode GraphQL using either:
        - Frontend question ID / number (e.g. '1', '42')
        - Title slug (e.g. 'two-sum', 'trapping-rain-water')
        """
        query_val = id_or_slug.strip().lower()
        if not query_val:
            return None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            title_slug = query_val

            # Step 1: If numeric ID, query problemsetQuestionList to resolve to titleSlug
            if query_val.isdigit():
                title_slug = await self._resolve_id_to_slug(client, query_val)
                if not title_slug:
                    logger.warning(f"Could not resolve problem number '{query_val}' to title slug on LeetCode.")
                    return None

            # Step 2: Query questionData using titleSlug
            return await self._fetch_question_data(client, title_slug)

    async def _resolve_id_to_slug(self, client: httpx.AsyncClient, question_id: str) -> Optional[str]:
        search_query = """
        query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
          problemsetQuestionList: questionList(
            categorySlug: $categorySlug
            limit: $limit
            skip: $skip
            filters: $filters
          ) {
            questions: data {
              frontendQuestionId: questionFrontendId
              title
              titleSlug
            }
          }
        }
        """
        payload = {
            "query": search_query,
            "variables": {
                "categorySlug": "",
                "skip": 0,
                "limit": 10,
                "filters": {"searchKeywords": question_id},
            },
            "operationName": "problemsetQuestionList",
        }
        try:
            resp = await client.post(self.base_url, json=payload, headers=DEFAULT_HEADERS)
            if resp.status_code != 200:
                logger.warning(f"LeetCode problem list query returned HTTP {resp.status_code}")
                return None
            data = resp.json()
            questions = data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])
            # Prioritize exact match on frontendQuestionId
            matched = next((q for q in questions if str(q.get("frontendQuestionId")) == question_id), None)
            if not matched and questions:
                # If exact string didn't match, check if first question has the ID
                matched = questions[0]
            if matched and matched.get("titleSlug"):
                return matched["titleSlug"]
            return None
        except Exception as e:
            logger.warning(f"Failed to query LeetCode problem list: {e}")
            return None

    async def _fetch_question_data(self, client: httpx.AsyncClient, title_slug: str) -> Optional[Dict[str, Any]]:
        detail_query = """
        query questionData($titleSlug: String!) {
          question(titleSlug: $titleSlug) {
            questionId
            questionFrontendId
            title
            titleSlug
            content
            difficulty
            isPaidOnly
            topicTags {
              name
              slug
            }
            codeSnippets {
              lang
              langSlug
              code
            }
          }
        }
        """
        payload = {
            "query": detail_query,
            "variables": {"titleSlug": title_slug},
            "operationName": "questionData",
        }
        try:
            resp = await client.post(self.base_url, json=payload, headers=DEFAULT_HEADERS)
            if resp.status_code != 200:
                logger.warning(f"LeetCode question detail query returned HTTP {resp.status_code}")
                return None
            data = resp.json()
            q = data.get("data", {}).get("question")
            if not q:
                return None

            raw_content = q.get("content") or ""
            clean_content = clean_leetcode_html(raw_content)

            starter_code = {}
            for snippet in q.get("codeSnippets") or []:
                slug = snippet.get("langSlug")
                code = snippet.get("code")
                if slug == "python3":
                    starter_code["python"] = code
                elif slug == "java":
                    starter_code["java"] = code
                elif slug == "cpp":
                    starter_code["cpp"] = code

            return {
                "id": str(q.get("questionFrontendId") or ""),
                "title": q.get("title") or "",
                "title_slug": q.get("titleSlug") or "",
                "difficulty": (q.get("difficulty") or "Medium").lower(),
                "is_paid_only": bool(q.get("isPaidOnly")),
                "content": clean_content,
                "content_raw": raw_content,
                "topic_tags": [t.get("name") for t in (q.get("topicTags") or []) if t.get("name")],
                "starter_code": starter_code,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch LeetCode question data for '{title_slug}': {e}")
            return None


leetcode_service = LeetCodeService()
