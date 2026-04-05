import numpy as np
from sklearn.linear_model import LinearRegression
import joblib
import os

try:
    from ament_index_python.packages import get_package_share_directory
except ImportError:
    get_package_share_directory = None


class EnhancedAIPredictor:
    """ML-based AI module using trained LinearRegression for task duration prediction."""

    MODEL_PATH = None

    def __init__(self):
        if EnhancedAIPredictor.MODEL_PATH is None:
            if get_package_share_directory is not None:
                try:
                    base_dir = get_package_share_directory('hospital_fleet_manager')
                except Exception:
                    base_dir = os.path.dirname(__file__)
            else:
                base_dir = os.path.dirname(__file__)
            EnhancedAIPredictor.MODEL_PATH = os.path.join(base_dir, 'models', 'ai_model.joblib')
        self.model_path = EnhancedAIPredictor.MODEL_PATH
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
        else:
            self.train_model()

    def train_model(self):
        print('Training new AI model...')
        np.random.seed(42)
        n_samples = 1000
        distance = np.random.uniform(1, 10, n_samples)
        congestion = np.random.uniform(0, 5, n_samples)
        noise = np.random.normal(0, 1.0, n_samples)
        X = np.column_stack((distance, congestion))
        y = 5.0 + 2.0 * distance + 4.0 * congestion + noise
        self.model = LinearRegression().fit(X, y)
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f'Model saved to {self.model_path}')

    def predict(self, distance, congestion):
        if distance < 0 or congestion < 0:
            raise ValueError('Distance and congestion must be non-negative')
        return float(self.model.predict([[distance, congestion]])[0])

