use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::sync::Arc;
use tokio::sync::Mutex;

mod simd_parser;
mod stream_processor;
mod metrics;
mod error;

use simd_parser::SimdParser;
use stream_processor::StreamProcessor;
use metrics::MetricsCollector;

/// Python module for high-performance data processing
#[pymodule]
fn dataset_core_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SimdParser>()?;
    m.add_class::<StreamProcessor>()?;
    m.add_class::<MetricsCollector>()?;
    m.add_function(wrap_pyfunction!(parse_csv_simd, m)?)?;
    m.add_function(wrap_pyfunction!(process_stream, m)?)?;
    Ok(())
}

/// High-performance CSV parsing with SIMD optimizations
#[pyfunction]
fn parse_csv_simd(
    data: &[u8],
    delimiter: Option<char>,
    batch_size: Option<usize>,
) -> PyResult<PyObject> {
    let parser = SimdParser::new();
    let result = parser.parse_csv(data, delimiter.unwrap_or(','), batch_size.unwrap_or(16384));
    
    Python::with_gil(|py| {
        match result {
            Ok(table) => {
                // Convert Arrow table to Python object
                let pyarrow = py.import("pyarrow")?;
                let table_py = pyarrow.call_method1("Table", (table,))?;
                Ok(table_py.to_object(py))
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        }
    })
}

/// Process high-volume data streams
#[pyfunction]
fn process_stream(
    stream_config: PyObject,
) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let processor = StreamProcessor::new();
        
        // Extract configuration from Python object
        let source_url: String = stream_config.getattr(py, "source_url")?.extract(py)?;
        let batch_size: usize = stream_config.getattr(py, "batch_size")?.extract(py)?;
        let schema_id: String = stream_config.getattr(py, "schema_id")?.extract(py)?;
        
        let result = processor.process_stream(&source_url, batch_size, &schema_id);
        
        match result {
            Ok(stats) => {
                // Return processing statistics
                let stats_dict = PyDict::new(py);
                stats_dict.set_item(py, "rows_processed", stats.rows_processed)?;
                stats_dict.set_item(py, "bytes_processed", stats.bytes_processed)?;
                stats_dict.set_item(py, "throughput_mbps", stats.throughput_mbps)?;
                stats_dict.set_item(py, "processing_time_ms", stats.processing_time_ms)?;
                Ok(stats_dict.to_object(py))
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simd_parser() {
        let csv_data = b"ts,symbol,price,size\n2025-01-27T09:30:00,ES,4500.25,100\n";
        let result = parse_csv_simd(csv_data, Some(','), Some(1000));
        assert!(result.is_ok());
    }

    #[test]
    fn test_stream_processor() {
        // Test stream processing with mock data
        let processor = StreamProcessor::new();
        let result = processor.process_stream("mock://test", 1000, "ticks_v1");
        assert!(result.is_ok());
    }
} 