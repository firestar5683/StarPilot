package maps

import (
	"errors"
	"fmt"
	"math"
	"sync"
	"syscall"
)

var ErrSnapshotDiskBudget = errors.New("snapshot new disk budget unavailable")

// SnapshotDiskBudget conservatively charges every newly written staging byte,
// even if a temporary copy is later removed. The floor matches hardwared's
// existing >2% free-space startup condition; this is resource protection,
// not a forecast of remote archive size.
type SnapshotDiskBudget struct {
	root  string
	limit int64
	used  int64
	mu    sync.Mutex
}

func NewSnapshotDiskBudget(root string, limit int64) (*SnapshotDiskBudget, error) {
	if limit <= 0 || limit >= math.MaxInt64 {
		return nil, errors.New("invalid new disk byte budget")
	}
	return &SnapshotDiskBudget{root: root, limit: limit}, nil
}

func (b *SnapshotDiskBudget) charge(size int64) error {
	if b == nil {
		return nil
	}
	if size < 0 {
		return errors.New("invalid snapshot write size")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	if size > b.limit-b.used {
		return fmt.Errorf("%w: exhausted", ErrSnapshotDiskBudget)
	}
	var stat syscall.Statfs_t
	if err := syscall.Statfs(b.root, &stat); err != nil {
		return err
	}
	if stat.Bsize <= 0 || stat.Blocks == 0 {
		return errors.New("snapshot filesystem capacity unavailable")
	}
	needed := uint64(size) / uint64(stat.Bsize)
	if uint64(size)%uint64(stat.Bsize) != 0 {
		needed++
	}
	if uint64(stat.Bavail) <= uint64(stat.Blocks)/50+needed {
		return fmt.Errorf("%w: filesystem free-space floor reached", ErrSnapshotDiskBudget)
	}
	b.used += size
	return nil
}
