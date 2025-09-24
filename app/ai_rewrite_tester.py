import pandas as pd
import numpy as np
import time
import re
import json
from typing import Optional, Tuple, Dict, List
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
        
    def parse_outcomes_from_csv(self, outcomes_str: str) -> List[Dict]:
        """
        Parse outcomes string from CSV into list of outcome dictionaries
        
        Args:
            outcomes_str: Raw outcomes string with |*| and | delimiters
            
        Returns:
            List of dicts with outcome text and assessment
        """
        if pd.isna(outcomes_str) or outcomes_str == '':
            return []
        
        outcomes = []
        outcome_parts = str(outcomes_str).split('|*|')
        
        for idx, outcome_full in enumerate(outcome_parts):
            outcome_full = outcome_full.strip()
            if not outcome_full:
                continue
            
            # Split outcome and assessment
            if '|' in outcome_full:
                parts = outcome_full.split('|')
                outcome_text = parts[0].strip()
                assessment = parts[1].strip() if len(parts) > 1 else ''
            else:
                outcome_text = outcome_full
                assessment = ''
            
            if outcome_text:
                outcomes.append({
                    'number': idx + 1,
                    'text': outcome_text,
                    'assessment': assessment
                })
        
        return outcomes
        
    def load_and_sample_units(self, sample_size: float = 0.2) -> pd.DataFrame:
        """
        Load CSV and sample units (not individual outcomes)
        
        Returns:
            DataFrame with sampled units
        """
        print(f"Loading data from {self.csv_path}...")
        df = pd.read_csv(self.csv_path)
        
        # Filter units that have outcomes
        df_with_outcomes = df[df['Outcomes'].notna() & (df['Outcomes'] != '')].copy()
        print(f"Total units with outcomes: {len(df_with_outcomes)}")
        
        # Count total outcomes
        total_outcomes = 0
        for _, row in df_with_outcomes.iterrows():
            outcomes = self.parse_outcomes_from_csv(row['Outcomes'])
            total_outcomes += len(outcomes)
        print(f"Total individual outcomes: {total_outcomes}")
        
        # Sample units
        sample_units = int(len(df_with_outcomes) * sample_size)
        df_sampled = df_with_outcomes.sample(n=min(sample_units, len(df_with_outcomes)), random_state=42)
        
        # Count outcomes in sample
        sampled_outcomes = 0
        for _, row in df_sampled.iterrows():
            outcomes = self.parse_outcomes_from_csv(row['Outcomes'])
            sampled_outcomes += len(outcomes)
        
        print(f"Sampled {len(df_sampled)} units containing {sampled_outcomes} outcomes")
        
        return df_sampled
    
    def parse_ai_evaluation(self, response_text: str, original_outcomes: List[str]) -> List[Dict]:
        """
        Parse AI evaluation response for multiple outcomes
        
        Args:
            response_text: AI response text
            original_outcomes: List of original outcome texts for matching
            
        Returns:
            List of parsed evaluations
        """
        evaluations = []
        
        # Create a mapping of original outcomes (normalized) to their index
        outcome_map = {}
        for idx, outcome in enumerate(original_outcomes):
            # Normalize for matching (remove extra spaces, lowercase for key)
            normalized = ' '.join(outcome.split()).lower()
            outcome_map[normalized] = idx
        
        # Split response into lines
        lines = response_text.split('\n')
        
        current_eval = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for outcome evaluation pattern
            # Pattern: 'outcome text' - STATUS:XXX - feedback... SUGGESTION: 'suggestion'
            
            # Try to extract quoted text at beginning of line
            quote_match = re.match(r"^['\"](.+?)['\"]", line)
            
            if quote_match:
                # Save previous evaluation if exists
                if current_eval:
                    evaluations.append(current_eval)
                
                # Start new evaluation
                quoted_text = quote_match.group(1)
                
                # Try to match with original outcomes
                normalized_quoted = ' '.join(quoted_text.split()).lower()
                
                # Find best match
                best_match_idx = None
                best_match_score = 0
                
                for norm_outcome, idx in outcome_map.items():
                    # Check if quoted text is contained in original or vice versa
                    if normalized_quoted in norm_outcome or norm_outcome in normalized_quoted:
                        score = len(normalized_quoted) if normalized_quoted in norm_outcome else len(norm_outcome)
                        if score > best_match_score:
                            best_match_score = score
                            best_match_idx = idx
                
                # Extract status
                status_match = re.search(r"STATUS:\s*(\w+)", line, re.IGNORECASE)
                status = status_match.group(1).upper() if status_match else "UNKNOWN"
                
                # Extract suggestion if present
                suggestion_match = re.search(r"SUGGESTION:\s*['\"]?([^'\"]+)['\"]?", line, re.IGNORECASE)
                suggestion = suggestion_match.group(1).strip() if suggestion_match else None
                
                # Extract feedback (everything between status and suggestion)
                feedback = line
                if status_match:
                    feedback = line[status_match.end():].strip()
                    if feedback.startswith('-'):
                        feedback = feedback[1:].strip()
                if suggestion_match:
                    feedback = feedback[:feedback.lower().find('suggestion:')].strip()
                
                current_eval = {
                    'outcome_index': best_match_idx if best_match_idx is not None else len(evaluations),
                    'quoted_text': quoted_text,
                    'status': status,
                    'feedback': feedback,
                    'suggestion': suggestion
                }
            elif current_eval and line and not line.startswith('**'):
                # Continuation of current evaluation
                if 'SUGGESTION:' in line.upper():
                    suggestion_match = re.search(r"SUGGESTION:\s*['\"]?([^'\"]+)['\"]?", line, re.IGNORECASE)
                    if suggestion_match:
                        current_eval['suggestion'] = suggestion_match.group(1).strip()
                else:
                    current_eval['feedback'] += ' ' + line
        
        # Add last evaluation
        if current_eval:
            evaluations.append(current_eval)
        
        # Sort by outcome index
        evaluations.sort(key=lambda x: x['outcome_index'])
        
        return evaluations
    
    def evaluate_unit_outcomes(self, unit_code: str, unit_name: str, level: int, 
                               outcomes_list: List[Dict], credit_points: int = 6) -> List[Dict]:
        """
        Evaluate all outcomes for a unit in one API call
        
        Args:
            unit_code: Unit code
            unit_name: Unit name  
            level: Unit level
            outcomes_list: List of outcome dictionaries
            credit_points: Credit points for unit
            
        Returns:
            List of evaluation results for each outcome
        """
        # Extract just the outcome texts
        outcome_texts = [o['text'] for o in outcomes_list]
        
        print(f"  Evaluating {len(outcome_texts)} outcomes for {unit_code}...")
        
        for attempt in range(self.max_retries):
            try:
                # Build prompt using existing function with ALL outcomes
                prompt = build_prompt(level, unit_name, credit_points, outcome_texts, self.config)
                
                # Generate response
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                
                response_text = getattr(resp, "text", "")
                
                if not response_text:
                    print(f"    Warning: No response for unit {unit_code}")
                    return [{'status': 'ERROR', 'suggestion': None} for _ in outcomes_list]
                
                # Parse response for all outcomes
                evaluations = self.parse_ai_evaluation(response_text, outcome_texts)
                
                # Map evaluations back to outcomes
                results = []
                for idx, outcome in enumerate(outcomes_list):
                    # Find matching evaluation
                    eval_match = None
                    for eval_item in evaluations:
                        if eval_item['outcome_index'] == idx:
                            eval_match = eval_item
                            break
                    
                    if eval_match:
                        results.append({
                            'outcome_number': outcome['number'],
                            'original_outcome': outcome['text'],
                            'assessment': outcome['assessment'],
                            'status': eval_match['status'],
                            'feedback': eval_match['feedback'],
                            'suggestion': eval_match['suggestion']
                        })
                    else:
                        # No match found
                        results.append({
                            'outcome_number': outcome['number'],
                            'original_outcome': outcome['text'],
                            'assessment': outcome['assessment'],
                            'status': 'NOT_FOUND',
                            'feedback': '',
                            'suggestion': None
                        })
                
                return results
                
            except Exception as e:
                print(f"    Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    print(f"    Waiting {self.retry_delay} seconds before retry...")
                    time.sleep(self.retry_delay)
                else:
                    print(f"    Max retries reached for unit {unit_code}")
                    return [{'status': 'ERROR', 'suggestion': None} for _ in outcomes_list]
    
    def compare_outcomes_batch(self, comparisons: List[Dict], unit_name: str, level: int) -> List[str]:
        """
        Compare multiple original vs rewritten outcomes in one API call
        
        Args:
            comparisons: List of dicts with 'original' and 'rewritten' keys
            unit_name: Unit name
            level: Unit level
            
        Returns:
            List of evaluations ('GOOD' or 'BAD')
        """
        if not comparisons:
            return []
        
        # Build batch comparison prompt
        comparison_prompt = f"""You are evaluating the quality of rewritten learning outcomes.

Unit: {unit_name}
Level: {level}

For each pair below, determine if the REWRITTEN outcome is an improvement over the ORIGINAL.
Consider: appropriate action verbs for Level {level}, specificity, measurability, and clarity.

Respond with exactly one word per pair (GOOD or BAD), one per line, in order.

COMPARISONS:
"""
        
        for i, comp in enumerate(comparisons, 1):
            comparison_prompt += f"\n{i}. ORIGINAL: \"{comp['original']}\""
            comparison_prompt += f"\n   REWRITTEN: \"{comp['rewritten']}\"\n"
        
        comparison_prompt += "\nYOUR RESPONSE (one word per line, in order):"
        
        for attempt in range(self.max_retries):
            try:
                resp = self.client.models.generate_content(
                    model=self.model_name,
                    contents=comparison_prompt,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                
                response_text = getattr(resp, "text", "").strip()
                
                # Parse response - expect one word per line
                evaluations = []
                for line in response_text.split('\n'):
                    line = line.strip().upper()
                    if 'GOOD' in line:
                        evaluations.append('GOOD')
                    elif 'BAD' in line:
                        evaluations.append('BAD')
                    elif line and line in ['GOOD', 'BAD']:
                        evaluations.append(line)
                
                # Pad with UNKNOWN if needed
                while len(evaluations) < len(comparisons):
                    evaluations.append('UNKNOWN')
                
                return evaluations[:len(comparisons)]
                    
            except Exception as e:
                print(f"    Comparison attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return ['ERROR'] * len(comparisons)
    
    def process_unit(self, row: pd.Series) -> List[Dict]:
        """
        Process all outcomes for a single unit
        
        Args:
            row: DataFrame row for a unit
            
        Returns:
            List of result dictionaries (one per outcome)
        """
        start_time = time.time()
        
        # Parse outcomes from CSV format
        outcomes_list = self.parse_outcomes_from_csv(row['Outcomes'])
        
        if not outcomes_list:
            return []
        
        print(f"\nProcessing unit: {row['code']} - {row['title']}")
        print(f"  Level: {row['level']}, Outcomes: {len(outcomes_list)}")
        
        # Evaluate all outcomes in ONE API call
        evaluations = self.evaluate_unit_outcomes(
            unit_code=row['code'],
            unit_name=row['title'],
            level=int(row['level']),
            outcomes_list=outcomes_list
        )
        
        # Rate limiting delay
        time.sleep(self.delay_between_requests)
        
        # Collect outcomes that need comparison
        comparisons_needed = []
        comparison_indices = []
        
        for idx, eval_result in enumerate(evaluations):
            if eval_result.get('suggestion') and eval_result['status'] in ['NEEDS_REVISION', 'COULD_IMPROVE']:
                comparisons_needed.append({
                    'original': eval_result['original_outcome'],
                    'rewritten': eval_result['suggestion']
                })
                comparison_indices.append(idx)
        
        # Batch compare all rewrites for this unit (if any)
        comparison_results = []
        if comparisons_needed:
            print(f"  Comparing {len(comparisons_needed)} suggested revisions...")
            comparison_results = self.compare_outcomes_batch(
                comparisons_needed,
                unit_name=row['title'],
                level=int(row['level'])
            )
            
            # Rate limiting delay
            time.sleep(self.delay_between_requests)
        
        # Build final results
        results = []
        comparison_idx = 0
        
        for eval_idx, eval_result in enumerate(evaluations):
            result = {
                'unitcode': row['code'],
                'title': row['title'], 
                'level': row['level'],
                'outcome_number': eval_result.get('outcome_number', eval_idx + 1),
                'original_outcome': eval_result.get('original_outcome', ''),
                'assessment': eval_result.get('assessment', ''),
                'status': eval_result.get('status', 'UNKNOWN'),
                'feedback': eval_result.get('feedback', ''),
                'rewritten_outcome': eval_result.get('suggestion'),
                'evaluation': None,
                'processing_time': None
            }
            
            # Add comparison result if this outcome was rewritten
            if eval_idx in comparison_indices:
                result['evaluation'] = comparison_results[comparison_idx] if comparison_idx < len(comparison_results) else 'UNKNOWN'
                comparison_idx += 1
            elif eval_result.get('status') == 'GOOD' or not eval_result.get('suggestion'):
                result['evaluation'] = 'ALREADY_GOOD'
            else:
                result['evaluation'] = 'NO_COMPARISON'
            
            results.append(result)
        
        processing_time = (time.time() - start_time) / len(outcomes_list)  # Average per outcome
        for result in results:
            result['processing_time'] = processing_time
        
        return results
    
    def run_test(self, output_path: str = None, sample_size: float = 0.2, 
                 save_incremental: bool = True) -> pd.DataFrame:
        """
        Run the complete test
        
        Args:
            output_path: Path to save results CSV
            sample_size: Fraction of units to sample
            save_incremental: Save progress incrementally
            
        Returns:
            DataFrame with results (one row per outcome)
        """
        print("=" * 80)
        print("AI REWRITE QUALITY TESTING (Batch Mode)")
        print("=" * 80)
        print(f"Sample size: {sample_size * 100}% of units")
        
        # Load and sample units
        df_units = self.load_and_sample_units(sample_size)
        
        # Calculate estimates
        total_units = len(df_units)
        estimated_api_calls = total_units * 2  # One for evaluation, one for comparison per unit
        estimated_time = estimated_api_calls * (self.delay_between_requests + 3)
        
        print(f"\nEstimated API calls: {estimated_api_calls} (2 per unit)")
        print(f"Estimated processing time: {estimated_time/60:.1f} minutes")
        print("-" * 80)
        
        # Process each unit
        all_results = []
        units_processed = 0
        
        for idx, (_, unit_row) in enumerate(df_units.iterrows(), 1):
            try:
                # Process all outcomes for this unit
                unit_results = self.process_unit(unit_row)
                all_results.extend(unit_results)
                units_processed += 1
                
                # Progress update
                print(f"  Completed unit {idx}/{total_units}: {len(unit_results)} outcomes processed")
                
                # Save incremental results
                if save_incremental and idx % 5 == 0:
                    temp_df = pd.DataFrame(all_results)
                    temp_path = output_path.replace('.csv', '_temp.csv') if output_path else 'temp_results.csv'
                    temp_df.to_csv(temp_path, index=False)
                    print(f"  ✓ Saved incremental results ({len(all_results)} outcomes) to {temp_path}")
                
                # ETA update
                if idx % 10 == 0:
                    elapsed_per_unit = sum(r['processing_time'] for r in all_results) / len(all_results) * \
                                      (len(all_results) / units_processed)
                    remaining_units = total_units - idx
                    eta = remaining_units * elapsed_per_unit
                    print(f"\n>>> Progress: {idx}/{total_units} units ({idx/total_units*100:.1f}%)")
                    print(f">>> Total outcomes processed: {len(all_results)}")
                    print(f">>> ETA: {eta/60:.1f} minutes remaining\n")
                    
            except KeyboardInterrupt:
                print("\n\nTesting interrupted by user")
                break
            except Exception as e:
                print(f"  Error processing unit {unit_row['code']}: {str(e)}")
                continue
        
        # Create final DataFrame
        df_results = pd.DataFrame(all_results)
        
        # Reorder columns
        column_order = [
            'unitcode', 'title', 'level', 'outcome_number',
            'original_outcome', 'rewritten_outcome', 'evaluation',
            'status', 'feedback', 'assessment', 'processing_time'
        ]
        column_order = [col for col in column_order if col in df_results.columns]
        df_results = df_results[column_order]
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("TESTING COMPLETE")
        print("=" * 80)
        print(f"Units processed: {units_processed}")
        print(f"Total outcomes evaluated: {len(df_results)}")
        print(f"API calls made: ~{units_processed * 2}")
        
        print(f"\nResults breakdown:")
        print(f"  Already good outcomes: {(df_results['evaluation'] == 'ALREADY_GOOD').sum()}")
        print(f"  Good rewrites: {(df_results['evaluation'] == 'GOOD').sum()}")
        print(f"  Bad rewrites: {(df_results['evaluation'] == 'BAD').sum()}")
        print(f"  Unknown/Errors: {df_results['evaluation'].isin(['UNKNOWN', 'ERROR', 'NO_COMPARISON']).sum()}")
        
        # Calculate success rate
        total_rewrites = (df_results['evaluation'].isin(['GOOD', 'BAD'])).sum()
        if total_rewrites > 0:
            success_rate = (df_results['evaluation'] == 'GOOD').sum() / total_rewrites * 100
            print(f"\n✅ Rewrite Success Rate: {success_rate:.1f}%")
        
        # Save results
        if output_path:
            df_results.to_csv(output_path, index=False)
            print(f"\n📁 Results saved to: {output_path}")
            
            # Clean up temp file
            temp_path = output_path.replace('.csv', '_temp.csv')
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return df_results


# Main execution  
if __name__ == "__main__":
    CSV_PATH = "UnitsOutcomes.csv"
    OUTPUT_PATH = f"ai_rewrite_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Create tester
    tester = AIRewriteTester(
        csv_path=CSV_PATH,
        api_key=None  # Uses environment variable
    )
    
    # Adjust rate limiting if needed
    tester.delay_between_requests = 3
    
    # Run test - now much more efficient!
    results_df = tester.run_test(
        output_path=OUTPUT_PATH,
        sample_size=0.01,  # Start with 1% for testing
        save_incremental=True
    )
    
    # Analysis
    print("\n📊 Results by Level:")
    level_summary = results_df.groupby('level')['evaluation'].value_counts().unstack(fill_value=0)
    print(level_summary)
    
    print("\n📋 Sample Results:")
    print(results_df[['unitcode', 'title', 'outcome_number', 'evaluation']].head(10))