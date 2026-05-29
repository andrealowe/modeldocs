#!/usr/bin/env python3
"""
Ground Truth Configuration Upload for Domino Model Monitor

Uploads ground truth dataset configuration to Domino Model Monitor API v2.
Automatically discovers ground truth files from the last 24 hours and registers
them with the model monitoring system.

Usage:
    python upload_ground_truth_config.py                    # Last 24 hours
    python upload_ground_truth_config.py --hours 48         # Last 48 hours
    python upload_ground_truth_config.py --start-date 2025-10-25 --end-date 2025-10-27
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src directory to path for imports
current_dir = Path(__file__).parent
src_paths = [
    str(current_dir.parent),   # /mnt/code/src
    '/mnt/code/src',           # Git-based project
    '/mnt/src',                # File-based project
    '/mnt/code',               # Git root
    '/mnt',                    # File-based root
]
for path in src_paths:
    if path not in sys.path and Path(path).exists():
        sys.path.insert(0, path)

# Import unified configuration
from config_loader import get_config

# Load configuration
config = get_config()

class GroundTruthUploader:
    """Client for uploading ground truth configurations to Domino Model Monitor API v2"""
    
    def __init__(self, config_instance: Optional[object] = None):
        self.config = config_instance or config
        
        # Initialize API settings from config
        self.api_host = self.config.domino_base_url
        self.api_key = self.config.domino_api_key
        
        self.base_url = self.config.model_monitor_api_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Domino-Api-Key": self.api_key
        }
        
        print(f"🔗 Connecting to: {self.api_host}")
        print(f"📋 Model Monitor ID: {self.config.model_monitor_id}")
        print(f"💾 Data Source: {self.config.ground_truth_datasource}")

    def discover_ground_truth_files(self, 
                                   start_date: Optional[datetime] = None, 
                                   end_date: Optional[datetime] = None,
                                   hours_back: Optional[int] = None) -> List[str]:
        """
        Discover ground truth CSV files from the data source within the specified time range.
        Checks multiple path patterns and verifies that files actually exist.
        
        Args:
            start_date: Start date for file discovery (UTC)
            end_date: End date for file discovery (UTC) 
            hours_back: Hours back from now if start_date/end_date not specified
            
        Returns:
            List of file paths that actually exist in the data source
        """
        if hours_back is None:
            hours_back = self.config.default_hours_back
            
        if not start_date or not end_date:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=hours_back)
        
        print(f"🔍 Searching for ground truth files from {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')} UTC")
        
        # Generate date range
        current_date = start_date.date()
        end_date_only = end_date.date()
        date_strings = []
        while current_date <= end_date_only:
            date_strings.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # Define multiple path patterns to check
        path_patterns = [
            # Pattern 1: Current model ID path
            lambda date_str: f"{self.config.ground_truth_prefix}/{self.config.prediction_model_id}/{date_str}.csv",
            # Pattern 2: Old model ID path (from copy function default)
            lambda date_str: f"{self.config.ground_truth_prefix}/68eda1eb2500c81ff5fed203/{date_str}.csv",
            # Pattern 3: Direct under ground_truth (no model ID)
            lambda date_str: f"{self.config.ground_truth_prefix}/{date_str}.csv"
        ]
        
        # Generate all potential file paths
        potential_file_paths = []
        for date_str in date_strings:
            for pattern in path_patterns:
                potential_file_paths.append(pattern(date_str))
        
        print(f"📂 Generated {len(potential_file_paths)} potential file paths to check")
        
        # Verify files actually exist in the data source
        try:
            from domino.data_sources import DataSourceClient
            object_store = DataSourceClient().get_datasource(self.config.ground_truth_datasource)
            objects = object_store.list_objects()
            existing_files = {obj.key for obj in objects}
            
            verified_files = []
            found_dates = set()
            
            # Check each potential path and only keep one file per date (prioritize current model ID path)
            for date_str in date_strings:
                date_found = False
                for pattern in path_patterns:
                    file_path = pattern(date_str)
                    if file_path in existing_files and date_str not in found_dates:
                        verified_files.append(file_path)
                        found_dates.add(date_str)
                        print(f"   ✅ Found: {file_path}")
                        date_found = True
                        break  # Use first matching pattern (prioritized order)
                
                if not date_found:
                    print(f"   ❌ No file found for date: {date_str}")
            
            print(f"📊 File verification: {len(verified_files)} files found for {len(date_strings)} dates")
            return verified_files
            
        except Exception as e:
            print(f"⚠️  Could not verify file existence in data source: {e}")
            print(f"   Returning current model ID paths (fallback behavior)")
            return [self.config.get_ground_truth_file_path(date_str) for date_str in date_strings]

    def create_ground_truth_config(self, file_path: str) -> Dict[str, Any]:
        """
        Create ground truth dataset configuration payload for API upload.
        
        Args:
            file_path: Path to the ground truth CSV file in the data source
            
        Returns:
            Configuration payload for API
        """
        # Extract filename from path for dataset name
        filename = Path(file_path).name
        # Create unique dataset name with timestamp to avoid conflicts
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        dataset_name = f"seabed_ground_truth_{self.config.model_monitor_id}_{filename.replace('.csv', '')}_{timestamp}"
        
        # Only include datasetDetails - variables are already configured
        payload = {
            "datasetDetails": {
                "name": dataset_name,
                "datasetType": "file",
                "datasetConfig": {
                    "path": file_path,
                    "fileFormat": "csv"
                },
                "datasourceName": self.config.ground_truth_datasource,
                "datasourceType": "s3"
            }
        }
        
        return payload

    def upload_ground_truth_config(self, config: Dict[str, Any]) -> bool:
        """
        Upload ground truth configuration to Model Monitor API.
        
        Args:
            config: Ground truth configuration payload
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/model/{self.config.model_monitor_id}/register-dataset/ground_truth"
        file_path = config["datasetDetails"]["datasetConfig"]["path"]
        
        print(f"📤 Uploading configuration for: {file_path}")
        
        try:
            response = requests.put(
                url,
                headers=self.headers,
                json=config,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Successfully registered: {file_path}")
                return True
            elif response.status_code == 409:
                print(f"ℹ️  Already registered: {file_path}")
                return True
            else:
                print(f"❌ Failed to register: {file_path}")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error uploading {file_path}: {e}")
            return False

    def upload_files_in_range(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None, 
                             hours_back: int = 24) -> Dict[str, int]:
        """
        Upload ground truth configurations for all files in the specified time range.
        
        Args:
            start_date: Start date for file discovery (UTC)
            end_date: End date for file discovery (UTC)
            hours_back: Hours back from now if dates not specified
            
        Returns:
            Dictionary with counts of successful/failed uploads
        """
        # Discover files in the time range
        file_paths = self.discover_ground_truth_files(start_date, end_date, hours_back)
        
        if not file_paths:
            print("⚠️  No ground truth files found in the specified time range")
            return {"successful": 0, "failed": 0, "total": 0}
        
        successful = 0
        failed = 0
        
        print(f"\n🚀 Starting upload process for {len(file_paths)} files...")
        
        for file_path in file_paths:
            print(f"\n📋 Processing: {file_path}")
            
            # Create configuration for this file
            config = self.create_ground_truth_config(file_path)
            
            # Upload configuration
            if self.upload_ground_truth_config(config):
                successful += 1
            else:
                failed += 1
        
        print(f"\n📊 Upload Summary:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📁 Total: {len(file_paths)}")
        
        return {
            "successful": successful,
            "failed": failed, 
            "total": len(file_paths)
        }

    def copy_ground_truth_files_to_correct_path(self,
                                               source_model_id: str = "68eda1eb2500c81ff5fed203",
                                               target_model_id: str = None) -> Dict[str, int]:
        """
        Copy existing ground truth files from old model ID path to new model ID path.
        
        Args:
            source_model_id: Old model ID path to copy from
            target_model_id: New model ID path to copy to (defaults to MODEL_MONITOR_ID)
            
        Returns:
            Dictionary with counts of copied files
        """
        if not target_model_id:
            target_model_id = self.config.prediction_model_id
            
        print(f"📁 Copying ground truth files:")
        print(f"   From: ground_truth/{source_model_id}/")
        print(f"   To:   ground_truth/{target_model_id}/")
        
        try:
            from domino.data_sources import DataSourceClient
            import io
            
            # Get data source client
            object_store = DataSourceClient().get_datasource(self.config.ground_truth_datasource)
            
            # List all objects
            objects = object_store.list_objects()
            object_keys = [obj.key for obj in objects]
            
            # Find files with the source model ID
            source_files = [key for key in object_keys if key.startswith(f"ground_truth/{source_model_id}/")]
            
            if not source_files:
                print(f"⚠️  No files found for source model ID: {source_model_id}")
                return {"copied": 0, "failed": 0, "total": 0}
            
            print(f"🔍 Found {len(source_files)} files to copy:")
            for f in source_files:
                print(f"   - {f}")
            
            copied = 0
            failed = 0
            
            for source_file in source_files:
                try:
                    # Extract date part from filename
                    filename = Path(source_file).name
                    target_file = f"ground_truth/{target_model_id}/{filename}"
                    
                    print(f"📋 Copying: {source_file} -> {target_file}")
                    
                    # Download source file content
                    file_content = object_store.get(source_file)
                    
                    # Upload to new location using bytes
                    object_store.put(target_file, file_content)
                    
                    print(f"✅ Successfully copied: {filename}")
                    copied += 1
                    
                except Exception as e:
                    print(f"❌ Failed to copy {source_file}: {e}")
                    failed += 1
            
            print(f"\n📊 Copy Summary:")
            print(f"   ✅ Copied: {copied}")
            print(f"   ❌ Failed: {failed}")
            print(f"   📁 Total: {len(source_files)}")
            
            return {"copied": copied, "failed": failed, "total": len(source_files)}
            
        except Exception as e:
            print(f"❌ Error accessing data source: {e}")
            return {"copied": 0, "failed": 0, "total": 0}


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format to UTC datetime"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    """Command-line interface for ground truth upload"""
    parser = argparse.ArgumentParser(
        description="Upload ground truth configurations to Domino Model Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload ground truth files from last 24 hours
  python upload_ground_truth_config.py
  
  # Upload files from last 48 hours  
  python upload_ground_truth_config.py --hours 48
  
  # Upload files from specific date range
  python upload_ground_truth_config.py --start-date 2025-10-25 --end-date 2025-10-27
  
  # Test with dry run (shows what would be uploaded)
  python upload_ground_truth_config.py --dry-run

Environment Variables:
  DOMINO_USER_API_KEY    Required: Your Domino API key
        """
    )
    
    # Time range options
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument(
        '--hours', 
        type=int, 
        default=None,
        help=f'Hours back from now to search for files (default: {config.default_hours_back})'
    )
    time_group.add_argument(
        '--date-range',
        action='store_true',
        help='Use --start-date and --end-date instead of --hours'
    )
    
    parser.add_argument(
        '--start-date',
        type=parse_date,
        help='Start date for file search (YYYY-MM-DD format, UTC)'
    )
    parser.add_argument(
        '--end-date', 
        type=parse_date,
        help='End date for file search (YYYY-MM-DD format, UTC)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be uploaded without actually uploading'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true', 
        help='Show detailed output'
    )
    
    args = parser.parse_args()
    
    # Validate date range arguments
    if args.date_range or args.start_date or args.end_date:
        if not (args.start_date and args.end_date):
            parser.error("Both --start-date and --end-date are required when using date range")
        if args.start_date > args.end_date:
            parser.error("Start date must be before end date")
    
    print("🔬 Seabed Object Detection - Ground Truth Configuration Upload")
    print("=" * 70)
    
    # Check API key
    api_key = os.environ.get('DOMINO_USER_API_KEY')
    if not api_key:
        print("❌ Error: DOMINO_USER_API_KEY environment variable not set")
        print("💡 Get your API key from: Account Settings → API Keys in Domino UI")
        sys.exit(1)
    
    try:
        # Create uploader client
        uploader = GroundTruthUploader()
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No files will be uploaded")
            
            # Just discover files to show what would be processed
            if args.start_date and args.end_date:
                files = uploader.discover_ground_truth_files(args.start_date, args.end_date)
            else:
                files = uploader.discover_ground_truth_files(hours_back=args.hours or config.default_hours_back)
            
            print(f"\n📋 Would process {len(files)} files:")
            for file_path in files:
                print(f"   - {file_path}")
            
        else:
            # Perform actual upload
            if args.start_date and args.end_date:
                results = uploader.upload_files_in_range(args.start_date, args.end_date)
            else:
                results = uploader.upload_files_in_range(hours_back=args.hours or config.default_hours_back)
            
            if results["failed"] > 0:
                print(f"\n⚠️  {results['failed']} uploads failed. Check the logs above for details.")
                sys.exit(1)
            elif results["successful"] > 0:
                print(f"\n🎉 All {results['successful']} configurations uploaded successfully!")
            else:
                print(f"\n💡 No files found to upload in the specified time range.")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()