"""Asset validation entry point for the model-based bridge prototype."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('test_models.py')),run_name='__main__')
