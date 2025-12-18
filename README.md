# Soil System Dashboard

## Overview

The Soil System Dashboard is an integrated web application designed to assist farmers and agricultural professionals in making informed decisions regarding crop selection, fertilizer recommendations, and irrigation management. This project leverages machine learning models to provide intelligent recommendations based on soil properties, environmental conditions, and crop requirements.

### Key Features

- **Crop Recommendation System**: Utilizes a high-accuracy ensemble approach to recommend optimal crops based on soil and environmental factors.
- **Fertilizer Recommendation System**: Implements a stacking ensemble classifier to suggest appropriate fertilizers tailored to specific soil properties and crops.
- **Irrigation Management**: An intelligent water recommendation system predicts the optimal volume of water required for irrigation events.
- **Real-Time Monitoring**: Displays real-time sensor data for temperature, humidity, pH, and nutrient levels, helping users monitor soil health.
- **User-Friendly Interface**: A responsive web interface built with Bootstrap for easy navigation and interaction.

## Project Structure

```
project/
│
├── dataset/                          # Contains datasets used for training models
│   ├── Crop_Groundwater_Irrigation_Schedule.csv
│   ├── Crop_recommendation.csv
│   └── Dakshina Kannada Crop and fertilizer dataset.csv
│
├── templates/                        # HTML templates for the web application
│   └── base.html
│
├── water.ipynb                      # Jupyter Notebook for the Water Recommendation System
├── crop_recommendation.ipynb        # Jupyter Notebook for the Crop Recommendation System
└── fertilizer.ipynb                 # Jupyter Notebook for the Fertilizer Recommendation System
```

## Installation

### Prerequisites

- Python 3.x
- pip (Python package installer)

### Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install required packages**:
   Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

   Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Jupyter Notebooks**:
   Each notebook contains the code for training the respective models. You can run them in Jupyter Notebook or Jupyter Lab.

   ```bash
   jupyter notebook
   ```

4. **Start the Flask web application**:
   Ensure you have Flask installed. If not, you can install it using:
   ```bash
   pip install Flask
   ```

   Run the Flask application:
   ```bash
   python app.py
   ```

   The application will be accessible at `http://127.0.0.1:5000`.

## Usage

### Crop Recommendation

1. Navigate to the "Crop Recommend" section in the dashboard.
2. Input the soil and environmental parameters.
3. Submit the form to receive crop recommendations based on the trained model.

### Fertilizer Recommendation

1. Go to the "Fertilizer" section.
2. Enter the soil properties and crop type.
3. Submit the form to get fertilizer recommendations.

### Water Management

1. Access the "Motor Control" section to manage irrigation.
2. View real-time sensor data and adjust settings as needed.

## Model Training

The machine learning models are trained using the provided datasets. Each Jupyter Notebook contains detailed steps for data preprocessing, model training, evaluation, and saving the trained models for deployment.

### Models Used

- **Water Recommendation**: Gradient Boosting Regressor
- **Crop Recommendation**: Weighted Soft Voting Ensemble Classifier (LightGBM, XGBoost, Random Forest)
- **Fertilizer Recommendation**: Stacking Ensemble Classifier (KNN, Decision Tree, Logistic Regression with LightGBM as the meta-model)

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Scikit-learn](https://scikit-learn.org/stable/) for machine learning algorithms.
- [LightGBM](https://lightgbm.readthedocs.io/en/latest/) and [XGBoost](https://xgboost.readthedocs.io/en/latest/) for gradient boosting frameworks.
- [Flask](https://flask.palletsprojects.com/) for web application development.
- [Bootstrap](https://getbootstrap.com/) for responsive design.

```

### Notes:
- Replace `<repository-url>` and `<repository-directory>` with the actual URL of your repository and the directory name.
- Ensure that you have a `requirements.txt` file that lists all the necessary Python packages for your project.
- You can customize the content further based on your specific project details and preferences.
