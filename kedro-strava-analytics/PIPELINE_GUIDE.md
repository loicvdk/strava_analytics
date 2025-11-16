# Strava Data Pipeline Guide

## Overview

The Strava data ingestion system now includes two specialized pipelines to handle different data collection scenarios:

1. **Day 0 Pipeline** (`day0`) - Initial full data collection
2. **BAU Pipeline** (`bau`) - Business as usual incremental updates

## Pipeline Architecture

### 🚀 Day 0 Pipeline

**Purpose**: Bootstrap your dataset with all available activities

**Features**:
- Fetches activities from newest to oldest
- No dependency on existing data
- Uses standardized schema for consistent data structure
- Ideal for first-time setup

**Usage**:
```bash
# Fetch up to 1000 activities (default)
kedro run --pipeline=day0

# Fetch specific number of activities
kedro run --pipeline=day0 --params="max_activities=500"

# Small test run
kedro run --pipeline=day0 --params="max_activities=10"
```

### 🔄 BAU Pipeline

**Purpose**: Keep your dataset up-to-date with new activities

**Features**:
- Fetches only new activities since last update
- Detects most recent activity in existing data
- Automatically merges with existing dataset
- Optimized for regular scheduled runs

**Usage**:
```bash
# Fetch up to 100 new activities (default)
kedro run --pipeline=bau

# Fetch specific number of new activities
kedro run --pipeline=bau --params="max_activities=50"

# Check for just a few new activities
kedro run --pipeline=bau --params="max_activities=5"
```

## Data Schema

Both pipelines use a **standardized schema** that ensures consistent data structure:

### Key Features:
- **67 standardized columns** covering all Strava activity attributes
- **Automatic type conversion** (String, Int64, Float64, Boolean)
- **Null handling** for missing fields
- **Complex field normalization** (converts lists/objects to strings)

### Schema Benefits:
- ✅ **No more schema conflicts** between API calls
- ✅ **Consistent data types** across all runs
- ✅ **Backwards compatibility** with existing data
- ✅ **Handles missing fields** gracefully

## Recommended Workflow

### Initial Setup (Day 0)
```bash
# Step 1: Run Day 0 to bootstrap your dataset
kedro run --pipeline=day0 --params="max_activities=1000"

# Step 2: Verify the data
head -5 data/01_raw/strava_activities.csv
wc -l data/01_raw/strava_activities.csv
```

### Regular Updates (BAU)
```bash
# Daily/weekly runs to fetch new activities
kedro run --pipeline=bau --params="max_activities=50"

# Or set up as scheduled job
crontab -e
# Add: 0 6 * * * cd /path/to/project && kedro run --pipeline=bau
```

## Pipeline Comparison

| Feature | Day 0 | BAU |
|---------|-------|-----|
| **Purpose** | Initial bootstrap | Incremental updates |
| **Data Strategy** | Fetch all available | Fetch newer than existing |
| **Dependency** | None | Requires existing data |
| **Direction** | Newest to oldest | Newest only |
| **Typical Size** | 500-2000 activities | 5-50 activities |
| **Frequency** | Once | Daily/weekly |

## Error Handling & Recovery

### If Day 0 Fails:
```bash
# Simply re-run - it will overwrite
kedro run --pipeline=day0 --params="max_activities=200"
```

### If BAU Fails:
```bash
# Check existing data first
head data/01_raw/strava_activities.csv

# Re-run BAU
kedro run --pipeline=bau --params="max_activities=10"
```

### Schema Issues:
The standardized schema automatically handles:
- Missing columns (filled with nulls)
- Type mismatches (converted or nulled)
- Complex data structures (converted to strings)

## Output Data

### File Location:
```
data/01_raw/strava_activities.csv
```

### Schema:
- **67 columns** with standardized types
- **Sorted by date** (oldest first)
- **Deduplicated** by activity ID
- **CSV format** for maximum compatibility

### Key Columns:
- `id` - Unique activity identifier
- `name` - Activity name
- `type` - Activity type (Run, Ride, Hike, etc.)
- `start_date` - ISO format timestamp
- `distance` - Distance in meters
- `moving_time` - Moving time in seconds
- `average_speed` - Speed in m/s
- `total_elevation_gain` - Elevation in meters

## Advanced Usage

### Check Available Pipelines:
```bash
kedro pipeline list
```

### Run Specific Nodes:
```bash
# Just load credentials
kedro run --pipeline=day0 --nodes="day0.load_strava_credentials_node"

# Just fetch activities (after credentials loaded)
kedro run --pipeline=bau --nodes="bau.collect_strava_activities_bau_node"
```

### Debug Mode:
```bash
# Add logging to see detailed progress
kedro run --pipeline=day0 --params="max_activities=5" --log-level=DEBUG
```

## Best Practices

1. **Start Small**: Use `max_activities=10` for testing
2. **Day 0 First**: Always run Day 0 before BAU
3. **Regular BAU**: Schedule BAU runs to keep data current
4. **Monitor Logs**: Watch for rate limiting and errors
5. **Backup Data**: Keep copies of your CSV files

## Troubleshooting

### Common Issues:

**"No new activities found"**
- Normal for BAU if you're up-to-date
- Check if you have recent activities on Strava

**"Authorization Error"**
- Run the OAuth setup script: `python scripts/setup_strava_auth.py`
- Check credentials in `conf/local/credentials.yml`

**"Rate Limit Exceeded"**
- Wait 15 minutes for rate limit reset
- Reduce `max_activities` parameter

**"Schema Warnings"**
- These are usually harmless
- The system handles type conversions automatically

This pipeline architecture provides a robust, scalable solution for Strava data collection with clear separation of concerns between initial setup and ongoing maintenance.