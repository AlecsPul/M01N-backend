# BexInsights Demo Prompt Library

**Document Version:** 1.0  
**Date:** January 15, 2026  
**Purpose:** Curated prompt scenarios for testing the interactive matching system across all branches

---

## Table of Contents

1. [System Validation Rules](#system-validation-rules)
2. [Scenario A: Under-Specified → Expanded → Rejected](#scenario-a-under-specified--expanded--rejected)
3. [Scenario B: Under-Specified → Expanded → Matches](#scenario-b-under-specified--expanded--matches)
4. [Scenario C: Very Detailed → Immediate Accept → Matches](#scenario-c-very-detailed--immediate-accept--matches)
5. [Scenario D: Very Detailed → Rejected](#scenario-d-very-detailed--rejected)
6. [Testing Notes](#testing-notes)

---

## System Validation Rules

**Current System Requirements (as of evaluation):**

A prompt is considered **valid** when it meets ALL of the following:
- **Minimum 2 labels** (functional categories from closed catalog)
- **Minimum 1 tag** (business context keyword)
- **Minimum 1 integration** (external service/platform name)

**Note:** The system description in the task mentions 4 labels, but according to `validation_helpers.py`, the actual implementation requires only 2 labels. This library uses the implemented threshold (2 labels).

**Status Values:**
- `needs_more` - Missing one or more requirements, system asks clarifying question
- `ready` - All requirements met, ready for matching
- `rejected` - After matching, no suitable apps found or all apps scored ≤5%

---

## Scenario A: Under-Specified → Expanded → Rejected

**Business Context:** Small architectural firm looking for project management tools but has very specific, incompatible requirements.

### A.1 Initial Prompt (Turn 1)

**User Input:**
```
I need a tool to manage my projects
```

**Expected Backend Response:**
```json
{
  "status": "needs_more",
  "missing": {
    "labels_needed": 2,
    "tags_needed": 1,
    "integrations_needed": 1
  },
  "question": "What main functions do you need? (e.g., Project Management, Time Tracking, CRM, Invoicing, ...)"
}
```

**Reason:** 
- Extracted labels: 0-1 (possibly "Project Management" but insufficient)
- Extracted tags: 0 (no business context)
- Extracted integrations: 0

---

### A.2 Follow-up Prompt (Turn 2)

**User Input:**
```
I need time tracking and resource planning for my architecture firm
```

**Expected Backend Response:**
```json
{
  "status": "needs_more",
  "missing": {
    "labels_needed": 0,
    "tags_needed": 0,
    "integrations_needed": 1
  },
  "question": "Which external tools must it integrate with? (e.g., Salesforce, QuickBooks, Slack, ...)"
}
```

**Reason:**
- Accumulated labels: ["Project Management", "Time Tracking"] (2 labels ✓)
- Accumulated tags: ["Architecture"] (1 tag ✓)
- Accumulated integrations: [] (0 integrations ✗)

---

### A.3 Final Prompt (Turn 3)

**User Input:**
```
It must integrate with AutoCAD and Revit, and it needs to be completely free
```

**Expected Backend Response:**
```json
{
  "status": "ready",
  "session": {
    "is_valid": true,
    "accumulated": {
      "labels": ["Project Management", "Time Tracking"],
      "tags": ["Architecture"],
      "integrations": ["AutoCAD", "Revit"]
    }
  },
  "final_prompt": "User need: I need a tool to manage my projects\nClarifications:\n- I need time tracking and resource planning for my architecture firm\n- It must integrate with AutoCAD and Revit...",
  "results": null
}
```

**Reason:**
- All requirements met: 2 labels, 1 tag, 2 integrations
- Ready for matching via `/finalize`

---

### A.4 Finalize (Matching Execution)

**POST /finalize Request:**
```json
{
  "session": { ... },
  "top_k": 30,
  "top_n": 10
}
```

**Expected Outcome: REJECTED**

**Expected Backend Response:**
```json
{
  "status": "ready",
  "results": []
}
```
**OR**
```json
{
  "status": "ready",
  "results": [
    {"app_id": "...", "name": "Generic Project Tool", "similarity_percent": 5}
  ]
}
```

**Rationale for Rejection:**
1. **Niche integrations:** AutoCAD and Revit are highly specialized CAD software integrations
2. **Price constraint:** "Completely free" (`price_max = 0`) eliminates most professional tools
3. **Domain mismatch:** Architecture-specific project management is uncommon in general business marketplace
4. **Expected behavior:** 
   - Vector search may find generic PM tools
   - Hard constraints fail: missing AutoCAD/Revit integrations → `similarity_percent = 5`
   - Free constraint filters out most paid options
   - Result: Empty or near-empty result set

---

## Scenario B: Under-Specified → Expanded → Matches

**Business Context:** E-commerce startup looking for accounting and payment processing tools.

### B.1 Initial Prompt (Turn 1)

**User Input:**
```
I need accounting software for my online store
```

**Expected Backend Response:**
```json
{
  "status": "needs_more",
  "missing": {
    "labels_needed": 1,
    "tags_needed": 1,
    "integrations_needed": 1
  },
  "question": "What main functions do you need? (e.g., Invoicing, Expense Tracking, Reporting, Tax Management, ...)"
}
```

**Reason:**
- Extracted labels: ["Accounting"] (1 label, need 1 more)
- Extracted tags: ["Online Store"] (possibly, but might be missed → 0 tags)
- Extracted integrations: [] (0 integrations)

---

### B.2 Follow-up Prompt (Turn 2)

**User Input:**
```
I need invoicing and expense tracking for my Swiss e-commerce business
```

**Expected Backend Response:**
```json
{
  "status": "needs_more",
  "missing": {
    "labels_needed": 0,
    "tags_needed": 0,
    "integrations_needed": 1
  },
  "question": "Which external tools must it integrate with? (e.g., Stripe, Shopify, PayPal, WooCommerce, ...)"
}
```

**Reason:**
- Accumulated labels: ["Accounting", "Invoicing", "Expense Tracking"] (3 labels ✓)
- Accumulated tags: ["E-commerce", "Switzerland"] (2 tags ✓)
- Accumulated integrations: [] (0 integrations ✗)

---

### B.3 Final Prompt (Turn 3)

**User Input:**
```
It should work with Stripe and WooCommerce
```

**Expected Backend Response:**
```json
{
  "status": "ready",
  "session": {
    "is_valid": true,
    "accumulated": {
      "labels": ["Accounting", "Invoicing", "Expense Tracking"],
      "tags": ["E-commerce", "Switzerland"],
      "integrations": ["Stripe", "WooCommerce"]
    }
  },
  "final_prompt": "...",
  "results": null
}
```

**Reason:**
- All requirements met: 3 labels, 2 tags, 2 integrations
- Ready for matching

---

### B.4 Finalize (Matching Execution)

**Expected Outcome: MATCHES**

**Expected Backend Response:**
```json
{
  "status": "ready",
  "results": [
    {"app_id": "uuid-1", "name": "Bexio", "similarity_percent": 92},
    {"app_id": "uuid-2", "name": "Run my Accounts", "similarity_percent": 87},
    {"app_id": "uuid-3", "name": "Klara", "similarity_percent": 81},
    {"app_id": "uuid-4", "name": "Zervant", "similarity_percent": 75},
    {"app_id": "uuid-5", "name": "AbaNinja", "similarity_percent": 72}
  ]
}
```

**Rationale for Success:**
1. **Common business need:** Accounting + Invoicing is well-represented in marketplace
2. **Popular integrations:** Stripe and WooCommerce are widely supported
3. **Clear context:** E-commerce + Switzerland provides strong semantic signals
4. **No restrictive constraints:** No unrealistic budget or rare integrations
5. **Expected behavior:**
   - Vector embedding finds semantically similar accounting apps
   - Integration overlap: Many apps support Stripe/WooCommerce
   - Label overlap: Accounting and Invoicing are standard categories
   - Strong hybrid scores (75-95% range)

---

## Scenario C: Very Detailed → Immediate Accept → Matches

**Business Context:** Growing SaaS company needs comprehensive customer management and analytics platform.

### C.1 Single Detailed Prompt

**User Input:**
```
I need a comprehensive CRM system with sales pipeline management, customer analytics, and reporting dashboards for my B2B SaaS company. The platform must integrate with Salesforce, HubSpot, and Google Workspace for seamless data flow. We're a mid-sized tech startup in Zurich serving enterprise clients across Europe, and we need robust API access for custom integrations. The solution should support multi-user collaboration and have strong data export capabilities.
```

**Expected Backend Response:**
```json
{
  "status": "ready",
  "session": {
    "is_valid": true,
    "accumulated": {
      "labels": ["CRM", "Sales Management", "Analytics", "Reporting", "API"],
      "tags": ["B2B", "SaaS", "Tech", "Zurich", "Enterprise", "Startup"],
      "integrations": ["Salesforce", "HubSpot", "Google Workspace"]
    },
    "missing": {
      "labels_needed": 0,
      "tags_needed": 0,
      "integrations_needed": 0
    },
    "is_valid": true
  },
  "final_prompt": "User need: I need a comprehensive CRM system...",
  "results": null
}
```

**Reason:**
- Extracted labels: 5+ labels (CRM, Sales Management, Analytics, Reporting, API)
- Extracted tags: 6+ tags (B2B, SaaS, Tech, Zurich, Enterprise, Startup)
- Extracted integrations: 3 integrations (Salesforce, HubSpot, Google Workspace)
- **Immediately valid** - no `needs_more` cycle required

---

### C.2 Finalize (Matching Execution)

**Expected Outcome: STRONG MATCHES (2+ apps)**

**Expected Backend Response:**
```json
{
  "status": "ready",
  "results": [
    {"app_id": "uuid-1", "name": "HubSpot CRM", "similarity_percent": 94},
    {"app_id": "uuid-2", "name": "Pipedrive", "similarity_percent": 89},
    {"app_id": "uuid-3", "name": "Zoho CRM", "similarity_percent": 85},
    {"app_id": "uuid-4", "name": "Salesforce Essentials", "similarity_percent": 82},
    {"app_id": "uuid-5", "name": "Monday CRM", "similarity_percent": 78}
  ]
}
```

**Rationale for Strong Matches:**
1. **Rich feature set:** CRM + Analytics + Reporting are mainstream business needs
2. **Popular integrations:** Salesforce, HubSpot, Google Workspace have broad marketplace support
3. **Clear buyer profile:** B2B SaaS + Enterprise + Zurich provide strong semantic context
4. **No hard blockers:** No extreme budget constraints or impossible requirements
5. **Multi-signal alignment:**
   - High embedding similarity (detailed, specific language)
   - Strong label overlap (5 labels = first 5 as `labels_must`)
   - Excellent integration overlap (3 major platforms)
   - Rich tag context (6 tags boost scoring)
6. **Expected scores:** 75-95% range due to comprehensive matching across all signals

---

## Scenario D: Very Detailed → Rejected

**Business Context:** Niche pharmaceutical research lab with highly specialized compliance requirements.

### D.1 Single Detailed Prompt (Incompatible Requirements)

**User Input:**
```
I need a laboratory information management system with FDA 21 CFR Part 11 compliance, GxP validation documentation, and electronic lab notebook functionality. The platform must integrate with our proprietary LIMS system called LabCore Pro, connect to Thermo Fisher Scientific instruments via direct API, and support CDISC data standards for clinical trial submissions. We require on-premise deployment only due to Swiss healthcare data privacy regulations, with support for ISO 27001 and HIPAA compliance. The solution must handle mass spectrometry data processing and integrate with our existing SAP ERP system. Budget is limited to CHF 500 per month maximum.
```

**Expected Backend Response:**
```json
{
  "status": "ready",
  "session": {
    "is_valid": true,
    "accumulated": {
      "labels": ["Laboratory Management", "Compliance", "Data Management", "ERP Integration", "Analytics"],
      "tags": ["Pharmaceutical", "Healthcare", "Clinical Trials", "Switzerland", "On-Premise", "Research"],
      "integrations": ["LabCore Pro", "Thermo Fisher", "SAP", "CDISC"]
    },
    "missing": {
      "labels_needed": 0,
      "tags_needed": 0,
      "integrations_needed": 0
    },
    "is_valid": true
  },
  "final_prompt": "User need: I need a laboratory information management system...",
  "results": null
}
```

**Reason:**
- Extracted labels: 5+ labels (Laboratory Management, Compliance, Data Management, ERP Integration, Analytics)
- Extracted tags: 6+ tags (Pharmaceutical, Healthcare, Clinical Trials, Switzerland, On-Premise, Research)
- Extracted integrations: 4 integrations (LabCore Pro, Thermo Fisher, SAP, CDISC)
- **Immediately valid** - detailed and structured

---

### D.2 Finalize (Matching Execution)

**Expected Outcome: REJECTED (No matches or all 5%)**

**Expected Backend Response:**
```json
{
  "status": "ready",
  "results": []
}
```
**OR**
```json
{
  "status": "ready",
  "results": [
    {"app_id": "uuid-1", "name": "Generic Data Platform", "similarity_percent": 5},
    {"app_id": "uuid-2", "name": "Basic ERP Connector", "similarity_percent": 5}
  ]
}
```

**Rationale for Rejection:**

**Hard Constraint Failures:**
1. **Proprietary integration:** "LabCore Pro" is a fictional/proprietary system unlikely in `integration_keys` catalog
   - Missing required integration → `similarity_percent = 5`
   
2. **Specialized integrations:** "Thermo Fisher Scientific" and "CDISC" are highly niche
   - Bexio marketplace focuses on general business apps, not scientific instruments
   - Missing required integrations → hard constraint fails

3. **Budget mismatch:** CHF 500/month is low for enterprise-grade pharmaceutical compliance software
   - Real pharmaceutical LIMS systems cost CHF 5,000-50,000+/month
   - Price constraint (`price_max = 500`) eliminates realistic matches

**Semantic Mismatch:**
4. **Domain disconnect:** Bexio marketplace targets SMEs (accounting, CRM, HR, project management)
   - Pharmaceutical LIMS is a vertical-specific enterprise solution
   - Low embedding similarity with marketplace app descriptions

5. **Regulatory complexity:** FDA 21 CFR Part 11, GxP, ISO 27001, HIPAA are specialized compliance frameworks
   - Not common in general business software catalog
   - Semantic signals won't match general business app embeddings

**Expected Matching Behavior:**
- **Vector search phase:** May retrieve generic "Data Management" or "Analytics" apps with low similarity (0.2-0.4)
- **Constraint filtering:** All apps fail integration requirements (LabCore Pro, Thermo Fisher, CDISC absent)
- **Penalty assignment:** Apps assigned `similarity_percent = 5` due to missing hard constraints
- **Price filtering:** Any apps with parseable prices >CHF 500 also get penalized
- **Final result:** Empty list or list of 5% matches (effectively rejected)

**Realistic Outcome:**
This buyer should be redirected to:
- Specialized scientific software vendors (not general business marketplace)
- Custom enterprise solution providers
- Or backlog for future consideration as "out of scope" request

---

## Testing Notes

### Test Execution Guidelines

**For Each Scenario:**

1. **Start Session**
   - `POST /api/v1/match/interactive/start`
   - Send initial prompt
   - Verify `status` and `missing` fields
   - Check question relevance

2. **Continue Session** (if `needs_more`)
   - `POST /api/v1/match/interactive/continue`
   - Send follow-up prompt with session state
   - Verify accumulated data merges correctly
   - Repeat until `status = "ready"`

3. **Finalize Matching**
   - `POST /api/v1/match/interactive/finalize`
   - Verify results array content
   - Check similarity percentages
   - Validate app names returned

4. **Observe Behaviors**
   - Question generation varies examples (labels/integrations/tags change per seed)
   - Prompt translations work for non-English inputs
   - Session state persists across turns
   - Error handling for invalid states

---

### Expected System Variations

**Due to Prompt Variation System:**
- Question wording will differ between runs (deterministic based on seed)
- Integration examples rotate (Stripe/DATEV/Shopify vs Salesforce/QuickBooks/Slack)
- Label catalog samples vary (different starting positions)
- Tag context examples alternate (industry/company size vs sector/team size)

**Matching Variations:**
- Exact similarity percentages may vary slightly due to:
  - Database state changes (new apps added)
  - Embedding model updates
  - Label synonym additions
  - Integration catalog expansions

**Acceptable Ranges:**
- Scenario B (success): Similarity 70-95% expected
- Scenario C (strong success): Similarity 75-95% expected
- Scenario A & D (rejection): Similarity ≤10% expected

---

### Validation Checklist

**Per Scenario, verify:**

- [ ] Initial prompt triggers correct `needs_more` or `ready` status
- [ ] Missing requirements correctly identified (labels/tags/integrations)
- [ ] Questions generated are relevant to missing data
- [ ] Follow-up prompts accumulate data correctly
- [ ] Session state persists and merges properly
- [ ] Final validation logic passes when thresholds met
- [ ] Matching algorithm runs without errors
- [ ] Results array contains expected number of items
- [ ] Similarity percentages are within expected ranges
- [ ] Hard constraints are enforced (rejected apps get 5%)
- [ ] Budget constraints are respected
- [ ] Label synonyms work correctly (if applicable)

---

### Additional Test Scenarios (Optional Extensions)

**E) Multi-language Test:**
```
Prompt (German): "Ich brauche eine CRM-Lösung mit Stripe-Integration für mein B2B-Startup in Zürich"
Expected: Translation works, extracts labels/tags/integrations, returns results
```

**F) Edge Case - Exactly Minimum Requirements:**
```
Prompt: "I need CRM and invoicing software with Zapier integration for my B2B company"
Expected: Exactly 2 labels, 1 tag, 1 integration → immediate "ready"
```

**G) Conflicting Constraints:**
```
Prompt: "I need enterprise-grade CRM with advanced analytics and must be completely free"
Expected: Matches returned but low scores due to price filter
```

**H) Generic Request:**
```
Prompt: "I need something to help my business"
Expected: Multiple "needs_more" turns required, clarifying questions about functions, integrations, context
```

---

**End of Document**
