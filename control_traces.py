
import csv, random
from simulator import Function, Simulator, GDSF, LRU, LFU, TTL, SizeOnly

random.seed(42)

functions = {
    "A": Function("A", 128, 1800),
    "B": Function("B", 512, 4500),
    "C": Function("C", 64, 300),
    "D": Function("D", 1024, 800),
    "E": Function("E", 256, 2200),
    "F": Function("F", 128, 150),
}

def iid_trace(n=20000):
    names = list(functions)
    weights = [0.32, 0.08, 0.25, 0.07, 0.16, 0.12]
    return [(i, random.choices(names, weights=weights, k=1)[0]) for i in range(n)]

def phase_trace(n=20000):
    """Popularity changes halfway through: useful for exposing LFU staleness."""
    out=[]
    names=list(functions)
    w1=[0.45,0.20,0.15,0.03,0.12,0.05]
    w2=[0.05,0.04,0.16,0.20,0.20,0.35]
    for i in range(n):
        w=w1 if i < n//2 else w2
        out.append((i, random.choices(names, weights=w, k=1)[0]))
    return out

def burst_trace(n=20000):
    """Alternating bursts create strong temporal locality."""
    out=[]
    groups=[(["A","C","E"],[0.55,0.30,0.15]), (["B","D","F"],[0.30,0.15,0.55])]
    for i in range(n):
        names,w=groups[(i//1000)%2]
        out.append((i, random.choices(names, weights=w, k=1)[0]))
    return out

workloads={"IID":iid_trace(), "PHASE":phase_trace(), "BURST":burst_trace()}
capacities=[256,384,512,768,1024,1536,2048]
policy_factories={
    "GDSF": lambda:GDSF(),
    "LRU": lambda:LRU(),
    "LFU": lambda:LFU(),
    "TTL-500": lambda:TTL(500),
    "SIZE": lambda:SizeOnly(),
}

rows=[]
for wname,trace in workloads.items():
    for cap in capacities:
        for pname,factory in policy_factories.items():
            r=Simulator(functions,cap,factory()).run(trace)
            rows.append({"workload":wname,"capacity_mb":cap,"policy":pname,**r})

with open("control_results.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

print("Completed", len(rows), "runs")
for wname in workloads:
    print("\n",wname,"@ 1536 MB")
    for r in rows:
        if r["workload"]==wname and r["capacity_mb"]==1536:
            print(r["policy"], "hit=",round(r["hit_ratio"],3),
                  "avg cold ms=",round(r["avg_cold_overhead_ms"],1))
