import csv, random, math
from simulator import Function, Simulator, GDSF, LRU, LFU, TTL, SizeOnly

SEED = 2026
random.seed(SEED)

# Azure-inspired synthetic workloads.
# IMPORTANT: these are NOT the original Azure Functions traces.
# We preserve the paper's workload categories/function counts (Representative=400,
# Rare=1000, Random=200) but synthesize function properties and requests so the
# project is runnable without the private/preprocessed trace data.

def make_function(name):
    # Heterogeneous memory sizes similar to serverless memory tiers.
    sizes = [64, 128, 256, 512, 1024, 1536, 2048]
    size = random.choices(sizes, weights=[8,18,26,24,14,6,4], k=1)[0]
    # Initialization cost is heterogeneous and only loosely related to size.
    base = 180 + 1.15 * size
    cold = max(80, min(6500, random.lognormvariate(math.log(base), 0.65)))
    return Function(name, size, round(cold,1))

def make_functions(prefix, n):
    return {f"{prefix}{i:04d}": make_function(f"{prefix}{i:04d}") for i in range(n)}

def weighted_trace(functions, weights, n_requests):
    names=list(functions)
    return [(i, random.choices(names, weights=weights, k=1)[0]) for i in range(n_requests)]

def representative_workload(n_requests=60000):
    # Paper: 400 functions sampled across frequency quartiles.
    fs=make_functions("R",400)
    # Four 100-function groups; deliberately heterogeneous popularity.
    group_mass=[0.55,0.25,0.15,0.05]
    weights=[]
    for g,mass in enumerate(group_mass):
        # Small within-quartile skew avoids making every function identical.
        local=[1/(i+1)**0.35 for i in range(100)]
        s=sum(local)
        weights += [mass*x/s for x in local]
    return fs, weighted_trace(fs,weights,n_requests)

def rare_workload(n_requests=60000):
    # Paper: 1000 of the rarest functions. Near-uniform accesses make reuse weak.
    fs=make_functions("Q",1000)
    weights=[random.uniform(0.8,1.2) for _ in fs]
    return fs, weighted_trace(fs,weights,n_requests)

def random_workload(n_requests=60000):
    # Paper: random sample of 200 functions. Use moderate Zipf-like skew.
    fs=make_functions("X",200)
    weights=[1/(i+1)**0.75 for i in range(len(fs))]
    return fs, weighted_trace(fs,weights,n_requests)

workloads={
    "AZURE_REPRESENTATIVE_SYNTH": representative_workload(),
    "AZURE_RARE_SYNTH": rare_workload(),
    "AZURE_RANDOM_SYNTH": random_workload(),
}

# Paper evaluates server memory in GB-scale ranges; these capacities are synthetic
# but chosen to expose the same memory-pressure tradeoff.
capacities_mb=[4096,8192,12288,16384,24576,32768,49152]
policy_factories={
    "GDSF": lambda:GDSF(),
    "LRU": lambda:LRU(),
    "LFU": lambda:LFU(),
    # Here t is request index, so this is an idle-request-count TTL, not milliseconds.
    "TTL-2000": lambda:TTL(2000),
    "SIZE": lambda:SizeOnly(),
}

rows=[]
for wname,(functions,trace) in workloads.items():
    for cap in capacities_mb:
        for pname,factory in policy_factories.items():
            r=Simulator(functions,cap,factory()).run(trace)
            rows.append({"workload":wname,"capacity_mb":cap,"policy":pname,**r})

with open("azure_synthetic_results.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)

print("Completed",len(rows),"Azure-inspired synthetic runs")
for wname in workloads:
    print("\n",wname,"@ 16384 MB")
    for r in rows:
        if r["workload"]==wname and r["capacity_mb"]==16384:
            print(r["policy"],"hit=",round(r["hit_ratio"],3),
                  "avg cold ms=",round(r["avg_cold_overhead_ms"],1))
