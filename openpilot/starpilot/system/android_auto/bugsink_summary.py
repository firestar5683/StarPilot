"""Readable report text and session-owned software identity."""

TRANSPORTS = {"wired": "Wired USB", "wireless": "Wireless", "headunitpad": "HeadunitPad (Wi-Fi)",
              "openheadunit": "Open Headunit (Wi-Fi)", "unknown": "Unknown"}


def connection_label(value):
  return TRANSPORTS.get(value, value.replace("_", " ") if value else "Unknown")


def software_tags(records):
  software = [record.get("software") or {} for record in records]
  result = {}
  for field in ("commit", "branch"):
    values = {str(item.get(field) or "unknown") for item in software}
    result[field] = next(iter(values)) if len(values) == 1 else "mixed"
  return result


def overview(records):
  software = software_tags(records)
  transports = sorted({connection_label(record.get("transport", "")) for record in records})
  return [f"Connection: {', '.join(transports)}", f"Session commit: {software['commit']}", f"Branch: {software['branch']}"]


def failure_summary(assessment):
  return "\n".join([f"Assessment ({assessment['confidence']}): {assessment['summary']}", f"Evidence: {assessment['evidence']}",
                    "Next steps:", *(f"  {index}. {step}" for index, step in enumerate(assessment["next_steps"], 1))])


def session_timeline(session):
  lines = [f"Outcome: {session['outcome'].capitalize()} | Failures: {session['failures']} | Drops: {session['drops']}"]
  if session.get("settings"):
    lines.append("Settings: " + ", ".join(f"{key}={value}" for key, value in session["settings"].items()))
  attempts = session.get("attempts", [])
  lines.append("Attempt timeline:")
  for attempt in attempts[-5:]:
    stages = " → ".join(f"{stage['stage'].replace('_', ' ')} ({stage['at_s']}s)" for stage in attempt["stages"][-6:])
    result = "video acknowledged" if attempt["video_acknowledged"] else "no acknowledged video"
    if attempt.get("error_kind"):
      result += f"; {attempt['error_kind']} at {attempt.get('failed_at_s')}s"
    if attempt["after_car_shutdown"]:
      result += "; retry after car shutdown"
    lines.append(f"  {attempt['attempt']}. {stages or 'No stage recorded'} — {result}")
  if len(attempts) > 5:
    lines.append(f"  Showing last 5 of {len(attempts)} attempts; see session details.")
  lines.append(f"Log: {session['name']}")
  return "\n".join(lines)


def batch_summary(sessions, summary):
  lines = overview(sessions) + [f"Sessions: {len(sessions)} | Failures: {summary['failures']} | Drops: {summary['drops']}",
    f"Outcome: {summary['outcome'].capitalize()} | Average FPS: {summary['fps_avg'] if summary['fps_avg'] is not None else 'unknown'}"]
  for session in sessions:
    commit = (session.get("software") or {}).get("commit") or "unknown"
    lines.append(f"  Session {session['seq']}: {connection_label(session['transport'])}, {session['outcome']}, commit {commit}")
  return "\n".join(lines)


def pairing_summary(record):
  return "\n".join(overview([record]) + [f"Pairing: {record.get('result', 'unknown')}",
    f"Duration: {record.get('duration_s', 'unknown')} seconds",
    "Steps: " + " → ".join(step.get("step", "unknown").replace("_", " ") for step in record.get("steps", [])[-10:])])
