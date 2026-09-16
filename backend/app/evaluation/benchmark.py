from app.services.evaluation import (
    EvaluationCase,
)


EVALUATION_CASES = [
    EvaluationCase(
        id="nist_core_functions",
        question=(
            "What are the four core functions "
            "of the NIST AI Risk Management "
            "Framework?"
        ),
        expected_answer_terms=[
            "GOVERN",
            "MAP",
            "MEASURE",
            "MANAGE",
        ],
        expected_evidence_terms=[
            "GOVERN",
            "MAP",
            "MEASURE",
            "MANAGE",
        ],
        expected_filenames=[
            "NIST.AI.100-1.pdf",
        ],
        expected_pages=[
            8,
            25,
        ],
    ),

    EvaluationCase(
        id="rag_gpu_training",
        question=(
            "What GPU hardware was used to "
            "train the RAG models?"
        ),
        expected_answer_terms=[
            "8",
            "32GB",
            "V100",
        ],
        expected_evidence_terms=[
            "8",
            "32GB",
            "V100",
        ],
        expected_filenames=[
            "rag.pdf",
        ],
        expected_pages=[
            17,
        ],
    ),

    EvaluationCase(
        id="out_of_knowledge_base",
        question=(
            "Who won the 2018 FIFA World Cup?"
        ),
        should_refuse=True,
    ),
]