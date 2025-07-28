use thiserror::Error;

#[derive(Error, Debug)]
pub enum DatasetError {
    #[error("CSV parsing error: {0}")]
    CsvParseError(String),
    
    #[error("Arrow error: {0}")]
    ArrowError(String),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Unknown error: {0}")]
    Unknown(String),
}

pub type Result<T> = std::result::Result<T, DatasetError>; 