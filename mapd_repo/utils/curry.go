package utils

type Curry[T any] struct {
	set bool
	val T
}

func (c *Curry[T]) Value(setter func() T) T {
	if c.set {
		return c.val
	}
	c.set = true
	c.val = setter()
	return c.val
}

func (c *Curry[T]) Set(val T) {
	c.set = true
	c.val = val
}
