import pandas as pd
import numpy as np
import time
import re
import json
from typing import Optional, Tuple, Dict
import google.genai as genai
from google.genai import types
import os
from datetime import datetime

# Import your existing functions
import sys
sys.path.append('app')  # Adjust path as needed
from .ai_evaluate import build_prompt, run_eval
from .ai_handler import ConfigManager

class AIRewriteTester:
    def __init__(self, csv_path: str, api_key: str = None, config_path: str = 'app/AIConfig.json'):
        """
        Initialize the AI Rewrite Tester
        
        Args:
            csv_path: Path to the Units Outcomes CSV file
            api_key: Google API key (if None, uses environment variable)
            config_path: Path to AI configuration JSON
        """
        self.csv_path = csv_path
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.getCurrentParams()
        
        # Setup API key
        if api_key:
            self.api_key = api_key
        elif self.config["API_key"] == 'environ':
            self.api_key = os.getenv("GOOGLE_API_KEY")
        else:
            self.api_key = self.config["API_key"]
            
        if not self.api_key:
            raise ValueError("No API key found. Set GOOGLE_API_KEY environment variable or provide api_key parameter")
        
        # Configure genai client
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = self.config["selected_model"]
        
        # Rate limiting parameters
        self.delay_between_requests = 2  # seconds
        self.max_retries = 3
        self.retry_delay = 60  # seconds to wait if rate limited
        
    def load_and_sample_data(self, sample_size: float = 0.2) -> pd.DataFrame:
        """
        Load CSV and sample 20% of rows with outcomes
        
        Returns:
            DataFrame with sampled data
        """
        print(f"Loading data from {self.csv_path}...")
        df = pd.read_csv(self.csv_path)
        
        # Filter rows that have outcomes (not NaN or empty)
        df_with_outcomes = df[df['Outcomes'].notna() & (df['Outcomes'] != '')].copy()
        
        print(f"Total rows with outcomes: {len(df_with_outcomes)}")
        
        # Sample 20%
        sample_size = int(len(df_with_outcomes) * sample_size)
        df_sample = df_with_outcomes.sample(n=min(sample_size, len(df_with_outcomes)), random_state=42)
        
        print(f"Sampled {len(df_sample)} rows for testing")
        
        return df_sample
    
    def parse_evaluation_response(self, response_text: str) -> Dict[str, list]:
        """
        Parse the AI evaluation response to extract suggestions
        
        Returns:
            Dict with outcomes and their suggestions
        """
        results = {
            'outcomes': [],
            'statuses': [],
            'suggestions': []
        }
        
        # Split response into lines
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for outcome evaluations with the pattern:
            # 'outcome' - STATUS:[STATUS] - feedback... SUGGESTION: 'suggestion'
            
            # First try to match quoted outcomes
            outcome_match = re.match(r"^['\"](.+?)['\"].*?STATUS:\s*(\w+)", line, re.IGNORECASE)
            
            if outcome_match:
                outcome_text = outcome_match.group(1)
                status = outcome_match.group(2).upper()
                
                # Extract suggestion if present
                suggestion_match = re.search(r"SUGGESTION:\s*['\"]?([^'\"]+)['\"]?", line, re.IGNORECASE)
                suggestion = suggestion_match.group(1).strip() if suggestion_match else None
                
                results['outcomes'].append(outcome_text)
                results['statuses'].append(status)
                results['suggestions'].append(suggestion)
        
        return results
    
    def evaluate_single_outcome(self, unit_name: str, level: int, outcome: str, 
                                credit_points: int = 6) -> Optional[str]:
        """
        Evaluate a single outcome and extract suggested revision
        
        Returns:
            Suggested revision or None if outcome is good
        """
        for attempt in range(self.max_retries):
            try:
                # Build prompt using existing function
                prompt = build_prompt(level, unit_name, credit_points, [outcome], self.config)
                
                # Generate response
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                
                response_text = getattr(resp, "text", "")
                
                if not response_text:
                    print(f"  Warning: No response for outcome: {outcome[:50]}...")
                    return None
                
                # Parse response
                parsed = self.parse_evaluation_response(response_text)
                
                # Get the first suggestion (should only be one outcome)
                if parsed['suggestions'] and parsed['suggestions'][0]:
                    # Only return suggestion if status is NEEDS_REVISION or COULD_IMPROVE
                    if parsed['statuses'] and parsed['statuses'][0] in ['NEEDS_REVISION', 'COULD_IMPROVE']:
                        return parsed['suggestions'][0]
                
                return None  # Outcome is GOOD, no revision needed
                
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    print(f"  Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"  Max retries reached. Skipping this outcome.")
                    return None
    
    def compare_outcomes(self, original: str, rewritten: str, 
                        unit_name: str, level: int) -> str:
        """
        Compare original and rewritten outcomes to determine if rewrite is GOOD or BAD
        
        Returns:
            'GOOD' or 'BAD' evaluation
        """
        comparison_prompt = f"""You are evaluating the quality of a rewritten learning outcome.

Unit: {unit_name}
Level: {level}

ORIGINAL OUTCOME: "{original}"
REWRITTEN OUTCOME: "{rewritten}"

Evaluate if the REWRITTEN outcome is an improvement over the ORIGINAL by considering:
1. Does it use more appropriate action verbs for Level {level}?
2. Is it more specific and measurable?
3. Does it better align with Bloom's Taxonomy level requirements?
4. Is it clearer and more actionable?

Respond with EXACTLY one word: either "GOOD" if the rewrite is an improvement or maintains quality, or "BAD" if the rewrite is worse or introduces problems.

YOUR RESPONSE (one word only):"""
        
        for attempt in range(self.max_retries):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=comparison_prompt,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                
                response_text = getattr(resp, "text", "").strip().upper()
                
                # Extract GOOD or BAD from response
                if "GOOD" in response_text:
                    return "GOOD"
                elif "BAD" in response_text:
                    return "BAD"
                else:
                    # Default to UNKNOWN if can't parse
                    print(f"  Warning: Unexpected comparison response: {response_text}")
                    return "UNKNOWN"
                    
            except Exception as e:
                print(f"  Comparison attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return "ERROR"
    
    def process_unit(self, row: pd.Series) -> Dict:
        """
        Process a single unit row
        
        Returns:
            Dictionary with results
        """
        result = {
            'unitcode': row['code'],
            'title': row['title'],
            'level': row['level'],
            'original_outcomes': row['Outcomes'],
            'rewritten_outcome': None,
            'evaluation': None,
            'processing_time': None
        }
        
        start_time = time.time()
        
        # Parse outcomes (handle the |*| delimiter)
        outcomes = str(row['Outcomes']).split('|*|')
        
        # For testing, just use the first outcome if multiple exist
        first_outcome = outcomes[0].strip() if outcomes else ""
        
        # Remove assessment part if present (after | delimiter)
        if '|' in first_outcome:
            first_outcome = first_outcome.split('|')[0].strip()
        
        if not first_outcome:
            print(f"  No valid outcome found for {row['code']}")
            result['evaluation'] = 'NO_OUTCOME'
            return result
        
        print(f"  Evaluating outcome: {first_outcome[:50]}...")
        
        # Get suggested revision
        suggested_revision = self.evaluate_single_outcome(
            unit_name=row['title'],
            level=int(row['level']),
            outcome=first_outcome,
            credit_points=6  # Default since not in dataset
        )
        
        # Rate limiting delay
        time.sleep(self.delay_between_requests)
        
        if suggested_revision:
            result['rewritten_outcome'] = suggested_revision
            
            print(f"  Comparing original vs rewritten...")
            
            # Compare original vs rewritten
            evaluation = self.compare_outcomes(
                original=first_outcome,
                rewritten=suggested_revision,
                unit_name=row['title'],
                level=int(row['level'])
            )
            
            result['evaluation'] = evaluation
            
            # Rate limiting delay
            time.sleep(self.delay_between_requests)
        else:
            result['evaluation'] = 'ALREADY_GOOD'
            print(f"  Outcome already good, no revision needed")
        
        result['processing_time'] = time.time() - start_time
        
        return result
    
    def run_test(self, output_path: str = None, sample_size: float = 0.2) -> pd.DataFrame:
        """
        Run the complete test
        
        Args:
            output_path: Path to save results CSV (optional)
            sample_size: Fraction of data to sample (default 0.2 for 20%)
            
        Returns:
            DataFrame with results
        """
        print("=" * 80)
        print("AI REWRITE QUALITY TESTING")
        print("=" * 80)
        
        # Load and sample data
        df_sample = self.load_and_sample_data(sample_size)
        
        # Estimate processing time
        total_api_calls = len(df_sample) * 2  # One for evaluation, one for comparison
        estimated_time = total_api_calls * (self.delay_between_requests + 2)  # +2 sec for processing
        print(f"\nEstimated API calls: {total_api_calls}")
        print(f"Estimated processing time: {estimated_time/60:.1f} minutes")
        print("-" * 80)
        
        # Process each unit
        results = []
        
        for idx, (_, row) in enumerate(df_sample.iterrows(), 1):
            print(f"\nProcessing {idx}/{len(df_sample)}: {row['code']} - {row['title']}")
            
            try:
                result = self.process_unit(row)
                results.append(result)
                
                # Progress update
                if idx % 10 == 0:
                    elapsed = sum(r['processing_time'] for r in results if r['processing_time'])
                    remaining_items = len(df_sample) - idx
                    avg_time = elapsed / idx
                    eta = remaining_items * avg_time
                    print(f"\n>>> Progress: {idx}/{len(df_sample)} completed")
                    print(f">>> ETA: {eta/60:.1f} minutes remaining")
                    
            except KeyboardInterrupt:
                print("\n\nTesting interrupted by user")
                break
            except Exception as e:
                print(f"  Error processing unit: {str(e)}")
                results.append({
                    'unitcode': row['code'],
                    'title': row['title'],
                    'level': row['level'],
                    'original_outcomes': row['Outcomes'],
                    'rewritten_outcome': None,
                    'evaluation': 'ERROR',
                    'processing_time': None
                })
        
        # Create results DataFrame
        df_results = pd.DataFrame(results)
        
        # Add summary statistics
        print("\n" + "=" * 80)
        print("TESTING COMPLETE")
        print("=" * 80)
        print(f"Total units processed: {len(df_results)}")
        print(f"Outcomes needing revision: {(df_results['rewritten_outcome'].notna()).sum()}")
        print(f"Already good outcomes: {(df_results['evaluation'] == 'ALREADY_GOOD').sum()}")
        print(f"Good rewrites: {(df_results['evaluation'] == 'GOOD').sum()}")
        print(f"Bad rewrites: {(df_results['evaluation'] == 'BAD').sum()}")
        print(f"Errors: {(df_results['evaluation'] == 'ERROR').sum()}")
        
        # Calculate success rate
        total_rewrites = (df_results['evaluation'].isin(['GOOD', 'BAD'])).sum()
        if total_rewrites > 0:
            success_rate = (df_results['evaluation'] == 'GOOD').sum() / total_rewrites * 100
            print(f"\nRewrite Success Rate: {success_rate:.1f}%")
        
        # Save results
        if output_path:
            df_results.to_csv(output_path, index=False)
            print(f"\nResults saved to: {output_path}")
        
        return df_results


# Main execution
if __name__ == "__main__":
    # Configuration
    CSV_PATH = "UnitsOutcomes.csv"  # Path to your CSV file
    OUTPUT_PATH = f"ai_rewrite_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Optional: Set API key directly or use environment variable
    API_KEY = None  # Set to your API key or leave None to use environment variable
    
    # Create tester instance
    tester = AIRewriteTester(
        csv_path=CSV_PATH,
        api_key=API_KEY
    )
    
    # Optional: Adjust rate limiting if needed
    tester.delay_between_requests = 3  # Increase delay if hitting rate limits
    
    # Run test with smaller sample for testing (e.g., 0.01 for 1% = ~70 units)
    # Change to 0.2 for full 20% test
    results_df = tester.run_test(
        output_path=OUTPUT_PATH,
        sample_size=0.01  # Start with 1% for testing, then increase to 0.2
    )
    
    # Display first few results
    print("\nSample Results:")
    print(results_df.head())
    
    # Detailed analysis
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)
    
    # Group by level
    print("\nResults by Level:")
    level_summary = results_df.groupby('level')['evaluation'].value_counts().unstack(fill_value=0)
    print(level_summary)
    
    # Show some examples of rewrites
    print("\n" + "=" * 80)
    print("EXAMPLE REWRITES")
    print("=" * 80)
    
    good_rewrites = results_df[results_df['evaluation'] == 'GOOD'].head(3)
    for _, row in good_rewrites.iterrows():
        print(f"\nUnit: {row['unitcode']} - {row['title']}")
        print(f"Level: {row['level']}")
        print(f"Original: {row['original_outcomes'][:100]}...")
        print(f"Rewritten: {row['rewritten_outcome']}")
        print(f"Evaluation: {row['evaluation']}")
        print("-" * 40)
