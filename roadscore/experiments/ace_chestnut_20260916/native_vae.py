"""ACE Oobleck decoder, folded weight normalization and explicit precision boundary."""
from pathlib import Path
import numpy as np
from tinygrad import TinyJit
from native_ace import tensor
class VAE:
 def __init__(self,path):self.w={p.stem:tensor(np.load(p)) for p in sorted(Path(path).glob('*.npy'))}
 def snake(self,x,p):
  z=x.float();a=self.w[p+'.alpha'].float().exp();b=self.w[p+'.beta'].float().exp()
  return (z+(a*z).sin().square()/(b+1e-9)).cast(x.dtype)
 def conv(self,x,p,padding=0,dilation=1):return x.conv2d(self.w[p+'.weight'],self.w.get(p+'.bias'),padding=padding,dilation=dilation).realize()
 def residual(self,x,p,d):
  y=self.conv(self.snake(x,p+'.snake1'),p+'.conv1',3*d,d)
  return (x+self.conv(self.snake(y,p+'.snake2'),p+'.conv2')).realize()
 def forward(self,x):
  x=self.conv(x,'conv1',3)
  for i,stride in enumerate([10,6,4,4,2]):
   p=f'block.{i}';x=self.snake(x,p+'.snake1').conv_transpose2d(self.w[p+'.conv_t1.weight'],self.w[p+'.conv_t1.bias'],stride=stride,padding=(stride+1)//2).realize()
   for j,d in enumerate([1,3,9]):x=self.residual(x,p+f'.res_unit{j+1}',d)
  return self.conv(self.snake(x,'snake1'),'conv2',3)
