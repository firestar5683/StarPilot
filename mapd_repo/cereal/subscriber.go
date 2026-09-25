package cereal

import (
	"capnproto.org/go/capnp/v3"
	"github.com/pfeiferj/gomsgq"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/settings"
)

type Reader[T any] func(log.Event) (T, error)

type Subscriber[T any] struct {
	Sub       gomsgq.MsgqSubscriber
	reader    Reader[T]
	readBytes func() []byte
	maxBytes  int
}

type DecodedEvent[T any] struct {
	Value       T
	Valid       bool
	LogMonoTime uint64
}

func (s *Subscriber[T]) ReadEvent() (result DecodedEvent[T], success bool) {
	// Generated union accessors panic on a different Event variant. An IPC
	// message with the wrong discriminant is a decode failure, not a process
	// crash.
	defer func() {
		if recover() != nil {
			result = DecodedEvent[T]{}
			success = false
		}
	}()
	read := s.readBytes
	if read == nil {
		read = s.Sub.Read
	}
	data := read()
	if len(data) == 0 || (s.maxBytes > 0 && len(data) > s.maxBytes) {
		return result, false
	}
	msg, err := capnp.Unmarshal(data)
	if err != nil {
		return result, false
	}

	// Bound traversal even for malformed pointer graphs. The limit scales with
	// the service's message size so large modelV2 events remain readable.
	msg.ResetReadLimit(uint64(len(data)) * 16)

	event, err := log.ReadRootEvent(msg)
	if err != nil {
		return result, false
	}

	result.Value, err = s.reader(event)
	if err != nil {
		return result, false
	}
	result.Valid = event.Valid()
	result.LogMonoTime = event.LogMonoTime()
	return result, true
}

// Read retains the established value-only API for car, model, and CLI users.
func (s *Subscriber[T]) Read() (obj T, success bool) {
	event, success := s.ReadEvent()
	return event.Value, success
}

func NewSubscriber[T any](name string, reader Reader[T], conflate bool, shadow bool) (subscriber Subscriber[T]) {
	msgq := gomsgq.Msgq{}
	err := msgq.Init(name, settings.GetSegmentSize(name))
	if err != nil {
		panic(err)
	}
	sub := gomsgq.MsgqSubscriber{}
	sub.Conflate = conflate
	sub.Shadow = shadow
	sub.Init(msgq)

	subscriber.Sub = sub
	subscriber.reader = reader
	subscriber.maxBytes = int(settings.GetSegmentSize(name))
	return subscriber
}
