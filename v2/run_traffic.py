#!/usr/bin/env python3
"""
Traffic Analysis System
Runs detection and analysis as parallel processes with shared queue.

Usage:
    python run_traffic.py [hours]
    
Examples:
    python run_traffic.py 1      # Run for 1 hour
    python run_traffic.py 0.5    # Run for 30 minutes
    python run_traffic.py 3      # Run for 3 hours
"""

import sys
import time
import yaml

# Load configuration FIRST (before importing other modules)
try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print("Configuration loaded from config.yaml")
except FileNotFoundError:
    print("ERROR: config.yaml not found")
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"ERROR: Invalid YAML in config.yaml: {e}")
    sys.exit(1)

# Import detection/analysis modules AFTER config is loaded
try:
    from detect_cars import run_detection
    from analyze import analyze_stream
except ImportError as e:
    print(f"ERROR: Failed to import modules: {e}")
    print(f"Make sure detect_cars.py and analyze.py are in the same directory")
    sys.exit(1)

from multiprocessing import Process, Queue


def run_detector(queue, config):
    """Wrapper for detection process"""
    run_detection(queue, config)


def run_analyzer(queue, config):
    """Wrapper for analysis process"""
    analyze_stream(queue, config)


def main():
    # Parse duration argument
    if len(sys.argv) > 1:
        try:
            duration_hours = float(sys.argv[1])
        except ValueError:
            print(f"ERROR: Invalid duration '{sys.argv[1]}'")
            print(f"Usage: python run_traffic.py [hours]")
            sys.exit(1)
    else:
        duration_hours = config['runtime']['default_duration_hours']
    
    duration_seconds = int(duration_hours * 3600)
    
    print("="*70)
    print("TRAFFIC ANALYSIS SYSTEM")
    print("="*70)
    print(f"Duration: {duration_hours} hour(s) ({duration_seconds/60:.0f} minutes)")
    print(f"Camera: {config['camera']['url']}")
    print(f"Model: {config['detection']['model_file']}")
    print(f"Press Ctrl+C to stop early")
    print("="*70)
    print()
    
    # Create shared queue
    queue = Queue()
    
    # Start analyzer first (consumer must be ready)
    analyzer = Process(target=run_analyzer, args=(queue, config), name="Analyzer")
    analyzer.start()
    
    time.sleep(config['runtime']['analyzer_startup_delay'])
    
    # Start detector
    detector = Process(target=run_detector, args=(queue, config), name="Detector")
    detector.start()
    
    # Wait for duration or interruption
    try:
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed >= duration_seconds:
                print(f"\n{'='*70}")
                print(f"Time's up! Stopping after {elapsed/60:.1f} minutes")
                print(f"{'='*70}")
                break
            
            time.sleep(1)
            
            # Check if detector died
            if not detector.is_alive():
                print(f"\nDetector process ended")
                break
    
    except KeyboardInterrupt:
        print(f"\n{'='*70}")
        print(f"Interrupted by user")
        print(f"{'='*70}")
    
    # Gracefully stop detector
    if detector.is_alive():
        print(f"\nStopping detector...")
        detector.terminate()
        detector.join(timeout=config['runtime']['detector_shutdown_timeout'])
        
        if detector.is_alive():
            print(f"  Detector not responding, forcing...")
            detector.kill()
            detector.join()
    
    # Wait for analyzer to finish processing queue
    print(f"Waiting for analyzer to complete...")
    analyzer.join(timeout=config['runtime']['analyzer_shutdown_timeout'])
    
    if analyzer.is_alive():
        print(f"  Analyzer timeout, forcing...")
        analyzer.terminate()
        analyzer.join()
    
    print(f"\n{'='*70}")
    print(f"COMPLETE")
    print(f"{'='*70}")
    print(f"Check output files:")
    print(f"  {config['output']['csv_dir']}/traffic_data_YYYYMMDD_HHMMSS.csv")
    print(f"  {config['output']['reports_dir']}/traffic_analysis_YYYYMMDD_HHMMSS.txt")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
