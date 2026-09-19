"""Status passed with PCM; preserve actual rendered state and its audio clock."""
EXPORT_FIELDS = ['composer','job_inflight','generation_elapsed_seconds','readiness','profile','safe_extensions','quality_failures','holding_accepted_music','identity','style','playing_identity','phase','lead','buffered','arrival_at','worker_failed','section','next_section','scheduled','gesture_active','gesture_queued','turn_signal_music','outro_heard_seconds','form_labels_are_intent'] + ['render_mode','presentation_policy','elapsed','alert_accent','signal_shaker','core_apex','engagement_presentation']

def export_status(snapshot):
    return {key: snapshot.get(key) for key in EXPORT_FIELDS}
