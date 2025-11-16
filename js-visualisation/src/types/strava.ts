export interface Activity {
  id: string;
  name: string;
  type: string;
  distance: number;
  moving_time: number;
  elapsed_time: number;
  total_elevation_gain: number;
  start_date: string;
  start_date_local: string;
  average_speed: number;
  max_speed: number;
  average_heartrate?: number;
  max_heartrate?: number;
  calories?: number;
}

export interface ActivityStats {
  totalDistance: number;
  totalTime: number;
  totalActivities: number;
  averageSpeed: number;
  totalElevationGain: number;
}

export interface DashboardData {
  activities: Activity[];
  stats: ActivityStats;
}