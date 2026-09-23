"""
Unit tests for Similarity Calculator.
"""
import pytest
from myslides.template_matching.similarity_calculator import SimilarityCalculator, SimilarityScore
from myslides.generation.generation_models import SlideType


class TestSimilarityScore:
    """Test cases for SimilarityScore dataclass."""

    def test_similarity_score_creation(self):
        """Test creating a similarity score."""
        score = SimilarityScore(
            semantic_score=0.8,
            visual_score=0.6,
            structural_score=0.9,
            combined_score=0.75
        )
        assert score.semantic_score == 0.8
        assert score.visual_score == 0.6
        assert score.structural_score == 0.9
        assert score.combined_score == 0.75

    def test_to_dict(self):
        """Test converting similarity score to dictionary."""
        score = SimilarityScore(
            semantic_score=0.5,
            visual_score=0.5,
            structural_score=0.5,
            combined_score=0.5
        )
        result = score.to_dict()
        assert result == {
            "semantic_score": 0.5,
            "visual_score": 0.5,
            "structural_score": 0.5,
            "combined_score": 0.5
        }


class TestSimilarityCalculator:
    """Test cases for SimilarityCalculator."""

    def test_initialization(self):
        """Test calculator initialization with default weights."""
        calc = SimilarityCalculator()
        assert calc.semantic_weight == 0.5
        assert calc.visual_weight == 0.3
        assert calc.structural_weight == 0.2

    def test_initialization_custom_weights(self):
        """Test calculator initialization with custom weights."""
        calc = SimilarityCalculator(semantic_weight=0.7, visual_weight=0.2, structural_weight=0.1)
        assert calc.semantic_weight == 0.7
        assert calc.visual_weight == 0.2
        assert calc.structural_weight == 0.1

    def test_calculate_similarity_basic(self):
        """Test basic similarity calculation."""
        calc = SimilarityCalculator()
        score = calc.calculate_similarity(
            query_embedding=[0.1, 0.2, 0.3],
            template_embedding=[0.1, 0.2, 0.3],
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.PROCESS_FLOW
        )
        assert isinstance(score, SimilarityScore)
        assert 0.0 <= score.combined_score <= 1.0

    def test_calculate_similarity_no_embeddings(self):
        """Test similarity calculation with no embeddings."""
        calc = SimilarityCalculator()
        score = calc.calculate_similarity(
            query_embedding=None,
            template_embedding=None
        )
        assert score.semantic_score == 0.0
        assert score.visual_score == 0.0  # No metadata
        assert score.structural_score == 0.0
        assert score.combined_score == 0.0

    def test_semantic_similarity_identical(self):
        """Test semantic similarity with identical embeddings."""
        calc = SimilarityCalculator()
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        score = calc._calculate_semantic_similarity(embedding, embedding)
        assert score == 1.0

    def test_semantic_similarity_different(self):
        """Test semantic similarity with different embeddings."""
        calc = SimilarityCalculator()
        score = calc._calculate_semantic_similarity([0.1, 0.2, 0.3], [0.9, 0.8, 0.7])
        assert score < 1.0
        assert score >= 0.0

    def test_semantic_similarity_empty(self):
        """Test semantic similarity with empty embeddings."""
        calc = SimilarityCalculator()
        score = calc._calculate_semantic_similarity([], [])
        assert score == 0.0

    def test_structural_similarity_same_type(self):
        """Test structural similarity with same slide type."""
        calc = SimilarityCalculator()
        score = calc._calculate_structural_similarity(
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.PROCESS_FLOW,
            query_element_count=None,
            template_element_count=None
        )
        assert score >= 0.7  # High score for same type

    def test_structural_similarity_compatible_type(self):
        """Test structural similarity with compatible slide types."""
        calc = SimilarityCalculator()
        score = calc._calculate_structural_similarity(
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.TIMELINE,
            query_element_count=None,
            template_element_count=None
        )
        assert score >= 0.3  # Medium score for compatible types

    def test_structural_similarity_incompatible_type(self):
        """Test structural similarity with incompatible slide types."""
        calc = SimilarityCalculator()
        score = calc._calculate_structural_similarity(
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.DATA_CHART,
            query_element_count=None,
            template_element_count=None
        )
        assert score < 0.3  # Low score for incompatible types

    def test_structural_similarity_element_count_match(self):
        """Test structural similarity with matching element count."""
        calc = SimilarityCalculator()
        score = calc._calculate_structural_similarity(
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.PROCESS_FLOW,
            query_element_count=5,
            template_element_count=5
        )
        assert score >= 0.3  # Bonus for element count match

    def test_structural_similarity_element_count_close(self):
        """Test structural similarity with close element count."""
        calc = SimilarityCalculator()
        score = calc._calculate_structural_similarity(
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.PROCESS_FLOW,
            query_element_count=5,
            template_element_count=6
        )
        assert score >= 0.15  # Partial bonus for close match

    def test_structural_similarity_element_count_far(self):
        """Test structural similarity with far element count."""
        calc = SimilarityCalculator()
        score = calc._calculate_structural_similarity(
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.PROCESS_FLOW,
            query_element_count=5,
            template_element_count=20
        )
        # With same type (0.7) and penalty for far count, score should be < 0.85
        assert score < 0.85

    def test_combined_score_calculation(self):
        """Test combined score calculation with weights."""
        calc = SimilarityCalculator(semantic_weight=0.6, visual_weight=0.2, structural_weight=0.2)
        score = calc.calculate_similarity(
            query_embedding=[0.1, 0.2, 0.3],
            template_embedding=[0.1, 0.2, 0.3],
            query_slide_type=SlideType.PROCESS_FLOW,
            template_slide_type=SlideType.PROCESS_FLOW,
            template_metadata={"element_count": 5}  # Provide metadata for visual score
        )
        # Combined = 0.6 * 1.0 + 0.2 * 0.5 + 0.2 * 0.7 = 0.6 + 0.1 + 0.14 = 0.84
        assert abs(score.combined_score - 0.84) < 0.01

    def test_is_compatible_slide_type(self):
        """Test slide type compatibility checking."""
        calc = SimilarityCalculator()
        assert calc._is_compatible_slide_type(SlideType.PROCESS_FLOW, SlideType.TIMELINE)
        assert calc._is_compatible_slide_type(SlideType.TEXT_HEAVY, SlideType.TITLE_SLIDE)
        assert not calc._is_compatible_slide_type(SlideType.PROCESS_FLOW, SlideType.DATA_CHART)
