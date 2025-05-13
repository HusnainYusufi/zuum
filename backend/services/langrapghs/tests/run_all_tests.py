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
# from .test_transit_offtime import test_transit_langgraph
# from .test_destination import test_destination_langgraph
os.environ['LANGSMITH_API_KEY'] = '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'
os.environ['LANGSMITH_TRACING'] = 'true'
os.environ['LANGSMITH_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGSMITH_PROJECT'] = 'voice_freight_broker'
os.environ['OPENAI_API_KEY'] = 'ssk-proj-QzDMBdW8JkcYlRgG0tqwrGZTa0RrKCF1OzTx6nz2HQHCcX-2QIihpzVex0dqOSP9DJy_VBr-EVT3BlbkFJvtRpnLi2eKMpyaRQnxB9kMnqfiS4_mIbuUyQ1wGS0mNShsEesLNa9CYgy5ZIXRZRiGWusIZsoA'


def run_all_tests():
    print("\n=== Starting All LangGraph Tests ===")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*50)
    
    # Dictionary to store test results
    test_results = {}
    
    # Run Origin LangGraph Test
    print("\nRunning Origin LangGraph Test...")
    try:
        test_origin_langgraph()
        test_results['Origin'] = "Passed"
    except Exception as e:
        print(f"Error in Origin test: {str(e)}")
        test_results['Origin'] = f"Failed: {str(e)}"
    
    print("\n" + "="*50)
    
    # # Run Transit LangGraph Test
    # print("\nRunning Transit LangGraph Test...")
    # try:
    #     test_transit_langgraph()
    #     test_results['Transit'] = "Passed"
    # except Exception as e:
    #     print(f"Error in Transit test: {str(e)}")
    #     test_results['Transit'] = f"Failed: {str(e)}"
    
    # print("\n" + "="*50)
    
    # # Run Destination LangGraph Test
    # print("\nRunning Destination LangGraph Test...")
    # try:
    #     test_destination_langgraph()
    #     test_results['Destination'] = "Passed"
    # except Exception as e:
    #     print(f"Error in Destination test: {str(e)}")
    #     test_results['Destination'] = f"Failed: {str(e)}"
    
    # Print Summary
    print("\n=== Test Summary ===")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nResults:")
    for test_name, result in test_results.items():
        print(f"{test_name}: {result}")
    
    # Calculate overall status
    passed_tests = sum(1 for result in test_results.values() if result == "Passed")
    total_tests = len(test_results)
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    print("\n=== All Tests Complete ===")

if __name__ == "__main__":
    run_all_tests() 