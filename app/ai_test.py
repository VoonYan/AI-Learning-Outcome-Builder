from .ai_rewrite_tester import AIRewriteTester

# Test with small sample first
tester = AIRewriteTester(csv_path="app/UnitsOutcomes.csv",api_key=None)
results = tester.run_test(
    output_path="test_results.csv",
    sample_size=0.01,  # 1% of units (~70 units)
    save_incremental=True,
)

# # Full 20% test
# results = tester.run_test(
#     output_path="final_results.csv",
#     sample_size=0.2,  # 20% of units (~1,400 units)
#     save_incremental=True
# )
# python -m app.small_test