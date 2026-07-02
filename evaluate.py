import sys
import json
import re
from agent import process
from catalog import search

# Benchmark test cases to evaluate the system
BENCHMARK_CASES = [
    {
        "query": "I am looking for a junior java developer",
        "expected_role": "java",
        "expected_seniority": "junior",
        "must_contain_assessment": "Java Coding Test"
    },
    {
        "query": "Hiring a senior python developer to join our team",
        "expected_role": "python",
        "expected_seniority": "senior",
        "must_contain_assessment": "Python Coding Test"
    },
    {
        "query": "We need a mid-level SQL database analyst",
        "expected_role": "sql",
        "expected_seniority": "mid",
        "must_contain_assessment": "SQL Database Test"
    },
    {
        "query": "Looking for a junior machine learning engineer",
        "expected_role": "machine learning",
        "expected_seniority": "junior",
        "must_contain_assessment": "Verify Interactive - Numerical Reasoning"
    },
    {
        "query": "We need a frontend developer who knows react",
        "expected_role": "frontend",
        "expected_seniority": None,
        "must_contain_assessment": "React Framework Coding Test"
    }
]

def run_evaluation():
    print("=" * 60)
    print("      SHL RECOMMENDATION SYSTEM BENCHMARK & EVALUATION")
    print("=" * 60)
    
    # Load database catalog for groundedness checks
    try:
        with open("catalog.json", "r", encoding="utf-8") as f:
            catalog_db = json.load(f)
        valid_assessment_names = {item["name"] for item in catalog_db}
    except Exception as e:
        print(f"Error loading catalog.json: {e}")
        sys.exit(1)
        
    total_cases = len(BENCHMARK_CASES)
    role_matches = 0
    seniority_matches = 0
    groundedness_passes = 0
    relevance_passes = 0
    total_recommendations_count = 0
    hallucinated_count = 0
    
    for i, case in enumerate(BENCHMARK_CASES, start=1):
        print(f"\nEvaluating Case #{i}: '{case['query']}'")
        
        # Step 1: Execute Recommendation API call
        # For simplicity, we pass the direct message. 
        # Since these queries contain both role and seniority, the bot will directly recommend!
        response = process([{"role": "user", "content": case["query"]}])
        
        reply = response.get("reply", "")
        recs = response.get("recommendations", [])
        
        # We parse the assistant response to extract what role/seniority it processed
        detected_role = None
        detected_seniority = None
        
        # Pattern checks
        if "java" in reply.lower(): detected_role = "java"
        elif "python" in reply.lower(): detected_role = "python"
        elif "sql" in reply.lower(): detected_role = "sql"
        elif "machine learning" in reply.lower(): detected_role = "machine learning"
        elif "frontend" in reply.lower(): detected_role = "frontend"
        
        # Check if this was a clarifying question
        is_clarifying = len(recs) == 0 and "seniority" in reply.lower()

        if is_clarifying:
            detected_seniority = None
        else:
            if "junior" in reply.lower(): detected_seniority = "junior"
            elif "mid" in reply.lower() or "middle" in reply.lower(): detected_seniority = "mid"
            elif "senior" in reply.lower(): detected_seniority = "senior"
        
        # Score role extraction
        role_ok = detected_role == case["expected_role"]
        if role_ok:
            role_matches += 1
            
        # Score seniority extraction
        seniority_ok = detected_seniority == case["expected_seniority"]
        if seniority_ok:
            seniority_matches += 1
            
        # Score Groundedness (All recommendations must exist in database)
        case_grounded = True
        case_hallucinated = 0
        for rec in recs:
            total_recommendations_count += 1
            rec_name = rec.get("name") if isinstance(rec, dict) else rec
            # Check if this recommendation exists in the catalog database
            if rec_name not in valid_assessment_names:
                case_grounded = False
                case_hallucinated += 1
                hallucinated_count += 1
                
        if (case_grounded and len(recs) > 0) or is_clarifying:
            groundedness_passes += 1
            
        # Score Retrieval Relevance (Must contain the primary domain assessment, or be a correct clarifying question)
        if is_clarifying:
            relevance_ok = case["expected_seniority"] is None
        else:
            relevance_ok = any(
                (rec.get("name") if isinstance(rec, dict) else rec) == case["must_contain_assessment"]
                for rec in recs
            )
        if relevance_ok:
            relevance_passes += 1
            
        print(f" -> Detected Role:      '{detected_role}' (Expected: '{case['expected_role']}') -> {'PASS' if role_ok else 'FAIL'}")
        print(f" -> Detected Seniority: '{detected_seniority}' (Expected: '{case['expected_seniority']}') -> {'PASS' if seniority_ok else 'FAIL'}")
        print(f" -> Recs Returned:      {len(recs)} assessments")
        print(f" -> Groundedness Check: {'PASS' if case_grounded else 'FAIL (Hallucinated: ' + str(case_hallucinated) + ')'}")
        print(f" -> Primary Relevance:  {'PASS' if relevance_ok else 'FAIL'}")
        
    # Calculate overall metrics
    role_acc = (role_matches / total_cases) * 100
    seniority_acc = (seniority_matches / total_cases) * 100
    groundedness_score = (groundedness_passes / total_cases) * 100
    relevance_score = (relevance_passes / total_cases) * 100
    hallucination_rate = (hallucinated_count / total_recommendations_count * 100) if total_recommendations_count > 0 else 0
    
    print("\n" + "=" * 60)
    print("                     EVALUATION REPORT")
    print("=" * 60)
    print(f"Total Benchmark Cases Run:     {total_cases}")
    print(f"Role Extraction Accuracy:      {role_acc:.1f}%")
    print(f"Seniority Extraction Accuracy: {seniority_acc:.1f}%")
    print(f"Retrieval Relevance (Recall):  {relevance_score:.1f}%")
    print(f"Groundedness Score:            {groundedness_score:.1f}%")
    print(f"Hallucination Rate:            {hallucination_rate:.1f}%")
    print("=" * 60)
    
if __name__ == "__main__":
    run_evaluation()
