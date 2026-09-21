"""Prioritätswarteschlangen für Dijkstra (aus dijkstra-demo, hier nur die zwei Binärheap-Varianten), beide mit denselben Zählern: `pushes` (neue Einträge), `decrease_keys` (Schlüssel eines vorhandenen Knotens gesenkt), `pops` (entnommen),
`work` (Schlüsselvergleiche; bei Dial: Eimerschritte). Beide liefern bei gleichen Eingaben dieselben Entfernungen.

Schnittstelle: `push_or_decrease(node, key)`, `pop_min() -> (key, node)`, `peek_key()` (kleinster Schlüssel, inf wenn leer), `len(queue)`."""

import heapq


class _Counters:
    def __init__(self):
        self.pushes = self.decrease_keys = self.pops = self.work = 0

    def as_dict(self):
        return {"pushes": self.pushes, "decrease_keys": self.decrease_keys, "pops": self.pops, "work": self.work}


class BinaryHeapQueue(_Counters):
    """Binärheap mit Positionsfeld und echtem Decrease-Key: O(log n) je Operation."""

    def __init__(self, n=0, max_weight=None):
        super().__init__()
        self.heap, self.pos, self.key = [], {}, {}

    def __len__(self):
        return len(self.heap)

    def _less(self, i, j):
        self.work += 1
        return self.key[self.heap[i]] < self.key[self.heap[j]]

    def _swap(self, i, j):
        h = self.heap
        h[i], h[j] = h[j], h[i]
        self.pos[h[i]], self.pos[h[j]] = i, j

    def _up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if not self._less(i, parent):
                break
            self._swap(i, parent)
            i = parent

    def _down(self, i):
        n = len(self.heap)
        while True:
            left, right, small = 2 * i + 1, 2 * i + 2, i
            if left < n and self._less(left, small):
                small = left
            if right < n and self._less(right, small):
                small = right
            if small == i:
                return
            self._swap(i, small)
            i = small

    def push_or_decrease(self, node, key):
        if node in self.pos:
            self.decrease_keys += 1
            self.key[node] = key
            self._up(self.pos[node])
        else:
            self.pushes += 1
            self.key[node] = key
            self.heap.append(node)
            self.pos[node] = len(self.heap) - 1
            self._up(len(self.heap) - 1)

    def peek_key(self):
        return self.key[self.heap[0]] if self.heap else float("inf")

    def pop_min(self):
        node = self.heap[0]
        key = self.key.pop(node)
        last = self.heap.pop()
        del self.pos[node]
        if self.heap:
            self.heap[0] = last
            self.pos[last] = 0
            self._down(0)
        self.pops += 1
        return key, node


class LazyHeapQueue(_Counters):
    """Binärheap ohne Decrease-Key (`heapq`): ein gesenkter Schlüssel legt einen zweiten Eintrag an, der alte wird beim Entnehmen übersprungen (faule Löschung).
    Schlüsselvergleiche macht `heapq` in C, sie sind hier nicht zählbar (work = 0)."""

    def __init__(self, n=0, max_weight=None):
        super().__init__()
        self.heap, self.best = [], {}
        self.stale_pops = 0

    def __len__(self):
        return len(self.best)

    def push_or_decrease(self, node, key):
        if node in self.best:
            self.decrease_keys += 1
        else:
            self.pushes += 1
        self.best[node] = key
        heapq.heappush(self.heap, (key, node))

    def peek_key(self):
        """Kleinster lebender Schlüssel (tote Einträge oben werden verworfen); inf bei leerer Warteschlange."""
        while self.heap and self.best.get(self.heap[0][1]) != self.heap[0][0]:
            heapq.heappop(self.heap)
            self.stale_pops += 1
        return self.heap[0][0] if self.heap else float("inf")

    def pop_min(self):
        while True:
            key, node = heapq.heappop(self.heap)
            if self.best.get(node) == key:
                del self.best[node]
                self.pops += 1
                return key, node
            self.stale_pops += 1


QUEUES = {"binary": BinaryHeapQueue, "lazy": LazyHeapQueue}
QUEUE_LABELS = {"binary": "Binärheap (Decrease-Key)", "lazy": "Binärheap, faul (heapq)"}
