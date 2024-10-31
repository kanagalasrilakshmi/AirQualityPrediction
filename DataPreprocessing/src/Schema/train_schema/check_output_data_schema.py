import pandas as pd
import logging
import os
from ml_metadata.metadata_store import metadata_store
from ml_metadata.proto import metadata_store_pb2

# Set up logging configuration
def setup_logging():
    log_file_path = 'check_output_data_schema_train.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Initialize MLMD metadata store
def setup_mlmd_store():
    connection_config = metadata_store_pb2.ConnectionConfig()
    connection_config.sqlite.filename_uri = os.path.join(os.getcwd(), 'mlmd_metadata.db')
    connection_config.sqlite.connection_mode = metadata_store_pb2.SqliteMetadataSourceConfig.READWRITE_OPENCREATE
    return metadata_store.MetadataStore(connection_config)

mlmd_store = setup_mlmd_store()

# Define schema
def get_schema():
    return {
        "pm25": {"type": "float", "required": True, "sign": "positive"},
        "pm25_boxcox": {"type": "float", "required": False, "sign": "positive"},
        "pm25_log": {"type": "float", "required": False, "sign": "positive"},
        "lag_1": {"type": "float", "required": True, "sign": "positive"},
        "lag_2": {"type": "float", "required": True, "sign": "positive"},
        "lag_3": {"type": "float", "required": True, "sign": "positive"},
        "lag_4": {"type": "float", "required": True, "sign": "positive"},
        "lag_5": {"type": "float", "required": True, "sign": "positive"},
        "rolling_mean_3": {"type": "float", "required": True, "sign": "positive"},
        "rolling_mean_6": {"type": "float", "required": True, "sign": "positive"},
        "rolling_mean_24": {"type": "float", "required": True, "sign": "positive"},
        "rolling_std_3": {"type": "float", "required": True, "sign": "positive"},
        "rolling_std_6": {"type": "float", "required": True, "sign": "positive"},
        "rolling_std_24": {"type": "float", "required": True, "sign": "positive"},
        "ema_3": {"type": "float", "required": True, "sign": "positive"},
        "ema_6": {"type": "float", "required": True, "sign": "positive"},
        "ema_24": {"type": "float", "required": True, "sign": "positive"},
        "diff_1": {"type": "float", "required": True, "sign": "unrestricted"},
        "diff_2": {"type": "float", "required": True, "sign": "unrestricted"},
        "hour": {"type": "int", "min": 0, "max": 23, "required": True},
        "day_of_week": {"type": "int", "min": 0, "max": 6, "required": True},
        "day_of_year": {"type": "int", "min": 1, "max": 365, "required": True},
        "month": {"type": "int", "min": 1, "max": 12, "required": True},
        "sin_hour": {"type": "float", "min": -1.0, "max": 1.0, "required": True},
        "cos_hour": {"type": "float", "min": -1.0, "max": 1.0, "required": True},
        "sin_day_of_week": {"type": "float", "min": -1.0, "max": 1.0, "required": True},
        "cos_day_of_week": {"type": "float", "min": -1.0, "max": 1.0, "required": True},
    }

# Log schema to MLMD
def log_schema_to_mlmd(store, schema):
    schema_artifact_type = metadata_store_pb2.ArtifactType(name="DataSchema")
    schema_artifact_type_id = store.put_artifact_type(schema_artifact_type)
    schema_artifact = metadata_store_pb2.Artifact(type_id=schema_artifact_type_id)
    schema_artifact.uri = "schema.json"  # Could save the schema to a file and reference here
    store.put_artifacts([schema_artifact])
    logger.info("Schema logged to MLMD.")

# Validation function for each column
def validate_column(column_name, column_data, column_schema):
    if column_schema.get("required", False) and column_data.isnull().any():
        logger.warning(f"Missing values found in required column '{column_name}'")
    
    if column_schema.get("sign") == "positive" and (column_data < 0).any():
        logger.warning(f"Negative values found in column '{column_name}' expected to be positive")
    
    if "min" in column_schema and column_data.min() < column_schema["min"]:
        logger.warning(f"Column '{column_name}' has values below expected minimum {column_schema['min']}")
    if "max" in column_schema and column_data.max() > column_schema["max"]:
        logger.warning(f"Column '{column_name}' has values above expected maximum {column_schema['max']}")
    
    logger.info(f"{column_name}: min = {column_data.min()}, max = {column_data.max()}")

# Validate the dataset against the schema
def validate_data(data, schema):
    has_pm25_boxcox = "pm25_boxcox" in data.columns
    has_pm25_log = "pm25_log" in data.columns

    if has_pm25_boxcox and has_pm25_log:
        logger.error("Both 'pm25_boxcox' and 'pm25_log' columns are present. Only one should be present.")
        return False
    elif not has_pm25_boxcox and not has_pm25_log:
        logger.error("Neither 'pm25_boxcox' nor 'pm25_log' column is present. One of them must be present.")
        return False

    all_valid = True
    for column_name, column_schema in schema.items():
        if column_name not in data.columns:
            if column_schema.get("required", False):
                logger.error(f"Missing required column '{column_name}' specified in the schema.")
                all_valid = False
            elif column_name not in ["pm25_boxcox", "pm25_log"]:
                logger.warning(f"Optional column '{column_name}' is missing from the dataset.")
        else:
            column_data = data[column_name]
            validate_column(column_name, column_data, column_schema)

    return all_valid

# Main function to load data and run validation
def main():
    file_path = os.path.join(os.getcwd(), 'DataPreprocessing/src/data_store_pkl_files/train_data/feature_eng_train_data.pkl')
    data = pd.read_pickle(file_path)
    schema = get_schema()
    
    # Log schema to MLMD
    log_schema_to_mlmd(mlmd_store, schema)
    
    # Run data validation
    if validate_data(data, schema):
        logger.info("Data validation passed.")
    else:
        logger.info("Data validation failed.")

# Run the main function
if __name__ == "__main__":
    main()
