"""
serial.py — Serialization & Persistence
=========================================

JSON and pickle serialization of entire snapkit state.
Export delta history, attention allocations, and script libraries.

Version-stamped serialization for forward compatibility.
"""

import json
import pickle
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import (
    Optional, Dict, Any, List, 
    Union, TextIO, BinaryIO
)
from pathlib import Path
from datetime import datetime
import io
import os


# Current serialization format version
SERIALIZATION_VERSION = "1.0.0"


class SnapKitEncoder(json.JSONEncoder):
    """Custom JSON encoder for snapkit data structures."""
    
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return {
                '__type__': 'ndarray',
                'data': obj.tolist(),
                'dtype': str(obj.dtype),
                'shape': list(obj.shape),
            }
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        if hasattr(obj, '_asdict'):
            return obj._asdict()
        # Handle enum types
        if hasattr(obj, 'value'):
            return obj.value
        return super().default(obj)


def _decode_hook(dct: Dict[str, Any]) -> Any:
    """JSON decode hook for custom types."""
    if '__type__' in dct:
        t = dct['__type__']
        if t == 'ndarray':
            return np.array(dct['data'], dtype=dct.get('dtype', float))
    return dct


def _make_serializable(obj: Any) -> Any:
    """Recursively convert an object to JSON-serializable form."""
    if obj is None:
        return None
    if isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if hasattr(obj, 'value'):  # Enum
        return obj.value
    if hasattr(obj, '__dict__'):
        return _make_serializable(obj.__dict__)
    return str(obj)


def _make_serializable_statistics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Convert statistics dict to fully serializable form."""
    return _make_serializable(stats)


# ─── Core Serialization Functions ────────────────────────────────────


def save(
    data: Any,
    path: Union[str, Path],
    format: str = 'json',
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Save snapkit state to file.
    
    Supports JSON (human-readable) and pickle (full object state).
    
    Args:
        data: Snapkit object or dict to save.
        path: File path. Extension can indicate format (.json, .pkl).
        format: 'json' or 'pickle'. Ignored if path has extension.
        metadata: Optional metadata dict to include.
    
    Returns:
        Path string the data was saved to.
    
    Examples:
        >>> snap = SnapFunction(tolerance=0.1)
        >>> save(snap.statistics, "snap_state.json")
        '/path/to/snap_state.json'
        
        >>> save(snap, "snap_full.pkl", format='pickle')
        '/path/to/snap_full.pkl'
    """
    path = Path(path)
    
    # Determine format from extension
    if path.suffix == '.json':
        format = 'json'
    elif path.suffix in ('.pkl', '.pickle'):
        format = 'pickle'
    
    # Add metadata
    save_data = {
        '__snapkit_serialized__': True,
        '__version__': SERIALIZATION_VERSION,
        '__timestamp__': datetime.utcnow().isoformat(),
    }
    
    if metadata:
        save_data['__metadata__'] = metadata
    
    if isinstance(data, dict):
        save_data['data'] = _make_serializable(data)
    else:
        save_data['data'] = data
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(path, 'w') as f:
            json.dump(save_data, f, cls=SnapKitEncoder, indent=2)
    elif format == 'pickle':
        with open(path, 'wb') as f:
            pickle.dump(save_data, f)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'pickle'.")
    
    return str(path)


def load(
    path: Union[str, Path],
    format: Optional[str] = None,
) -> Any:
    """
    Load snapkit state from file.
    
    Args:
        path: File path.
        format: 'json' or 'pickle'. Auto-detected from extension if None.
    
    Returns:
        Loaded data.
    
    Examples:
        >>> stats = load("snap_state.json")
        >>> snap = load("snap_full.pkl")
    """
    path = Path(path)
    
    if format is None:
        if path.suffix == '.json':
            format = 'json'
        elif path.suffix in ('.pkl', '.pickle'):
            format = 'pickle'
        else:
            format = 'json'  # Default
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if format == 'json':
        with open(path, 'r') as f:
            load_data = json.load(f, object_hook=_decode_hook)
    elif format == 'pickle':
        with open(path, 'rb') as f:
            load_data = pickle.load(f)
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    # Validate
    if not load_data.get('__snapkit_serialized__'):
        return load_data  # Plain data, not snapkit-serialized
    
    version = load_data.get('__version__', '0.0.0')
    
    return load_data.get('data', load_data)


# ─── CSV Export ──────────────────────────────────────────────────────


def export_csv(
    data: List[Dict[str, Any]],
    path: Union[str, Path],
    columns: Optional[List[str]] = None,
    include_header: bool = True,
) -> str:
    """
    Export list of dicts as CSV.
    
    Useful for exporting delta history, attention allocations, etc.
    
    Args:
        data: List of dicts to export.
        path: Output CSV path.
        columns: Columns to include. None = all keys from first item.
        include_header: Whether to include CSV header row.
    
    Returns:
        Path string.
    
    Examples:
        >>> deltas = [{'magnitude': 0.3, 'stream': 'cpu'},
        ...           {'magnitude': 0.1, 'stream': 'mem'}]
        >>> export_csv(deltas, "deltas.csv", columns=['stream', 'magnitude'])
        '/path/to/deltas.csv'
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if not data:
        # Write empty CSV with just header
        with open(path, 'w') as f:
            if columns and include_header:
                f.write(','.join(str(c) for c in columns) + '\n')
        return str(path)
    
    # Determine columns
    if columns is None:
        columns = list(data[0].keys())
    
    with open(path, 'w') as f:
        # Header
        if include_header:
            f.write(','.join(str(c) for c in columns) + '\n')
        
        # Rows
        for item in data:
            row = []
            for col in columns:
                val = item.get(col, '')
                # Format for CSV
                val_str = str(_make_serializable(val))
                if ',' in val_str or '"' in val_str or '\n' in val_str:
                    val_str = '"' + val_str.replace('"', '""') + '"'
                row.append(val_str)
            f.write(','.join(row) + '\n')
    
    return str(path)


# ─── Dict Conversion ────────────────────────────────────────────────


def to_dict(obj: Any) -> Dict[str, Any]:
    """
    Convert a snapkit object to a plain dictionary.
    
    Args:
        obj: Any snapkit object (SnapFunction, DeltaDetector, etc.)
    
    Returns:
        Plain dictionary representation.
    
    Examples:
        >>> snap = SnapFunction(tolerance=0.1)
        >>> d = to_dict(snap)
        >>> d['tolerance']
        0.1
    """
    if hasattr(obj, 'statistics'):
        stats = obj.statistics
        if isinstance(stats, dict):
            return _make_serializable(stats)
    
    if hasattr(obj, '__dict__'):
        return _make_serializable(obj.__dict__)
    
    return _make_serializable(obj)


def from_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Restore a dict from serialized form (reverse of to_dict).
    
    Currently returns the dict directly (no reconstruction of
    custom objects). For full object reconstruction, use pickle.
    
    Args:
        data: Dict to restore.
    
    Returns:
        Restored dict.
    """
    return dict(data)  # Dict is portable; objects need pickle


# ─── Convenience Functions ──────────────────────────────────────────


def save_snapshot(
    snap_function: Any,
    detector: Any = None,
    budget: Any = None,
    library: Any = None,
    path: Union[str, Path] = "snapkit_snapshot.json",
) -> str:
    """
    Save a full system snapshot with all major components.
    
    Args:
        snap_function: SnapFunction instance.
        detector: DeltaDetector instance (optional).
        budget: AttentionBudget instance (optional).
        library: ScriptLibrary instance (optional).
        path: Output path.
    
    Returns:
        Path string.
    """
    snapshot = {}
    
    if snap_function is not None:
        snapshot['snap_function'] = _make_serializable(snap_function.statistics)
    
    if detector is not None:
        snapshot['delta_detector'] = _make_serializable(detector.statistics)
    
    if budget is not None:
        snapshot['attention_budget'] = _make_serializable(budget.statistics)
    
    if library is not None:
        snapshot['script_library'] = _make_serializable(library.statistics)
    
    # Add derived metrics
    snapshot['summary'] = _make_serializable({
        'snap_rate': snap_function.snap_rate if snap_function else None,
        'delta_rate': snap_function.delta_rate if snap_function else None,
        'tolerance': snap_function.tolerance if snap_function else None,
        'baseline': snap_function.baseline if snap_function else None,
    })
    
    return save(snapshot, path)


def load_snapshot(
    path: Union[str, Path] = "snapkit_snapshot.json",
) -> Dict[str, Any]:
    """
    Load a previously saved system snapshot.
    
    Args:
        path: Path to snapshot file.
    
    Returns:
        Dict with 'snap_function', 'delta_detector', 'attention_budget',
        'script_library', 'summary' keys (as available).
    """
    return load(path)


# ─── Version Utilities ──────────────────────────────────────────────


def get_serialization_version() -> str:
    """Get the current serialization format version."""
    return SERIALIZATION_VERSION


def check_version(data: Dict[str, Any]) -> bool:
    """
    Check if serialized data is compatible with this version.
    
    Args:
        data: Loaded serialized data.
    
    Returns:
        True if compatible, False if version mismatch.
    """
    if not isinstance(data, dict):
        return False
    version = data.get('__version__', '0.0.0')
    # Simple semantic check: major version must match
    try:
        data_major = version.split('.')[0]
        this_major = SERIALIZATION_VERSION.split('.')[0]
        return data_major == this_major
    except (IndexError, AttributeError):
        return False


def migrate_from_v0(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate data from v0.x format to current.
    
    Args:
        data: Data in v0 format.
    
    Returns:
        Data in current format.
    """
    version = data.get('__version__', '0.0.0')
    if not version.startswith('0.'):
        return data  # Already migrated or unknown format
    
    # v0 used flat structure, v1 wraps in 'data' key
    if 'data' not in data:
        return {
            '__snapkit_serialized__': True,
            '__version__': SERIALIZATION_VERSION,
            '__timestamp__': datetime.utcnow().isoformat(),
            '__metadata__': {'migrated_from': version},
            'data': {k: v for k, v in data.items() if not k.startswith('__')},
        }
    
    return data
