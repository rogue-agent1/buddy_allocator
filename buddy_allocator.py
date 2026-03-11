#!/usr/bin/env python3
"""Buddy allocator — power-of-2 memory allocation with coalescing.

One file. Zero deps. Does one thing well.

Splits blocks in half to satisfy requests, merges buddies on free.
O(log n) alloc/free. Used in Linux kernel page allocator, jemalloc.
"""
import math, sys

class BuddyAllocator:
    def __init__(self, total_size=1024):
        self.total = total_size
        self.max_order = int(math.log2(total_size))
        # free_lists[order] = set of block start addresses
        self.free_lists = [set() for _ in range(self.max_order + 1)]
        self.free_lists[self.max_order].add(0)
        self.allocated = {}  # addr -> order
        self.alloc_count = 0
        self.free_count = 0

    def _order_for(self, size):
        order = 0
        block = 1
        while block < size:
            order += 1
            block <<= 1
        return order

    def alloc(self, size):
        needed = self._order_for(size)
        if needed > self.max_order:
            return None
        # Find smallest available block >= needed order
        for order in range(needed, self.max_order + 1):
            if self.free_lists[order]:
                addr = min(self.free_lists[order])
                self.free_lists[order].remove(addr)
                # Split down to needed size
                while order > needed:
                    order -= 1
                    buddy = addr + (1 << order)
                    self.free_lists[order].add(buddy)
                self.allocated[addr] = needed
                self.alloc_count += 1
                return addr
        return None  # Out of memory

    def free(self, addr):
        if addr not in self.allocated:
            raise ValueError(f"Double free or invalid address: {addr}")
        order = self.allocated.pop(addr)
        self.free_count += 1
        # Coalesce with buddy
        while order < self.max_order:
            buddy = addr ^ (1 << order)
            if buddy in self.free_lists[order]:
                self.free_lists[order].remove(buddy)
                addr = min(addr, buddy)
                order += 1
            else:
                break
        self.free_lists[order].add(addr)

    def stats(self):
        free_blocks = sum(len(fl) for fl in self.free_lists)
        free_bytes = sum(len(fl) * (1 << i) for i, fl in enumerate(self.free_lists))
        used_bytes = sum(1 << o for o in self.allocated.values())
        return {
            "total": self.total,
            "used": used_bytes,
            "free": free_bytes,
            "fragmentation": f"{(1 - free_bytes/(self.total - used_bytes))*100:.1f}%" if self.total > used_bytes else "100%",
            "allocated_blocks": len(self.allocated),
            "free_blocks": free_blocks,
            "allocs": self.alloc_count,
            "frees": self.free_count,
        }

    def visualize(self, width=64):
        """ASCII visualization of memory layout."""
        bitmap = ['.'] * self.total
        for addr, order in self.allocated.items():
            size = 1 << order
            for i in range(addr, min(addr + size, self.total)):
                bitmap[i] = '#'
        scale = max(1, self.total // width)
        line = []
        for i in range(0, self.total, scale):
            chunk = bitmap[i:i+scale]
            if all(c == '#' for c in chunk):
                line.append('█')
            elif all(c == '.' for c in chunk):
                line.append('░')
            else:
                line.append('▒')
        return ''.join(line)

def main():
    ba = BuddyAllocator(1024)
    print("=== Buddy Allocator (1024 bytes) ===\n")
    
    # Allocate various sizes
    addrs = []
    for size in [100, 50, 200, 30, 64, 128]:
        addr = ba.alloc(size)
        addrs.append((addr, size))
        actual = 1 << ba._order_for(size)
        print(f"  alloc({size:3d}) → addr={addr:4d} (actual={actual})")
    
    print(f"\n  Memory: {ba.visualize()}")
    print(f"  {ba.stats()}")
    
    # Free some and show coalescing
    print(f"\n  Freeing addr={addrs[1][0]} (size={addrs[1][1]})")
    ba.free(addrs[1][0])
    print(f"  Freeing addr={addrs[3][0]} (size={addrs[3][1]})")
    ba.free(addrs[3][0])
    
    print(f"\n  Memory: {ba.visualize()}")
    
    # Allocate to show reuse
    addr = ba.alloc(40)
    print(f"  alloc(40) → addr={addr} (reuses freed block)")
    print(f"\n  Memory: {ba.visualize()}")
    print(f"  {ba.stats()}")

if __name__ == "__main__":
    main()
