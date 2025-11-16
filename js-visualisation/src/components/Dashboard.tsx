"use client";

import { StatsCard } from "./StatsCard";
import { ActivityTable } from "./ActivityTable";
import { SimpleBarChart } from "./SimpleBarChart";
import { DashboardData } from "@/types/strava";
import { formatDistance, formatTime, formatSpeed } from "@/lib/utils";

interface DashboardProps {
  data: DashboardData;
}

export function Dashboard({ data }: DashboardProps) {
  const { activities, stats } = data;

  // Calculate activity type distribution for chart
  const activityTypeData = activities.reduce((acc, activity) => {
    acc[activity.type] = (acc[activity.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartData = Object.entries(activityTypeData).map(([type, count]) => ({
    label: type,
    value: count,
  }));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-slate-900">Strava Analytics</h1>
        </div>
        <p className="text-slate-600 text-lg max-w-2xl mx-auto">
          Track your fitness journey with beautiful insights and comprehensive activity analytics
        </p>
        <div className="w-24 h-1 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full mx-auto"></div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Activities"
          value={stats.totalActivities.toString()}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          }
        />
        <StatsCard
          title="Total Distance"
          value={formatDistance(stats.totalDistance)}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          }
        />
        <StatsCard
          title="Total Time"
          value={formatTime(stats.totalTime)}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatsCard
          title="Average Speed"
          value={formatSpeed(stats.averageSpeed)}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          }
        />
      </div>

      {/* Charts and Activities */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Activity Distribution Chart */}
        <div className="lg:col-span-1">
          <SimpleBarChart
            data={chartData}
            title="Activity Distribution"
          />
        </div>

        {/* Activities Table */}
        <div className="lg:col-span-2">
          <ActivityTable activities={activities} />
        </div>
      </div>
    </div>
  );
}