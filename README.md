# FaasCache Complete Project Package

This package deliberately keeps the two experiment families separate.

## Code
- `code/simulator.py` — shared cache simulator and policies.
- `code/control_traces.py` — original IID / PHASE / BURST controlled synthetic experiments.
- `code/azure_synthetic_traces.py` — Azure-inspired synthetic REPRESENTATIVE / RARE / RANDOM experiments. These are **not** the original Azure trace.
- `code/plot_all_results.py` — regenerates graphs from both result CSV files.

## Results
- `results/control/` — control CSV and six graphs.
- `results/azure_synthetic/` — Azure-inspired CSV and six graphs.

## Deliverables
- `report/FaasCache_Combined_Experimental_Report.docx`
- `presentation/FaasCache_Project_Presentation.pptx`

## References
- FaasCache ASPLOS 2021 paper.
- NTU project brief.

## Run
From the project root:
```bash
pip install -r requirements.txt
cd results/control
python ../../code/control_traces.py
cd ../azure_synthetic
python ../../code/azure_synthetic_traces.py
cd ../..
python code/plot_all_results.py
```

The control and Azure-inspired trace generators remain separate Python files as requested.
