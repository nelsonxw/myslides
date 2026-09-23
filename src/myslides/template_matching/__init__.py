"""
Template Matching Module for MySlides.

Provides intelligent template suggestion and matching based on
semantic similarity, visual similarity, and adaptive element count.
"""
from myslides.template_matching.template_matcher import TemplateMatcher
from myslides.template_matching.similarity_calculator import SimilarityCalculator
from myslides.template_matching.ranking import TemplateRanker

__all__ = ['TemplateMatcher', 'SimilarityCalculator', 'TemplateRanker']
