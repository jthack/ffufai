# ffufai Roadmap

This roadmap maps the major capability areas and how they build on each other.

## Phase 1: Accuracy & Signal
- Multi-phase AI inference (plan → generate → verify) for extensions and wordlists.
- Technology fingerprinting from headers + HTML + cookies to improve context.
- Wappalyzer-style signatures and config-driven tech mappings.
- Tech-aware wordlist catalog selection and recon-driven list generation.
- Profiles/goals to bias toward critical targets and reduce noise.

## Phase 2: Performance & Scale
- Caching of AI results for repeated scans.
- Auto-mode selection to choose wordlist vs extension fuzzing.
- Targets file support for batch runs.

## Phase 3: Intelligence & Refinement
- Consensus mode across Gemini, OpenAI, Anthropic, Groq, and OpenRouter.
- Feedback loop using ffuf JSON results to refine wordlists.
- Adaptive category-driven wordlist switching.
- Concise attack-plan reporting to guide follow-up actions.
- DNS/TLS and error-page enrichment signals.

## Phase 4: Expansion
- Expand tech knowledge base and platform indicators.
- Add more profiles (e.g., API-only, SPA) and goals.
- Add persistence for successful findings and active learning.
- Cross-target learning with global knowledge base.
- Add provider rotation and multi-key management.
