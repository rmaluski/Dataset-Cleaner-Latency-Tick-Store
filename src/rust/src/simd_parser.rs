use arrow::array::{ArrayRef, StringArray, Float64Array, Int64Array};
use arrow::datatypes::{DataType, Field, Schema};
use arrow::record_batch::RecordBatch;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::time::Instant;

#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

#[pyclass]
pub struct SimdParser {
    stats: HashMap<String, f64>,
}

#[pymethods]
impl SimdParser {
    #[new]
    fn new() -> Self {
        SimdParser {
            stats: HashMap::new(),
        }
    }

    /// Parse CSV data with SIMD optimizations
    #[pyo3(name = "parse_csv")]
    fn parse_csv_py(
        &mut self,
        data: &[u8],
        delimiter: char,
        batch_size: usize,
    ) -> PyResult<PyObject> {
        let start_time = Instant::now();
        
        let result = self.parse_csv(data, delimiter, batch_size);
        
        let duration = start_time.elapsed();
        self.stats.insert("parse_time_ms".to_string(), duration.as_millis() as f64);
        self.stats.insert("bytes_processed".to_string(), data.len() as f64);
        
        Python::with_gil(|py| {
            match result {
                Ok(table) => {
                    let pyarrow = py.import("pyarrow")?;
                    let table_py = pyarrow.call_method1("Table", (table,))?;
                    Ok(table_py.to_object(py))
                }
                Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
            }
        })
    }

    /// Get parsing statistics
    #[pyo3(name = "get_stats")]
    fn get_stats_py(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let stats_dict = PyDict::new(py);
            for (key, value) in &self.stats {
                stats_dict.set_item(py, key, *value)?;
            }
            Ok(stats_dict.to_object(py))
        })
    }
}

impl SimdParser {
    /// Parse CSV data with SIMD optimizations
    pub fn parse_csv(
        &self,
        data: &[u8],
        delimiter: char,
        batch_size: usize,
    ) -> Result<arrow::record_batch::RecordBatch, Box<dyn std::error::Error>> {
        let csv_string = String::from_utf8_lossy(data);
        let lines: Vec<&str> = csv_string.lines().collect();
        
        if lines.is_empty() {
            return Err("Empty CSV data".into());
        }

        // Parse header
        let header = self.parse_line_simd(lines[0], delimiter);
        let schema = self.create_schema(&header);

        // Parse data rows
        let mut columns: Vec<Vec<String>> = vec![Vec::new(); header.len()];
        
        for line in lines.iter().skip(1) {
            let row = self.parse_line_simd(line, delimiter);
            for (i, value) in row.iter().enumerate() {
                if i < columns.len() {
                    columns[i].push(value.to_string());
                }
            }
        }

        // Convert to Arrow arrays
        let arrays: Vec<ArrayRef> = columns
            .iter()
            .zip(schema.fields().iter())
            .map(|(col_data, field)| self.create_array(col_data, field.data_type()))
            .collect::<Result<Vec<_>, _>>()?;

        RecordBatch::try_new(Arc::new(schema), arrays)
            .map_err(|e| e.into())
    }

    /// SIMD-optimized line parsing
    fn parse_line_simd(&self, line: &str, delimiter: char) -> Vec<String> {
        let mut tokens = Vec::new();
        let mut current_token = String::new();
        let mut in_quotes = false;

        #[cfg(target_arch = "x86_64")]
        if delimiter == ',' && line.len() >= 32 {
            // Use AVX2 for comma-separated values
            unsafe {
                let bytes = line.as_bytes();
                let mut i = 0;
                
                while i + 32 <= bytes.len() {
                    let data = _mm256_loadu_si256(bytes.as_ptr().add(i) as *const __m256i);
                    let commas = _mm256_cmpeq_epi8(data, _mm256_set1_epi8(b','));
                    let mask = _mm256_movemask_epi8(commas);
                    
                    if mask != 0 {
                        let mut bit_pos = 0;
                        while bit_pos < 32 {
                            if (mask >> bit_pos) & 1 != 0 {
                                tokens.push(current_token.clone());
                                current_token.clear();
                            } else {
                                current_token.push(bytes[i + bit_pos] as char);
                            }
                            bit_pos += 1;
                        }
                    } else {
                        current_token.push_str(&line[i..i + 32]);
                    }
                    i += 32;
                }
                
                // Handle remaining bytes
                for &byte in &bytes[i..] {
                    if byte == b',' && !in_quotes {
                        tokens.push(current_token.clone());
                        current_token.clear();
                    } else if byte == b'"' {
                        in_quotes = !in_quotes;
                    } else {
                        current_token.push(byte as char);
                    }
                }
            }
        } else {
            // Fallback to standard parsing
            for ch in line.chars() {
                if ch == delimiter && !in_quotes {
                    tokens.push(current_token.clone());
                    current_token.clear();
                } else if ch == '"' {
                    in_quotes = !in_quotes;
                } else {
                    current_token.push(ch);
                }
            }
        }

        tokens.push(current_token);
        tokens
    }

    /// Create Arrow schema from header
    fn create_schema(&self, header: &[String]) -> Schema {
        let fields: Vec<Field> = header
            .iter()
            .map(|name| Field::new(name, DataType::Utf8, true))
            .collect();
        Schema::new(fields)
    }

    /// Create Arrow array from column data
    fn create_array(
        &self,
        data: &[String],
        data_type: &DataType,
    ) -> Result<ArrayRef, Box<dyn std::error::Error>> {
        match data_type {
            DataType::Utf8 => {
                let array = StringArray::from(data.to_vec());
                Ok(Arc::new(array))
            }
            DataType::Float64 => {
                let values: Result<Vec<f64>, _> = data
                    .iter()
                    .map(|s| s.parse::<f64>())
                    .collect();
                let array = Float64Array::from(values?);
                Ok(Arc::new(array))
            }
            DataType::Int64 => {
                let values: Result<Vec<i64>, _> = data
                    .iter()
                    .map(|s| s.parse::<i64>())
                    .collect();
                let array = Int64Array::from(values?);
                Ok(Arc::new(array))
            }
            _ => {
                // Default to string
                let array = StringArray::from(data.to_vec());
                Ok(Arc::new(array))
            }
        }
    }
}

use std::sync::Arc; 