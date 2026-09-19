"""Shared musical intent for a candidate; this alone does not change prepared tensors."""
import hashlib
import json

VERSION = 'prism-hook-v1'
IDENTITY = (
    'Instrumental polished K-pop and modern electronic game score. No vocals, singing or speech. '
    '128 BPM, D minor, 4/4. Tight electronic drums, punchy rubbery syncopated bass, '
    'crystal pluck arpeggios and bright glass synth leads. '
)
HOOK = (
    'Give this composition one distinctive, immediately memorable four-note rising synth hook '
    'with a catchy syncopated rhythm and a short answering phrase. Establish its recognizable '
    'melodic contour and rhythm early. Keep that SAME hook identity throughout this song: '
    'develop its rhythm, register, accompaniment and dynamics, then bring back the clear original '
    'phrase at each chorus. Make the motif specific to this composition, not a generic running '
    'arpeggio. Leave breathing space between hook statements. Do not replace it with unrelated '
    'lead melodies or mechanically repeat an unchanged loop. '
)
ROLES = {
    'initial': 'Introduce the hook clearly, develop a lighter verse, rise into a build and deliver a confident first chorus. ',
    'verse': 'Develop a lighter verse using recognizable fragments and a quieter call-and-response of the established hook over an active bass groove. Vary the accompaniment and leave space for the hook return. ',
    'prechorus': 'Build tension with shorter recognizable hook fragments, rising register and denser drum subdivisions. Aim the phrase toward the chorus; do not introduce a new main melody. ',
    'chorus': 'State the complete established hook prominently with its original contour and signature rhythm; answer it with the same phrase in a wider register and fuller bass/drums. Make this a clear melodic payoff, not merely louder texture. ',
    'bridge': 'Create contrast by reducing the arrangement and transforming the same hook into a spacious half-time rhythmic answer in compatible glass/pluck timbre. Retain its melodic identity and D minor harmony, then rebuild toward the original chorus hook. ',
    'outro': 'Return to the recognizable complete hook, answer and resolve its last phrase, then thin the arrangement into a gentle intentional conclusion. ',
}
TIMELINE = [
    ('initial', 2, 'Clear hook introduction'),
    ('verse', 8, 'Hook fragments and lighter call-and-response'),
    ('prechorus', 4, 'Rising fragment development'),
    ('chorus', 8, 'Complete hook and melodic payoff'),
    ('bridge', 4, 'Contrasting transformation of same motif'),
    ('chorus', 4, 'Recognizable original hook reprise'),
    ('outro', 2, 'Motif answer and resolution'),
]


def spec(route_seed=None):
    if route_seed is not None and (type(route_seed) is not int or not 0 <= route_seed < 2**32):
        raise ValueError('route_seed must be an unsigned 32-bit integer')
    seed = 33602 if route_seed is None else int.from_bytes(
        hashlib.sha256(f'roadscore-sample-v1:{route_seed}:prepare:0'.encode()).digest()[:4], 'big')
    interior = 'This is a continuing interior section: preserve the pulse and hand off naturally without a terminal fade or silence. '
    prompts = {role: IDENTITY + HOOK + text + (interior if role not in ('initial', 'outro') else '')
               for role, text in ROLES.items()}
    cursor = 0
    timeline = []
    for role, bars, intent in TIMELINE:
        duration = bars * 4 * 60 / 128
        timeline.append({'role': role, 'bars': bars, 'start_seconds': cursor,
                         'end_seconds': cursor + duration, 'intent': intent})
        cursor += duration
    result = {
        'version': VERSION, 'profile': 'prism', 'bpm': 128, 'keyscale': 'D minor', 'timesignature': '4',
        'duration': 60, 'seed': seed, 'seed_mode': 'fixed-reference' if route_seed is None else 'route-derived',
        'route_seed': route_seed, 'thinking': True, 'role_captions': prompts,
        'role_lyrics': {r: '[Instrumental]\n[' + ('Pre-Chorus' if r == 'prechorus' else r.title()) + ']'
                        for r in ROLES if r != 'initial'},
        'caption': IDENTITY + HOOK + (
            'Compose a coherent one-minute arc: establish the hook, develop a lighter verse, '
            'build anticipation, reveal a full chorus, give a brief contrasting bridge variation, '
            'then reprise the original hook and resolve naturally. Each section should change '
            'the musical arrangement while retaining the song\'s identity. '),
        'lyrics': '[Instrumental]\n[Intro]\n[Verse]\n[Pre-Chorus]\n[Chorus]\n[Bridge]\n[Chorus]\n[Outro]',
        'desired_timeline': timeline,
        'timeline_status': '32-bar intent at 128 BPM, not verified generated section boundaries; never force cuts to these timestamps',
        'continuation_policy': 'role contracts only; no prepared continuation tensors or runtime deployment claimed',
        'uniqueness_limit': 'Distinct hook is musical intent, not a metric guarantee; fixed seeds intentionally reproduce a composition.',
    }
    result['caption'] += ('Target a 32-bar arc: 2-bar introduction, 8-bar verse, 4-bar build, '
                          '8-bar chorus, 4-bar bridge variation, 4-bar chorus reprise and 2-bar resolution. ')
    result['role_lyrics']['initial'] = result['lyrics']
    result['spec_sha256'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    return result
