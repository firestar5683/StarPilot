"""Seed-aware semantic plan contract and cache. No device/route access or audio generation.

Normal-session callers supply a fresh session seed (or explicit/judging seed), the
current section intent, and only already-generated musical context. A preparation
adapter must return real planner-conditioned tensors; prompt edits are not assets.
"""
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

VERSION = 'roadscore-hook-plan-v2'
PROFILES = {
    'prism': {'bpm': 128, 'keyscale': 'D minor', 'identity':
              'Polished instrumental K-pop and modern electronic game score; crystal pluck '
              'arpeggios, bright glass synth leads, punchy syncopated bass and tight electronic drums.'},
    'aurora': {'bpm': 116, 'keyscale': 'A minor', 'identity':
               'Instrumental melodic game score; warm analog synths, shimmering bell answers, '
               'octave bass ostinato and syncopated dance-pop drums.'},
}
HOOK = (
    'Build this composition around one distinctive compact four-to-six-note melodic hook '
    'with a recognizable rhythmic signature and an answering phrase. Choose its notes and '
    'contour for this composition. Establish it clearly, leave breathing space, and preserve '
    'that SAME melodic and rhythmic identity across subsequent sections. Develop accompaniment, '
    'register, articulation and dynamics rather than substituting unrelated lead melodies or '
    'mechanically repeating an unchanged loop. When established musical reference is supplied, '
    'continue its actual hook rather than inventing a replacement. '
)
ROLES = {
    'initial': 'Introduce the new composition\'s memorable hook and its answer, establish the groove, then develop it into an open-ended verse. ',
    'verse': 'Use recognizable hook fragments and a lighter call-and-response over an active groove. Develop accompaniment while leaving space for the full melody to return. ',
    'prechorus': 'Build tension with shorter fragments of the same hook, rising register and denser subdivisions; aim toward a chorus without inventing a new main melody. ',
    'chorus': 'Bring back the complete established hook prominently with its signature rhythm, fuller bass and drums, and a wider-register answer. Deliver a melodic payoff, not just louder texture. ',
    'bridge': 'Contrast the arrangement with a spacious rhythmic or register transformation of the same hook in compatible timbre and harmony, then prepare its recognizable return. ',
    'outro': 'Return to the recognizable original hook, answer and resolve it; thin the arrangement and allow an intentional closing fade. ',
}
FORM_CYCLE = ('verse', 'prechorus', 'chorus', 'verse', 'bridge', 'chorus')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _hex_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def planner_seed(session_seed, plan_index, profile):
    if type(session_seed) is not int or not 0 <= session_seed < 2**32:
        raise ValueError('A caller-supplied unsigned32 session seed is required; no fixed default')
    if type(plan_index) is not int or plan_index < 0:
        raise ValueError('plan_index must be nonnegative')
    if profile not in PROFILES:
        raise ValueError('Unsupported musical profile')
    value = f'roadscore-semantic-plan-v1:{session_seed}:{plan_index}:{profile}'
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:4], 'big')


def next_section(completed_continuations, *, arrival_intent=False):
    """Fallback intent only; no route duration or future event schedule is accepted."""
    if type(completed_continuations) is not int or completed_continuations < 0:
        raise ValueError('Invalid completed section count')
    return 'outro' if arrival_intent else FORM_CYCLE[completed_continuations % len(FORM_CYCLE)]


@dataclass(frozen=True)
class PlanRequest:
    version: str
    session_seed: int
    semantic_seed: int
    plan_index: int
    profile: str
    section: str
    window_seconds: int
    prefix_seconds: int
    bpm: int
    keyscale: str
    caption: str
    lyrics: str
    model_fingerprint: str
    preparation_fingerprint: str
    hook_reference_sha256: str | None
    committed_prefix_sha256: str | None
    previous_plan_sha256: str | None

    def identity(self):
        return asdict(self)

    @property
    def cache_key(self):
        return hashlib.sha256(json.dumps(self.identity(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def request_plan(*, session_seed, plan_index, profile, section, window_seconds,
                 model_fingerprint, preparation_fingerprint, hook_reference_sha256=None,
                 committed_prefix_sha256=None, previous_plan_sha256=None):
    semantic_seed = planner_seed(session_seed, plan_index, profile)
    if section not in ROLES or window_seconds not in (30, 45, 60):
        raise ValueError('Unknown section or unvalidated window shape')
    for value in (model_fingerprint, preparation_fingerprint):
        if not _hex_digest(value):
            raise ValueError('Exact model/preparation fingerprints required')
    context = (hook_reference_sha256, committed_prefix_sha256, previous_plan_sha256)
    if plan_index == 0:
        if section != 'initial' or any(value is not None for value in context):
            raise ValueError('Initial plan must establish a new hook without prior-session context')
        prefix = 0
    else:
        if section == 'initial' or not all(_hex_digest(value) for value in context):
            raise ValueError('Continuation needs current-session hook, committed prefix and prior plan identities')
        prefix = 8
    family = PROFILES[profile]
    caption = (family['identity'] + f" {family['bpm']} BPM, {family['keyscale']}, 4/4. No vocals, singing or speech. "
               + HOOK + ROLES[section])
    if section != 'outro':
        caption += ('This window is part of an ongoing composition, not a whole short song: '
                    'keep an audible groove and hand off naturally without an ending, terminal fade or silence. ')
    return PlanRequest(VERSION, session_seed, semantic_seed, plan_index, profile, section,
                       window_seconds, prefix, family['bpm'], family['keyscale'], caption,
                       '[Instrumental]\n[' + ('Intro' if section == 'initial' else 'Pre-Chorus' if section == 'prechorus' else section.title()) + ']',
                       model_fingerprint, preparation_fingerprint, *context)


def validate_sources(request, sources):
    """Adapter receives verified present audio context, never a recorded future route."""
    expected = {'hook_reference': request.hook_reference_sha256,
                'committed_prefix': request.committed_prefix_sha256}
    if set(sources) != {key for key, value in expected.items() if value is not None}:
        raise ValueError('Missing/unexpected musical source files')
    for key, path in sources.items():
        if digest(path) != expected[key]:
            raise ValueError(f'Musical context changed: {key}')


def validate_prepared(request, directory, sources=None):
    """Reject strings-only, stale, or unplanned artifacts before native consumption."""
    directory = Path(directory)
    record = json.loads((directory / 'prepared.json').read_text())
    if record.get('request_key') != request.cache_key or record.get('semantic_seed') != request.semantic_seed:
        raise ValueError('Prepared plan belongs to another request/seed')
    if record.get('semantic_plan_present') is not True or record.get('audio_diffusion_called') is not False:
        raise ValueError('Adapter must attest captured semantic planning before diffusion')
    plan = json.loads((directory / 'semantic_plan.json').read_text())
    if not plan.get('audio_codes') or plan.get('semantic_seed') != request.semantic_seed:
        raise ValueError('Actual semantic codes missing; prompt changes alone are not a plan')
    names = ['encoder_hidden_states.npy', 'encoder_attention_mask.npy', 'context_latents.npy',
             'semantic_plan.json', 'prepared.json']
    encoder, mask, context = [np.load(directory / name, allow_pickle=False) for name in names[:3]]
    n = request.window_seconds * 25
    if encoder.ndim != 3 or encoder.shape[0] != 1 or encoder.shape[2] != 2048:
        raise ValueError('Invalid native encoder shape')
    if mask.shape != encoder.shape[:2] or not np.isin(mask, [0, 1]).all() or not mask.any():
        raise ValueError('Invalid native attention mask')
    if context.shape != (1, n, 128) or not all(np.isfinite(a).all() for a in (encoder, mask, context)):
        raise ValueError('Invalid native context or non-finite tensor')
    if request.prefix_seconds:
        names += ['sampler_repaint_mask.npy', 'sampler_clean_src_latents.npy', 'sampler.json']
        repaint = np.load(directory / names[-3], allow_pickle=False)
        source = np.load(directory / names[-2], allow_pickle=False)
        boundary = request.prefix_seconds * 25
        if repaint.shape != (1, n) or not np.isin(repaint, [0, 1]).all() or not np.array_equal(repaint.astype(bool), np.arange(n)[None, :] >= boundary):
            raise ValueError('Expected exact8-second preserved prefix and generated remainder')
        if source.shape != (1, n, 64) or not np.isfinite(source).all():
            raise ValueError('Invalid continuation source latent')
        if sources is None:
            raise ValueError('Actual committed prefix required to verify continuation')
        prefix = np.load(sources['committed_prefix'], allow_pickle=False)
        if prefix.shape != (1, boundary, 64) or not np.array_equal(source[:, :boundary], prefix) or not np.array_equal(context[:, :boundary, :64], prefix):
            raise ValueError('Prepared continuation does not preserve the requested actual musical prefix')
        sampler = json.loads((directory / 'sampler.json').read_text())
        if sampler.get('repaint_crossfade_frames') != 12 or sampler.get('repaint_injection_ratio') != .5:
            raise ValueError('Unexpected native repaint policy')
    elif (directory / 'sampler_repaint_mask.npy').exists():
        raise ValueError('Initial plan must not reuse an old repaint prefix')
    return {name: digest(directory / name) for name in names}


class PlanCache:
    """Caller supplies the real host adapter. One locked prepare per exact request.

    `prepare(request, verified_sources, staging_directory)` must write the files
    validated above. There is intentionally no fallback to a generic cached hook.
    """
    def __init__(self, root):
        self.root = Path(root)

    def resolve(self, request, prepare, *, sources=None):
        sources = sources or {}
        validate_sources(request, sources)
        self.root.mkdir(parents=True, exist_ok=True)
        key = request.cache_key
        final = self.root / key
        with (self.root / (key + '.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if final.exists():
                manifest = json.loads((final / 'cache.json').read_text())
                hashes = validate_prepared(request, final, sources)
                if manifest.get('request') != request.identity() or manifest.get('sha256') != hashes:
                    raise ValueError('Plan cache corrupted; do not silently replace musical context')
                return final, True
            staging = Path(tempfile.mkdtemp(prefix=key + '.', dir=self.root))
            try:
                prepare(request, sources, staging)
                validate_sources(request, sources)
                hashes = validate_prepared(request, staging, sources)
                # Only planning tensors/metadata are cached; no PCM from an earlier performance.
                extra = set(p.name for p in staging.iterdir()) - set(hashes)
                if extra:
                    raise ValueError(f'Unexpected assets in semantic cache: {sorted(extra)}')
                (staging / 'cache.json').write_text(json.dumps({'request': request.identity(), 'sha256': hashes}, indent=2))
                staging.rename(final)
                return final, False
            except BaseException:
                shutil.rmtree(staging)
                raise
