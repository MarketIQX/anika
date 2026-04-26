from app.db import fetch_one

# Queue 15 should have anika_proposed=firm_policy, user's pick recorded
q = fetch_one("SELECT id, status, anika_proposed_purpose, awaiting_confirmation, error_text FROM teaching_queue WHERE id=15")
print("Queue 15:")
print(f"  status: {q['status']}")
print(f"  anika_proposed: {q['anika_proposed_purpose']}")
print(f"  awaiting: {q['awaiting_confirmation']}")
print(f"  error: {q['error_text']}")

# Library entry 23 — how was it created?
lib = fetch_one("SELECT id, purpose, anika_proposed_purpose, user_confirmed_purpose, source_queue_id, created_by FROM knowledge_library WHERE id=23")
print()
print("Library id=23:")
print(f"  purpose: {lib['purpose']}")
print(f"  anika_proposed: {lib['anika_proposed_purpose']}")
print(f"  user_confirmed: {lib['user_confirmed_purpose']}")
print(f"  source_queue: {lib['source_queue_id']}")
print(f"  created_by: {lib['created_by']}")
