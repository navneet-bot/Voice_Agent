"""Conservative structured extraction for crawled website pages."""

from __future__ import annotations

import re
from collections import Counter
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from .crawler import CrawledPage


_INDUSTRY_KEYWORDS = {
    "real_estate": ("property", "real estate", "apartment", "villa", "plot", "home loan"),
    "finance": ("loan", "investment", "wealth", "mutual fund", "insurance", "credit"),
    "insurance": ("insurance", "policy", "premium", "claim", "coverage"),
    "healthcare": ("clinic", "doctor", "patient", "treatment", "diagnostic"),
    "education": ("course", "admission", "student", "training", "school"),
    "saas": ("software", "platform", "automation", "dashboard", "api"),
}

_PAGE_TYPE_KEYWORDS = {
    "services": ("service", "services", "solution", "solutions", "product", "products", "property", "course"),
    "faq": ("faq", "frequently asked", "question", "questions"),
    "pricing": ("pricing", "price", "cost", "fees", "plans"),
    "contact": ("contact", "enquiry", "enquire", "callback", "book", "schedule", "demo"),
    "about": ("about", "company", "team", "mission"),
    "blog": ("blog", "article", "news", "insight", "insights"),
    "legal": ("privacy", "terms", "refund", "cookie"),
    "careers": ("career", "jobs", "hiring"),
}

_NOISE_EXACT_TEXT = {
    "home",
    "login",
    "sign in",
    "sign up",
    "privacy policy",
    "terms and conditions",
    "all rights reserved",
}


class _PageTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.meta_description = ""
        self.headings: list[str] = []
        self.text_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self._tag_stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag == "meta":
            attr_map = {name.lower(): value for name, value in attrs if value}
            if attr_map.get("name", "").lower() == "description":
                self.meta_description = _clean_text(attr_map.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = _clean_text(data)
        if not text:
            return
        current = self._tag_stack[-1] if self._tag_stack else ""
        if current != "title" and _is_noise_text(text):
            return
        if current == "title":
            self.title_parts.append(text)
        elif current in {"h1", "h2", "h3"}:
            self.headings.append(text)
            self.text_parts.append(text)
        elif current in {"p", "li", "span", "div", "strong", "em"}:
            self.text_parts.append(text)


def extract_website_knowledge(
    pages: list[CrawledPage],
    *,
    source_url: str,
    domain: str,
    industry_hint: str | None = None,
) -> dict[str, Any]:
    parsed_pages = [_parse_page(page) for page in pages]
    combined_text = " ".join(page["text"] for page in parsed_pages)
    industry = industry_hint or _infer_industry(combined_text)
    title = next((page["title"] for page in parsed_pages if page["title"]), domain)

    products = _extract_products_or_services(parsed_pages)
    faqs = _extract_faqs(parsed_pages)
    value_props = _extract_value_props(parsed_pages)

    knowledge = {
        "source_url": source_url,
        "domain": domain,
        "industry": industry,
        "company": {"name": _company_name_from_title(title, domain), "evidence": [source_url]},
        "pages_crawled": [
            {
                "url": page["url"],
                "title": page["title"],
                "description": page["description"],
                "headings": page["headings"][:12],
                "page_type": page["page_type"],
                "signals": page["signals"],
            }
            for page in parsed_pages
        ],
        "content_inventory": _build_content_inventory(parsed_pages),
        "products_or_services": products,
        "value_propositions": value_props,
        "qualification_questions": _qualification_questions_for(industry, products),
        "objections": _objections_for(industry),
        "faqs": faqs,
        "limitations": [
            "Only public website content fetched within configured crawl limits was used.",
            "Human review is required before publishing any generated workflow.",
        ],
    }
    knowledge["quality"] = assess_website_knowledge(knowledge)
    return knowledge


def assess_website_knowledge(knowledge: dict[str, Any]) -> dict[str, Any]:
    """Return advisory-only readiness signals for generated script review."""
    domain = _clean_text(knowledge.get("domain", ""))
    company_name = _clean_text((knowledge.get("company") or {}).get("name", ""))
    products = knowledge.get("products_or_services") or []
    value_props = knowledge.get("value_propositions") or []
    questions = knowledge.get("qualification_questions") or []
    pages = knowledge.get("pages_crawled") or []
    industry = _clean_text(knowledge.get("industry", "unknown")).lower()

    checks = [
        {
            "key": "pages_crawled",
            "passed": bool(pages),
            "weight": 20,
            "message": "At least one public page was crawled.",
        },
        {
            "key": "company_identified",
            "passed": bool(company_name) and company_name.lower() != domain.lower(),
            "weight": 15,
            "message": "Business name was identified from website content.",
        },
        {
            "key": "offering_detected",
            "passed": bool(products),
            "weight": 20,
            "message": "Products or services were detected.",
        },
        {
            "key": "value_points_detected",
            "passed": bool(value_props),
            "weight": 15,
            "message": "Website-backed value points were detected.",
        },
        {
            "key": "qualification_ready",
            "passed": bool(questions),
            "weight": 10,
            "message": "Qualification questions are available for the generated flow.",
        },
        {
            "key": "industry_detected",
            "passed": bool(industry and industry != "unknown"),
            "weight": 10,
            "message": "Industry was detected or provided.",
        },
        {
            "key": "evidence_present",
            "passed": _has_evidence(knowledge),
            "weight": 10,
            "message": "Extracted claims include source evidence URLs.",
        },
    ]
    score = sum(item["weight"] for item in checks if item["passed"])
    if score >= 75:
        level = "high"
    elif score >= 50:
        level = "medium"
    elif score >= 25:
        level = "low"
    else:
        level = "insufficient"
    warnings = [item["message"] for item in checks if not item["passed"]]
    return {
        "score": score,
        "level": level,
        "ready_for_review": score >= 50,
        "advisory_only": True,
        "warnings": warnings,
        "checks": checks,
    }


def _parse_page(page: CrawledPage) -> dict[str, Any]:
    parser = _PageTextExtractor()
    if "html" in page.content_type.lower():
        try:
            parser.feed(page.body or "")
        except Exception:
            pass
    else:
        parser.text_parts.append(_clean_text(page.body))

    title = _clean_text(" ".join(parser.title_parts))
    description = parser.meta_description
    text = _clean_text(" ".join(parser.text_parts))
    parsed = {
        "url": page.url,
        "title": title,
        "description": description,
        "headings": _unique(parser.headings),
        "text": text[:20_000],
    }
    parsed["page_type"] = _classify_page(parsed)
    parsed["signals"] = _page_signals(parsed)
    return parsed


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _is_noise_text(value: str) -> bool:
    clean = _clean_text(value).lower()
    if clean in _NOISE_EXACT_TEXT:
        return True
    return any(phrase in clean for phrase in ("accept cookies", "cookie settings", "subscribe to our newsletter"))


def _has_evidence(knowledge: dict[str, Any]) -> bool:
    groups = [
        [knowledge.get("company") or {}],
        knowledge.get("products_or_services") or [],
        knowledge.get("value_propositions") or [],
        knowledge.get("faqs") or [],
    ]
    for group in groups:
        for item in group:
            if item.get("evidence"):
                return True
    return False


def _unique(values: list[str], limit: int = 30) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = _clean_text(value)
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
        if len(result) >= limit:
            break
    return result


def _classify_page(page: dict[str, Any]) -> str:
    parsed = urlparse(page.get("url", ""))
    path = parsed.path.lower().strip("/")
    blob = " ".join([
        path,
        page.get("title", ""),
        page.get("description", ""),
        " ".join(page.get("headings") or []),
    ]).lower()
    if not path and not blob.strip():
        return "home"
    scores = {
        page_type: sum(1 for keyword in keywords if keyword in blob)
        for page_type, keywords in _PAGE_TYPE_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return "home" if not path else "general"


def _page_signals(page: dict[str, Any]) -> list[str]:
    text = " ".join([
        page.get("description", ""),
        " ".join(page.get("headings") or []),
        page.get("text", "")[:2000],
    ]).lower()
    signals: list[str] = []
    if "?" in text or "faq" in text:
        signals.append("questions")
    if any(word in text for word in ("price", "pricing", "cost", "budget", "fees")):
        signals.append("pricing")
    if any(word in text for word in ("contact", "callback", "book", "schedule", "call us")):
        signals.append("contact")
    if any(word in text for word in ("trusted", "expert", "personalized", "secure", "transparent")):
        signals.append("value_proposition")
    return _unique(signals, limit=6)


def _build_content_inventory(pages: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(page.get("page_type", "general") for page in pages)
    primary_types = {"home", "services", "faq", "pricing", "contact", "about", "general"}
    primary_pages = [
        {
            "url": page["url"],
            "title": page["title"],
            "page_type": page.get("page_type", "general"),
            "signals": page.get("signals", []),
        }
        for page in pages
        if page.get("page_type", "general") in primary_types
    ][:10]
    return {
        "page_types": dict(counts),
        "primary_pages": primary_pages,
        "has_services": bool(counts.get("services")),
        "has_faq": bool(counts.get("faq")),
        "has_contact": bool(counts.get("contact")),
        "noise_filtered": True,
    }


def _infer_industry(text: str) -> str:
    lower = text.lower()
    scores = {
        industry: sum(1 for keyword in keywords if keyword in lower)
        for industry, keywords in _INDUSTRY_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def _company_name_from_title(title: str, domain: str) -> str:
    clean = _clean_text(title)
    if not clean:
        return domain
    return re.split(r"\s[-|]\s", clean, maxsplit=1)[0][:120] or domain


def _extract_products_or_services(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for page in pages:
        headings = page["headings"] or []
        if not headings and page.get("page_type") == "services" and page.get("title"):
            headings = [page["title"]]
        for heading in headings:
            lower = heading.lower()
            if page.get("page_type") == "services" or any(word in lower for word in ("service", "solution", "product", "plan", "property", "course")):
                candidates.append({"name": heading[:120], "evidence": [page["url"]]})
    return _dedupe_named_items(candidates)[:8]


def _extract_value_props(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    patterns = ("trusted", "fast", "secure", "expert", "personalized", "affordable", "transparent")
    for page in pages:
        sentences = re.split(r"(?<=[.!?])\s+", page["text"])
        for sentence in sentences:
            clean = _clean_text(sentence)
            if 30 <= len(clean) <= 180 and any(word in clean.lower() for word in patterns):
                candidates.append({"text": clean, "evidence": [page["url"]]})
                break
    return candidates[:6]


def _extract_faqs(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    faqs: list[dict[str, Any]] = []
    for page in pages:
        for heading in page["headings"]:
            if heading.endswith("?"):
                faqs.append({"question": heading[:180], "answer": "", "evidence": [page["url"]]})
    return faqs[:8]


def _qualification_questions_for(industry: str, products: list[dict[str, Any]]) -> list[str]:
    if industry == "real_estate":
        return ["What budget range are you considering?", "Which city or area are you interested in?"]
    if industry in {"finance", "insurance"}:
        return ["What goal are you planning for?", "What monthly budget are you comfortable with?"]
    if products:
        return ["Which service are you most interested in?", "When are you planning to make a decision?"]
    return ["What are you looking for right now?", "What timeline should we keep in mind?"]


def _objections_for(industry: str) -> list[dict[str, str]]:
    common = [
        {"intent": "price_concern", "guidance": "Acknowledge budget concern and offer to match options to their range."},
        {"intent": "needs_time", "guidance": "Offer a short follow-up slot instead of pressuring the caller."},
    ]
    if industry == "real_estate":
        common.append({"intent": "location_unclear", "guidance": "Ask for preferred city, commute, or investment goal."})
    return common


def _dedupe_named_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        name = _clean_text(item.get("name", ""))
        key = name.lower()
        if name and key not in seen:
            seen.add(key)
            result.append({"name": name, "evidence": item.get("evidence", [])})
    return result
