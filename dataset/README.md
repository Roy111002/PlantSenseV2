# Dataset plan
Metadata: image_path, plant_species, cultivar, growth_stage, condition_label, symptom_labels, diagnosis_source, capture_date, plant_id, capture_session.
Include healthy and affected examples for each species. Split by plant identity or capture session (not random near-duplicate images) to avoid leakage. Keep a held-out test set and document dataset licenses/provenance. Do not assume internet image labels are ground truth.
