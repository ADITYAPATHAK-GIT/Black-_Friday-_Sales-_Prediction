# -*- coding: utf-8 -*-
"""DWR PROJECT L004 L030.py

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1nPektxQBYv_PhBggJt9rHaVui4X-nhVh

**DWR PROJECT ROLLNO: L004 L030**
"""

pip install dask[dataframe]

!pip install xgboost lightgbm

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error
import xgboost as xgb
import lightgbm as lgb

# Load the train and test datasets
train_df = pd.read_csv('/content/train.csv')
test_df = pd.read_csv('/content/test.csv')

# Save 'User_ID' and 'Product_ID' from test data for final submission
test_user_product_ids = test_df[['User_ID', 'Product_ID']]

# Combine train and test datasets for consistent preprocessing
test_df['Purchase'] = np.nan
combined_df = pd.concat([train_df, test_df], ignore_index=True)

combined_df['Product_Category_2'] = combined_df['Product_Category_2'].fillna(-2)
combined_df['Product_Category_3'] = combined_df['Product_Category_3'].fillna(-2)

# Encode categorical variables using Label Encoding
categorical_cols = ['Gender', 'Age', 'City_Category', 'Stay_In_Current_City_Years']
for col in categorical_cols:
    le = LabelEncoder()
    combined_df[col] = le.fit_transform(combined_df[col].astype(str))

# Label encoding for 'User_ID' and 'Product_ID'
le_user = LabelEncoder()
le_product = LabelEncoder()
combined_df['User_ID'] = le_user.fit_transform(combined_df['User_ID'])
combined_df['Product_ID'] = le_product.fit_transform(combined_df['Product_ID'])

# Frequency encoding for 'User_ID' and 'Product_ID'
user_freq = combined_df['User_ID'].value_counts().to_dict()
product_freq = combined_df['Product_ID'].value_counts().to_dict()
combined_df['User_ID_Freq'] = combined_df['User_ID'].map(user_freq)
combined_df['Product_ID_Freq'] = combined_df['Product_ID'].map(product_freq)

# Split combined data back into train and test sets
train = combined_df[~combined_df['Purchase'].isna()]
test = combined_df[combined_df['Purchase'].isna()].drop('Purchase', axis=1)
y = train['Purchase']
X = train.drop('Purchase', axis=1)

# Create aggregate features on training data
user_purchase_mean = train.groupby('User_ID')['Purchase'].mean()
product_purchase_mean = train.groupby('Product_ID')['Purchase'].mean()

# Map aggregate features to training data
X['User_Purchase_Mean'] = X['User_ID'].map(user_purchase_mean)
X['Product_Purchase_Mean'] = X['Product_ID'].map(product_purchase_mean)

# Map aggregate features to test data
test['User_Purchase_Mean'] = test['User_ID'].map(user_purchase_mean)
test['Product_Purchase_Mean'] = test['Product_ID'].map(product_purchase_mean)

# For missing values in test data, fill with overall mean
overall_mean_purchase = y.mean()
test['User_Purchase_Mean'] = test['User_Purchase_Mean'].fillna(overall_mean_purchase)
test['Product_Purchase_Mean'] = test['Product_Purchase_Mean'].fillna(overall_mean_purchase)

# Split training data into training and validation sets
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42
)

lgb_model = lgb.LGBMRegressor(objective='regression', random_state=42)



param_dist = {
    'n_estimators': [1000, 1500],
    'learning_rate': [0.01, 0.05],
    'num_leaves': [31, 63],
    'max_depth': [-1, 10],
    'subsample': [0.8, 1.0],
    'colsample_bytree': [0.8, 1.0],
    'reg_lambda': [0, 1],
    'reg_alpha': [0, 1]
}

random_search = RandomizedSearchCV(
    estimator=lgb_model,
    param_distributions=param_dist,
    n_iter=5,
    scoring='neg_root_mean_squared_error',
    cv=2,  # Reduce number of CV folds
    verbose=1,
    random_state=42,
    n_jobs=-1
)

random_search.fit(X_train, y_train)



best_lgb_model_sample = random_search.best_estimator_
print(best_lgb_model_sample)

# Best model
best_lgb = random_search.best_estimator_

# Evaluate the model on the validation set
y_pred = best_lgb.predict(X_val)
rmse = np.sqrt(mean_squared_error(y_val, y_pred))
print(f'Optimized LightGBM RMSE: {rmse}')

# Train the best model on the full training data
# Recreate aggregate features on full training data
user_purchase_mean_full = train.groupby('User_ID')['Purchase'].mean()
product_purchase_mean_full = train.groupby('Product_ID')['Purchase'].mean()

X['User_Purchase_Mean'] = X['User_ID'].map(user_purchase_mean_full)
X['Product_Purchase_Mean'] = X['Product_ID'].map(product_purchase_mean_full)

best_lgb.fit(X, y)

# Predict on the test dataset
test_predictions = best_lgb.predict(test)

# Prepare the submission dataframe
submission = pd.DataFrame({
    'User_ID': test_user_product_ids['User_ID'],
    'Product_ID': test_user_product_ids['Product_ID'],
    'Purchase': test_predictions
})

# Save the submission file locally
submission.to_csv('optimized_purchase_predictions.csv', index=False)

# Download the CSV file to your local machine
from google.colab import files
files.download('optimized_purchase_predictions.csv')