import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_file(csv_path, out_dir, azure=False):
    df=pd.read_csv(csv_path); out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    for workload in df.workload.unique():
        sub=df[df.workload==workload]
        short=workload.replace("AZURE_","").replace("_SYNTH","").lower()
        for metric,label,suffix in [("hit_ratio","Hit ratio","hit_ratio"),("avg_cold_overhead_ms","Average cold-start overhead per request (ms)","cold_overhead")]:
            fig,ax=plt.subplots(figsize=(7.2,4.4))
            for policy in sub.policy.unique():
                s=sub[sub.policy==policy].sort_values("capacity_mb")
                x=s.capacity_mb/1024 if azure else s.capacity_mb
                ax.plot(x,s[metric],marker="o",label=policy)
            ax.set_title(f"{short.title()}: memory vs {suffix.replace('_',' ')}")
            ax.set_xlabel("Server memory capacity (GB)" if azure else "Server memory capacity (MB)")
            ax.set_ylabel(label); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout()
            fig.savefig(out_dir/f"{short}_{suffix}.png",dpi=160); plt.close(fig)

if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    plot_file(root/"results/control/control_results.csv",root/"results/control",False)
    plot_file(root/"results/azure_synthetic/azure_synthetic_results.csv",root/"results/azure_synthetic",True)
    print("Graphs regenerated.")
