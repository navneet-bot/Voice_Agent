"""Async-safe scaffolding for website intelligence jobs.

Live crawling remains opt-in. With scrape.worker_v1 disabled, the pipeline keeps
the original placeholder behavior. With the flag enabled by the API layer, the
pipeline runs a bounded crawler, stores page snapshot metadata, and generates
review-only FlowSpec drafts from extracted public website facts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .crawler import CrawlError, WebsiteCrawler
from .extraction import assess_website_knowledge, extract_website_knowledge
from .script_generation import build_structured_knowledge_stub, generate_draft_flow_from_knowledge
from .url_guard import SafeURL, validate_public_http_url


logger = logging.getLogger("intelligence.pipeline")


@dataclass(frozen=True)
class ScrapeLimits:
    max_pages: int = 20
    max_bytes: int = 2_000_000
    timeout_s: int = 30


class WebsiteIntelligencePipeline:
    def __init__(self, db, crawler: WebsiteCrawler | None = None):
        self.db = db
        self.crawler = crawler or WebsiteCrawler()

    async def create_job(
        self,
        *,
        client_id: str | None,
        agent_id: str | None,
        url: str,
        requested_by: str | None = None,
        limits: ScrapeLimits | None = None,
        reuse_existing: bool = True,
    ) -> dict:
        safe = validate_public_http_url(url, resolve_dns=False)
        if reuse_existing:
            existing = await self.db.get_reusable_scrape_job(
                client_id=client_id,
                agent_id=agent_id,
                url=safe.normalized_url,
            )
            if existing:
                existing["cache"] = {"reused": True, "reason": "same_agent_url"}
                logger.info("[INTEL] reused scrape job=%s domain=%s", existing.get("id"), safe.domain)
                return existing
        cfg = limits or ScrapeLimits()
        job = await self.db.create_scrape_job(
            client_id=client_id,
            agent_id=agent_id,
            url=safe.normalized_url,
            domain=safe.domain,
            requested_by=requested_by,
            limits={
                "max_pages": cfg.max_pages,
                "max_bytes": cfg.max_bytes,
                "timeout_s": cfg.timeout_s,
            },
        )
        job["cache"] = {"reused": False}
        logger.info("[INTEL] created scrape job=%s domain=%s", job.get("id"), safe.domain)
        return job

    async def create_draft_from_job(
        self,
        *,
        job_id: str,
        agent: dict,
        industry_hint: str | None = None,
        use_live_extraction: bool = False,
    ) -> dict:
        job = await self.db.get_scrape_job(job_id)
        if not job:
            raise ValueError(f"scrape job not found: {job_id}")
        knowledge = None
        if use_live_extraction:
            latest = await self.db.get_latest_scrape_extraction(job_id)
            knowledge = latest["extraction"] if latest else None
            if not knowledge:
                run_result = await self.run_job(job_id=job_id, industry_hint=industry_hint or agent.get("agent_type"))
                knowledge = run_result.get("knowledge")
                if not knowledge:
                    status = run_result.get("status") or job.get("status") or "unknown"
                    if status in {"already_running", "running", "dispatching"}:
                        raise CrawlError("Scrape job is still running. Please wait for completion before creating a draft.")
                    raise CrawlError(f"Scrape extraction is not ready yet. Current status: {status}.")
        if not knowledge:
            safe = SafeURL(
                url=job["url"],
                normalized_url=job["url"],
                domain=job["domain"],
                scheme=job["url"].split(":", 1)[0],
            )
            knowledge = build_structured_knowledge_stub(
                url=safe.normalized_url,
                domain=safe.domain,
                industry_hint=industry_hint or agent.get("agent_type"),
            )
            await self.db.save_scrape_extraction(job_id, knowledge)
        if "quality" not in knowledge:
            knowledge["quality"] = assess_website_knowledge(knowledge)
        flow = generate_draft_flow_from_knowledge(
            agent_id=agent["id"],
            agent_name=agent.get("name") or "Voice Agent",
            agent_type=agent.get("agent_type") or "real_estate_sales",
            script=agent.get("script") or "",
            data_fields=agent.get("data_fields") or [],
            knowledge=knowledge,
        )
        draft = await self.db.create_generated_script_draft(
            job_id=job_id,
            client_id=job.get("client_id"),
            agent_id=agent["id"],
            status="draft",
            draft_json=flow,
            knowledge_json=knowledge,
        )
        await self.db.update_scrape_job_status(job_id, "draft_ready")
        return draft

    async def run_job(self, *, job_id: str, industry_hint: str | None = None) -> dict:
        job = await self.db.get_scrape_job(job_id)
        if not job:
            raise ValueError(f"scrape job not found: {job_id}")
        if job.get("status") == "cancelled":
            return {"job_id": job_id, "status": "cancelled", "cancelled": True}
        if job.get("status") in {"completed", "draft_ready"}:
            return {"job_id": job_id, "status": job.get("status"), "skipped": True}
        limits = job.get("limits") or {}
        started_job = await self.db.mark_scrape_job_running(job_id)
        if started_job and started_job.get("status") == "cancelled":
            return {"job_id": job_id, "status": "cancelled", "cancelled": True}
        if not started_job:
            raise ValueError(f"scrape job not found: {job_id}")
        if not started_job.get("_started"):
            status = started_job.get("status") or "unknown"
            return {
                "job_id": job_id,
                "status": "already_running" if status == "running" else status,
                "skipped": True,
            }

        try:
            pages = await self.crawler.crawl(
                job["url"],
                max_pages=int(limits.get("max_pages") or ScrapeLimits.max_pages),
                max_bytes=int(limits.get("max_bytes") or ScrapeLimits.max_bytes),
                timeout_s=int(limits.get("timeout_s") or ScrapeLimits.timeout_s),
            )
            if await self._is_cancelled(job_id):
                return {"job_id": job_id, "status": "cancelled", "cancelled": True}
            for page in pages:
                if await self._is_cancelled(job_id):
                    return {"job_id": job_id, "status": "cancelled", "cancelled": True}
                await self.db.save_page_snapshot(
                    job_id=job_id,
                    url=page.url,
                    content_hash=page.content_hash,
                    content_type=page.content_type,
                    storage_path=None,
                )
            if await self._is_cancelled(job_id):
                return {"job_id": job_id, "status": "cancelled", "cancelled": True}
            knowledge = extract_website_knowledge(
                pages,
                source_url=job["url"],
                domain=job["domain"],
                industry_hint=industry_hint,
            )
            if await self._is_cancelled(job_id):
                return {"job_id": job_id, "status": "cancelled", "cancelled": True}
            extraction = await self.db.save_scrape_extraction(job_id, knowledge)
            if await self._is_cancelled(job_id):
                return {"job_id": job_id, "status": "cancelled", "cancelled": True}
            await self.db.update_scrape_job_status(job_id, "completed")
            return {
                "job_id": job_id,
                "status": "completed",
                "pages_crawled": len(pages),
                "extraction_id": extraction["id"],
                "knowledge": knowledge,
            }
        except CrawlError as exc:
            if await self._is_cancelled(job_id):
                return {"job_id": job_id, "status": "cancelled", "cancelled": True}
            await self.db.update_scrape_job_status(job_id, "failed", error=str(exc))
            raise
        except Exception as exc:
            if await self._is_cancelled(job_id):
                return {"job_id": job_id, "status": "cancelled", "cancelled": True}
            await self.db.update_scrape_job_status(job_id, "failed", error=type(exc).__name__)
            raise

    async def _is_cancelled(self, job_id: str) -> bool:
        current = await self.db.get_scrape_job(job_id)
        return bool(current and current.get("status") == "cancelled")
