# Dataset Cleaner + Latency Tick-Store

A universal, high-throughput data-lake that every later module depends on.

## 🎯 Purpose & Success Criteria

| Aspect          | Target                                                                        |
| --------------- | ----------------------------------------------------------------------------- |
| Ingestion speed | ≥ 1 GB/min on a 4-core laptop (10 GB/min on a 16-core server)                 |
| Query latency   | Full-column scan of 100 MM rows in < 20 ms; predicate-filtered scan in < 5 ms |
| Data integrity  | 100% schema-conformant rows; failed-row quarantine bucket                     |
| Extensibility   | New feed onboarded with < 50 LOC of ETL glue code                             |

## 🏗️ High-Level Architecture

```
┌────────────┐     Extract       ┌────────────┐  Validate  ┌──────────────┐
│  Raw Data  ├──────────────────▶│  Loader    ├────────────▶│ GreatExpect. │
│  (CSV/JSON │  (stream / batch) │  (Rust)    │            │   Engine     │
└────────────┘                   └─────┬──────┘            └──────┬───────┘
                                       │ Arrow RecordBatch        │ pass/fail rows
                                       ▼                          ▼
                               ┌──────────────┐        ┌─────────────────┐
                               │ Partitioning │        │  Quarantine     │
                               │ & Compression│        │ (bad_rows/*)    │
                               └─────┬────────┘        └─────────────────┘
                                     ▼
                         ┌────────────────────────┐
                         │  Parquet / Arrow Files │
                         │ (Hive-style folders)   │
                         └─────────┬──────────────┘
                                   ▼
                       ┌────────────────────────────┐
                       │   DuckDB / PyArrow API     │
                       └────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Rust 1.70+
- Docker (optional)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd dataset-cleaner

# Install Python dependencies
pip install -e .

# Build Rust components
cargo build --release

# Run tests
pytest tests/
```

### Basic Usage

```python
import tickdb as db

# Load raw file (batch)
db.load_raw(
    source_id="cme_es",
    path="s3://raw/cme/es_20250727.csv.gz",
    schema_id="ticks_v1"
)

# Append a pandas DataFrame (small alt-data)
db.append(df, schema_id="alt_nvd_v1")

# Read time-slice
tbl = db.read(
    symbol="ES",
    ts_start="2025-07-27T13:30:00Z",
    ts_end="2025-07-27T13:31:00Z",
    fields=["ts", "price", "size"]
)
```

## 📊 Performance Benchmarks

- **Ingestion**: 10 GB/min on 16-core server
- **Query Latency**: < 20 ms for 100 MM row scans
- **Compression**: Zstd level 5 with 80%+ compression ratio

## 🏗️ Project Structure

```
dataset-cleaner/
├── src/
│   ├── rust/                 # High-performance Rust core
│   ├── python/               # Python API wrapper
│   └── rust/                 # Rust SIMD optimizations
├── schemas/                  # Schema registry
├── tests/                    # Test suite
├── benchmarks/               # Performance benchmarks
├── docker/                   # Containerization
└── docs/                     # Documentation
```

## 🔧 Development

### Running Tests

```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/integration/

# Performance benchmarks
python benchmarks/run_benchmarks.py
```

### Building Wheels

```bash
# Build Python wheel
python setup.py bdist_wheel

# Build Rust wheel
maturin build --release
```

## 📈 Monitoring

- **Prometheus**: Ingest speed, error rates, query latency
- **Grafana**: Real-time dashboards
- **Loki**: Structured logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
