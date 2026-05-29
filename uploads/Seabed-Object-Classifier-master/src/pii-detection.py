#!/usr/bin/env python3
"""
PII Detection Script for Domino Data Lab
Searches files in DOMINO_WORKING_DIR for common PII patterns
"""

import os
import re
import sys
from pathlib import Path

# Common PII patterns to detect
PII_PATTERNS = {
    'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
    'Email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'Phone': r'\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b',
    'Credit Card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    'IP Address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'Date of Birth': r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
    'Passport': r'\b[A-Z]{1,2}\d{6,9}\b',
    'Driver License': r'\b[A-Z]\d{7,8}\b',
}

# Keywords that might indicate PII
PII_KEYWORDS = [
    'ssn', 'social security', 'password', 'passcode', 'pin',
    'credit card', 'account number', 'routing number',
    'date of birth', 'dob', 'driver license', 'passport',
    'maiden name', 'tax id', 'national id'
]

# File extensions to scan
SCANNABLE_EXTENSIONS = {'.txt', '.csv', '.json', '.xml', '.log', '.py', '.sql', '.md'}

def scan_file(filepath):
    """Scan a single file for PII patterns and keywords"""
    findings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # Check for regex patterns
            for pii_type, pattern in PII_PATTERNS.items():
                matches = re.findall(pattern, content)
                if matches:
                    findings.append({
                        'type': pii_type,
                        'pattern': 'regex',
                        'count': len(matches),
                        'samples': matches[:3]  # Show first 3 matches
                    })
            
            # Check for keywords (case-insensitive)
            content_lower = content.lower()
            for keyword in PII_KEYWORDS:
                if keyword in content_lower:
                    findings.append({
                        'type': 'Keyword',
                        'pattern': keyword,
                        'count': content_lower.count(keyword)
                    })
    
    except Exception as e:
        return None, str(e)
    
    return findings, None

def scan_directory(directory):
    """Recursively scan directory for PII"""
    results = {}
    error_count = 0
    
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common non-data directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'__pycache__', 'node_modules'}]
        
        for file in files:
            filepath = Path(root) / file
            
            # Only scan relevant file types
            if filepath.suffix.lower() not in SCANNABLE_EXTENSIONS:
                continue
            
            findings, error = scan_file(filepath)
            
            if error:
                error_count += 1
                continue
            
            if findings:
                results[str(filepath)] = findings
    
    return results, error_count

def print_results(results, error_count):
    """Print scan results in a readable format"""
    print("=" * 80)
    print("PII DETECTION SCAN RESULTS")
    print("=" * 80)
    print()
    
    if not results:
        print("✓ No PII patterns detected in scanned files.")
    else:
        print(f"⚠ WARNING: Found PII patterns in {len(results)} file(s)")
        print()
        
        for filepath, findings in results.items():
            print(f"\nFile: {filepath}")
            print("-" * 80)
            
            for finding in findings:
                if finding['pattern'] == 'regex':
                    print(f"  • {finding['type']}: {finding['count']} occurrence(s)")
                    if 'samples' in finding:
                        print(f"    Samples: {', '.join(str(s) for s in finding['samples'])}")
                else:
                    print(f"  • Keyword '{finding['pattern']}': {finding['count']} occurrence(s)")
    
    print()
    print("=" * 80)
    print(f"Files scanned: {sum(1 for _ in Path(os.environ['DOMINO_WORKING_DIR']).rglob('*') if _.is_file() and _.suffix.lower() in SCANNABLE_EXTENSIONS)}")
    if error_count > 0:
        print(f"Files with read errors: {error_count}")
    print("=" * 80)
    
    # Return exit code
    return 1 if results else 0

def main():
    # Get the working directory from environment variable
    working_dir = os.environ.get('DOMINO_WORKING_DIR')
    
    if not working_dir:
        print("ERROR: DOMINO_WORKING_DIR environment variable not set")
        sys.exit(1)
    
    if not os.path.isdir(working_dir):
        print(f"ERROR: Directory does not exist: {working_dir}")
        sys.exit(1)
    
    print(f"Scanning directory: {working_dir}")
    print("This may take a few moments...")
    print()
    
    results, error_count = scan_directory(working_dir)
    exit_code = print_results(results, error_count)
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
