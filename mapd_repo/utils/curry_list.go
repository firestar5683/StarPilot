package utils

type CurryList[T any] struct {
	getter func(int) T
	set []bool
	val []T
}

func (c *CurryList[T]) At(index int) T {
	if c.set[index] {
		return c.val[index]
	}
	c.Set(c.getter(index), index)
	return c.val[index]
}

func (c *CurryList[T]) Set(val T, index int) {
	c.set[index] = true
	c.val[index] = val
}

func (c *CurryList[T]) Len() int {
	return len(c.val)
}

func (c *CurryList[T]) Init(getter func(int) T, length int) {
	c.getter = getter
	c.set = make([]bool, length)
	c.val = make([]T, length)
}

func (c *CurryList[T]) Slice() []T {
	res := make([]T, c.Len())
	for i := range res {
		res[i] = c.At(i)
	}
	return res
}
