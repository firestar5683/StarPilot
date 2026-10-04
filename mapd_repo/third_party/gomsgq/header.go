package gomsgq

import (
	"unsafe"

	"github.com/edsrzf/mmap-go"
)

type Header struct {
	NumReaders   *uint64
	WritePointer *uint64
	WriteUid     *uint64
	ReadPointers []uint64
	ReadValids   []uint64
	ReadUids     []uint64
}

func (h *Header) Init(m mmap.MMap) {
	h.NumReaders = (*uint64)(unsafe.Pointer(&m[0]))
	h.WritePointer = (*uint64)(unsafe.Pointer(&m[8]))
	h.WriteUid = (*uint64)(unsafe.Pointer(&m[16]))
	readPointers := unsafe.Slice((*uint64)(unsafe.Pointer(&m[24])), NUM_READERS)
	h.ReadPointers = readPointers
	readValids := unsafe.Slice((*uint64)(unsafe.Pointer(&m[24+NUM_READERS*8])), NUM_READERS)
	h.ReadValids = readValids
	readUids := unsafe.Slice((*uint64)(unsafe.Pointer(&m[24+2*NUM_READERS*8])), NUM_READERS)
	h.ReadUids = readUids
}
