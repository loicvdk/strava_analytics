import { Dashboard } from "@/components/Dashboard";
import { DashboardData } from "@/types/strava";

// Sample data for demonstration
const sampleData: DashboardData = {
  activities: [
    {
      id: "1",
      name: "Morning Run",
      type: "Run",
      distance: 5000,
      moving_time: 1800,
      elapsed_time: 1900,
      total_elevation_gain: 50,
      start_date: "2024-09-26T06:30:00Z",
      start_date_local: "2024-09-26T08:30:00",
      average_speed: 2.78,
      max_speed: 4.2,
      average_heartrate: 150,
      max_heartrate: 175,
    },
    {
      id: "2",
      name: "Afternoon Cycle",
      type: "Ride",
      distance: 25000,
      moving_time: 3600,
      elapsed_time: 3800,
      total_elevation_gain: 200,
      start_date: "2024-09-25T14:00:00Z",
      start_date_local: "2024-09-25T16:00:00",
      average_speed: 6.94,
      max_speed: 12.5,
      average_heartrate: 140,
      max_heartrate: 165,
    },
    {
      id: "3",
      name: "Evening Walk",
      type: "Walk",
      distance: 3000,
      moving_time: 2400,
      elapsed_time: 2500,
      total_elevation_gain: 20,
      start_date: "2024-09-24T18:00:00Z",
      start_date_local: "2024-09-24T20:00:00",
      average_speed: 1.25,
      max_speed: 2.1,
    },
  ],
  stats: {
    totalDistance: 33000,
    totalTime: 7800,
    totalActivities: 3,
    averageSpeed: 4.23,
    totalElevationGain: 270,
  },
};

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="container mx-auto py-12 px-6 max-w-7xl">
        <Dashboard data={sampleData} />
      </div>
    </div>
  );
}
