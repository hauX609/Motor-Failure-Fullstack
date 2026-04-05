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
                raise FileNotFoundError(f"Missing required files: {missing_files}")
            
            # Load assets
            self.model = load_model('motor_model_multi.keras')
            self.feature_scaler = joblib.load('scaler.pkl')
            self.rul_scaler = joblib.load('rul_scaler.pkl')
            self.feature_cols = joblib.load('feature_columns.pkl')
            
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
            return False
    
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
