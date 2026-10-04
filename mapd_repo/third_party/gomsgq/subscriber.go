package gomsgq

import (
	"math/rand/v2"
	"os"
	"unsafe"

	"sync/atomic"
)

type MsgqSubscriber struct {
	Shadow                bool
	Msgq                  Msgq
	Uid                   uint64
	Id                    uint64
	Conflate              bool
	shadowPointer         uint64
	previousShadowPointer uint64
	shadowReset           bool
}

func generateUid() uint64 {
	return uint64(rand.Uint32())<<32 | uint64(os.Getpid())
}

func (s *MsgqSubscriber) Init(msgq Msgq) {
	s.Msgq = msgq
	s.Uid = generateUid()
	if !s.Shadow {
		for {
			curNumReaders := *s.Msgq.Header.NumReaders
			newNumReaders := curNumReaders + 1
			if newNumReaders > NUM_READERS {
				*s.Msgq.Header.NumReaders = 0

				for i := range NUM_READERS {
					s.Msgq.Header.ReadValids[i] = 0

					old_uid := s.Msgq.Header.ReadUids[i]
					s.Msgq.Header.ReadUids[i] = 0

					ThreadSignal(uint32(old_uid & 0xFFFFFFFF))
				}
				continue
			}
			if atomic.CompareAndSwapUint64(s.Msgq.Header.NumReaders, curNumReaders, newNumReaders) {
				s.Id = curNumReaders
				s.Msgq.Header.ReadValids[curNumReaders] = 0
				s.Msgq.Header.ReadPointers[curNumReaders] = 0
				s.Msgq.Header.ReadUids[curNumReaders] = s.Uid
				break
			}
		}
	}
	s.Reset()
}

func (s *MsgqSubscriber) ShadowValid(writePointer Pointer) bool {
	readPointer := NewPointer(s.shadowPointer)

	if !s.shadowReset {
		previousReadPointer := NewPointer(s.previousShadowPointer)
		previousSize := *(*int64)(unsafe.Pointer(&s.Msgq.Data[previousReadPointer.Position]))

		if previousSize == -1 && readPointer.Position != 0 {
			return false
		}

		if previousSize != -1 {
			calculatedCurrentReadPointer := previousReadPointer.Next(previousSize)

			if readPointer.Position != calculatedCurrentReadPointer.Position {
				return false
			}
		}
	}

	if readPointer.Cycles != writePointer.Cycles && readPointer.Position <= writePointer.Position {
		return false
	}

	if readPointer.Cycles != writePointer.Cycles && readPointer.Position > s.Msgq.WraparoundPosition() {
		return false
	}

	if readPointer.Cycles == writePointer.Cycles && readPointer.Position > writePointer.Position {
		return false
	}

	return true
}

func (s *MsgqSubscriber) Reset() {
	if !s.Shadow {
		s.Msgq.Header.ReadValids[s.Id] = 1
		s.Msgq.Header.ReadPointers[s.Id] = *s.Msgq.Header.WritePointer
	} else {
		s.shadowPointer = *s.Msgq.Header.WritePointer
		s.shadowReset = true
	}
}

func (s *MsgqSubscriber) Ready() bool {
	if !s.Shadow {
		for s.Uid != s.Msgq.Header.ReadUids[s.Id] {
			s.Init(s.Msgq)
		}

		for s.Msgq.Header.ReadValids[s.Id] == 0 {
			s.Reset()
		}

		readPointer := NewPointer(s.Msgq.Header.ReadPointers[s.Id])

		writePointer := NewPointer(*s.Msgq.Header.WritePointer)

		return readPointer.Position != writePointer.Position
	} else {
		for {
			readPointer := NewPointer(s.shadowPointer)
			writePointer := NewPointer(*s.Msgq.Header.WritePointer)

			if !s.ShadowValid(writePointer) {
				s.Reset()
				continue
			}

			return readPointer.Position != writePointer.Position
		}

	}
}

func (s *MsgqSubscriber) Read() []byte {
	if !s.Ready() {
		return nil
	}

	for {
		var readPointer Pointer
		if s.Shadow {
			readPointer = NewPointer(s.shadowPointer)
		} else {
			readPointer = NewPointer(s.Msgq.Header.ReadPointers[s.Id])
		}
		if s.Shadow {
			writePointer := NewPointer(*s.Msgq.Header.WritePointer)
			if !s.ShadowValid(writePointer) {
				s.Reset()
				continue
			}
		}
		size := *(*int64)(unsafe.Pointer(&s.Msgq.Data[readPointer.Position]))

		if size == -1 {
			readPointer.Cycle()
			if s.Shadow {
				s.previousShadowPointer = s.shadowPointer
				s.shadowReset = false
				s.shadowPointer = readPointer.Marshal()
			} else {
				s.Msgq.Header.ReadPointers[s.Id] = readPointer.Marshal()
			}
			continue
		}

		if size >= s.Msgq.Size || size <= 0 {
			if s.Shadow || s.Conflate {
				s.Reset()
				continue
			}

			panic("Invalid Msgq message size")
		}

		nextReadPointer := readPointer.Next(size)
		if s.Conflate {
			writePointer := NewPointer(*s.Msgq.Header.WritePointer)
			if nextReadPointer.Position != writePointer.Position {
				if s.Shadow {
					s.previousShadowPointer = s.shadowPointer
					s.shadowReset = false
					s.shadowPointer = nextReadPointer.Marshal()
				} else {
					s.Msgq.Header.ReadPointers[s.Id] = nextReadPointer.Marshal()
				}
				continue
			}
		}

		err := s.Msgq.Mem.Flush()
		if err != nil {
			panic("Msgq Flush Error")
		}
		result := make([]byte, size)
		for i := range size {
			result[i] = s.Msgq.Data[int64(readPointer.Position)+8+i]
		}
		err = s.Msgq.Mem.Flush()
		if err != nil {
			panic("Msgq Flush Error")
		}

		if s.Shadow {
			s.previousShadowPointer = s.shadowPointer
			s.shadowPointer = nextReadPointer.Marshal()
		} else {
			s.Msgq.Header.ReadPointers[s.Id] = nextReadPointer.Marshal()
		}

		if !s.Shadow && s.Msgq.Header.ReadValids[s.Id] == 0 {
			s.Reset()
			continue
		}

		return result
	}
}
