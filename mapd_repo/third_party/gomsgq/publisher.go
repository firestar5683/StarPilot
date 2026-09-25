package gomsgq

import (
	"unsafe"
)

type MsgqPublisher struct {
	Msgq Msgq
	Uid  uint64
	Id   uint64
}

func (p *MsgqPublisher) Init(msgq Msgq) {
	p.Msgq = msgq
	p.Uid = generateUid()

	*p.Msgq.Header.NumReaders = 0
	*p.Msgq.Header.WriteUid = p.Uid
	*p.Msgq.Header.WritePointer = 0

	for i := range NUM_READERS {
		p.Msgq.Header.ReadValids[i] = 0
		p.Msgq.Header.ReadUids[i] = 0
	}
}

func (p *MsgqPublisher) Send(data []byte) {
	if p.Uid != *p.Msgq.Header.WriteUid {
		panic("We are not the active Msgq publisher, panic")
	}
	totalSize := int64(len(data)+8) + align(int64(len(data)))
	if totalSize*3 >= p.Msgq.Size {
		panic("Msgq size too small, panic")
	}
	numReaders := *p.Msgq.Header.NumReaders
	writePointer := NewPointer(*p.Msgq.Header.WritePointer)
	remainingSpace := p.Msgq.Size - int64(writePointer.Position) - totalSize - 8

	// Invalidate all readers that are beyond the write pointer
	if remainingSpace <= 0 {
		// write -1 size tag indicating wraparound
		*(*int64)(unsafe.Pointer(&p.Msgq.Data[writePointer.Position])) = int64(-1)
		for i := range numReaders {
			readPointer := NewPointer(p.Msgq.Header.ReadPointers[i])
			if readPointer.Position > writePointer.Position && readPointer.Cycles != writePointer.Cycles {
				p.Msgq.Header.ReadValids[i] = 0 //false
			}
		}
		writePointer.Position = 0
		writePointer.Cycles += 1
		*p.Msgq.Header.WritePointer = writePointer.Marshal()
	}

	// Invalidate readers that are in the area that will be written
	end := writePointer.Position + uint64(totalSize)
	for i := range numReaders {
		readPointer := NewPointer(p.Msgq.Header.ReadPointers[i])

		if readPointer.Position >= writePointer.Position && readPointer.Position < end && readPointer.Cycles != writePointer.Cycles {
			p.Msgq.Header.ReadValids[i] = 0 //false
		}
	}

	// Write size tag
	*(*int64)(unsafe.Pointer(&p.Msgq.Data[writePointer.Position])) = int64(len(data))

	// Copy data
	for i, b := range data {
		p.Msgq.Data[int(writePointer.Position)+8+i] = b
	}

	// Update write pointer
	writePointer.Position += uint64(totalSize)
	*p.Msgq.Header.WritePointer = writePointer.Marshal()

	// Notify readers
	for i := range numReaders {
		rUid := p.Msgq.Header.ReadUids[i]
		ThreadSignal(uint32(rUid))
	}
}
