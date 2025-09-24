from .ai_rewrite_tester import AIRewriteTester

# Create tester instance
tester = AIRewriteTester(
    csv_path="app/UnitsOutcomes.csv",
    api_key=None  # Uses environment variable
)

# Run test with 1% sample first (for testing)
results = tester.run_test(
    output_path="test_results.csv",
    sample_size=0.01  # Start small!
)

# python -m app.small_test