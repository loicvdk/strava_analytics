# CLAUDE.md - Strava Analytics Project

## Project Overview

This Kedro project analyzes Strava activity data to extract insights, create visualizations, and enhance athlete understanding of their performance. The project uses Python for backend processing with Polars for high-performance data manipulation.

## Development Environment

- **Project Directory**: `strava-analytics/`
- **Virtual Environment**: `strava-env`
- **Primary Framework**: Kedro (Data Pipeline)
- **Data Processing**: Polars
- **Testing Framework**: pytest
- **Documentation Style**: NumPy docstrings

## Architecture & Design Patterns

### Data Pipeline Structure
```
strava-analytics/
├── conf/                   # Configuration files
│   ├── base/
│   ├── local/
│   └── parameters/
├── data/                   # Data storage (gitignored)
│   ├── 01_raw/
│   ├── 02_intermediate/
│   ├── 03_primary/
│   ├── 04_feature/
│   ├── 05_model_input/
│   ├── 06_models/
│   ├── 07_model_output/
│   └── 08_reporting/
├── src/strava_analytics/
│   ├── pipelines/
│   │   ├── data_ingestion/
│   │   ├── data_processing/
│   │   ├── feature_engineering/
│   │   └── analytics/
│   └── utils/
├── tests/
└── notebooks/              # Jupyter notebooks for exploration and basic visualisation
```

## Available Pipelines

The project includes three main pipelines for different data collection scenarios:

### 1. BAU Pipeline (`bau`) - **DEFAULT & MOST COMMON**
```bash
# Regular incremental data collection (recommended for daily/weekly use)
kedro run --pipeline=bau
# OR simply (bau is now the default)
kedro run
```
- **Purpose**: Business-as-usual incremental data collection
- **Behavior**: Only fetches NEW activities since the last run
- **Use case**: Regular updates to keep data current
- **Smart filtering**: Automatically detects latest saved activity date

### 2. Day0 Pipeline (`day0`)
```bash
# Initial historical data collection (first time setup)
kedro run --pipeline=day0
```
- **Purpose**: Bootstrap initial historical data collection
- **Behavior**: Fetches all available activities (respects rate limits)
- **Use case**: First-time setup or complete data rebuild
- **Note**: Use only once or when rebuilding from scratch

### 3. Streams Pipeline (`streams`)
```bash
# Enrich activities with detailed time-series data
kedro run --pipeline=streams
```
- **Purpose**: Add streams data (GPS, heart rate, power, etc.) to activities
- **Behavior**: Only processes activities without existing streams data
- **Features**:
  - Incremental processing
  - Crash recovery with intermediate saves
  - Smart rate limiting
- **See**: `STREAMS_GUIDE.md` for detailed usage

### Pipeline Selection Guide
- **First time setup**: `day0` → `streams`
- **Regular updates**: `bau` → `streams` (as needed)
- **Just activity data**: `bau`
- **Just streams data**: `streams`

## Coding Standards & Best Practices

### 1. Code Quality
- **Production-grade code**: All code must be robust, error-handled, and maintainable
- **Type hints**: Use throughout for better IDE support and documentation
- **Error handling**: Comprehensive exception handling with meaningful error messages
- **Logging**: Structured logging using Python's `logging` module

### 2. Documentation Standards
```python
def process_activity_data(
    activities_df: pl.DataFrame,
    athlete_id: str,
    date_range: tuple[str, str] | None = None
) -> pl.DataFrame:
    """Process raw Strava activity data for analysis.
    
    Parameters
    ----------
    activities_df : pl.DataFrame
        Raw activities dataframe from Strava API
    athlete_id : str
        Unique identifier for the athlete
    date_range : tuple[str, str] | None, optional
        Start and end dates in 'YYYY-MM-DD' format, by default None
        
    Returns
    -------
    pl.DataFrame
        Processed activities with calculated metrics
        
    Raises
    ------
    ValueError
        If date_range format is invalid
    KeyError
        If required columns are missing from activities_df
        
    Examples
    --------
    >>> activities = pl.DataFrame({...})
    >>> processed = process_activity_data(activities, "12345")
    """
```

### 3. Data Handling with Polars
- **Lazy evaluation**: Use `pl.LazyFrame` for large datasets when possible
- **Memory efficiency**: Leverage Polars' columnar format and optimizations
- **Schema validation**: Explicit schema definitions for data integrity
- **Performance**: Utilize Polars' native operations over pandas-style operations

```python
# Example Polars usage pattern
def calculate_training_load(activities: pl.LazyFrame) -> pl.LazyFrame:
    """Calculate training load metrics using Polars lazy evaluation."""
    return (
        activities
        .with_columns([
            pl.col("moving_time").dt.total_seconds().alias("duration_seconds"),
            pl.col("average_heartrate").fill_null(0).alias("hr_avg"),
        ])
        .with_columns([
            (pl.col("duration_seconds") * pl.col("hr_avg") / 3600)
            .alias("training_load")
        ])
        .filter(pl.col("training_load") > 0)
    )
```

### 4. Testing Strategy
- **Comprehensive coverage**: Aim for >90% test coverage
- **Unit tests**: Test individual functions and methods
- **Integration tests**: Test pipeline components together
- **Data validation tests**: Verify data quality and schema compliance

```python
# Example test structure
import pytest
import polars as pl
from strava_analytics.pipelines.data_processing.nodes import process_activity_data

class TestDataProcessing:
    """Test suite for data processing functions."""
    
    @pytest.fixture
    def sample_activities(self) -> pl.DataFrame:
        """Create sample activity data for testing."""
        return pl.DataFrame({
            "id": [1, 2, 3],
            "name": ["Morning Run", "Evening Ride", "Recovery Run"],
            "type": ["Run", "Ride", "Run"],
            "distance": [5000.0, 15000.0, 3000.0],
            "moving_time": [1800, 3600, 1200],
        })
    
    def test_process_activity_data_basic(self, sample_activities):
        """Test basic activity data processing."""
        result = process_activity_data(sample_activities, "athlete_123")
        
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 3
        assert "pace" in result.columns
```

## Strava API Integration

### 1. Authentication & Rate Limiting
- **OAuth2 flow**: Implement secure token management
- **Rate limiting**: Respect Strava's API limits (100 requests every 15 minutes, 1,000 daily)
- **Token refresh**: Automatic token renewal handling
- **Error handling**: Graceful degradation for API failures

### 2. Data Extraction Patterns
```python
class StravaAPIClient:
    """Production-grade Strava API client with rate limiting and error handling."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.rate_limiter = RateLimiter()
        self.logger = logging.getLogger(__name__)
    
    async def get_activities(
        self, 
        after: datetime | None = None,
        per_page: int = 30
    ) -> list[dict]:
        """Fetch activities with rate limiting and pagination."""
        # Implementation with proper error handling
```

## Data Pipeline Components

### 1. Data Ingestion Pipeline
- **Raw data extraction**: Strava API calls with pagination
- **Data validation**: Schema validation and data quality checks  
- **Storage**: Efficient storage in Parquet format
- **Incremental loading**: Only fetch new/updated activities

### 2. Data Processing Pipeline
- **Data cleaning**: Handle missing values, outliers, and data inconsistencies
- **Standardization**: Normalize units and formats
- **Enrichment**: Add calculated fields (pace, power zones, training load)
- **Aggregation**: Time-based and activity-type aggregations

### 3. Feature Engineering Pipeline
- **Performance metrics**: VO2 max estimation, fitness trends, fatigue indicators
- **Activity patterns**: Weekly/monthly patterns, activity clustering
- **Comparative metrics**: Personal records, segment performance
- **Advanced analytics**: Training peaks, recovery analysis

### 4. Analytics & Visualization Pipeline
- **Statistical analysis**: Correlation analysis, trend detection
- **Visualizations**: Interactive charts using Plotly/Bokeh
- **Reports**: Automated insight generation
- **Export**: Data export for external tools

## Configuration Management

### Parameters Structure
```yaml
# conf/base/parameters/data_processing.yml
data_processing:
  activity_types:
    - "Run"
    - "Ride" 
    - "Swim"
  
  filters:
    min_distance: 1000  # meters
    min_duration: 300   # seconds
    
  calculations:
    pace_smoothing_window: 30
    power_zones: [0, 0.55, 0.75, 0.9, 1.05, 1.2, 1.5]
```

### Environment Configuration
```yaml
# conf/local/credentials.yml (not committed)
strava_api:
  client_id: ${STRAVA_CLIENT_ID}
  client_secret: ${STRAVA_CLIENT_SECRET}
  refresh_token: ${STRAVA_REFRESH_TOKEN}

database:
  connection_string: ${DATABASE_URL}
```

## Performance Optimization

### 1. Data Processing Optimizations
- **Lazy evaluation**: Use Polars LazyFrames for memory efficiency
- **Columnar operations**: Leverage vectorized operations
- **Parallel processing**: Use Polars' built-in parallelization
- **Memory management**: Explicit memory cleanup for large datasets

### 2. API Optimization
- **Batch processing**: Group API calls efficiently
- **Caching**: Cache frequently accessed data
- **Async operations**: Non-blocking API calls
- **Connection pooling**: Reuse HTTP connections

## Deployment & Production Considerations

### 1. Environment Setup
```bash
# Virtual environment setup
python -m venv strava-env
source strava-env/bin/activate  # On Windows: strava-env\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration Management
- **Environment variables**: Sensitive data via environment variables
- **Configuration validation**: Validate all configuration on startup
- **Secrets management**: Use proper secrets management in production
- **Feature flags**: Enable/disable features via configuration

### 3. Monitoring & Logging
- **Structured logging**: JSON-formatted logs for production
- **Metrics collection**: Track pipeline performance and data quality
- **Error tracking**: Comprehensive error tracking and alerting
- **Health checks**: Regular pipeline health monitoring

## AI-Assisted Development Guidelines

### 1. Code Generation Prompts
When requesting code generation, always specify:
- Use Polars for data manipulation
- Include NumPy-style docstrings
- Add comprehensive error handling
- Include type hints
- Follow the established project structure

### 2. Testing Assistance
- Generate pytest test cases for all new functions
- Include edge cases and error conditions
- Create fixtures for common test data
- Validate data quality in tests

### 3. Documentation Updates
- Update this CLAUDE.md file when architecture changes
- Maintain inline documentation
- Update README.md for user-facing changes
- Document API changes and breaking changes

## Common Patterns & Utilities

### 1. Data Validation
```python
def validate_activity_schema(df: pl.DataFrame) -> None:
    """Validate that DataFrame has required activity columns."""
    required_columns = ["id", "name", "type", "distance", "moving_time"]
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
```

### 2. Error Handling
```python
class StravaAnalyticsError(Exception):
    """Base exception for Strava analytics errors."""
    pass

class APIError(StravaAnalyticsError):
    """Raised when Strava API calls fail."""
    pass

class DataValidationError(StravaAnalyticsError):
    """Raised when data validation fails."""
    pass
```

### 3. Configuration Access
```python
from kedro.config import ConfigLoader

def load_config() -> dict:
    """Load and validate configuration."""
    config_loader = ConfigLoader(conf_source="conf")
    return config_loader.get("parameters*")
```

## Development Workflow

### 1. Feature Development
1. Create feature branch from main
2. Implement feature with tests
3. Run full test suite
4. Update documentation
5. Create pull request with detailed description

### 2. Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/strava_analytics --cov-report=html

# Run specific test category
pytest -m integration

# Run data quality tests
pytest tests/test_data_quality.py
```

### 3. Pipeline Execution
```bash
# Run full pipeline
kedro run

# Run specific pipeline
kedro run --pipeline=data_processing

# Run with specific parameters
kedro run --params="date_range=['2024-01-01','2024-12-31']"
```

---

## Notes for AI Assistance

This project prioritizes:
- **Data quality and reliability**
- **Performance and scalability** 
- **Maintainable, production-grade code**
- **Comprehensive testing and documentation**
- **Efficient use of modern Python data tools**

Always consider these priorities when generating code or providing suggestions for this project.