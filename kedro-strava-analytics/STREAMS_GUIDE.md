# Strava Streams Enrichment Guide

## Overview

The Strava Streams enrichment functionality adds detailed time-series data to your activity dataset. This includes granular data like GPS coordinates, heart rate, power, cadence, and more recorded throughout each activity.

## What are Streams?

Streams provide time-series data for various metrics during an activity:

- **time**: Time elapsed (seconds)
- **distance**: Cumulative distance (meters)
- **latlng**: GPS coordinates (latitude/longitude pairs)
- **altitude**: Elevation (meters)
- **velocity_smooth**: Smoothed speed (m/s)
- **heartrate**: Heart rate (bpm)
- **cadence**: Pedaling/stride rate (rpm/spm)
- **watts**: Power output (watts)
- **temp**: Temperature (°C)
- **moving**: Whether athlete was moving (boolean)
- **grade_smooth**: Smoothed gradient (%)

## Data Storage Architecture

### Files Created
- `data/02_intermediate/activity_streams.parquet` - Main streams data (compressed)
- `data/02_intermediate/stream_metadata.csv` - Metadata about which activities have streams

### Data Format
The streams data is stored in a normalized format:

```
activity_id | stream_type | time_index | value     | series_type
12345       | heartrate   | 0          | 145.0     | time
12345       | heartrate   | 1          | 147.0     | time
12345       | distance    | 0          | 0.0       | distance
12345       | distance    | 1          | 10.2      | distance
```

## Usage

### 1. Basic Streams Enrichment

After collecting activities with `day0` or `bau` pipelines:

```bash
# Enrich ALL activities with streams data (processes all missing activities in one run)
kedro run --pipeline=streams

# Increase delay between batches for extra safety
kedro run --pipeline=streams --params="streams_enrichment.rate_limit_delay=2.0"

# Reduce concurrent requests for slower processing
kedro run --pipeline=streams --params="streams_enrichment.max_concurrent_requests=5"
```

### 2. Incremental Enrichment

The streams pipeline automatically processes ALL activities that don't already have streams data:

```bash
# First run: processes ALL activities without streams data
kedro run --pipeline=streams

# Second run: only processes newly added activities (existing ones are skipped)
kedro run --pipeline=streams
```

### 3. Pipeline Parameters

Configure in `conf/base/parameters.yml`:

```yaml
streams_enrichment:
  rate_limit_delay: 1.0          # Seconds between batch requests
  max_concurrent_requests: 10    # Concurrent API requests per batch
```

## Rate Limiting Strategy

### Strava API Limits
- **100 requests per 15 minutes**
- **1,000 requests per day**

### Our Implementation
- **Smart batching**: Processes 10 concurrent requests per batch (well within limits)
- **Batch delays**: 1-second delay between batches (not individual requests)
- **Progress tracking**: Real-time progress with detailed logging
- **Automatic processing**: All missing activities processed in one run
- **Incremental**: Only fetches new activities on subsequent runs

### Recommended Usage Pattern

**Initial Data Collection:**
```bash
# Process ALL historical activities in one run
kedro run --pipeline=streams
```

**Ongoing: New Activities**
```bash
# Weekly enrichment for new activities (only processes newly added activities)
kedro run --pipeline=streams
```

## Data Analysis Examples

### Loading Streams Data

```python
import polars as pl
import pandas as pd

# Load streams data
streams = pl.read_parquet('data/02_intermediate/activity_streams.parquet')
metadata = pl.read_csv('data/02_intermediate/stream_metadata.csv')

# Check what's available
print("Available stream types:")
print(streams.select('stream_type').unique().sort('stream_type'))

print("Activities with streams:")
print(metadata.select(['activity_id', 'stream_types', 'record_count']))
```

### Analyzing Heart Rate Data

```python
# Get heart rate data for a specific activity
activity_hr = streams.filter(
    (pl.col('activity_id') == 12345) &
    (pl.col('stream_type') == 'heartrate')
).sort('time_index')

# Plot heart rate over time
import plotly.express as px
hr_df = activity_hr.to_pandas()
fig = px.line(hr_df, x='time_index', y='value', title='Heart Rate Over Time')
fig.show()
```

### GPS Trajectory Analysis

```python
# Get GPS coordinates for an activity
activity_coords = streams.filter(
    (pl.col('activity_id') == 12345) &
    (pl.col('stream_type').is_in(['latitude', 'longitude']))
).pivot(values='value', index='time_index', columns='stream_type')

# Plot on map
import plotly.graph_objects as go
fig = go.Figure(go.Scattermapbox(
    lat=activity_coords['latitude'],
    lon=activity_coords['longitude'],
    mode='lines',
    line=dict(width=3, color='red')
))
fig.update_layout(mapbox_style="open-street-map")
fig.show()
```

### Power Analysis

```python
# Get power data for activities
power_data = streams.filter(pl.col('stream_type') == 'watts')

# Calculate average power per activity
avg_power = (
    power_data
    .group_by('activity_id')
    .agg(pl.col('value').mean().alias('avg_watts'))
)
```

## Troubleshooting

### Common Issues

**1. "No new activities found"**
- All activities already have streams data
- Check `stream_metadata.csv` to see processed activities

**2. "Rate Limit Exceeded"**
- Reduce `max_activities_to_process`
- Increase `rate_limit_delay`
- Wait 15 minutes for rate limit reset

**3. "Authorization Error"**
- Re-run OAuth: `python scripts/setup_strava_auth.py`
- Check credentials in `conf/local/credentials.yml`

**4. "Some activities have no streams"**
- Normal - not all activities have streams data
- Virtual activities often lack GPS/power data
- Check activity type and device used

### Monitoring Progress

```bash
# Check how many activities have streams
wc -l data/02_intermediate/stream_metadata.csv

# Check streams file size
ls -lh data/02_intermediate/activity_streams.parquet

# View sample of streams data
head data/02_intermediate/stream_metadata.csv
```

## Performance Notes

### Memory Usage
- Streams data can be large (MB per activity)
- Parquet format provides ~70% compression
- Processing in chunks prevents memory issues

### Storage Estimates
- **Basic activity**: ~1MB streams data
- **GPS activity with power**: ~3-5MB streams data
- **1000 activities**: ~1-3GB total storage

### Processing Time
- ~2-3 seconds per activity (including API delays)
- 50 activities: ~2-3 minutes total
- 500 activities: ~20-30 minutes total

## Advanced Usage

### Custom Stream Selection

Modify `streams_enrichment.py` to fetch only specific streams:

```python
# In get_activity_streams, modify stream_types
stream_types = ["heartrate", "latlng", "altitude"]  # Only essential data
```

### One-Time Processing

```bash
#!/bin/bash
# Process ALL activities in one go (no manual batching needed)
echo "Processing ALL activities with streams..."
kedro run --pipeline=streams
echo "Streams enrichment completed!"
```

### Integration with Analysis Pipeline

Create a combined pipeline:

```bash
# Collect activities then enrich with streams
kedro run --pipeline=bau
kedro run --pipeline=streams
```

## Best Practices

1. **One Command**: Simply run `kedro run --pipeline=streams` - handles everything automatically
2. **Smart Rate Limiting**: Built-in batching respects API limits
3. **Monitor Progress**: Watch real-time progress logs during processing
4. **Regular Updates**: Run weekly for new activities
5. **Backup Data**: Streams data is valuable and time-consuming to recreate

This enriched data enables advanced analytics like power zone analysis, route optimization, pacing strategies, and detailed performance tracking over time.