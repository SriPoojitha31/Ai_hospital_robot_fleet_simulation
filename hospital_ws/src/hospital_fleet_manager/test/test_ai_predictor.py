import pytest
import numpy as np
import os
import tempfile
from unittest.mock import patch

from hospital_fleet_manager.ai_predictor import EnhancedAIPredictor


@pytest.fixture
def predictor():
    return EnhancedAIPredictor()


def test_predict_positive(predictor):
    pred = predictor.predict(1.0, 0.0)
    assert pred > 0


def test_predict_reasonable(predictor):
    pred = predictor.predict(5.0, 2.0)
    assert 15 < pred < 25


def test_negative_input(predictor):
    with pytest.raises(ValueError):
        predictor.predict(-1, 0)
