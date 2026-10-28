
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class Function:
    name: str
    size_mb: float
    cold_ms: float
    warm_ms: float = 0.0

class Simulator:
    """Single-server trace-driven warm-container cache simulator."""
    def __init__(self, functions, capacity_mb, policy):
        self.functions = functions
        self.capacity = float(capacity_mb)
        self.policy = policy
        self.warm = set()
        self.used = 0.0
        self.hits = self.misses = 0
        self.cold_overhead_ms = 0.0
        self.evictions = 0

    def _expire(self, t):
        # TTL may proactively expire idle containers.
        expired = self.policy.expired(self.warm, t)
        for name in list(expired):
            if name in self.warm:
                self.warm.remove(name)
                self.used -= self.functions[name].size_mb
                self.policy.on_evict(name)
                self.evictions += 1

    def _evict_until_fits(self, incoming):
        need = self.functions[incoming].size_mb
        while self.used + need > self.capacity and self.warm:
            victim = self.policy.victim(self.warm, self.functions)
            self.warm.remove(victim)
            self.used -= self.functions[victim].size_mb
            self.policy.on_evict(victim)
            self.evictions += 1

    def run(self, trace):
        for t, name in trace:
            self._expire(t)
            f = self.functions[name]
            hit = name in self.warm
            self.policy.on_request(name, hit, t, f)
            if hit:
                self.hits += 1
            else:
                self.misses += 1
                self.cold_overhead_ms += f.cold_ms
                self._evict_until_fits(name)
                if f.size_mb <= self.capacity:
                    self.warm.add(name)
                    self.used += f.size_mb
                    self.policy.on_insert(name, t, f)
        n = self.hits + self.misses
        return {
            "requests": n,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits/n if n else 0.0,
            "cold_overhead_ms": self.cold_overhead_ms,
            "avg_cold_overhead_ms": self.cold_overhead_ms/n if n else 0.0,
            "evictions": self.evictions,
        }

class BasePolicy:
    def expired(self, warm, t): return []
    def on_evict(self, name): pass

class LRU(BasePolicy):
    def __init__(self): self.last = {}
    def on_request(self, name, hit, t, f): self.last[name] = t
    def on_insert(self, name, t, f): self.last[name] = t
    def victim(self, warm, functions): return min(warm, key=lambda x: self.last.get(x, -1))

class LFU(BasePolicy):
    def __init__(self):
        self.freq = defaultdict(int); self.last = {}
    def on_request(self, name, hit, t, f):
        self.freq[name] += 1; self.last[name] = t
    def on_insert(self, name, t, f): self.last[name] = t
    def victim(self, warm, functions):
        return min(warm, key=lambda x: (self.freq[x], self.last.get(x, -1)))

class SizeOnly(BasePolicy):
    def on_request(self, name, hit, t, f): pass
    def on_insert(self, name, t, f): pass
    def victim(self, warm, functions): return max(warm, key=lambda x: functions[x].size_mb)

class TTL(BasePolicy):
    """
    Keep a container warm until it has been idle for ttl time units.
    If capacity pressure occurs first, evict the least-recently-used warm container.
    """
    def __init__(self, ttl):
        self.ttl = ttl; self.last = {}
    def on_request(self, name, hit, t, f): self.last[name] = t
    def on_insert(self, name, t, f): self.last[name] = t
    def expired(self, warm, t):
        return [x for x in warm if t - self.last.get(x, t) > self.ttl]
    def victim(self, warm, functions):
        return min(warm, key=lambda x: self.last.get(x, -1))

class GDSF(BasePolicy):
    """
    FaasCache core:
        priority = clock + frequency * cold_start_cost / size
    Lowest priority is evicted.
    """
    def __init__(self):
        self.clock = 0.0
        self.freq = defaultdict(int)
        self.priority = {}
        self.container_clock = {}

    def _update(self, name, f):
        c = self.container_clock.get(name, self.clock)
        self.priority[name] = c + self.freq[name] * f.cold_ms / f.size_mb

    def on_request(self, name, hit, t, f):
        self.freq[name] += 1
        if hit:
            self.container_clock[name] = self.clock
            self._update(name, f)

    def on_insert(self, name, t, f):
        self.container_clock[name] = self.clock
        self._update(name, f)

    def victim(self, warm, functions):
        return min(warm, key=lambda x: self.priority[x])

    def on_evict(self, name):
        self.clock = self.priority.get(name, self.clock)
        # In this simplified one-container-per-function model, no warm
        # container remains after eviction, so function frequency resets.
        self.freq[name] = 0
        self.priority.pop(name, None)
        self.container_clock.pop(name, None)
