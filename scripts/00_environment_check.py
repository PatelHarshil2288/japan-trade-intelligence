
import sys
import duckdb
import pandas
import polars
import numpy
import pyarrow
import scipy
import sklearn
import plotly

print("PYTHON:", sys.version)
print("EXECUTABLE:", sys.executable)

packages = {
    "DuckDB": duckdb.__version__,
    "Pandas": pandas.__version__,
    "Polars": polars.__version__,
    "NumPy": numpy.__version__,
    "PyArrow": pyarrow.__version__,
    "SciPy": scipy.__version__,
    "Scikit-learn": sklearn.__version__,
    "Plotly": plotly.__version__,
}

print("\nPACKAGE VERSIONS")

for name, version in packages.items():
    print(f"{name}: {version}")

print("\nENVIRONMENT VERIFICATION COMPLETED")
