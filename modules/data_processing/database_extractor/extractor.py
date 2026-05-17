"""
Job 5: role description extractor template.

Owner: Ben
Input: RAGMatcherOutput
Output: list[RoleDescription]

This module turns role ids from the matcher into user-facing descriptions,
required skills, and practical next steps.
"""
from modules.shared.types import DataSource, RAGMatcherOutput, RoleDescription
