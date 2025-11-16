# Strava Analytics - Python Frontend

A fast, interactive Python frontend for visualizing Strava running data using Reflex.

## 🚀 Features

### 📊 High-Level Statistics
- **Distance tracking**: Kilometers run this week and year-to-date
- **Pace monitoring**: Average pace for current week in min/km
- **Real-time updates**: Automatically loads from Kedro pipeline data

### 📈 Interactive Charts
- **Weekly Distance**: Line chart showing running distance over time
- **Average Pace**: Bar chart displaying weekly pace trends
- **Time Spent**: Weekly time investment in running
- **Time Period Selection**: Switch between 90 days, 6 months, YTD, and all-time views

### 📋 Activities List
- **Recent activities**: Sortable, searchable table of latest runs
- **Key metrics**: Name, distance, time, and average pace for each activity
- **Pagination**: Easy navigation through activity history

## 🛠️ Setup & Installation

### Prerequisites
Ensure you have run the Kedro data pipeline to generate the required data files:
```bash
cd ../kedro-strava-analytics
kedro run  # or kedro run --pipeline=bau for incremental updates
```

### Install Dependencies
```bash
cd py-visualisation
pip install -r requirements.txt
```

### Run the Dashboard
```bash
python app.py
```

The dashboard will be available at: http://localhost:3001

## 🏗️ Architecture

### Data Flow
```
Kedro Pipeline Outputs → Data Loader → Reflex Components → Web Dashboard
```

1. **Data Source**: Reads from `../kedro-strava-analytics/data/01_raw/strava_activities.csv`
2. **Processing**: `StravaDataLoader` filters running activities and calculates metrics
3. **State Management**: Reflex `State` class manages data and UI state
4. **Visualization**: Plotly charts and Radix UI components render the dashboard

### File Structure
```
py-visualisation/
├── app.py                      # Application entry point
├── rxconfig.py                 # Reflex configuration
├── data_loader.py              # Data processing utilities
├── strava_dashboard/
│   ├── __init__.py
│   └── strava_dashboard.py     # Main dashboard components
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

### Key Components

**StravaDataLoader** (`data_loader.py`):
- Loads activities from CSV with error handling
- Filters running activities only
- Calculates weekly statistics and pace metrics
- Provides data aggregation for charts

**State Management** (`strava_dashboard.py`):
- Reactive state with automatic UI updates
- Data loading with loading states
- Period selection for chart filtering
- Chart generation with Plotly

**UI Components**:
- `stat_card()`: Metric display cards
- `period_selector()`: Time range buttons
- `activities_table()`: Sortable data table
- `dashboard()`: Main layout composition

## 🎨 Design System

### Theme
- **Clean white background** with subtle gradients
- **Modern typography** using Inter font family
- **Consistent spacing** with Reflex's design tokens
- **Subtle borders** and shadows for visual hierarchy

### Color Palette
- **Primary Blue**: #2563eb (charts, buttons)
- **Success Green**: #059669 (pace charts)
- **Danger Red**: #dc2626 (time charts)
- **Gray Scale**: #1f2937, #374151, #6b7280 (text)

### Interactive Elements
- **Responsive design** for desktop and mobile
- **Hover states** on buttons and cards
- **Loading states** with spinners
- **Real-time data updates** without page refresh

## 🔧 Configuration

### Port Configuration
Default port is `3001`. To change:
```python
# rxconfig.py
config = rx.Config(
    app_name="strava_dashboard",
    port=3002,  # Change port here
)
```

### Data Path Configuration
Default reads from `../kedro-strava-analytics/data/`. To customize:
```python
# In your code
loader = StravaDataLoader(data_path="/custom/path/to/data")
```

## 🚦 Development

### Running in Development Mode
```bash
reflex run --env dev
```

### Building for Production
```bash
reflex export
```

### Adding New Features
1. **New metrics**: Add calculations to `StravaDataLoader`
2. **New charts**: Create chart functions in `State` class
3. **New components**: Add to `strava_dashboard.py`
4. **New pages**: Use `app.add_page()` in main file

## 📊 Data Requirements

The dashboard expects the following data structure from Kedro pipeline:

**Activities CSV columns**:
- `sport_type`: Must include "Run" activities
- `start_date`: Activity start time
- `distance`: Distance in meters
- `moving_time`: Duration in seconds
- `name`: Activity name

**Optional enhancements**:
- Add streams data support for detailed GPS/sensor visualizations
- Implement caching for faster data loading
- Add export functionality for charts and data

## 🤝 Integration with Kedro

This frontend automatically integrates with the Kedro data pipeline:

1. **Automatic data loading**: Reads latest pipeline outputs
2. **Incremental updates**: Works with BAU pipeline for new activities
3. **Error handling**: Graceful fallbacks when data is unavailable
4. **Performance**: Uses Polars for efficient data processing

Perfect for rapid prototyping and interactive data exploration!

---

**Built with:** Reflex, Plotly, Polars, Python 3.9+