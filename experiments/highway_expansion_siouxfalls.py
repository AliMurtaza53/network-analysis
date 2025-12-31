from network import Network
from policies.modifiers import scale_capacity, reset_flows

highway_links = [
    '(5,9)', '(9,5)', '(9,10)', '(10,9)',
    '(10,15)', '(15,10)', '(15,22)', '(22,15)',
    '(22,21)', '(21,22)'
]

# Baseline
print('Baseline...')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
baseline_tstt = sum(l.flow * l.cost for l in net.link.values())
baseline_gap = net.relativeGap()

# Store baseline link data
baseline_data = {}
for link_id, link in net.link.items():
    baseline_data[link_id] = {
        'capacity': link.capacity,
        'fft': link.freeFlowTime,
        'flow': link.flow
    }

# Policy
print('\\nPolicy: 2x capacity...')
reset_flows(net)
scale_capacity(net, highway_links, capacity_factor=2.0)
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
policy_tstt = sum(l.flow * l.cost for l in net.link.values())
policy_gap = net.relativeGap()

# Results
print(f'\\nBaseline TSTT: {baseline_tstt:,.0f}, Gap: {baseline_gap:.6f}')
print(f'Policy TSTT:   {policy_tstt:,.0f}, Gap: {policy_gap:.6f}')
print(f'Reduction:     {(1 - policy_tstt/baseline_tstt)*100:.1f}%')

# Save summary
import csv, os
os.makedirs('results', exist_ok=True)
with open('results/highway_expansion_summary.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['scenario', 'tstt', 'gap'])
    w.writeheader()
    w.writerow({'scenario': 'baseline', 'tstt': baseline_tstt, 'gap': baseline_gap})
    w.writerow({'scenario': 'policy', 'tstt': policy_tstt, 'gap': policy_gap})

# Save link-by-link comparison
with open('results/highway_expansion_links.csv', 'w', newline='') as f:
    fieldnames = ['link_id', 'baseline_capacity', 'new_capacity', 
                  'baseline_fft', 'new_fft', 'baseline_flow', 'new_flow', 
                  'pct_flow_change']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    
    for link_id in sorted(net.link.keys()):
        link = net.link[link_id]
        baseline = baseline_data[link_id]
        
        # Calculate percent change in flow
        if baseline['flow'] > 0:
            pct_change = ((link.flow - baseline['flow']) / baseline['flow']) * 100
        else:
            pct_change = 0 if link.flow == 0 else float('inf')
        
        w.writerow({
            'link_id': link_id,
            'baseline_capacity': baseline['capacity'],
            'new_capacity': link.capacity,
            'baseline_fft': baseline['fft'],
            'new_fft': link.freeFlowTime,
            'baseline_flow': baseline['flow'],
            'new_flow': link.flow,
            'pct_flow_change': round(pct_change, 1)
        })

print('\\nSaved: results/highway_expansion_summary.csv')
print('Saved: results/highway_expansion_links.csv')
