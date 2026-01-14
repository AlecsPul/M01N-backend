# Backlog System Architecture

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT REQUEST                                │
│                    POST /api/v1/backlog/ingest                       │
│                                                                       │
│  {                                                                    │
│    "prompt_text": "Necesito integrar Stripe...",                     │
│    "comment_text": "Es urgente..."                                   │
│  }                                                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              FASTAPI ENDPOINT (app/api/routes/backlog.py)            │
│                                                                       │
│  1. Validate request (Pydantic schema)                               │
│  2. Get database session (AsyncSession)                              │
│  3. Handle exceptions (400/502/500)                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   MATCHER (backlog/matcher.py)                       │
│                  find_matching_card_id()                             │
│                                                                       │
│  For each active card:                                               │
│    ├─ Get random prompt sample                                       │
│    ├─ Call similarity evaluation                                     │
│    └─ Calculate similarity %                                         │
│                                                                       │
│  Return: UUID (if match ≥50%) OR 0 (if no match)                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        MATCH FOUND              NO MATCH
         (card_id)                (0)
                │                     │
                ▼                     ▼
    ┌───────────────────┐   ┌────────────────────┐
    │   EXISTING CARD   │   │    NEW CARD        │
    └─────────┬─────────┘   └─────────┬──────────┘
              │                       │
              │                       ▼
              │         ┌──────────────────────────────────┐
              │         │  CARD GENERATION                 │
              │         │  (backlog/card_generation.py)    │
              │         │                                  │
              │         │  1. Normalize to English         │
              │         │  2. Generate title (<10 words)   │
              │         │  3. Generate description         │
              │         │  4. Validate (retry if needed)   │
              │         │                                  │
              │         │  Uses: OpenAI gpt-4o-mini        │
              │         └────────────┬─────────────────────┘
              │                      │
              └──────────┬───────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│              REPOSITORY (backlog/repository.py)                      │
│                  process_incoming_request()                          │
│                                                                       │
│  IF MATCH FOUND:                                                     │
│    └─ add_prompt_to_existing_card()                                 │
│       ├─ Insert into card_prompts_comments                          │
│       └─ Increment card.number_of_requests                          │
│                                                                       │
│  IF NO MATCH:                                                        │
│    └─ create_new_card_with_prompt()                                 │
│       ├─ Create card (status=1, number_of_requests=1)               │
│       └─ Insert into card_prompts_comments                          │
│                                                                       │
│  Transaction: COMMIT or ROLLBACK                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL)                           │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ cards                                                         │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ id (UUID)           │ title            │ description        │   │
│  │ status              │ number_of_requests│ created_at        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ card_prompts_comments                                        │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ id (UUID)           │ card_id (FK)     │ prompt_text        │   │
│  │ comment_text        │ created_at                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          RESPONSE                                    │
│                     HTTP 204 No Content                              │
│                     (Success, no body)                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Similarity Evaluation Detail

```
┌─────────────────────────────────────────────────────────────────────┐
│              SIMILARITY (backlog/similarity.py)                      │
│                  evaluate_similarity()                               │
│                                                                       │
│  1. NORMALIZE TO ENGLISH                                             │
│     ├─ incoming_prompt → English                                     │
│     ├─ incoming_comment → English (if provided)                      │
│     └─ card_prompt → English                                         │
│                                                                       │
│     Uses: openai_client.normalize_to_english()                       │
│     Model: gpt-4o-mini, temperature: 0.3                             │
│                                                                       │
│  2. GENERATE EMBEDDINGS                                              │
│     ├─ incoming_text = prompt + comment                              │
│     ├─ card_text = card_prompt                                       │
│     └─ Get 1536-dim vectors                                          │
│                                                                       │
│     Uses: openai_client.get_embedding()                              │
│     Model: text-embedding-3-small                                    │
│                                                                       │
│  3. CALCULATE SIMILARITY                                             │
│     ├─ Cosine similarity (dot product / norms)                       │
│     ├─ Sigmoid transformation: 1/(1+e^(-10*(x-0.5)))                │
│     └─ Convert to percentage (0-100)                                 │
│                                                                       │
│  Return: int (0-100) similarity percentage                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Dependencies

```
app/api/routes/backlog.py
├── app/api/schemas/backlog.py (Pydantic models)
├── app/core/database.py (get_db dependency)
├── backlog/matcher.py
│   ├── backlog/similarity.py
│   │   ├── app/core/openai_client.py (get_embedding, normalize_to_english)
│   │   └── app/matching/algorithm.py (sigmoid function)
│   └── app/models/models.py (Card, CardPromptComment)
├── backlog/card_generation.py
│   └── app/core/openai_client.py (normalize_to_english, OpenAI client)
└── backlog/repository.py
    └── app/models/models.py (Card, CardPromptComment)
```

## Error Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ERROR HANDLING                                │
│                                                                       │
│  INPUT VALIDATION ERROR                                              │
│  ├─ Empty prompt_text                                                │
│  ├─ prompt_text too short (<5 chars)                                 │
│  ├─ prompt_text too long (>2000 chars)                               │
│  └─ comment_text too long (>1000 chars)                              │
│      │                                                                │
│      └─→ HTTP 400 Bad Request                                        │
│          {"detail": "Invalid input: ..."}                            │
│                                                                       │
│  OPENAI API ERROR                                                    │
│  ├─ Rate limit exceeded                                              │
│  ├─ Invalid API key                                                  │
│  ├─ Timeout                                                          │
│  └─ Model unavailable                                                │
│      │                                                                │
│      └─→ HTTP 502 Bad Gateway                                        │
│          {"detail": "External service error: ..."}                   │
│                                                                       │
│  DATABASE ERROR                                                      │
│  ├─ Connection failed                                                │
│  ├─ Transaction rollback                                             │
│  └─ Constraint violation                                             │
│      │                                                                │
│      └─→ HTTP 500 Internal Server Error                              │
│          {"detail": "Failed to process backlog request: ..."}        │
└─────────────────────────────────────────────────────────────────────┘
```

## Matching Algorithm Detail

```
THRESHOLD = 50%

For each active card in database:
  │
  ├─ Get random prompt (sample one per card)
  │
  ├─ Evaluate similarity
  │  └─ Returns percentage (0-100)
  │
  └─ Track best match

IF best_similarity >= THRESHOLD:
  └─ Return matched_card_id
ELSE:
  └─ Return 0 (no match)


Example:
  Card A prompts: ["Need CRM integration", "Want Salesforce sync"]
    → Sample: "Need CRM integration"
    → Similarity: 75% ✓

  Card B prompts: ["Excel export feature", "Data to CSV"]
    → Sample: "Excel export feature"
    → Similarity: 22% ✗

  Card C prompts: ["Payment gateway", "Stripe integration"]
    → Sample: "Payment gateway"
    → Similarity: 45% ✗

  Result: Match Card A (75% > 50%)
```

## Data Flow Example

```
INPUT:
  prompt_text: "Necesito integrar Stripe con mi CRM"
  comment_text: "Es urgente para Q2"

↓ NORMALIZE
  prompt_en: "I need to integrate Stripe with my CRM"
  comment_en: "It's urgent for Q2"

↓ EMBEDDING
  vector: [0.123, -0.456, 0.789, ..., 0.234] (1536 dims)

↓ COMPARE WITH CARDS
  Card 1: "Payment gateway integration" → 82% ✓
  Card 2: "Dashboard analytics" → 18% ✗
  Card 3: "Export to Excel" → 25% ✗

↓ MATCH FOUND
  card_id: 550e8400-e29b-41d4-a716-446655440000

↓ UPDATE DATABASE
  - Add to card_prompts_comments:
    {
      card_id: 550e8400-...,
      prompt_text: "Necesito integrar Stripe con mi CRM",
      comment_text: "Es urgente para Q2"
    }
  - Increment card.number_of_requests: 5 → 6

↓ RESPONSE
  HTTP 204 No Content
```

## Performance Considerations

### Optimization Points

1. **Embedding Cache**: Cache normalized + embedded texts
2. **Batch Processing**: Process multiple requests in parallel
3. **Database Indexing**: Index card.status and created_at
4. **Random Sampling**: O(1) per card vs O(n) for all prompts
5. **Connection Pooling**: Reuse database connections

### Scalability

- **Current**: ~100 cards, ~1000 prompts/card
- **Load**: ~1-2 seconds per request (OpenAI latency)
- **Bottleneck**: OpenAI API rate limits (500 RPM for embeddings)
- **Solution**: Implement request queue + worker pool

### Cost Estimation (OpenAI)

Per request:
- 2-3 normalization calls: $0.000015 (gpt-4o-mini)
- 2-3 embedding calls: $0.000002 (text-embedding-3-small)
- 1 generation call (if new): $0.000030 (gpt-4o-mini)

Total: ~$0.000047 per request (~$47 per million requests)
