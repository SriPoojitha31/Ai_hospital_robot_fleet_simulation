import numpy as np
import os

try:
    from sklearn.linear_model import LinearRegression
except Exception:
    LinearRegression = None

try:
    import joblib
except Exception:
    joblib = None

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
        if os.path.exists(self.model_path) and joblib is not None:
            try:
                self.model = joblib.load(self.model_path)
            except Exception:
                # Handle model incompatibilities (e.g., saved sklearn model without sklearn runtime).
                self.train_model()
        else:
            self.train_model()

    def train_model(self):
        if LinearRegression is None:
            # Runtime-safe fallback when sklearn isn't available in ROS system Python.
            self.model = _FallbackLinearModel(intercept=5.0, distance_coeff=2.0, congestion_coeff=4.0)
            return

        print('Training new AI model...')
        np.random.seed(42)
        n_samples = 1000
        distance = np.random.uniform(1, 10, n_samples)
        congestion = np.random.uniform(0, 5, n_samples)
        noise = np.random.normal(0, 1.0, n_samples)
        X = np.column_stack((distance, congestion))
        y = 5.0 + 2.0 * distance + 4.0 * congestion + noise
        self.model = LinearRegression().fit(X, y)
        if joblib is not None:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            print(f'Model saved to {self.model_path}')

    def predict(self, distance, congestion):
        if distance < 0 or congestion < 0:
            raise ValueError('Distance and congestion must be non-negative')
        return float(self.model.predict([[distance, congestion]])[0])


class _FallbackLinearModel:
    """Minimal drop-in replacement for sklearn model when sklearn isn't installed."""

    def __init__(self, intercept=5.0, distance_coeff=2.0, congestion_coeff=4.0):
        self.intercept = float(intercept)
        self.distance_coeff = float(distance_coeff)
        self.congestion_coeff = float(congestion_coeff)

    def predict(self, X):
        preds = []
        for row in X:
            distance, congestion = row
            preds.append(self.intercept + self.distance_coeff * distance + self.congestion_coeff * congestion)
        return np.array(preds, dtype=float)
