import os
import sys
from pathlib import Path
from flytekitplugins.domino.helpers import Input, Output, run_domino_job_task
from flytekitplugins.domino.task import DatasetSnapshot
from flytekitplugins.domino.artifact import Artifact, DATA
from flytekit import workflow
from flytekit.types.file import FlyteFile
from flytekit.types.directory import FlyteDirectory
from typing import TypeVar

# Import shared data configuration - add multiple possible paths
current_dir = Path(__file__).parent
src_paths = [
    str(current_dir / 'src'),  # flow.py in root, src as subdirectory
    '/mnt/code/src',           # Git-based project absolute path
    '/mnt/src',                # File-based project absolute path
]
for src_path in src_paths:
    if src_path not in sys.path and Path(src_path).exists():
        sys.path.insert(0, src_path)

from data_config import DataConfig

# Initialize global config
config = DataConfig()

# Get project-specific dataset name for Flow snapshots
dataset_name = os.environ.get('DOMINO_PROJECT_NAME', 'Seabed-Object-Detection')

# Dynamic ETL script path based on DOMINO_WORKING_DIR
# Git-based projects: /mnt/code, File-based projects: /mnt
etl_base_path = config.domino_working_dir + '/src/etl'

# Define Flow Artifacts for cleaned sonar data
CleanedSonarData = Artifact(name="Cleaned Sonar Data", type=DATA)

@workflow
def seabed_etl_pipeline(input_dataset_path: str,
                       gamma_transform: float = 0.5) -> CleanedSonarData.File(name="cleaned_sonar_data.zip"):
    '''
    SEABED SONAR IMAGE PROCESSING PIPELINE

    This flow processes sonar images through a four-stage ETL pipeline:

        1. NORMALIZATION: Log-gamma transform sonar images for consistent luminance
        2. DENOISING: Median + bilateral filtering with background subtraction
        3. ENHANCEMENT: CLAHE contrast boost + unsharp mask feature sharpening
        4. PACKAGING: Zip results and output as Flow Artifact

    To run this flow with custom dataset path:

    pyflyte run --remote flow.py seabed_etl_pipeline --input_dataset_path /domino/datasets/local/Seabed-Object-Detection/balanced_training_validation_set
    pyflyte run --remote flow.py seabed_etl_pipeline --input_dataset_path /path/to/custom/dataset --gamma_transform 0.0

    :param input_dataset_path: Path to input sonar imagery dataset (required)
    :param gamma_transform: Gamma correction factor (0.5 default, 0 for log transform)
    :return: Cleaned dataset zip file as "Cleaned Sonar Data" artifact (discoverable in Domino UI)
    '''

    working_dir = config.domino_working_dir

    # STAGE 1: NORMALIZATION AND GAMMA CORRECTION
    # Note: gamma is passed as input and read from /workflow/inputs/gamma by the script
    normalize = run_domino_job_task(
        flyte_task_name='normalize_sonar_images',
        command=f'python {etl_base_path}/etl_normalize.py --input_dir {input_dataset_path}',
        hardware_tier_name='Small',
        inputs=[
            Input(name='gamma', type=float, value=gamma_transform)
        ],
        output_specs=[
            Output(name='normalized_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 2: DENOISING AND BACKGROUND SUBTRACTION
    denoise = run_domino_job_task(
        flyte_task_name='denoise_sonar_images',
        command=f'python {etl_base_path}/etl_denoise.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='normalized_data', type=FlyteDirectory, value=normalize['normalized_data'])
        ],
        output_specs=[
            Output(name='denoised_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 3: FEATURE ENHANCEMENT AND CONTRAST OPTIMIZATION
    enhance = run_domino_job_task(
        flyte_task_name='enhance_sonar_features',
        command=f'python {etl_base_path}/etl_enhance.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='denoised_data', type=FlyteDirectory, value=denoise['denoised_data'])
        ],
        output_specs=[
            Output(name='enhanced_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 4: PACKAGE INTO ZIP FILE
    package = run_domino_job_task(
        flyte_task_name='package_cleaned_data',
        command=f'python {etl_base_path}/etl_package.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='enhanced_data', type=FlyteDirectory, value=enhance['enhanced_data'])
        ],
        output_specs=[
            Output(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')])
        ],
        use_project_defaults_for_omitted=True
    )

    return package['cleaned_data_zip']


# Define Flow Artifact for trained models
TrainedModelArtifact = Artifact(name="Champion Model", type=DATA)

@workflow
def etl_and_model_training(input_dataset_path: str = None,
                          gamma_transform: float = 0.5) -> TrainedModelArtifact.File(name="champion_model_registration.json"):
    '''
    ETL AND MODEL TRAINING PIPELINE

    This comprehensive workflow demonstrates a complete machine learning pipeline:

        1. ETL PROCESSING: 4-stage sonar image preprocessing (same as existing ETL)
        2. PARALLEL TRAINING: Train 3 different models simultaneously
           - Vision Transformer (ViT) Model
           - Convolutional Neural Network (CNN) Model  
           - Ensemble/Hybrid Model
        3. CHAMPION SELECTION: Evaluate all models and register the best performer

    To run this workflow:

    pyflyte run --remote flow.py etl_and_model_training
    pyflyte run --remote flow.py etl_and_model_training --input_dataset_path /path/to/dataset --gamma_transform 0.0

    :param input_dataset_path: Path to input sonar imagery dataset (optional, defaults to balanced dataset)
    :param gamma_transform: Gamma correction factor (0.5 default, 0 for log transform)
    :return: Champion model registration data as "Champion Model" artifact
    '''

    # Use balanced dataset as default if no input path specified
    if input_dataset_path is None:
        input_dataset_path = str(config.balanced_dataset_path)
    
    working_dir = config.domino_working_dir

    # ============================================================================
    # PHASE 1: ETL PROCESSING (Sequential Pipeline)
    # ============================================================================

    # STAGE 1: NORMALIZATION AND GAMMA CORRECTION
    normalize = run_domino_job_task(
        flyte_task_name='etl_normalize_sonar_images',
        command=f'python {etl_base_path}/etl_normalize.py --input_dir {input_dataset_path}',
        hardware_tier_name='Small',
        inputs=[
            Input(name='gamma', type=float, value=gamma_transform)
        ],
        output_specs=[
            Output(name='normalized_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 2: DENOISING AND BACKGROUND SUBTRACTION
    denoise = run_domino_job_task(
        flyte_task_name='etl_denoise_sonar_images',
        command=f'python {etl_base_path}/etl_denoise.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='normalized_data', type=FlyteDirectory, value=normalize['normalized_data'])
        ],
        output_specs=[
            Output(name='denoised_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 3: FEATURE ENHANCEMENT AND CONTRAST OPTIMIZATION
    enhance = run_domino_job_task(
        flyte_task_name='etl_enhance_sonar_features',
        command=f'python {etl_base_path}/etl_enhance.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='denoised_data', type=FlyteDirectory, value=denoise['denoised_data'])
        ],
        output_specs=[
            Output(name='enhanced_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 4: PACKAGE INTO ZIP FILE
    package = run_domino_job_task(
        flyte_task_name='etl_package_cleaned_data',
        command=f'python {etl_base_path}/etl_package.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='enhanced_data', type=FlyteDirectory, value=enhance['enhanced_data'])
        ],
        output_specs=[
            Output(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')])
        ],
        use_project_defaults_for_omitted=True
    )

    # ============================================================================
    # PHASE 2: PARALLEL MODEL TRAINING
    # ============================================================================

    # PARALLEL TASK 1: Vision Transformer (ViT) Training
    vit_training = run_domino_job_task(
        flyte_task_name='train_vit_model',
        command=f'python {working_dir}/src/demo_train_vit_model.py',
        hardware_tier_name='Medium',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='vit_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # PARALLEL TASK 2: Convolutional Neural Network (CNN) Training  
    cnn_training = run_domino_job_task(
        flyte_task_name='train_cnn_model',
        command=f'python {working_dir}/src/demo_train_cnn_model.py',
        hardware_tier_name='Medium',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='cnn_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # PARALLEL TASK 3: Ensemble/Hybrid Model Training
    ensemble_training = run_domino_job_task(
        flyte_task_name='train_ensemble_model',
        command=f'python {working_dir}/src/demo_train_ensemble_model.py',
        hardware_tier_name='Large',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='ensemble_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # ============================================================================
    # PHASE 3: CHAMPION MODEL SELECTION AND REGISTRATION
    # ============================================================================

    # FINAL TASK: Champion Model Registration (depends on all 3 training tasks)
    champion_registration = run_domino_job_task(
        flyte_task_name='register_champion_model',
        command=f'python {working_dir}/src/demo_register_champion_model.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='vit_model_metrics', type=FlyteFile[TypeVar('json')], value=vit_training['vit_model_metrics']),
            Input(name='cnn_model_metrics', type=FlyteFile[TypeVar('json')], value=cnn_training['cnn_model_metrics']),
            Input(name='ensemble_model_metrics', type=FlyteFile[TypeVar('json')], value=ensemble_training['ensemble_model_metrics'])
        ],
        output_specs=[
            Output(name='champion_model_registration', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    return champion_registration['champion_model_registration']


@workflow
def seabed_etl_pipeline_balanced(gamma_transform: float = 0.5) -> CleanedSonarData.File(name="cleaned_sonar_data_balanced.zip"):
    '''
    SEABED ETL PIPELINE - BALANCED DATASET

    Processes the balanced training dataset (138 images).

    DEPLOYMENT:
    pyflyte run --remote flow.py seabed_etl_pipeline_balanced
    pyflyte run --remote flow.py seabed_etl_pipeline_balanced --gamma_transform 0.0

    :param gamma_transform: Gamma correction factor (0.5 default, 0 for log transform)
    :return: Cleaned dataset zip file as "Cleaned Sonar Data" artifact (balanced dataset)
    '''
    balanced_path = str(config.balanced_dataset_path)
    working_dir = config.domino_working_dir

    # STAGE 1: NORMALIZATION
    normalize = run_domino_job_task(
        flyte_task_name='normalize_sonar_images',
        command=f'python {etl_base_path}/etl_normalize.py --input_dir {balanced_path}',
        hardware_tier_name='Small',
        inputs=[
            Input(name='gamma', type=float, value=gamma_transform)
        ],
        output_specs=[Output(name='normalized_data', type=FlyteDirectory)],
        use_project_defaults_for_omitted=True
    )

    # STAGE 2: DENOISING
    denoise = run_domino_job_task(
        flyte_task_name='denoise_sonar_images',
        command=f'python {etl_base_path}/etl_denoise.py',
        hardware_tier_name='Small',
        inputs=[Input(name='normalized_data', type=FlyteDirectory, value=normalize['normalized_data'])],
        output_specs=[Output(name='denoised_data', type=FlyteDirectory)],
        use_project_defaults_for_omitted=True
    )

    # STAGE 3: ENHANCEMENT
    enhance = run_domino_job_task(
        flyte_task_name='enhance_sonar_features',
        command=f'python {etl_base_path}/etl_enhance.py',
        hardware_tier_name='Small',
        inputs=[Input(name='denoised_data', type=FlyteDirectory, value=denoise['denoised_data'])],
        output_specs=[Output(name='enhanced_data', type=FlyteDirectory)],
        use_project_defaults_for_omitted=True
    )

    # STAGE 4: PACKAGE
    package = run_domino_job_task(
        flyte_task_name='package_cleaned_data',
        command=f'python {etl_base_path}/etl_package.py',
        hardware_tier_name='Small',
        inputs=[Input(name='enhanced_data', type=FlyteDirectory, value=enhance['enhanced_data'])],
        output_specs=[Output(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')])],
        use_project_defaults_for_omitted=True
    )

    return package['cleaned_data_zip']


# Define Flow Artifact for trained models
TrainedModelArtifact = Artifact(name="Champion Model", type=DATA)

@workflow
def etl_and_model_training(input_dataset_path: str = None,
                          gamma_transform: float = 0.5) -> TrainedModelArtifact.File(name="champion_model_registration.json"):
    '''
    ETL AND MODEL TRAINING PIPELINE

    This comprehensive workflow demonstrates a complete machine learning pipeline:

        1. ETL PROCESSING: 4-stage sonar image preprocessing (same as existing ETL)
        2. PARALLEL TRAINING: Train 3 different models simultaneously
           - Vision Transformer (ViT) Model
           - Convolutional Neural Network (CNN) Model  
           - Ensemble/Hybrid Model
        3. CHAMPION SELECTION: Evaluate all models and register the best performer

    To run this workflow:

    pyflyte run --remote flow.py etl_and_model_training
    pyflyte run --remote flow.py etl_and_model_training --input_dataset_path /path/to/dataset --gamma_transform 0.0

    :param input_dataset_path: Path to input sonar imagery dataset (optional, defaults to balanced dataset)
    :param gamma_transform: Gamma correction factor (0.5 default, 0 for log transform)
    :return: Champion model registration data as "Champion Model" artifact
    '''

    # Use balanced dataset as default if no input path specified
    if input_dataset_path is None:
        input_dataset_path = str(config.balanced_dataset_path)
    
    working_dir = config.domino_working_dir

    # ============================================================================
    # PHASE 1: ETL PROCESSING (Sequential Pipeline)
    # ============================================================================

    # STAGE 1: NORMALIZATION AND GAMMA CORRECTION
    normalize = run_domino_job_task(
        flyte_task_name='etl_normalize_sonar_images',
        command=f'python {etl_base_path}/etl_normalize.py --input_dir {input_dataset_path}',
        hardware_tier_name='Small',
        inputs=[
            Input(name='gamma', type=float, value=gamma_transform)
        ],
        output_specs=[
            Output(name='normalized_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 2: DENOISING AND BACKGROUND SUBTRACTION
    denoise = run_domino_job_task(
        flyte_task_name='etl_denoise_sonar_images',
        command=f'python {etl_base_path}/etl_denoise.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='normalized_data', type=FlyteDirectory, value=normalize['normalized_data'])
        ],
        output_specs=[
            Output(name='denoised_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 3: FEATURE ENHANCEMENT AND CONTRAST OPTIMIZATION
    enhance = run_domino_job_task(
        flyte_task_name='etl_enhance_sonar_features',
        command=f'python {etl_base_path}/etl_enhance.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='denoised_data', type=FlyteDirectory, value=denoise['denoised_data'])
        ],
        output_specs=[
            Output(name='enhanced_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 4: PACKAGE INTO ZIP FILE
    package = run_domino_job_task(
        flyte_task_name='etl_package_cleaned_data',
        command=f'python {etl_base_path}/etl_package.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='enhanced_data', type=FlyteDirectory, value=enhance['enhanced_data'])
        ],
        output_specs=[
            Output(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')])
        ],
        use_project_defaults_for_omitted=True
    )

    # ============================================================================
    # PHASE 2: PARALLEL MODEL TRAINING
    # ============================================================================

    # PARALLEL TASK 1: Vision Transformer (ViT) Training
    vit_training = run_domino_job_task(
        flyte_task_name='train_vit_model',
        command=f'python {working_dir}/src/demo_train_vit_model.py',
        hardware_tier_name='Medium',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='vit_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # PARALLEL TASK 2: Convolutional Neural Network (CNN) Training  
    cnn_training = run_domino_job_task(
        flyte_task_name='train_cnn_model',
        command=f'python {working_dir}/src/demo_train_cnn_model.py',
        hardware_tier_name='Medium',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='cnn_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # PARALLEL TASK 3: Ensemble/Hybrid Model Training
    ensemble_training = run_domino_job_task(
        flyte_task_name='train_ensemble_model',
        command=f'python {working_dir}/src/demo_train_ensemble_model.py',
        hardware_tier_name='Large',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='ensemble_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # ============================================================================
    # PHASE 3: CHAMPION MODEL SELECTION AND REGISTRATION
    # ============================================================================

    # FINAL TASK: Champion Model Registration (depends on all 3 training tasks)
    champion_registration = run_domino_job_task(
        flyte_task_name='register_champion_model',
        command=f'python {working_dir}/src/demo_register_champion_model.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='vit_model_metrics', type=FlyteFile[TypeVar('json')], value=vit_training['vit_model_metrics']),
            Input(name='cnn_model_metrics', type=FlyteFile[TypeVar('json')], value=cnn_training['cnn_model_metrics']),
            Input(name='ensemble_model_metrics', type=FlyteFile[TypeVar('json')], value=ensemble_training['ensemble_model_metrics'])
        ],
        output_specs=[
            Output(name='champion_model_registration', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    return champion_registration['champion_model_registration']


@workflow
def seabed_etl_pipeline_unbalanced(gamma_transform: float = 0.5) -> CleanedSonarData.File(name="cleaned_sonar_data_unbalanced.zip"):
    '''
    SEABED ETL PIPELINE - UNBALANCED DATASET

    Processes the unbalanced training dataset (498 images).

    DEPLOYMENT:
    pyflyte run --remote flow.py seabed_etl_pipeline_unbalanced
    pyflyte run --remote flow.py seabed_etl_pipeline_unbalanced --gamma_transform 0.0

    :param gamma_transform: Gamma correction factor (0.5 default, 0 for log transform)
    :return: Cleaned dataset zip file as "Cleaned Sonar Data" artifact (unbalanced dataset)
    '''
    unbalanced_path = str(config.unbalanced_dataset_path)
    working_dir = config.domino_working_dir

    # STAGE 1: NORMALIZATION
    normalize = run_domino_job_task(
        flyte_task_name='normalize_sonar_images',
        command=f'python {etl_base_path}/etl_normalize.py --input_dir {unbalanced_path}',
        hardware_tier_name='Small',
        inputs=[
            Input(name='gamma', type=float, value=gamma_transform)
        ],
        output_specs=[Output(name='normalized_data', type=FlyteDirectory)],
        use_project_defaults_for_omitted=True
    )

    # STAGE 2: DENOISING
    denoise = run_domino_job_task(
        flyte_task_name='denoise_sonar_images',
        command=f'python {etl_base_path}/etl_denoise.py',
        hardware_tier_name='Small',
        inputs=[Input(name='normalized_data', type=FlyteDirectory, value=normalize['normalized_data'])],
        output_specs=[Output(name='denoised_data', type=FlyteDirectory)],
        use_project_defaults_for_omitted=True
    )

    # STAGE 3: ENHANCEMENT
    enhance = run_domino_job_task(
        flyte_task_name='enhance_sonar_features',
        command=f'python {etl_base_path}/etl_enhance.py',
        hardware_tier_name='Small',
        inputs=[Input(name='denoised_data', type=FlyteDirectory, value=denoise['denoised_data'])],
        output_specs=[Output(name='enhanced_data', type=FlyteDirectory)],
        use_project_defaults_for_omitted=True
    )

    # STAGE 4: PACKAGE
    package = run_domino_job_task(
        flyte_task_name='package_cleaned_data',
        command=f'python {etl_base_path}/etl_package.py',
        hardware_tier_name='Small',
        inputs=[Input(name='enhanced_data', type=FlyteDirectory, value=enhance['enhanced_data'])],
        output_specs=[Output(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')])],
        use_project_defaults_for_omitted=True
    )

    return package['cleaned_data_zip']


# Define Flow Artifact for trained models
TrainedModelArtifact = Artifact(name="Champion Model", type=DATA)

@workflow
def etl_and_model_training(input_dataset_path: str = None,
                          gamma_transform: float = 0.5) -> TrainedModelArtifact.File(name="champion_model_registration.json"):
    '''
    ETL AND MODEL TRAINING PIPELINE

    This comprehensive workflow demonstrates a complete machine learning pipeline:

        1. ETL PROCESSING: 4-stage sonar image preprocessing (same as existing ETL)
        2. PARALLEL TRAINING: Train 3 different models simultaneously
           - Vision Transformer (ViT) Model
           - Convolutional Neural Network (CNN) Model  
           - Ensemble/Hybrid Model
        3. CHAMPION SELECTION: Evaluate all models and register the best performer

    To run this workflow:

    pyflyte run --remote flow.py etl_and_model_training
    pyflyte run --remote flow.py etl_and_model_training --input_dataset_path /path/to/dataset --gamma_transform 0.0

    :param input_dataset_path: Path to input sonar imagery dataset (optional, defaults to balanced dataset)
    :param gamma_transform: Gamma correction factor (0.5 default, 0 for log transform)
    :return: Champion model registration data as "Champion Model" artifact
    '''

    # Use balanced dataset as default if no input path specified
    if input_dataset_path is None:
        input_dataset_path = str(config.balanced_dataset_path)
    
    working_dir = config.domino_working_dir

    # ============================================================================
    # PHASE 1: ETL PROCESSING (Sequential Pipeline)
    # ============================================================================

    # STAGE 1: NORMALIZATION AND GAMMA CORRECTION
    normalize = run_domino_job_task(
        flyte_task_name='etl_normalize_sonar_images',
        command=f'python {etl_base_path}/etl_normalize.py --input_dir {input_dataset_path}',
        hardware_tier_name='Small',
        inputs=[
            Input(name='gamma', type=float, value=gamma_transform)
        ],
        output_specs=[
            Output(name='normalized_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 2: DENOISING AND BACKGROUND SUBTRACTION
    denoise = run_domino_job_task(
        flyte_task_name='etl_denoise_sonar_images',
        command=f'python {etl_base_path}/etl_denoise.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='normalized_data', type=FlyteDirectory, value=normalize['normalized_data'])
        ],
        output_specs=[
            Output(name='denoised_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 3: FEATURE ENHANCEMENT AND CONTRAST OPTIMIZATION
    enhance = run_domino_job_task(
        flyte_task_name='etl_enhance_sonar_features',
        command=f'python {etl_base_path}/etl_enhance.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='denoised_data', type=FlyteDirectory, value=denoise['denoised_data'])
        ],
        output_specs=[
            Output(name='enhanced_data', type=FlyteDirectory)
        ],
        use_project_defaults_for_omitted=True
    )

    # STAGE 4: PACKAGE INTO ZIP FILE
    package = run_domino_job_task(
        flyte_task_name='etl_package_cleaned_data',
        command=f'python {etl_base_path}/etl_package.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='enhanced_data', type=FlyteDirectory, value=enhance['enhanced_data'])
        ],
        output_specs=[
            Output(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')])
        ],
        use_project_defaults_for_omitted=True
    )

    # ============================================================================
    # PHASE 2: PARALLEL MODEL TRAINING
    # ============================================================================

    # PARALLEL TASK 1: Vision Transformer (ViT) Training
    vit_training = run_domino_job_task(
        flyte_task_name='train_vit_model',
        command=f'python {working_dir}/src/demo_train_vit_model.py',
        hardware_tier_name='Medium',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='vit_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # PARALLEL TASK 2: Convolutional Neural Network (CNN) Training  
    cnn_training = run_domino_job_task(
        flyte_task_name='train_cnn_model',
        command=f'python {working_dir}/src/demo_train_cnn_model.py',
        hardware_tier_name='Medium',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='cnn_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # PARALLEL TASK 3: Ensemble/Hybrid Model Training
    ensemble_training = run_domino_job_task(
        flyte_task_name='train_ensemble_model',
        command=f'python {working_dir}/src/demo_train_ensemble_model.py',
        hardware_tier_name='Large',
        inputs=[
            Input(name='cleaned_data_zip', type=FlyteFile[TypeVar('zip')], value=package['cleaned_data_zip'])
        ],
        output_specs=[
            Output(name='ensemble_model_metrics', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    # ============================================================================
    # PHASE 3: CHAMPION MODEL SELECTION AND REGISTRATION
    # ============================================================================

    # FINAL TASK: Champion Model Registration (depends on all 3 training tasks)
    champion_registration = run_domino_job_task(
        flyte_task_name='register_champion_model',
        command=f'python {working_dir}/src/demo_register_champion_model.py',
        hardware_tier_name='Small',
        inputs=[
            Input(name='vit_model_metrics', type=FlyteFile[TypeVar('json')], value=vit_training['vit_model_metrics']),
            Input(name='cnn_model_metrics', type=FlyteFile[TypeVar('json')], value=cnn_training['cnn_model_metrics']),
            Input(name='ensemble_model_metrics', type=FlyteFile[TypeVar('json')], value=ensemble_training['ensemble_model_metrics'])
        ],
        output_specs=[
            Output(name='champion_model_registration', type=FlyteFile[TypeVar('json')])
        ],
        use_project_defaults_for_omitted=True
    )

    return champion_registration['champion_model_registration']
