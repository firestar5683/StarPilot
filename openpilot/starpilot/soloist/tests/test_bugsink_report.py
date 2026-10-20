import json

from openpilot.starpilot.soloist import bugsink_report as report
from openpilot.starpilot.soloist.paths import Layout

BASE = 1_000_000.0


def rtp(at, lost):
  return f'{at:.6f} comma bluealsa[1]: bluealsa: [2] W: rtp.c:145: Missing RTP packets [5 != 4]: {lost}'


def underrun(at):
  return f"{at:.6f} comma pulseaudio[3]: Implicit underrun of 'Phone music'"


def timing(at, audio_ms=1020.0, reads=0):
  body = json.dumps({'event': 'phone_audio_timing', 'interval_s': 1.0, 'audio_ms': audio_ms, 'max_read_ms': 90.0,
                     'max_write_ms': 10.0, 'reads_over_50ms': reads, 'writes_over_50ms': 0})
  return f'{at:.6f} comma starpilot-phone-audio[4]: {body}'


def test_nearby_signals_form_one_window_and_quiet_gaps_split_them():
  lines = [rtp(BASE, 2), rtp(BASE + 3, 4), underrun(BASE + 4), timing(BASE + 5, 700, 2), rtp(BASE + 40, 1), 'junk line']
  first, second = report.windows(lines)
  assert (first['lost_packets'], first['rtp_warnings'], first['underruns']) == (6, 2, 1)
  assert first['slow_reads'] == 2 and first['short_audio_seconds'] == 1 and first['max_read_ms'] == 90.0
  assert second['lost_packets'] == 1 and not report.significant(second)


def test_healthy_timing_lines_are_not_windows():
  assert report.windows([timing(BASE)]) == []


def test_event_is_phone_audio_not_android_auto_and_has_no_addresses():
  window = report.windows([rtp(BASE, 12)])[0]
  event = report.dropout_event(window, output='android_auto')
  assert event['fingerprint'] == ['phone-audio', 'dropout'] and event['tags']['component'] == 'phone_audio'
  assert event['tags']['pa.cause_hint'] == 'bluetooth_input' and 'aa.schema' not in event['tags']
  assert '12 Bluetooth packets lost' in event['message']


def test_send_reports_waits_for_quiet_sends_once_and_advances(tmp_path):
  layout = Layout(tmp_path)
  lines = [rtp(BASE + i, 2) for i in range(8)]
  sent = []
  def capture(**event):
    sent.append(event)
    return True
  assert report.send_reports(capture, layout, now=BASE + 9, read=lambda since: lines) == 0  # still in progress
  assert report.send_reports(capture, layout, now=BASE + 30, read=lambda since: lines) == 1
  assert sent[0]['contexts']['phone_audio']['lost_packets'] == 16
  assert report.send_reports(capture, layout, now=BASE + 60, read=lambda since: [l for l in lines if float(l.split()[0]) >= since]) == 0


def test_failed_delivery_is_retried_next_pass(tmp_path):
  layout = Layout(tmp_path)
  lines = [rtp(BASE, 20)]
  assert report.send_reports(lambda **event: False, layout, now=BASE + 30, read=lambda since: lines) == 0
  assert report.send_reports(lambda **event: True, layout, now=BASE + 60, read=lambda since: lines) == 1


def test_background_kernel_bluetooth_noise_never_extends_a_window():
  hci = lambda at: f'{at:.6f} comma kernel: R0: hci0 ACL packet for unknown connection handle 3804'
  lines = [hci(BASE - 5), rtp(BASE, 12), hci(BASE + 2), hci(BASE + 30), hci(BASE + 31)]
  [window] = report.windows(lines)
  assert window['hci_unknown_handle'] == 1 and window['end'] == BASE
