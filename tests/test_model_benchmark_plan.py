from writing_agent.evaluation.model_benchmark import plan_model_benchmark


def test_model_benchmark_plan_builds_cartesian_product() -> None:
    combos = plan_model_benchmark(
        models="m1,m2",
        embedding_models="e1,e2",
        rag_modes="hybrid,vector",
        mode="multi",
        max_agent_rounds=2,
    )

    assert len(combos) == 8
    assert combos[0].mode == "multi"
    assert combos[0].max_agent_rounds == 2
