# CMS Risk Adjustment & GAP Suspecting

This document summarizes the purpose and high-level requirements for a CMS Risk
Adjustment and Diagnosis GAP Suspecting application.

## Purpose

- Explain CMS Risk Adjustment (RAF) calculations and data inputs.
- Describe Diagnosis GAP Suspecting to identify missing or undocumented chronic
	conditions that could impact risk scores and revenue.

## 1. CMS Risk Adjustment (RAF) — Overview

CMS Risk Adjustment ensures health plans are fairly compensated for the risk
profile of their enrolled members. It adjusts payments based on member health
status and demographics, and it drives capitation payments for Medicare
Advantage and ACA plans.

### Why it matters

- Fair reimbursement for plans serving higher-risk members
- Encourages accurate clinical documentation and coding
- Supports value-based care by aligning payments with expected costs

### How it works (high level)

1. Ingest claims and encounter data
2. Extract diagnosis codes from clinical records
3. Map diagnoses to Hierarchical Condition Categories (HCCs)
4. Apply HCC weights and model variables to compute a RAF score
5. Output RAF per member for capitation/payment calculations

### Data inputs

- Claims/encounter records (diagnosis codes, procedure codes, dates)
- Member demographics (DOB, gender, plan type)
- Enrollment records
- Reference tables (ICD→HCC mapping, HCC weights, exclusion rules)

### Data outputs

- RAF score per member
- HCC mappings per diagnosis code
- RAF calculation breakdown (variables and weights)

## 2. GAP Suspecting — Overview

Diagnosis GAP Suspecting finds conditions that were documented in prior years
but are missing from the current reporting period. The goal is to surface gaps
that, if confirmed, would increase RAF scores and recover revenue.

### Key processes

- Compare historical diagnoses with current-year claims and encounters
- Apply configurable suspecting rules to flag likely missing conditions
- Generate prioritized CHASE suspect lists for provider/chart review
- Integrate with provider outreach and chart retrieval workflows

### Data inputs

- Current-year claims and encounters
- Prior-year diagnoses and claims
- Enrollment history (to check continuity)
- Provider and member contact information

### Data outputs

- Prioritized GAP suspect lists (CHASE) for outreach
- Gap details and clinical rationale
- Outreach/review assignments and status tracking

## 3. Core Functional Requirements (Summary)

### CMS Risk Adjustment Module

- Ingest and normalize claims data from professional, facility and pharmacy
	sources
- Extract diagnosis codes and deduplicate per member
- Map ICD codes to HCCs using method metadata and ref tables
- Apply age/gender/exclusion rules and hierarchy logic
- Select appropriate risk model and variables
- Calculate RAF as the sum of weighted variables and demographic factors
- Persist RAF, HCC details, and calculation breakdown for audit

### GAP Suspecting Module

- Identify members with continuous enrollment across comparison periods
- Map prior-year diagnoses to HCCs and compare against current-year HCCs
- Create gap candidates for HCCs present historically but missing currently
- Score/prioritize gaps using impact, recency, age-appropriateness,
	and comorbidity signals
- Assign provider(s) and generate CHASE records for chart review/outreach
- Track outreach status and measure capture/closure rates

## 4. Business Value & Use Cases

- Revenue optimization — capture all eligible diagnoses to avoid underpayment
- Compliance and audit readiness — preserve transparent RAF calculations
- Population health — identify high-risk members for care management
- Operational efficiency — prioritize chart reviews and provider outreach

## 5. Next steps / Implementation suggestions

- Build ingestion pipelines to load stage tables (pipe-delimited sources)
- Implement HCC mapping and rule engine (SQL/Spark with reference tables)
- Implement RAF calculation engine (variable selection, interactions, sums)
- Implement GAP detection and prioritization pipeline (CHASE outputs)
- Provide dashboards & APIs for outreach teams and reporting

---

If you'd like, I can now:

1. Generate database table schemas or ETL SQL (Spark/Databricks) for staging
	 and transform layers.
2. Implement a reference HCC mapping and a small RAF calculation prototype
	 (Python/PySpark).
3. Build the GAP suspect scoring function and sample CHASE export.

Tell me which step you want to tackle first and I will implement it.