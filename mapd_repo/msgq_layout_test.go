package main

import (
	"os"
	"regexp"
	"strconv"
	"testing"
	"unsafe"

	"github.com/edsrzf/mmap-go"
	"github.com/pfeiferj/gomsgq"
)

func TestMsgqNativeLayout(t *testing.T) {
	source, err := os.ReadFile("../msgq_repo/msgq/msgq.h")
	if err != nil {
		t.Fatal(err)
	}
	match := regexp.MustCompile(`(?m)^#define NUM_READERS ([0-9]+)$`).FindSubmatch(source)
	if len(match) != 2 {
		t.Fatal("native reader layout missing")
	}
	count, err := strconv.Atoi(string(match[1]))
	if err != nil {
		t.Fatal(err)
	}
	if gomsgq.NUM_READERS != count || gomsgq.HEADER_SIZE != int64(24+24*count) {
		t.Fatalf("Go/native msgq ABI differs: Go readers=%d bytes=%d native readers=%d", gomsgq.NUM_READERS, gomsgq.HEADER_SIZE, count)
	}
	mem := make(mmap.MMap, gomsgq.HEADER_SIZE+8)
	var header gomsgq.Header
	header.Init(mem)
	for index := range count {
		header.ReadPointers[index] = uint64(index + 1)
		header.ReadValids[index] = uint64(index + 101)
		header.ReadUids[index] = uint64(index + 201)
		for column, expected := range []uint64{uint64(index + 1), uint64(index + 101), uint64(index + 201)} {
			actual := *(*uint64)(unsafe.Pointer(&mem[24+8*(column*count+index)]))
			if actual != expected {
				t.Fatalf("reader %d column %d wrong offset", index, column)
			}
		}
	}
	if *(*uint64)(unsafe.Pointer(&mem[gomsgq.HEADER_SIZE])) != 0 {
		t.Fatal("reader metadata overlaps payload")
	}
}
