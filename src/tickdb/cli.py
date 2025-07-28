"""
Command-line interface for TickDB.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
import pandas as pd
import pyarrow as pa
from rich.console import Console
from rich.table import Table

from .core import TickDB, TickDBConfig

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--data-path", type=click.Path(), help="Data storage path")
@click.option("--quarantine-path", type=click.Path(), help="Quarantine storage path")
@click.pass_context
def main(ctx: click.Context, config: Optional[str], verbose: bool, data_path: Optional[str], quarantine_path: Optional[str]) -> None:
    """TickDB - High-throughput data lake for financial tick data."""
    
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Load configuration
    config_obj = TickDBConfig()
    if config:
        config_obj = _load_config(config)
    
    if data_path:
        config_obj.data_path = Path(data_path)
    if quarantine_path:
        config_obj.quarantine_path = Path(quarantine_path)
    
    # Initialize TickDB
    try:
        tickdb = TickDB(config_obj)
        ctx.obj = tickdb
    except Exception as e:
        console.print(f"[red]Failed to initialize TickDB: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("source_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.argument("schema_id")
@click.option("--delimiter", default=",", help="CSV delimiter")
@click.option("--skip-rows", default=0, help="Number of rows to skip")
@click.option("--column-names", help="Comma-separated column names")
@click.pass_obj
def load(tickdb: TickDB, source_id: str, file_path: str, schema_id: str, delimiter: str, skip_rows: int, column_names: Optional[str]) -> None:
    """Load a file into the data lake."""
    
    console.print(f"[blue]Loading file: {file_path}[/blue]")
    console.print(f"Source ID: {source_id}")
    console.print(f"Schema ID: {schema_id}")
    
    # Parse column names if provided
    columns = None
    if column_names:
        columns = [col.strip() for col in column_names.split(",")]
    
    try:
        result = tickdb.load_raw(
            source_id=source_id,
            path=file_path,
            schema_id=schema_id,
            delimiter=delimiter,
            skip_rows=skip_rows,
            column_names=columns
        )
        
        # Display results
        table = Table(title="Load Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Rows Processed", str(result.get("rows_processed", 0)))
        table.add_row("Rows Failed", str(result.get("rows_failed", 0)))
        table.add_row("Bytes Processed", f"{result.get('bytes_processed', 0):,}")
        table.add_row("Files Created", str(len(result.get("files_created", []))))
        table.add_row("Processing Time (ms)", f"{result.get('processing_time_ms', 0):.2f}")
        
        console.print(table)
        
        # Show errors if any
        if result.get("errors"):
            console.print("\n[red]Errors:[/red]")
            for error in result["errors"]:
                console.print(f"  - {error}")
        
        # Show warnings if any
        if result.get("warnings"):
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in result["warnings"]:
                console.print(f"  - {warning}")
        
        if result.get("rows_failed", 0) == 0:
            console.print("\n[green]✓ Load completed successfully![/green]")
        else:
            console.print(f"\n[yellow]⚠ Load completed with {result['rows_failed']} failed rows[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Load failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("schema_id")
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--source-id", help="Source identifier")
@click.pass_obj
def append(tickdb: TickDB, schema_id: str, csv_file: str, source_id: Optional[str]) -> None:
    """Append data from a CSV file."""
    
    console.print(f"[blue]Appending data from: {csv_file}[/blue]")
    console.print(f"Schema ID: {schema_id}")
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_file)
        console.print(f"Loaded {len(df)} rows from CSV")
        
        result = tickdb.append(
            df=df,
            schema_id=schema_id,
            source_id=source_id
        )
        
        # Display results
        table = Table(title="Append Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Rows Processed", str(result.get("rows_processed", 0)))
        table.add_row("Rows Failed", str(result.get("rows_failed", 0)))
        table.add_row("Files Created", str(len(result.get("files_created", []))))
        table.add_row("Processing Time (ms)", f"{result.get('processing_time_ms', 0):.2f}")
        
        console.print(table)
        
        if result.get("rows_failed", 0) == 0:
            console.print("\n[green]✓ Append completed successfully![/green]")
        else:
            console.print(f"\n[yellow]⚠ Append completed with {result['rows_failed']} failed rows[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Append failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--symbol", help="Filter by symbol")
@click.option("--ts-start", help="Start timestamp (ISO format)")
@click.option("--ts-end", help="End timestamp (ISO format)")
@click.option("--fields", help="Comma-separated list of fields to return")
@click.option("--schema-id", default="ticks_v1", help="Schema identifier")
@click.option("--limit", type=int, help="Limit number of rows")
@click.option("--output", "-o", type=click.Path(), help="Output file (CSV/Parquet)")
@click.pass_obj
def query(tickdb: TickDB, symbol: Optional[str], ts_start: Optional[str], ts_end: Optional[str], 
          fields: Optional[str], schema_id: str, limit: Optional[int], output: Optional[str]) -> None:
    """Query data from the data lake."""
    
    console.print("[blue]Querying data lake...[/blue]")
    
    # Parse fields
    field_list = None
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
    
    try:
        # Build query parameters
        query_params = {
            "schema_id": schema_id,
            "fields": field_list
        }
        
        if symbol:
            query_params["symbol"] = symbol
        if ts_start:
            query_params["ts_start"] = ts_start
        if ts_end:
            query_params["ts_end"] = ts_end
        if limit:
            query_params["limit"] = limit
        
        # Execute query
        result = tickdb.read(**query_params)
        
        console.print(f"[green]Query returned {len(result)} rows[/green]")
        
        # Display sample data
        if len(result) > 0:
            df = result.to_pandas()
            
            # Show first few rows
            console.print("\n[cyan]Sample data:[/cyan]")
            console.print(df.head().to_string())
            
            # Show summary statistics
            if len(df) > 1:
                console.print("\n[cyan]Summary statistics:[/cyan]")
                console.print(df.describe().to_string())
            
            # Save to file if requested
            if output:
                output_path = Path(output)
                if output_path.suffix.lower() == ".csv":
                    df.to_csv(output_path, index=False)
                elif output_path.suffix.lower() == ".parquet":
                    result.to_pandas().to_parquet(output_path, index=False)
                else:
                    console.print(f"[red]Unsupported output format: {output_path.suffix}[/red]")
                    return
                
                console.print(f"[green]Data saved to: {output_path}[/green]")
        else:
            console.print("[yellow]No data found matching query criteria[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Query failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--schema-id", default="ticks_v1", help="Schema identifier")
@click.pass_obj
def list_symbols(tickdb: TickDB, schema_id: str) -> None:
    """List all symbols in the data lake."""
    
    console.print(f"[blue]Listing symbols for schema: {schema_id}[/blue]")
    
    try:
        symbols = tickdb.reader.list_symbols(schema_id)
        
        if symbols:
            console.print(f"[green]Found {len(symbols)} symbols:[/green]")
            
            # Display symbols in a table
            table = Table(title="Symbols")
            table.add_column("Symbol", style="cyan")
            
            for symbol in symbols:
                table.add_row(symbol)
            
            console.print(table)
        else:
            console.print("[yellow]No symbols found[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Failed to list symbols: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option("--schema-id", default="ticks_v1", help="Schema identifier")
@click.option("--symbol", help="Filter by symbol")
@click.pass_obj
def metadata(tickdb: TickDB, schema_id: str, symbol: Optional[str]) -> None:
    """Show metadata about the data lake."""
    
    console.print(f"[blue]Metadata for schema: {schema_id}[/blue]")
    
    try:
        # Get metadata
        metadata = tickdb.reader.get_metadata(schema_id, symbol)
        date_range = tickdb.reader.get_date_range(symbol, schema_id)
        
        # Display metadata
        table = Table(title="Data Lake Metadata")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Files", str(metadata.get("total_files", 0)))
        table.add_row("Total Rows", str(metadata.get("total_rows", 0)))
        table.add_row("Date Range Start", str(date_range.get("min_ts", "N/A")))
        table.add_row("Date Range End", str(date_range.get("max_ts", "N/A")))
        table.add_row("Total Rows (Date Range)", str(date_range.get("total_rows", 0)))
        
        if metadata.get("columns"):
            table.add_row("Columns", ", ".join(metadata["columns"]))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Failed to get metadata: {e}[/red]")
        sys.exit(1)


@main.command()
@click.pass_obj
def schemas(tickdb: TickDB) -> None:
    """List available schemas."""
    
    console.print("[blue]Available schemas:[/blue]")
    
    try:
        schemas = tickdb.list_schemas()
        
        if schemas:
            table = Table(title="Schemas")
            table.add_column("Schema ID", style="cyan")
            table.add_column("Description", style="green")
            
            for schema_id in schemas:
                schema = tickdb.get_schema(schema_id)
                description = schema.get("description", "No description")
                table.add_row(schema_id, description)
            
            console.print(table)
        else:
            console.print("[yellow]No schemas found[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Failed to list schemas: {e}[/red]")
        sys.exit(1)


@main.command()
@click.pass_obj
def health(tickdb: TickDB) -> None:
    """Check system health."""
    
    console.print("[blue]Checking system health...[/blue]")
    
    try:
        health_status = tickdb.health_check()
        
        table = Table(title="Health Check Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        overall_status = health_status.get("status", "unknown")
        table.add_row("Overall", overall_status, "")
        
        for component, details in health_status.get("components", {}).items():
            if isinstance(details, dict):
                status = details.get("status", "unknown")
                info = str(details)
            else:
                status = details
                info = ""
            table.add_row(component, status, info)
        
        console.print(table)
        
        if overall_status == "healthy":
            console.print("\n[green]✓ System is healthy![/green]")
        else:
            console.print("\n[red]✗ System has issues![/red]")
            if "error" in health_status:
                console.print(f"[red]Error: {health_status['error']}[/red]")
    
    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        sys.exit(1)


@main.command()
@click.pass_obj
def metrics(tickdb: TickDB) -> None:
    """Show system metrics."""
    
    console.print("[blue]System metrics:[/blue]")
    
    try:
        metrics_data = tickdb.get_metrics()
        
        if not metrics_data:
            console.print("[yellow]No metrics available[/yellow]")
            return
        
        # Display aggregate metrics
        aggregates = metrics_data.get("aggregates", {})
        
        table = Table(title="System Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Uptime (seconds)", f"{metrics_data.get('uptime_seconds', 0):.1f}")
        table.add_row("Total Ingest Bytes", f"{aggregates.get('total_ingest_bytes', 0):,}")
        table.add_row("Total Ingest Rows", f"{aggregates.get('total_ingest_rows', 0):,}")
        table.add_row("Total Queries", str(aggregates.get("total_queries", 0)))
        table.add_row("Total Query Rows", f"{aggregates.get('total_query_rows', 0):,}")
        table.add_row("Avg Ingest Throughput (MB/s)", f"{aggregates.get('avg_ingest_throughput_mbps', 0):.2f}")
        
        console.print(table)
        
        # Show Prometheus endpoint
        if "prometheus_endpoint" in metrics_data:
            console.print(f"\n[cyan]Prometheus metrics: {metrics_data['prometheus_endpoint']}[/cyan]")
    
    except Exception as e:
        console.print(f"[red]Failed to get metrics: {e}[/red]")
        sys.exit(1)


def _load_config(config_path: str) -> TickDBConfig:
    """Load configuration from file."""
    try:
        with open(config_path, "r") as f:
            config_data = json.load(f)
        
        return TickDBConfig(**config_data)
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main() 