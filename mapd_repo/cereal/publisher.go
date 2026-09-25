package cereal

import (
	"log/slog"
	"time"

	"capnproto.org/go/capnp/v3"
	"github.com/pfeiferj/gomsgq"
	"pfeifer.dev/mapd/cereal/log"
	"pfeifer.dev/mapd/settings"
)

type MessageCreator[T any] func(log.Event) (T, error)

type Publisher[T any] struct {
	Pub     gomsgq.MsgqPublisher
	creator MessageCreator[T]

	msgChan     chan *capnp.Message
	stop        chan struct{}
	done        chan struct{}
	sendMessage func(*capnp.Message) error
}

func (p *Publisher[T]) Send(msg *capnp.Message) error {
	b, err := msg.Marshal()
	if err != nil {
		return err
	}
	p.Pub.Send(b)
	return nil
}

func (p *Publisher[T]) NewMessage(valid bool) (msg *capnp.Message, obj T) {
	arena := capnp.SingleSegment(nil)

	msg, seg, err := capnp.NewMessage(arena)
	if err != nil {
		panic(err)
	}

	event, err := log.NewRootEvent(seg)
	if err != nil {
		panic(err)
	}

	event.SetLogMonoTime(GetTime())
	event.SetValid(valid)

	obj, err = p.creator(event)
	if err != nil {
		panic(err)
	}

	return msg, obj
}

// StartAutoPublish sends newly queued messages at the given rate. It never
// re-sends an old sample or changes the sample's timestamp.
func (p *Publisher[T]) StartAutoPublish(rate time.Duration) {
	p.msgChan = make(chan *capnp.Message, 1)
	p.stop = make(chan struct{})
	p.done = make(chan struct{})
	go p.autoPublishLoop(rate)
}

// Publish hands msg to the auto-publish loop, replacing any message queued
// since the last tick. It never blocks. Only the newest message queued
// between ticks is ever sent. Requires StartAutoPublish to have been called
// first.
func (p *Publisher[T]) Publish(msg *capnp.Message) {
	for {
		select {
		case p.msgChan <- msg:
			return
		default:
			select {
			case <-p.msgChan:
			default:
			}
		}
	}
}

// Stop halts the auto-publish loop started by StartAutoPublish, if any.
func (p *Publisher[T]) Stop() {
	if p.stop == nil {
		return
	}
	close(p.stop)
	<-p.done
}

func (p *Publisher[T]) autoPublishLoop(rate time.Duration) {
	ticker := time.NewTicker(rate)
	defer ticker.Stop()
	p.runAutoPublishLoop(ticker.C, nil)
}

// The tick channel is injectable so the real loop can be exercised without
// wall-clock sleeps; tickDone is only used by tests to acknowledge a tick.
func (p *Publisher[T]) runAutoPublishLoop(ticks <-chan time.Time, tickDone chan<- struct{}) {
	defer close(p.done)
	for {
		select {
		case <-p.stop:
			return
		case <-ticks:
			p.publishTick()
			if tickDone != nil {
				tickDone <- struct{}{}
			}
		}
	}
}

func (p *Publisher[T]) publishTick() {
	select {
	case msg := <-p.msgChan:
		if msg == nil {
			return
		}
		send := p.sendMessage
		if send == nil {
			send = p.Send
		}
		if err := send(msg); err != nil {
			slog.Error("failed to auto-publish message", "error", err)
		}
	default:
	}
}

func NewPublisher[T any](name string, creator MessageCreator[T]) (publisher Publisher[T]) {
	msgq := gomsgq.Msgq{}
	err := msgq.Init(name, settings.GetSegmentSize(name))
	if err != nil {
		panic(err)
	}
	pub := gomsgq.MsgqPublisher{}
	pub.Init(msgq)

	publisher.Pub = pub
	publisher.creator = creator
	return publisher
}
