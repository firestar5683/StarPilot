"""Check official prefix-delay mapping and cached continuation logits after prompt replacement."""
import gc,json,time
from pathlib import Path
import numpy as np
import torch
from transformers import AutoProcessor,MusicgenForConditionalGeneration
from tinygrad import Tensor
from native_decoder import NativeDecoder
ROOT=Path('/data/roadscore-feasibility');OUT=ROOT/'controllability'
result=json.loads((OUT/'result.json').read_text())
torch.set_num_threads(4)
path=str(ROOT/'musicgen-small-fp16')
model=MusicgenForConditionalGeneration.from_pretrained(path,local_files_only=True,torch_dtype=torch.float16,low_cpu_mem_usage=True,attn_implementation='eager').eval()
processor=AutoProcessor.from_pretrained(path,local_files_only=True)
model.text_encoder.float();model.enc_to_dec_proj.float()
checks={};inputs={};conditions={};refs={}
prompt_lengths={name:len(processor.tokenizer(prompt)['input_ids']) for name,prompt in result['prompts'].items()}
assert max(prompt_lengths.values())<=64, prompt_lengths
(OUT/'prompt_token_lengths.json').write_text(json.dumps(prompt_lengths,indent=2))
with torch.no_grad():
  for name in ['neutral','low','high','release']:
    parent='high' if name=='release' else 'base'
    prefix=torch.load(OUT/f'{parent}_codes.pt',weights_only=True)[...,-400:]
    child=torch.load(OUT/f'{name}_codes.pt',weights_only=True)
    assert torch.equal(child[...,:400],prefix)
    initial,mask=model.decoder.build_delay_pattern_mask(torch.cat([torch.full((4,1),2048,dtype=torch.long),prefix.reshape(4,400)],1),2048,804)
    manual=torch.full((4,804),-1,dtype=torch.long)
    for c in range(4):
      manual[c,:c+1]=2048;manual[c,c+1:c+401]=prefix[0,0,c];manual[c,801+c:]=2048
    assert torch.equal(manual,mask)
    checks[name]={'exact_prefix_codes':True,'official_delay_mask_equal':True}
    if name not in ['low','high']:continue
    # Shorten the test prefix to 8 frames, then check four sampled continuation inputs.
    # Retain actual generated token inputs but rebuild official BOS/delay positions.
    short=prefix[...,:8].reshape(4,8)
    _,shortmask=model.decoder.build_delay_pattern_mask(torch.cat([torch.full((4,1),2048,dtype=torch.long),short],1),2048,32)
    seq=shortmask[:,:16].clone()
    replacement=child.reshape(4,-1)[:,400:416]
    seq=torch.where(seq==-1,replacement,seq)
    inputs[name]=seq.repeat(2,1)
    txt=processor(text=[result['prompts'][name]],padding='max_length',max_length=64,truncation=True,return_tensors='pt')
    enc=model.text_encoder(**txt).last_hidden_state
    enc=model.enc_to_dec_proj(torch.cat([enc,torch.zeros_like(enc)],0))
    mask=torch.cat([txt['attention_mask'],torch.zeros_like(txt['attention_mask'])],0)
    enc=(enc*mask[...,None]).half();conditions[name]=(enc,mask)
    refs[name]=model.decoder(input_ids=inputs[name],encoder_hidden_states=enc,encoder_attention_mask=mask,use_cache=True).logits[:,-4:].float().numpy()
  native=NativeDecoder(model.decoder,*conditions['low'],32)
  del model;gc.collect()
  for name in ['low','high']:
    enc,mask=conditions[name]
    native.enc.assign(Tensor(enc.numpy(),device='AMD')).realize()
    native.mask.assign(Tensor(((1-mask.numpy())*-65504.).astype(np.float16),device='AMD').reshape(2,1,1,-1)).realize()
    for i,(k,v) in enumerate(native.cross):
      p=f'model.decoder.layers.{i}.encoder_attn.'
      k.assign(native.linear(native.enc,p+'k_proj').reshape(2,-1,16,64).transpose(1,2)).realize()
      v.assign(native.linear(native.enc,p+'v_proj').reshape(2,-1,16,64).transpose(1,2)).realize()
    raws=[]
    for pos in range(16):
      raw=native(inputs[name][:,pos:pos+1],pos)
      if pos>=12: raws.append(raw)
    raw=np.stack(raws,axis=1);ref=refs[name]
    checks[name]['cached_continuation_cosine']=float(np.dot(raw.ravel(),ref.ravel())/(np.linalg.norm(raw)*np.linalg.norm(ref)))
    checks[name]['cached_continuation_mae']=float(np.abs(raw-ref).mean())
    assert checks[name]['cached_continuation_cosine']>.999,checks[name]
    print(name,checks[name],flush=True)
(OUT/'validation.json').write_text(json.dumps(checks,indent=2))
divergence={}
for a,b in [('neutral','low'),('neutral','high'),('low','high')]:
  ca=torch.load(OUT/f'{a}_codes.pt',weights_only=True)[...,400:]
  cb=torch.load(OUT/f'{b}_codes.pt',weights_only=True)[...,400:]
  divergence[f'{a}_vs_{b}']=float((ca!=cb).float().mean())
(OUT/'token_divergence.json').write_text(json.dumps(divergence,indent=2))
print('CONTINUATION_CHECKS_PASSED',flush=True)
