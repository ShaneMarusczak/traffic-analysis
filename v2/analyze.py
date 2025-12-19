"""
Traffic Analysis - Consumer
Receives raw detection data, computes speeds, generates statistics and reports.
All computational work happens here to keep detection loop fast.
"""

import csv
from datetime import datetime
import os


def analyze_stream(data_queue, config):
    """
    Continuously process vehicle data from queue.
    Updates CSV and report in real-time.
    
    Args:
        data_queue: multiprocessing.Queue receiving vehicle data
        config: Configuration dictionary from config.yaml
    """
    
    vehicles = []
    report_update_interval = config['analysis']['report_update_interval']
    
    # Create output directories
    os.makedirs(config['output']['csv_dir'], exist_ok=True)
    os.makedirs(config['output']['reports_dir'], exist_ok=True)
    
    # Generate filenames with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{config['output']['csv_dir']}/traffic_data_{timestamp}.csv"
    report_filename = f"{config['output']['reports_dir']}/traffic_analysis_{timestamp}.txt"
    
    # Open CSV for streaming writes
    csv_file = open(csv_filename, 'w', newline='')
    csv_writer = csv.DictWriter(csv_file, fieldnames=[
        'vehicle_number',
        'track_id',
        'direction',
        'distance_pixels',
        'time_elapsed',
        'speed_raw',
        'speed_normalized',
        'timestamp'
    ])
    csv_writer.writeheader()
    
    rtl_factor = config['perspective']['rtl_correction_factor']
    
    print(f"Analyzer initialized")
    print(f"  CSV: {csv_filename}")
    print(f"  Report: {report_filename}")
    print(f"  Perspective factor (RTL): {rtl_factor}x")
    print(f"  Report updates: Every {report_update_interval} vehicles")
    print(f"\nAnalysis started\n")
    
    vehicle_count = 0
    
    try:
        while True:
            # Block waiting for data
            data = data_queue.get()
            
            # None signals end of stream
            if data is None:
                break
            
            vehicle_count += 1
            
            # COMPUTE SPEED (all computation happens here, not in detector)
            speed_raw = data['distance_pixels'] / data['time_elapsed']
            
            # Apply perspective correction
            if data['direction'] == 'RTL':
                speed_normalized = speed_raw * rtl_factor
            else:
                speed_normalized = speed_raw
            
            # Build complete vehicle record
            vehicle = {
                'vehicle_number': data['vehicle_number'],
                'track_id': data['track_id'],
                'direction': data['direction'],
                'distance_pixels': data['distance_pixels'],
                'time_elapsed': data['time_elapsed'],
                'speed_raw': speed_raw,
                'speed_normalized': speed_normalized,
                'timestamp': data['timestamp']
            }
            
            vehicles.append(vehicle)
            
            # Write to CSV immediately
            csv_writer.writerow(vehicle)
            csv_file.flush()
            
            # Console output
            print(f"Vehicle #{vehicle['vehicle_number']:3d} | "
                  f"{vehicle['direction']} | "
                  f"{speed_normalized:6.1f} px/s | "
                  f"({speed_raw:.1f} raw)")
            
            # Update report periodically
            if len(vehicles) % report_update_interval == 0:
                write_report(vehicles, report_filename, config)
                print(f"  [Report updated: {len(vehicles)} vehicles]")
    
    except KeyboardInterrupt:
        print("\nAnalysis stopped by user")
    except Exception as e:
        print(f"\nERROR in analysis: {e}")
    finally:
        # Write final report
        if vehicles:
            write_report(vehicles, report_filename, config)
        
        csv_file.close()
        
        print(f"\nAnalysis complete")
        print(f"  Total vehicles: {len(vehicles)}")
        print(f"  CSV: {csv_filename}")
        print(f"  Report: {report_filename}")


def write_report(vehicles, filename, config):
    """
    Generate statistical report from vehicle data.
    Uses 6 bins: outliers below/above + 4 bins for normal range.
    
    Args:
        vehicles: List of vehicle dicts with speed data
        filename: Output filename for report
        config: Configuration dictionary from config.yaml
    """
    
    if len(vehicles) < 4:
        return
    
    # Extract configuration
    p_low = config['analysis']['percentile_low']
    p_high = config['analysis']['percentile_high']
    num_bins = config['analysis']['normal_range_bins']
    rtl_factor = config['perspective']['rtl_correction_factor']
    clustering_thresh = config['thresholds']['clustering_threshold']
    dir_diff_thresh = config['thresholds']['directional_difference']
    
    # Extract speeds
    speeds = [v['speed_normalized'] for v in vehicles]
    speeds_rtl = [v['speed_normalized'] for v in vehicles if v['direction'] == 'RTL']
    speeds_ltr = [v['speed_normalized'] for v in vehicles if v['direction'] == 'LTR']
    
    # Sort for percentile calculations
    sorted_speeds = sorted(speeds)
    n = len(sorted_speeds)
    
    # Percentile boundaries
    p_low_idx = int(n * (p_low / 100))
    p_high_idx = int(n * (p_high / 100))
    
    min_speed_p = sorted_speeds[p_low_idx]
    max_speed_p = sorted_speeds[p_high_idx]
    speed_range = max_speed_p - min_speed_p
    
    actual_min = sorted_speeds[0]
    actual_max = sorted_speeds[-1]
    mean_speed = sum(speeds) / len(speeds)
    
    # Create 6 bins: outlier_low + num_bins normal + outlier_high
    bin_width = speed_range / num_bins
    bins = [(0, min_speed_p, f"Below {p_low}th %ile")]
    
    for i in range(num_bins):
        low = min_speed_p + i * bin_width
        high = min_speed_p + (i + 1) * bin_width
        bins.append((low, high, f"Bin {i+1}"))
    
    bins.append((max_speed_p, float('inf'), f"Above {p_high}th %ile"))
    
    # Count vehicles in each bin
    bin_counts = [0] * (num_bins + 2)
    
    for speed in speeds:
        for i, (low, high, label) in enumerate(bins):
            if i == len(bins) - 1:  # Last bin
                if speed >= low:
                    bin_counts[i] += 1
                    break
            elif low <= speed < high:
                bin_counts[i] += 1
                break
    
    # Generate report
    with open(filename, 'w') as f:
        f.write("TRAFFIC SPEED ANALYSIS\n")
        f.write("="*70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Vehicles analyzed: {len(vehicles)}\n")
        f.write(f"Perspective correction: RTL x{rtl_factor}\n\n")
        
        # Summary
        f.write(f"SUMMARY\n")
        f.write(f"-"*70 + "\n")
        f.write(f"Total vehicles:    {len(vehicles)}\n")
        f.write(f"  RTL direction:   {len(speeds_rtl)} ({len(speeds_rtl)/len(vehicles)*100:.1f}%)\n")
        f.write(f"  LTR direction:   {len(speeds_ltr)} ({len(speeds_ltr)/len(vehicles)*100:.1f}%)\n\n")
        
        f.write(f"Speed statistics:\n")
        f.write(f"  Full range:      {actual_min:.1f} - {actual_max:.1f} px/s\n")
        f.write(f"  Mean speed:      {mean_speed:.1f} px/s\n")
        f.write(f"  {p_low}th percentile:  {min_speed_p:.1f} px/s\n")
        f.write(f"  {p_high}th percentile: {max_speed_p:.1f} px/s\n\n")
        
        # Speed distribution with bins
        f.write(f"SPEED DISTRIBUTION ({num_bins+2} bins)\n")
        f.write(f"-"*70 + "\n")
        
        for i, (low, high, label) in enumerate(bins):
            pct = bin_counts[i] / len(vehicles) * 100
            bar = '█' * int(pct / 2)
            
            if i == 0:
                f.write(f"Bin {i} [< {min_speed_p:6.1f}]:        "
                        f"{bin_counts[i]:4d} vehicles ({pct:5.1f}%) {bar} {label}\n")
            elif i == len(bins) - 1:
                f.write(f"Bin {i} [> {max_speed_p:6.1f}]:        "
                        f"{bin_counts[i]:4d} vehicles ({pct:5.1f}%) {bar} {label}\n")
            else:
                f.write(f"Bin {i} [{low:6.1f} - {high:6.1f}]: "
                        f"{bin_counts[i]:4d} vehicles ({pct:5.1f}%) {bar}\n")
        
        # Key metrics
        normal_traffic = sum(bin_counts[1:-1])
        outliers_low = bin_counts[0]
        outliers_high = bin_counts[-1]
        
        f.write(f"\nKEY METRICS\n")
        f.write(f"-"*70 + "\n")
        f.write(f"Normal traffic ({p_low}th-{p_high}th %ile): {normal_traffic:4d} vehicles ({normal_traffic/len(vehicles)*100:.1f}%)\n")
        if outliers_low > 0:
            f.write(f"Slow outliers (< {p_low}th %ile):     {outliers_low:4d} vehicles ({outliers_low/len(vehicles)*100:.1f}%)\n")
        if outliers_high > 0:
            f.write(f"Fast outliers (> {p_high}th %ile):    {outliers_high:4d} vehicles ({outliers_high/len(vehicles)*100:.1f}%)\n")
        
        # Clustering within normal range
        mid_point = len(bin_counts[1:-1]) // 2
        top_half_normal = sum(bin_counts[1 + mid_point:-1])
        bottom_half_normal = sum(bin_counts[1:1 + mid_point])
        top_half_pct = top_half_normal / normal_traffic * 100 if normal_traffic > 0 else 0
        
        f.write(f"\nWithin normal range:\n")
        f.write(f"  Lower half: {bottom_half_normal:4d} vehicles ({100-top_half_pct:5.1f}%)\n")
        f.write(f"  Upper half: {top_half_normal:4d} vehicles ({top_half_pct:5.1f}%)\n\n")
        
        # Interpretation
        f.write(f"INTERPRETATION\n")
        f.write(f"-"*70 + "\n")
        
        if outliers_high > len(vehicles) * 0.05:
            f.write(f"⚠️  EXCESSIVE SPEEDING\n")
            f.write(f"   {outliers_high} vehicles ({outliers_high/len(vehicles)*100:.1f}%) above {p_high}th percentile\n")
        elif top_half_pct > clustering_thresh:
            f.write(f"⚠️  HIGH-SPEED CLUSTERING\n")
            f.write(f"   {top_half_pct:.1f}% of normal traffic in upper half of range\n")
        elif (100-top_half_pct) > clustering_thresh:
            f.write(f"✓ LOW-SPEED CLUSTERING\n")
            f.write(f"   {100-top_half_pct:.1f}% of normal traffic in lower half of range\n")
        else:
            f.write(f"✓ EVEN DISTRIBUTION\n")
            f.write(f"   Normal traffic spread relatively evenly\n")
        
        # Directional comparison
        if speeds_rtl and speeds_ltr:
            avg_rtl = sum(speeds_rtl) / len(speeds_rtl)
            avg_ltr = sum(speeds_ltr) / len(speeds_ltr)
            
            f.write(f"\nDIRECTIONAL COMPARISON\n")
            f.write(f"-"*70 + "\n")
            f.write(f"RTL (farther lane):  {len(speeds_rtl):4d} vehicles, mean {avg_rtl:6.1f} px/s\n")
            f.write(f"LTR (closer lane):   {len(speeds_ltr):4d} vehicles, mean {avg_ltr:6.1f} px/s\n\n")
            
            diff_pct = abs(avg_rtl - avg_ltr) / min(avg_rtl, avg_ltr) * 100
            if diff_pct > dir_diff_thresh:
                faster = "RTL" if avg_rtl > avg_ltr else "LTR"
                f.write(f"Direction {faster} averages {diff_pct:.1f}% faster\n")
            else:
                f.write(f"Both directions show similar average speeds\n")
        
        f.write("\n" + "="*70 + "\n")


if __name__ == "__main__":
    # Standalone testing
    import yaml
    from multiprocessing import Queue
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    queue = Queue()
    analyze_stream(queue, config)
