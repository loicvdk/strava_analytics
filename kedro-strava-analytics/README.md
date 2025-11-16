# Kedro Strava Analytics Pipeline

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

Production-grade data pipeline for collecting and processing Strava activity data with intelligent rate limiting and incremental updates.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Setup Strava credentials (one-time)
python scripts/setup_strava_auth.py

# Collect all historical data (first time)
kedro run --pipeline=day0

# Regular incremental updates (most common)
kedro run

# Add detailed streams data (GPS, heart rate, power)
kedro run --pipeline=streams
```

## ✨ Key Features

- **🔄 Incremental Updates**: Only fetches NEW activities since last run
- **⚡ Smart Rate Limiting**: Respects API limits with intelligent batching
- **💾 Crash Recovery**: Saves intermediate results to prevent data loss
- **📊 Rich Data**: Collects both activities and detailed streams (GPS, sensors)
- **🛡️ Production Ready**: Comprehensive error handling and logging
- **⚙️ Configurable**: Flexible parameters for different use cases

## Strava API Setup

Before running the pipeline, you need to set up Strava API credentials:

1. Create a Strava application at https://www.strava.com/settings/api
2. Note down your `Client ID` and `Client Secret`
3. Get your refresh token using OAuth2 flow
4. Set environment variables:

```bash
export STRAVA_CLIENT_ID="your_client_id"
export STRAVA_CLIENT_SECRET="your_client_secret"
export STRAVA_REFRESH_TOKEN="your_refresh_token"
```

The credentials are already configured in `conf/local/credentials.yml` to use these environment variables.

## Rules and guidelines

In order to get the best out of the template:

* Don't remove any lines from the `.gitignore` file we provide
* Make sure your results can be reproduced by following a data engineering convention
* Don't commit data to your repository
* Don't commit any credentials or your local configuration to your repository. Keep all your credentials and local configuration in `conf/local/`

## How to install dependencies

Declare any dependencies in `requirements.txt` for `pip` installation.

To install them, run:

```
pip install -r requirements.txt
```

## How to run your Kedro pipeline

### Run the complete pipeline
```bash
kedro run
```

### Running Pipelines
```bash
# Regular incremental updates (most common)
kedro run

# OR explicitly use the BAU pipeline
kedro run --pipeline=bau

# First-time historical data collection
kedro run --pipeline=day0

# Add detailed streams data (GPS, heart rate, power, etc.)
kedro run --pipeline=streams
```

### Available Pipelines

- **`bau`** (default): Regular incremental updates - only fetches NEW activities
- **`day0`**: First-time historical data collection - fetches all activities
- **`streams`**: Adds detailed time-series data to activities (see `STREAMS_GUIDE.md`)

### Pipeline Behavior

- **Incremental**: Only collects new activities since the last run
- **Rate Limiting**: Smart rate limiting with progress tracking
- **Data Storage**: Activities saved to `data/01_raw/strava_activities.csv`
- **Streams Storage**: Time-series data saved to `data/02_intermediate/activity_streams.parquet`

## How to test your Kedro project

Have a look at the file `tests/test_run.py` for instructions on how to write your tests. You can run your tests as follows:

```
pytest
```

You can configure the coverage threshold in your project's `pyproject.toml` file under the `[tool.coverage.report]` section.


## Project dependencies

To see and update the dependency requirements for your project use `requirements.txt`. You can install the project requirements with `pip install -r requirements.txt`.

[Further information about project dependencies](https://docs.kedro.org/en/stable/kedro_project_setup/dependencies.html#project-specific-dependencies)

## How to work with Kedro and notebooks

> Note: Using `kedro jupyter` or `kedro ipython` to run your notebook provides these variables in scope: `context`, 'session', `catalog`, and `pipelines`.
>
> Jupyter, JupyterLab, and IPython are already included in the project requirements by default, so once you have run `pip install -r requirements.txt` you will not need to take any extra steps before you use them.

### Jupyter
To use Jupyter notebooks in your Kedro project, you need to install Jupyter:

```
pip install jupyter
```

After installing Jupyter, you can start a local notebook server:

```
kedro jupyter notebook
```

### JupyterLab
To use JupyterLab, you need to install it:

```
pip install jupyterlab
```

You can also start JupyterLab:

```
kedro jupyter lab
```

### IPython
And if you want to run an IPython session:

```
kedro ipython
```

### How to ignore notebook output cells in `git`
To automatically strip out all output cell contents before committing to `git`, you can use tools like [`nbstripout`](https://github.com/kynan/nbstripout). For example, you can add a hook in `.git/config` with `nbstripout --install`. This will run `nbstripout` before anything is committed to `git`.

> *Note:* Your output cells will be retained locally.

## Package your Kedro project

[Further information about building project documentation and packaging your project](https://docs.kedro.org/en/stable/tutorial/package_a_project.html)
