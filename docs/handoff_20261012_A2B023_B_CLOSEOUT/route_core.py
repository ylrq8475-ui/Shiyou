"""Untrained fixed whole-well router. No labels, fitting, thresholds or I/O."""
import numpy as np

def fallback_mask(raw_last):
    raw = np.asarray(raw_last, dtype=float)
    if raw.ndim != 1 or raw.size == 0:
        raise ValueError('one raw pre-imputation value per well is required')
    return ~(np.isfinite(raw) & (raw > 0))

def route_predictions(raw_last, scaled_log_predictions, absolute_log_predictions):
    """Both inputs are already inverse-transformed RCYL predictions, (wells,12)."""
    mask = fallback_mask(raw_last)
    b0 = np.asarray(scaled_log_predictions, dtype=float)
    c1 = np.asarray(absolute_log_predictions, dtype=float)
    if b0.shape != (mask.size, 12) or c1.shape != b0.shape:
        raise ValueError('two aligned complete 12-month prediction matrices are required')
    if not np.isfinite(b0).all() or not np.isfinite(c1).all():
        raise ValueError('predictions must be finite')
    if (b0 < 0).any() or (c1 < 0).any():
        raise ValueError('predictions must already use the locked nonnegative inverse transform')
    return np.where(mask[:, None], c1, b0)
