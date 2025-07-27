#include "simd_parser.hpp"
#include <arrow/csv/api.h>
#include <arrow/io/api.h>
#include <arrow/result.h>
#include <chrono>
#include <fstream>
#include <sstream>
#include <immintrin.h> // For AVX2/AVX-512 instructions

namespace dataset_core {

SimdParser::SimdParser() = default;
SimdParser::~SimdParser() = default;

arrow::Result<std::shared_ptr<arrow::Table>> SimdParser::parse_csv_simd(
    const std::string& data,
    char delimiter,
    int64_t batch_size) {
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Use Arrow's CSV reader with optimized settings
    auto input = std::make_shared<arrow::io::BufferReader>(data);
    
    arrow::csv::ReadOptions read_options;
    read_options.block_size = 1 << 20; // 1MB blocks
    read_options.skip_rows = 0;
    read_options.batch_size = batch_size;
    
    arrow::csv::ParseOptions parse_options;
    parse_options.delimiter = delimiter;
    parse_options.quote_char = '"';
    parse_options.escape_char = '\\';
    parse_options.newlines_in_values = false;
    
    arrow::csv::ConvertOptions convert_options;
    convert_options.strings_can_be_null = true;
    convert_options.null_values = {"", "null", "NULL", "Null"};
    
    // Create CSV reader
    ARROW_ASSIGN_OR_RAISE(auto reader,
        arrow::csv::TableReader::Make(
            arrow::io::default_io_context(),
            input,
            read_options,
            parse_options,
            convert_options
        ));
    
    // Read all data
    ARROW_ASSIGN_OR_RAISE(auto table, reader->Read());
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
    
    // Update statistics
    stats_.rows_processed = table->num_rows();
    stats_.bytes_processed = data.size();
    stats_.parse_time_ms = duration.count() / 1000.0;
    stats_.throughput_mbps = (data.size() / (1024.0 * 1024.0)) / (stats_.parse_time_ms / 1000.0);
    
    return table;
}

arrow::Result<std::shared_ptr<arrow::Table>> SimdParser::parse_csv_file_simd(
    const std::string& file_path,
    char delimiter,
    int64_t batch_size) {
    
    // Read file into memory for SIMD processing
    std::ifstream file(file_path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        return arrow::Status::IOError("Failed to open file: " + file_path);
    }
    
    auto file_size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    std::string data(file_size, '\0');
    file.read(&data[0], file_size);
    file.close();
    
    return parse_csv_simd(data, delimiter, batch_size);
}

arrow::Result<std::vector<std::string>> SimdParser::tokenize_line_simd(
    const std::string& line,
    char delimiter) {
    
    std::vector<std::string> tokens;
    std::string current_token;
    bool in_quotes = false;
    
    // SIMD-optimized tokenization for common cases
    if (delimiter == ',' && line.size() >= 32) {
        // Use AVX2 for comma-separated values
        const char* ptr = line.data();
        const char* end = ptr + line.size();
        
        // Process 32 bytes at a time with AVX2
        while (ptr + 32 <= end) {
            __m256i data = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(ptr));
            __m256i commas = _mm256_cmpeq_epi8(data, _mm256_set1_epi8(','));
            int mask = _mm256_movemask_epi8(commas);
            
            // Process matches
            while (mask != 0) {
                int pos = __builtin_ctz(mask);
                tokens.emplace_back(ptr, ptr + pos);
                ptr += pos + 1;
                mask &= mask - 1;
            }
            
            ptr += 32;
        }
        
        // Handle remaining bytes
        while (ptr < end) {
            if (*ptr == delimiter && !in_quotes) {
                tokens.push_back(current_token);
                current_token.clear();
            } else if (*ptr == '"') {
                in_quotes = !in_quotes;
            } else {
                current_token += *ptr;
            }
            ++ptr;
        }
    } else {
        // Fallback to standard tokenization
        for (char c : line) {
            if (c == delimiter && !in_quotes) {
                tokens.push_back(current_token);
                current_token.clear();
            } else if (c == '"') {
                in_quotes = !in_quotes;
            } else {
                current_token += c;
            }
        }
    }
    
    tokens.push_back(current_token);
    return tokens;
}

arrow::Result<std::shared_ptr<arrow::Schema>> SimdParser::infer_schema_simd(
    const std::vector<std::string>& sample_rows,
    char delimiter) {
    
    if (sample_rows.empty()) {
        return arrow::Status::Invalid("No sample rows provided");
    }
    
    // Parse first row to get column names
    ARROW_ASSIGN_OR_RAISE(auto header_tokens, tokenize_line_simd(sample_rows[0], delimiter));
    
    std::vector<std::shared_ptr<arrow::Field>> fields;
    std::vector<std::vector<std::string>> column_samples(header_tokens.size());
    
    // Parse sample rows to infer types
    for (size_t i = 1; i < std::min(sample_rows.size(), size_t(100)); ++i) {
        ARROW_ASSIGN_OR_RAISE(auto tokens, tokenize_line_simd(sample_rows[i], delimiter));
        for (size_t j = 0; j < std::min(tokens.size(), column_samples.size()); ++j) {
            column_samples[j].push_back(tokens[j]);
        }
    }
    
    // Infer types for each column
    for (size_t i = 0; i < header_tokens.size(); ++i) {
        std::shared_ptr<arrow::DataType> inferred_type = arrow::utf8();
        
        if (i < column_samples.size()) {
            // Try to infer numeric types
            bool all_numeric = true;
            bool all_integer = true;
            bool has_decimal = false;
            
            for (const auto& value : column_samples[i]) {
                if (value.empty()) continue;
                
                try {
                    size_t pos = 0;
                    std::stod(value, &pos);
                    if (pos != value.length()) {
                        all_numeric = false;
                        break;
                    }
                    
                    if (value.find('.') != std::string::npos) {
                        has_decimal = true;
                    }
                } catch (...) {
                    all_numeric = false;
                    break;
                }
            }
            
            if (all_numeric) {
                if (has_decimal) {
                    inferred_type = arrow::float64();
                } else {
                    inferred_type = arrow::int64();
                }
            }
        }
        
        fields.push_back(arrow::field(header_tokens[i], inferred_type));
    }
    
    return std::make_shared<arrow::Schema>(fields);
}

arrow::Result<std::shared_ptr<arrow::Array>> SimdParser::parse_column_simd(
    const std::vector<std::string>& values,
    const std::shared_ptr<arrow::DataType>& type) {
    
    if (type->id() == arrow::Type::INT64) {
        arrow::Int64Builder builder;
        for (const auto& value : values) {
            if (value.empty()) {
                ARROW_RETURN_NOT_OK(builder.AppendNull());
            } else {
                try {
                    ARROW_RETURN_NOT_OK(builder.Append(std::stoll(value)));
                } catch (...) {
                    ARROW_RETURN_NOT_OK(builder.AppendNull());
                }
            }
        }
        return builder.Finish();
    } else if (type->id() == arrow::Type::DOUBLE) {
        arrow::DoubleBuilder builder;
        for (const auto& value : values) {
            if (value.empty()) {
                ARROW_RETURN_NOT_OK(builder.AppendNull());
            } else {
                try {
                    ARROW_RETURN_NOT_OK(builder.Append(std::stod(value)));
                } catch (...) {
                    ARROW_RETURN_NOT_OK(builder.AppendNull());
                }
            }
        }
        return builder.Finish();
    } else {
        arrow::StringBuilder builder;
        for (const auto& value : values) {
            ARROW_RETURN_NOT_OK(builder.Append(value));
        }
        return builder.Finish();
    }
}

} // namespace dataset_core 