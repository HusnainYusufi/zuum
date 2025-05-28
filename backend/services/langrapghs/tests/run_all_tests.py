import os
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Import test modules using relative imports
from services.langrapghs.tests.test_origin import test_origin_langgraph
from services.langrapghs.tests.test_transit_offtime import test_transit_langgraph
from services.langrapghs.tests.test_destination import test_destination_langgraph
os.environ['LANGSMITH_API_KEY'] = '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'
os.environ['LANGSMITH_TRACING'] = 'true'
os.environ['LANGSMITH_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGSMITH_PROJECT'] = 'voice_freight_broker'
os.environ['OPENAI_API_KEY'] = 'ssk-proj-QzDMBdW8JkcYlRgG0tqwrGZTa0RrKCF1OzTx6nz2HQHCcX-2QIihpzVex0dqOSP9DJy_VBr-EVT3BlbkFJvtRpnLi2eKMpyaRQnxB9kMnqfiS4_mIbuUyQ1wGS0mNShsEesLNa9CYgy5ZIXRZRiGWusIZsoA'


def run_all_tests():
    """
    Run all LangGraph tests and return results as JSON instead of printing
    """
    start_time = datetime.now()
    
    # Dictionary to store test results
    test_results = {}
    test_details = []
    
    # Run Origin LangGraph Test
    try:
        origin_metrics = test_origin_langgraph()
        test_results['Origin'] = "Passed"
        test_details.append({
            "test_name": "Origin LangGraph Test",
            "status": "Passed",
            "error": None,
            "metrics": origin_metrics
        })
    except Exception as e:
        error_msg = str(e)
        test_results['Origin'] = f"Failed: {error_msg}"
        test_details.append({
            "test_name": "Origin LangGraph Test", 
            "status": "Failed",
            "error": error_msg,
            "metrics": None
        })
    
    # Run Transit LangGraph Test
    try:
        transit_metrics = test_transit_langgraph()
        test_results['Transit'] = "Passed"
        test_details.append({
            "test_name": "Transit LangGraph Test",
            "status": "Passed", 
            "error": None,
            "metrics": transit_metrics
        })
    except Exception as e:
        error_msg = str(e)
        test_results['Transit'] = f"Failed: {error_msg}"
        test_details.append({
            "test_name": "Transit LangGraph Test",
            "status": "Failed",
            "error": error_msg,
            "metrics": None
        })
    
    # Run Destination LangGraph Test
    try:
        destination_metrics = test_destination_langgraph()
        test_results['Destination'] = "Passed"
        test_details.append({
            "test_name": "Destination LangGraph Test",
            "status": "Passed",
            "error": None,
            "metrics": destination_metrics
        })
    except Exception as e:
        error_msg = str(e)
        test_results['Destination'] = f"Failed: {error_msg}"
        test_details.append({
            "test_name": "Destination LangGraph Test", 
            "status": "Failed",
            "error": error_msg,
            "metrics": None
        })
    
    end_time = datetime.now()
    
    # Calculate overall status
    passed_tests = sum(1 for result in test_results.values() if result == "Passed")
    total_tests = len(test_results)
    
    # Calculate overall metrics from individual test metrics
    overall_total_responses = 0
    overall_correct_responses = 0
    
    for detail in test_details:
        if detail["metrics"]:
            overall_total_responses += detail["metrics"]["total_responses"]
            overall_correct_responses += detail["metrics"]["correct_responses"]
    
    overall_accuracy = f"{(overall_correct_responses/overall_total_responses)*100:.1f}%" if overall_total_responses > 0 else "0%"
    
    # Return structured JSON results
    return {
        "summary": {
            "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "end_time": end_time.strftime('%Y-%m-%d %H:%M:%S'),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            "overall_metrics": {
                "total_responses": overall_total_responses,
                "correct_responses": overall_correct_responses,
                "accuracy": overall_accuracy
            }
        },
        "test_results": test_results,
        "test_details": test_details
    }


def run_all_tests_cli():
    """
    CLI version that prints results (for backward compatibility)
    """
    results = run_all_tests()
    
    print("\n=== Starting All LangGraph Tests ===")
    print(f"Test started at: {results['summary']['start_time']}")
    print("\n" + "="*50)
    
    for detail in results['test_details']:
        print(f"\nRunning {detail['test_name']}...")
        if detail['status'] == "Failed":
            print(f"Error: {detail['error']}")
        elif detail['metrics']:
            print(f"Total Responses: {detail['metrics']['total_responses']}")
            print(f"Correct Responses: {detail['metrics']['correct_responses']}")
            print(f"Accuracy: {detail['metrics']['accuracy']}")
        print("\n" + "="*50)
    
    # Print Summary
    print("\n=== Test Summary ===")
    print(f"Test completed at: {results['summary']['end_time']}")
    print("\nResults:")
    for test_name, result in results['test_results'].items():
        print(f"{test_name}: {result}")
    
    summary = results['summary']
    print(f"\nOverall: {summary['passed_tests']}/{summary['total_tests']} tests passed")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Duration: {summary['duration_seconds']:.2f} seconds")
    
    # Print overall metrics
    overall_metrics = summary['overall_metrics']
    print(f"\nOverall Test Metrics:")
    print(f"Total Responses: {overall_metrics['total_responses']}")
    print(f"Correct Responses: {overall_metrics['correct_responses']}")
    print(f"Overall Accuracy: {overall_metrics['accuracy']}")
    
    print("\n=== All Tests Complete ===")


if __name__ == "__main__":
    run_all_tests_cli() 