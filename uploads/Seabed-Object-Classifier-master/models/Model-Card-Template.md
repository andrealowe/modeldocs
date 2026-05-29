# SEABED TARGET CLASSIFICATION MODEL

## MISSION BRIEF

This is an **enhanced Vision Transformer (ViT)** model optimized for seabed object classification with **improved ship detection performance**. The model addresses severe class imbalance using advanced techniques including balanced sampling, focal loss, and enhanced data augmentation.

### OPERATIONAL CAPABILITIES
- **Base Model**: Google ViT-Base-Patch16-224-in21k
- **Target Classes**: 3 (Plane, Ship, Seafloor)
- **Enhanced Architecture**: Class-imbalance aware training
- **Optimization**: Optuna hyperparameter optimization with Domino experiment tracking
- **Performance Focus**: Specialized ship class detection improvements

## INTELLIGENCE ASSESSMENT

### Target Distribution (Training)
- **Plane**: 38 images (7.6%) - *Minority class*
- **Ship**: 82 images (16.5%) - *Primary target class*  
- **Seafloor**: 378 images (75.9%) - *Majority class*

### DATA SOURCES
- **Training Set**: `unbalanced_training_validation_set/`
- **Test Set**: `test_set/`
- **Total Images**: 859 (498 train + 361 test)

## TACTICAL ENHANCEMENTS

### TARGET ACQUISITION SOLUTIONS
- **Weighted Sampling**: Balanced representation during training
- **Enhanced Augmentation**: Ship-specific transformations
- **Focal Loss**: Addresses severe class imbalance (optional)
- **Label Smoothing**: Prevents overconfidence (0.1 factor)

### PERFORMANCE UPGRADES
- **Ship-focused Metrics**: Detailed per-class F1, precision, recall
- **Best Model Selection**: Optimizes for ship F1-score
- **Advanced Augmentation**: Color jitter, rotation, blur for robustness
- **Mixed Precision**: FP16 for faster training

### TRAINING PARAMETERS
- **Learning Rate**: 5e-5 (optimized for minority classes)
- **Batch Size**: 16 (better gradient updates)
- **Epochs**: 5 (sufficient for convergence)
- **Scheduler**: Cosine decay with 10% warmup
- **Evaluation**: Every 50 steps for close monitoring

## EXPECTED PERFORMANCE

### MISSION OBJECTIVES
- **Overall Accuracy**: >90%
- **Ship F1-Score**: >80% (primary target)
- **Balanced Performance**: Improved minority class detection

### ASSESSMENT PROTOCOLS
- Detailed confusion matrices
- Per-class precision/recall analysis
- Ship-specific performance tracking
- Domino experiment logging

## PRIMARY TARGET FOCUS

This model specifically addresses poor ship class performance through:

1. **Targeted Optimization**: Ship F1-score as primary metric
2. ** Balanced Training**: Equal sampling across all classes
3. **Enhanced Augmentation**: Ship-specific transformations
4. **Detailed Monitoring**: Per-class performance tracking
5. **Hyperparameter Tuning**: Optimized for minority class performance

---

*This enhanced model represents a significant improvement over the baseline VIT implementation, with specialized techniques to address the challenging ship detection task in imbalanced seabed imagery.*




