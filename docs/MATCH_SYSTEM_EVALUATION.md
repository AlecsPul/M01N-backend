# BexInsights Match System Evaluation

**Document Version:** 1.0  
**Date:** January 15, 2026  
**Purpose:** End-to-end analysis of the matching system for QA and validation purposes

---

## Table of Contents

1. [Algorithm Behavior](#1-algorithm-behavior)
2. [Match Endpoints Flow](#2-match-endpoints-flow)
3. [Database Signals Used](#3-database-signals-used)
4. [Failure Modes & Edge Cases](#4-failure-modes--edge-cases)
5. [Test Coverage Matrix](#5-test-coverage-matrix)
6. [Validation Thresholds](#6-validation-thresholds)

---

## 1. Algorithm Behavior

### 1.1 Input Structure

**Buyer Requirements (`buyer_struct`):**
```python
{
  "buyer_text": str,              # Natural language requirement
  "labels_must": List[str],       # Required functional categories (hard constraint)
  "labels_nice": List[str],       # Nice-to-have functional categories
  "tag_must": List[str],          # Required business context tags
  "tag_nice": List[str],          # Nice-to-have context tags
  "integration_required": List[str],  # Required integrations (hard constraint)
  "integration_nice": List[str],      # Nice-to-have integrations
  "constraints": {"price_max": float | None},  # Budget constraint
  "notes": str                    # Additional context
}
```

**Buyer Embedding:**
- 1536-dimensional float vector from OpenAI `text-embedding-3-small`
- Generated from composed final prompt text

### 1.2 Processing Pipeline

**Step 1: Vector Candidate Retrieval**
- Retrieves top K candidates (default: K=30) using cosine similarity
- Query: `ORDER BY embedding <=> buyer_embedding`
- Uses pgvector extension for efficient nearest neighbor search
- Returns: `app_search_id`, `app_id`, `price_text`, `cosine_similarity`

**Step 2: Batch Feature Fetching**
- Fetches labels from `application_labels`
- Fetches integration keys from `application_integration_keys`
- Fetches tags from `apps_tags` (uses `app_id`, not `app_search_id`)
- Fetches label synonyms from `labels` table for `labels_must` matching

**Step 3: Hard Constraint Filtering**

*Function: `check_must_have_requirements()`*

**Required Labels (`labels_must`):**
- All labels in `labels_must` must be present in app labels
- Supports synonym matching via `labels.synonyms` column
- Case-insensitive comparison
- **Failure behavior:** App assigned `similarity_percent = 5` (not completely discarded)

**Required Integrations (`integration_required`):**
- All integrations in `integration_required` must be present
- Normalized to Title Case for comparison
- Case-insensitive matching
- **Failure behavior:** App assigned `similarity_percent = 5`

**Price Constraint:**
- Extracted from `application.price_text` (formats: "CHF 50", "Gratis", "CHF 50/mes")
- If `price_max` specified: app price must be ≤ `price_max`
- Free indicators: "gratis", "free", "kostenlos", "gratuit" → price = 0.0
- Unparseable prices: optimistically included (returns `True`)
- **Failure behavior:** App assigned `similarity_percent = 5`

**Note on `tag_must`:**
- Currently **NOT** enforced as hard constraint
- Used in hybrid scoring with 10% weight
- **Assumption:** Design decision to avoid over-filtering

**Step 4: Hybrid Scoring**

*Function: `calculate_hybrid_score()`*

**Formula:**
```
hybrid_score = (
  0.60 * cosine_similarity +
  0.10 * tag_must_overlap +
  0.10 * labels_nice_overlap +
  0.05 * tag_nice_overlap +
  0.15 * integrations_nice_overlap
) * 0.45 + 0.55
```

**Overlap Calculation:**
- `overlap_ratio(buyer_list, app_list) = |intersection| / |buyer_list|`
- If `buyer_list` is empty: returns 0.1 (10% baseline)
- Case-insensitive string matching
- Integrations normalized to Title Case before comparison

**Scoring Weights Breakdown:**
- **60%** - Vector embedding similarity (semantic understanding)
- **10%** - Must-have tags overlap (business context alignment)
- **10%** - Nice-to-have labels (functional feature bonus)
- **5%** - Nice-to-have tags (additional context bonus)
- **15%** - Nice-to-have integrations (ecosystem compatibility)

**Note:** The formula includes a final transformation: `* 0.45 + 0.55`
- This shifts the score range significantly
- **Assumption:** This may be a calibration adjustment to center scores around 70-80%
- **Recommendation:** Verify if this is intentional or should be removed

### 1.3 Score to Percentage Mapping

*Function: `score_to_percentage()`*

**Sigmoid Transformation:**
```python
transformed = 1 / (1 + exp(-10 * (score - 0.5)))
percentage = round(100 * transformed)
```

**Behavior:**
- Input: hybrid score in [0, 1]
- Output: percentage in [0, 100]
- Sigmoid steepness: 10 (aggressive S-curve)
- Center point: 0.5 (50% score → ~50% percentage after sigmoid)

**Practical Ranges** (approximate):
- Score 0.3 → ~5% (sigmoid floor)
- Score 0.4 → ~18%
- Score 0.5 → ~50%
- Score 0.6 → ~82%
- Score 0.7 → ~95% (sigmoid ceiling)
- Score 0.8+ → ~99%

**Consequence:**
- Small differences near 0.5 create large percentage jumps
- Very difficult to get <10% or >95%
- Most results cluster in 30-80% range

### 1.4 Output Structure

**Returns:** List of dicts sorted by `similarity_percent` descending
```python
[
  {
    "app_id": "uuid-string",
    "similarity_percent": int  # Range: [0, 100]
  },
  ...
]
```

**Size:** Top N results (default: N=10)

**Validation:**
- Raises `ValueError` if buyer has NO labels, tags, or integrations
- Returns empty list `[]` if no vector candidates found

---

## 2. Match Endpoints Flow

### 2.1 Interactive Matching Flow

**Endpoint:** `POST /api/v1/match/interactive/start`

**Request:**
```json
{
  "prompt_text": "string (10-2000 chars)"
}
```

**Processing:**
1. Parse prompt using OpenAI (translation → extraction)
2. Validate against minimum requirements:
   - `MIN_LABELS_REQUIRED = 2`
   - `MIN_TAGS_REQUIRED = 1`
   - `MIN_INTEGRATIONS_REQUIRED = 1`
3. If valid → return `status="ready"`
4. If invalid → generate clarifying question using OpenAI

**Response (needs_more):**
```json
{
  "status": "needs_more",
  "session": {
    "turns": [...],
    "accumulated": {"labels": [], "tags": [], "integrations": []},
    "missing": {"labels_needed": 2, "tags_needed": 0, ...},
    "is_valid": false
  },
  "question": "What main functions do you need? (e.g., CRM, Analytics...)",
  "missing": {...}
}
```

**Response (ready):**
```json
{
  "status": "ready",
  "session": {...},
  "final_prompt": "User need: ...\nExtracted labels: ...",
  "results": null
}
```

---

**Endpoint:** `POST /api/v1/match/interactive/continue`

**Request:**
```json
{
  "session": {...},
  "answer_text": "string (1-1000 chars)"
}
```

**Processing:**
1. Parse answer with prior context
2. Merge new data with accumulated data
3. Re-validate requirements
4. If valid → ready, else → generate next question

**Response:** Same as `/start`

---

**Endpoint:** `POST /api/v1/match/interactive/finalize`

**Request:**
```json
{
  "session": {...},  // must have is_valid=true
  "top_k": 30,
  "top_n": 10
}
```

**Processing:**
1. Validate session is complete (`is_valid=true`)
2. Compose final prompt from all turns
3. Convert session to `buyer_struct` format:
   - First 6 labels → `labels_must`
   - Next 6 labels → `labels_nice`
   - Similar split for tags and integrations
4. Generate embedding from final prompt
5. Run `run_match()` algorithm
6. Fetch app names for results

**Response:**
```json
{
  "status": "ready",
  "session": {...},
  "final_prompt": "...",
  "results": [
    {"app_id": "...", "name": "Salesforce", "similarity_percent": 85},
    ...
  ]
}
```

**Error Handling:**
- `400 Bad Request`: Invalid session, missing fields, constraints violated
- `502 Bad Gateway`: OpenAI API failures, embedding generation errors
- `500 Internal Server Error`: Database errors, unexpected exceptions

---

### 2.2 Backlog Flow

**Endpoint:** `POST /api/v1/backlog/ingest`

**Request:**
```json
{
  "prompt_text": "string",
  "comment_text": "string (optional)"
}
```

**When Request Goes to Backlog:**
- **Always** - this endpoint is specifically for backlog card creation
- Not part of the matching flow
- Used when user request cannot be matched or is a feature request

**Processing:**
1. Search for similar existing backlog cards (embedding similarity)
2. Threshold: ≥50% similarity
3. If match found → append request to existing card
4. If no match → generate title/description via OpenAI → create new card

**Response:** `204 No Content` (currently)

**Assumption:** Separate from match flow. Match flow doesn't auto-redirect to backlog.

---

## 3. Database Signals Used

### 3.1 Tables and Columns

**`application_search`**
- **`embedding`** (vector, 1536 dimensions)
  - Primary signal for semantic similarity
  - Generated from combined app description text
  - Used in: Vector candidate retrieval (cosine distance)
- **`app_id`** (uuid, FK to application)
- **`id`** (uuid, PK, referenced as `app_search_id`)

**`application_labels`**
- **`app_search_id`** (uuid, FK to application_search)
- **`label`** (text)
  - Closed catalog functional categories (e.g., "CRM", "Analytics")
  - Used in: Hard constraint filtering (`labels_must`), hybrid scoring (`labels_nice`)
  - Case-insensitive matching

**`labels`** (lookup table)
- **`label`** (text, PK)
- **`synonyms`** (text[])
  - Used to expand `labels_must` matching
  - E.g., "CRM" might have synonyms ["Customer Management", "Contact Management"]

**`application_integration_keys`**
- **`app_search_id`** (uuid, FK to application_search)
- **`integration_key`** (text)
  - Integration names (e.g., "Stripe", "Salesforce", "Zapier")
  - Normalized to Title Case for comparison
  - Used in: Hard constraint filtering (`integration_required`), hybrid scoring (`integration_nice`)

**`apps_tags`**
- **`app_id`** (uuid, FK to application) ⚠️ Note: Uses `app_id`, not `app_search_id`
- **`tag`** (text)
  - Business context tags (e.g., "B2B", "Enterprise", "Healthcare")
  - Used in: Hybrid scoring only (`tag_must`, `tag_nice`)
  - NOT used as hard constraint

**`application`**
- **`price_text`** (text)
  - Format: "CHF 50", "CHF 50/mes", "Gratis", etc.
  - Used in: Budget constraint filtering (`constraints.price_max`)
  - Extracted to float or 0.0 (free) during matching

**`application_features`**
- **`features_text`** (text)
  - Long-form feature descriptions
  - **NOT used in matching algorithm**
  - Used in: Comparison API for highlights generation
  - **Assumption:** Not part of embedding or label extraction

---

### 3.2 Signal Importance Ranking

**Primary (Core Algorithm):**
1. `application_search.embedding` - 60% weight in hybrid score
2. `application_labels.label` - Hard constraint + 10% weight
3. `application_integration_keys.integration_key` - Hard constraint + 15% weight
4. `apps_tags.tag` - 15% weight (10% tag_must + 5% tag_nice)

**Secondary (Filtering):**
5. `application.price_text` - Hard constraint (budget)
6. `labels.synonyms` - Expands label matching

**Tertiary (Not in Match):**
7. `application_features.features_text` - Used only in comparison API

---

## 4. Failure Modes & Edge Cases

### 4.1 Input Validation Failures

**Too Short Prompt**
- **Constraint:** `prompt_text` min_length=10 chars
- **Behavior:** FastAPI returns `422 Unprocessable Entity`
- **Interactive flow:** If parsed result has insufficient data → `needs_more` status
- **Recommendation:** Test with 5-char, 9-char inputs

**Empty Arrays After Parsing**
- **Scenario:** Prompt like "I need something" → no labels/tags/integrations extracted
- **Behavior:** `ValueError` raised: "at least one of labels, tags, or integrations must be specified"
- **Impact:** Match algorithm refuses to run
- **Recommendation:** Frontend should enforce minimum specificity or catch ValueError

**Missing Required Integrations**
- **Scenario:** Buyer has `integration_required=["Stripe"]`, app doesn't have Stripe
- **Behavior:** App not discarded, assigned `similarity_percent=5`
- **Impact:** App still appears in results but at bottom
- **Assumption:** Design allows visibility of "almost matches"

---

### 4.2 Semantic Ambiguity

**Conflicting Constraints**
- **Scenario:** "Cheap CRM with enterprise features" → `price_max=50`, `tag_must=["Enterprise"]`
- **Behavior:** Very few apps pass both constraints → low result count
- **No explicit handling:** Algorithm doesn't detect or warn about conflicts
- **Recommendation:** Pre-flight validation to detect incompatible constraints

**Multi-Intent Prompts**
- **Scenario:** "I need a CRM and also want to track invoices separately"
- **Behavior:** Parser extracts both CRM and Invoicing labels
- **Impact:** Matching looks for apps with BOTH → may miss specialized tools
- **Recommendation:** Test with conjunctive ("and") vs disjunctive ("or") prompts

**Ambiguous Language**
- **Scenario:** "I need integration with banks" → parser might miss specific bank names
- **Behavior:** Generic term "banks" unlikely in `integration_keys` catalog
- **Impact:** Zero integration overlap → lower scores
- **Recommendation:** Test with generic vs specific integration names

---

### 4.3 Scoring Edge Cases

**Low Similarity but High Label Overlap**
- **Scenario:** 
  - Embedding similarity: 0.3 (30%)
  - Label overlap: 100%
  - Integration overlap: 100%
- **Calculation:**
  ```
  hybrid = (0.6*0.3 + 0.1*1.0 + 0.15*1.0) * 0.45 + 0.55
         = (0.18 + 0.25) * 0.45 + 0.55
         = 0.7435
  percentage = sigmoid(10*(0.7435-0.5)) = ~98%
  ```
- **Result:** High match percentage despite low semantic similarity
- **Assumption:** Label/integration overlap can compensate for semantic mismatch

**High Similarity but Missing Hard Constraints**
- **Scenario:**
  - Embedding similarity: 0.95
  - Missing 1 required label
- **Behavior:** Assigned `similarity_percent=5` regardless of high embedding score
- **Impact:** Excellent semantic match ranked last
- **Recommendation:** Consider graduated penalties instead of flat 5%

**All Nice-to-Have Arrays Empty**
- **Scenario:** Buyer only specifies `labels_must`, all `*_nice` arrays empty
- **Calculation:**
  ```
  hybrid = (0.6*cosine + 0.1*0.1 + 0.1*0.1 + 0.05*0.1 + 0.15*0.1) * 0.45 + 0.55
         ≈ (0.6*cosine + 0.04) * 0.45 + 0.55
  ```
- **Impact:** Nice-to-have weights effectively wasted
- **Behavior:** Still functional, heavily relies on embedding

---

### 4.4 Data Quality Issues

**Empty Integration Keys**
- **Scenario:** App has no integrations in database
- **Behavior:** Integration overlap = 0.1 (baseline from empty list)
- **Impact:** App loses 15% weight from `integrations_nice`

**Synonym Mismatch**
- **Scenario:** Label "CRM" required, app has "Customer Management", synonym not in DB
- **Behavior:** Hard constraint fails → `similarity_percent=5`
- **Impact:** False negative if synonyms incomplete
- **Recommendation:** Audit `labels.synonyms` completeness

**Price Text Parsing Failure**
- **Scenario:** Price text "Contact for pricing" or "Custom"
- **Behavior:** `extract_price_from_text()` returns `None` → optimistically included
- **Impact:** Apps with unparseable prices bypass budget constraint
- **Assumption:** Better to include than exclude when uncertain

---

### 4.5 System Failures

**OpenAI API Timeout**
- **Scenario:** Embedding generation takes >30s or API is down
- **Behavior:** Exception propagates → `502 Bad Gateway`
- **Impact:** Entire match request fails
- **No retry logic visible in code**
- **Recommendation:** Implement exponential backoff retry

**Database Connection Lost**
- **Scenario:** PostgreSQL connection drops mid-query
- **Behavior:** asyncpg raises exception → `500 Internal Server Error`
- **Impact:** Partial results lost, no graceful degradation
- **Recommendation:** Connection pool health checks

**No Vector Candidates**
- **Scenario:** `application_search.embedding` is NULL for all apps
- **Behavior:** Returns empty list `[]`
- **Impact:** Silent failure - client sees zero results
- **Recommendation:** Return 404 or specific error message

---

## 5. Test Coverage Matrix

### 5.1 Interactive Flow Test Cases

| # | Prompt Type | Expected Status | Expected Behavior | Validates |
|---|-------------|-----------------|-------------------|-----------|
| **1** | Complete valid prompt: "I need a CRM with Stripe integration for my B2B SaaS company in healthcare" | `ready` | Extracts 2+ labels, 1+ tag, 1+ integration | Happy path, full extraction |
| **2** | Minimal valid: "I need CRM and analytics, Stripe integration, for B2B" | `ready` | Meets minimum thresholds exactly | Boundary condition |
| **3** | Missing labels: "I need something with Stripe for B2B companies" | `needs_more` | Question about functions/features | Label extraction failure |
| **4** | Missing integration: "I need CRM and analytics for my startup" | `needs_more` | Question about external tools | Integration prompt |
| **5** | Missing tags: "I need CRM with Stripe" | `needs_more` | Question about business context | Tag prompt |
| **6** | Too short: "CRM" | `needs_more` | Multiple iterations needed | Incremental extraction |
| **7** | Non-English: "Necesito un CRM con integración a Stripe para mi empresa B2B" | `ready` or `needs_more` | Translation works, extracts data | i18n support |
| **8** | Ambiguous: "I need a tool" | `needs_more` | Clarifying question | Vague prompt handling |
| **9** | Multi-turn: Start with vague → answer question → answer again | `ready` after 2-3 turns | Accumulation works correctly | Session state management |
| **10** | Invalid session state in `/continue` | `400 Bad Request` | Validation catches corrupt state | Error handling |

### 5.2 Matching Algorithm Test Cases

| # | Scenario | Buyer Requirements | Expected Result | Validates |
|---|----------|-------------------|-----------------|-----------|
| **A** | Perfect match | labels_must=["CRM"], integrations=["Stripe"], App has both | ~95%+ similarity | High confidence match |
| **B** | Synonym match | labels_must=["CRM"], App has "Customer Management" in synonyms | Pass constraint, high score | Synonym expansion |
| **C** | Missing required label | labels_must=["CRM", "Analytics"], App only has "CRM" | 5% similarity | Hard constraint enforcement |
| **D** | Missing required integration | integration_required=["Stripe"], App doesn't have Stripe | 5% similarity | Integration filtering |
| **E** | Over budget | price_max=50, App costs 100 | 5% similarity | Price constraint |
| **F** | Free app with budget | price_max=50, App is "Gratis" | Normal scoring | Free price parsing |
| **G** | All nice-to-have match | labels_nice overlap 100%, embeddings ~0.5 | ~70-80% | Nice-to-have weight |
| **H** | High embedding, no label overlap | cosine=0.9, zero label overlap | ~65-75% | Embedding dominance |
| **I** | Low embedding, perfect labels | cosine=0.3, all labels/integrations match | ~98% | Label/integration compensation |
| **J** | Empty nice-to-have arrays | Only labels_must specified | Relies on embedding only | Weight distribution |
| **K** | Tag overlap (tag_must) | tag_must=["B2B"], App has "B2B" | +10% boost | Tag scoring |
| **L** | Zero results (no candidates) | Embedding returns empty | Empty list [] | Graceful degradation |
| **M** | No requirements (all arrays empty) | labels=[], tags=[], integrations=[] | ValueError exception | Input validation |

### 5.3 Backlog Ingestion Test Cases

| # | Scenario | Expected Behavior | Validates |
|---|----------|-------------------|-----------|
| **B1** | New unique request | Creates new card, generates title/description | Card generation |
| **B2** | Similar to existing card (>50% similarity) | Appends to existing card | Similarity matching |
| **B3** | Just below threshold (48% similarity) | Creates new card | Threshold enforcement |
| **B4** | Non-English request | Translates, processes correctly | i18n support |
| **B5** | Very long prompt (>2000 chars) | Truncates or rejects | Length handling |

### 5.4 Minimum Coverage Set (10 Critical Tests)

**Priority Order for Demo:**

1. **Interactive - Happy Path (Test #1):** Full valid prompt → ready
2. **Interactive - Missing Data (Test #3):** No labels → needs_more → answer → ready
3. **Match - Perfect Match (Test A):** High similarity for exact match
4. **Match - Missing Constraint (Test C):** Hard constraint violation → 5%
5. **Match - Over Budget (Test E):** Price constraint working
6. **Match - Synonym (Test B):** Label synonym expansion
7. **Match - No Results (Test L):** Empty result handling
8. **Match - Invalid Input (Test M):** ValueError on empty requirements
9. **Backlog - New Card (Test B1):** Card creation flow
10. **Error - OpenAI Failure:** Mock API error → 502 response

---

## 6. Validation Thresholds

### 6.1 Configurable Constants

**Location:** `app/services/validation_helpers.py`

```python
MIN_LABELS_REQUIRED = 2
MIN_TAGS_REQUIRED = 1
MIN_INTEGRATIONS_REQUIRED = 1
```

**Recommendation:** Make these environment variables for easy tuning

---

**Location:** `algorithm.py` - `run_match()`

```python
top_k = 30  # Candidates retrieved from vector search
top_n = 10  # Final results returned
```

**Recommendation:** 
- Test with `top_k=50` to see if better candidates appear beyond top 30
- Test with `top_k=10` to measure performance impact

---

### 6.2 Scoring Weights

**Location:** `algorithm.py` - `calculate_hybrid_score()`

```python
EMBEDDING_WEIGHT = 0.60       # 60%
TAG_MUST_WEIGHT = 0.10        # 10%
LABELS_NICE_WEIGHT = 0.10     # 10%
TAG_NICE_WEIGHT = 0.05        # 5%
INTEGRATIONS_NICE_WEIGHT = 0.15  # 15%

# Mystery transformation:
SCALE_FACTOR = 0.45
OFFSET = 0.55
# score = (weighted_sum * 0.45) + 0.55
```

**Questions to Answer:**
- Why the `*0.45 + 0.55` transformation? Is this intentional?
- Should `tag_must` be a hard constraint instead of scoring component?
- Should integration weight be higher given business importance?

**Recommended A/B Tests:**
- Variant 1: Remove transformation (use raw weighted sum)
- Variant 2: Increase integration weight to 20%, decrease embedding to 55%
- Variant 3: Make `tag_must` a hard constraint like `labels_must`

---

### 6.3 Failure Penalty Score

**Location:** `algorithm.py` - `run_match()`

```python
if not meets_requirements or not within_budget:
    similarity_percent = 5  # Fixed penalty score
```

**Current Behavior:**
- Apps failing constraints still appear in results
- Always ranked at bottom (5% similarity)

**Questions:**
- Should failed apps be completely excluded?
- Should penalty be graduated based on how many constraints failed?

**Proposed Alternatives:**
- **Strict Mode:** Discard completely (not append to results)
- **Graduated Penalty:**
  - 1 constraint missed: 15%
  - 2 constraints missed: 10%
  - 3+ constraints missed: 5%

---

### 6.4 Sigmoid Transformation

**Location:** `algorithm.py` - `score_to_percentage()`

```python
sigmoid_steepness = 10
sigmoid_center = 0.5
transformed = 1 / (1 + exp(-10 * (score - 0.5)))
```

**Current Impact:**
- Very steep curve → small score differences create large percentage gaps
- Difficult to get <10% or >95%
- Most results cluster in 30-80% range

**Recommendation to Test:**
- **Gentler curve:** `steepness = 5` → more linear distribution
- **Linear mapping:** `percentage = round(100 * score)` → no sigmoid
- **Threshold alerts:** Flag results where score transformation crosses major boundaries

---

### 6.5 Backlog Similarity Threshold

**Location:** `app/api/backlog_routes.py` - `ingest_backlog_request()`

```python
threshold = 50  # 50% similarity to match existing card
```

**Behavior:**
- ≥50% → append to existing card
- <50% → create new card

**Recommendation:**
- Test with 40%, 60%, 70% to find optimal balance
- Track metrics: % new cards vs % appended requests
- Monitor false positives (wrong card matched) and false negatives (duplicate cards created)

---

### 6.6 Overlap Baseline

**Location:** `algorithm.py` - `overlap_ratio()`

```python
if not list_a:
    return 0.1  # 10% baseline when buyer list is empty
```

**Impact:**
- Empty nice-to-have arrays still contribute small positive score
- Prevents complete zero in overlap calculations

**Question:** Should empty buyer list return 0.0 instead of 0.1?

---

### 6.7 Suggested Demo Validation Criteria

**Acceptance Thresholds (Proposed):**

| Metric | Minimum | Target | Excellent |
|--------|---------|--------|-----------|
| Match similarity for perfect match | 80% | 90% | 95%+ |
| Match similarity for good match | 60% | 75% | 85%+ |
| Hard constraint enforcement | 100% | 100% | 100% |
| False positive rate (wrong apps ranked high) | <20% | <10% | <5% |
| Empty result rate (valid prompts) | <5% | <2% | <1% |
| Interactive flow success (2-3 turns max) | 70% | 85% | 95%+ |
| Response time (p95) | <3s | <2s | <1s |

**≥50% Requirements Interpretation:**

**Assumption:** The "50%" mentioned in backlog context refers to similarity threshold for card matching, NOT a general match threshold.

**In matching algorithm:**
- No explicit "50% minimum" threshold enforced
- Apps failing hard constraints get 5%, not discarded
- Sigmoid transformation makes 50% score → 50% percentage → median result

**To approximate "50% requirement coverage":**
```python
# Pseudo-code for validation
coverage_percent = (
  (len(matched_labels_must) / len(labels_must) * 100) +
  (len(matched_integrations) / len(integrations_required) * 100)
) / 2

if coverage_percent < 50:
    # Reject or flag as low confidence
```

**Recommendation:** Add explicit requirement coverage metric to response

---

## 7. Assumptions & Verification Checklist

**Items Marked as Assumptions:**

- [ ] `tag_must` intentionally not a hard constraint (verify with product team)
- [ ] `*0.45 + 0.55` score transformation is intentional (check git history/comments)
- [ ] `application_features.features_text` not used in matching (confirm with lead engineer)
- [ ] Apps failing constraints assigned 5% by design (verify business logic)
- [ ] Empty nice-to-have arrays returning 0.1 baseline is correct (validate math)
- [ ] Price parsing optimistically includes unparseable prices (confirm safety approach)
- [ ] No retry logic for OpenAI API is acceptable (check infrastructure resilience)
- [ ] Interactive flow doesn't auto-redirect to backlog on low scores (verify product flow)

**Verification Steps:**

1. Run Test Suite #1-10 (Interactive) and A-M (Algorithm)
2. Measure actual percentage distributions in production logs
3. A/B test alternative scoring weights
4. Profile top_k parameter for performance vs accuracy tradeoff
5. Audit `labels.synonyms` table completeness
6. Load test with concurrent OpenAI embedding requests
7. Validate sigmoid transformation intent with stakeholders

---

**End of Document**
