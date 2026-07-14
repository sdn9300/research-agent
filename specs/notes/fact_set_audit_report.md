# Fact Set Audit Report

Date: 2026-07-01
Dataset: research_agent_fact_set_v1
Result: FROZEN_VERIFIED

## Audit Scope

This report records a manual source-by-source review of `eval/fact_set.json`.
The initial scaffold was tightened so that each fact now maps to a checked live source page.

## Source Standard

- Primary target: official company pages
- Allowed exception: one secondary-source fallback when an official page could not be reliably accessed through the available browsing tools
- Outcome: 15 companies audited against official pages, 1 company (`Figma`) retained with a documented secondary-source exception

## Company Review

- Google: verified against About Google company info, story, and locations pages
- Microsoft: verified against the official Microsoft facts page
- Apple: revised away from weak founding/HQ claims to stronger product, services, and retail claims supported by Apple pages
- Amazon: revised to mission, business lines, and CEO facts supported by About Amazon
- NVIDIA: revised to accelerated computing, AI systems, RTX, and Omniverse claims supported by NVIDIA's About page
- Salesforce: verified and tightened around 1999 origin, CRM positioning, and SaaS history
- Adobe: verified against Adobe history and company overview sections
- Shopify: revised to commerce-platform capabilities directly stated on Shopify's About page
- Databricks: verified against Databricks About Us page
- Figma: retained with secondary-source exception due official-page access limitations in the available tooling during audit
- Notion: verified against Notion About page
- Vercel: revised to company-positioning and tooling facts directly stated on Vercel's About page
- Anthropic: revised to company type, safety focus, and governance/product facts supported by Anthropic's Company page
- PostHog: verified against PostHog About page and revised to launch/toolkit/open-source claims
- Linear: verified against Linear About page
- Langfuse: verified against Langfuse About page and revised to origin, product, and office-footprint claims

## Final Assessment

The fact set is now substantially stronger for Gate 1 use than the initial scaffold.
The remaining caveat is the single Figma secondary-source exception. If you want a strict official-only dataset later, replace Figma with another company whose official about/investor pages are easily accessible in the toolchain.
