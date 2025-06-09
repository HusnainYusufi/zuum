import os
import sys
from pathlib import Path

# Add the backend directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

from services.langrapghs.tests.test_origin import test_origin_langgraph
from services.langrapghs.tests.test_transit_offtime import test_transit_langgraph
from services.langrapghs.tests.test_destination import test_destination_langgraph

def run_all_tests():
    print("\n=== Starting All Tests ===")
    
    # Collect all test results
    test_results = {}
    
    # Run origin tests
    print("\n=== Running Origin Tests ===")
    origin_results = test_origin_langgraph()
    test_results['origin'] = origin_results
    
    # Run transit tests
    print("\n=== Running Transit Tests ===")
    transit_results = test_transit_langgraph()
    test_results['transit'] = transit_results
    
    # Run destination tests
    print("\n=== Running Destination Tests ===")
    destination_results = test_destination_langgraph()
    test_results['destination'] = destination_results
    
    # Calculate total metrics across all tests
    total_metrics = {
        'total_responses': 0,
        'scores': {
            'meaning': {'passed': 0, 'total': 0, 'percentage': 0},
            'cosine': {'passed': 0, 'total': 0, 'percentage': 0},
            'rouge': {'passed': 0, 'total': 0, 'percentage': 0},
            'combined': {'passed': 0, 'total': 0, 'percentage': 0}
        }
    }
    
    # Aggregate scores from all tests
    for test_name, result in test_results.items():
        total_metrics['total_responses'] += result['total_responses']
        for score_type in ['meaning', 'cosine', 'rouge', 'combined']:
            total_metrics['scores'][score_type]['passed'] += result['scores'][score_type]['passed']
            total_metrics['scores'][score_type]['total'] += result['scores'][score_type]['total']
    
    # Calculate percentages for total metrics
    for score_type in ['meaning', 'cosine', 'rouge', 'combined']:
        if total_metrics['scores'][score_type]['total'] > 0:
            total_metrics['scores'][score_type]['percentage'] = (
                total_metrics['scores'][score_type]['passed'] / 
                total_metrics['scores'][score_type]['total'] * 100
            )
    
    print("\n=== All Tests Complete ===")
    
    # Return comprehensive results
    return {
        'individual_tests': test_results,
        'total_metrics': total_metrics,
        'summary': {
            'tests_run': len(test_results),
            'total_responses_evaluated': total_metrics['total_responses'],
            'overall_meaning_match_percentage': total_metrics['scores']['meaning']['percentage'],
            'overall_cosine_similarity_percentage': total_metrics['scores']['cosine']['percentage'],
            'overall_rouge_percentage': total_metrics['scores']['rouge']['percentage'],
            'overall_combined_score_percentage': total_metrics['scores']['combined']['percentage']
        }
    }

if __name__ == "__main__":
    results = run_all_tests()
    import json
    print("\n=== Final Results JSON ===")
    print(json.dumps(results['summary'], indent=2)) 