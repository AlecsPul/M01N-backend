"""
Prompt Composer
Compose final prompt from interactive session state.
"""
from app.schemas.interactive_match import SessionState


def compose_final_prompt(state: SessionState) -> str:
    """
    Compose final prompt text from interactive session state.
    
    Concatenates all English turns into a structured prompt format:
    - User need: initial prompt
    - Clarifications: follow-up answers
    - Extracted labels: comma-separated
    - Extracted tags: comma-separated
    - Extracted integrations: comma-separated
    
    Args:
        state: Complete session state
        
    Returns:
        Final prompt string ready for matching
    """
    if not state.turns:
        return ""
    
    sections = []
    
    sections.append(f"User need: {state.turns[0].english_text}")
    
    if len(state.turns) > 1:
        clarifications = []
        for turn in state.turns[1:]:
            clarifications.append(turn.english_text)
        sections.append("Clarifications:\n" + "\n".join(f"- {c}" for c in clarifications))
    
    if state.accumulated.labels:
        sections.append(f"Extracted labels: {', '.join(state.accumulated.labels)}")
    
    if state.accumulated.tags:
        sections.append(f"Extracted tags: {', '.join(state.accumulated.tags)}")
    
    if state.accumulated.integrations:
        sections.append(f"Extracted integrations: {', '.join(state.accumulated.integrations)}")
    
    return "\n\n".join(sections)


def format_for_matching_service(state: SessionState) -> dict:
    """
    Convert interactive session state to matching service format.
    
    Args:
        state: Session state
        
    Returns:
        Dict compatible with existing matching service (buyer_struct format)
    """
    all_labels = state.accumulated.labels
    labels_must = all_labels[:6] if all_labels else []
    labels_nice = all_labels[6:12] if len(all_labels) > 6 else []
    
    all_tags = state.accumulated.tags
    tag_must = all_tags[:6] if all_tags else []
    tag_nice = all_tags[6:12] if len(all_tags) > 6 else []
    
    all_integrations = state.accumulated.integrations
    integration_required = all_integrations[:10] if all_integrations else []
    integration_nice = all_integrations[10:20] if len(all_integrations) > 10 else []
    
    final_prompt = compose_final_prompt(state)
    
    return {
        "buyer_text": final_prompt,
        "labels_must": labels_must,
        "labels_nice": labels_nice,
        "tag_must": tag_must,
        "tag_nice": tag_nice,
        "integration_required": integration_required,
        "integration_nice": integration_nice,
        "constraints": {"price_max": None},
        "notes": f"Interactive session with {len(state.turns)} turn(s)"
    }
