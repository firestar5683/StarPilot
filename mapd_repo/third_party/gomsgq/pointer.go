package gomsgq

type Pointer struct {
	Position uint64
	Cycles   uint64
}

func (p *Pointer) Marshal() uint64 {
	return p.Position | (p.Cycles << 32)
}

func (p *Pointer) Cycle() {
	p.Position = 0
	p.Cycles++
}

func (p *Pointer) Next(size int64) Pointer {
	newPosition := p.Position + uint64(size) + uint64(align(size)) + 8
	return Pointer{
		Position: newPosition,
		Cycles:   p.Cycles,
	}
}

func NewPointer(value uint64) Pointer {
	return Pointer{
		Position: value & 0xFFFFFFFF,
		Cycles:   value >> 32,
	}
}
