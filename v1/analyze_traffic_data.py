import csv
import sys
from datetime import datetime

if len(sys.argv) < 2:
    print("Usage: python analyze.py traffic_data_YYYYMMDD_HHMMSS.csv")
    sys.exit(1)

filename = sys.argv[1]

# Create output filename based on input
output_filename = filename.replace('.csv', '_analysis.txt')

# Load data
vehicles = []
with open(filename, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        vehicles.append({
            'number': int(row['vehicle_number']),
            'direction': row['direction'],
            'speed': float(row['speed_normalized'])
        })

if len(vehicles) < 4:
    print("Not enough data")
    sys.exit(1)

speeds = [v['speed'] for v in vehicles]
speeds_rtl = [v['speed'] for v in vehicles if v['direction'] == 'RTL']
speeds_ltr = [v['speed'] for v in vehicles if v['direction'] == 'LTR']

min_speed = min(speeds)
max_speed = max(speeds)
speed_range = max_speed - min_speed
mean_speed = sum(speeds) / len(speeds)

# Divide SPEED RANGE into 4 equal bins
bin_width = speed_range / 4
bins = [
    (min_speed, min_speed + bin_width),
    (min_speed + bin_width, min_speed + 2*bin_width),
    (min_speed + 2*bin_width, min_speed + 3*bin_width),
    (min_speed + 3*bin_width, max_speed)
]

# Count vehicles in each bin
bin_counts = [0, 0, 0, 0]
for speed in speeds:
    for i, (low, high) in enumerate(bins):
        if low <= speed < high or (i == 3 and speed == high):
            bin_counts[i] += 1
            break

# Write analysis to file
with open(output_filename, 'w') as f:
    f.write("TRAFFIC SPEED ANALYSIS\n")
    f.write("="*70 + "\n")
    f.write(f"Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Data file: {filename}\n\n")
    
    f.write(f"SUMMARY\n")
    f.write(f"-"*70 + "\n")
    f.write(f"Total vehicles:    {len(vehicles)}\n")
    f.write(f"RTL direction:     {len(speeds_rtl)}\n")
    f.write(f"LTR direction:     {len(speeds_ltr)}\n\n")
    
    f.write(f"Speed range:       {min_speed:.1f} - {max_speed:.1f} px/s\n")
    f.write(f"Range span:        {speed_range:.1f} px/s\n")
    f.write(f"Mean speed:        {mean_speed:.1f} px/s\n\n")
    
    f.write(f"SPEED RANGE DISTRIBUTION\n")
    f.write(f"-"*70 + "\n")
    f.write(f"Speed range divided into 4 equal bins\n\n")
    
    for i, (low, high) in enumerate(bins):
        pct = bin_counts[i] / len(vehicles) * 100
        f.write(f"Bin {i+1} ({low:6.1f} - {high:6.1f} px/s): "
                f"{bin_counts[i]:4d} vehicles ({pct:5.1f}%)\n")
    
    # Analysis
    top_half_count = bin_counts[2] + bin_counts[3]
    top_half_pct = top_half_count / len(vehicles) * 100
    bottom_half_count = bin_counts[0] + bin_counts[1]
    bottom_half_pct = bottom_half_count / len(vehicles) * 100
    top_bin_pct = bin_counts[3] / len(vehicles) * 100
    
    f.write(f"\nKEY METRICS\n")
    f.write(f"-"*70 + "\n")
    f.write(f"Bottom half of range: {bottom_half_count:4d} vehicles ({bottom_half_pct:5.1f}%)\n")
    f.write(f"Top half of range:    {top_half_count:4d} vehicles ({top_half_pct:5.1f}%)\n")
    f.write(f"Fastest bin:          {bin_counts[3]:4d} vehicles ({top_bin_pct:5.1f}%)\n\n")
    
    # Interpretation
    f.write(f"INTERPRETATION\n")
    f.write(f"-"*70 + "\n")
    if top_half_pct > 60:
        f.write(f"⚠️  HIGH-SPEED CLUSTERING: {top_half_pct:.1f}% of vehicles in top half\n")
        f.write(f"    Traffic shows speeding tendency\n")
    elif bottom_half_pct > 60:
        f.write(f"✓ LOW-SPEED CLUSTERING: {bottom_half_pct:.1f}% of vehicles in bottom half\n")
        f.write(f"    Traffic shows cautious driving patterns\n")
    else:
        f.write(f"✓ EVEN DISTRIBUTION: Speeds spread across range\n")
        f.write(f"    Normal traffic behavior\n")
    
    # Directional comparison
    if speeds_rtl and speeds_ltr:
        avg_rtl = sum(speeds_rtl) / len(speeds_rtl)
        avg_ltr = sum(speeds_ltr) / len(speeds_ltr)
        
        f.write(f"\nDIRECTIONAL COMPARISON\n")
        f.write(f"-"*70 + "\n")
        f.write(f"RTL (farther lane):  {len(speeds_rtl):4d} vehicles, mean {avg_rtl:6.1f} px/s\n")
        f.write(f"LTR (closer lane):   {len(speeds_ltr):4d} vehicles, mean {avg_ltr:6.1f} px/s\n\n")
        
        diff_pct = abs(avg_rtl - avg_ltr) / min(avg_rtl, avg_ltr) * 100
        if diff_pct > 10:
            faster = "RTL" if avg_rtl > avg_ltr else "LTR"
            f.write(f"Direction {faster} averages {diff_pct:.1f}% faster\n")
        else:
            f.write(f"Both directions show similar speeds\n")
    
    f.write("\n" + "="*70 + "\n")

print(f"Analysis saved to: {output_filename}")
