// Bounded mono float32 alert renderer. PCM allocation/publication/reclamation occur on the control thread only.
#define _GNU_SOURCE
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SLOTS 16
#define MAX_PCM 1440000U
#define MAX_FRAMES 4096U
_Static_assert(ATOMIC_LONG_LOCK_FREE == 2 && ATOMIC_LLONG_LOCK_FREE == 2 && ATOMIC_POINTER_LOCK_FREE == 2, "Audio requires lock-free atomics");
struct pa_time { double input_adc, current, output_dac; };
struct bank { uint64_t revision; unsigned lengths[SLOTS]; float *pcm[SLOTS]; };
struct audio {
  struct bank *active;
  _Atomic(struct bank *) pending, retired;
  _Atomic uint64_t command_seq, command[8], status_seq, status[10];
  uint64_t applied_seq, restart, frame, stop_frame;
  uint64_t status_count, underflows, last_flags;
  unsigned alert, sound;
  int loops;
  float gain;
  bool pending_stop;
  atomic_flag rendering;
};
static void free_bank(struct bank *b) { if (b) { for(unsigned i=0;i<SLOTS;i++) free(b->pcm[i]); free(b); } }
unsigned audio_mixer_abi(void) { return 3; }
struct audio *audio_create(void) { struct audio *a=calloc(1,sizeof(*a)); if(a) { *a=(struct audio){.rendering=ATOMIC_FLAG_INIT,.loops=-1}; } return a; }
void audio_collect(struct audio *a) { free_bank(atomic_exchange(&a->retired,NULL)); }
int audio_can_publish(struct audio *a) { return a && atomic_load(&a->pending)==NULL; }
int audio_publish_bank(struct audio *a,const float *const *pcm,const unsigned *lengths,unsigned count,uint64_t revision) {
  if(!a || !revision || count>SLOTS || atomic_load(&a->pending)) return 0;
  audio_collect(a);
  struct bank *b=calloc(1,sizeof(*b)); if(!b) return 0; b->revision=revision;
  for(unsigned i=0;i<count;i++) {
    if(!lengths[i] || lengths[i]>MAX_PCM || !pcm[i]) { free_bank(b); return 0; }
    b->pcm[i]=malloc((size_t)lengths[i]*sizeof(float)); if(!b->pcm[i]) {free_bank(b);return 0;}
    memcpy(b->pcm[i],pcm[i],(size_t)lengths[i]*sizeof(float)); b->lengths[i]=lengths[i];
  }
  atomic_store(&a->pending,b); return 1;
}
uint64_t audio_command(struct audio *a,unsigned alert,unsigned sound,int loops,int stop,float gain,uint64_t restart,uint64_t bank_revision,uint64_t stop_frame) {
  if(!a || sound>=SLOTS || loops < -1 || loops==0 || !isfinite(gain) || gain<0 || gain>1) return 0;
  uint32_t bits;memcpy(&bits,&gain,sizeof(bits));
  uint64_t seq=atomic_load(&a->command_seq);atomic_store(&a->command_seq,seq+1);
  uint64_t values[8]={alert,sound,(uint64_t)(int64_t)loops,stop!=0,bits,restart,bank_revision,stop_frame};
  for(unsigned i=0;i<8;i++) atomic_store(&a->command[i],values[i]);
  atomic_store(&a->command_seq,seq+2); return seq+2;
}
static void accept_command(struct audio *a) {
  uint64_t seq=atomic_load(&a->command_seq),v[8];
  if(seq==a->applied_seq || (seq&1)) return;
  for(unsigned i=0;i<8;i++) v[i]=atomic_load(&a->command[i]);
  if(seq!=atomic_load(&a->command_seq)) return;
  if(!a->active || v[6]!=a->active->revision) {
    struct bank *next=atomic_load(&a->pending);
    if(!next || next->revision!=v[6] || atomic_load(&a->retired)) return;
    next=atomic_exchange(&a->pending,NULL);
    struct bank *old=a->active;a->active=next;atomic_store(&a->retired,old);
  }
  if(v[5]!=a->restart) { a->frame=0;a->restart=v[5]; }
  a->alert=(unsigned)v[0];a->sound=(unsigned)v[1];a->loops=(int)(int64_t)v[2];
  a->pending_stop=v[3]!=0;a->stop_frame=v[7];
  // The main thread may publish dismissal after this cursor has already crossed
  // its observed loop endpoint. Never replay an additional loop in that case.
  if(a->pending_stop && a->frame>=a->stop_frame) { a->alert=0;a->pending_stop=false; }
  uint32_t bits=(uint32_t)v[4];memcpy(&a->gain,&bits,sizeof(bits));a->applied_seq=seq;
}
// Initialization only: caller has not yet opened/started a PortAudio stream.
// Admit the initial bank without rendering samples or publishing fake timing.
int audio_prepare(struct audio *a) {
  if(!a) return 0;
  accept_command(a);
  return a->active!=NULL && a->applied_seq!=0;
}
static int audio_callback(const void *input,void *output,unsigned long frames,const struct pa_time *t,unsigned long flags,void *user) {
  (void)input;(void)t;struct audio *a=user;
  if(!a || !output || frames>MAX_FRAMES || atomic_flag_test_and_set(&a->rendering)) return 2;
  accept_command(a);
  float *out=output;memset(out,0,frames*sizeof(float));
  unsigned length=a->active?a->active->lengths[a->sound]:0;
  if(a->alert && !length) { atomic_flag_clear(&a->rendering);return 2; }
  unsigned written=0;
  while(a->alert && written<frames && (a->loops<0 || a->frame/length<(uint64_t)a->loops)) {
    unsigned pos=(unsigned)(a->frame%length),n=length-pos;
    if(n>frames-written)n=(unsigned)frames-written;
    memcpy(out+written,a->active->pcm[a->sound]+pos,n*sizeof(float));written+=n;a->frame+=n;
    if(a->pending_stop && a->frame%length==0) { a->alert=0;a->pending_stop=false;break; }
  }
  for(unsigned i=0;i<frames;i++) out[i]*=a->gain;
  // Only detached stream health and playback cursor cross the callback boundary.
  uint64_t status_seq=atomic_load(&a->status_seq);atomic_store(&a->status_seq,status_seq+1);
  if(flags) { a->status_count++;a->last_flags=flags; }
  if(flags&4U) a->underflows++;
  atomic_store(&a->status[0],a->frame);atomic_store(&a->status[1],a->alert);atomic_store(&a->status[2],a->pending_stop);
  atomic_store(&a->status[3],a->status_count);atomic_store(&a->status[4],a->underflows);atomic_store(&a->status[5],a->last_flags);
  atomic_store(&a->status[6],1U);atomic_store(&a->status[7],a->applied_seq);
  atomic_store(&a->status[8],a->restart);atomic_store(&a->status[9],a->sound);
  atomic_store(&a->status_seq,status_seq+2);
  atomic_flag_clear(&a->rendering);return 0;
}
uintptr_t audio_callback_address(void) { return (uintptr_t)&audio_callback; }
int audio_status(struct audio *a,uint64_t *out) {
  if(!a || !out) return 0;
  for(unsigned attempt=0;attempt<3;attempt++) {
    uint64_t seq=atomic_load(&a->status_seq);if(seq&1)continue;
    for(unsigned i=0;i<10;i++)out[i]=atomic_load(&a->status[i]);
    if(seq==atomic_load(&a->status_seq))return 1;
  }
  return 0;
}
// Caller MUST stop/close PortAudio before destroying this stream-owned mixer.
void audio_destroy(struct audio *a) { if(a) {free_bank(a->active);free_bank(atomic_load(&a->pending));free_bank(atomic_load(&a->retired));free(a);} }
