# GPTS Registry

## 深度研究员

- role: Fill external factual evidence.
- when_to_use: Product fundamentals, founder quotes, competitors, user feedback, market signals.
- output_requirements: Evidence levels A/B/C/X, source links, uncertainty notes.
- evidence_requirements: Prefer primary sources and dated references.
- ingestion_rule: Must be reviewed, converted to patch draft, then ingested before becoming SK state.
- limitations: External research is not current SK state.

## 写作工坊

- role: Draft and revise public-facing articles.
- when_to_use: Structure, voice, clarity, title, narrative refinement.
- output_requirements: Draft text, revision rationale, unresolved claims.
- evidence_requirements: Mark claims that need SK or external evidence.
- ingestion_rule: Article output is candidate material until reviewed and stored in SK.
- limitations: Cannot decide publication state.

## 第一读者

- role: Read as a critical first audience.
- when_to_use: Clarity check, reader confusion, weak argument detection.
- output_requirements: Reader objections, confusing passages, suggested fixes.
- evidence_requirements: Point to exact passages.
- ingestion_rule: Feedback may become SOP or revision notes after review.
- limitations: Feedback is subjective and not SK state.

## 产品初拆 GPTS

- role: Produce first-pass product teardown material.
- when_to_use: Early product scan before sk-agent intake.
- output_requirements: Product summary, user, scenario, evidence, uncertainty, suggested SK path.
- evidence_requirements: Separate facts from assumptions.
- ingestion_rule: Must go through sk-agent duplicate check and patch draft before ingestion.
- limitations: Does not update SK status.
