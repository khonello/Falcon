-- The local model's reading of a case, kept beside the rules' own conclusion and labelled as the model's (engine/detective/labels.py). It never changes a
-- weight or a level. NULL: it was not asked, or had no opinion. '': it read the case as nothing odd.
ALTER TABLE detective_cases ADD COLUMN model_says TEXT;
