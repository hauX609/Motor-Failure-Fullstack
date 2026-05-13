"""
ML Model management for Motor Monitoring System.
Handles model loading, caching, and predictions.
"""

import os
import logging
import numpy as np
import joblib
from typing import Dict, Tuple, List
from tensorflow.keras.models import load_model, Model
import shap
import threading

from config import STATUS_MAP, REQUIRED_SEQUENCE_LENGTH
from utils.errors import ServiceUnavailableError


logger = logging.getLogger(__name__)


DEFAULT_FEATURE_COLS = [
    'setting1', 'setting2', 'setting3',
    's1', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9',
    's10', 's11', 's12', 's13', 's14', 's15', 's16', 's17',
    's18', 's19', 's20', 's21'
]


class MLModelManager:
    """Manages ML model, scalers, and explainers."""
    
    def __init__(self):
        """Initialize ML model manager."""
        self.model = None
        self.feature_scaler = None
        self.rul_scaler = None
        self.feature_cols = None
        self.classification_explainer = None
        self.regression_explainer = None
        self.model_lock = threading.Lock()
        self.fallback_mode = False
        self.fallback_reason = None

    def _enable_fallback(self, reason: str) -> None:
        """Enable heuristic predictions when trained assets are unavailable."""
        self.model = None
        self.feature_scaler = None
        self.rul_scaler = None
        self.feature_cols = DEFAULT_FEATURE_COLS.copy()
        self.classification_explainer = None
        self.regression_explainer = None
        self.fallback_mode = True
        self.fallback_reason = reason
        logger.warning("Using heuristic prediction fallback: %s", reason)

    def has_trained_model(self) -> bool:
        """Return True only when the trained ML bundle is loaded."""
        return self.model is not None and not self.fallback_mode

    def is_fallback_active(self) -> bool:
        """Return True when heuristic fallback is serving predictions."""
        return self.fallback_mode

    def get_runtime_state(self) -> dict:
        """Summarize the current prediction runtime state."""
        return {
            'trained_model_loaded': self.has_trained_model(),
            'fallback_active': self.is_fallback_active(),
            'ready': self.is_ready(),
            'mode': 'fallback' if self.fallback_mode else ('trained' if self.model else 'unavailable'),
            'fallback_reason': self.fallback_reason,
            'feature_count': self.get_feature_count(),
        }
    
    def load_assets(self) -> bool:
        """Load all necessary model assets."""
        required_files = {
            'motor_model_multi.keras': 'model',
            'scaler.pkl': 'feature_scaler',
            'rul_scaler.pkl': 'rul_scaler',
            'feature_columns.pkl': 'feature_cols'
        }
        
        try:
            # Check if all required files exist
            missing_files = [f for f in required_files.keys() if not os.path.exists(f)]
            if missing_files:
                self._enable_fallback(f"Missing required files: {missing_files}")
                return True
            
            # Load assets
            # Inference does not need optimizer state; skipping compile avoids
            # Keras optimizer deserialization issues across versions.
            self.model = load_model('motor_model_multi.keras', compile=False)
            self.feature_scaler = joblib.load('scaler.pkl')
            self.rul_scaler = joblib.load('rul_scaler.pkl')
            self.feature_cols = joblib.load('feature_columns.pkl')
            self.fallback_mode = False
            self.fallback_reason = None
            
            # Validate model outputs
            if len(self.model.outputs) != 2:
                raise ValueError("Model must have exactly 2 outputs (classification and regression)")
            
            # Validate feature columns
            if not isinstance(self.feature_cols, list) or len(self.feature_cols) == 0:
                raise ValueError("feature_cols must be a non-empty list")
            
            logger.info("✅ All model assets loaded successfully.")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error loading model assets: {e}")
            self._enable_fallback(str(e))
            return True
    
    def initialize_explainers(self) -> bool:
        """Initialize SHAP explainers for both outputs."""
        if self.model is None:
            logger.error("Cannot initialize explainers: model not loaded")
            return False
        
        logger.info("Initializing SHAP explainers...")
        try:
            if not os.path.exists('shap_background.pkl'):
                logger.warning("SHAP background data not found. Explainers will not be available.")
                return False
            
            background_data = joblib.load('shap_background.pkl')
            classification_model = Model(inputs=self.model.inputs, outputs=self.model.outputs[0])
            regression_model = Model(inputs=self.model.inputs, outputs=self.model.outputs[1])
            
            self.classification_explainer = shap.GradientExplainer(classification_model, background_data)
            self.regression_explainer = shap.GradientExplainer(regression_model, background_data)
            
            logger.info("✅ SHAP explainers initialized successfully.")
            return True
        
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize SHAP explainers: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if model is ready for predictions."""
        if self.fallback_mode:
            return self.feature_cols is not None

        return self.model is not None and all([
            self.feature_scaler is not None,
            self.rul_scaler is not None,
            self.feature_cols is not None
        ])
    
    def get_feature_count(self) -> int:
        """Get number of features."""
        return len(self.feature_cols) if self.feature_cols else 0
    
    def has_explainers(self) -> bool:
        """Check if explainers are available."""
        return all([
            self.classification_explainer is not None,
            self.regression_explainer is not None
        ])


# Global ML model manager instance
ml_manager = MLModelManager()
