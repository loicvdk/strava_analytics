# Dynamic running zones identification 

Your are a senior software engineer/data scientist focusing on performance science. You goal is to keep track of the average pace per running zone as well as the time spent in those. To make this happen the first step is identify correctly the zones. 
This document explains the methodology for identifying training zones in running activities using heart rate data with lag compensation based on pace changes.

## Setup 

You will work on a setup with 4 zones: 
1. easy 
2. tempo
3. threshold 
4. above threshold 

You will mainly look at heart rate to identify the zones and the rolling page changes. 

## The Problem: Heart Rate Lag
Heart rate (HR) is a lagging indicator of exercise intensity. When a runner increases their pace:

Pace increases immediately (within 1-2 seconds)
Heart rate responds slowly (30-60 seconds later)

This lag creates a problem: if we only use HR to classify zones, we miss the first 30-60 seconds of each hard effort.
Example Scenario
Time:     0s    15s    30s    45s    60s    75s
Pace:     5:00  4:15   4:15   4:15   4:15   5:30
HR:       145   148    158    168    175    172
Without lag compensation:

0-45s: "Zone 2" (HR < 155)
45-60s: "Threshold" (HR 155-183)
60-75s: "Threshold" (HR still elevated)

**Problem:** The runner was actually at threshold pace from 15s onwards and stopped at 75s, but HR-only classification misses 30 seconds of the effort! However, you cannot only focus on paces as pace is dependant on a lot of factors. 

## Solution: Multi-Signal Zone Classification

We use three signals to accurately identify training zones:
1. Heart Rate (Primary Signal)
Provides the ground truth of physiological stress, but with lag.
2. Pace (Leading Signal)
Responds immediately to effort changes, used to anticipate zone transitions.
3. Pace Change Rate (Transition Detector)
Identifies when efforts are starting or ending.

### Zone Classification Algorithm - Summary
Core Concept
Heart rate tells us the true physiological stress, but it responds 30-60 seconds late. Pace changes immediately when effort changes. By combining both signals, we can accurately identify when training zones actually begin and end, not just when heart rate finally catches up.

#### The Five Steps
1. Clean the Noisy Data
Raw GPS and heart rate data jumps around every second due to measurement error. We smooth both signals to see the real patterns underneath the noise. Think of it like taking a moving average - instead of reacting to every spike, we look at the general trend over 15-20 seconds.
Purpose: Separate real effort changes from random fluctuations

2. Initial Heart Rate Classification
We start by using heart rate alone to classify each moment:

Below 155 bpm = Recovery zone
Between 155-183 bpm = Threshold zone
Above 183 bpm = Above Threshold zone

This gives us a baseline, but it's wrong at every transition because of the lag problem.
**Purpose:** Establish ground truth based on physiological stress

3. Fix the Beginning of Hard Efforts (Forward Extension)
When heart rate crosses into the threshold zone, we know the runner has been working hard. But when did the hard effort actually start?
We look backwards up to 45 seconds and search for when pace started increasing - getting faster. That's when the effort truly began, even though heart rate didn't respond yet.
Example: Runner starts interval at 10:00. Heart rate enters threshold at 10:45. But pace spiked at 10:15. We extend the threshold zone back to 10:15 to capture those first 30 seconds.
**Purpose:** Catch the early part of efforts that heart rate missed

4. Fix the End of Hard Efforts (Backward Truncation)
When heart rate drops back to recovery, we know the runner has eased off. But when did they actually slow down?
We look backwards about 20 seconds to find when pace started decreasing - getting slower. That's when the effort ended, even though heart rate stayed elevated for a bit longer during the cooldown.
Example: Runner finishes interval at 15:00. Heart rate drops to recovery at 15:30. But pace slowed at 15:05. We end the threshold zone at 15:05, not 15:30.
**Purpose:** Remove the cooldown period where heart rate is still high but effort has ended

5. Remove Brief Blips
After adjustment, we filter out any zones shorter than meaningful training durations:

Threshold efforts must last at least 2 minutes
Recovery segments must last at least 3 minutes

Brief spikes that don't meet these minimums get merged into the surrounding zone. This prevents the striped pattern you saw in your graph.
**Purpose:** Only flag sustained efforts that create training adaptations

#### Why This Works
The Problem We're Solving:
A runner starts a hard interval. Their legs respond instantly - pace jumps from 5:00/km to 4:15/km within seconds. But their heart rate takes 45 seconds to climb from 145 to 175 bpm. Using heart rate alone, we'd miss the first 45 seconds of hard work.
**The Solution:**
We watch for pace changes as the early warning signal. When pace increases significantly, we know a hard effort is starting. When heart rate eventually confirms this 45 seconds later, we extend the zone classification backwards to when the pace actually changed.
**The Result:**
Zone boundaries align with when effort actually changed, not when heart rate caught up.

#### Key Principles
##### Multi-Signal Approach
No single metric is perfect. Heart rate is slow but accurate. Pace is fast but noisy. Together, they give us the complete picture.

##### Sustained Effort Detection
We don't react to every momentary change. A 10-second surge isn't meaningful training. We only flag efforts sustained for multiple minutes using rolling windows that average over 60-second periods.

##### Context-Aware Adjustment
The same heart rate means different things depending on context. 170 bpm while pace is increasing = threshold effort starting. 170 bpm while pace is decreasing = cooldown from a finished effort.

##### Conservative Classification
When in doubt, we underclassify rather than overclassify. Better to miss a short effort than to incorrectly label easy running as hard work. This matches the training philosophy that quality efforts should be clearly defined and sustained.

### Visual Summary

Time:        0s    15s    30s    45s    60s 
Pace:       5:00  4:15   4:15   4:15   5:00
HR:          145   155    170    175    165

Without lag: [Recovery][Recovery][Threshold][Threshold]
With lag:    [Recovery][Threshold Threshold][Recovery]
             ↑         ↑                    ↑
        Start at    Extend back          End when
        pace change  to catch             pace slows
                     early effort